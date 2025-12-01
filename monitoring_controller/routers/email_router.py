from fastapi import APIRouter
from utils.smtp_services import send_email_SMTP

router = APIRouter()

@router.post("/send_email")
async def send_email(subject: str, body: str, job_id: str, email_type: str):
    success = await send_email_SMTP(subject, body, job_id, email_type)
    return {"success": success, "subject": subject, "body": body}
