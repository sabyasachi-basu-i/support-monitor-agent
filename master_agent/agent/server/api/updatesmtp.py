import smtplib
import imaplib
import email
import time
from datetime import datetime, timezone
from typing import Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorClient

# ------------------------
# MongoDB Setup
# ------------------------
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "automation_logs_db"

client = AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]
job_collection = db["jobs"]

# ------------------------
# Email Credentials
# ------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
IMAP_SERVER = "imap.gmail.com"

SENDER_EMAIL = "your_email@gmail.com"
SENDER_PASSWORD = "your_app_password"  # Use environment variable in production
RECEIVER_EMAIL = "receiver_email@gmail.com"

# ------------------------
# Send Email Function
# ------------------------
def send_email(execution_id: str, subject_prefix: str = "RCA Bot Alert") -> str:
    subject = f"{subject_prefix} | ExecutionId: {execution_id}"
    body = f"""Hi,

ExecutionId: {execution_id}
I got this RCA from the bot: it needs a restart.
If you want to allow the restart, reply YES; otherwise reply NO.
"""
    message = f"Subject: {subject}\n\n{body}"

    # Send email
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, message)

    # Update MongoDB
    job_collection.update_one(
        {"ExecutionId": execution_id},
        {
            "$set": {
                "is_mailsent": True,
                "mailsent_text": body,
                "UpdatedAt": datetime.now(timezone.utc)
            }
        }
    )
    print(f"Email sent successfully for ExecutionId: {execution_id}")
    return body

# ------------------------
# Check Reply Function
# ------------------------
def check_reply() -> Tuple[Optional[str], Optional[str]]:
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(SENDER_EMAIL, SENDER_PASSWORD)
    mail.select("inbox")

    result, data = mail.search(None, f'(FROM "{RECEIVER_EMAIL}")')
    mail_ids = data[0].split()

    if not mail_ids:
        return None, None

    # Get the latest email
    latest_email_id = mail_ids[-1]
    result, msg_data = mail.fetch(latest_email_id, "(RFC822)")
    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    # Extract ExecutionId from subject
    exec_id_in_mail = None
    subject = msg["subject"]
    if "ExecutionId:" in subject:
        exec_id_in_mail = subject.split("ExecutionId:")[1].strip()

    # Extract body
    mail_body = None
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                mail_body = part.get_payload(decode=True).decode().strip()
    else:
        mail_body = msg.get_payload(decode=True).decode().strip()

    return exec_id_in_mail, mail_body

# ------------------------
# Main Function: Send Email and Wait for Reply
# ------------------------
def send_email_and_wait_reply(execution_id: str, poll_interval: int = 10):
    send_email(execution_id)

    print("Waiting for reply...")
    while True:
        exec_id, reply_text = check_reply()
        if reply_text and exec_id:
            print(f"Reply received for ExecutionId {exec_id}: {reply_text}")

            # Update MongoDB
            job_collection.update_one(
                {"ExecutionId": exec_id},
                {
                    "$set": {
                        "mailrecived_text": reply_text,
                        "UpdatedAt": datetime.now(timezone.utc)
                    }
                }
            )

            # Handle YES/NO logic
            if reply_text.upper() == "YES":
                print("✅ Call run action")
            elif reply_text.upper() == "NO":
                print("❌ Log for developer action")
            else:
                print("⚠️ Unexpected reply text")
            break

        time.sleep(poll_interval)

# ------------------------
# Example usage
# ------------------------
if __name__ == "__main__":
    execution_id = "3NfeEctP"
    send_email_and_wait_reply(execution_id)
