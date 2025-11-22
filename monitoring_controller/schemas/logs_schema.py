from pydantic import BaseModel
from typing import Optional

class Log(BaseModel):
    logid: int
    ExecutionID: str
    Time: str
    Level: str
    message: str
    machineName: Optional[str]
    userName: Optional[str]
    processName: Optional[str]
    dateTime: str
