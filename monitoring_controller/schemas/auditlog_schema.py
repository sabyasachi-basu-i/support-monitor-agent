from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class AuditLog(BaseModel):
    jobType: str
    jobId: str
    actor: str
    timestamp: datetime = datetime.now(timezone.utc)
    message: Optional[str]
