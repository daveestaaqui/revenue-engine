#!/usr/bin/env python3
"""
Surplus Docket — Concise Legal Outreach Draft Generator & Gmail Uploader
========================================================================
Generates concise, punchy, factually accurate, lawyer-to-lawyer outreach emails
(~100 words, easily digestible in 15 seconds) and uploads them directly into
Gmail's Drafts folder.
"""

import csv
import imaplib
import os
import re
import sys
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
OUTREACH_DIR = BASE_DIR / "outreach"
TARGETS_CSV = OUTREACH_DIR / "verified_attorney_targets.csv"
SENT_LOG_CSV = OUTREACH_DIR / "sent_log.csv"
FEED_CSV = BASE_DIR / "exports" / "Master_Surplus_Lead_Feed.csv"
DRAFTS_DIR = OUTREACH_DIR / "drafts"
LOG_DIR = OUTREACH_DIR / "drafts_uploaded"

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

# Credentials & Sender Identity
GMAIL_USER = os.getenv("GMAIL_USER", "sandwichfitness@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")
FROM_NAME = "Dave Mahler"
REPLY_TO = "data@surplusdocket.com"
SITE_URL = "https://surplusdocket.com"

STATE_METADATA = {
    "FL": {
        "name": "Florida",
        "statute": "Fla. Stat. § 197.582",
    },
    "TX": {
        "name": "Texas",
        "statute": "Tex. Tax Code § 34.04",
    },
    "GA": {
        "name": "Georgia",
        "statute": "O.C.G.A. § 48-4-5",
    },
    "NC": {
        "name": "North Carolina",
        "statute": "N.C.G.S. § 105-374",
    },
    "TN": {
        "name": "Tennessee",
        "statute": "T.C.A. § 67-5-2501",
    },
    "CA": {
        "name": "California",
        "statute": "Cal. Rev. & Tax Code § 4675",
    },
    "NY": {
        "name": "New York",
        "statute": "RPAPL § 1361",
    },
    "NJ": {
        "name": "New Jersey",
        "statute": "N.J. Court Rule 4:64-3",
    },
    "OH": {
        "name": "Ohio",
        "statute": "Ohio Rev. Code § 5721.20",
    },
    "IL": {
        "name": "Illinois",
        "statute": "35 ILCS 200/21-310",
    },
    "PA": {
        "name": "Pennsylvania",
        "statute": "72 P.S. § 5860.205",
    },
    "MD": {
        "name": "Maryland",
        "statute": "Md. Code, Tax-Prop. § 14-818",
    },
}

EXCLUDED_DOMAINS = {
    "farahlawtexas.com",
    "schuenemanlaw.com",
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
            })

    for state in state_cases:
        state_cases[state].sort(key=lambda x: x["balance"], reverse=True)
    return state_cases


def get_already_sent():
    sent = set()
    if not SENT_LOG_CSV.exists():
        return sent

    with open(SENT_LOG_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get("Status", "").strip()
            email_addr = row.get("Email", "").strip().lower()
            if "SENT" in status and "DRY_RUN" not in status:
                sent.add(email_addr)
    return sent


def load_targets():
    if not TARGETS_CSV.exists():
        return []

    targets = []
    with open(TARGETS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {k.strip(): (v or "").strip() for k, v in row.items() if k}
            email_addr = clean.get("Email", "").strip().lower()
            if not email_addr or "@" not in email_addr:
                continue
            domain = email_addr.split("@")[1]
            if domain in EXCLUDED_DOMAINS:
                continue
            targets.append(clean)
    return targets


def build_salutation(full_name):
    if not full_name:
        return "Dear Counsel,"
    return f"Dear {full_name},"


def format_case_evidence(state, state_cases):
    cases = state_cases.get(state, [])
    if not cases:
        for s in ["FL", "TX", "GA", "CA", "NC", "TN"]:
            if state_cases.get(s):
                cases = state_cases[s]
                break

    top_cases = cases[:2]
    lines = []
    for c in top_cases:
        lines.append(f"• Docket {c['case_no']} ({c['county']} County): ${c['balance']:,.0f} surplus balance")
    return "\n".join(lines)


def compose_concise_email(target, state_cases):
    full_name = target.get("Name", "").strip()
    firm = target.get("Firm", "").strip()
    state = target.get("State", "FL").strip().upper()
    
    meta = STATE_METADATA.get(state, {"name": state, "statute": "applicable state statutes"})
    state_name = meta["name"]
    statute = meta["statute"]
    
    salutation = build_salutation(full_name)
    case_evidence = format_case_evidence(state, state_cases)

    subject = f"{state_name} surplus & excess proceeds data for {firm}"

    body = f"""{salutation}

I run Surplus Docket. We provide a structured daily data feed of tax deed surplus and excess proceeds filings across {state_name} court registries, pre-filtered to remove senior mortgages and corporate liens.

Most raw county lists are heavily encumbered by institutional lienholders that extinguish the surplus under {statute}. We scrub those out upstream so your team only spends time on actionable individual and estate claims.

Verified records from our current {state_name} index:
{case_evidence}

Feeds are delivered daily at 7:00 AM EST in CSV, Excel, and JSON ($249/mo flat, month-to-month, cancel anytime). More details at {SITE_URL}.

If you would like to see a sample data extract for {state_name} to evaluate the data, let me know and I will be glad to send one over.

Sincerely,

Dave Mahler
Surplus Docket
{SITE_URL}"""

    return subject, body


def update_drafts():
    print("=" * 75)
    print("  ⚖️  SURPLUS DOCKET — CONCISE DRAFT GENERATOR & GMAIL SYNC")
    print("=" * 75)
    print(f"Target Account: {GMAIL_USER}")

    state_cases = load_feed_data()
    already_sent = get_already_sent()
    targets = load_targets()
    eligible_targets = [t for t in targets if t["Email"].lower() not in already_sent]
    print(f"✓ {len(eligible_targets)} targets ready for concise draft generation\n")

    if not eligible_targets:
        print("No eligible targets.")
        return

    # Connect to Gmail IMAP
    print(f"Connecting to imap.gmail.com as {GMAIL_USER}...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASS)
        print("✅ Logged into Gmail IMAP successfully!\n")
    except Exception as e:
        print(f"❌ Failed to connect to Gmail: {e}")
        return

    drafts_mailbox = "[Gmail]/Drafts"
    status, count = mail.select(drafts_mailbox)
    if status != "OK":
        drafts_mailbox = "Drafts"
        status, count = mail.select(drafts_mailbox)

    print(f"Purging previous drafts in '{drafts_mailbox}'...")
    for query in ['SUBJECT "Scrubbed"', 'SUBJECT "Structured"', 'SUBJECT "surplus & excess proceeds"']:
        status, messages = mail.search(None, query)
        if status == "OK" and messages[0]:
            for msg_id in messages[0].split():
                mail.store(msg_id, "+FLAGS", r"(\Deleted)")
    mail.expunge()
    print("✓ Drafts mailbox cleaned up.\n")

    # Local directory setup
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in DRAFTS_DIR.glob("*.eml"):
        old_file.unlink()

    uploaded = 0
    failed = 0
    manifest = []

    print("Uploading concise, easily digestible drafts to Gmail...")
    print("-" * 75)

    for i, target in enumerate(eligible_targets, 1):
        to_email = target["Email"].strip()
        to_name = target.get("Name", "Counsel").strip()
        firm = target.get("Firm", "").strip()
        state = target.get("State", "").strip()

        subject, body = compose_concise_email(target, state_cases)

        # Create MIME Message
        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = f"{FROM_NAME} <{GMAIL_USER}>"
        msg["To"] = f"{to_name} <{to_email}>"
        msg["Subject"] = subject
        msg["Reply-To"] = f"Surplus Docket <{REPLY_TO}>"
        msg["X-Unsent"] = "1"
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()

        # Save local .eml
        safe_name = re.sub(r"[^a-zA-Z0-9]", "_", to_email.split("@")[0])
        domain = to_email.split("@")[1].replace(".", "_") if "@" in to_email else "unknown"
        eml_filename = f"{i:03d}_{safe_name}_at_{domain}.eml"
        (DRAFTS_DIR / eml_filename).write_text(msg.as_string(), encoding="utf-8")

        # Append to Gmail Drafts
        try:
            now_epoch = time.time()
            internal_date = imaplib.Time2Internaldate(now_epoch)
            append_status, res = mail.append(drafts_mailbox, r"(\Draft)", internal_date, msg.as_bytes())
            if append_status == "OK":
                uploaded += 1
                print(f"  [{i:02d}/{len(eligible_targets):02d}] ✅ Draft Created: {to_name} | {firm} ({to_email}) — {state}")
                manifest.append({
                    "idx": i,
                    "name": to_name,
                    "firm": firm,
                    "email": to_email,
                    "state": state,
                    "subject": subject,
                    "file": eml_filename,
                    "status": "DRAFT_IN_GMAIL",
                    "timestamp": datetime.now().isoformat(),
                })
            else:
                failed += 1
                print(f"  [{i:02d}/{len(eligible_targets):02d}] ❌ Append Error: {res}")
        except Exception as e:
            failed += 1
            print(f"  [{i:02d}/{len(eligible_targets):02d}] ❌ Error for {to_email}: {e}")

    mail.logout()

    manifest_path = LOG_DIR / "gmail_concise_drafts_manifest.csv"
    with open(manifest_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["idx", "name", "firm", "email", "state", "subject", "file", "status", "timestamp"])
        writer.writeheader()
        writer.writerows(manifest)

    print("\n" + "=" * 75)
    print("  🎉 CONCISE DRAFTS SYNC COMPLETE")
    print("=" * 75)
    print(f"  • Total Drafts in Gmail Drafts : {uploaded}")
    print(f"  • Local .eml Copies Saved      : {uploaded} in {DRAFTS_DIR}")
    print(f"  • Manifest Log                 : {manifest_path}")
    print("=" * 75)


if __name__ == "__main__":
    update_drafts()
