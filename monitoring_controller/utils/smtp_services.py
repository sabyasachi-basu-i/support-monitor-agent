from dotenv import load_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid
from db_connection.database import db
import logging
from bson import ObjectId
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
IMAP_SERVER = os.getenv("IMAP_SERVER")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
DEVELOPER_EMAIL = os.getenv("DEVELOPER_EMAIL")
BUSINESS_EMAIL = os.getenv("BUSINESS_EMAIL")

async def send_email_SMTP(subject: str, body: str, job_id: str,email_type:str) -> bool:
    logging.info(f"Preparing to send email to {DEVELOPER_EMAIL} with subject '{subject}'")
    short_id = uuid.uuid4().hex[:4]  
    subject = f"{subject} {short_id}"
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    if email_type =="Business":
        msg['To'] = BUSINESS_EMAIL    
    else:
        msg['To'] = DEVELOPER_EMAIL    
        

    msg['Subject'] = subject
   

    msg.attach(MIMEText(body, 'plain'))


    # Update MongoDB
    update_fields = {
        "is_mailsent": True,
        "mailsent_text": body,
        "threadId": short_id
    }

    try:
        logging.info(f"Updating MongoDB job {job_id} before sending email")
        result = await db.jobs.update_one({"_id": ObjectId(job_id)}, {"$set": update_fields})
        logging.info(f"MongoDB update result: {result.raw_result}")
    except Exception as e:
        logging.error(f"Failed to update MongoDB: {e}")

    try:
        logging.info(f"Connecting to SMTP server {SMTP_SERVER}:{SMTP_PORT}")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.set_debuglevel(1)  # Enable detailed SMTP debug output
            logging.info("Starting TLS")
            server.starttls()
            logging.info("Logging in to SMTP server")
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            logging.info("Sending email message")
            server.send_message(msg)
        logging.info("Email sent successfully")
        return True
    except smtplib.SMTPAuthenticationError as auth_err:
        logging.error(f"SMTP Authentication failed: {auth_err}")
    except smtplib.SMTPException as smtp_err:
        logging.error(f"SMTP error occurred: {smtp_err}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    return False
