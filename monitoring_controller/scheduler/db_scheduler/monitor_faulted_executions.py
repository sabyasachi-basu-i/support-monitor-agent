import logging
from datetime import datetime, timezone
import asyncio
import aiohttp
from db_connection.database import db
from schemas.job_schema import Job

# ---------------------------
# Configure Logging
# ---------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


async def process_faulted_executions():
    """
    Check for executions with status 'Faulted'.
    For each, check if a job already exists; if not, create it.
    Always send POST request with job_id.
    """
    logger.info("🔍 Checking for faulted executions...")

    try:
        async for exec_doc in db.executions.find({"State": "Faulted"}):
            exec_id = exec_doc.get("ExecutionId")
            logger.info(f"➡ Processing Faulted ExecutionId: {exec_id}")

            # Check if job already exists for this ExecutionId
            job_doc = await db.jobs.find_one({"ExecutionId": exec_id})
            isNew = False

            if job_doc:
                job_id = job_doc["_id"]
                logger.info(f"🔹 Existing job found | ExecutionId={exec_id}, JobId={job_id}")
            else:
                # Create new job
                job_doc = {
                        "ExecutionId":exec_id,
                        "JobType":"RetryFaulted",
                        "status":"Not Started",
                        "is_mailsent":False,
                        "mailrecived_text": "",
                        "mailsent_text" : ""
                }
                isNew=True

            if job_doc["status"] not in ["Completed", "Started"]:
                if isNew:
                    job_doc["status"] = "Started"
                    job_data = Job(**job_doc)  
                    result = await db.jobs.insert_one(job_data.model_dump())
                    job_id = result.inserted_id
                    print(f"✅ Created new job for ExecutionId {exec_id}, JobId: {job_id}")
                    
                if job_doc["mailrecived_text"] or isNew or not job_doc["RCA_ID"] or not job_doc["is_mailsent"] : 
                    # await send_job_api(job_id)
                    asyncio.create_task(send_job_api(job_id))
            else :
                 print(f"mailrecived_text not found !!!!!!!!!!!!!!!!!!!!!")

            if should_send:
                logger.info(f"📨 Triggering API call for JobId={job_id}...")
                asyncio.create_task(send_job_api(job_id))
            else:
                logger.info(f"⛔ API not triggered for JobId={job_id} (conditions not met)")

    except Exception as e:
        logger.error(f"⚠ Error processing faulted executions: {e}", exc_info=True)



async def send_job_api(job_id):
    api_url = f"http://127.0.0.1:8000/v1/event?jobid={job_id}"

    logger.info(f"🚀 Sending POST request for JobId={job_id}...")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(api_url) as response:
                if response.status in (200, 201):
                    logger.info(f"✅ Successfully sent job {job_id} to API (status={response.status})")
                else:
                    logger.warning(f"❌ Failed to send job {job_id} (status={response.status})")
        except Exception as e:
            logger.error(f"⚠ Error sending job {job_id} to API: {e}", exc_info=True)



async def monitor_faulted_executions(poll_interval=10):
    logger.info(f"🕒 Starting monitoring loop (poll interval={poll_interval}s)...")
    while True:
        await process_faulted_executions()
        logger.info("⏳ Waiting for next poll...")
        await asyncio.sleep(poll_interval)
