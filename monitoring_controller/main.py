from fastapi import FastAPI, HTTPException,Request
from bson import ObjectId
from typing import List
from db_connection.database import db,ensure_collections,watch_jobs_changes

from schemas.job_schema import Job,JobUpdate
from schemas.execution_schema import Execution
from schemas.logs_schema import Log
from schemas.rca_schema import RCA,RCAUpdate
from schemas.auditlog_schema import AuditLog
import asyncio
from scheduler.execution_scheduler.ws_client import run_ws_client
from scheduler.db_scheduler.monitor_faulted_executions import monitor_faulted_executions
from scheduler.monitor_email_replies.monitor_email_replies import monitor_email_replies
from scheduler.execution_scheduler.utils.apis import get_token,negotiate_connection
from datetime import datetime, timezone
from fastapi.middleware.cors import CORSMiddleware
from utils.smtp_services import send_email_SMTP
from utils.llm_mail_format import generate_email_content
from utils.restart_web_connection  import restart_action_bot

app = FastAPI(title="Automation Logging Server")


# Helper to convert ObjectId to str
def convert_id(doc):
    doc["_id"] = str(doc["_id"])
    return doc


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow your frontend origins
    allow_credentials=False,
    allow_methods=["*"],    # allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],    # allow all headers
)

@app.on_event("startup")
async def start_ws_client():
    access_token = get_token()
    connection_token = negotiate_connection(access_token)
    
    await ensure_collections()
    # Run websocket client as background task
    asyncio.create_task(run_ws_client(access_token, connection_token))
    asyncio.create_task(monitor_faulted_executions())
    asyncio.create_task(monitor_email_replies())

# -------------------------------
# JOB APIs
# -------------------------------
@app.post("/jobs")
async def create_job(job: Job):
    result = await db.jobs.insert_one(job.model_dump())
    return {"status": "Job inserted", "id": str(result.inserted_id)}

@app.get("/jobs")
async def get_jobs():
    jobs = await db.jobs.find().sort("CreatedAt", -1).to_list(2000)
    return [convert_id(j) for j in jobs]

@app.get("/jobs/{job_id}")
async def get_job_by_id(job_id: str):
    job = await db.jobs.find_one({"_id": ObjectId(job_id)})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return convert_id(job)

@app.put("/jobs/{job_id}")
async def update_job(job_id: str, job: JobUpdate):
    update_data = {k: v for k, v in job.dict().items() if v is not None}

    # Always update timestamp
    update_data["UpdatedAt"] = datetime.now(timezone.utc)

    result = await db.jobs.update_one(
        {"_id": ObjectId(job_id)},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")

    updated_job = await db.jobs.find_one({"_id": ObjectId(job_id)})
    return convert_id(updated_job)

# -------------------------------
# EXECUTION APIs
# -------------------------------
@app.post("/executions")
async def create_execution(execution: Execution):
    result = await db.executions.insert_one(execution.dict())
    return {"status": "Execution inserted", "id": str(result.inserted_id)}

@app.get("/executions")
async def get_executions():
    executions = await db.executions.find().to_list(2000)
    return [convert_id(e) for e in executions]

@app.get("/executions/{execution_id}")
async def get_execution_by_id(execution_id: str):
    execution = await db.executions.find_one({"ExecutionId": execution_id})
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return convert_id(execution)



# -------------------------------
# LOG APIs
# -------------------------------
@app.post("/logs")
async def create_log(log: Log):
    result = await db.logs.insert_one(log.dict())
    return {"status": "Log inserted", "id": str(result.inserted_id)}

@app.get("/logs/{exicution_id}")
async def get_logs(exicution_id:str):
    logs = await db.logs.find({"ExecutionID":exicution_id}).to_list(2000)
    return [convert_id(l) for l in logs]

@app.get("/logs/{log_id}")
async def get_log_by_id(log_id: str):
    log = await db.logs.find_one({"_id": ObjectId(log_id)})
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return convert_id(log)


# -------------------------------
# RCA APIs
# -------------------------------
@app.post("/rca")
async def create_rca(rca: RCA):
    result = await db.rca.insert_one(rca.dict())
    return {"status": "RCA inserted", "id": str(result.inserted_id)}

@app.get("/rca")
async def get_rcas():
    rcas = await db.rca.find().to_list(2000)
    return [convert_id(r) for r in rcas]

@app.get("/rca/{rca_id}")
async def get_rca_by_id(rca_id: str):
    rca = await db.rca.find_one({"_id": ObjectId(rca_id)})
    if not rca:
        raise HTTPException(status_code=404, detail="RCA not found")
    return convert_id(rca)

@app.put("/rca/{rca_id}")
async def update_rca(rca_id: str, rca_update: RCAUpdate):
    """
    Update an existing RCA record by RCA_ID.
    Supports partial updates: only provided fields are updated.
    """
    # Convert RCAUpdate object to dict and remove None values
    update_data = {k: v for k, v in rca_update.dict().items() if v is not None}

    if not update_data:
        return {"status": "No fields to update"}

    # Always update timestamp
    update_data["UpdatedAt"] = datetime.now(timezone.utc)

    result = await db.rca.update_one(
        {"RCA_ID": rca_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="RCA not found")

    # Return the updated record
    updated_rca = await db.rca.find_one({"RCA_ID": rca_id})
    return convert_id(updated_rca)

@app.post("/add_rca")
async def add_new_rca_endpoint(rca: RCA):
    """
    API endpoint to add a new RCA record.
    """
    try:
        result = await db.rca.insert_one(rca.model_dump())
        return {
            "status": "success",
            "message": "RCA added successfully",
            "id": str(result.inserted_id)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to add RCA: {str(e)}"
        }

# -------------------------------
# AUDIT LOG APIs
# -------------------------------
@app.post("/auditlog")
async def create_audit_log(audit: AuditLog):
    result = await db.auditlogs.insert_one(audit.model_dump())
    return {"status": "Audit log inserted", "id": str(result.inserted_id)}

@app.post("/auditlogs")
async def create_audit_logs(audits: List[AuditLog]):
    inserted_ids = []
    for audit in audits:
        result = await db.auditlogs.insert_one(audit.model_dump())
        inserted_ids.append(str(result.inserted_id))
    
    return {
        "status": "Audit logs inserted",
        "inserted_ids": inserted_ids,
        "count": len(inserted_ids)
    }

@app.get("/auditlogs")
async def get_audit_logs():
    logs = await db.auditlogs.find().to_list(2000)
    return [convert_id(l) for l in logs]

@app.get("/auditlogs/{audit_id}")
async def get_audit_log_by_id(audit_id: str):
    audit = await db.auditlogs.find_one({"_id": ObjectId(audit_id)})
    if not audit:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return convert_id(audit)

@app.get("/auditlogs/job/{job_id}")
async def get_audit_logs_by_job_id(job_id: str):
    """
    Return all audit logs associated with a specific job_id.
    """
    logs_cursor = db.auditlogs.find({"jobId": job_id}).sort("timestamp", -1)
    logs = await logs_cursor.to_list(2000)

    return [convert_id(log) for log in logs]

@app.post("/send_email")
async def send_email(subject:str,body:str,job_id:str,email_type:str):
    """
    Generates subject and body using LLM, then sends email.
    """
    print(f"subject : {subject}, body: {body}, job_id: {job_id}")
    success = await send_email_SMTP(subject, body,job_id,email_type)

    return {"success": success, "subject": subject, "body": body}

@app.post("/restart/{job_id}")
async def restart_bot(job_id:str):
    re=await restart_action_bot(job_id)
    return {"status":"success"}
# uvicorn main:app --reload --port 8001