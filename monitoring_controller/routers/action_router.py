from fastapi import APIRouter
from utils.restart_web_connection import restart_action_bot

router = APIRouter()

@router.post("/restart/{job_id}")
async def restart_bot(job_id: str):
    await restart_action_bot(job_id)
    return {"status": "success"}
