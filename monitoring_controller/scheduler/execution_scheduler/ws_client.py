import json
import asyncio
from datetime import datetime
import websockets
from db_connection.database import db

all_exec = None
all_logs = None
EXT = "\x1e"

def make_invocation(target, invocation_id, args):
    return json.dumps({
        "type": 1,
        "target": target,
        "invocationId": str(invocation_id),
        "arguments": args
    }) + EXT

# -------------------------------
# Save executions into MongoDB
# -------------------------------
async def save_executions_to_db(df_exec):
    print("save_executions_to_db :")
    for exec_dict in df_exec:
        await db.executions.update_one(
            {"ExecutionId": exec_dict["ExecutionId"]},
            {"$set": exec_dict},
            upsert=True
        )

# -------------------------------
# Save logs into MongoDB
# -------------------------------
async def save_logs_to_db(df_log):
    print("save_logs_to_db :")
    if not isinstance(df_log, list):
        df_log = df_log.to_dict('records')
    for log_dict in df_log:
        await db.logs.update_one(
            {"logid": log_dict["logid"]},
            {"$set": log_dict},
            upsert=True
        )

# -------------------------------
# WebSocket client
# -------------------------------
async def run_ws_client(access_token: str, connection_token: str):

    websocket_url = (
        "wss://us01governor.futuredge.com/api/myhub"
        f"?Machine=WebClient&Key=random&id={connection_token}"
        f"&access_token={access_token.replace('Bearer ', '')}"
    )

    async with websockets.connect(websocket_url) as ws:
        print(f"✔ Connected to WebSocket: {datetime.now()}")

        # SignalR handshake
        await ws.send(json.dumps({"protocol": "json", "version": 1}) + EXT)
        await asyncio.sleep(0.1)

        async def fetch_executions():
            await ws.send(make_invocation("ViewExecution", "1", [0, 3, None]))
            print("📤 Requested executions")

        async def fetch_logs(execution_ids):
            for exc_id in execution_ids:
                await ws.send(make_invocation(
                    "ViewLogExecution",
                    str(datetime.now().timestamp()).replace('.', ''),  # unique ID
                    [exc_id, 0, 50, datetime.now().day, datetime.now().month, datetime.now().year, ""]
                ))
            print("📤 Requested logs for executions:", execution_ids)
            
        

        # Run first fetch immediately
        await fetch_executions()

        # Schedule periodic fetch every 10 minutes
        asyncio.create_task(periodic_fetch(ws, fetch_executions, interval=300))

        global all_exec, all_logs
        while True:
            raw = await ws.recv()
            frames = [f for f in raw.split(EXT) if f.strip()]

            for frame in frames:
                try:
                    msg = json.loads(frame)
                    if msg.get("type") == 6:  # ping
                        continue

                    target = msg.get("target", "").lower()

                    # Executions
                    if msg.get("type") == 1 and target == "viewexecution":
                        data = msg["arguments"][0]["Data"]
                        print(f"📌 Executions received: {len(data)}")
                        await save_executions_to_db(data)

                        # Fetch logs for all executions
                        execution_ids = [e["ExecutionId"] for e in data]
                        asyncio.create_task(fetch_logs(execution_ids))

                    # Logs
                    elif msg.get("type") == 1 and target == "viewlogexecution":
                        data = msg["arguments"][0]["Data"]
                        print(f"📝 Logs received: {len(data)}")
                        await save_logs_to_db(data)

                except Exception as e:
                    print("⚠ Error processing frame:", e, frame)

# -------------------------------
# Periodic fetch task
# -------------------------------
async def periodic_fetch(ws, fetch_func, interval=600):
    while True:
        await asyncio.sleep(interval)
        await fetch_func()
