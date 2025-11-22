
import requests
from typing import Any,List


async def get_job_by_id(jobid: str) -> dict:
    print(jobid)
    url = f"http://127.0.0.1:8001/jobs/{jobid}"
    print(url)
    response = requests.get(url)
    response.raise_for_status()
    return response.json()
    
    # return {
    #     "job_id": job_id,
    #     "execution_id":"Process67890",
    #     "status": "pending",
    #     "rca_id":"RCA12345",
    #     "is_mail_sent":False,
    #     "recived_mail_content":"Sample email content related to the job."
    #  }

async def get_logs_by_execution_id(execution_id: str) -> dict:
    url=f"http://localhost:8001/logs/{execution_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()
    
    # return {
    #     "execution_id": execution_id,      
    #     "logid": 865257,
    #     "ExecutionID": "3NfeEctP",
    #     "Time": "11/18/2025 23:57:53:1740 -06:00:00",
    #     "Level": "Info",
    #     "message": "Process Faulted",
    #     "machineName": "DAL-CTX-VRPC003",
    #     "userName": "s-fdev3",
    #     "processName": "TestLogs",
    #     "dateTime": "2025-11-19T05:57:53.2010733"         
    # }
    
    
def update_job(job_id: str, update_data: dict) -> dict:
    # response = requests.put(f"http://localhost:8000/jobs/{job_id}", json=update_data)
    # response.raise_for_status()
    # return response.json()
    updated_job = {"job_id": job_id}
    updated_job.update(update_data)
    return updated_job

    
def send_email(recipient: str, subject: str, body: str) -> bool:
    # Simulate sending email
    print(f"Sending email to {recipient} with subject '{subject}'")
    print("Email body:")
    print(body)
    return True

def get_rca_by_id(rca_id: str) -> dict:
    # response = requests.get(f"http://localhost:8000/rca/{rca_id}")
    # response.raise_for_status()
    # return response.json()
    
    return {
        "rca_id": rca_id,
        "analysis": "Root cause analysis details for the given RCA ID.",
        "recommended_actions": [
            "Action 1",
            "Action 2",
            "Action 3"
        ]
    }
async def get_execution_by_executionid(execution_id:str):
    url=f"http://localhost:8001/executions/{execution_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


async def create_audit_logs(audits: list[dict] ):
    print(audits.__str__)
    url = "http://localhost:8001/auditlogs"  # your FastAPI endpoint
    response = requests.post(url, json={"audits":audits.__str__})
    response.raise_for_status()
    return response.json()