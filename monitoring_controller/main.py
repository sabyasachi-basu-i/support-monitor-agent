from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

# Schedulers
from db_connection.database import ensure_collections
from scheduler.execution_scheduler.ws_client import run_ws_client
from scheduler.db_scheduler.monitor_faulted_executions import monitor_faulted_executions
from scheduler.monitor_email_replies.monitor_email_replies import monitor_email_replies
from scheduler.execution_scheduler.utils.apis import get_token, negotiate_connection

# Routers
from routers.jobs_router import router as jobs_router
from routers.executions_router import router as executions_router
from routers.logs_router import router as logs_router
from routers.rca_router import router as rca_router
from routers.auditlogs_router import router as auditlogs_router
from routers.email_router import router as email_router
from routers.action_router import router as action_router

app = FastAPI(title="Automation Logging Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(jobs_router)
app.include_router(executions_router)
app.include_router(logs_router)
app.include_router(rca_router)
app.include_router(auditlogs_router)
app.include_router(email_router)
app.include_router(action_router)

@app.on_event("startup")
async def startup_event():
    access_token = get_token()
    connection_token = negotiate_connection(access_token)

    await ensure_collections()

    asyncio.create_task(run_ws_client(access_token, connection_token))
    asyncio.create_task(monitor_faulted_executions())
    asyncio.create_task(monitor_email_replies())

# uvicorn main:app --reload --port 8001
