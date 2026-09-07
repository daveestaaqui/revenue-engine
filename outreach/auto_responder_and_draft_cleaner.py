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
import smtplib
import ssl
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid, parseaddr, parsedate_to_datetime
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTREACH_DIR = BASE_DIR / "outreach"
FEED_CSV = BASE_DIR / "exports" / "Master_Surplus_Lead_Feed.csv"
TARGETS_CSV = OUTREACH_DIR / "verified_attorney_targets.csv"
MASTER_TARGETS_CSV = OUTREACH_DIR / "master_ranked_attorney_targets.csv"
SUBMISSIONS_LOG_CSV = OUTREACH_DIR / "form_submissions_log.csv"
LOG_FILE = OUTREACH_DIR / "auto_responder.log"
UNSUBSCRIBE_LOG = OUTREACH_DIR / "unsubscribed.log"
UNSUBSCRIBED_URLS_FILE = OUTREACH_DIR / "unsubscribed_urls.json"
CREATED_DRAFTS_LOG = OUTREACH_DIR / "created_drafts_log.json"
NOTABLE_ACTIVITY_FILE = DATA_DIR / "notable_email_activity.json"

# Optional local .env loading
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    try:
        with open(ENV_FILE, "r") as ef:
            for line in ef:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))
    except Exception:
        pass

# Credentials & Identity
GMAIL_USER = os.getenv("GMAIL_USER", "sandwichfitness@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
AUTO_SEND = os.getenv("AUTO_SEND", "true").lower() in ["true", "1", "yes"]
FROM_NAME = os.getenv("FROM_NAME", "Surplus Docket Intelligence")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "dockets@surplusdocket.com")
REPLY_TO = os.getenv("REPLY_TO", "dockets@surplusdocket.com")
REPORT_RECIPIENT = os.getenv("REPORT_RECIPIENT", "sandwichfitness@gmail.com")
SITE_URL = "https://surplusdocket.com"
STRIPE_LINK = "https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X"

# Human Turnaround Pacing (Policy SD-POL-PACING-2026-V1)
# Ensures enough time elapses to simulate realistic coordinator review & docket lookup
MIN_HUMAN_RESPONSE_DELAY_SECONDS = int(os.getenv("MIN_HUMAN_RESPONSE_DELAY_SECONDS", "360"))  # 6 min base
MAX_HUMAN_RESPONSE_DELAY_SECONDS = int(os.getenv("MAX_HUMAN_RESPONSE_DELAY_SECONDS", "600"))  # 10 min max

# Operational Hours for Automated Dispatch (Policy SD-POL-HOURS-2026-V1)
# Ensures auto-responses are sent during legal operations hours (Mon-Fri 8:00 AM - 6:30 PM EST)
SENDING_START_HOUR_EST = int(os.getenv("SENDING_START_HOUR_EST", "8"))     # 8:00 AM EST
SENDING_END_HOUR_EST = int(os.getenv("SENDING_END_HOUR_EST", "18"))       # 6:00 PM EST
SENDING_END_MINUTE_EST = int(os.getenv("SENDING_END_MINUTE_EST", "30"))   # 6:30 PM EST

STATE_NAMES = {
    "FL": "Florida", "TX": "Texas", "GA": "Georgia",
    "NC": "North Carolina", "TN": "Tennessee", "CA": "California",
    "NY": "New York", "NJ": "New Jersey", "OH": "Ohio",
    "IL": "Illinois", "PA": "Pennsylvania", "MD": "Maryland",
    "AZ": "Arizona", "WA": "Washington", "MI": "Michigan",
}

STATE_STATUTES = {
    "FL": ("Florida", "Fla. Stat. § 197.582"),
    "TX": ("Texas", "Tex. Tax Code § 34.04"),
    "GA": ("Georgia", "O.C.G.A. § 48-4-5"),
    "NC": ("North Carolina", "N.C. Gen. Stat. § 105-374"),
    "TN": ("Tennessee", "Tenn. Code Ann. § 67-5-2510"),
    "CA": ("California", "Cal. Rev. & Tax Code § 4675"),
}

# Synchronized Statutory Knowledge Base (Reflects all website guides & appellate authorities)
JURISDICTION_STATUTORY_KNOWLEDGE = {
    "FL": {
        "state_name": "Florida",
        "statute_cite": "Fla. Stat. § 197.582",
        "claim_window": "120-day statutory notice window from clerk mailing",
        "custodian": "County Clerk of Court / Tax Collector",
        "procedural_mechanism": "Verified claim or motion for distribution filed with the clerk of the circuit court",
        "priority_rules": "Governmental liens -> senior recorded mortgagees/lienholders -> record title owner or estate heirs",
        "escheat_rule": "Unclaimed funds escheat to Florida Department of Financial Services (DFS) Division of Unclaimed Property",
        "toolkit_motion": "Verified Petition for Distribution of Tax Deed Surplus Funds",
    },
    "TX": {
        "state_name": "Texas",
        "statute_cite": "Tex. Tax Code § 34.04",
        "claim_window": "Strict 2-year statutory limitation period from deed recordation",
        "custodian": "District Court Registry",
        "procedural_mechanism": "Formal judicial petition filed in original tax suit with citation/service on all former taxing units",
        "priority_rules": "Taxing entities -> non-party lienholders -> former titleholder of record",
        "escheat_rule": "Funds unclaimed after 2 years transfer to county general fund under Sec. 34.04",
        "toolkit_motion": "Petition for Distribution of Excess Proceeds under Tex. Tax Code § 34.04",
    },
    "GA": {
        "state_name": "Georgia",
        "statute_cite": "O.C.G.A. § 48-4-5",
        "claim_window": "5-year statutory hold before interpleader",
        "custodian": "County Tax Commissioner / Sheriff Registry",
        "procedural_mechanism": "Statutory demand to custodian or interpleader action in Superior Court",
        "priority_rules": "Record owner at time of tax sale -> junior lienholders in order of priority",
        "escheat_rule": "Custodian may interplead funds into Superior Court if competing claims exist",
        "toolkit_motion": "Demand for Excess Proceeds & Affidavit of Record Ownership",
    },
    "CA": {
        "state_name": "California",
        "statute_cite": "Cal. Rev. & Tax Code § 4675",
        "claim_window": "Strict 1-year statutory deadline from recording of tax deed",
        "custodian": "County Board of Supervisors / County Tax Collector",
        "procedural_mechanism": "Claim for Excess Proceeds with required documentary proof of interest under Section 4675",
        "priority_rules": "Holders of recorded liens in legal priority -> parties of interest (titleholders/heirs)",
        "escheat_rule": "Unclaimed funds remain with county or escheat to state controller",
        "toolkit_motion": "Claim for Excess Proceeds from Sale of Tax-Defaulted Property",
    },
    "NC": {
        "state_name": "North Carolina",
        "statute_cite": "N.C. Gen. Stat. § 105-374",
        "claim_window": "10-day upset bid period following sale; statutory claim window",
        "custodian": "Clerk of Superior Court Registry",
        "procedural_mechanism": "Special proceeding or motion in tax foreclosure cause",
        "priority_rules": "Costs and taxes -> mortgagees and judgment creditors -> titleholders",
        "escheat_rule": "Unclaimed proceeds escheat to state Escheat Fund",
        "toolkit_motion": "Motion for Disbursement of Surplus Foreclosure Proceeds",
    },
    "TN": {
        "state_name": "Tennessee",
        "statute_cite": "Tenn. Code Ann. § 67-5-2510",
        "claim_window": "1-year statutory redemption and claim period",
        "custodian": "Chancery Court / Circuit Court Registry",
        "procedural_mechanism": "Motion for distribution of excess proceeds filed in Chancery Court",
        "priority_rules": "Taxes and court costs -> lienholders -> delinquent property owner or heirs",
        "escheat_rule": "Funds held by clerk & master pending judicial order of distribution",
        "toolkit_motion": "Petition for Excess Proceeds from Chancery Delinquent Tax Sale",
    },
}

# Regulatory & Non-Legal-Advice Disclaimer (Protects against UPL and ensures clear non-lawyer status)
LEGAL_DISCLAIMER = """---
Legal Notice & Regulatory Disclaimer: Surplus Docket is a specialized legal technology and court records intelligence service, not a law firm. Surplus Docket does not provide legal advice, legal counsel, or legal representation, and no attorney-client relationship is formed by this correspondence. All docket records, statutory references, and procedural timelines are compiled exclusively for informational and intelligence purposes for licensed attorneys and recovery professionals. Surplus recovery petitions, motions, and pleadings must be prepared and filed by a licensed attorney admitted to practice in the appropriate jurisdiction."""

# Policy SD-POL-OUTREACH-2026-V1 Hard Domain Blocklist
SYSTEM_BLOCKLIST_DOMAINS = {
    # Tech / Platform / Email providers
    "google.com", "gmail.com", "googlemail.com", "googleapis.com",
    "cloudflare.com", "cloudflare.net",
    "microsoft.com", "outlook.com", "hotmail.com", "live.com", "office.com", "office365.com", "msn.com",
    "apple.com", "icloud.com",
    "yahoo.com", "aol.com",
    # Transactional / APIs / Infrastructure
    "stripe.com", "github.com", "resend.com", "formsubmit.co",
    "sendgrid.net", "sendgrid.com", "mailgun.org", "mailgun.net", "postmarkapp.com",
    "amazonses.com", "amazonaws.com",
    # Marketing platforms & CRMs
    "mailchimp.com", "lawmatics.com", "hubspot.com", "activecampaign.com", "constantcontact.com",
    # Retail / E-commerce / Banking
    "amazon.com", "paypal.com", "citi.com", "citicards.com", "chase.com", "bankofamerica.com",
    "wellsfargo.com", "capitalist.net", "starkbros.com",
    # Internal domain
    "surplusdocket.com",
}

# Senders matching these patterns never receive outreach drafts
SYSTEM_SENDER_PATTERNS = [
    "noreply", "no-reply", "no_reply", "donotreply", "do-not-reply",
    "mailer-daemon", "postmaster", "bounce", "notification", "notifications",
    "alert", "alerts", "security", "support", "billing", "invoicing",
    "account", "accounts", "service", "services", "team", "newsletter", "digest",
    "confirm", "confirmation", "verify", "verification", "auto-reply", "automated"
]

# Subjects matching these cues are system / administrative emails
SYSTEM_SUBJECT_BLOCKLIST = [
    "confirmation", "verification", "verify", "security alert",
    "payment", "invoice", "statement", "receipt", "shipping confirmation",
    "password", "login", "welcome to", "delivery status", "failure notice",
    "undelivered mail", "out of office", "automatic reply", "auto-reply", "missing email"
]

BANNED_FIRST_NAMES = {
    "gmail", "google", "noreply", "no-reply", "team", "support", "info",
    "admin", "intake", "mailer", "daemon", "service", "customer", "billing"
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


def load_target_directory():
    """
    Loads verified target database into:
    1. directory: dict mapping canonical domain -> target metadata dict
    2. email_directory: dict mapping email address -> target metadata dict
    3. domains: set of valid domains
    """
    directory = {}
    email_directory = {}
    domains = set()

    def add_target(domain, email_addr, name, firm, state, specialty, details):
        record = {
            "name": (name or "").strip(),
            "firm": (firm or "").strip(),
            "state": (state or "FL").strip().upper(),
            "specialty": (specialty or "").strip(),
            "practice_details": (details or "").strip(),
        }
        if domain and domain not in SYSTEM_BLOCKLIST_DOMAINS:
            domains.add(domain)
            if domain not in directory or not directory[domain].get("name"):
                directory[domain] = record
        if email_addr and "@" in email_addr:
            clean_em = email_addr.lower().strip()
            if clean_em not in email_directory or not email_directory[clean_em].get("name"):
                email_directory[clean_em] = record

    if MASTER_TARGETS_CSV.exists():
        with open(MASTER_TARGETS_CSV, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d = clean_domain_str(r.get("Source_URL", "")) or clean_domain_str(r.get("Contact_Email", ""))
                em = r.get("Contact_Email", "").strip()
                add_target(d, em, r.get("Name"), r.get("Firm"), r.get("State"), r.get("Specialty"), r.get("Practice_Details"))

    if TARGETS_CSV.exists():
        with open(TARGETS_CSV, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d = clean_domain_str(r.get("Source_URL", "")) or clean_domain_str(r.get("Email", ""))
                em = r.get("Email", "").strip()
                add_target(d, em, r.get("Name"), r.get("Firm"), r.get("State"), r.get("Specialty"), r.get("Practice_Details"))

    if SUBMISSIONS_LOG_CSV.exists():
        with open(SUBMISSIONS_LOG_CSV, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d = clean_domain_str(r.get("target_url", "")) or clean_domain_str(r.get("form_url", ""))
                add_target(d, "", r.get("firm_name"), r.get("firm_name"), r.get("state"), "", "")

    return directory, email_directory, domains


def load_target_domains():
    """Backward compatibility wrapper returning set of domains."""
    _, _, domains = load_target_directory()
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


_last_pacing_logged = {}


def get_required_human_delay(message_id, sender_email, text_body):
    """
    Calculates an authentic human turnaround delay (default 6 to 10 minutes)
    with natural deterministic jitter based on message metadata.
    Deterministic so the delay threshold stays consistent across daemon polling ticks.
    """
    seed = f"{message_id}_{sender_email}_{text_body[:40]}"
    jitter_range = max(1, MAX_HUMAN_RESPONSE_DELAY_SECONDS - MIN_HUMAN_RESPONSE_DELAY_SECONDS)
    jitter = abs(hash(seed)) % jitter_range
    return MIN_HUMAN_RESPONSE_DELAY_SECONDS + jitter


def get_message_age_seconds(msg):
    """
    Computes how many seconds have elapsed since the inbound message was sent.
    """
    date_header = msg.get("Date")
    if not date_header:
        return 999999.0
    try:
        msg_dt = parsedate_to_datetime(date_header)
        if msg_dt.tzinfo is None:
            msg_dt = msg_dt.replace(tzinfo=timezone.utc)
        now_dt = datetime.now(timezone.utc)
        return max(0.0, (now_dt - msg_dt.astimezone(timezone.utc)).total_seconds())
    except Exception:
        return 999999.0


def is_within_sending_hours(now_dt=None, start_hour=SENDING_START_HOUR_EST, end_hour=SENDING_END_HOUR_EST, end_minute=SENDING_END_MINUTE_EST):
    """
    Checks if current time in America/New_York (Eastern Time) falls within
    standard legal operations business hours:
    Monday through Friday: 8:00 AM to 6:30 PM EST.
    Returns: (is_valid: bool, reason: str)
    """
    if now_dt is None:
        try:
            from zoneinfo import ZoneInfo
            now_dt = datetime.now(ZoneInfo("America/New_York"))
        except Exception:
            now_dt = datetime.now()

    # weekday: 0 = Monday, 4 = Friday, 5 = Saturday, 6 = Sunday
    if now_dt.weekday() >= 5:
        day_name = "Saturday" if now_dt.weekday() == 5 else "Sunday"
        return False, f"Weekend hold ({day_name} outside Mon-Fri business hours)"

    current_minute_of_day = now_dt.hour * 60 + now_dt.minute
    start_minute_of_day = start_hour * 60
    end_minute_of_day = end_hour * 60 + end_minute

    if current_minute_of_day < start_minute_of_day:
        return False, f"Early morning hold (Current time {now_dt.strftime('%I:%M %p')} is before {start_hour}:00 AM EST)"

    if current_minute_of_day > end_minute_of_day:
        return False, f"Evening hold (Current time {now_dt.strftime('%I:%M %p')} is after {end_hour}:{end_minute:02d} EST)"

    return True, f"Within business hours ({now_dt.strftime('%A %I:%M %p EST')})"


def send_response_email(msg_obj, from_email, recipient_email, dry_run=False):
    """
    Directly dispatches an authoritative, persona-aligned response via Gmail SMTP.
    When sent via smtp.gmail.com, Google automatically archives a copy to [Gmail]/Sent Mail.
    Returns: (success: bool, detail: str)
    """
    if dry_run:
        log(f"  [DRY RUN] Would auto-send email to {recipient_email} from {from_email}")
        return True, "Dry-run successful"

    if not GMAIL_APP_PASS:
        return False, "GMAIL_APP_PASS not configured in environment or .env"

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.starttls(context=context)
            server.login(GMAIL_USER, GMAIL_APP_PASS)
            server.send_message(msg_obj, from_addr=from_email, to_addrs=[recipient_email])
        return True, "Dispatched successfully via SMTP"
    except Exception as e:
        err_msg = f"SMTP transmission error: {e}"
        log(f"  ❌ {err_msg}")
        return False, err_msg


def record_notable_email_activity(activity):
    """
    Records notable inbound/outbound email and voicemail interactions in
    data/notable_email_activity.json for inclusion in the Weekly Executive Report.
    """
    try:
        NOTABLE_ACTIVITY_FILE.parent.mkdir(parents=True, exist_ok=True)
        activities = []
        if NOTABLE_ACTIVITY_FILE.exists():
            try:
                with open(NOTABLE_ACTIVITY_FILE, "r", encoding="utf-8") as f:
                    activities = json.load(f)
            except Exception:
                activities = []

        # Avoid duplicate entries by id
        act_id = activity.get("id", "")
        existing_ids = {a.get("id") for a in activities if a.get("id")}
        if act_id and act_id in existing_ids:
            return

        activities.insert(0, activity)  # Newest first
        activities = activities[:200]    # Keep up to 200 most recent activities

        with open(NOTABLE_ACTIVITY_FILE, "w", encoding="utf-8") as f:
            json.dump(activities, f, indent=2)
    except Exception as e:
        log(f"Warning: could not record notable email activity: {e}")


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
    s_dom = clean_domain_str(s_email)
    local_part = s_email.split("@")[0] if "@" in s_email else s_email

    # 1. Hard domain blocklist
    if s_dom in SYSTEM_BLOCKLIST_DOMAINS:
        return True

    # 2. Bounce and notification sender local-parts
    if any(k in local_part for k in SYSTEM_SENDER_PATTERNS):
        return True

    # 3. Standard headers for automated emails
    auto_submitted = (msg.get("Auto-Submitted") or "").lower()
    if auto_submitted and auto_submitted != "no":
        return True

    if (msg.get("X-Autoreply") or "").lower() == "yes":
        return True

    precedence = (msg.get("Precedence") or "").lower()
    if precedence in ["bulk", "list", "junk"]:
        return True

    if msg.get("List-Unsubscribe"):
        return True

    # 4. Bounce / Administrative subject cues
    if any(cue in subj for cue in SYSTEM_SUBJECT_BLOCKLIST):
        return True

    return False


def is_prospect_eligible(msg, sender_email, sender_name, subject_raw, text_body, directory, email_directory, target_domains):
    """
    Enforces Rule 2.1 & 2.2 of Surplus Docket Inbound Outreach Policy (SD-POL-OUTREACH-2026-V1):
    Returns: (is_eligible: bool, reason: str, target_info: dict, inquiry_info: dict)
    """
    # 1. Check if it is an official statutory website inquiry from surplusdocket.com/inquiry.html
    # (Must check this first because third-party delivery relays like FormSubmit or Cloudflare forward these)
    inquiry_data = parse_statutory_inquiry(subject_raw, text_body)
    if inquiry_data and inquiry_data.get("email"):
        inq_email = inquiry_data.get("email", "").lower().strip()
        inq_dom = clean_domain_str(inq_email)
        if inq_dom not in SYSTEM_BLOCKLIST_DOMAINS and inq_email != "sandwichfitness@gmail.com":
            return True, "Verified statutory website inquiry", None, inquiry_data

    # 1.5 Check if it is a Google Voice voicemail notification for (508) 419-3178
    gv_inquiry = parse_google_voice_voicemail(sender_email, subject_raw, text_body)
    if gv_inquiry:
        return True, "Verified Google Voice voicemail inquiry", None, gv_inquiry

    # 1.6 Check if email was sent directly to inquiries@surplusdocket.com or aubrey.hayes@surplusdocket.com
    msg_to = (msg.get("To", "") + " " + msg.get("Delivered-To", "") + " " + msg.get("X-Forwarded-To", "")).lower()
    if any(addr in msg_to for addr in ["inquiries@surplusdocket.com", "aubrey.hayes@surplusdocket.com", "contact@surplusdocket.com"]):
        s_email = sender_email.lower().strip()
        det_state, c_name, c_circ = extract_jurisdiction_context(subject_raw, text_body, default_state="FL")
        state_name = STATE_NAMES.get(det_state, "Florida")
        direct_inquiry = {
            "name": sender_name or "",
            "email": s_email,
            "firm": "",
            "department": "Inquiries & Intake Desk",
            "jurisdiction": state_name,
            "state_code": det_state,
            "docket": "",
            "ref": f"DIRECT-INQ-{hash(s_email + text_body[:40]) % 10000000}",
            "message": text_body.strip(),
            "is_direct_inbound": True,
        }
        return True, "Verified direct inbound inquiry to inquiries@surplusdocket.com", None, direct_inquiry

    s_email = sender_email.lower().strip()
    s_dom = clean_domain_str(s_email)

    # 2. Filter all automated, bounce, or system messages
    if is_automated_receipt_or_bounce(msg, s_email, subject_raw):
        return False, "Message identified as automated notification, bounce, or system alert", None, None

    # 3. Filter self-sent or internal domain emails
    if s_dom == "surplusdocket.com" or s_email == "sandwichfitness@gmail.com":
        return False, "Self-sent or internal domain transmission", None, None

    # 4. Check if sender matches our verified law firm target directory
    target_info = email_directory.get(s_email) or directory.get(s_dom)
    if target_info:
        return True, f"Verified target firm match ({target_info.get('firm', s_dom)})", target_info, None

    # Fallback: check if domain is directly in target domains
    if s_dom in target_domains:
        fallback_info = {
            "name": sender_name or "",
            "firm": s_dom.replace(".com", "").replace("-", " ").title(),
            "state": "FL",
            "specialty": "Surplus & Excess Proceeds",
            "practice_details": "",
        }
        return True, f"Verified target domain match ({s_dom})", fallback_info, None

    return False, f"Sender '{s_email}' is not in verified target database and not a statutory inquiry", None, None


# County & Judicial Circuit / Court Registry Directory
COUNTY_CIRCUIT_MAP = {
    # Florida (FL)
    "miami-dade": ("FL", "Miami-Dade", "11th Judicial Circuit"),
    "broward": ("FL", "Broward", "17th Judicial Circuit"),
    "palm beach": ("FL", "Palm Beach", "15th Judicial Circuit"),
    "hillsborough": ("FL", "Hillsborough", "13th Judicial Circuit"),
    "orange": ("FL", "Orange", "9th Judicial Circuit"),
    "duval": ("FL", "Duval", "4th Judicial Circuit"),
    "pinellas": ("FL", "Pinellas", "6th Judicial Circuit"),
    "lee": ("FL", "Lee", "20th Judicial Circuit"),
    "polk": ("FL", "Polk", "10th Judicial Circuit"),
    "brevard": ("FL", "Brevard", "18th Judicial Circuit"),
    "volusia": ("FL", "Volusia", "7th Judicial Circuit"),
    "pasco": ("FL", "Pasco", "6th Judicial Circuit"),
    "seminole": ("FL", "Seminole", "18th Judicial Circuit"),
    "sarasota": ("FL", "Sarasota", "12th Judicial Circuit"),
    "manatee": ("FL", "Manatee", "12th Judicial Circuit"),

    # Texas (TX)
    "harris": ("TX", "Harris", "Harris County Civil District Courts"),
    "dallas": ("TX", "Dallas", "Dallas County Civil District Courts"),
    "tarrant": ("TX", "Tarrant", "Tarrant County Civil District Courts"),
    "bexar": ("TX", "Bexar", "Bexar County Civil District Courts"),
    "travis": ("TX", "Travis", "Travis County Civil District Courts"),
    "collin": ("TX", "Collin", "Collin County Civil District Courts"),
    "denton": ("TX", "Denton", "Denton County Civil District Courts"),
    "el paso": ("TX", "El Paso", "El Paso County Civil District Courts"),
    "fort bend": ("TX", "Fort Bend", "Fort Bend County Civil District Courts"),
    "montgomery": ("TX", "Montgomery", "Montgomery County Civil District Courts"),

    # Georgia (GA)
    "fulton": ("GA", "Fulton", "Fulton County Superior Court"),
    "gwinnett": ("GA", "Gwinnett", "Gwinnett County Superior Court"),
    "cobb": ("GA", "Cobb", "Cobb County Superior Court"),
    "dekalb": ("GA", "DeKalb", "DeKalb County Superior Court"),
    "chatham": ("GA", "Chatham", "Chatham County Superior Court"),
    "clayton": ("GA", "Clayton", "Clayton County Superior Court"),
    "cherokee": ("GA", "Cherokee", "Cherokee County Superior Court"),
    "henry": ("GA", "Henry", "Henry County Superior Court"),

    # North Carolina (NC)
    "mecklenburg": ("NC", "Mecklenburg", "26th Judicial District Superior Court"),
    "wake": ("NC", "Wake", "10th Judicial District Superior Court"),
    "guilford": ("NC", "Guilford", "18th Judicial District Superior Court"),
    "forsyth": ("NC", "Forsyth", "21st Judicial District Superior Court"),
    "durham": ("NC", "Durham", "14th Judicial District Superior Court"),
    "cumberland": ("NC", "Cumberland", "12th Judicial District Superior Court"),

    # Tennessee (TN)
    "shelby": ("TN", "Shelby", "30th Judicial District (Chancery & Circuit)"),
    "davidson": ("TN", "Davidson", "20th Judicial District (Chancery & Circuit)"),
    "knox": ("TN", "Knox", "6th Judicial District (Chancery & Circuit)"),
    "hamilton": ("TN", "Hamilton", "11th Judicial District (Chancery & Circuit)"),
    "rutherford": ("TN", "Rutherford", "16th Judicial District (Chancery & Circuit)"),

    # California (CA)
    "los angeles": ("CA", "Los Angeles", "Los Angeles County Superior Court"),
    "san diego": ("CA", "San Diego", "San Diego County Superior Court"),
    "orange, ca": ("CA", "Orange", "Orange County Superior Court"),
    "riverside": ("CA", "Riverside", "Riverside County Superior Court"),
    "san bernardino": ("CA", "San Bernardino", "San Bernardino County Superior Court"),
    "santa clara": ("CA", "Santa Clara", "Santa Clara County Superior Court"),
    "alameda": ("CA", "Alameda", "Alameda County Superior Court"),
    "sacramento": ("CA", "Sacramento", "Sacramento County Superior Court"),
    "contra costa": ("CA", "Contra Costa", "Contra Costa County Superior Court"),
}


def extract_jurisdiction_context(subject_raw, text_body, default_state="FL"):
    """
    Identifies specific counties and judicial circuits mentioned in the correspondence.
    Returns: (detected_state, county_name, circuit_name)
    """
    content = f"{subject_raw} {text_body}".lower()

    # 1. Match specific counties with whole-word regex
    for county_key, (st, c_name, circ_name) in COUNTY_CIRCUIT_MAP.items():
        pattern = r"\b" + re.escape(county_key) + r"\b"
        if re.search(pattern, content):
            return st, c_name, circ_name

    # 2. Match state names
    for code, s_name in STATE_NAMES.items():
        pattern = r"\b" + re.escape(s_name.lower()) + r"\b"
        if re.search(pattern, content):
            return code, None, None

    return default_state, None, None


def analyze_prospect_intent(subject_raw, text_body):
    """
    Multi-factor semantic pattern classifier for law firm replies and objections.
    Evaluates context, specific legal operations, and nuanced attorney queries across 14 categories:
    - 'OPT_OUT'
    - 'IN_HOUSE_PARALEGAL'
    - 'CONTINGENCY_FEE_SPLIT'
    - 'TAX_DEED_VS_MORTGAGE'
    - 'PROBATE_HEIR_RECOVERY'
    - 'TITLE_LIEN_SCRUBBING'
    - 'DATA_FRESHNESS_TIMING'
    - 'SKIP_TRACING_CONTACT'
    - 'LEGAL_TOOLKIT_MOTIONS'
    - 'JURISDICTION'
    - 'DATA_FORMAT'
    - 'SAMPLE_DATA'
    - 'PRICING'
    - 'GENERAL'
    """
    content = f"{subject_raw} {text_body}".lower()

    # 1. Opt-out check takes absolute precedence
    opt_out_cues = [
        "unsubscribe", "remove me", "remove us", "stop emailing",
        "not interested", "take me off", "do not contact", "please remove",
        "wrong email", "cease and desist", "do not email", "not looking for this",
        "take us off", "no thanks", "no thank you", "pass on this"
    ]
    if any(c in content for c in opt_out_cues):
        return "OPT_OUT"

    scores = {
        "TYLER_V_HENNEPIN": 0,
        "LEGAL_REPRESENTATION_OR_ADVICE_REQUEST": 0,
        "IN_HOUSE_PARALEGAL": 0,
        "CONTINGENCY_FEE_SPLIT": 0,
        "TAX_DEED_VS_MORTGAGE": 0,
        "PROBATE_HEIR_RECOVERY": 0,
        "TITLE_LIEN_SCRUBBING": 0,
        "DATA_FRESHNESS_TIMING": 0,
        "SKIP_TRACING_CONTACT": 0,
        "LEGAL_TOOLKIT_MOTIONS": 0,
        "JURISDICTION": 0,
        "DATA_FORMAT": 0,
        "SAMPLE_DATA": 0,
        "PRICING": 0,
    }

    # 2. LEGAL_REPRESENTATION_OR_ADVICE_REQUEST cues (UPL Protection & Non-Lawyer Boundaries)
    upl_cues = [
        "represent me", "represent us", "represent my", "need a lawyer", "need an attorney",
        "are you an attorney", "are you a lawyer", "are you lawyers", "hire you", "hire your firm",
        "take my case", "take our case", "help me get my money", "get my money back",
        "can you file my claim", "file my claim for me", "file a claim for me",
        "is my claim valid", "evaluate my claim", "give me legal advice", "need legal advice",
        "legal counsel", "do i have a case", "fight the bank for me",
        "represent my estate", "can you file on my behalf", "act as my attorney",
        "i need legal help", "give me advice on my case", "can you recover my surplus",
        "get the money from the county for me", "can you handle my claim"
    ]
    for c in upl_cues:
        if c in content:
            scores["LEGAL_REPRESENTATION_OR_ADVICE_REQUEST"] += 5

    # 3. TYLER_V_HENNEPIN cues (SCOTUS 9-0 ruling on Takings Clause & surplus retention)
    tyler_strong = [
        "tyler", "hennepin", "supreme court", "scotus", "takings clause",
        "5th amendment", "fifth amendment", "unconstitutional taking", "equity forfeiture",
        "home equity theft", "unconstitutional retention", "constitutional challenge",
        "post-tyler", "post tyler", "county keeping surplus", "can the county keep"
    ]
    for c in tyler_strong:
        if c in content:
            scores["TYLER_V_HENNEPIN"] += 4

    # 3. IN_HOUSE_PARALEGAL cues
    paralegal_strong = [
        "already have a paralegal", "our paralegal", "paralegal checks",
        "paralegal pulls", "staff handles", "do this in house", "do it in house",
        "in-house", "in house", "our staff", "pull from the county site",
        "pull from the clerk", "search the clerk ourselves", "check the records ourselves",
        "we do our own research", "we pull these ourselves", "already searching",
        "we monitor the clerk", "we check the clerk weekly", "internal team handles",
        "we have staff", "have a paralegal"
    ]
    for c in paralegal_strong:
        if c in content:
            scores["IN_HOUSE_PARALEGAL"] += 4

    has_in_house = any(k in content for k in ["paralegal", "staff", "in house", "in-house", "internal", "ourselves"])
    has_pull_check = any(k in content for k in ["pull", "pulls", "pulling", "check", "checks", "search", "searches", "monitor", "clerk", "county site"])
    if has_in_house and has_pull_check:
        scores["IN_HOUSE_PARALEGAL"] += 4

    # 3. CONTINGENCY_FEE_SPLIT cues
    fee_split_strong = [
        "what percentage do you take", "what cut do you take", "contingency cut",
        "contingency fee", "split the fee", "fee split", "fee splitting",
        "percentage of recovery", "percentage of the surplus", "take a cut",
        "finder fee percentage", "rule 4-5.4", "bar rules on fee sharing",
        "ethics rule", "percentage do you charge", "what is your cut",
        "take a percentage", "co-counsel fee", "referral fee"
    ]
    for c in fee_split_strong:
        if c in content:
            scores["CONTINGENCY_FEE_SPLIT"] += 4

    # 4. TAX_DEED_VS_MORTGAGE cues
    tax_vs_mortgage_strong = [
        "tax deed or mortgage", "mortgage foreclosure or tax", "civil foreclosure vs",
        "tax collector or clerk", "tax collector vs clerk", "are these tax sales or bank foreclosures",
        "tax overages vs civil", "mortgage surplus vs tax surplus", "tax overbid",
        "civil registry funds", "tax deed surplus or mortgage", "mortgage or tax",
        "are these mortgage or tax"
    ]
    for c in tax_vs_mortgage_strong:
        if c in content:
            scores["TAX_DEED_VS_MORTGAGE"] += 4

    has_tax_concept = any(k in content for k in ["tax deed", "tax sale", "tax overage", "tax overages", "tax overbid", "tax collector"])
    has_mortgage_concept = any(k in content for k in ["mortgage", "foreclosure surplus", "civil foreclosure", "civil registry"])
    if has_tax_concept and has_mortgage_concept:
        scores["TAX_DEED_VS_MORTGAGE"] += 4

    # 5. PROBATE_HEIR_RECOVERY cues
    probate_strong = [
        "deceased", "heir", "heirs", "probate", "estate", "intestate", "intestacy",
        "decedent", "next of kin", "inheritance", "ancillary probate",
        "deceased owner", "deceased titleholder", "surviving spouse", "estate recovery"
    ]
    for c in probate_strong:
        if c in content:
            scores["PROBATE_HEIR_RECOVERY"] += 4

    # 6. TITLE_LIEN_SCRUBBING cues
    lien_strong = [
        "how do you scrub", "senior mortgage", "senior lien", "first mortgage",
        "title search", "title commitment", "encumbrance", "junior lien",
        "second mortgage", "heloc", "hoa lien", "irs lien", "municipal lien",
        "code enforcement", "lis pendens", "clean title", "how do you verify equity",
        "how do you know there is equity", "lien screening", "unencumbered"
    ]
    for c in lien_strong:
        if c in content:
            scores["TITLE_LIEN_SCRUBBING"] += 4

    # 7. DATA_FRESHNESS_TIMING cues
    freshness_strong = [
        "how fresh", "turnaround time", "lag time", "how soon after auction",
        "how soon after sale", "delay between sale and", "when is it published",
        "what time does the feed go out", "update frequency", "real-time or daily",
        "how fast do we get", "auction lag", "how recent", "how quickly after the sale"
    ]
    for c in freshness_strong:
        if c in content:
            scores["DATA_FRESHNESS_TIMING"] += 4

    # 8. SKIP_TRACING_CONTACT cues
    skip_trace_strong = [
        "skip trace", "skip-trace", "skip tracing", "phone number", "phone numbers",
        "owner contact", "contact information", "reach the owner", "locate the owner",
        "mailing address", "mailing addresses", "how do we reach", "do you provide phone",
        "cold call", "direct mail", "skip-tracing"
    ]
    for c in skip_trace_strong:
        if c in content:
            scores["SKIP_TRACING_CONTACT"] += 4

    # 9. LEGAL_TOOLKIT_MOTIONS cues
    toolkit_strong = [
        "motion", "motions", "pleading", "pleadings", "template", "templates",
        "toolkit", "petition", "petitions", "affidavit", "affidavits",
        "retainer", "retainer agreement", "claim form", "court forms",
        "claim packet", "motion for distribution", "legal templates"
    ]
    for c in toolkit_strong:
        if c in content:
            scores["LEGAL_TOOLKIT_MOTIONS"] += 4

    # 10. JURISDICTION cues
    jurisdiction_phrases = [
        "what counties", "which counties", "do you cover", "jurisdiction",
        "circuits", "what circuits", "which circuits", "county coverage",
        "are you in", "do you have data for", "cover in florida", "cover in texas",
        "statewide coverage", "specific counties"
    ]
    for c in jurisdiction_phrases:
        if c in content:
            scores["JURISDICTION"] += 3

    for c_key in COUNTY_CIRCUIT_MAP:
        pattern = r"\b" + re.escape(c_key) + r"\b"
        if re.search(pattern, content):
            scores["JURISDICTION"] += 2

    # 11. DATA_FORMAT cues
    format_strong = [
        "api endpoint", "csv format", "excel file", "spreadsheet columns",
        "webhook", "rest api", "json feed", "data fields", "export format",
        "import into our crm", "practice management", "clio", "filevine",
        "smokeball", "raw data format", "what fields do you provide"
    ]
    for c in format_strong:
        if c in content:
            scores["DATA_FORMAT"] += 3

    # 12. SAMPLE_DATA cues
    sample_strong = [
        "send me a sample", "can i see a sample", "can you send examples",
        "preview of the data", "show me a few cases", "example records",
        "see a sample spreadsheet", "sample feed", "pull a few files",
        "proof of records", "send a sample", "send over a sample",
        "share a sample", "see an example"
    ]
    for c in sample_strong:
        if c in content:
            scores["SAMPLE_DATA"] += 3

    # 13. PRICING cues
    pricing_strong = [
        "how much is it", "what is the cost", "subscription cost", "pricing structure",
        "month to month", "annual contract", "billing terms", "what does it cost",
        "rates for subscription", "payment terms", "how much per month", "flat fee or",
        "how much do you charge", "what are your fees", "what are the terms"
    ]
    for c in pricing_strong:
        if c in content:
            scores["PRICING"] += 3

    # Weak baseline fallback if no strong trigger hit
    if max(scores.values()) == 0:
        if any(w in content for w in ["cost", "price", "pricing", "rate", "rates", "fee"]):
            scores["PRICING"] += 1
        if any(w in content for w in ["sample", "example", "preview"]):
            scores["SAMPLE_DATA"] += 1
        if any(w in content for w in ["format", "api", "csv", "excel", "json"]):
            scores["DATA_FORMAT"] += 1
        if any(w in content for w in ["county", "counties", "coverage"]):
            scores["JURISDICTION"] += 1

    best_intent, best_score = max(scores.items(), key=lambda x: x[1])
    if best_score >= 2:
        return best_intent

    return "GENERAL"


def format_sample_records(cases, target_county=None):
    """Formats sample docket cases cleanly without promotional bullet decks."""
    if not cases:
        return "- Verified individual & estate records indexed daily across all judicial circuits"
    sorted_cases = list(cases)
    if target_county:
        target_lower = str(target_county).strip().lower()
        sorted_cases.sort(
            key=lambda c: (
                0 if str(c.get("county", "")).strip().lower() == target_lower else 1,
                -float(c.get("balance", 0))
            )
        )
    lines = []
    for c in sorted_cases[:3]:
        lines.append(f"- {c['county']} Co. (Docket {c['case_no']}): ${c['balance']:,.0f} surplus balance")
    return "\n".join(lines)


DEPARTMENT_PERSONAS = {
    "ONBOARDING": {
        "name": "Elena Brooks",
        "title": "Practitioner Onboarding Specialist",
        "full_title": "Practitioner Onboarding Specialist | Surplus Docket",
        "email": "elena.brooks@surplusdocket.com",
        "department": "7-Day Institutional Practice Evaluation",
    },
    "ENTERPRISE": {
        "name": "Julian Vance",
        "title": "Director of Practice Relations & Licensing",
        "full_title": "Director of Practice Relations & Licensing | Surplus Docket",
        "email": "julian.vance@surplusdocket.com",
        "department": "Enterprise Feed Licensing",
    },
    "TECHNICAL": {
        "name": "Marcus Chen",
        "title": "Lead Technical Specialist & API Integrations",
        "full_title": "Lead Technical Specialist & API Integrations | Surplus Docket",
        "email": "marcus.chen@surplusdocket.com",
        "department": "Law Practice API Integration",
    },
    "REGISTRY": {
        "name": "Rachel Holloway",
        "title": "County Registry Operations Liaison",
        "full_title": "County Registry Operations Liaison | Surplus Docket",
        "email": "rachel.holloway@surplusdocket.com",
        "department": "Clerk Docket Correction / Notice",
    },
    "COMPLIANCE": {
        "name": "Arthur Miller",
        "title": "Senior Compliance & Research Specialist",
        "full_title": "Senior Compliance & Research Specialist | Surplus Docket",
        "email": "arthur.miller@surplusdocket.com",
        "department": "Statutory Compliance Verification",
    },
    "RESEARCH": {
        "name": "Claire Montgomery",
        "title": "Public Information Liaison",
        "full_title": "Public Information Liaison | Surplus Docket",
        "email": "claire.montgomery@surplusdocket.com",
        "department": "Press / Academic Research",
    },
    "GENERAL": {
        "name": "Elena Brooks",
        "title": "Senior Docket Specialist",
        "full_title": "Senior Docket Specialist | Surplus Docket",
        "email": "elena.brooks@surplusdocket.com",
        "department": "General Publisher Inquiry",
    },
    "INTAKE": {
        "name": "Aubrey Hayes",
        "title": "Executive Intake Coordinator",
        "full_title": "Executive Intake Coordinator | Surplus Docket",
        "email": "aubrey.hayes@surplusdocket.com",
        "department": "Inquiries & Intake Desk",
    },
}


def get_department_persona(role=None, department=None, intent=None):
    """
    Resolves the specialized institutional employee persona based on role, department, or intent.
    """
    if role:
        r = role.strip().lower()
        if r in ["intake", "aubrey", "reception"]:
            return DEPARTMENT_PERSONAS["INTAKE"]
        if r in ["enterprise", "licensing"]:
            return DEPARTMENT_PERSONAS["ENTERPRISE"]
        if r in ["api", "technical", "integrations"]:
            return DEPARTMENT_PERSONAS["TECHNICAL"]
        if r in ["clerk", "registry", "correction", "notice"]:
            return DEPARTMENT_PERSONAS["REGISTRY"]
        if r in ["compliance", "statutory", "research", "title"]:
            return DEPARTMENT_PERSONAS["COMPLIANCE"]
        if r in ["press", "media", "academic"]:
            return DEPARTMENT_PERSONAS["RESEARCH"]
        if r in ["onboarding", "evaluation", "trial"]:
            return DEPARTMENT_PERSONAS["ONBOARDING"]
        if r in ["general", "docket"]:
            return DEPARTMENT_PERSONAS["GENERAL"]

    dept_lower = (department or "").lower()
    if any(k in dept_lower for k in ["intake", "aubrey", "voicemail", "phone inquiry"]):
        return DEPARTMENT_PERSONAS["INTAKE"]
    if any(k in dept_lower for k in ["evaluation", "7-day", "trial", "onboarding"]):
        return DEPARTMENT_PERSONAS["ONBOARDING"]
    if any(k in dept_lower for k in ["enterprise", "licensing", "custom feed", "multi-jurisdiction"]):
        return DEPARTMENT_PERSONAS["ENTERPRISE"]
    if any(k in dept_lower for k in ["api", "integration", "developer", "technical", "rest", "webhook"]):
        return DEPARTMENT_PERSONAS["TECHNICAL"]
    if any(k in dept_lower for k in ["clerk", "correction", "notice", "registry", "court reporter"]):
        return DEPARTMENT_PERSONAS["REGISTRY"]
    if any(k in dept_lower for k in ["compliance", "statutory", "senior lien", "title", "encumbrance"]):
        return DEPARTMENT_PERSONAS["COMPLIANCE"]
    if any(k in dept_lower for k in ["press", "academic", "media", "journalist", "research"]):
        return DEPARTMENT_PERSONAS["RESEARCH"]

    intent_upper = (intent or "").upper()
    if intent_upper in ["TITLE_LIEN_SCRUBBING", "TYLER_V_HENNEPIN", "SKIP_TRACING_CONTACT"]:
        return DEPARTMENT_PERSONAS["COMPLIANCE"]
    if intent_upper in ["DATA_FORMAT", "API_INTEGRATION"]:
        return DEPARTMENT_PERSONAS["TECHNICAL"]
    if intent_upper in ["PRICING", "ENTERPRISE_LICENSING"]:
        return DEPARTMENT_PERSONAS["ENTERPRISE"]

    return DEPARTMENT_PERSONAS["GENERAL"]


def get_employee_signature(persona=None, role=None, department=None, intent=None):
    """
    Generates an authentic institutional signature for the assigned specialized employee.
    """
    if not persona:
        persona = get_department_persona(role=role, department=department, intent=intent)
    return f"""Best regards,

{persona['name']}
{persona['full_title']}
surplusdocket.com
{persona['email']}"""


def extract_thread_history(text_body):
    """
    Extracts the complete conversational thread context from an inbound email.
    Separates the latest response from prior turns, tracks turn count, and preserves
    mentioned counties, dockets, and counsel identity across the conversation.
    """
    if not text_body:
        return {
            "latest_message": "",
            "prior_history": "",
            "thread_turn_count": 0,
            "mentioned_counties": [],
            "is_follow_up": False,
        }

    split_patterns = [
        r"\n\s*(?:On\s+[A-Za-z]+,?\s+[A-Za-z0-9\s,:]+wrote:)",
        r"\n\s*[-_]{2,}\s*Original Message\s*[-_]{2,}",
        r"\n\s*From:\s*[^\n]+\s*Sent:\s*[^\n]+",
        r"\n\s*Begin forwarded message:",
        r"\n\s*>+\s*",
    ]

    combined_split = "|".join(split_patterns)
    parts = re.split(combined_split, text_body, maxsplit=1, flags=re.IGNORECASE)

    latest_message = parts[0].strip() if len(parts) > 0 else text_body.strip()
    prior_history = parts[1].strip() if len(parts) > 1 else ""

    turn_markers = len(re.findall(r"(?:On\s+.+wrote:|Original Message|From:\s*)", text_body, re.IGNORECASE))

    full_text = text_body.lower()
    mentioned_counties = []
    for county, (c_state, c_name, c_circuit) in COUNTY_CIRCUIT_MAP.items():
        if county in full_text:
            mentioned_counties.append((c_state, c_name, c_circuit))

    return {
        "latest_message": latest_message,
        "prior_history": prior_history,
        "thread_turn_count": turn_markers,
        "mentioned_counties": mentioned_counties,
        "is_follow_up": turn_markers > 0 or len(prior_history) > 0,
    }


def get_gmail_drafts_mailbox(mail):
    """
    Dynamically identifies the exact Drafts folder on Gmail IMAP.
    Ensures drafts are deposited directly into the user's primary Drafts view.
    """
    try:
        typ, folders = mail.list()
        if typ == "OK" and folders:
            for f in folders:
                dec = f.decode("utf-8", errors="ignore")
                if r"\Drafts" in dec:
                    parts = dec.split(' "/" ')
                    if len(parts) > 1:
                        return parts[1].strip()
    except Exception:
        pass
    return '"[Gmail]/Drafts"'


def get_elena_role_title(role=None, department=None, intent=None):
    """
    Returns the dynamic institutional role title for Elena Brooks based on
    explicit role, inquiry department, or intent context.
    Defaults to Senior Docket Specialist for general outreach follow-ups.
    """
    if role or department:
        persona = get_department_persona(role=role, department=department)
        return persona["full_title"]
    return "Senior Docket Specialist | Surplus Docket"


def get_elena_signature(role=None, department=None, intent=None):
    """
    Generates an authentic Elena Brooks signature reflecting her dynamic institutional role.
    """
    role_title = get_elena_role_title(role=role, department=department, intent=intent)
    return f"""Best regards,

Elena Brooks
{role_title}
surplusdocket.com
elena.brooks@surplusdocket.com"""


def compose_elena_response(intent, target_info, sender_name, sender_email, subject_raw, text_body, state_cases, role=None, department=None):
    """
    Drafts an authentic, context-aware legal correspondence adhering strictly to
    Elena Brooks' persona voice. Completely free of AI tells, buzzwords, or formulaic templates.
    """
    # 0. Thread History Context
    thread_ctx = extract_thread_history(text_body)

    # 1. Resolve Name and Greeting
    raw_name = target_info.get("name") if target_info else sender_name
    first_name = ""
    if raw_name:
        parts = [p.strip() for p in raw_name.split() if p.strip()]
        if parts:
            cand = parts[0].title()
            if cand.lower() not in BANNED_FIRST_NAMES and len(cand) > 1:
                first_name = cand

    firm_name = target_info.get("firm") if target_info else ""
    if first_name:
        greeting = f"Hi {first_name},"
    elif firm_name:
        greeting = f"Hello {firm_name} team,"
    else:
        greeting = "Hello,"

    # 2. Resolve State, County, and Circuit Context
    default_state = target_info.get("state", "FL") if target_info else "FL"
    detected_state, county_name, circuit_name = extract_jurisdiction_context(
        subject_raw, text_body, default_state=default_state
    )

    # Preserve county and jurisdiction from prior thread turns if omitted in latest reply
    if not county_name and thread_ctx["mentioned_counties"]:
        c_st, c_nm, c_circ = thread_ctx["mentioned_counties"][0]
        detected_state = c_st
        county_name = c_nm
        circuit_name = c_circ

    state_name = STATE_NAMES.get(detected_state, "Florida")
    statute_cite = STATE_STATUTES.get(detected_state, (state_name, "applicable state civil code"))[1]
    stat_entry = JURISDICTION_STATUTORY_KNOWLEDGE.get(detected_state, JURISDICTION_STATUTORY_KNOWLEDGE["FL"])
    claim_window = stat_entry.get("claim_window", "designated statutory claim window")
    custodian = stat_entry.get("custodian", "court or county registry")
    toolkit_motion = stat_entry.get("toolkit_motion", "Verified Petition for Distribution of Surplus Funds")
    priority_rules = stat_entry.get("priority_rules", "Governmental liens -> recorded senior mortgagees -> titleholder of record")

    # Resolve benchmark cases
    cases = state_cases.get(detected_state, state_cases.get("FL", []))

    signature = get_elena_signature(role=role, department=department, intent=intent)

    # 3. Intent-Specific Authentic Legal Prose
    if intent == "OPT_OUT":
        body = f"""{greeting}

Understood completely. I've marked your firm's file and removed you from all future docket distributions and updates.

{signature}"""

    elif intent == "TYLER_V_HENNEPIN":
        body = f"""{greeting}

Thanks for asking about how Tyler v. Hennepin County impacts surplus recovery.

The Supreme Court's unanimous 9-0 ruling in Tyler v. Hennepin County, 598 U.S. 631 (2023), established unequivocally that county governments cannot retain property equity exceeding the tax debt owed. Chief Justice Roberts made clear that the Takings Clause of the Fifth Amendment protects excess proceeds as private property, fundamentally invalidating state statutes that historically allowed municipal windfalls.

As a practical matter for recovery counsel in {state_name}, counties that previously allowed surplus funds to escheat directly to county general funds or retained overages under strict forfeiture schemes are now establishing administrative court registry procedures. Under {statute_cite}, former owners and lienholders have designated statutory windows ({claim_window}) to claim excess proceeds deposited with the {custodian}.

Our data intelligence desk monitors clerk registries and tax collector sale dockets across {state_name} every morning. We identify unencumbered equity balances, scrub out junior and senior bank liens upstream, and alert counsel to files with active statutory claim windows before funds escheat.

The feed is delivered every business morning at 7:00 AM EST in CSV, Excel, and JSON ($249/month flat, cancel anytime):
{STRIPE_LINK}

Let me know if your practice is litigating post-Tyler recovery claims in {state_name} or if you'd like to inspect sample cases from our current index.

{signature}"""

    elif intent == "LEGAL_REPRESENTATION_OR_ADVICE_REQUEST":
        body = f"""{greeting}

Thank you for reaching out to Surplus Docket.

Surplus Docket is a specialized court records intelligence and public data indexing service for licensed legal counsel and recovery professionals—we are not a law firm and do not provide legal representation, legal counsel, or legal advice, nor do we file surplus petitions on behalf of individuals or property owners.

Because tax deed surplus and excess proceeds claims involve formal court procedures, title encumbrance examinations, and strict statutory deadlines (such as {statute_cite}), all surplus recovery petitions, motions, and evidentiary hearings must be evaluated and conducted by independent, licensed legal counsel admitted to practice in {state_name}.

If you are seeking legal counsel regarding property equity or surplus funds, we strongly recommend consulting a licensed real estate litigation or probate attorney in your county, or contacting the {state_name} Bar Association Lawyer Referral Service for assistance in retaining qualified counsel.

{signature}"""

    elif intent == "IN_HOUSE_PARALEGAL":
        county_context = f"in {county_name} County" if county_name else f"in {state_name}"
        body = f"""{greeting}

Thanks for getting back to me.

Most of the firms we work with already have an in-house paralegal checking the clerk of court websites weekly. The real bottleneck usually isn't pulling the raw auction overbid list—it's the title search step. County clerk spreadsheets don't scrub out first mortgages or senior institutional liens, so staff often spends 10 to 15 hours pulling deeds only to find a bank lien wiped out the entire balance.

What our research desk does is cross-reference each overage against county recording records and lis pendens upstream. If a senior mortgage or second mortgage eats the equity, we drop the file before delivery. That way your staff is only spending billable hours skip-tracing heirs on clean, claimable funds under {statute_cite}.

The feed is delivered every business morning at 7:00 AM EST in standard CSV and Excel format ($249/month flat across all circuits, cancel anytime). You can review details or activate access here:
{STRIPE_LINK}

Let me know if you'd like me to send over a few sample files {county_context} so your team can compare them against what you're currently pulling.

{signature}"""

    elif intent == "CONTINGENCY_FEE_SPLIT":
        body = f"""{greeting}

Thanks for asking. We don't take any percentage, cut, or contingency fee on recoveries.

Surplus Docket is strictly an intelligence and software subscription ($249/month flat). Under state bar ethics rules governing fee-sharing with non-lawyers (such as Florida Bar Rule 4-5.4 and equivalent state rules), fee splits are prohibited. Because we operate purely as a technology data feed, your firm retains 100% of your statutory or contingency fees with your clients. There are no backend cuts or per-claim fees.

If you'd like to test the feed for your practice, you can activate daily 7:00 AM EST delivery directly here:
{STRIPE_LINK}

Happy to answer any other compliance or vendor billing questions your office might have.

{signature}"""

    elif intent == "TAX_DEED_VS_MORTGAGE":
        body = f"""{greeting}

Thanks for following up. We actually track both, but we separate them into dedicated columns so counsel can route them according to practice focus.

Tax deed overbids under {statute_cite} are held by the {custodian} with specific statutory claim deadlines ({claim_window} before funds escheat). Civil mortgage foreclosure surpluses sit in the circuit court civil registry following final judgment and certificate of disbursements.

In every morning report, each record identifies the funds custodian, auction origin, and claim expiration window so your team doesn't have to cross-check which registry holds the deposit.

We publish the updated dockets every business morning at 7:00 AM EST in standard CSV, Excel, and JSON ($249/month flat, cancel anytime). You can activate access for your firm here:
{STRIPE_LINK}

Let me know if your office focuses specifically on tax deeds or if you also litigate mortgage surplus motions.

{signature}"""

    elif intent == "PROBATE_HEIR_RECOVERY":
        body = f"""{greeting}

Thanks for asking. In roughly 35% of the tax deed and foreclosure surplus files we index, the former record titleholder is deceased.

When our desk identifies an estate or deceased owner, we tag the file specifically so probate and heir recovery counsel can review it immediately. In many states, excess proceeds from deceased owners sit unclaimed in the {custodian} until an ancillary or formal probate is opened. Under {statute_cite}, heirs have a limited statutory window ({claim_window}) before funds escheat under state unclaimed property statutes. Statutory priority strictly favors verifiable heirs over junior judgment creditors: {priority_rules}.

Each morning feed flags estate files and provides the decedent's record name, situs address, parcel ID, and direct links to the clerk's docket so your team can verify probate status and file petitions for determination of heirs.

We publish the compiled feed every business morning at 7:00 AM EST in CSV and Excel ($249/month flat, cancel anytime):
{STRIPE_LINK}

Let me know if you'd like me to pull a sample batch of recent estate and heir files from our {state_name} index.

{signature}"""

    elif intent == "TITLE_LIEN_SCRUBBING":
        body = f"""{greeting}

Thanks for asking—upstream title examination is the core foundation of our indexing desk.

The biggest issue with raw clerk overage sheets is that 60% to 70% of apparent surpluses are completely consumed by senior encumbrances. A property might show $100,000 in excess auction proceeds, but if there's an unsatisfied first mortgage, an IRS lien, or an HOA super-priority lien, there is zero recoverable equity for the former owner or heirs.

Our research desk cross-references recorded deeds, mortgages, and lis pendens against the certificate of disbursements. If a senior bank mortgage or municipal lien wipes out the fund, we purge the file before delivery. Your attorneys only receive dockets with verified, claimable equity under {statute_cite}.

The verified feed goes out at 7:00 AM EST every business day in CSV, Excel, and JSON ($249/month flat):
{STRIPE_LINK}

Let me know if you'd like me to send over a sample extract showing our lien screening columns for {state_name}.

{signature}"""

    elif intent == "DATA_FRESHNESS_TIMING":
        body = f"""{greeting}

Thanks for asking about our turnaround time.

Our crawlers reconcile county clerk dockets overnight as certificates of disbursements and certificates of title are entered into the court record.

We publish the compiled feed every business morning at 7:00 AM EST. That typically puts verified records in your hands within 24 to 48 hours of the funds being deposited with the clerk's registry—well before unrepresented asset locators begin mailing or the county publishes monthly summary sheets.

Subscriptions are $249/month flat for your entire office, with month-to-month billing and no annual contract:
{STRIPE_LINK}

Let me know if you'd like me to pull the latest filings from {state_name} so you can review our current filing dates.

{signature}"""

    elif intent == "SKIP_TRACING_CONTACT":
        body = f"""{greeting}

Thanks for following up. We provide the verified record titleholder/estate name, property situs address, parcel identification number, and recorded deed history.

We intentionally do not provide consumer phone numbers or cold-call lists. Most state bar associations—including Florida Bar Rule 4-7.18 and equivalent rules—strictly regulate direct telephone solicitation of distressed property owners and surplus claimants. 

Instead, our data is structured for compliant, professional attorney direct mail and legal notice consultation. We also provide our Asset Recovery Legal Toolkit (client intake agreements, statutory fee disclosures, and heir representation contracts) so your practice can initiate outreach cleanly and within Bar guidelines.

Morning delivery across all circuits is $249/month flat, cancel anytime:
{STRIPE_LINK}

Let me know if you have any questions about how our partner firms handle their initial client contact workflows in {state_name}.

{signature}"""

    elif intent == "LEGAL_TOOLKIT_MOTIONS":
        body = f"""{greeting}

Yes, all subscriptions include full access to our Asset Recovery Legal Toolkit at no additional charge.

The toolkit provides court-ready pleading templates and client documentation drafted for practice under {statute_cite}, including:
- Verified Petition for Distribution of Surplus Funds ({toolkit_motion})
- Owner / Heir Affidavit of Claim and Non-Assignment
- Notice of Appearance and Motion for Evidentiary Hearing on Surplus
- Heir Representation Retainer Agreement & Statutory Fee Disclosure
- Standard Certificate of Service and Proposed Order of Disbursement

These documents are provided in editable Word (.docx) format so your team can adapt them to your firm's caption and local administrative orders.

Subscription access is $249/month flat for your entire firm (no per-seat or download charges):
{STRIPE_LINK}

Let me know if you'd like me to send over an example petition template along with today's {state_name} docket sample.

{signature}"""

    elif intent == "JURISDICTION":
        if county_name and circuit_name:
            jurisdiction_line = f"Yes, we actively monitor {county_name} County ({circuit_name}) as part of our statewide {state_name} feed."
        elif county_name:
            jurisdiction_line = f"Yes, we actively monitor {county_name} County as part of our statewide {state_name} feed."
        else:
            jurisdiction_line = f"We monitor county clerk registries and tax collector excess proceeds daily across all major judicial circuits in {state_name}."

        matching_sample = ""
        if county_name:
            matching = [c for c in cases if county_name.lower() in c["county"].lower()]
            if matching:
                c = matching[0]
                matching_sample = f"\nFor reference, in our current {county_name} County index, Docket {c['case_no']} has an unencumbered surplus balance of ${c['balance']:,.0f} subject to claim under {statute_cite}.\n"

        if not matching_sample and cases:
            sample_lines = format_sample_records(cases)
            sample_section = f"\nHere are a few active records from our current {state_name} index:\n{sample_lines}\n"
        else:
            sample_section = matching_sample

        body = f"""{greeting}

Thanks for reaching out regarding coverage.

{jurisdiction_line}

Before publishing, we cross-reference public records to filter out senior bank mortgages and municipal liens upstream. Your attorneys only receive verified equity balances with active statutory filing windows under {statute_cite}.
{sample_section}
Standardized feeds are delivered every business morning at 7:00 AM EST in CSV, Excel, and JSON ($249/month flat, cancel anytime):
{STRIPE_LINK}

If there are any additional counties or circuits your firm handles, let me know and I'll be glad to confirm our active volume there.

{signature}"""

    elif intent == "DATA_FORMAT":
        body = f"""{greeting}

Thanks for asking about our technical delivery options.

We deliver the morning feed at 7:00 AM EST in two standard formats designed for immediate intake:

First, standard .CSV and Excel (.xlsx) files formatted for direct import into practice management platforms like Clio, Filevine, or Smokeball without column remapping. Fields include Court Docket / Tax Deed Number, County, Judicial Circuit, Verified Surplus Balance, Sale Date, Prior Owner / Estate, Situs Address, and a direct verification link to the clerk's portal.

Second, a structured REST JSON endpoint for firms running automated intake workflows or webhooks.

Access is $249/month flat across all circuits:
{STRIPE_LINK}

I'd be glad to share our JSON schema or a sample CSV extract if your intake team would like to inspect the fields.

{signature}"""

    elif intent == "SAMPLE_DATA":
        sample_lines = format_sample_records(cases)
        body = f"""{greeting}

Thanks for getting back to me.

Here are a few verified surplus files from our current {state_name} index with senior bank encumbrances filtered out:

{sample_lines}

We compile court overages daily and deliver the standardized report every business morning at 7:00 AM EST in CSV, Excel, and JSON ($249/month flat, cancel anytime).

You can activate daily delivery directly for your office here:
{STRIPE_LINK}

Let me know if you'd like me to pull files for any specific county or judicial circuit in {state_name}.

{signature}"""

    elif intent == "PRICING":
        body = f"""{greeting}

Thanks for following up on pricing.

Our subscription is a flat $249/month for your entire practice—there are no per-lead fees, no contingency cuts, and no annual contracts. 

We also offer a 7-day complimentary practice evaluation for counsel of record ($0 due today with card on file). Your office receives 7 full business days of live 7:00 AM EST morning docket feeds. If your practice decides to maintain uninterrupted delivery, it transitions to $249/month on Day 8, and you can cancel anytime with 1 click in our self-service Stripe portal.

Given that a typical surplus recovery in {state_name} yields $10,000 to $15,000 in statutory fees for counsel under {statute_cite}, a single successful petition covers several years of subscription access.

You can activate your 7-day practice evaluation directly here:
{STRIPE_LINK}

Let me know if your firm requires an invoice for accounting rather than standard card billing.

{signature}"""

    else:  # GENERAL
        body = f"""{greeting}

Thanks for following up with our research desk.

Surplus Docket compiles verified tax deed and foreclosure surplus records directly from county clerk registries across {state_name} every business day.

The primary difference between our feed and the raw clerk notices is upstream title screening. We cross-reference deeds and encumbrances to drop files where senior mortgages or second mortgages consume the equity, so your attorneys only spend time on actionable surplus balances under {statute_cite}.

The feed is delivered every morning at 7:00 AM EST in CSV and Excel format ($249/month flat, cancel anytime):
{STRIPE_LINK}

Let me know if you have questions about specific circuits or if you'd like to review recent records for your primary counties.

{signature}"""

    reply_subject = subject_raw if subject_raw.lower().startswith("re:") else f"Re: {subject_raw}"
    if intent != "OPT_OUT":
        body = f"{body}\n\n{LEGAL_DISCLAIMER}"
    return reply_subject, body


def parse_statutory_inquiry(subject_raw, text_body):
    """
    Parses statutory inquiry form submissions originating from surplusdocket.com/inquiry.html,
    modal inquiry forms, or forwarded email inquiries.
    """
    subj = subject_raw.strip()
    is_inquiry = any(k in subj for k in [
        "STATUTORY INQUIRY RECORD",
        "[Surplus Docket Inquiry]",
        "[Surplus Docket Modal Inquiry]",
        "Surplus Docket Public Record Request",
        "Surplus Docket Inquiry",
        "Surplus Docket Legal & Regulatory Inquiries",
    ]) or any(k in text_body for k in [
        "OFFICIAL STATUTORY INQUIRY RECORD",
        "SURPLUS DOCKET — LEGAL & STATUTORY CORRESPONDENCE MEMORANDUM",
        "TRANSMITTING PRACTITIONER / PARTY",
        "STATEMENT OF INQUIRY",
        "INQUIRY MEMORANDUM"
    ])

    if not is_inquiry:
        return None

    # 1. Extract Practitioner / Requester Name
    name = ""
    name_patterns = [
        r"(?:Name\s*/\s*Counsel|PRACTITIONER\s+NAME|Inquiring\s+Entity\s+Name|Counsel\s+Name|Requester\s+Name|Counsel|Name):\s*([^\r\n]+)",
        r"(?:^|\n)\s*Name:\s*([^\r\n]+)",
    ]
    for pat in name_patterns:
        m = re.search(pat, text_body, re.IGNORECASE)
        if m and m.group(1).strip():
            name = m.group(1).strip()
            break
    if not name:
        m_subj_name = re.search(r"\(([^)]+)\)\s*$", subj)
        if m_subj_name:
            name = m_subj_name.group(1).strip()

    # 2. Extract Direct Email
    email_addr = ""
    email_patterns = [
        r"(?:Direct\s+Email|WORK\s+EMAIL|Inquiring\s+Entity\s+Email|Work\s+Email|Counsel\s+Email|Requester\s+Email|Email(?:\s+Address)?):\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
        r"(?:^|\n)\s*Email:\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
    ]
    for pat in email_patterns:
        m = re.search(pat, text_body, re.IGNORECASE)
        if m and m.group(1).strip():
            email_addr = m.group(1).strip()
            break

    # 3. Extract Law Firm / Organization
    firm = ""
    firm_patterns = [
        r"(?:Firm\s*/\s*Org(?:anization)?|LAW\s+FIRM\s*/\s*ENTITY|Law\s+Firm|Organization|Company|Firm):\s*([^\r\n]+)",
    ]
    for pat in firm_patterns:
        m = re.search(pat, text_body, re.IGNORECASE)
        if m and m.group(1).strip():
            cand = m.group(1).strip()
            if cand.lower() not in ["none specified", "not specified", "independent practice", "n/a", "none"]:
                firm = cand
            break
    if not firm:
        m_subj_firm = re.search(r"—\s*([^—(\n]+)\s*\([^)]+\)\s*$", subj)
        if m_subj_firm:
            cand = m_subj_firm.group(1).strip()
            if cand.lower() not in ["direct", "independent practice", "n/a", "none"]:
                firm = cand

    # 4. Extract Department / Inquiry Category
    department = "General Publisher Inquiry"
    dept_patterns = [
        r"(?:Inquiry\s+Category|Department|DEPARTMENT|Category):\s*([^\r\n]+)",
    ]
    for pat in dept_patterns:
        m = re.search(pat, text_body, re.IGNORECASE)
        if m and m.group(1).strip():
            department = m.group(1).strip()
            break
    if department == "General Publisher Inquiry":
        m_subj_dept = re.search(r"\[Surplus Docket Inquiry\]\s*([^—–\(\n]+)", subj)
        if m_subj_dept:
            department = m_subj_dept.group(1).strip()

    # 5. Extract Jurisdiction and State Code
    jurisdiction = "Multi-Jurisdiction / National"
    jur_patterns = [
        r"(?:Practice\s+Jurisdiction|Jurisdiction|JURISDICTION|State):\s*([^\r\n]+)",
    ]
    for pat in jur_patterns:
        m = re.search(pat, text_body, re.IGNORECASE)
        if m and m.group(1).strip():
            jurisdiction = m.group(1).strip()
            break

    state_code = ""
    if jurisdiction and jurisdiction.lower() not in ["multi-jurisdiction / national", "other jurisdiction / agency", "all jurisdictions"]:
        for code, s_name in STATE_NAMES.items():
            if s_name.lower() in jurisdiction.lower() or f"({code.lower()}" in jurisdiction.lower() or code.lower() == jurisdiction.strip().lower():
                state_code = code
                break

    if not state_code:
        jur_text = (subj + " " + text_body).lower()
        for code, s_name in STATE_NAMES.items():
            if s_name.lower() in jur_text or f"({code.lower()}" in jur_text or f"[{code.lower()}" in jur_text:
                state_code = code
                break

    if not state_code:
        state_code = "FL"

    # 6. Extract Docket / Parcel ID
    docket = ""
    docket_patterns = [
        r"(?:Docket\s*/\s*Parcel(?:\s+ID)?|DOCKET\s*/\s*PARCEL|Docket(?:\s+Number)?|Parcel\s+ID):\s*([^\r\n]+)",
    ]
    for pat in docket_patterns:
        m = re.search(pat, text_body, re.IGNORECASE)
        if m and m.group(1).strip():
            cand = m.group(1).strip()
            if cand.lower() not in ["not specified", "none specified", "n/a", "none"]:
                docket = cand
            break

    # 7. Extract Tracking / Reference Number
    ref_num = ""
    ref_patterns = [
        r"(?:Tracking\s+Ref|OFFICIAL\s+RECORD|Reference(?:\s+Number)?):\s*([^\r\n]+)",
    ]
    for pat in ref_patterns:
        m = re.search(pat, text_body, re.IGNORECASE)
        if m and m.group(1).strip():
            ref_num = m.group(1).strip()
            break

    # 8. Extract Message / Statement of Inquiry
    msg_text = ""
    msg_patterns = [
        r"(?:STATEMENT\s+OF\s+INQUIRY|Statement\s+of\s+Inquiry|INQUIRY\s+MEMORANDUM):\s*[\r\n]+([\s\S]+?)(?:\n[-=]{10,}|\nSurplus Docket Legal|\Z)",
        r"(?:^|\n)\s*Message:\s*([\s\S]+?)(?:\n[-=]{10,}|\nSurplus Docket Legal|\Z)",
    ]
    for pat in msg_patterns:
        m = re.search(pat, text_body, re.IGNORECASE)
        if m and m.group(1).strip():
            msg_text = m.group(1).strip()
            break
    if not msg_text:
        m_fallback = re.search(r"Message:\s*(.+)", text_body, re.DOTALL)
        if m_fallback:
            msg_text = m_fallback.group(1).strip()

    return {
        "name": name,
        "email": email_addr,
        "firm": firm,
        "department": department,
        "jurisdiction": jurisdiction,
        "state_code": state_code,
        "docket": docket,
        "ref": ref_num,
        "message": msg_text,
    }


def extract_spoken_email(text):
    """
    Extracts and normalizes email addresses from spoken audio transcripts
    and Google Voice speech-to-text outputs.
    Handles:
    - Standard literal email: 'john@example.com'
    - Spoken cues with provider: 'my email address is sandwich fitnessgmailcom' -> sandwichfitness@gmail.com
    - Spoken with spaces: 'sandwich fitness gmail com' -> sandwichfitness@gmail.com
    - Spoken 'at' and 'dot': 'john dot doe at legalfirm dot com' -> john.doe@legalfirm.com
    """
    if not text:
        return ""
    text = text.strip()

    # 1. Standard literal email address regex
    m = re.search(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b", text)
    if m:
        return m.group(0).lower().strip()

    known_tlds = r"(?:com|org|net|edu|gov|io|co|us)"
    known_providers = r"(?:gmail|yahoo|outlook|hotmail|icloud|aol|proton|protonmail|comcast|sbcglobal|att|verizon|zoho)"

    # 2. Spoken with explicit email cue: "email is ...", "email address is ...", "email me at ..."
    cue_pattern = re.search(
        rf"(?:my\s+)?email(?:\s+address)?(?:\s+is|\s*:|\s+me\s+at|\s+at|\s+to)?\s+(?:the\s+)?([a-zA-Z0-9\s._-]+?)(?:\s*(?:@|at)\s*|\s+)?({known_providers})\s*(?:dot|\.|\s*)?({known_tlds})\b",
        text,
        re.IGNORECASE
    )
    if cue_pattern:
        raw_user = cue_pattern.group(1).strip()
        provider = cue_pattern.group(2).strip().lower()
        tld = cue_pattern.group(3).strip().lower()
        stopwords = {"the", "is", "my", "a", "an", "me", "to", "at", "it", "its", "address"}
        words = [w for w in re.split(r"[\s_]+", raw_user) if w and w.lower() not in stopwords]
        user_clean = "".join(words).lower()
        if user_clean:
            return f"{user_clean}@{provider}.{tld}"

    # 3. Merged format without explicit cue: "sandwich fitnessgmailcom" or "sandwichfitnessgmailcom"
    merged_pattern = re.search(
        rf"\b([a-zA-Z0-9]+(?:\s+[a-zA-Z0-9]+){{0,2}})\s*({known_providers})({known_tlds})\b",
        text,
        re.IGNORECASE
    )
    if merged_pattern:
        raw_user = merged_pattern.group(1).strip()
        provider = merged_pattern.group(2).strip().lower()
        tld = merged_pattern.group(3).strip().lower()
        stopwords = {"the", "is", "my", "email", "address", "to", "at", "me", "for", "in"}
        words = [w for w in re.split(r"[\s_]+", raw_user) if w and w.lower() not in stopwords]
        user_clean = "".join(words).lower()
        if user_clean:
            return f"{user_clean}@{provider}.{tld}"

    # 4. Spoken with "dot" and "at" (custom domain, e.g. "john dot doe at lawfirm dot com")
    at_dot_pattern = re.search(
        r"(?:my\s+)?email(?:\s+address)?(?:\s+is|\s*:|\s+me\s+at|\s+at|\s+to)?\s*(?:the\s+)?([a-zA-Z0-9]+(?:\s*(?:dot|\.)\s*[a-zA-Z0-9]+)*)\s+(?:at|@)\s+([a-zA-Z0-9-]+)\s+(?:dot|\.)\s+([a-zA-Z]{2,})\b",
        text,
        re.IGNORECASE
    )
    if at_dot_pattern:
        raw_user = at_dot_pattern.group(1).strip()
        domain = at_dot_pattern.group(2).strip().lower()
        tld = at_dot_pattern.group(3).strip().lower()
        user_clean = re.sub(r"\s*dot\s*", ".", raw_user, flags=re.IGNORECASE)
        stopwords = {"the", "is", "my", "a", "an", "me", "to", "at", "address"}
        words = [w for w in re.split(r"[\s_]+", user_clean) if w and w.lower() not in stopwords]
        clean_name = "".join(words).lower()
        if clean_name:
            return f"{clean_name}@{domain}.{tld}"

    return ""


def parse_google_voice_voicemail(sender_email, subject_raw, text_body):
    """
    Parses Google Voice voicemail notification emails forwarding to sandwichfitness@gmail.com
    originating from Surplus Docket's inbound line (508) 419-3178.
    Extracts caller phone, transcript, mentioned jurisdiction, and intent.
    """
    s_lower = (sender_email or "").lower().strip()
    subj_lower = (subject_raw or "").lower().strip()

    is_gv = (
        "voice-noreply@google.com" in s_lower or
        "google voice" in s_lower or
        "new voicemail from" in subj_lower or
        "voicemail from" in subj_lower
    )
    if not is_gv:
        return None

    # 1. Extract phone number
    phone_match = re.search(r"(\+?1?[\s\.-]?\(?\d{3}\)?[\s\.-]?\d{3}[\s\.-]?\d{4})", f"{subject_raw} {text_body}")
    caller_phone = phone_match.group(1).strip() if phone_match else "Unknown Caller"

    # 2. Extract transcript
    lines = text_body.splitlines()
    capturing = False
    captured = []
    for line in lines:
        l = line.strip()
        if any(k in l.lower() for k in ["new voicemail from", "voicemail from"]):
            capturing = True
            continue
        if capturing:
            if any(k in l.lower() for k in ["play message", "call back", "google voice", "play audio", "help center"]):
                break
            if l:
                captured.append(l)

    transcript = " ".join(captured).strip() if captured else text_body.strip()

    # 3. Detect attorney email if spoken or present
    caller_email = extract_spoken_email(transcript)

    # 4. Extract jurisdiction
    det_state, c_name, c_circ = extract_jurisdiction_context(subject_raw, transcript, default_state="FL")
    state_name = STATE_NAMES.get(det_state, "Florida")

    # 5. Extract caller name if stated
    clean_text = re.sub(r"\bmy name\s+my name is\b", "my name is", transcript, flags=re.IGNORECASE)
    stopwords = r"(?!my\b|our\b|can\b|could\b|just\b|email\b|phone\b|with\b|from\b|and\b|the\b|at\b)"
    delims = r"(?:\s+(?:can\s+you|can|could|my|our|email|phone|number|just|calling|from|with|regarding|about|at)\b|[.,;!?\n]|$)"
    name_match = re.search(
        rf"(?:this is|my name is|i\x27m|im|i am|calling is)\s+({stopwords}[A-Za-z]+(?:\s+{stopwords}[A-Za-z]+){{0,2}}){delims}",
        clean_text,
        re.IGNORECASE
    )
    if name_match:
        cand = name_match.group(1).strip().title()
        stop = {"a", "an", "the", "someone", "unknown", "calling", "just"}
        if cand.lower() not in stop and len(cand.split()) <= 3:
            caller_name = cand
        else:
            caller_name = f"Inquiring Counsel ({caller_phone})"
    else:
        caller_name = f"Inquiring Counsel ({caller_phone})"

    ref_hash = abs(hash(transcript[:60])) % 1000000
    return {
        "name": caller_name,
        "email": caller_email,
        "phone": caller_phone,
        "firm": "",
        "department": "Inquiries & Intake Desk",
        "jurisdiction": state_name,
        "state_code": det_state,
        "docket": "",
        "ref": f"GV-VM-{caller_phone}-{ref_hash}",
        "message": f"[Phone Inquiry via Google Voice (508) 419-3178]: {transcript}",
        "is_voicemail": True,
    }


def compose_elena_inquiry_response(inquiry_info, state_cases):
    """
    Drafts an authoritative, tailored response to a statutory website inquiry
    originating from surplusdocket.com/inquiry.html or incoming email inquiry.
    Dynamically adjusts role, greeting, citations, benchmarks, and answers.
    """
    raw_name = inquiry_info.get("name", "").strip()
    first_name = ""
    if raw_name:
        parts = [p.strip() for p in raw_name.split() if p.strip()]
        if parts and parts[0].title().lower() not in BANNED_FIRST_NAMES:
            first_name = parts[0].title()

    firm = inquiry_info.get("firm", "").strip()
    if first_name:
        greeting = f"Hi {first_name},"
    elif firm:
        greeting = f"Hello {firm} team,"
    else:
        greeting = "Hello,"

    department = inquiry_info.get("department", "General Publisher Inquiry").strip()
    state_code = inquiry_info.get("state_code", "FL").strip().upper()
    state_name = STATE_NAMES.get(state_code, "Florida")
    statute_cite = STATE_STATUTES.get(state_code, (state_name, "applicable state civil code"))[1]
    stat_entry = JURISDICTION_STATUTORY_KNOWLEDGE.get(state_code, JURISDICTION_STATUTORY_KNOWLEDGE["FL"])
    claim_window = stat_entry.get("claim_window", "designated statutory claim window")
    custodian = stat_entry.get("custodian", "court or county registry")
    user_message = inquiry_info.get("message", "").strip()
    docket_ref = inquiry_info.get("docket", "").strip()
    _, detected_county, circuit_name = extract_jurisdiction_context(
        subject_raw=docket_ref, text_body=user_message, default_state=state_code
    )
    cases = state_cases.get(state_code, state_cases.get("FL", []))
    sample_lines = format_sample_records(cases, target_county=detected_county)

    persona = get_department_persona(department=department)
    role_title = persona["full_title"]
    signature = get_employee_signature(persona=persona)

    # Contextual additions based on user inquiry queries
    bar_note = ""
    if any(k in user_message.lower() for k in ["phone", "skip trace", "cold call", "contact info", "call the owner"]):
        bar_note = f"\n\nRegarding owner contact information: we intentionally do not provide consumer phone numbers or cold-call lists. Most state bar associations—including Florida Bar Rule 4-7.18 and equivalent rules across {state_name}—strictly regulate direct telephone solicitation of distressed property owners and surplus claimants. Instead, our feed delivers verified record owner and estate names, property situs addresses, parcel IDs, and recorded deed history so counsel can utilize compliant direct written correspondence."

    tyler_note = ""
    if any(k in user_message.lower() for k in ["tyler", "hennepin", "supreme court", "scotus", "takings clause"]):
        tyler_note = f"\n\nRegarding Tyler v. Hennepin County (598 U.S. 631): the Supreme Court's unanimous ruling established that county governments cannot retain property equity exceeding delinquent tax debt under the Fifth Amendment. In {state_name}, this has established clearer court registry deposit procedures under {statute_cite}, requiring former owners and lienholders to petition for surplus funds within {claim_window}."

    upl_note = ""
    if any(k in user_message.lower() for k in ["represent me", "my case", "hire you", "file my claim", "need a lawyer", "need an attorney"]):
        upl_note = f"\n\nImportant Notice: Surplus Docket is an independent court records compiler and technology provider for licensed counsel and recovery professionals—we are not a law firm and do not provide legal representation or file petitions on behalf of property owners. All formal recovery claims must be evaluated and filed by licensed legal counsel admitted to practice in {state_name}."

    dept_lower = department.lower()

    # 1. 7-Day Institutional Practice Evaluation
    if any(k in dept_lower for k in ["evaluation", "7-day", "trial", "onboarding"]):
        is_expansion = state_code in ["NC", "TN", "CA"]
        if is_expansion:
            tier_note = f"Records for {state_name} are compiled and delivered under our National Feed + REST API Tier ($449/month, covering FL, TX, GA, NC, TN, and CA with priority 6:00 AM EST dispatch and live REST API Bearer tokens)."
            checkout_url = "https://buy.stripe.com/9B68wP9Cu7ndfqlfgy0ZW1Y"
        else:
            tier_note = f"Under our Tri-State Core Feed plan, coverage includes Florida, Texas, and Georgia for a flat $249/month starting on Day 8. There are no per-claim charges, no long-term contracts, and you can cancel anytime with one click through your self-service Stripe billing portal."
            checkout_url = STRIPE_LINK

        reply_subject = f"Re: Surplus Docket — 7-Day Practice Evaluation [{state_name}]"
        reply_body = f"""{greeting}

Thank you for requesting an institutional practice evaluation of Surplus Docket for {state_name}.

Your 7-day evaluation is activated with $0 due today. During the evaluation, your practice receives our full morning feed delivered directly to your inbox every business morning at 7:00 AM EST in both CSV and Excel formats.

Here are verified, active records from our current {state_name} index (with senior institutional mortgages scrubbed upstream):

{sample_lines}

{tier_note}

You can initialize your evaluation directly here:
{checkout_url}
{bar_note}{tyler_note}{upl_note}

Please let me know if your team needs specific judicial circuit filtering, statutory guidelines under {statute_cite}, or sample dossiers for {state_name}.

{signature}

{LEGAL_DISCLAIMER}"""

    # 2. Enterprise Feed Licensing
    elif any(k in dept_lower for k in ["enterprise", "licensing", "custom feed", "multi-jurisdiction"]):
        reply_subject = f"Re: Surplus Docket — Enterprise & Multi-Jurisdiction Feed Licensing"
        reply_body = f"""{greeting}

Thank you for your inquiry regarding enterprise and multi-jurisdiction feed licensing with Surplus Docket.

For practices requiring comprehensive multi-state coverage and direct data ingestion, we offer our National Feed + REST API Tier ($449/month):
- Full 6-State Coverage: Florida, Texas, Georgia, North Carolina, Tennessee, and California.
- Priority Morning Dispatch: Feeds delivered at 6:00 AM EST (one hour ahead of standard distribution).
- Direct REST API Access: Bearer-token authenticated endpoints (/api/v1/*.json) for automated pipeline and CRM ingestion.
- Enterprise Multi-Seat Access: Unlimited distribution across your firm's attorneys and paralegals.

Here is a verified sample from our current {state_name} docket index:

{sample_lines}

You can activate the National Feed + REST API tier directly here:
https://buy.stripe.com/9B68wP9Cu7ndfqlfgy0ZW1Y
{bar_note}{tyler_note}{upl_note}

If your firm requires custom high-surplus thresholding (e.g., filtering exclusively for files exceeding $50k or $100k) or specialized billing arrangements, I would be glad to set that up for your file.

{signature}

{LEGAL_DISCLAIMER}"""

    # 3. Law Practice API Integration
    elif any(k in dept_lower for k in ["api", "integration", "developer", "technical", "rest", "webhook"]):
        reply_subject = f"Re: Surplus Docket — REST API & Practice Management Integration"
        reply_body = f"""{greeting}

Thank you for reaching out regarding REST API and practice management integration with Surplus Docket.

Our Developer REST API is designed for programmatic legal practice management integration (including Clio, Filevine, Smokeball, or internal SQL databases):
- Standard Endpoints: Available in JSON format at /api/v1/*.json (including state-specific feeds for FL, TX, GA, NC, TN, CA and consolidated master feed).
- Authentication: Secure HTTP header authentication using standard Bearer tokens (Authorization: Bearer <API_TOKEN>).
- Daily Data Pipeline: Feeds update automatically every business morning by 6:00 AM EST with complete court docket references, parcel IDs, clean equity calculations, and county registry links.
- Interactive Documentation: Complete schema specifications and endpoint parameters are published at https://surplusdocket.com/api-documentation.html.

API access is provisioned under our National Feed + REST API Tier ($449/month):
https://buy.stripe.com/9B68wP9Cu7ndfqlfgy0ZW1Y
{bar_note}{tyler_note}{upl_note}

Let me know what system your practice is currently integrating with, and I can provide sample JSON schemas or webhook recommendations for your developers.

{signature}

{LEGAL_DISCLAIMER}"""

    # 4. Clerk Docket Correction / Notice
    elif any(k in dept_lower for k in ["clerk", "correction", "notice", "registry", "court reporter"]):
        docket_clause = f"regarding file/docket {docket_ref}" if docket_ref else f"for {state_name}"
        reply_subject = f"Re: Surplus Docket — County Registry Record Verification & Notice [{docket_ref or state_name}]"
        reply_body = f"""{greeting}

Thank you for contacting Surplus Docket {docket_clause}.

We take county registry accuracy, certificate reconciliation, and statutory notice requirements with highest judicial deference and priority. Our operations desk cross-references clerk disbursement ledgers, court registry certificates, and subsequent claim petitions every business morning to maintain 100% fidelity with official public records.

If your notice concerns a specific certificate of disbursement, an amended surplus balance, or an entered order of distribution, please reply with the certificate number or docket reference so our compiler desk can update and reconcile the file across our daily index immediately.

We greatly appreciate the collaboration of county clerk offices and court administrators in ensuring public records integrity.

{signature}

{LEGAL_DISCLAIMER}"""

    # 5. Statutory Compliance Verification
    elif any(k in dept_lower for k in ["compliance", "statutory", "senior lien", "title", "encumbrance"]):
        reply_subject = f"Re: Surplus Docket — Statutory Compliance & Title Verification [{state_name}]"
        reply_body = f"""{greeting}

Thank you for reaching out regarding statutory compliance and title verification standards for {state_name}.

Raw county surplus ledgers often list gross excess proceeds without accounting for superior encumbrances. Our data compiler desk applies multi-layered title and institutional lien scrubbing upstream:
- Senior Institutional Encumbrances: We cross-reference county deed records and lis pendens filings to purge files encumbered by unreleased senior institutional mortgages or senior deeds of trust.
- Verified Clean Equity: Feeds isolate unencumbered equity balances where the surplus deposited with the {custodian} exceeds recorded senior claims.
- Statutory Deadlines: Files are tracked against state limitation periods ({statute_cite} designated {claim_window}) before escheatment.

Here is an excerpt of active, verified files currently indexed in {state_name}:

{sample_lines}

Surplus Docket operates strictly as an independent court records compiler and does not provide formal legal opinions or legal representation; all formal surplus distribution petitions must be verified and filed by licensed counsel.
{bar_note}{tyler_note}{upl_note}

Please let me know if you would like to review our title scrubbing methodology for specific judicial circuits in {state_name}.

{signature}

{LEGAL_DISCLAIMER}"""

    # 6. Press / Academic Research
    elif any(k in dept_lower for k in ["press", "academic", "media", "journalist", "research"]):
        reply_subject = f"Re: Surplus Docket — Public Records & Academic Research Inquiry"
        reply_body = f"""{greeting}

Thank you for contacting Surplus Docket regarding your research inquiry.

Surplus Docket compiles and monitors public record excess proceeds across judicial circuits and county clerk registries. Our indexing focuses on post-foreclosure property equity and statutory claim windows under state codes and constitutional standards established by the Supreme Court in Tyler v. Hennepin County, 598 U.S. 631 (2023).

We frequently assist academic researchers, journalists, and legal scholars by providing aggregated public data sets, statutory timeline comparisons, and municipal surplus retention analytics across our covered jurisdictions.

Please reply with the specific scope, academic institution, or research parameters you are examining, and our research desk will be glad to compile relevant non-confidential public record data for your analysis.

{signature}

{LEGAL_DISCLAIMER}"""

    # 7. Inquiries & Intake Desk (Aubrey Hayes Executive Intake)
    elif any(k in dept_lower for k in ["intake", "aubrey", "voicemail", "inquiries"]):
        # Conditionally rope in Elena Brooks ONLY if the inquiry content justifies it:
        # Justified strictly when:
        # 1. Specific court docket, case number, or parcel ID is provided.
        # 2. Inquirer explicitly asks for docket lookup, case evaluation, lien/mortgage priority,
        #    court registry deposit research, or statutory petition filings.
        has_specific_docket = bool(docket_ref) or bool(
            re.search(r"\b(\d{2,4}[-\s][A-Za-z]{1,4}[-\s]\d{3,}|\d{4,}[-\s]\d{2,}|\b[A-Za-z]{1,3}\d{6,}\b|\bF-\d{4,}\b|\b\d{2,4}-CA-\d+|\b\d{2,4}-CC-\d+)\b", user_message)
        )
        statutory_keywords = [
            "docket search", "case search", "case lookup", "docket lookup", "look up docket",
            "pull filing", "pull the filing", "lien search", "mortgage priority", "title search",
            "petition for distribution", "certificate of disbursement", "interpleader", "registry deposit",
            "escheatment search", "case status", "docket status"
        ]
        msg_lower = user_message.lower()
        has_statutory_need = any(k in msg_lower for k in statutory_keywords)
        justifies_elena = has_specific_docket or has_statutory_need

        is_vm = bool(inquiry_info.get("is_voicemail"))
        is_overview = any(k in msg_lower for k in [
            "overview", "what you offer", "what do you offer", "different places",
            "services", "how does it work", "tell me about", "what is surplus docket",
            "explain your service", "coverage"
        ])
        is_pricing = any(k in msg_lower for k in [
            "pricing", "price", "cost", "how much", "rate", "fee", "subscription",
            "how much is", "what does it cost", "plan", "trial", "evaluation"
        ])
        is_delivery = any(k in msg_lower for k in [
            "what time", "delivery", "when do you send", "csv", "excel", "spreadsheet",
            "schedule", "format", "ingest", "filevine", "clio", "crm"
        ])
        is_title = any(k in msg_lower for k in [
            "mortgage", "senior lien", "bank lien", "scrub", "encumbrance",
            "clean equity", "first mortgage", "deed of trust", "title"
        ])
        is_probate = any(k in msg_lower for k in [
            "probate", "heir", "deceased", "estate", "intestate", "heirs", "heirship"
        ])

        if justifies_elena:
            reply_subject = f"Re: Surplus Docket — Docket Research & Intake [{docket_ref or state_name}]"
        else:
            reply_subject = f"Re: Surplus Docket — Court Surplus Feeds [{state_name}]"

        # Context-aware opening tailored to channel and user inquiry
        if is_vm:
            if is_overview:
                if detected_county:
                    opening_paragraph = (
                        f"Thank you for your voicemail earlier today requesting an overview of our surplus feeds "
                        f"and coverage for {detected_county} County and across {state_name}."
                    )
                elif state_name:
                    opening_paragraph = (
                        f"Thank you for your voicemail earlier today requesting an overview of what we offer "
                        f"across different jurisdictions in {state_name}."
                    )
                else:
                    opening_paragraph = (
                        "Thank you for your voicemail earlier today requesting an overview of our court surplus feeds and coverage."
                    )
            elif is_pricing or is_delivery:
                opening_paragraph = (
                    f"Thank you for your voicemail earlier today regarding delivery schedules and subscription pricing "
                    f"for our {state_name} court surplus feeds."
                )
            elif has_specific_docket:
                docket_label = docket_ref or "your referenced case"
                opening_paragraph = (
                    f"Thank you for your voicemail earlier today regarding court records and filing details "
                    f"for docket {docket_label} in {state_name}."
                )
            else:
                opening_paragraph = (
                    f"Thank you for your voicemail earlier today regarding {state_name} public record excess proceeds."
                )
        else:
            if is_overview:
                if detected_county:
                    opening_paragraph = (
                        f"Thank you for reaching out to the Surplus Docket intake desk regarding our coverage "
                        f"in {detected_county} County and across {state_name}."
                    )
                else:
                    opening_paragraph = (
                        f"Thank you for reaching out to the Surplus Docket intake desk regarding an overview of our "
                        f"{state_name} public record excess proceeds feeds."
                    )
            elif is_pricing or is_delivery:
                opening_paragraph = (
                    f"Thank you for contacting our intake desk with your questions regarding delivery schedule "
                    f"and subscription details for {state_name}."
                )
            elif has_specific_docket:
                docket_label = docket_ref or "your referenced case"
                opening_paragraph = (
                    f"Thank you for contacting the Surplus Docket intake desk regarding docket {docket_label} in {state_name}."
                )
            else:
                opening_paragraph = (
                    f"Thank you for reaching out to the Surplus Docket intake desk regarding {state_name} public record excess proceeds."
                )

        if justifies_elena:
            docket_clause = f" regarding docket {docket_ref}" if docket_ref else ""
            status_paragraph = (
                f"Because your inquiry involves specific county court filings{docket_clause}, "
                f"I have forwarded your request to Elena Brooks on our docket research desk to review active registry balances in {state_name}."
            )
            followup_clause = (
                f"Elena will review your file and follow up directly regarding the specific court records for {state_name}. "
                f"If you have additional docket numbers or parcel references, please feel free to reply directly to this email."
            )
        else:
            status_paragraph = (
                f"Surplus Docket indexes and delivers verified court surplus records every business morning at 7:00 AM EST "
                f"in CSV and Excel formats, with senior institutional mortgages scrubbed upstream under {statute_cite}."
            )
            followup_clause = (
                f"If your practice requires coverage for a specific county or if you would like our research desk to pull active filings "
                f"for a specific docket or parcel ID, please reply with the case reference and our intake desk will pull the records for your review."
            )

        contextual_paragraphs = []

        if detected_county:
            county_context = (
                f"Regarding {detected_county} County ({circuit_name or 'local court registry'}): our compiler desk actively "
                f"monitors the {detected_county} County registry and court filings under {statute_cite}. In {state_name}, "
                f"surplus funds deposited with the {custodian} must be petitioned within {claim_window} before escheatment. "
                f"We have prioritized active records from {detected_county} County in the excerpt below so your practice can "
                f"evaluate current balances."
            )
            contextual_paragraphs.append(county_context)
        elif is_overview and not justifies_elena:
            jurisdiction_overview = (
                f"Across {state_name}, our operations desk monitors county clerk ledgers and court registries daily under "
                f"{statute_cite}, capturing excess proceeds from tax deed sales and foreclosure auctions. By reconciling "
                f"certificate disbursements against land records and cross-referencing recorded liens, we isolate actionable "
                f"files before the statutory claim window ({claim_window}) expires."
            )
            contextual_paragraphs.append(jurisdiction_overview)

        if is_delivery:
            delivery_context = (
                f"Regarding delivery schedule and file formats: feeds are dispatched every business morning at 7:00 AM EST "
                f"directly to your inbox. Each transmission includes both structured CSV and formatted Excel (.xlsx) workbooks "
                f"containing docket numbers, parcel IDs, auction dates, deposited amounts, and property situs addresses—ready "
                f"for immediate review or import into case management software like Clio, Filevine, or internal databases."
            )
            contextual_paragraphs.append(delivery_context)

        if is_title:
            title_context = (
                f"Regarding senior mortgage and encumbrance scrubbing: raw county ledgers frequently list gross surplus "
                f"amounts without accounting for first mortgages that would wipe out the recovery. Our compiler desk runs "
                f"upstream deed and lis pendens title checks to filter out unreleased senior institutional liens, ensuring our "
                f"daily feed contains only files with true unencumbered equity."
            )
            contextual_paragraphs.append(title_context)

        if is_probate:
            probate_context = (
                f"Regarding probate and heir recovery: our data indexing flags files where property ownership was held in "
                f"an estate, deceased individual, or intestate succession. When available, we include probate docket cross-references "
                f"to assist counsel in filing petitions for determination of heirship and letters of administration."
            )
            contextual_paragraphs.append(probate_context)

        if state_code in ["NC", "TN", "CA"]:
            pricing_clause = (
                f"For {state_name}, records are compiled under our National Feed + REST API Tier ($449/mo), covering FL, TX, GA, NC, TN, and CA "
                f"with priority 6:00 AM EST dispatch and live REST API Bearer tokens:\n"
                f"https://buy.stripe.com/9B68wP9Cu7ndfqlfgy0ZW1Y"
            )
        else:
            pricing_clause = (
                f"We offer two transparent subscriptions:\n"
                f"1. Tri-State Core Feed ($249/mo flat with 7-day evaluation $0 due today): Florida, Texas, and Georgia morning CSV & Excel delivery.\n"
                f"   {STRIPE_LINK}\n"
                f"2. National Feed + REST API ($449/mo): Full 6-state coverage (FL, TX, GA + NC, TN, CA) with priority 6:00 AM EST dispatch and live REST API Bearer tokens.\n"
                f"   https://buy.stripe.com/9B68wP9Cu7ndfqlfgy0ZW1Y"
            )

        body_sections = [
            greeting,
            opening_paragraph,
            status_paragraph,
        ]
        if contextual_paragraphs:
            body_sections.extend(contextual_paragraphs)

        body_sections.append(f"Here is an excerpt of active, verified files from our current {state_name} index:\n\n{sample_lines}")
        body_sections.append(pricing_clause)

        extra_notes = "".join(filter(None, [bar_note, tyler_note, upl_note])).strip()
        if extra_notes:
            body_sections.append(extra_notes)

        body_sections.append(followup_clause)
        body_sections.append(signature)
        body_sections.append(LEGAL_DISCLAIMER)

        reply_body = "\n\n".join(body_sections)

    # 8. General Publisher Inquiry / Default
    else:
        is_expansion = state_code in ["NC", "TN", "CA"]
        reply_subject = f"Re: Surplus Docket — Public Record Docket Inquiry [{state_name}]"
        reply_body = f"""{greeting}

Thank you for reaching out to Surplus Docket regarding {state_name} public record excess proceeds intelligence.

Surplus Docket indexes active, unencumbered surplus funds across county registries every business morning. We scrub raw county ledgers to purge senior bank mortgages and dead leads, delivering verified equity balances directly to counsel at 7:00 AM EST every Monday through Friday.

Here are sample active records from our current {state_name} index:

{sample_lines}

We offer two transparent subscriptions:
1. Tri-State Core Feed ($249/mo with 7-day trial $0 due today): Florida, Texas, and Georgia morning CSV & Excel delivery.
   {STRIPE_LINK}
2. National Feed + REST API ($449/mo): Complete 6-state coverage (FL, TX, GA + NC, TN, CA) with priority 6:00 AM EST dispatch and full REST API Bearer token access.
   https://buy.stripe.com/9B68wP9Cu7ndfqlfgy0ZW1Y
{bar_note}{tyler_note}{upl_note}

Please let me know if your practice requires specific county-level coverage or if you have questions about statutory procedures under {statute_cite}.

{signature}

{LEGAL_DISCLAIMER}"""

    return reply_subject, reply_body, role_title


def build_inquiry_draft_email(inquiry_info, state_cases, message_id=None):
    """
    Constructs a full MIMEText email draft response for a statutory inquiry.
    Returns: (draft_msg: MIMEText, reply_subject: str, reply_body: str, role_title: str)
    """
    prospect_name = inquiry_info.get("name", "").strip()
    prospect_email = inquiry_info.get("email", "").strip()
    department = inquiry_info.get("department", "General Publisher Inquiry").strip()
    persona = get_department_persona(department=department)
    reply_subject, reply_body, role_title = compose_elena_inquiry_response(inquiry_info, state_cases)

    if inquiry_info.get("is_voicemail"):
        phone_num = inquiry_info.get("phone", "")
        if phone_num:
            reply_subject = f"[Phone Inquiry Dossier — {phone_num}] {reply_subject}"

    now_epoch = time.time()
    draft_msg = MIMEText(reply_body, "plain", "utf-8")
    draft_msg["From"] = f"{persona['name']} <{persona['email']}>"
    draft_msg["To"] = f"{prospect_name} <{prospect_email}>" if prospect_name else prospect_email
    draft_msg["Subject"] = reply_subject
    draft_msg["Reply-To"] = f"{persona['name']} <{persona['email']}>"
    if message_id:
        draft_msg["In-Reply-To"] = message_id
        draft_msg["References"] = message_id
    draft_msg["Date"] = formatdate(now_epoch, localtime=True)
    draft_msg["Message-ID"] = make_msgid()

    return draft_msg, reply_subject, reply_body, role_title


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
    drafts_box = get_gmail_drafts_mailbox(mail)
    status, count = mail.select(drafts_box)
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


def sync_voicemails_to_inbox(mail):
    """
    Ensures any Google Voice voicemail notifications in [Gmail]/All Mail
    are present in INBOX so the user never misses an inbound voicemail.
    """
    try:
        status, _ = mail.select('"[Gmail]/All Mail"')
        if status != "OK":
            return
        status, messages = mail.search(None, '(FROM "voice-noreply@google.com")')
        if status != "OK" or not messages[0]:
            return
        gv_ids = messages[0].split()
        for mid in gv_ids[-15:]:
            res, data = mail.fetch(mid, "(X-GM-LABELS)")
            if res == "OK" and data and isinstance(data[0], tuple):
                raw_labels = data[0][0] if isinstance(data[0][0], (bytes, str)) else data[0][1]
                labels_str = raw_labels.decode("utf-8", errors="ignore") if isinstance(raw_labels, bytes) else str(raw_labels)
                if "\\Inbox" not in labels_str and "Inbox" not in labels_str:
                    mail.store(mid, "+X-GM-LABELS", r"(\Inbox)")
                    mail.copy(mid, "INBOX")
                    log(f"  📥 Auto-routed Google Voice voicemail {mid.decode() if isinstance(mid, bytes) else mid} from All Mail into INBOX.")
    except Exception as e:
        log(f"Notice during voicemail inbox sync: {e}")


def check_and_create_auto_responses(mail, state_cases, enforce_delay=True, enforce_hours=True):
    """
    Scans INBOX:
    1. Automatically detects and executes unsubscriptions for marketing/newsletters.
    2. Detects prospect replies from law firms and inquiries from surplusdocket.com or Google Voice.
    3. Auto-dispatches personalized responses via SMTP during business hours with human delay pacing.
    4. Records notable email/voicemail interactions for the Weekly Executive Report.
    """
    status, count = mail.select("INBOX")
    if status != "OK":
        return

    # Gather UNSEEN messages plus recent INBOX messages (last 25)
    candidate_ids = []
    seen_ids = set()

    status, unseen = mail.search(None, "UNSEEN")
    if status == "OK" and unseen[0]:
        for mid in unseen[0].split():
            if mid not in seen_ids:
                candidate_ids.append((mid, False))  # (mid, is_already_seen=False)
                seen_ids.add(mid)

    status, all_msgs = mail.search(None, "ALL")
    if status == "OK" and all_msgs[0]:
        all_ids = all_msgs[0].split()
        for mid in reversed(all_ids[-25:]):
            if mid not in seen_ids:
                candidate_ids.append((mid, True))  # (mid, is_already_seen=True)
                seen_ids.add(mid)

    if not candidate_ids:
        return

    directory, email_directory, target_domains = load_target_directory()
    already_unsubscribed = load_unsubscribed_urls()
    already_drafted = load_created_drafts()

    for mid, is_already_seen in candidate_ids:
        # Optimization: for messages already seen, quickly check header first to avoid unnecessary processing
        if is_already_seen:
            h_res, h_data = mail.fetch(mid, "(BODY[HEADER.FIELDS (FROM SUBJECT TO)])")
            if h_res != "OK" or not h_data or not isinstance(h_data[0], tuple):
                continue
            h_msg = email.message_from_bytes(h_data[0][1])
            h_from = decode_str(h_msg.get("From", "")).lower()
            h_subj = decode_str(h_msg.get("Subject", "")).lower()
            h_to = decode_str(h_msg.get("To", "")).lower()

            is_candidate = (
                "voice-noreply@google.com" in h_from or
                "google voice" in h_from or
                "formsubmit.co" in h_from or
                "surplusdocket.com" in h_to or
                "voicemail" in h_subj or
                "inquiry" in h_subj or
                "surplus docket" in h_subj
            )
            if not is_candidate:
                continue

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
        # 1. AUTO-UNSUBSCRIBE MODULE (Only for unread messages)
        # -------------------------------------------------------------
        if not is_already_seen:
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
        # 2. ELIGIBILITY & POLICY ENFORCEMENT (SD-POL-OUTREACH-2026-V1)
        # -------------------------------------------------------------
        is_eligible, reason, target_info, inquiry_info = is_prospect_eligible(
            msg, sender_email, sender_name, subject_raw, text_body,
            directory, email_directory, target_domains
        )

        if not is_eligible:
            if not is_already_seen:
                log(f"  ⏭️ Skipped non-prospect from {sender_email} (Sub: '{subject_raw[:40]}'): {reason}")
                mail.store(mid, "+FLAGS", r"(\Seen)")
            continue

        # -------------------------------------------------------------
        # 2.4 BUSINESS SENDING HOURS (Policy SD-POL-HOURS-2026-V1)
        # -------------------------------------------------------------
        # Restricts automated dispatch strictly to Mon-Fri 8:00 AM - 6:30 PM EST
        if enforce_hours:
            target_prospect_email = (inquiry_info.get("email") if inquiry_info else sender_email) or ""
            is_tester = target_prospect_email.lower() in [
                GMAIL_USER.lower(),
                "sandwichfitness@gmail.com",
                "david@surplusdocket.com",
                "dave@surplusdocket.com"
            ]
            if not is_tester:
                is_open, hours_reason = is_within_sending_hours()
                if not is_open:
                    pacing_key = f"hours_hold_{sender_email}"
                    now_ts = time.time()
                    if now_ts - _last_pacing_logged.get(pacing_key, 0) >= 120:
                        _last_pacing_logged[pacing_key] = now_ts
                        log(f"  🌙 Operational Hours: {hours_reason}. Holding auto-send until legal business hours resume (Mon-Fri 8:00 AM EST).")
                    continue

        # -------------------------------------------------------------
        # 2.5 HUMAN PACING WINDOW (Policy SD-POL-PACING-2026-V1)
        # -------------------------------------------------------------
        # Ensure realistic time has elapsed since inbound message arrival
        # to simulate professional coordinator review and docket compilation.
        if enforce_delay:
            age_secs = get_message_age_seconds(msg)
            required_delay = get_required_human_delay(message_id, sender_email, text_body)
            if age_secs < required_delay:
                remaining_secs = required_delay - age_secs
                pacing_key = f"{sender_email}_{message_id}"
                now_ts = time.time()
                if now_ts - _last_pacing_logged.get(pacing_key, 0) >= 60:
                    _last_pacing_logged[pacing_key] = now_ts
                    log(f"  ⏳ Human Pacing: Inbound inquiry from {sender_email} is {age_secs/60.0:.1f}m old. Holding auto-send for {remaining_secs/60.0:.1f}m more (total {required_delay/60.0:.1f}m window) to maintain authentic human turnaround.")
                continue

        # -------------------------------------------------------------
        # 3. STATUTORY WEBSITE INQUIRY & VOICEMAIL HANDLING
        # -------------------------------------------------------------
        if inquiry_info:
            prospect_name = inquiry_info["name"]
            prospect_email = inquiry_info["email"] or reply_to_email
            state_code = inquiry_info.get("state_code", "FL")
            department = inquiry_info.get("department", "General Publisher Inquiry")
            is_vm = inquiry_info.get("is_voicemail", False)

            if is_vm and not prospect_email:
                prospect_email = REPORT_RECIPIENT
                inquiry_info["email"] = prospect_email

            draft_key = f"inquiry:{prospect_email}:{state_code}:{department}:{inquiry_info.get('ref', '')}"
            if draft_key in already_drafted:
                if not is_already_seen:
                    mail.store(mid, "+FLAGS", r"(\Seen)")
                continue

            draft_msg, reply_subject, reply_body, role_title = build_inquiry_draft_email(
                inquiry_info, state_cases, message_id=message_id
            )
            persona = get_department_persona(department=department)
            from_addr = persona["email"]

            if AUTO_SEND:
                sent_ok, send_detail = send_response_email(draft_msg, from_addr, prospect_email)
                if sent_ok:
                    save_created_draft(draft_key)
                    already_drafted.add(draft_key)
                    mail.store(mid, "+FLAGS", r"(\Seen)")
                    log(f"  🚀 {persona['name']} ({role_title}) response AUTO-SENT to {prospect_email} via SMTP!")

                    # Record notable activity for Weekly Executive Report
                    channel = "VOICEMAIL" if is_vm else ("WEB_FORM" if "SD-INQ" in str(inquiry_info.get("ref", "")) else "DIRECT_EMAIL")
                    snippet = text_body[:160].replace("\n", " ").strip()
                    summary_text = (
                        f"Inbound {channel.lower()} from {prospect_name} regarding {state_code} excess proceeds. "
                        f"{persona['name']} auto-dispatched tailored response with active records and subscription terms."
                    )
                    record_notable_email_activity({
                        "id": f"ACT-{abs(hash(draft_key)) % 10000000}",
                        "timestamp": datetime.now().isoformat(),
                        "sender_name": prospect_name,
                        "sender_email": prospect_email,
                        "phone": inquiry_info.get("phone", ""),
                        "channel": channel,
                        "jurisdiction": STATE_NAMES.get(state_code, state_code),
                        "county": inquiry_info.get("county", ""),
                        "docket": inquiry_info.get("docket", ""),
                        "category": "INQUIRY",
                        "subject": reply_subject,
                        "inbound_snippet": snippet,
                        "summary": summary_text,
                        "action_taken": "AUTO_SENT_REPLY",
                        "persona": f"{persona['name']} ({role_title})",
                        "notable": True,
                    })
                else:
                    log(f"  ⚠️ Auto-send failed ({send_detail}); falling back to [Gmail]/Drafts creation.")
                    drafts_box = get_gmail_drafts_mailbox(mail)
                    mail.select(drafts_box)
                    now_epoch = time.time()
                    internal_date = imaplib.Time2Internaldate(now_epoch)
                    append_status, res = mail.append(drafts_box, r"(\Draft)", internal_date, draft_msg.as_bytes())
                    mail.select("INBOX")
                    if append_status == "OK":
                        save_created_draft(draft_key)
                        already_drafted.add(draft_key)
                        mail.store(mid, "+FLAGS", r"(\Seen)")
            else:
                drafts_box = get_gmail_drafts_mailbox(mail)
                mail.select(drafts_box)
                now_epoch = time.time()
                internal_date = imaplib.Time2Internaldate(now_epoch)
                append_status, res = mail.append(drafts_box, r"(\Draft)", internal_date, draft_msg.as_bytes())
                mail.select("INBOX")
                if append_status == "OK":
                    save_created_draft(draft_key)
                    already_drafted.add(draft_key)
                    mail.store(mid, "+FLAGS", r"(\Seen)")
                    log(f"  🎉 {persona['name']} ({role_title}) statutory inquiry draft created in Gmail for {prospect_email}!")
            continue

        # -------------------------------------------------------------
        # 4. VERIFIED LAW FIRM OUTREACH REPLY HANDLING
        # -------------------------------------------------------------
        msg_uid = re.sub(r"[^a-zA-Z0-9_\-]", "", message_id) if message_id else f"{sender_email}_{hash(text_body[:80])}"
        draft_key = f"reply:{sender_email}:{msg_uid}"
        if draft_key in already_drafted:
            if not is_already_seen:
                mail.store(mid, "+FLAGS", r"(\Seen)")
            continue

        intent = analyze_prospect_intent(subject_raw, text_body)
        log(f"  📩 Processing verified prospect reply from: {sender_name} <{sender_email}> | Intent: {intent} (Sub: {subject_raw})")

        reply_subject, reply_body = compose_elena_response(
            intent=intent,
            target_info=target_info,
            sender_name=sender_name,
            sender_email=sender_email,
            subject_raw=subject_raw,
            text_body=text_body,
            state_cases=state_cases,
        )

        draft_msg = MIMEText(reply_body, "plain", "utf-8")
        draft_msg["From"] = f"{FROM_NAME} <{SENDER_EMAIL}>"
        draft_msg["To"] = sender_raw
        draft_msg["Subject"] = reply_subject
        draft_msg["Reply-To"] = f"{FROM_NAME} <{REPLY_TO}>"
        if message_id:
            draft_msg["In-Reply-To"] = message_id
            draft_msg["References"] = message_id
        now_epoch = time.time()
        draft_msg["Date"] = formatdate(now_epoch, localtime=True)
        draft_msg["Message-ID"] = make_msgid()

        if AUTO_SEND:
            sent_ok, send_detail = send_response_email(draft_msg, SENDER_EMAIL, sender_email)
            if sent_ok:
                save_created_draft(draft_key)
                already_drafted.add(draft_key)
                mail.store(mid, "+FLAGS", r"(\Seen)")
                log(f"  🚀 Elena Brooks response AUTO-SENT to {sender_email} (Intent: {intent}) via SMTP!")

                summary_text = (
                    f"Law firm reply from {sender_name} ({target_info.get('firm', sender_email) if target_info else sender_email}). "
                    f"Intent: {intent}. Elena Brooks auto-responded with tailored statutory analysis."
                )
                record_notable_email_activity({
                    "id": f"ACT-{abs(hash(draft_key)) % 10000000}",
                    "timestamp": datetime.now().isoformat(),
                    "sender_name": sender_name,
                    "sender_email": sender_email,
                    "phone": "",
                    "channel": "DIRECT_EMAIL",
                    "jurisdiction": target_info.get("state", "FL") if target_info else "FL",
                    "county": "",
                    "docket": "",
                    "category": intent,
                    "subject": reply_subject,
                    "inbound_snippet": text_body[:160].replace("\n", " ").strip(),
                    "summary": summary_text,
                    "action_taken": "AUTO_SENT_REPLY",
                    "persona": "Elena Brooks (Senior Docket Specialist)",
                    "notable": True,
                })
            else:
                log(f"  ⚠️ Auto-send failed ({send_detail}); falling back to [Gmail]/Drafts creation.")
                drafts_box = get_gmail_drafts_mailbox(mail)
                mail.select(drafts_box)
                internal_date = imaplib.Time2Internaldate(now_epoch)
                append_status, res = mail.append(drafts_box, r"(\Draft)", internal_date, draft_msg.as_bytes())
                mail.select("INBOX")
                if append_status == "OK":
                    save_created_draft(draft_key)
                    already_drafted.add(draft_key)
                    mail.store(mid, "+FLAGS", r"(\Seen)")
        else:
            drafts_box = get_gmail_drafts_mailbox(mail)
            mail.select(drafts_box)
            internal_date = imaplib.Time2Internaldate(now_epoch)
            append_status, res = mail.append(drafts_box, r"(\Draft)", internal_date, draft_msg.as_bytes())
            mail.select("INBOX")
            if append_status == "OK":
                save_created_draft(draft_key)
                already_drafted.add(draft_key)
                mail.store(mid, "+FLAGS", r"(\Seen)")
                log(f"  🎉 Contextual [{intent}] follow-up draft created in Gmail for {sender_email}!")


def run_single_check(enforce_delay=True, enforce_hours=True):
    """Runs a single check across Apple Mail and Gmail."""
    clean_apple_mail_drafts()
    state_cases = load_feed_data()
    if not GMAIL_APP_PASS:
        log("GMAIL_APP_PASS is not configured in environment or .env; skipping IMAP operations.")
        return
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASS)
        sync_voicemails_to_inbox(mail)
        clean_imap_drafts(mail)
        check_and_create_auto_responses(mail, state_cases, enforce_delay=enforce_delay, enforce_hours=enforce_hours)
        mail.logout()
    except Exception as e:
        log(f"IMAP connection error: {e}")


def daemon_loop():
    log("🚀 Surplus Docket Continuous Daemon Started (Auto-send active with Mon-Fri 8am-6:30pm EST sending window & human pacing)...")
    while True:
        try:
            run_single_check(enforce_delay=True, enforce_hours=True)
        except Exception as e:
            log(f"Unexpected error in daemon loop: {e}")
        time.sleep(15)


if __name__ == "__main__":
    force = any(arg in sys.argv for arg in ["--force", "--force-now", "--now", "--immediate"])
    if len(sys.argv) > 1 and any(arg in sys.argv for arg in ["--once", "--single-pass"]):
        run_single_check(enforce_delay=not force, enforce_hours=not force)
    else:
        daemon_loop()

