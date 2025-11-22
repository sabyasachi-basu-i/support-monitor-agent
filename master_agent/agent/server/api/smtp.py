import smtplib
import imaplib
import email
import time

# ------------------------
# Email credentials
# ------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
IMAP_SERVER = "imap.gmail.com"

SENDER_EMAIL = "rameshbomburi123@gmail.com"
SENDER_PASSWORD = "lhsy vfvv fsae abpr"  # 16-char App password

RECEIVER_EMAIL = "rameshbomburi121@gmail.com"  # can be same as sender

# ------------------------
# Step 1: Send email
# ------------------------
subject = "RCA Bot Alert"
body = """Hi Ramesh,

I got this RCA from the bot: it needs a restart.
If you want to allow the restart, reply YES; otherwise reply NO.
"""

message = f"Subject: {subject}\n\n{body}"

with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, message)
    print("Email sent successfully!")

# ------------------------
# Step 2: Wait for reply
# ------------------------
def check_reply():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(SENDER_EMAIL, SENDER_PASSWORD)
    mail.select("inbox")

    result, data = mail.search(None, f'(FROM "{RECEIVER_EMAIL}")')
    mail_ids = data[0].split()

    if not mail_ids:
        return None

    # Get the latest email
    latest_email_id = mail_ids[-1]
    result, msg_data = mail.fetch(latest_email_id, "(RFC822)")
    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode().strip()
    else:
        return msg.get_payload(decode=True).decode().strip()


# ------------------------
# Step 3: Poll for reply
# ------------------------
print("Waiting for reply...")
while True:
    reply = check_reply()
    if reply:
        print("Reply received:", reply)
        if reply.upper() == "YES":
            print("✅ Call run action")
        elif reply.upper() == "NO":
            print("❌ Log for developer action")
        break
    time.sleep(10)  # wait 10 seconds before checking again
