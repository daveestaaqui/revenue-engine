#!/usr/bin/env python3
"""
Direct IMAP draft uploader for the 10 fresh attorney targets.
Connects securely to sandwichfitness@gmail.com and uploads all 10 drafts to [Gmail]/Drafts.
"""
import imaplib
import os
import time
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

GMAIL_USER = os.getenv("GMAIL_USER", "sandwichfitness@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")
FROM_NAME = "Elena Brooks"
FROM_EMAIL = "elena.brooks@surplusdocket.com"
REPLY_TO = "elena.brooks@surplusdocket.com"

# Import targets from generate_gmail_drafts_suite
from generate_gmail_drafts_suite import TARGETS

def upload_all_drafts():
    print(f"Connecting to imap.gmail.com as {GMAIL_USER}...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASS)
        print("✅ Logged into Gmail IMAP successfully!")
    except Exception as e:
        print(f"❌ IMAP connection failed: {e}")
        return False

    drafts_box = "[Gmail]/Drafts"
    status, count = mail.select(drafts_box)
    if status != "OK":
        drafts_box = "Drafts"
        mail.select(drafts_box)

    print(f"Selected mailbox: '{drafts_box}'. Uploading {len(TARGETS)} fresh drafts...\n")
    uploaded = 0
    for idx, t in enumerate(TARGETS, 1):
        msg = MIMEText(t["body"], "plain", "utf-8")
        msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg["To"] = f"{t['name']} <{t['email']}>"
        msg["Reply-To"] = REPLY_TO
        msg["Subject"] = t["subject"]
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="surplusdocket.com")

        # Draft flag
        raw = msg.as_bytes()
        status, _ = mail.append(drafts_box, "\\Draft", imaplib.Time2Internaldate(time.time()), raw)
        if status == "OK":
            uploaded += 1
            print(f"  [{idx}/10] ✓ Created draft for {t['name']} ({t['email']})")
        else:
            print(f"  [{idx}/10] ❌ Failed to append draft for {t['email']}")

    mail.logout()
    print(f"\n🎉 Successfully uploaded {uploaded}/{len(TARGETS)} drafts directly into your Gmail Drafts folder!")
    return True

if __name__ == "__main__":
    upload_all_drafts()
