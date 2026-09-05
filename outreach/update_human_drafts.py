#!/usr/bin/env python3
"""
Surplus Docket — Natural, Human, Concise Legal Outreach Generator & Gmail Uploader
==================================================================================
Generates ~80-word, natural, human outreach emails in David's authentic voice
and syncs them to Gmail's Drafts folder.

Sender: David Mahler <david@surplusdocket.com>
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
FROM_NAME = "David Mahler"
SENDER_EMAIL = "david@surplusdocket.com"
REPLY_TO = "david@surplusdocket.com"
SITE_URL = "https://surplusdocket.com"

STATE_NAMES = {
    "FL": "Florida",
    "TX": "Texas",
    "GA": "Georgia",
    "NC": "North Carolina",
    "TN": "Tennessee",
    "CA": "California",
    "NY": "New York",
    "NJ": "New Jersey",
    "OH": "Ohio",
    "IL": "Illinois",
    "PA": "Pennsylvania",
    "MD": "Maryland",
}

EXCLUDED_DOMAINS = {
    "farahlawtexas.com",
    "schuenemanlaw.com",
}


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


def get_first_name(full_name):
    if not full_name:
        return ""
    parts = full_name.strip().split()
    return parts[0] if parts else ""


def compose_human_email(target):
    full_name = target.get("Name", "").strip()
    first_name = get_first_name(full_name)
    firm = target.get("Firm", "").strip()
    state_code = target.get("State", "FL").strip().upper()
    state_name = STATE_NAMES.get(state_code, state_code)

    greeting = f"Hi {first_name}," if first_name else f"Hello {firm} team,"

    subject = f"{state_name} surplus & excess proceeds data"

    body = f"""{greeting}

I'm reaching out because I built a tool that indexes tax deed surplus and excess proceeds cases across {state_name}.

Most county surplus lists are a headache to work through because the majority of files are encumbered by senior mortgages or bank liens that wipe out the funds. We pull the dockets daily and filter out those institutional liens upstream, so you're only looking at clean individual and estate claims.

If you'd like to see a sample export for {state_name} to see if it's useful for your practice, let me know and I'd be happy to send one over.

Best,

David Mahler
surplusdocket.com
david@surplusdocket.com"""

    return subject, body


def update_site_contact_info():
    """Updates site HTML files to reference david@surplusdocket.com."""
    site_dir = BASE_DIR / "site"
    html_files = list(site_dir.glob("**/*.html"))
    count = 0
    for file_path in html_files:
        content = file_path.read_text(encoding="utf-8")
        original = content
        
        # Replace data@surplusdocket.com if any
        content = content.replace("data@surplusdocket.com", "david@surplusdocket.com")
        content = content.replace("contact@surplusdocket.com", "david@surplusdocket.com")
        
        # Add contact email to footer if not already present
        if "david@surplusdocket.com" not in content and "All rights reserved" in content:
            content = content.replace(
                "All rights reserved.",
                "All rights reserved. • Contact: <a href=\"mailto:david@surplusdocket.com\" class=\"hover:text-brand-green underline transition-colors\">david@surplusdocket.com</a>"
            )
        
        if content != original:
            file_path.write_text(content, encoding="utf-8")
            count += 1
    print(f"✓ Updated contact email to david@surplusdocket.com in {count} site files")


def sync_gmail_drafts():
    print("=" * 75)
    print("  📧 SURPLUS DOCKET — NATURAL HUMAN DRAFTS GMAIL SYNC")
    print("=" * 75)
    print(f"Sender Identity: {FROM_NAME} <{SENDER_EMAIL}>")
    print(f"Target Gmail   : {GMAIL_USER}\n")

    # 1. Update site contact info
    update_site_contact_info()

    # 2. Check sent history and load targets
    already_sent = get_already_sent()
    targets = load_targets()
    eligible_targets = [t for t in targets if t["Email"].lower() not in already_sent]
    print(f"✓ {len(eligible_targets)} verified targets ready for draft generation\n")

    if not eligible_targets:
        print("No eligible targets.")
        return

    # 3. Connect to Gmail IMAP
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

    print(f"Purging old drafts in '{drafts_mailbox}'...")
    # Clean out previous automated drafts
    for q in ['SUBJECT "surplus & excess proceeds data"', 'SUBJECT "Structured"', 'SUBJECT "Scrubbed"']:
        status, messages = mail.search(None, q)
        if status == "OK" and messages[0]:
            for msg_id in messages[0].split():
                mail.store(msg_id, "+FLAGS", r"(\Deleted)")
    mail.expunge()
    print("✓ Old drafts purged.\n")

    # 4. Prepare local draft storage
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in DRAFTS_DIR.glob("*.eml"):
        old_file.unlink()

    uploaded = 0
    failed = 0
    manifest = []

    print("Uploading natural, concise drafts to Gmail Drafts...")
    print("-" * 75)

    for i, target in enumerate(eligible_targets, 1):
        to_email = target["Email"].strip()
        to_name = target.get("Name", "Counsel").strip()
        firm = target.get("Firm", "").strip()
        state = target.get("State", "").strip()

        subject, body = compose_human_email(target)

        # Create MIME Message
        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = f"{FROM_NAME} <{GMAIL_USER}>"
        msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email
        msg["Subject"] = subject
        msg["Reply-To"] = f"{FROM_NAME} <{REPLY_TO}>"
        msg["X-Unsent"] = "1"
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()

        # Save local .eml copy
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

    manifest_path = LOG_DIR / "gmail_human_drafts_manifest.csv"
    with open(manifest_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["idx", "name", "firm", "email", "state", "subject", "file", "status", "timestamp"])
        writer.writeheader()
        writer.writerows(manifest)

    print("\n" + "=" * 75)
    print("  🎉 NATURAL HUMAN DRAFTS SYNC COMPLETE")
    print("=" * 75)
    print(f"  • Total Drafts in Gmail Drafts : {uploaded}")
    print(f"  • Local .eml Copies Saved      : {uploaded} in {DRAFTS_DIR}")
    print(f"  • Sender Identity              : David Mahler (david@surplusdocket.com)")
    print(f"  • Manifest Log                 : {manifest_path}")
    print("=" * 75)


if __name__ == "__main__":
    sync_gmail_drafts()
