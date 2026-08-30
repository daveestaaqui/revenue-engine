#!/usr/bin/env python3
"""
Surplus Docket — Continuous Background Daemon: Auto-Cleaner & Reply Drafter
==========================================================================
1. Instantly cleans sent drafts from BOTH Apple Mail (Mail.app) and Gmail IMAP
   so drafts disappear the moment you click Send.
2. Monitors INBOX for any prospect replies and automatically prepares customized
   response drafts with verified state benchmark records and Stripe link in your voice.
3. Runs continuously in a lightweight background process.
"""

import csv
import email
from email.header import decode_header
import imaplib
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid, parseaddr
from pathlib import Path

# Paths
BASE_DIR = Path("/Users/davidmahler/revenue-engine")
OUTREACH_DIR = BASE_DIR / "outreach"
FEED_CSV = BASE_DIR / "exports" / "Master_Surplus_Lead_Feed.csv"
LOG_FILE = OUTREACH_DIR / "auto_responder.log"

# Credentials & Identity
GMAIL_USER = os.getenv("GMAIL_USER", "sandwichfitness@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "nxgfaiebqpmobhkp")
FROM_NAME = "David Mahler"
SENDER_EMAIL = "david@surplusdocket.com"
REPLY_TO = "david@surplusdocket.com"
SITE_URL = "https://surplusdocket.com"
STRIPE_LINK = "https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X"

STATE_NAMES = {
    "FL": "Florida", "TX": "Texas", "GA": "Georgia",
    "NC": "North Carolina", "TN": "Tennessee", "CA": "California",
    "NY": "New York", "NJ": "New Jersey", "OH": "Ohio",
    "IL": "Illinois", "PA": "Pennsylvania", "MD": "Maryland",
    "AZ": "Arizona", "WA": "Washington", "MI": "Michigan",
}


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def decode_str(header_val):
    if not header_val:
        return ""
    parts = decode_header(header_val)
    res = []
    for text, enc in parts:
        if isinstance(text, bytes):
            res.append(text.decode(enc or "utf-8", errors="ignore"))
        else:
            res.append(str(text))
    return "".join(res)


def load_feed_data():
    state_cases = {}
    if not FEED_CSV.exists():
        return state_cases

    with open(FEED_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            state = row.get("State", "").strip()
            if state not in state_cases:
                state_cases[state] = []
            state_cases[state].append({
                "case_no": row.get("Case_or_TaxDeed_No", "").strip(),
                "county": row.get("County", "").strip(),
                "balance": float(row.get("Surplus_Balance_USD", 0)),
                "sale_date": row.get("Sale_Date", "").strip(),
            })

    for state in state_cases:
        state_cases[state].sort(key=lambda x: x["balance"], reverse=True)
    return state_cases


def clean_apple_mail_drafts():
    """
    Tells Apple Mail (Mail.app) directly via AppleScript to delete drafts
    whose recipients have already been sent to.
    """
    applescript = """
    tell application "System Events"
        set isRunning to (name of processes) contains "Mail"
    end tell
    if isRunning then
        tell application "Mail"
            try
                set sentBox to sent mailbox
                set totalSent to count of messages of sentBox
                set maxCount to 40
                if totalSent < maxCount then set maxCount to totalSent
                
                set recentSent to messages 1 thru maxCount of sentBox
                set sentRecipients to {}
                repeat with aMsg in recentSent
                    try
                        repeat with aRecipient in (every to recipient of aMsg)
                            set end of sentRecipients to (address of aRecipient)
                        end repeat
                    end try
                end repeat
                
                set draftsBox to drafts mailbox
                set draftList to every message of draftsBox
                set deletedCount to 0
                repeat with dMsg in draftList
                    try
                        repeat with dRecipient in (every to recipient of dMsg)
                            set dAddr to (address of dRecipient)
                            if sentRecipients contains dAddr then
                                delete dMsg
                                set deletedCount to deletedCount + 1
                            end if
                        end repeat
                    end try
                end repeat
                return deletedCount
            on error
                return 0
            end try
        end tell
    else
        return 0
    end if
    """
    try:
        res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True, timeout=5)
        count = int(res.stdout.strip()) if res.stdout.strip().isdigit() else 0
        if count > 0:
            log(f"  🍎 Apple Mail: Expunged {count} sent draft(s) directly in Mail.app.")
    except Exception:
        pass


def clean_imap_drafts(mail):
    """
    Scans [Gmail]/Sent Mail and purges corresponding drafts from [Gmail]/Drafts.
    """
    # 1. Get recent sent recipients
    status, count = mail.select('"[Gmail]/Sent Mail"')
    if status != "OK":
        return

    status, messages = mail.search(None, "ALL")
    if status != "OK" or not messages[0]:
        return

    sent_emails = set()
    msg_ids = messages[0].split()
    for mid in reversed(msg_ids[-50:]):
        res, data = mail.fetch(mid, "(BODY[HEADER.FIELDS (TO CC SUBJECT)])")
        if res == "OK" and data and isinstance(data[0], tuple):
            msg = email.message_from_bytes(data[0][1])
            to_raw = decode_str(msg.get("To", ""))
            _, to_addr = parseaddr(to_raw)
            if to_addr:
                sent_emails.add(to_addr.lower().strip())

    if not sent_emails:
        return

    # 2. Select Drafts and purge matches
    status, count = mail.select('"[Gmail]/Drafts"')
    if status != "OK":
        return

    status, messages = mail.search(None, "ALL")
    if status != "OK" or not messages[0]:
        return

    draft_ids = messages[0].split()
    removed_count = 0

    for did in draft_ids:
        res, data = mail.fetch(did, "(BODY[HEADER.FIELDS (TO SUBJECT)])")
        if res == "OK" and data and isinstance(data[0], tuple):
            msg = email.message_from_bytes(data[0][1])
            to_raw = decode_str(msg.get("To", ""))
            _, to_addr = parseaddr(to_raw)
            to_clean = to_addr.lower().strip() if to_addr else ""

            if to_clean in sent_emails:
                mail.store(did, "+FLAGS", r"(\Deleted)")
                removed_count += 1
                log(f"  🗑️ IMAP: Removed sent draft for: {to_clean}")

    if removed_count > 0:
        mail.expunge()
        log(f"✓ Expunged {removed_count} sent draft(s) from [Gmail]/Drafts.")


def check_and_create_auto_responses(mail, state_cases):
    """
    Scans INBOX for replies to outreach emails and creates a customized reply draft.
    """
    status, count = mail.select("INBOX")
    if status != "OK":
        return

    status, messages = mail.search(None, "UNSEEN")
    if status != "OK" or not messages[0]:
        return

    msg_ids = messages[0].split()

    for mid in msg_ids:
        res, data = mail.fetch(mid, "(RFC822)")
        if res != "OK" or not data or not isinstance(data[0], tuple):
            continue

        msg = email.message_from_bytes(data[0][1])
        sender_raw = decode_str(msg.get("From", ""))
        sender_name, sender_email = parseaddr(sender_raw)
        subject_raw = decode_str(msg.get("Subject", ""))
        message_id = msg.get("Message-ID", "")

        if "surplus" not in subject_raw.lower() and "excess proceeds" not in subject_raw.lower():
            continue

        log(f"  📩 Detected outreach reply from: {sender_name} <{sender_email}> (Sub: {subject_raw})")

        first_name = sender_name.split()[0] if sender_name else ""

        body_text = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body_text = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body_text = msg.get_payload(decode=True).decode(errors="ignore")

        detected_state = "FL"
        for code, name in STATE_NAMES.items():
            if name.lower() in subject_raw.lower() or name.lower() in body_text.lower():
                detected_state = code
                break

        state_name = STATE_NAMES.get(detected_state, "Florida")
        cases = state_cases.get(detected_state, state_cases.get("FL", []))[:3]
        
        sample_bullets = []
        for c in cases:
            sample_bullets.append(f"• Docket {c['case_no']} ({c['county']} Co.) — ${c['balance']:,.0f} surplus balance")
        sample_block = "\n".join(sample_bullets)

        greeting = f"Hi {first_name}," if first_name else "Hello,"

        reply_body = f"""{greeting}

Thanks for getting back to me.

Here are a few verified records from our current {state_name} index with bank and senior mortgages filtered out:

{sample_block}

We deliver the full feed every morning at 7:00 AM EST in CSV, Excel, and JSON ($249/month flat, cancel anytime).

You can start subscription access directly here:
{STRIPE_LINK}

Let me know if you have any questions or if you'd like to see more details on any of these files.

Best,

David Mahler
surplusdocket.com
david@surplusdocket.com"""

        reply_subject = subject_raw if subject_raw.lower().startswith("re:") else f"Re: {subject_raw}"

        draft_msg = MIMEText(reply_body, "plain", "utf-8")
        draft_msg["From"] = f"{FROM_NAME} <{SENDER_EMAIL}>"
        draft_msg["To"] = sender_raw
        draft_msg["Subject"] = reply_subject
        draft_msg["Reply-To"] = f"{FROM_NAME} <{REPLY_TO}>"
        if message_id:
            draft_msg["In-Reply-To"] = message_id
            draft_msg["References"] = message_id
        draft_msg["Date"] = formatdate(localtime=True)
        draft_msg["Message-ID"] = make_msgid()

        status, count = mail.select('"[Gmail]/Drafts"')
        if status == "OK":
            now_epoch = time.time()
            internal_date = imaplib.Time2Internaldate(now_epoch)
            append_status, res = mail.append('"[Gmail]/Drafts"', r"(\Draft)", internal_date, draft_msg.as_bytes())
            if append_status == "OK":
                log(f"  🎉 Auto-response draft created in Gmail for {sender_email}!")


def run_single_check():
    """Runs a single check across Apple Mail and Gmail."""
    clean_apple_mail_drafts()
    state_cases = load_feed_data()
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASS)
        clean_imap_drafts(mail)
        check_and_create_auto_responses(mail, state_cases)
        mail.logout()
    except Exception as e:
        log(f"IMAP connection error: {e}")


def daemon_loop():
    log("🚀 Surplus Docket Continuous Daemon Started (Running every 15s)...")
    while True:
        try:
            run_single_check()
        except Exception as e:
            log(f"Unexpected error in daemon loop: {e}")
        time.sleep(15)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_single_check()
    else:
        daemon_loop()
