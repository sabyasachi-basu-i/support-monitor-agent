"""
CORRECTED Monitoring Script - Follows Requirements EXACTLY
- Action 1: WebSocket → ViewExecution (skip duplicates)
- Action 2: Monitor ViewExecution → Process Faults → Job Table → Merge → API
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

# ---------------------------
# CONFIG
# ---------------------------
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "future_edge_db"

LOGIN_URL = "https://us01governor.futuredge.com/api/api/login"
NEGOTIATE_URL = (
    "https://us01governor.futuredge.com/api/myhub/negotiate"
    "?Machine=WebClient&Key=random&negotiateVersion=1"
)
WEBSOCKET_URL = "wss://us01governor.futuredge.com/api/myhub"
JOB_API_URL = "http://127.0.0.1:5000/post_event"  # REPLACE WITH REAL URL

LOGIN_PAYLOAD = {
    "loginType": "RiYSAGovernor",
    "loginuser": "admin",
    "pass": "FutureEdge@123",
    "tenant": "default",
}

# ---------------------------
# Logging
# ---------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("monitor")

# ---------------------------
# MongoDB Setup
# ---------------------------
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

execution_col = db["ViewExecution"]
log_col = db["ViewLogExecution"]
job_col = db["JobTable"]
merged_col = db["MergedExecutionData"]

# Create unique indexes
execution_col.create_index([("executionid", ASCENDING)], unique=True)
log_col.create_index([("executionid", ASCENDING), ("logid", ASCENDING)], unique=True)
job_col.create_index([("executionid", ASCENDING)], unique=True)

# ---------------------------
# Utilities
# ---------------------------
RECORD_TERMINATOR = "\x1e"
FAULT_STATES = {"fault", "faulted", "error", "failed"}

def make_invocation(target: str, invocation_id: str, args: List[Any]) -> str:
    """Create SignalR invocation message."""
    return json.dumps({
        "type": 1,
        "target": target,
        "invocationId": str(invocation_id),
        "arguments": args
    }) + RECORD_TERMINATOR


def normalize_executionid(record: Dict[str, Any]) -> Optional[str]:
    """Extract executionid from record (case-insensitive)."""
    for k, v in record.items():
        if isinstance(k, str) and k.lower().replace("_", "").replace(" ", "") == "executionid":
            return str(v) if v is not None else None
    return None


def normalize_state(record: Dict[str, Any]) -> str:
    """Extract and normalize state field."""
    for k, v in record.items():
        if isinstance(k, str) and k.lower() == "state":
            return str(v).strip().lower() if v else ""
    return ""


def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize record with lowercase keys and standard fields."""
    normalized = {}
    for k, v in record.items():
        if isinstance(k, str):
            normalized[k.lower()] = v
        else:
            normalized[k] = v
    
    # Ensure standard fields
    if "executionid" not in normalized:
        execid = normalize_executionid(record)
        if execid:
            normalized["executionid"] = execid
    
    if "state_lower" not in normalized:
        normalized["state_lower"] = normalize_state(record)
    
    return normalized


# ---------------------------
# ACTION 1: Store ViewExecution (Skip Duplicates)
# ---------------------------
def store_execution_record(record: Dict[str, Any]) -> bool:
    """
    Insert ViewExecution record only if new.
    Returns True if inserted, False if duplicate.
    """
    rec = normalize_record(record)
    execid = rec.get("executionid")
    
    if not execid:
        logger.debug("Skipping record without executionid")
        return False
    
    try:
        # Use insert_one to truly skip duplicates (don't update existing)
        rec["inserted_at"] = time.time()
        execution_col.insert_one(rec)
        logger.info(f"✓ Inserted NEW execution: {execid}")
        return True
    except DuplicateKeyError:
        logger.debug(f"⊘ Skipped DUPLICATE execution: {execid}")
        return False
    except Exception as exc:
        logger.error(f"Error storing execution {execid}: {exc}")
        return False


# ---------------------------
# ACTION 2: Monitor ViewExecution for Faults
# ---------------------------
# Global tracking to avoid re-processing same ExecutionId
processed_executions = set()

async def monitor_viewexecution_for_faults(poll_interval: float = 2.0):
    """
    ACTION 2: Continuously monitor ViewExecution collection.
    When state=Fault found, execute the full workflow.
    """
    logger.info("Started monitoring ViewExecution for Fault states...")
    
    while True:
        try:
            # Find all Fault records in ViewExecution
            fault_cursor = execution_col.find({"state_lower": {"$in": list(FAULT_STATES)}})
            
            for exec_record in fault_cursor:
                execid = exec_record.get("executionid")
                
                if not execid or execid in processed_executions:
                    continue
                
                logger.info(f"🔴 FAULT DETECTED: {execid}")
                
                # Step 1: Check if already in Job Table
                existing_job = job_col.find_one({"executionid": execid})
                
                if existing_job:
                    logger.info(f"⊘ ExecutionId {execid} already in Job Table → SKIP")
                    processed_executions.add(execid)
                    continue
                
                # Step 2: Insert ExecutionId into Job Table
                try:
                    job_col.insert_one({
                        "executionid": execid,
                        "created_at": time.time(),
                        "status": "pending"
                    })
                    logger.info(f"✓ Inserted {execid} into Job Table")
                except DuplicateKeyError:
                    logger.info(f"Race condition: {execid} already in Job Table")
                    processed_executions.add(execid)
                    continue
                
                # Step 3: Wait for logs to be fetched (they're fetched by WebSocket)
                # Give some time for logs to arrive
                await asyncio.sleep(1)
                
                # Step 4: Check if logs exist
                log_records = list(log_col.find({"executionid": execid}))
                
                if not log_records:
                    logger.warning(f"No logs found yet for {execid}, will retry next cycle")
                    continue
                
                # Step 5: Merge ViewExecution + ViewLogExecution into ONE record
                merged_data = merge_execution_with_logs(execid, exec_record, log_records)
                
                if not merged_data:
                    logger.warning(f"Failed to merge data for {execid}")
                    continue
                
                # Step 6: Send merged data via API
                success = send_to_api(execid, merged_data)
                
                if success:
                    # Update Job Table status
                    job_col.update_one(
                        {"executionid": execid},
                        {"$set": {"status": "completed", "completed_at": time.time()}}
                    )
                    processed_executions.add(execid)
                    logger.info(f"✓ COMPLETED processing for {execid}")
                else:
                    logger.error(f"Failed to send API for {execid}")
        
        except Exception as exc:
            logger.exception(f"Error in monitor loop: {exc}")
        
        await asyncio.sleep(poll_interval)


def merge_execution_with_logs(execid: str, exec_record: Dict, log_records: List[Dict]) -> Dict:
    """
    Merge execution record with all its log records into ONE record.
    Returns single merged record with logs as array.
    """
    # Clean execution record (remove MongoDB _id and normalize)
    clean_exec = {k: v for k, v in exec_record.items() if k != "_id"}
    
    # Clean all log records
    clean_logs = []
    for log_rec in log_records:
        clean_log = {k: v for k, v in log_rec.items() if k != "_id"}
        clean_logs.append(clean_log)
    
    # Create ONE merged record
    merged_record = {
        "executionid": execid,
        "execution": clean_exec,  # All execution data
        "logs": clean_logs,        # All logs as array
        "log_count": len(clean_logs),
        "merged_at": time.time()
    }
    
    # Store in MergedExecutionData collection (one record per ExecutionId)
    try:
        merged_col.update_one(
            {"executionid": execid},
            {"$set": merged_record},
            upsert=True
        )
        logger.info(f"✓ Merged 1 record with {len(clean_logs)} logs for {execid}")
    except Exception as exc:
        logger.warning(f"Failed to store merged record: {exc}")
    
    return merged_record


def send_to_api(execid: str, merged_data: Dict) -> bool:
    """
    Send ONE merged record to external API.
    Returns True if successful.
    """
    try:
        # merged_data is already clean (no _id fields)
        payload = merged_data  # Send the single merged record directly
        
        response = requests.post(JOB_API_URL, json=payload, timeout=15)
        response.raise_for_status()
        
        logger.info(f"✓ API POST successful for {execid} (status: {response.status_code})")
        return True
        
    except Exception as exc:
        logger.error(f"API POST failed for {execid}: {exc}")
        return False


# ---------------------------
# WebSocket Client (ACTION 1 + Log Fetching)
# ---------------------------
async def request_logs_for_execution(execid: str, ws):
    """Request logs from WebSocket for specific ExecutionId."""
    try:
        invocation = make_invocation(
            "ViewLogExecution",
            f"log-{execid}",
            [execid, 0, 10, 19, 11, 2025, ""]
        )
        await ws.send(invocation)
        logger.info(f"→ Requested logs for {execid}")
    except Exception as exc:
        logger.error(f"Failed to request logs for {execid}: {exc}")



async def websocket_client():
    """
    WebSocket client that:
    1. Receives ViewExecution data → stores in MongoDB (ACTION 1)
    2. When Fault detected → requests logs immediately
    """
    backoff = 1
    
    while True:
        try:
            # Authenticate
            token = get_token()
            conn_token = negotiate_connection(token)
            
            ws_url = (
                f"{WEBSOCKET_URL}?Machine=WebClient&Key=random&id={conn_token}"
                f"&access_token={token.replace('Bearer ', '')}"
            )
            
            logger.info("Connecting to WebSocket...")
            
            async with websockets.connect(ws_url, max_size=None) as ws:
                logger.info("✓ WebSocket connected")
                
                # SignalR handshake
                await ws.send(json.dumps({"protocol": "json", "version": 1}) + RECORD_TERMINATOR)
                await asyncio.sleep(0.1)
                
                # Request initial ViewExecution data
                await ws.send(make_invocation("ViewExecution", "1", [0, 100, None]))
                
                backoff = 1  # Reset backoff
                
                # Message loop
                while True:
                    raw = await ws.recv()
                    frames = [f for f in raw.split(RECORD_TERMINATOR) if f.strip()]
                    
                    for frame in frames:
                        try:
                            msg = json.loads(frame)
                        except:
                            continue
                        
                        msg_type = msg.get("type")
                        target = (msg.get("target") or "").lower()
                        
                        # Handle ViewExecution responses
                        if msg_type == 1 and target == "viewexecution":
                            args = msg.get("arguments", [])
                            if not args:
                                continue
                            
                            data_block = args[0].get("Data") if isinstance(args[0], dict) else None
                            if not data_block:
                                continue
                            
                            # ACTION 1: Store each execution record
                            fault_execids = []
                            for record in data_block:
                                inserted = store_execution_record(record)
                                
                                # Check if this is a fault
                                if inserted:
                                    rec_norm = normalize_record(record)
                                    if rec_norm.get("state_lower") in FAULT_STATES:
                                        execid = rec_norm.get("executionid")
                                        if execid:
                                            fault_execids.append(execid)
                            
                            # Request logs for faulted executions immediately
                            if fault_execids:
                                logger.info(f"Requesting logs for {len(fault_execids)} faulted executions")
                                for execid in fault_execids:
                                    await request_logs_for_execution(execid, ws)
                        
                        # Handle ViewLogExecution responses
                        elif msg_type == 1 and target == "viewlogexecution":
                            args = msg.get("arguments", [])
                            data_block = args[0].get("Data") if isinstance(args[0], dict) else None
                            
                            if not data_block:
                                continue
                            
                            # Store log records (skip duplicates)
                            for log_record in data_block:
                                rec_norm = normalize_record(log_record)
                                execid = rec_norm.get("executionid")
                                logid = rec_norm.get("logid") or rec_norm.get("id") or str(time.time())
                                
                                if not execid:
                                    continue
                                
                                try:
                                    rec_norm["logid"] = logid
                                    rec_norm["received_at"] = time.time()
                                    log_col.insert_one(rec_norm)
                                    logger.info(f"✓ Stored log for {execid}")
                                except DuplicateKeyError:
                                    logger.debug(f"⊘ Skipped duplicate log for {execid}")
                                except Exception as exc:
                                    logger.error(f"Error storing log: {exc}")
        
        except Exception as exc:
            logger.exception(f"WebSocket error: {exc}")
            await asyncio.sleep(min(backoff, 60))
            backoff = min(backoff * 2, 60)


# ---------------------------
# Authentication
# ---------------------------
def get_token() -> str:
    """Login and get Bearer token."""
    res = requests.post(LOGIN_URL, json=LOGIN_PAYLOAD, timeout=15)
    res.raise_for_status()
    token = "Bearer " + res.json()["token"]
    logger.info("✓ Login successful")
    return token


def negotiate_connection(access_token: str) -> str:
    """Negotiate SignalR connection."""
    headers = {
        "Authorization": access_token,
        "Accept": "*/*",
        "Content-Type": "text/plain;charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "x-signalr-user-agent": "Microsoft SignalR/5.0 (5.0.17; Python)",
    }
    res = requests.post(NEGOTIATE_URL, headers=headers, data="", timeout=15)
    res.raise_for_status()
    logger.info("✓ Negotiate successful")
    return res.json()["connectionToken"]


# ---------------------------
# Main Entry Point
# ---------------------------
async def main():
    """
    Run both actions concurrently:
    - WebSocket client (ACTION 1 + log fetching)
    - ViewExecution monitor (ACTION 2)
    """
    logger.info("=" * 60)
    logger.info("Starting Monitoring System")
    logger.info("=" * 60)
    
    ws_task = asyncio.create_task(websocket_client())
    monitor_task = asyncio.create_task(monitor_viewexecution_for_faults())
    
    await asyncio.gather(ws_task, monitor_task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")