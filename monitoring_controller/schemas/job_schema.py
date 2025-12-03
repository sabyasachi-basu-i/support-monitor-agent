from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class Job(BaseModel):
    ExecutionId: Optional[str] = None
    RCA_ID: Optional[str] = None
    threadId: Optional[str] = None
    is_mailsent: bool = False
    is_running: bool = False
    mailsent_text: Optional[str] = None
    mailrecived_text: Optional[str] = None
    status: Optional[str] = None
    CreatedAt: datetime = datetime.now(timezone.utc)
    UpdatedAt: Optional[datetime] = None
    
    
    
class JobUpdate(BaseModel):
    ExecutionId: Optional[str] = None
    RCA_ID: Optional[str] = None
    threadId: Optional[str] = None
    is_mailsent: Optional[bool] = None
    is_running: Optional[bool] = None
    mailsent_text: Optional[str] = None
    mailrecived_text: Optional[str] = None
    status: Optional[str] = None
    
