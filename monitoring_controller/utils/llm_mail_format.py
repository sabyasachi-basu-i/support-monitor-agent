# utils/llm_utils.py
from groq import Groq
import json,os
import requests
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL =os.getenv("GROQ_API_URL")
async def generate_email_content( payload: dict) -> dict:
    """
    Generates dynamic subject and body for email using LLM based on emailtype.
    emailtype: "action_request" | "early_acceptance" | others
    payload: dict containing JobId, Message, ErrorType, etc.
    Returns: {"subject": str, "body": str}
    """
    emailtype = payload.get("action_request")
    job_id = payload.get("JobId", "N/A")
    error_type = payload.get("ErrorType", "N/A")
    message = payload.get("Message", "")

    # Modify prompt based on email type
    if emailtype == "action_request":
        prompt = f"""
        You are an assistant drafting professional emails.
        This is an **action request** email where the bot requires permission to take action.

        JobId: {job_id}
        ErrorType: {error_type}
        Message: {message}

        Draft a polite email requesting permission. Return JSON:
        {{
          "subject": "short subject line",
          "body": "full email body"
        }}
        """
    elif emailtype == "early_acceptance":
        prompt = f"""
        You are an assistant drafting professional emails.
        Permission has already been granted for the action.

        JobId: {job_id}
        ErrorType: {error_type}
        Message: {message}

        Draft a polite confirmation email stating that action is being taken. Return JSON:
        {{
          "subject": "short subject line",
          "body": "full email body"
        }}
        """
    else:
        # Default prompt for other email types
        prompt = f"""
        Draft a professional email for JobId {job_id} with ErrorType {error_type}.
        Message: {message}
        Return JSON:
        {{
          "subject": "short subject line",
          "body": "full email body"
        }}
        """

    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    completion = groq_client.chat.completions.create(
          model=os.getenv("MODEL"),     # or "llama3-70b-8192"
          messages=[{"role": "user", "content": prompt}],
          temperature=0.1,
      )

    result_text = completion.choices[0].message.content.strip()


    

    # Parse JSON returned by model
    try:
        
        email_json = json.loads(result_text)
        return {"subject": email_json["subject"], "body": email_json["body"]}
    except Exception as e:
        print("Failed to parse LLM output, returning fallback")
        return {"subject": "No subject", "body": message}
    
    