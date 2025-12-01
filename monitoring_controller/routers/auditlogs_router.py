from fastapi import APIRouter, HTTPException
from bson import ObjectId
from db_connection.database import db
from schemas.auditlog_schema import AuditLog

router = APIRouter()

def convert_id(doc):
    doc["_id"] = str(doc["_id"])
    return doc

@router.post("/auditlog")
async def create_audit_log(audit: AuditLog):
    result = await db.auditlogs.insert_one(audit.model_dump())
    return {"status": "Audit log inserted", "id": str(result.inserted_id)}

@router.post("/auditlogs")
async def create_audit_logs(audits: list[AuditLog]):
    inserted_ids = []
    for audit in audits:
        result = await db.auditlogs.insert_one(audit.model_dump())
        inserted_ids.append(str(result.inserted_id))
    return {"status": "Audit logs inserted", "inserted_ids": inserted_ids, "count": len(inserted_ids)}

@router.get("/auditlogs")
async def get_audit_logs():
    logs = await db.auditlogs.find().to_list(2000)
    return [convert_id(l) for l in logs]

@router.get("/auditlogs/{audit_id}")
async def get_audit_log_by_id(audit_id: str):
    audit = await db.auditlogs.find_one({"_id": ObjectId(audit_id)})
    if not audit:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return convert_id(audit)

@router.get("/auditlogs/job/{job_id}")
async def get_audit_logs_by_job_id(job_id: str):
    logs_cursor = db.auditlogs.find({"jobId": job_id}).sort("timestamp", -1)
    logs = await logs_cursor.to_list(2000)
    return [convert_id(log) for log in logs]
