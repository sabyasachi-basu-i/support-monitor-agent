# main.py
from fastapi import FastAPI
from agent.client.client import setup_agent
from agent.server.api.jobs import get_job_by_id, get_logs_by_execution_id,get_execution_by_executionid ,get_rca_by_id
app = FastAPI()

@app.post("/v1/event")
async def read_root(jobid: str):
    job = await get_job_by_id(jobid)
    logs = await get_logs_by_execution_id(job["ExecutionId"])
    execution  =await get_execution_by_executionid(job["ExecutionId"])
    # print(execution)
    message = f"""
    JobId : {job["_id"]}
    JOB: {job}
    LOGS: {logs}
    EXCECUTION: {execution}
    """
    print(message)
    response = await setup_agent(message,job["_id"])
    return response


if __name__ == "__main__":
    import uvicorn
    # NOTE: uvicorn --reload spawns subprocesses; be mindful if your MCP child process
    # is started automatically from agent.client — you may get double-spawn behavior.
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
# uvicorn main:app --reload --port 8000