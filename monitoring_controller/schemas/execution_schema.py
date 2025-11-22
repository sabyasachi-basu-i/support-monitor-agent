from pydantic import BaseModel
from typing import Optional

class Execution(BaseModel):
    Id: int
    ExecutionId: str
    Process: str
    Robot: str
    EntryFile: Optional[str]
    Arguments: Optional[str]
    ToBeAborted: Optional[bool]
    Environment: Optional[str]
    State: Optional[str]
    StartTime: Optional[str]
    EndTime: Optional[str]
    Source: Optional[str]
    Tenant: Optional[str]
    TenantId: Optional[int]
