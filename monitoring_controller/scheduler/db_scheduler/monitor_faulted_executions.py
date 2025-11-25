from datetime import datetime
import asyncio
import aiohttp
from db_connection.database import db
from schemas.job_schema import Job

async def process_faulted_executions():
    """
    Check for executions with status 'Faulted'.
    For each, check if a job already exists; if not, create it.
    Always send POST request with job_id.
    """
    try:
        async for exec_doc in db.executions.find({"State": "Faulted"}):
            exec_id = exec_doc.get("ExecutionId")

            # Check if job already exists for this ExecutionId
            job_doc = await db.jobs.find_one({"ExecutionId": exec_id})
            isNew = False
            if job_doc:
                job_id = job_doc["_id"]
                print(f"🔹 Job already exists for ExecutionId {exec_id}, JobId: {job_id}")
            else:
                # Create new job
                job_data = Job(
                        ExecutionId=exec_id,
                        JobType="RetryFaulted",
                        status="Started",
                        is_mailsent=False,
                        mailrecived_text= "",
                        mailsent_text = ""
                    )
                result = await db.jobs.insert_one(job_data.model_dump())
                job_id = result.inserted_id
                print(f"✅ Created new job for ExecutionId {exec_id}, JobId: {job_id}")
                isNew=True

            if job_doc["status"] != "Completed":
                if job_doc["mailrecived_text"] or isNew or not job_doc["RCA_ID"] or not job_doc["is_mailsent"] : 
                    await send_job_api(job_id)
            else :
                 print(f"mailrecived_text not found !!!!!!!!!!!!!!!!!!!!!")

             

    except Exception as e:
        print("⚠ Error processing faulted executions:", e)


# -------------------------------
# Send job info to external API
# -------------------------------
async def send_job_api(job_id):
    api_url = f"http://127.0.0.1:8000/v1/event?jobid={job_id}"
    # payload = {"jobid": str(job_id)}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(api_url) as response:
                if response.status in (200, 201):
                    print(f"✅ Successfully sent job {job_id} to API")
                else:
                    print(f"❌ Failed to send job {job_id}, status: {response.status}")
        except Exception as e:
            print("⚠ Error sending job to API:", e)

async def monitor_faulted_executions(poll_interval=10):
    while True:
        await process_faulted_executions()
        await asyncio.sleep(poll_interval)
