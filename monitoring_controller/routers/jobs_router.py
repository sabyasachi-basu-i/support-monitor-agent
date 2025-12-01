from fastapi import APIRouter, HTTPException
from bson import ObjectId
from datetime import datetime, timezone
from db_connection.database import db
from schemas.job_schema import Job, JobUpdate

router = APIRouter()

def convert_id(doc):
    doc["_id"] = str(doc["_id"])
    return doc

@router.post("/jobs")
async def create_job(job: Job):
    result = await db.jobs.insert_one(job.model_dump())
    return {"status": "Job inserted", "id": str(result.inserted_id)}

@router.get("/jobs")
async def get_jobs():
    jobs = await db.jobs.find().sort("CreatedAt", -1).to_list(2000)
    return [convert_id(j) for j in jobs]

@router.get("/jobs/{job_id}")
async def get_job_by_id(job_id: str):
    job = await db.jobs.find_one({"_id": ObjectId(job_id)})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return convert_id(job)

@router.put("/jobs/{job_id}")
async def update_job(job_id: str, job: JobUpdate):
    update_data = {k: v for k, v in job.dict().items() if v is not None}
    update_data["UpdatedAt"] = datetime.now(timezone.utc)

    result = await db.jobs.update_one(
        {"_id": ObjectId(job_id)},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")

    updated_job = await db.jobs.find_one({"_id": ObjectId(job_id)})
    return convert_id(updated_job)
