# master_mcp_server.py
from mcp.server.fastmcp import FastMCP
import requests
import json
import asyncio
import smtplib
from tools.rca import get_rca_response
from api.jobs import update_job,action_job,get_job_by_id,send_audit_log,get_execution_by_executionid,update_rca
mcp = FastMCP("server")

# ---- SOP/RCA Lookup Tool ----
print("Server starting...")




@mcp.tool()
async def get_rca(jobid:str) -> dict:
    """
    Query knowledge base for exception resolution confidence.
    """
    rca_response= await get_rca_response(jobid)
  
    return rca_response
    

# ---- Action Executor Tool ----
@mcp.tool()
async def send_mail(jobid: str, subject: str,body:str) -> dict:
    """
    Send the mail to developer with exception message and get  the approval response.
    """

    url = f"http://localhost:8001/send_email?subject={subject}&body={body}&job_id={jobid}&email_type={'Developer'}"
    response = requests.post(url)
    new_job = {
        "status":"Waiting for Reply"
    }
    # Check response
    if response.status_code == 200:
        print("Email triggered successfully!")
        print(response.json())
        await update_job(jobid,new_job)
        
    else:
        print("Failed to trigger endpoint:", response.status_code, response.text)
        
@mcp.tool()
async def send_mail_to_bussiness_team_and_devloper(
    jobid: str,
    businessSubject: str,
    businessBody: str,
    developerSubject: str,
    developerBody: str
) -> dict:
    """
    Sends notification emails to both the business team and the developer team
    based on the RCA (Root Cause Analysis) response.

    Parameters:
    ----------
    jobid : str
        Unique identifier of the job for which notifications are being sent.

    businessSubject : str
        Subject line of the email that will be sent to the business team.

    businessBody : str
        Body content of the email sent to the business team.

    developerSubject : str
        Subject line of the email sent to the developer.

    developerBody : str
        Body content of the email sent to the developer.
    """

    # Send email to Business Team
    urlBusiness = (
        f"http://localhost:8001/send_email?"
        f"subject={businessSubject}&body={businessBody}&job_id={jobid}&email_type={"Business"}"
    )
    responseBusiness = requests.post(urlBusiness)

    # Send email to Developer for confirmation
    urlDeveloper = (
        f"http://localhost:8001/send_email?"
        f"subject={developerSubject}&body={developerBody}&job_id={jobid}&email_type={"Developer"}"
    )
    responseDeveloper = requests.post(urlDeveloper)

    # Update job status
    new_job = {
        "status": "Completed"
    }
    await update_job(jobid, new_job)

    return {"message": "Emails sent successfully and job updated."}
# ---- Audit Logging Tool ----
@mcp.tool()
async def perform_action(jobid:str,ExecutionId:str,mailrecived_text:str,event: str, data: dict) -> dict:
    """
    Log event for traceability.
    """
    
    print(f"[AUDIT] {event} :: {data}")
    new_job = {
        "status":"Completed"
    }
    if mailrecived_text:
        await action_job(jobid)
        await update_job(jobid,new_job)
    return {"status": "logged"}

@mcp.tool()
async def post_audit_log(jobType: str, jobId: str, actor: str, message: str) -> dict:
    """
    MCP Tool: create an audit log using the shared send_audit_log method.
    """
    return await send_audit_log(jobType, jobId, actor, message)

@mcp.tool()
async def add_new_rca(
    RCA_ID: str,
    Process_Name: str,
    Robot: str,
    State: str,
    Timestamp_First_Seen: str,
    Created_By: str,
    Exception_Type: str,
    Exception_Message: str,
    Exception_Signature: str,
    Root_Cause: str,
    Business_Impact: str,
    Solution_Type: str,
    Suggested_Action: str,
    Action_Parameters: str,
    SOP_Reference: str,
    Total_Occurrences: int,
    Auto_Action_Success: int,
    Auto_Action_Failure: int,
    Human_Approved: int,
    Human_Rejected: int,
    Base_Confidence: float
) -> dict:
    """
    Store a new RCA record into the database.

    This allows adding new RCA entries manually via MCP.
    """

    rca_data = {
        "RCA_ID": RCA_ID,
        "Process_Name": Process_Name,
        "Robot": Robot,
        "State": State,
        "Timestamp_First_Seen": Timestamp_First_Seen,
        "Created_By": Created_By,
        "Exception_Type": Exception_Type,
        "Exception_Message": Exception_Message,
        "Exception_Signature": Exception_Signature,
        "Root_Cause": Root_Cause,
        "Business_Impact": Business_Impact,
        "Solution_Type": Solution_Type,
        "Suggested_Action": Suggested_Action,
        "Action_Parameters": Action_Parameters,
        "SOP_Reference": SOP_Reference,
        "Total_Occurrences": Total_Occurrences,
        "Auto_Action_Success": Auto_Action_Success,
        "Auto_Action_Failure": Auto_Action_Failure,
        "Human_Approved": Human_Approved,
        "Human_Rejected": Human_Rejected,
        "Base_Confidence": Base_Confidence
    }

    # POST to your existing RCA persistence API
    url = "http://localhost:8001/add_rca"
    response = requests.post(url, json=rca_data)

    if response.status_code == 200:
        return {
            "status": "success",
            "message": "RCA added successfully",
            "data": response.json()
        }

    return {
        "status": "error",
        "message": f"Failed to add RCA: {response.text}"
    }
# @mcp.tool()
# async def update_Rca_Base_Confidence(RCA_ID:str,Base_Confidence:str):
#     update_data={
#         "Base_Confidence":Base_Confidence
#     }
#     await update_rca(RCA_ID,update_data)
#     return "Successfully rca updated"

if __name__ == "__main__":  
    mcp.run()
