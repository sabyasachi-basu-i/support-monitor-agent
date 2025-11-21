# monitoring_single_fixed.py
"""
Improved unified monitoring script (single-file).
- Handles different ExecutionID capitalizations.
- Uses upsert/unique index logic to avoid duplicates.
- Robust websocket parsing and reconnection.
- Normalized state handling.
- Continuous merged-table monitor + job posting.
"""

import asyncio
import json
import time
import logging
from typing import List, Dict, Any, Optional

import requests
import websockets
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ---------------------------
# CONFIG - change these
# ---------------------------
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "future_edge_db"

LOGIN_URL = "https://us01governor.futuredge.com/api/api/login"
NEGOTIATE_URL = (
    "https://us01governor.futuredge.com/api/myhub/negotiate"
    "?Machine=WebClient&Key=random&negotiateVersion=1"
)
WEBSOCKET_URL = "wss://us01governor.futuredge.com/api/myhub"
JOB_API_URL = "https://yourapi.com/post_event"  # <--- replace with real

# credentials - DO NOT hardcode in production
LOGIN_PAYLOAD = {
    "loginType": "RiYSAGovernor",
    "loginuser": "admin",
    "pass": "FutureEdge@123",
    "tenant": "default",
}

# ---------------------------
# logging
# ---------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("monitor")

# ---------------------------
# low-level utils
# ---------------------------
RECORD_TERMINATOR = "\x1e"


def make_invocation(target: str, invocation_id: str, args: List[Any]) -> str:
    return json.dumps(
        {"type": 1, "target": target, "invocationId": str(invocation_id), "arguments": args}
    ) + RECORD_TERMINATOR


# ---------------------------
# Mongo setup
# ---------------------------
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

execution_col = db["ViewExecution"]
log_col = db["ViewLogExecution"]
merged_col = db["MergedExecutionData"]
job_col = db["JobTable"]

# Ensure unique index on normalized 'executionid' (lowercase key).
execution_col.create_index([("executionid", ASCENDING)], unique=True)
log_col.create_index([("executionid", ASCENDING), ("logid", ASCENDING)], unique=True)
merged_col.create_index([("executionid", ASCENDING)], unique=True)
job_col.create_index([("executionid", ASCENDING)], unique=True)

# ---------------------------
# Normalization helpers
# ---------------------------
FAULT_STATES = {"fault", "faulted", "error", "failed"}


def find_executionid_in_record(rec: Dict[str, Any]) -> Optional[str]:
    """
    Search record keys case-insensitively for a field representing execution id.
    Accepts 'executionid', 'execution_id', 'executionid', 'execution id', 'executionID', etc.
    """
    for k, v in rec.items():
        if not isinstance(k, str):
            continue
        key_normal = k.lower().replace("_", "").replace(" ", "")
        if key_normal == "executionid" or key_normal.endswith("executionid"):
            return str(v) if v is not None else None
    return None


def normalize_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a copy with lower-cased keys and guaranteed 'executionid' and 'state_lower' fields.
    We intentionally keep original keys too (prefixed) if you want them, but main logic uses normalized fields.
    """
    out = {}
    for k, v in rec.items():
        if not isinstance(k, str):
            out[k] = v
            continue
        # keep original with lower-case key to simplify queries
        out[k.strip().lower()] = v

    # canonical executionid
    if "executionid" not in out or out.get("executionid") in (None, ""):
        execid = find_executionid_in_record(rec)
        if execid:
            out["executionid"] = execid

    # canonical state lowercase
    state_val = out.get("state") or out.get("state_lower") or ""
    out["state_lower"] = (state_val or "").strip().lower()

    return out


# ---------------------------
# DB operations (idempotent)
# ---------------------------
def upsert_execution(record: Dict[str, Any]) -> None:
    rec = normalize_record(record)
    execid = rec.get("executionid")
    if not execid:
        logger.debug("Skipping execution insert - no executionid in record: %s", record)
        return

    # avoid overwriting existing execution doc; set-on-insert keeps first-seen values.
    try:
        execution_col.update_one(
            {"executionid": execid},
            {"$setOnInsert": rec, "$set": {"last_seen": time.time()}},
            upsert=True,
        )
    except Exception as exc:
        logger.warning("Error upserting execution %s: %s", execid, exc)


def upsert_log(record: Dict[str, Any]) -> None:
    rec = normalize_record(record)
    execid = rec.get("executionid")
    # try to find a log-specific unique key (logid) to avoid false merges
    logid = rec.get("logid") or rec.get("log_id") or rec.get("id")
    filter_query = {"executionid": execid}
    if logid:
        filter_query["logid"] = logid
        rec["logid"] = logid

    if not execid:
        logger.debug("Skipping log insert - no executionid in log: %s", record)
        return

    try:
        log_col.update_one(filter_query, {"$setOnInsert": rec}, upsert=True)
    except Exception as exc:
        logger.warning("Error upserting log %s/%s: %s", execid, logid, exc)


def merge_execution_logs_if_ready(executionid: str) -> None:
    if not executionid:
        return
    exec_doc = execution_col.find_one({"executionid": executionid})
    if not exec_doc:
        logger.debug("No execution doc yet for %s", executionid)
        return
    log_docs = list(log_col.find({"executionid": executionid}))
    if not log_docs:
        logger.debug("No log docs yet for %s", executionid)
        return

    merged_records = []
    for log_doc in log_docs:
        # Combine exec and log; prefer execution fields from exec_doc and logs for log-specific keys
        merged = {**exec_doc, **log_doc}
        # maintain a normalized executionid & state_lower
        merged["executionid"] = executionid
        merged["state_lower"] = (exec_doc.get("state_lower") or exec_doc.get("state", "")).lower()
        merged_records.append(merged)

    # Insert each merged doc idempotently (use combination of executionid+logid)
    for m in merged_records:
        filter_q = {"executionid": m["executionid"], "logid": m.get("logid")}
        try:
            merged_col.update_one(filter_q, {"$setOnInsert": m}, upsert=True)
        except Exception as exc:
            logger.warning("Failed to upsert merged record for %s: %s", executionid, exc)


# ---------------------------
# Scheduler jobs
# ---------------------------
scheduler = AsyncIOScheduler()


def fault_monitor_job():
    """
    Periodically walk executions with fault states and try to merge logs.
    (Fallback if change streams are not used)
    """
    try:
        # find executions whose normalized state indicates fault
        docs = execution_col.find({"state_lower": {"$in": list(FAULT_STATES)}})
        for d in docs:
            exec_id = d.get("executionid")
            if exec_id:
                merge_execution_logs_if_ready(exec_id)
    except Exception as exc:
        logger.exception("Error in fault_monitor_job: %s", exc)


# schedule every 30 seconds
scheduler.add_job(fault_monitor_job, "interval", seconds=30)


# ---------------------------
# Monitor merged table and post job events
# ---------------------------
async def monitor_merged_table(poll_interval: float = 5.0):
    """
    Continuously poll merged table for records with fault-like states, then
    insert executionId into job table (if not exists) and POST related records.
    """
    while True:
        try:
            cursor = merged_col.find({"state_lower": {"$in": list(FAULT_STATES)}})
            async_exec_ids = set()
            for rec in cursor:
                exec_id = rec.get("executionid")
                if not exec_id:
                    continue
                if exec_id in async_exec_ids:
                    continue
                # atomic check-and-insert into job table
                existed = job_col.find_one({"executionid": exec_id})
                if existed:
                    logger.info("executionId %s already in JobTable -> skip", exec_id)
                    async_exec_ids.add(exec_id)
                    continue

                try:
                    job_col.insert_one({"executionid": exec_id, "created_at": time.time()})
                    logger.info("Inserted executionId %s into JobTable", exec_id)
                except DuplicateKeyError:
                    logger.info("Race: executionId %s already created by other process", exec_id)
                except Exception as exc:
                    logger.warning("Failed to insert into JobTable %s: %s", exec_id, exc)
                    continue

                # fetch all related merged records and POST them
                related = list(merged_col.find({"executionid": exec_id}))
                try:
                    resp = requests.post(JOB_API_URL, json=related, timeout=15)
                    resp.raise_for_status()
                    logger.info("Posted executionId %s to job API (%s)", exec_id, resp.status_code)
                except Exception as exc:
                    logger.warning("Failed to POST executionId %s: %s", exec_id, exc)

                async_exec_ids.add(exec_id)

        except Exception as exc:
            logger.exception("Error in monitor_merged_table loop: %s", exc)

        await asyncio.sleep(poll_interval)


# ---------------------------
# WebSocket listener
# ---------------------------
async def fetch_viewlog_via_ws(executionid: str, ws: websockets.WebSocketClientProtocol):
    """Request ViewLogExecution for a given executionid via invocation."""
    if not executionid:
        return
    try:
        # arguments example - keep same shape you used earlier
        await ws.send(make_invocation("ViewLogExecution", str(executionid), [executionid, 0, 10, 19, 11, 2025, ""]))
    except Exception as exc:
        logger.warning("Error sending ViewLogExecution invocation for %s: %s", executionid, exc)


async def run_client():
    """
    Main websocket loop with reconnection and message handling.
    """
    backoff = 1
    while True:
        try:
            # auth + negotiate
            token = get_token()
            conn_token = negotiate_connection(token)
            # build websocket url: ensure token is passed correctly
            ws_url = (
                f"{WEBSOCKET_URL}?Machine=WebClient&Key=random&id={conn_token}"
                f"&access_token={token.replace('Bearer ', '')}"
            )
            logger.info("Connecting to websocket: %s", WEBSOCKET_URL)
            async with websockets.connect(ws_url, max_size=None) as ws:
                logger.info("WebSocket connected")
                # send initial signalr handshake
                await ws.send(json.dumps({"protocol": "json", "version": 1}) + RECORD_TERMINATOR)
                await asyncio.sleep(0.1)
                # request initial ViewExecution snapshot
                await ws.send(make_invocation("ViewExecution", "1", [0, 100, None]))

                backoff = 1  # reset backoff on success

                while True:
                    raw = await ws.recv()
                    # SignalR frames are delimited by RECORD_TERMINATOR
                    frames = [f for f in raw.split(RECORD_TERMINATOR) if f.strip()]
                    for frame in frames:
                        try:
                            msg = json.loads(frame)
                        except Exception:
                            logger.debug("Non-JSON frame received (skip)")
                            continue

                        msg_type = msg.get("type")
                        target_raw = msg.get("target")
                        target = (target_raw or "").lower()
                        # invocation result
                        if msg_type == 1 and target == "viewexecution":
                            # arguments -> Data structure
                            args = msg.get("arguments") or []
                            if not args:
                                continue
                            # try to extract Data payload safely
                            data_block = args[0].get("Data") if isinstance(args[0], dict) else None
                            if not data_block:
                                logger.debug("No Data block in ViewExecution args")
                                continue
                            faulted_execids = []
                            # data_block can be a list of records
                            for rec in data_block:
                                upsert_execution(rec)
                                rec_norm = normalize_record(rec)
                                if rec_norm.get("state_lower") in FAULT_STATES:
                                    faulted_execids.append(rec_norm.get("executionid"))

                            logger.info("Inserted/updated %d execution records", len(data_block))
                            if faulted_execids:
                                logger.info("Faulted ExecutionIds: %s", faulted_execids)
                                # ask for logs for each
                                for eid in faulted_execids:
                                    await fetch_viewlog_via_ws(eid, ws)

                        elif msg_type == 1 and target == "viewlogexecution":
                            # handle view logs
                            args = msg.get("arguments") or []
                            data_block = args[0].get("Data") if isinstance(args[0], dict) else None
                            if not data_block:
                                logger.debug("No Data block in ViewLogExecution args")
                                continue
                            for rec in data_block:
                                upsert_log(rec)
                                rec_norm = normalize_record(rec)
                                execid = rec_norm.get("executionid")
                                if execid:
                                    merge_execution_logs_if_ready(execid)
                            logger.info("Inserted/updated %d log records and attempted merges", len(data_block))

                        else:
                            # other messages: ping/pong/ack etc
                            logger.debug("OTHER MESSAGE type=%s target=%s", msg_type, target_raw)

        except Exception as exc:
            logger.exception("WebSocket disconnected or error: %s", exc)
            # backoff with capped wait
            await asyncio.sleep(min(backoff, 60))
            backoff = backoff * 2 if backoff < 60 else 60


# ---------------------------
# simple auth helpers (same shape as your original)
# ---------------------------
def get_token() -> str:
    """Perform login and return Bearer token string."""
    res = requests.post(LOGIN_URL, json=LOGIN_PAYLOAD, timeout=15)
    res.raise_for_status()
    data = res.json()
    token = "Bearer " + data["token"]
    logger.info("Login success")
    return token


def negotiate_connection(access_token: str) -> str:
    headers = {
        "Authorization": access_token,
        "Accept": "*/*",
        "Content-Type": "text/plain;charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "x-signalr-user-agent": "Microsoft SignalR/5.0 (5.0.17; Python)",
    }
    res = requests.post(NEGOTIATE_URL, headers=headers, data="", timeout=15)
    res.raise_for_status()
    data = res.json()
    logger.info("Negotiate success")
    return data["connectionToken"]


# ---------------------------
# application entry
# ---------------------------
async def main():
    scheduler.start()
    ws_task = asyncio.create_task(run_client())
    job_task = asyncio.create_task(monitor_merged_table())
    await asyncio.gather(ws_task, job_task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted, shutting down.")
