import asyncio
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timezone

from db_connection.database import db


# -------------------------------------------------------------
#  CONFIG
# -------------------------------------------------------------
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
IMAP_USER = "rameshbomburi123@gmail.com"
IMAP_PASSWORD = "lhsy vfvv fsae abpr"


# -------------------------------------------------------------
#  HELPERS
# -------------------------------------------------------------
def extract_header(msg, key: str):
    """Decode and return a specific header like 'threadId'."""
    val = msg.get(key)
    if isinstance(val, str):
        return val
    if val:
        decoded, _ = decode_header(val)[0]
        return decoded.decode() if isinstance(decoded, bytes) else decoded
    return None


def get_email_body(msg):
    """Extract the readable email body (text/plain)."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(errors="ignore")
    return msg.get_payload(decode=True).decode(errors="ignore")


# -------------------------------------------------------------
#  IMAP EMAIL CHECKER (SYNC)
# -------------------------------------------------------------
def check_email_replies_sync():
    """
    Synchronous IMAP email checker.
    This function will be wrapped into async using run_in_executor.
    """

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(IMAP_USER, IMAP_PASSWORD)

        mail.select("inbox")

        # Search unread emails
        status, data = mail.search(None, "UNSEEN")
        if status != "OK":
            print("⚠ No unread emails found")
            mail.logout()
            return []

        email_ids = data[0].split()
        results = []

        for eid in email_ids:
            status, msg_data = mail.fetch(eid, "(RFC822)")
            if status != "OK":
                continue

            raw_msg = msg_data[0][1]
            msg = email.message_from_bytes(raw_msg)

            thread_id = extract_header(msg, "threadId")
            if not thread_id:
                print("⚠ Email does not have threadId header.")
                continue

            body = get_email_body(msg)

            results.append({
                "threadId": thread_id,
                "body": body
            })

        mail.logout()
        return results

    except Exception as e:
        print("⚠ Error reading emails:", e)
        return []


# -------------------------------------------------------------
#  ASYNC WRAPPER
# -------------------------------------------------------------
async def process_email_replies():
    """
    Async wrapper that runs the synchronous IMAP fetcher without blocking.
    """

    # Run sync function in separate thread
    replies = await asyncio.to_thread(check_email_replies_sync)

    for reply in replies:
        thread_id = reply["threadId"]
        body = reply["body"]

        # Find job based on threadId
        job = await db.jobs.find_one({"threadId": thread_id})

        if not job:
            print(f"⚠ No job found for threadId={thread_id}")
            continue

        # Update job
        await db.jobs.update_one(
            {"_id": job["_id"]},
            {
                "$set": {
                    "mailrecived_text": body,
                    "status": "EmailReceived",
                    "UpdatedAt": datetime.now(timezone.utc),
                }
            }
        )

        print(f"📨 Updated job {job['_id']} using email reply.")


# -------------------------------------------------------------
#  SCHEDULER LOOP
# -------------------------------------------------------------
async def monitor_email_replies(poll_interval=20):
    """
    Background scheduler that checks email replies every X seconds.
    """
    while True:
        await process_email_replies()
        await asyncio.sleep(poll_interval)
