#!/usr/bin/env python3
"""
Surplus Docket — Scheduled Inbound Follow-Up Sentinel (Cohen Asset Recovery)
===========================================================================
Automatically dispatches a timed, threaded follow-up to Alden (Cohen Asset Recovery)
on Monday, October 05, 2026 at 9:30 AM EDT (13:30 UTC).

Features:
- Time Gate: Only executes when current ET >= 2026-10-05 09:30:00 EDT
- Idempotency Ledger: outreach/alden_followup_log.json guarantees zero duplicate sends
- Threading: Preserves exact In-Reply-To and References to appear seamlessly in the thread
- Envelope Fix: Uses GMAIL_USER as SMTP envelope while presenting authentic persona headers
"""

import os
import sys
import json
import smtplib
import argparse
import email.utils
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Optional local .env loading
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as ef:
            for line in ef:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))
    except Exception:
        pass

LOG_FILE = BASE_DIR / "outreach" / "alden_followup_log.json"

GMAIL_USER = os.getenv("GMAIL_USER", "sandwichfitness@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# Scheduled Target: Monday, Oct 5, 2026 at 09:30:00 EDT
SCHEDULED_TIME_ISO = "2026-10-05T09:30:00"

THREAD_HEADERS = {
    "Message-ID-Ref": "<0A00ED4D-E826-46B2-A4E3-13B9170AA2EA@surplusdocket.com>",
    "In-Reply-To": "<0A00ED4D-E826-46B2-A4E3-13B9170AA2EA@surplusdocket.com>",
    "References": "<CAD4DNF_Nc-gKjn1H2vMypOzqrt9yipGDjysQ5iJ4-XtYm_cX9Q@mail.gmail.com> <0A00ED4D-E826-46B2-A4E3-13B9170AA2EA@surplusdocket.com>",
    "Subject": "Re: Florida feed questions: Miami-Dade, Palm Beach, and Broward",
    "To": '"A.L.D.E.N." <alden@cohenrecoverylaw.com>',
    "Cc": "phil@cohenrecoverylaw.com, adam@cohenrecoverylaw.com"
}


def get_current_et():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return datetime.now()


def is_already_sent():
    if not LOG_FILE.exists():
        return False
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("status") == "SENT"
    except Exception:
        return False


def build_email_content(persona="elena"):
    """
    Builds the tailored follow-up message depending on chosen persona.
    """
    if persona.lower() == "david":
        from_name = "David Mahler"
        from_email = "david@surplusdocket.com"
        reply_to = "david@surplusdocket.com"
        
        text_body = """Hi Alden,

Following up on Elena's note below to ensure the Florida sample dockets (Miami-Dade, Palm Beach, and Broward) imported cleanly into your system.

If you, Phil, or Adam have any questions on the data feed architecture or would like us to run a sample for any specific Florida judicial circuit before activating the 7-day trial, I'm glad to help directly.

Best regards,

David Mahler
Managing Director | Surplus Docket
david@surplusdocket.com
https://surplusdocket.com
"""
        html_body = """<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #1e293b;">
<p>Hi Alden,</p>

<p>Following up on Elena's note below to ensure the Florida sample dockets (Miami-Dade, Palm Beach, and Broward) imported cleanly into your system.</p>

<p>If you, Phil, or Adam have any questions on the data feed architecture or would like us to run a sample for any specific Florida judicial circuit before activating the 7-day trial, I'm glad to help directly.</p>

<p>Best regards,</p>

<p><strong>David Mahler</strong><br>
Managing Director | Surplus Docket<br>
<a href="mailto:david@surplusdocket.com" style="color: #1b365d;">david@surplusdocket.com</a><br>
<a href="https://surplusdocket.com" style="color: #4c6d48;">surplusdocket.com</a></p>
</body>
</html>
"""
    else:
        from_name = "Elena Brooks"
        from_email = "elena.brooks@surplusdocket.com"
        reply_to = "elena.brooks@surplusdocket.com"

        text_body = """Hi Alden,

Following up briefly to ensure the Florida sample dockets (Miami-Dade, Palm Beach, and Broward) imported cleanly into your case management system.

If you, Phil, or Adam have any questions regarding the court registry docket feeds or would like us to index a specific Florida judicial circuit before activating your 7-day evaluation, just let me know.

Best regards,

Elena Brooks
Director of Practice Relations
Surplus Docket
elena.brooks@surplusdocket.com
https://surplusdocket.com
"""
        html_body = """<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #1e293b;">
<p>Hi Alden,</p>

<p>Following up briefly to ensure the Florida sample dockets (Miami-Dade, Palm Beach, and Broward) imported cleanly into your case management system.</p>

<p>If you, Phil, or Adam have any questions regarding the court registry docket feeds or would like us to index a specific Florida judicial circuit before activating your 7-day evaluation, just let me know.</p>

<p>Best regards,</p>

<p><strong>Elena Brooks</strong><br>
Director of Practice Relations<br>
Surplus Docket<br>
<a href="mailto:elena.brooks@surplusdocket.com" style="color: #1b365d;">elena.brooks@surplusdocket.com</a><br>
<a href="https://surplusdocket.com" style="color: #4c6d48;">surplusdocket.com</a></p>
</body>
</html>
"""

    return from_name, from_email, reply_to, text_body, html_body


def check_and_send(persona="elena", dry_run=False, force=False):
    print("=" * 70)
    print(" 📬 SURPLUS DOCKET — AUTOMATED INBOUND FOLLOW-UP SENTINEL")
    print("=" * 70)
    
    if is_already_sent() and not force:
        print("✅ Follow-up to Cohen Asset Recovery (Alden) was ALREADY sent.")
        print(f"   Log record: {LOG_FILE}")
        return 0

    now_et = get_current_et()
    scheduled_dt = datetime.fromisoformat(SCHEDULED_TIME_ISO)
    if hasattr(now_et, "tzinfo") and now_et.tzinfo is not None:
        try:
            from zoneinfo import ZoneInfo
            scheduled_dt = scheduled_dt.replace(tzinfo=ZoneInfo("America/New_York"))
        except Exception:
            pass

    print(f"Current Time (ET) : {now_et.strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
    print(f"Scheduled Time(ET): {scheduled_dt.strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
    print(f"Persona           : {persona.upper()}")
    print(f"Mode              : {'DRY RUN' if dry_run else 'LIVE'}\n")

    if now_et < scheduled_dt and not force:
        time_diff = scheduled_dt - now_et
        hours, remainder = divmod(int(time_diff.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        print(f"⏳ STANDBY: Not yet scheduled time. Waiting for Monday 09:30 AM EDT.")
        print(f"   Time remaining: {hours}h {minutes}m. Exiting cleanly (code 0).")
        return 0

    from_name, from_email, reply_to, text_body, html_body = build_email_content(persona)

    # Build RFC 822 Message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = THREAD_HEADERS["Subject"]
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = THREAD_HEADERS["To"]
    msg["Cc"] = THREAD_HEADERS["Cc"]
    msg["Reply-To"] = reply_to
    msg["In-Reply-To"] = THREAD_HEADERS["In-Reply-To"]
    msg["References"] = THREAD_HEADERS["References"]
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain="surplusdocket.com")

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    all_recipients = ["alden@cohenrecoverylaw.com", "phil@cohenrecoverylaw.com", "adam@cohenrecoverylaw.com"]

    if dry_run:
        print("[DRY RUN PREVIEW] Generated threaded message:")
        print(f"From       : {msg['From']}")
        print(f"To         : {msg['To']}")
        print(f"Cc         : {msg['Cc']}")
        print(f"In-Reply-To: {msg['In-Reply-To']}")
        print(f"References : {msg['References']}")
        print("-" * 50)
        print(text_body)
        print("-" * 50)
        print("✅ Dry run successful. 0 emails sent.")
        return 0

    if not GMAIL_APP_PASS:
        print("❌ ERROR: GMAIL_APP_PASS is not configured. Cannot dispatch email.")
        return 1

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASS)
        
        # Envelope sender is GMAIL_USER for flawless deliverability & DKIM
        server.sendmail(GMAIL_USER, all_recipients, msg.as_string())
        server.quit()

        print(f"🚀 Successfully dispatched threaded follow-up to Alden & Cohen Recovery Law Team!")
        
        # Write idempotency ledger
        log_entry = {
            "status": "SENT",
            "timestamp": now_et.isoformat(),
            "target": "alden@cohenrecoverylaw.com",
            "cc": ["phil@cohenrecoverylaw.com", "adam@cohenrecoverylaw.com"],
            "persona": persona,
            "from": f"{from_name} <{from_email}>",
            "subject": THREAD_HEADERS["Subject"],
            "message_id": msg["Message-ID"]
        }
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log_entry, f, indent=2)
        print(f"✓ Recorded dispatch in {LOG_FILE.name}")
        return 0
    except Exception as e:
        print(f"❌ Failed to send follow-up: {e}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scheduled follow-up to Cohen Asset Recovery")
    parser.add_argument("--persona", choices=["elena", "david"], default="elena",
                        help="Sender persona: 'elena' (recommended) or 'david'")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without sending")
    parser.add_argument("--force", action="store_true", help="Force send even before scheduled time or if logged")
    args = parser.parse_args()

    sys.exit(check_and_send(persona=args.persona, dry_run=args.dry_run, force=args.force))
