#!/usr/bin/env python3
"""
Surplus Docket — Continuous Background Daemon: Auto-Cleaner, Drafter & Unsubscriber
==================================================================================
1. Instantly cleans sent drafts from BOTH Apple Mail (Mail.app) and Gmail IMAP
   so drafts disappear the moment you click Send.
2. Monitors INBOX for any prospect replies from contacted law firms and statutory
   inquiries from surplusdocket.com.
3. Automatically prepares customized response drafts with verified state benchmark
   records and Stripe checkout link in [Gmail]/Drafts for review before sending.
4. Auto-unsubscribes to any newsletter or marketing drip subscriptions resulting from
   form submissions via RFC 8058 One-Click, RFC 2369, and body unsubscribe links.
5. Runs continuously in a lightweight background process.
"""

import csv
import email
from email.header import decode_header
import imaplib
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid, parseaddr
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
OUTREACH_DIR = BASE_DIR / "outreach"
FEED_CSV = BASE_DIR / "exports" / "Master_Surplus_Lead_Feed.csv"
TARGETS_CSV = OUTREACH_DIR / "verified_attorney_targets.csv"
SUBMISSIONS_LOG_CSV = OUTREACH_DIR / "form_submissions_log.csv"
LOG_FILE = OUTREACH_DIR / "auto_responder.log"
UNSUBSCRIBE_LOG = OUTREACH_DIR / "unsubscribed.log"
UNSUBSCRIBED_URLS_FILE = OUTREACH_DIR / "unsubscribed_urls.json"
CREATED_DRAFTS_LOG = OUTREACH_DIR / "created_drafts_log.json"

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


def log_unsubscribe(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(UNSUBSCRIBE_LOG, "a", encoding="utf-8") as f:
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


def clean_domain_str(url_or_email):
    """Extracts a normalized canonical domain string."""
    if not url_or_email:
        return ""
    s = url_or_email.lower().strip()
    if "@" in s:
        s = s.split("@")[1]
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    s = s.split("/")[0].split("?")[0].split(":")[0]
    return s


def load_target_domains():
    """Loads all known target attorney/law firm domains."""
    domains = set()
    if TARGETS_CSV.exists():
        with open(TARGETS_CSV, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d1 = clean_domain_str(r.get("Source_URL", ""))
                d2 = clean_domain_str(r.get("Email", ""))
                if d1: domains.add(d1)
                if d2: domains.add(d2)
    if SUBMISSIONS_LOG_CSV.exists():
        with open(SUBMISSIONS_LOG_CSV, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d1 = clean_domain_str(r.get("target_url", ""))
                d2 = clean_domain_str(r.get("form_url", ""))
                if d1: domains.add(d1)
                if d2: domains.add(d2)
    return domains


def load_unsubscribed_urls():
    if UNSUBSCRIBED_URLS_FILE.exists():
        try:
            with open(UNSUBSCRIBED_URLS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_unsubscribed_url(url):
    urls = load_unsubscribed_urls()
    urls.add(url)
    try:
        with open(UNSUBSCRIBED_URLS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(urls), f, indent=2)
    except Exception:
        pass


def load_created_drafts():
    if CREATED_DRAFTS_LOG.exists():
        try:
            with open(CREATED_DRAFTS_LOG, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_created_draft(draft_key):
    drafts = load_created_drafts()
    drafts.add(draft_key)
    try:
        with open(CREATED_DRAFTS_LOG, "w", encoding="utf-8") as f:
            json.dump(list(drafts), f, indent=2)
    except Exception:
        pass


def extract_body_parts(msg):
    """Returns (text_body, html_body) decoded from email message."""
    text_body = ""
    html_body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition") or "")
            if "attachment" in cdispo:
                continue
            if ctype == "text/plain" and not text_body:
                text_body = part.get_payload(decode=True).decode(errors="ignore")
            elif ctype == "text/html" and not html_body:
                html_body = part.get_payload(decode=True).decode(errors="ignore")
    else:
        payload = msg.get_payload(decode=True).decode(errors="ignore")
        if msg.get_content_type() == "text/html":
            html_body = payload
        else:
            text_body = payload
    return text_body, html_body


def extract_unsubscribe_details(msg, text_body, html_body):
    """
    Extracts RFC 8058 One-Click, RFC 2369 header URLs, and body unsubscribe URLs.
    """
    one_click_post_url = None
    http_urls = []
    mailto_targets = []

    # 1. Check RFC 2369 / RFC 8058 headers
    list_unsub = decode_str(msg.get("List-Unsubscribe", ""))
    list_unsub_post = decode_str(msg.get("List-Unsubscribe-Post", "")).strip()

    if list_unsub:
        entries = re.findall(r"<([^>]+)>", list_unsub)
        for entry in entries:
            entry = entry.strip()
            if entry.startswith("mailto:"):
                mailto_targets.append(entry)
            elif entry.startswith("https://") or entry.startswith("http://"):
                if list_unsub_post.lower() == "list-unsubscribe=one-click" and entry.startswith("https://"):
                    one_click_post_url = entry
                else:
                    http_urls.append(entry)

    # 2. Check HTML body for unsubscribe links
    if html_body:
        html_matches = re.findall(r'href=["\'](https?://[^"\']*(?:unsubscribe|optout|opt-out|manage-preferences|email-preferences|subscription-preferences)[^"\']*)["\']', html_body, re.IGNORECASE)
        for u in html_matches:
            if u not in http_urls and u != one_click_post_url:
                http_urls.append(u)

    # 3. Check plain text body for unsubscribe links
    if text_body:
        text_matches = re.findall(r'(https?://[^\s<>"\'\)]*(?:unsubscribe|optout|opt-out|manage-preferences|email-preferences|subscription-preferences)[^\s<>"\'\)]*)', text_body, re.IGNORECASE)
        for u in text_matches:
            if u not in http_urls and u != one_click_post_url:
                http_urls.append(u)

    return {
        "one_click_post": one_click_post_url,
        "http_urls": http_urls,
        "mailto": mailto_targets,
    }


def execute_unsubscribe(url, is_one_click=False):
    """Executes unsubscription via HTTP POST or GET request."""
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    }
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        if is_one_click:
            req_data = b"List-Unsubscribe=One-Click"
            req_headers["Content-Type"] = "application/x-www-form-urlencoded"
            req = urllib.request.Request(url, data=req_data, headers=req_headers, method="POST")
        else:
            req = urllib.request.Request(url, headers=req_headers, method="GET")

        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            status_code = resp.getcode()
            if 200 <= status_code < 400:
                save_unsubscribed_url(url)
                return True, f"HTTP {status_code} Success"
            return False, f"HTTP {status_code} Response"
    except Exception as e:
        return False, str(e)


def is_automated_receipt_or_bounce(msg, sender_email, subject_raw):
    """Identifies automated delivery notices, bounces, and out-of-office autoreplies."""
    subj = subject_raw.lower().strip()
    s_email = sender_email.lower().strip()

    # Bounce and notification senders
    if any(k in s_email for k in ["mailer-daemon", "postmaster", "bounce", "notifications@", "no-reply@", "noreply@"]):
        return True

    # Standard headers for automated emails
    auto_submitted = (msg.get("Auto-Submitted") or "").lower()
    if auto_submitted in ["auto-generated", "auto-replied"]:
        return True

    # Bounce / Autoreply subject cues
    bounce_cues = [
        "automatic reply:",
        "out of office:",
        "undelivered mail",
        "delivery status notification",
        "failure notice",
        "mail delivery failed",
        "auto-reply",
        "autosubmitted",
    ]
    if any(cue in subj for cue in bounce_cues):
        return True

    return False


def parse_statutory_inquiry(subject_raw, text_body):
    """
    Parses inquiry form submissions originating from surplusdocket.com/inquiry.html
    or modal inquiry forms.
    """
    subj = subject_raw.strip()
    is_inquiry = any(k in subj for k in [
        "STATUTORY INQUIRY RECORD",
        "[Surplus Docket Inquiry]",
        "[Surplus Docket Modal Inquiry]",
        "Surplus Docket Public Record Request"
    ]) or "OFFICIAL STATUTORY INQUIRY RECORD" in text_body

    if not is_inquiry:
        return None

    name = ""
    name_m = re.search(r"Inquiring Entity Name:\s*([^\r\n]+)", text_body)
    if name_m:
        name = name_m.group(1).strip()
    else:
        name_m2 = re.search(r"\bName:\s*([^\r\n]+)", text_body)
        if name_m2:
            name = name_m2.group(1).strip()

    email_addr = ""
    email_m = re.search(r"Inquiring Entity Email:\s*([^\s\r\n]+)", text_body)
    if email_m:
        email_addr = email_m.group(1).strip()
    else:
        email_m2 = re.search(r"\bEmail:\s*([^\s\r\n]+)", text_body)
        if email_m2:
            email_addr = email_m2.group(1).strip()

    state_code = "FL"
    jur_m = re.search(r"Practice Jurisdiction:\s*([^\r\n]+)", text_body)
    jur_text = jur_m.group(1).strip().lower() if jur_m else text_body.lower()
    for code, s_name in STATE_NAMES.items():
        if s_name.lower() in jur_text or code.lower() == jur_text:
            state_code = code
            break

    msg_text = ""
    msg_m = re.search(r"Message:\s*(.+)", text_body, re.DOTALL)
    if msg_m:
        msg_text = msg_m.group(1).strip()

    return {
        "name": name,
        "email": email_addr,
        "state_code": state_code,
        "message": msg_text,
    }


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
    Scans INBOX:
    1. Automatically detects and executes unsubscriptions for marketing/newsletters.
    2. Detects prospect replies from law firms and inquiries from surplusdocket.com.
    3. Creates personalized response drafts in [Gmail]/Drafts for David's review.
    """
    status, count = mail.select("INBOX")
    if status != "OK":
        return

    status, messages = mail.search(None, "UNSEEN")
    if status != "OK" or not messages[0]:
        return

    msg_ids = messages[0].split()
    target_domains = load_target_domains()
    already_unsubscribed = load_unsubscribed_urls()
    already_drafted = load_created_drafts()

    for mid in msg_ids:
        res, data = mail.fetch(mid, "(RFC822)")
        if res != "OK" or not data or not isinstance(data[0], tuple):
            continue

        msg = email.message_from_bytes(data[0][1])
        sender_raw = decode_str(msg.get("From", ""))
        sender_name, sender_email = parseaddr(sender_raw)
        subject_raw = decode_str(msg.get("Subject", ""))
        message_id = msg.get("Message-ID", "")
        reply_to_raw = decode_str(msg.get("Reply-To", ""))
        _, reply_to_email = parseaddr(reply_to_raw)

        text_body, html_body = extract_body_parts(msg)

        # -------------------------------------------------------------
        # 1. AUTO-UNSUBSCRIBE MODULE
        # -------------------------------------------------------------
        unsub_details = extract_unsubscribe_details(msg, text_body, html_body)
        has_unsub = unsub_details["one_click_post"] or unsub_details["http_urls"] or unsub_details["mailto"]
        
        is_newsletter_or_drip = (
            bool(msg.get("List-Unsubscribe")) or
            (msg.get("Precedence") or "").lower() in ["bulk", "list"] or
            "newsletter" in subject_raw.lower() or
            "digest" in subject_raw.lower() or
            "subscribed" in subject_raw.lower() or
            "marketing" in subject_raw.lower() or
            "update from" in subject_raw.lower() or
            "lawmatics" in (text_body + html_body).lower() or
            "hubspot" in (text_body + html_body).lower() or
            "mailchimp" in (text_body + html_body).lower() or
            "activecampaign" in (text_body + html_body).lower()
        )

        if has_unsub and is_newsletter_or_drip:
            unsub_done = False
            if unsub_details["one_click_post"] and unsub_details["one_click_post"] not in already_unsubscribed:
                ok, detail = execute_unsubscribe(unsub_details["one_click_post"], is_one_click=True)
                log_unsubscribe(f"🛑 RFC 8058 One-Click Unsubscribe for {sender_email} ({unsub_details['one_click_post']}): {detail}")
                unsub_done = True
            
            if not unsub_done:
                for u in unsub_details["http_urls"]:
                    if u not in already_unsubscribed:
                        ok, detail = execute_unsubscribe(u, is_one_click=False)
                        log_unsubscribe(f"🛑 Web GET Unsubscribe for {sender_email} ({u}): {detail}")
                        unsub_done = True
                        break

            if unsub_done:
                mail.store(mid, "+FLAGS", r"(\Seen \Deleted)")
                mail.expunge()
                log(f"  🧹 Auto-unsubscribed and cleared marketing email from {sender_email}")
                continue

        # -------------------------------------------------------------
        # 2. FILTER AUTOMATED BOUNCES / NOTICES
        # -------------------------------------------------------------
        if is_automated_receipt_or_bounce(msg, sender_email, subject_raw):
            mail.store(mid, "+FLAGS", r"(\Seen)")
            continue

        # -------------------------------------------------------------
        # 3. STATUTORY WEBSITE INQUIRY DETECTION
        # -------------------------------------------------------------
        inquiry_data = parse_statutory_inquiry(subject_raw, text_body)
        if inquiry_data:
            prospect_name = inquiry_data["name"]
            prospect_email = inquiry_data["email"] or reply_to_email
            state_code = inquiry_data["state_code"]
            state_name = STATE_NAMES.get(state_code, "Florida")
            cases = state_cases.get(state_code, state_cases.get("FL", []))[:3]

            draft_key = f"inquiry:{prospect_email}:{state_code}"
            if draft_key in already_drafted:
                mail.store(mid, "+FLAGS", r"(\Seen)")
                continue

            first_name = prospect_name.split()[0] if prospect_name else ""
            greeting = f"Hi {first_name}," if first_name else "Hello,"

            sample_bullets = []
            for c in cases:
                sample_bullets.append(f"• Docket {c['case_no']} ({c['county']} Co.) — ${c['balance']:,.0f} surplus balance")
            sample_block = "\n".join(sample_bullets)

            reply_body = f"""{greeting}

Thank you for submitting your statutory inquiry to Surplus Docket regarding {state_name} public record excess proceeds data.

Here are a few verified, active records from our current {state_name} docket index (with bank and senior mortgages filtered out upstream):

{sample_block}

We publish and deliver the complete standardized morning feed at 7:00 AM EST every day in CSV, Excel, and JSON API formats ($249/month flat, cancel anytime).

You can activate daily feed delivery for your practice directly here:
{STRIPE_LINK}

Please let me know if you would like custom county-level filtering or have specific questions about our statutory lien-filtering methodology.

Best regards,

David Mahler
Surplus Docket
surplusdocket.com
david@surplusdocket.com"""

            reply_subject = f"Re: Surplus Docket — Statutory Public Record Inquiry [{state_name}]"

            draft_msg = MIMEText(reply_body, "plain", "utf-8")
            draft_msg["From"] = f"{FROM_NAME} <{SENDER_EMAIL}>"
            draft_msg["To"] = f"{prospect_name} <{prospect_email}>" if prospect_name else prospect_email
            draft_msg["Subject"] = reply_subject
            draft_msg["Reply-To"] = f"{FROM_NAME} <{REPLY_TO}>"
            if message_id:
                draft_msg["In-Reply-To"] = message_id
                draft_msg["References"] = message_id
            draft_msg["Date"] = formatdate(localtime=True)
            draft_msg["Message-ID"] = make_msgid()

            mail.select('"[Gmail]/Drafts"')
            now_epoch = time.time()
            internal_date = imaplib.Time2Internaldate(now_epoch)
            append_status, res = mail.append('"[Gmail]/Drafts"', r"(\Draft)", internal_date, draft_msg.as_bytes())
            mail.select("INBOX")
            if append_status == "OK":
                save_created_draft(draft_key)
                mail.store(mid, "+FLAGS", r"(\Seen)")
                log(f"  🎉 Statutory inquiry draft created in Gmail for {prospect_email}!")
            continue

        # -------------------------------------------------------------
        # 4. LAW FIRM OUTREACH REPLY DETECTION
        # -------------------------------------------------------------
        sender_dom = clean_domain_str(sender_email)
        is_target_firm = sender_dom in target_domains
        has_surplus_kw = any(k in subject_raw.lower() or k in text_body.lower() for k in [
            "surplus", "excess proceeds", "tax deed", "excess funds", "surplus docket", "tax sale", "overages"
        ])

        if not is_target_firm and not has_surplus_kw:
            continue

        draft_key = f"reply:{sender_email}:{subject_raw[:30]}"
        if draft_key in already_drafted:
            mail.store(mid, "+FLAGS", r"(\Seen)")
            continue

        log(f"  📩 Detected outreach reply from: {sender_name} <{sender_email}> (Sub: {subject_raw})")

        first_name = sender_name.split()[0] if sender_name else ""
        detected_state = "FL"
        for code, name in STATE_NAMES.items():
            if name.lower() in subject_raw.lower() or name.lower() in text_body.lower():
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

We deliver the full standardized feed every morning at 7:00 AM EST in CSV, Excel, and JSON ($249/month flat, cancel anytime).

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

        mail.select('"[Gmail]/Drafts"')
        now_epoch = time.time()
        internal_date = imaplib.Time2Internaldate(now_epoch)
        append_status, res = mail.append('"[Gmail]/Drafts"', r"(\Draft)", internal_date, draft_msg.as_bytes())
        mail.select("INBOX")
        if append_status == "OK":
            save_created_draft(draft_key)
            mail.store(mid, "+FLAGS", r"(\Seen)")
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
