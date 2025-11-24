import requests
import json
import os  
import datetime
from dotenv import load_dotenv  
import pandas as pd
import re
from api.jobs import update_job,get_execution_by_executionid,get_logs_by_execution_id,get_job_by_id,get_rca_list
from groq import Groq
load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

excel_path = r"C:\Users\vishesh\Downloads\RCA_Knowledge_Base.xlsx"


async def predict_rca_with_llm(execution, logs, rca_list):
    """
    Predicts the best matching RCA record using LLM reasoning
    based on execution details and execution logs.
    """
    # Prepare clean prompt
    prompt = f"""
You are an expert RPA Root Cause Analyzer.

You will be given:
1. A list of historical RCA records
2. The current execution metadata
3. The execution logs (latest error)

Your job:
- Compare the execution + log details with the RCA records.
- Pick the *best matching* RCA by similarity (exception message, type, robot, process).
- Output ONLY a JSON object (no explanation) with:
    {{
       "RCA_ID": "<best RCA_ID>",
       "Match_Confidence": <0-1>,
       "Predicted_Root_Cause": "<text>",
       "Predicted_Solution": "<text>",
       "RCA_ACTION": "<Description of action to take Suggested_Action>",
       "Matched_RCA_Record": <full RCA record object>
    }}

### RCA LIST:
{rca_list}

### EXECUTION:
{execution}

### LATEST LOG ENTRY:
{logs}

Return JSON only.
    """

    completion = groq_client.chat.completions.create(
        model=os.getenv("MODEL"),     # or "llama3-70b-8192"
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )

    result_text = completion.choices[0].message.content.strip()

    # Parse JSON returned by model
    try:
        
        return json.loads(result_text)
    except Exception as e:
        raise ValueError(f"LLM returned invalid JSON: {e}, content: {result_text}")


async def get_rca_response(jobid: str):
    job = await get_job_by_id(jobid)
    if not job:
        raise ValueError("Job not found")

    logs = await get_logs_by_execution_id(job["ExecutionId"])
    if not logs:
        raise ValueError("No logs found")

    execution = await get_execution_by_executionid(job["ExecutionId"])
    if not execution:
        raise ValueError("Execution details not found")

    rca_list =await get_rca_list()

    llm_result = await predict_rca_with_llm(execution, logs, rca_list)
    
    new_job = {
        "RCA_ID": llm_result["RCA_ID"],
    }
    await update_job(jobid,new_job)
    
    return llm_result 













    
