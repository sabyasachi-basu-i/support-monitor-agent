from fastapi import APIRouter, HTTPException
from bson import ObjectId
from db_connection.database import db
from schemas.logs_schema import Log

router = APIRouter()

def convert_id(doc):
    doc["_id"] = str(doc["_id"])
    return doc

@router.post("/logs")
async def create_log(log: Log):
    result = await db.logs.insert_one(log.dict())
    return {"status": "Log inserted", "id": str(result.inserted_id)}

@router.get("/logs/{exicution_id}")
async def get_logs(exicution_id: str):
    logs = await db.logs.find({"ExecutionID": exicution_id}).to_list(2000)
    return [convert_id(l) for l in logs]

@router.get("/logs/{log_id}")
async def get_log_by_id(log_id: str):
    log = await db.logs.find_one({"_id": ObjectId(log_id)})
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return convert_id(log)



