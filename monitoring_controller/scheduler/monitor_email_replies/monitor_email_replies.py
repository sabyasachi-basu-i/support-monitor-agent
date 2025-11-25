import asyncio
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timezone
import re
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

import logging

# -------------------------------------------------------------
#  LOGGING CONFIG
# -------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
def clean_subject(subject: str) -> str:
    """
    Remove Re:, Fwd:, FW:, etc. and return clean subject.
    """
    if not subject:
        return ""

    # Remove multiple "Re:", "Fwd:" recursively
    cleaned = re.sub(r"^(re:|fw:|fwd:)\s*", "", subject, flags=re.IGNORECASE)

    # Sometimes multiple layers: Re: Re: Fwd:
    while re.match(r"^(re:|fw:|fwd:)\s*", cleaned, flags=re.IGNORECASE):
        cleaned = re.sub(r"^(re:|fw:|fwd:)\s*", "", cleaned, flags=re.IGNORECASE)

    return cleaned.strip()
# -------------------------------------------------------------
#  IMAP EMAIL CHECKER (SYNC) WITH LOGS
# -------------------------------------------------------------
def check_email_replies_sync():
    """Synchronous IMAP email checker with logs."""
    logging.info("🔍 Connecting to IMAP server...")
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        logging.info("✅ Logged in successfully.")

        mail.select("inbox")
        logging.info("📂 Inbox selected.")

        status, data = mail.search(None, "UNSEEN")
        if status != "OK":
            logging.warning("⚠ No unread emails found")
            mail.logout()
            return []

        email_ids = data[0].split()
        logging.info(f"📬 Found {len(email_ids)} unread email(s).")

        results = []
        for eid in email_ids:
            status, msg_data = mail.fetch(eid, "(RFC822)")
            if status != "OK":
                logging.warning(f"⚠ Failed to fetch email ID {eid}")
                continue

            raw_msg = msg_data[0][1]
            msg = email.message_from_bytes(raw_msg)
            print(msg)
            thread_id = extract_header(msg, "Subject")
            if not thread_id:
                logging.warning("⚠ Email does not have threadId header.")
                continue
            
            body = get_email_body(msg)
            logging.info(f"✉️ Email with threadId={thread_id} fetched.")

            results.append({"threadId": thread_id[-4:], "body": body})

        mail.logout()
        logging.info("🔒 Logged out from IMAP server.")
        return results

    except Exception as e:
        logging.error(f"⚠ Error reading emails: {e}")
        return []


# -------------------------------------------------------------
#  ASYNC WRAPPER WITH LOGS
# -------------------------------------------------------------
async def process_email_replies():
    logging.info("⏳ Checking for new email replies...")
    replies = await asyncio.to_thread(check_email_replies_sync)

    if not replies:
        logging.info("📭 No new email replies to process.")
        return

    for reply in replies:
        thread_id = reply["threadId"]
        body = reply["body"]

        logging.info(f"🔎 Searching job for threadId={thread_id}...")
        job = await db.jobs.find_one({"threadId": thread_id})

        if not job:
            logging.warning(f"⚠ No job found for threadId={thread_id}")
            continue

        # Update job
        await db.jobs.update_one(
            {"_id": job["_id"]},
            {
                "$set": {
                    "status":"Processing",
                    "mailrecived_text": body,
                    "UpdatedAt": datetime.now(timezone.utc),
                }
            }
        )
        logging.info(f"📨 Updated job {job['_id']} using email reply.")


# -------------------------------------------------------------
#  SCHEDULER LOOP WITH LOGS
# -------------------------------------------------------------
async def monitor_email_replies(poll_interval=20):
    logging.info(f"⏱ Starting email monitor loop with interval {poll_interval}s")
    while True:
        try:
            await process_email_replies()
        except Exception as e:
            logging.error(f"⚠ Error in email monitoring loop: {e}")
        await asyncio.sleep(poll_interval)