import json
import asyncio
from datetime import datetime
import websockets
from db_connection.database import db
from scheduler.execution_scheduler.utils.apis  import negotiate_connection,get_token
from bson import ObjectId


EXT = "\x1e"

def make_invocation(target, invocation_id, args):
    return json.dumps({
        "type": 1,
        "target": target,
        "invocationId": str(invocation_id),
        "arguments": args
    }) + EXT

async def run_ws_client(access_token: str, connection_token: str,ProcessName:str,RobotName:str,EntryFile:str):
    websocket_url = (
        "wss://us01governor.futuredge.com/api/myhub"
        f"?Machine=WebClient&Key=random&id={connection_token}"
        f"&access_token={access_token.replace('Bearer ', '')}"
    )

    # State variables to store data between steps
    process_id = None
    target_robot_obj = None
    step = 0 # 0: Init, 1: Get Process, 2: Get Details/Robots, 3: Run, 4: Done

    async with websockets.connect(websocket_url) as ws:
        print(f"✔ Connected to WebSocket: {datetime.now()}")

        # --- Step 0: Handshake & Initial Pings ---
        await ws.send(json.dumps({"protocol": "json", "version": 1}) + EXT)
        await asyncio.sleep(0.1)
        # Initial keep-alive/view call provided in your example
        await ws.send(make_invocation("ViewNoPageProcess", "5", []))
        
        # --- Step 1: Request Process List ---
        print("-> Step 1: Requesting Process List...")
        await ws.send(make_invocation("ViewNoPageProcess", "25", []))

        async for message in ws:
            # Handle multiple messages in one packet (split by EXT)
            raw_messages = message.split(EXT)
            
            for raw_msg in raw_messages:
                if not raw_msg.strip():
                    continue
                
                data = json.loads(raw_msg)
                
                # Debug print (Optional: remove in production)
                # print(f"Received: {data}")

                # ---------------------------------------------------------
                # Handle Step 1 Response: Get Process ID
                # ---------------------------------------------------------
                if data.get("invocationId") == "25" and data.get("type") == 3:
                    result_list = data.get("result", [])
                    found_process = next((p for p in result_list if p["Name"] == ProcessName), None)
                    
                    if found_process:
                        process_id = found_process["Id"]
                        print(f"✔ Found Process '{ProcessName}' with ID: {process_id}")
                        
                        # Trigger Step 2: Get Entry File AND Get Robots
                        print("-> Step 2: Requesting File Info and Robot List...")
                        
                        # Request File Info (ID 26)
                        await ws.send(make_invocation("ViewNoPageXamlPackageVersion", "26", [process_id, False]))
                        
                        # Request Robot List (ID 27)
                        await ws.send(make_invocation("ViewRobot", "27", [0, 10, None, process_id]))
                    else:
                        print(f"❌ Process '{ProcessName}' not found.")
                        return "Failed: Process not found"

                # ---------------------------------------------------------
                # Handle Step 2 Response Part A: Get Entry File
                # ---------------------------------------------------------
                if data.get("invocationId") == "26" and data.get("type") == 3:
                    result = data.get("result", {})
                    file_list = result.get("listOfFiles", [])
                    # if file_list:
                    #     entry_file = file_list[0]["Name"]
                    #     print(f"✔ Entry File Found: {entry_file}")

                # ---------------------------------------------------------
                # Handle Step 2 Response Part B: Get Robot Object
                # ---------------------------------------------------------
                # Note: ViewRobot invocation returns 'true', the actual data comes as a target invocation 'viewRobot'
                if data.get("target") == "viewRobot" and data.get("type") == 1:
                    args = data.get("arguments", [])
                    if args and "Data" in args[0]:
                        robot_list = args[0]["Data"]
                        # Find the robot with the specific ClientId (e.g., 34)
                        target_robot_obj = next((r for r in robot_list if r["RobotName"] == RobotName), None)
                        
                        if target_robot_obj:
                            print(f"✔ Robot Found: {target_robot_obj['RobotName']} (RobotName: {RobotName})")
                        else:
                            print(f"❌ RobotName {RobotName} not found in available robots.")

                # ---------------------------------------------------------
                # Step 3: Run Execution
                # ---------------------------------------------------------
                # Check if we have gathered all necessary info
                if process_id and EntryFile and target_robot_obj and step < 3:
                    print("-> Step 3: Sending Execution Command...")
                    step = 3 # Prevent sending multiple times
                    
                    # Construct payload exactly as requested
                    # "arguments":["ProcessID","EntryFile",false,[RobotObj],[],0,10,null]
                    execution_args = [
                        process_id,
                        EntryFile,
                        False,
                        [target_robot_obj], # Must be a list containing the robot object
                        [],
                        0,
                        10,
                        None
                    ]
                    
                    await ws.send(make_invocation("RunProcessExecution", "28", execution_args))

                # ---------------------------------------------------------
                # Step 4: Confirm Execution Started
                # ---------------------------------------------------------
                if data.get("target") == "viewExecution" and step == 3:
                    print("✔ Execution Command Acknowledged via 'viewExecution'.")
                    print("-> Process Restarted Successfully.")
                    return "Completed"

                if data.get("invocationId") == "28" and data.get("type") == 3:
                    # Alternative confirmation if viewExecution doesn't come immediately
                    print("✔ RunProcessExecution returned success.")
                    return "Completed"

async def restart_action_bot(job_id:str):
    try:
        job = await db.jobs.find_one({"_id": ObjectId(job_id)})
        execution = await db.executions.find_one({"ExecutionId": job["ExecutionId"]})
        access_token = get_token()
        connection_token = negotiate_connection(access_token)
        response = await run_ws_client(access_token, connection_token,execution["Process"],execution["Robot"],execution["EntryFile"])
        return response
    except Exception as e:
        print(f"Error: {str(e)}")
        return "Failed"

# Logic to run the async loop
# if __name__ == "__main__":
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(restart_action_bot())