# master_mcp_server.py
from mcp.server.fastmcp import FastMCP
import requests
import json
import asyncio
import smtplib
from tools.rca import get_rca_response
from api.jobs import update_job,action_job,create_audit_logs,send_audit_log
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

    url = f"http://localhost:8001/send_email?subject={subject}&body={body}&job_id={jobid}"
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
        

# ---- Audit Logging Tool ----
@mcp.tool()
async def perform_action(jobid:str,mailrecived_text:str,event: str, data: dict) -> dict:
    """
    Log event for traceability.
    """
    print(f"[AUDIT] {event} :: {data}")
    new_job = {
        "status":"Completed"
    }
    if mailrecived_text:
        await action_job()
        await update_job(jobid,new_job)
    return {"status": "logged"}

@mcp.tool()
async def post_audit_log(jobType: str, jobId: str, actor: str, message: str) -> dict:
    """
    MCP Tool: create an audit log using the shared send_audit_log method.
    """
    return await send_audit_log(jobType, jobId, actor, message)


if __name__ == "__main__":  
    mcp.run()
