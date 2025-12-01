from fastapi import APIRouter, HTTPException
from bson import ObjectId
from datetime import datetime, timezone
from db_connection.database import db
from schemas.rca_schema import RCA, RCAUpdate

router = APIRouter()

def convert_id(doc):
    doc["_id"] = str(doc["_id"])
    return doc

@router.post("/rca")
async def create_rca(rca: RCA):
    result = await db.rca.insert_one(rca.dict())
    return {"status": "RCA inserted", "id": str(result.inserted_id)}

@router.get("/rca")
async def get_rcas():
    rcas = await db.rca.find().to_list(2000)
    return [convert_id(r) for r in rcas]

@router.get("/rca/{rca_id}")
async def get_rca_by_id(rca_id: str):
    rca = await db.rca.find_one({"_id": ObjectId(rca_id)})
    if not rca:
        raise HTTPException(status_code=404, detail="RCA not found")
    return convert_id(rca)

@router.put("/update_rca/{rca_id}")
async def update_rca(rca_id: str, rca_update: RCAUpdate):
    update_data = {k: v for k, v in rca_update.dict().items() if v is not None}
    update_data["UpdatedAt"] = datetime.now(timezone.utc)

    result = await db.rca.update_one({"RCA_ID": rca_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="RCA not found")

    updated_rca = await db.rca.find_one({"RCA_ID": rca_id})
    return convert_id(updated_rca)

@router.post("/add_rca")
async def add_new_rca_endpoint(rca: RCA):
    try:
        result = await db.rca.insert_one(rca.model_dump())
        return {"status": "success", "message": "RCA added successfully", "id": str(result.inserted_id)}
    except Exception as e:
        return {"status": "error", "message": f"Failed to add RCA: {str(e)}"}
