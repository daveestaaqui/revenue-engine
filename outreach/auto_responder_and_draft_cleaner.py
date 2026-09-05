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
MASTER_TARGETS_CSV = OUTREACH_DIR / "master_ranked_attorney_targets.csv"
SUBMISSIONS_LOG_CSV = OUTREACH_DIR / "form_submissions_log.csv"
LOG_FILE = OUTREACH_DIR / "auto_responder.log"
UNSUBSCRIBE_LOG = OUTREACH_DIR / "unsubscribed.log"
UNSUBSCRIBED_URLS_FILE = OUTREACH_DIR / "unsubscribed_urls.json"
CREATED_DRAFTS_LOG = OUTREACH_DIR / "created_drafts_log.json"

# Credentials & Identity
GMAIL_USER = os.getenv("GMAIL_USER", "sandwichfitness@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "nxgfaiebqpmobhkp")
FROM_NAME = os.getenv("FROM_NAME", "Elena Brooks")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "elena.brooks@surplusdocket.com")
REPLY_TO = os.getenv("REPLY_TO", "elena.brooks@surplusdocket.com")
SITE_URL = "https://surplusdocket.com"
STRIPE_LINK = "https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X"

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
    "NC": ("North Carolina", "N.C.G.S. § 105-374"),
    "TN": ("Tennessee", "T.C.A. § 67-5-2501"),
    "CA": ("California", "Cal. Rev. & Tax Code § 4675"),
}

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


def analyze_prospect_intent(subject_raw, text_body):
    """
    Classifies attorney inbound intent into:
    - 'OPT_OUT'
    - 'PRICING'
    - 'JURISDICTION'
    - 'DATA_FORMAT'
    - 'SAMPLE_DATA'
    - 'GENERAL'
    """
    content = (subject_raw + " " + text_body).lower()

    # Opt-out check takes absolute precedence
    opt_out_cues = [
        "unsubscribe", "remove me", "remove us", "stop emailing",
        "not interested", "take me off", "do not contact", "please remove",
        "wrong email", "cease and desist", "do not email"
    ]
    if any(c in content for c in opt_out_cues):
        return "OPT_OUT"

    # Pricing & Terms
    pricing_cues = [
        "how much", "cost", "pricing", "rate", "rates", "fee", "fees",
        "contract", "terms", "subscription", "price", "month to month",
        "billing", "payment options", "retainer"
    ]
    if any(c in content for c in pricing_cues):
        return "PRICING"

    # Jurisdiction / County Coverage
    jurisdiction_cues = [
        "what counties", "which counties", "do you cover", "jurisdiction", "circuits",
        "harris", "dallas", "tarrant", "travis", "bexar",
        "miami", "palm beach", "hillsborough", "orange", "broward", "duval", "pinellas",
        "fulton", "dekalb", "cobb", "gwinnett",
        "wake", "mecklenburg", "guilford",
        "shelby", "davidson", "knox", "hamilton",
        "los angeles", "san diego", "riverside", "san bernardino",
        "statewide", "coverage"
    ]
    if any(c in content for c in jurisdiction_cues):
        return "JURISDICTION"

    # Data Format / Technical Integration
    format_cues = [
        "api", "format", "csv", "excel", "xlsx", "json", "fields",
        "integration", "software", "crm", "clio", "filevine", "smokeball",
        "webhook", "feed format"
    ]
    if any(c in content for c in format_cues):
        return "DATA_FORMAT"

    # Sample Data Request
    sample_cues = [
        "sample", "example", "examples", "preview", "proof", "show me", "send me", "pull a few"
    ]
    if any(c in content for c in sample_cues):
        return "SAMPLE_DATA"

    return "GENERAL"


def compose_elena_response(intent, target_info, sender_name, sender_email, subject_raw, text_body, state_cases):
    """
    Drafts an authoritative, context-aware response adhering strictly to Elena Brooks' persona voice.
    """
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

    # 2. Resolve State & Statutory Context
    detected_state = target_info.get("state", "FL") if target_info else "FL"
    for code, name in STATE_NAMES.items():
        if name.lower() in subject_raw.lower() or name.lower() in text_body.lower():
            detected_state = code
            break

    state_name = STATE_NAMES.get(detected_state, "Florida")
    statute_cite = STATE_STATUTES.get(detected_state, (state_name, "applicable state civil code"))[1]

    # Sample block for cases
    cases = state_cases.get(detected_state, state_cases.get("FL", []))[:3]
    sample_bullets = []
    for c in cases:
        sample_bullets.append(f"• Docket {c['case_no']} ({c['county']} Co.) — ${c['balance']:,.0f} surplus balance")
    sample_block = "\n".join(sample_bullets) if sample_bullets else "• Verified individual & estate records indexed daily across all circuits"

    signature = f"""Best regards,

Elena Brooks
Senior Docket Specialist | Surplus Docket
surplusdocket.com
elena.brooks@surplusdocket.com"""

    # 3. Formulate Intent-Specific Body
    if intent == "OPT_OUT":
        body = f"""{greeting}

Understood. I have marked your firm's file and removed you from all future docket distributions and updates.

{signature}"""

    elif intent == "PRICING":
        body = f"""{greeting}

Thanks for following up regarding our data subscription.

Our pricing is a flat $249/month for your entire practice—there are zero per-claim fees, no contingency cuts, and no long-term contracts. Billing is month-to-month and managed through our self-service Stripe portal, allowing cancellation at any time.

From an ROI perspective, the average {state_name} surplus balance in our current index is roughly $45,000. At a standard 25% statutory contingency fee ($11,250), a single successful recovery covers multiple years of access.

You can inspect sample dockets and activate daily morning delivery here:
{STRIPE_LINK}

Let me know if your firm requires an invoice or specific vendor billing documentation.

{signature}"""

    elif intent == "JURISDICTION":
        body = f"""{greeting}

Thanks for reaching out regarding our court registry coverage.

Our automated court crawlers monitor county clerk of court registries and tax collector excess funds dockets daily across {state_name}. 

Critically, we filter out senior institutional mortgages, municipal utility liens, and bank encumbrances upstream before delivery. Your attorneys only receive verified, actionable equity balances with active statutory claim windows under {statute_cite}.

Here are active sample records from our {state_name} index:
{sample_block}

Standardized feeds are delivered every business morning at 7:00 AM EST (CSV, Excel, JSON). You can set up daily delivery for your practice directly here:
{STRIPE_LINK}

If your firm focuses on specific judicial circuits or county registries, let me know and I can verify our active inventory for those jurisdictions.

{signature}"""

    elif intent == "DATA_FORMAT":
        body = f"""{greeting}

Thanks for asking about our delivery specifications.

We deliver the standardized feed every morning at 7:00 AM EST in three concurrent formats:
1. Standard CSV & Excel (.xlsx) for direct review by counsel and paralegal staff.
2. Structured REST JSON API with webhooks for direct intake into practice management systems (Clio, Smokeball, Filevine).

Each record includes:
• Court / Registry Docket Number & Judicial Circuit
• Verified Surplus Balance & Sale Date
• Former Record Titleholder / Estate Identification
• Property Parcel ID & Situs Address
• Senior Mortgage & Institutional Lien Scrubbing Verification
• Direct Clerk Verification Portal Link

Access is $249/month flat across all circuits:
{STRIPE_LINK}

Happy to provide our JSON API schema or a sample Excel extract if your team would like to review the fields.

{signature}"""

    elif intent == "SAMPLE_DATA":
        body = f"""{greeting}

Thanks for getting back to me.

Here are three active, verified surplus records from our current {state_name} index, pre-scrubbed to eliminate senior bank encumbrances:

{sample_block}

Our crawlers index new foreclosure filings and court overages daily, delivering the standardized feed every morning at 7:00 AM EST in CSV, Excel, and JSON ($249/month flat, cancel anytime).

You can activate daily delivery directly for your practice here:
{STRIPE_LINK}

Let me know if you would like me to pull historical files for any specific county or circuit in {state_name}.

{signature}"""

    else:  # GENERAL
        body = f"""{greeting}

Thanks for following up with our research desk.

Our morning intelligence feed delivers verified, case-level public records every business day at 7:00 AM EST in CSV, Excel, and REST API formats ($249/month flat, cancel anytime).

Key details for your practice:
• 100% of institutional bank mortgages and senior liens are filtered out upstream so your attorneys only work claimable individual and estate equity.
• We index all high-volume judicial circuits in {state_name} (along with TX, GA, NC, TN, and CA).
• All subscriptions include our Asset Recovery Toolkit (court-ready petition motions, heir retainer contracts, and statutory fee calculators).

You can activate daily feed delivery directly for your firm here:
{STRIPE_LINK}

Please let me know if you have any questions or if you would like to review records for a specific county.

{signature}"""

    reply_subject = subject_raw if subject_raw.lower().startswith("re:") else f"Re: {subject_raw}"
    return reply_subject, body


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
    directory, email_directory, target_domains = load_target_directory()
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
        # 2. ELIGIBILITY & POLICY ENFORCEMENT (SD-POL-OUTREACH-2026-V1)
        # -------------------------------------------------------------
        is_eligible, reason, target_info, inquiry_info = is_prospect_eligible(
            msg, sender_email, sender_name, subject_raw, text_body,
            directory, email_directory, target_domains
        )

        if not is_eligible:
            log(f"  ⏭️ Skipped non-prospect from {sender_email} (Sub: '{subject_raw[:40]}'): {reason}")
            mail.store(mid, "+FLAGS", r"(\Seen)")
            continue

        # -------------------------------------------------------------
        # 3. STATUTORY WEBSITE INQUIRY HANDLING
        # -------------------------------------------------------------
        if inquiry_info:
            prospect_name = inquiry_info["name"]
            prospect_email = inquiry_info["email"] or reply_to_email
            state_code = inquiry_info["state_code"]
            state_name = STATE_NAMES.get(state_code, "Florida")
            statute_cite = STATE_STATUTES.get(state_code, (state_name, "applicable state civil code"))[1]
            cases = state_cases.get(state_code, state_cases.get("FL", []))[:3]

            draft_key = f"inquiry:{prospect_email}:{state_code}"
            if draft_key in already_drafted:
                mail.store(mid, "+FLAGS", r"(\Seen)")
                continue

            first_name = ""
            if prospect_name:
                parts = [p.strip() for p in prospect_name.split() if p.strip()]
                if parts and parts[0].title().lower() not in BANNED_FIRST_NAMES:
                    first_name = parts[0].title()

            greeting = f"Hi {first_name}," if first_name else "Hello,"

            sample_bullets = []
            for c in cases:
                sample_bullets.append(f"• Docket {c['case_no']} ({c['county']} Co.) — ${c['balance']:,.0f} surplus balance")
            sample_block = "\n".join(sample_bullets) if sample_bullets else "• Verified individual & estate records indexed daily across all circuits"

            reply_body = f"""{greeting}

Thank you for submitting your statutory inquiry to Surplus Docket regarding {state_name} public record excess proceeds data.

Here are a few verified, active records from our current {state_name} docket index (with bank and senior mortgages filtered out upstream):

{sample_block}

We publish and deliver the complete standardized morning feed at 7:00 AM EST every business day in CSV, Excel, and JSON API formats ($249/month flat, cancel anytime).

You can activate daily feed delivery for your practice directly here:
{STRIPE_LINK}

Please let me know if you would like custom county-level filtering or have specific questions about statutory filing windows under {statute_cite}.

Best regards,

Elena Brooks
Senior Docket Specialist | Surplus Docket
surplusdocket.com
elena.brooks@surplusdocket.com"""

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
        # 4. VERIFIED LAW FIRM OUTREACH REPLY HANDLING
        # -------------------------------------------------------------
        msg_uid = re.sub(r"[^a-zA-Z0-9_\-]", "", message_id) if message_id else f"{sender_email}_{hash(text_body[:80])}"
        draft_key = f"reply:{sender_email}:{msg_uid}"
        if draft_key in already_drafted:
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
            log(f"  🎉 Contextual [{intent}] follow-up draft created in Gmail for {sender_email}!")


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
