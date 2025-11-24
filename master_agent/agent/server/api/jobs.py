
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
    
    

async def update_job(job_id: str, update_data: dict) -> dict:
    """
    PUT request to update an existing job
    """
    url = f"http://localhost:8001/jobs/{job_id}"
    response = requests.put(url, json=update_data)
    response.raise_for_status()
    return response.json()

async def action_job() -> dict:
    """
    PUT request to update an existing job
    """
    url = f"http://localhost:8001/restart"
    response = requests.post(url)
    response.raise_for_status()
    return response.json()
    
def send_email(recipient: str, subject: str, body: str) -> bool:
    # Simulate sending email
    print(f"Sending email to {recipient} with subject '{subject}'")
    print("Email body:")
    print(body)
    return True

def get_rca_by_id(rca_id: str) -> dict:
    response = requests.get(f"http://localhost:8001/rca/{rca_id}")
    response.raise_for_status()
    return response.json()

async def get_rca_list() -> list[dict]:
    response = requests.get(f"http://localhost:8001/rca")
    response.raise_for_status()
    return response.json()
    
    # return {
    #     "rca_id": rca_id,
    #     "analysis": "Root cause analysis details for the given RCA ID.",
    #     "recommended_actions": [
    #         "Action 1",
    #         "Action 2",
    #         "Action 3"
    #     ]
    # }
async def get_execution_by_executionid(execution_id:str):
    url=f"http://localhost:8001/executions/{execution_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


async def create_audit_logs(audits: list[dict]):
    """
    Sends audit logs to FastAPI /auditlogs endpoint.
    """
    url = "http://localhost:8001/auditlogs"

    # POST JSON body format expected by your FastAPI endpoint:
    # {
    #     "audits": [ {...}, {...} ]
    # }
    payload = {"audits": audits}

    print("Sending audit logs:", payload)

    response = requests.post(url, json=payload)
    response.raise_for_status()

    return response.json()


async def send_audit_log(jobType: str, jobId: str, actor: str, message: str) -> dict:
    """
    Sends a single audit log entry to FastAPI /auditlog endpoint.
    """
    payload = {
        "jobType": jobType,
        "jobId": jobId,
        "actor": actor,
        "message": message
    }

    try:
        response = requests.post(
            "http://127.0.0.1:8001/auditlog",
            json=payload
        )
        response.raise_for_status()
        return {"status": "success", "payload": payload, "response": response.json()}

    except Exception as e:
        return {"status": "error", "error": str(e), "payload": payload}