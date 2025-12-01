from pydantic import BaseModel
from typing import Optional

class RCA(BaseModel):
    RCA_ID: str
    Process_Name: str
    Robot: str
    State: str
    Timestamp_First_Seen: str
    Created_By: Optional[str]
    Exception_Type: Optional[str]
    Exception_Message: Optional[str]
    Exception_Signature: Optional[str]
    Root_Cause: Optional[str]
    Business_Impact: Optional[str]
    Solution_Type: Optional[str]
    Suggested_Action: Optional[str]
    Action_Parameters: Optional[str]
    # SOP_Reference: Optional[str]
    Total_Occurrences: Optional[int]
    Auto_Action_Success: Optional[int]
    Auto_Action_Failure: Optional[int]
    Human_Approved: Optional[int]
    Human_Rejected: Optional[int]
    Base_Confidence: Optional[float]



class RCAUpdate(BaseModel):
    RCA_ID: Optional[str]= None
    Process_Name: Optional[str]= None
    Robot: Optional[str]= None
    State: Optional[str]= None
    Timestamp_First_Seen: Optional[str]= None
    Created_By: Optional[str]=  None
    Exception_Type: Optional[str]= None
    Exception_Message: Optional[str]= None
    Exception_Signature: Optional[str] = None
    Root_Cause: Optional[str]= None
    Business_Impact: Optional[str]= None
    Solution_Type: Optional[str]= None
    Suggested_Action: Optional[str]= None
    Action_Parameters: Optional[str]= None
    Total_Occurrences: Optional[int]= None
    Auto_Action_Success: Optional[int]= None
    Auto_Action_Failure: Optional[int]= None
    Human_Approved: Optional[int]= None
    Human_Rejected: Optional[int]= None
    Base_Confidence: Optional[float] = None