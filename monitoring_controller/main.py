from fastapi import FastAPI, HTTPException
from bson import ObjectId
from typing import List
from db_connection.database import db,ensure_collections

from schemas.job_schema import Job
from schemas.execution_schema import Execution
from schemas.logs_schema import Log
from schemas.rca_schema import RCA
from schemas.auditlog_schema import AuditLog
import asyncio
from scheduler.execution_scheduler.ws_client import run_ws_client
from scheduler.db_scheduler.monitor_faulted_executions import monitor_faulted_executions
from scheduler.db_scheduler.monitor_email_replies import monitor_email_replies
from scheduler.execution_scheduler.utils.apis import get_token,negotiate_connection

app = FastAPI(title="Automation Logging Server")

# Helper to convert ObjectId to str
def convert_id(doc):
    doc["_id"] = str(doc["_id"])
    return doc


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
    result = await db.jobs.insert_one(job.dict())
    return {"status": "Job inserted", "id": str(result.inserted_id)}

@app.get("/jobs")
async def get_jobs():
    jobs = await db.jobs.find().to_list(2000)
    return [convert_id(j) for j in jobs]

@app.get("/jobs/{job_id}")
async def get_job_by_id(job_id: str):
    job = await db.jobs.find_one({"_id": ObjectId(job_id)})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return convert_id(job)


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


# uvicorn main:app --reload --port 8001