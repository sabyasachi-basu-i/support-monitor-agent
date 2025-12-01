from fastapi import APIRouter, HTTPException
from bson import ObjectId
from db_connection.database import db
from schemas.execution_schema import Execution

router = APIRouter()

def convert_id(doc):
    doc["_id"] = str(doc["_id"])
    return doc

@router.post("/executions")
async def create_execution(execution: Execution):
    result = await db.executions.insert_one(execution.dict())
    return {"status": "Execution inserted", "id": str(result.inserted_id)}

@router.get("/executions")
async def get_executions():
    executions = await db.executions.find().to_list(2000)
    return [convert_id(e) for e in executions]

@router.get("/executions/{execution_id}")
async def get_execution_by_id(execution_id: str):
    execution = await db.executions.find_one({"ExecutionId": execution_id})
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return convert_id(execution)
