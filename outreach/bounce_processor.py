#!/usr/bin/env python3
"""
Surplus Docket — Autonomous Bounce Processor & Learning Engine
==============================================================
Continuously detects, analyzes, and learns from email delivery failures (NDRs):
1. Scans Gmail INBOX / All Mail via IMAP for bounces (mailer-daemon, postmaster, DSNs).
2. Extracts failed recipient email, domain, error code (550, 554, NoSuchUser), and diagnostic text.
3. Automatically persists failed addresses and root domains to outreach/bounced_emails.json.
4. Updates outreach/sent_log.csv: retroactively modifies status from SENT_DELIVERED to BOUNCED_REJECTED.
5. Updates target registries (high_conviction_attorneys.csv, verified_pool.json) to exclude dead addresses.
6. Feeds into deliverability_guard.py and ground_truth_gatekeeper.py to permanently immunize outreach.
"""

import csv
import email
import email.message
from email.message import Message
import imaplib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from email.utils import parseaddr
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

BOUNCED_JSON = BASE_DIR / "outreach" / "bounced_emails.json"
SENT_LOG_CSV = BASE_DIR / "outreach" / "sent_log.csv"
HIGH_CONVICTION_CSV = BASE_DIR / "outreach" / "high_conviction_attorneys.csv"
VERIFIED_TARGETS_CSV = BASE_DIR / "outreach" / "verified_attorney_targets.csv"
MASTER_TARGETS_CSV = BASE_DIR / "outreach" / "master_ranked_attorney_targets.csv"
TOOL_TARGETS_CSV = BASE_DIR / "marketing" / "link_building" / "tool_outreach_targets.csv"
TOOL_LOG_CSV = BASE_DIR / "marketing" / "link_building" / "tool_outreach_log.csv"
POOL_JSON = BASE_DIR / "outreach" / "verified_pool.json"

ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    try:
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))
    except Exception:
        pass

GMAIL_USER = os.getenv("GMAIL_USER", "sandwichfitness@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")


def record_bounced_entity(email_addr: str, error_diag: str = "") -> bool:
    """Records email address and domain into bounced_emails.json."""
    if not email_addr or "@" not in email_addr:
        return False
    clean_em = email_addr.strip().lower()
    domain = clean_em.split("@")[-1]

    current_data = []
    if BOUNCED_JSON.exists():
        try:
            with open(BOUNCED_JSON, "r", encoding="utf-8") as f:
                current_data = json.load(f)
        except Exception:
            current_data = []

    changed = False
    if clean_em not in current_data:
        current_data.append(clean_em)
        changed = True
    is_shared_or_institutional = (
        domain in ("gmail.com", "googlemail.com", "yahoo.com", "outlook.com", "americanbar.org", "ncbar.org", "gabar.org", "floridabar.org", "texasbar.com", "nysba.org", "okbar.org", "azbar.org")
        or domain.endswith(".edu")
    )
    if domain not in current_data and not is_shared_or_institutional:
        current_data.append(domain)
        changed = True

    if changed:
        try:
            with open(BOUNCED_JSON, "w", encoding="utf-8") as f:
                json.dump(sorted(list(set(current_data))), f, indent=2)
            print(f"  🛡️ Recorded bounced target to blacklist: {clean_em} ({domain})")
        except Exception as e:
            print(f"  ⚠️ Warning writing to {BOUNCED_JSON}: {e}")

    return changed


def update_sent_log_bounce(bounced_email: str, error_diag: str = "") -> int:
    """Updates status of matching records in sent_log.csv to BOUNCED_REJECTED."""
    if not SENT_LOG_CSV.exists() or not bounced_email:
        return 0

    clean_target = bounced_email.strip().lower()
    updated_rows = []
    matched_count = 0

    with open(SENT_LOG_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or ["Timestamp", "Email", "Name", "Firm", "State", "Subject", "Status", "Mode", "Output_File"]
        for row in reader:
            em = row.get("Email", "").strip().lower()
            status = row.get("Status", "").upper()
            if em == clean_target and "SENT" in status:
                row["Status"] = f"BOUNCED_REJECTED"
                if error_diag:
                    row["Mode"] = f"BOUNCE: {error_diag[:40]}"
                matched_count += 1
                print(f"  🔄 Updated sent_log.csv status for {em} -> BOUNCED_REJECTED")
            updated_rows.append(row)

    if matched_count > 0:
        with open(SENT_LOG_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)

    return matched_count


def update_target_csv_bounce(csv_path: Path, bounced_email: str) -> int:
    """Removes bounced/dead email rows directly from target CSV registries."""
    if not csv_path.exists() or not bounced_email:
        return 0

    clean_target = bounced_email.strip().lower()
    kept_rows = []
    removed_count = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            em = (row.get("Email") or row.get("contact_email") or "").strip().lower()
            if em == clean_target:
                removed_count += 1
                print(f"  🗑️ Deleted bounced target {em} from {csv_path.name}")
            else:
                kept_rows.append(row)

    if removed_count > 0 and fieldnames:
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(kept_rows)

    return removed_count


def update_tool_log_bounce(bounced_email: str, error_diag: str = "") -> int:
    """Updates status of matching records in tool_outreach_log.csv to BOUNCED_REJECTED."""
    if not TOOL_LOG_CSV.exists() or not bounced_email:
        return 0

    clean_target = bounced_email.strip().lower()
    updated_rows = []
    matched_count = 0

    with open(TOOL_LOG_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            em = (row.get("recipient_email") or "").strip().lower()
            status = (row.get("status") or "").upper()
            if em == clean_target and status == "SENT":
                row["status"] = "BOUNCED_INVALID_ADDRESS"
                if error_diag:
                    row["notes"] = f"Bounced: {error_diag[:80]}"
                matched_count += 1
                print(f"  🔄 Updated tool_outreach_log.csv status for {em} -> BOUNCED_INVALID_ADDRESS")
            updated_rows.append(row)

    if matched_count > 0 and fieldnames:
        with open(TOOL_LOG_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)

    return matched_count


def remove_from_verified_pool(bounced_email: str) -> bool:
    """Removes a bounced attorney from verified_pool.json."""
    if not POOL_JSON.exists():
        return False
    try:
        with open(POOL_JSON, "r", encoding="utf-8") as f:
            pool = json.load(f)
        clean_target = bounced_email.strip().lower()
        new_pool = [p for p in pool if p.get("email", "").strip().lower() != clean_target]
        if len(new_pool) < len(pool):
            with open(POOL_JSON, "w", encoding="utf-8") as f:
                json.dump(new_pool, f, indent=2)
            print(f"  🧹 Removed {clean_target} from active verified_pool.json")
            return True
    except Exception as e:
        print(f"  ⚠️ Warning updating {POOL_JSON}: {e}")
    return False


def extract_bounce_metadata(msg: Message) -> tuple[list[str], str]:
    """Parses an RFC822 message for failed recipient addresses and diagnostic reasons."""
    body = ""
    hdr_failed = msg.get_all("X-Failed-Recipients") or []
    for hf in hdr_failed:
        body += f"\nFailed-Recipients: {hf}\n"

    for part in msg.walk():
        ct = part.get_content_type()
        if ct in ("text/plain", "text/html"):
            p = part.get_payload(decode=True)
            if p:
                body += "\n" + p.decode("utf-8", errors="replace")
        elif ct in ("message/delivery-status", "text/rfc822-headers", "message/rfc822"):
            try:
                body += "\n" + part.as_string()
            except Exception:
                pass

    # Diagnostic error regexes
    err_match = re.search(r"(5\d{2}\s+5\.\d+\.\d+[^<\n\r]+)", body) or \
                re.search(r"(The email account that you tried to reach does not exist[^<\n\r]*)", body) or \
                re.search(r"(Your message wasn't delivered to[^<\n\r]*)", body) or \
                re.search(r"(Address not found[^<\n\r]*)", body) or \
                re.search(r"(\*\* Address not found \*\*)", body) or \
                re.search(r"Diagnostic-Code:[^;]+;\s*([^\n\r]+)", body, re.IGNORECASE)

    err_str = err_match.group(1).strip() if err_match else "Delivery failed (NDR)"

    # Recipient extraction patterns
    found = set()
    patterns = [
        r"delivered to\s+<?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)>?",
        r"Original-Recipient:[^;]+;\s*<?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)>?",
        r"Final-Recipient:[^;]+;\s*<?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)>?",
        r"Failed-Recipients:\s*<?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)>?",
        r"<([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)>:\s*5\d\d",
        r"<([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)> Recipient not found",
        r"Your message to\s+<?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)>?\s+couldn't be delivered",
    ]

    for pat in patterns:
        for m in re.finditer(pat, body, re.IGNORECASE):
            em = m.group(1).lower().strip().rstrip(".")
            if em and not any(x in em for x in ["google", "mailer-daemon", "postmaster", "sandwichfitness", "surplusdocket"]):
                found.add(em)

    return list(found), err_str


def process_mailbox_bounces(mail, mailbox="INBOX", delete_messages: bool = True) -> int:
    """Scans the specified mailbox on IMAP for bounce notifications, records them, and deletes the bounce emails."""
    try:
        status, _ = mail.select(mailbox)
        if status != "OK":
            return 0

        queries = [
            '(FROM "mailer-daemon")',
            '(FROM "postmaster")',
            '(SUBJECT "Delivery Status Notification")',
            '(SUBJECT "Undeliverable")',
            '(SUBJECT "Mail delivery failed")',
            '(SUBJECT "Delivery Failure")',
        ]

        bounce_mids = set()
        for q in queries:
            s, data = mail.search(None, q)
            if s == "OK" and data and data[0]:
                for mid in data[0].split():
                    bounce_mids.add(mid)

        if not bounce_mids:
            return 0

        processed = 0
        deleted_mids = 0
        is_trash = "trash" in mailbox.lower()
        for mid in sorted(bounce_mids, key=lambda x: int(x), reverse=True):
            res, data = mail.fetch(mid, "(RFC822)")
            if res != "OK" or not data or not isinstance(data[0], tuple):
                continue

            msg = email.message_from_bytes(data[0][1])
            recipients, error_diag = extract_bounce_metadata(msg)

            for target_email in recipients:
                print(f"\n🚨 Detected Delivery Failure for: {target_email}")
                print(f"   Diagnostic: {error_diag[:65]}")

                # 1. Add to blacklist
                record_bounced_entity(target_email, error_diag)

                # 2. Update sent_log & tool_outreach_log
                update_sent_log_bounce(target_email, error_diag)
                update_tool_log_bounce(target_email, error_diag)

                # 3. Delete bounced target from all target CSV registries
                update_target_csv_bounce(HIGH_CONVICTION_CSV, target_email)
                update_target_csv_bounce(VERIFIED_TARGETS_CSV, target_email)
                update_target_csv_bounce(MASTER_TARGETS_CSV, target_email)
                update_target_csv_bounce(TOOL_TARGETS_CSV, target_email)

                # 4. Remove from active pool
                remove_from_verified_pool(target_email)

                processed += 1

            if delete_messages:
                if not is_trash:
                    try:
                        mail.store(mid, "+X-GM-LABELS", "\\Trash")
                    except Exception:
                        try:
                            mail.copy(mid, '"[Gmail]/Trash"')
                        except Exception:
                            pass
                mail.store(mid, "+FLAGS", r"(\Deleted)")
                deleted_mids += 1
            else:
                mail.store(mid, "+FLAGS", r"(\Seen)")

        if deleted_mids > 0:
            mail.expunge()
            print(f"  🗑️ Permanently deleted & expunged {deleted_mids} bounce notification message(s) from {mailbox}.")

        return processed
    except Exception as e:
        print(f"  ⚠️ Error scanning {mailbox} for bounces: {e}")
        return 0


def delete_sent_messages_to_bounced(mail) -> int:
    """Deletes outbound sent messages addressed to any known bounced recipient across Sent Mail, All Mail, and Trash."""
    bounced_addrs = set()
    if BOUNCED_JSON.exists():
        try:
            with open(BOUNCED_JSON, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    if isinstance(item, str) and "@" in item:
                        bounced_addrs.add(item.strip().lower())
        except Exception:
            pass
    if SENT_LOG_CSV.exists():
        try:
            with open(SENT_LOG_CSV, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if "BOUNCE" in (r.get("Status") or "").upper():
                        em = (r.get("Email") or "").strip().lower()
                        if em and "@" in em:
                            bounced_addrs.add(em)
        except Exception:
            pass
    if TOOL_LOG_CSV.exists():
        try:
            with open(TOOL_LOG_CSV, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if "BOUNCE" in (r.get("status") or "").upper():
                        em = (r.get("recipient_email") or "").strip().lower()
                        if em and "@" in em:
                            bounced_addrs.add(em)
        except Exception:
            pass

    if not bounced_addrs:
        return 0

    total_deleted = 0
    for box in ('"[Gmail]/Sent Mail"', '"[Gmail]/All Mail"', '"[Gmail]/Trash"'):
        try:
            st, _ = mail.select(box)
            if st != "OK":
                continue
            is_trash = "trash" in box.lower()
            mids_to_delete = set()
            for b_em in sorted(bounced_addrs):
                s, data = mail.search(None, f'(TO "{b_em}")')
                if s == "OK" and data and data[0]:
                    for mid in data[0].split():
                        mids_to_delete.add(mid)
            if mids_to_delete:
                for mid in sorted(mids_to_delete, key=lambda x: int(x), reverse=True):
                    if not is_trash:
                        try:
                            mail.store(mid, "+X-GM-LABELS", "\\Trash")
                        except Exception:
                            try:
                                mail.copy(mid, '"[Gmail]/Trash"')
                            except Exception:
                                pass
                    mail.store(mid, "+FLAGS", r"(\Deleted)")
                mail.expunge()
                total_deleted += len(mids_to_delete)
                print(f"  🗑️ Permanently deleted & expunged {len(mids_to_delete)} outbound message(s) to bounced recipients from {box}.")
        except Exception as e:
            print(f"  ⚠️ Error cleaning bounced outbound messages in {box}: {e}")
    return total_deleted


def scan_and_learn_bounces(mail=None) -> int:
    """
    Main entry point for bounce learning engine.
    Connects to IMAP (or uses existing session), learns from all pending bounces,
    purges bounced targets from registries, and permanently deletes bounce emails from Gmail.
    """
    should_logout = False
    if not mail:
        if not GMAIL_USER or not GMAIL_APP_PASS:
            print("❌ GMAIL_USER or GMAIL_APP_PASS not set.")
            return 0
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASS)
        should_logout = True

    total_processed = 0
    try:
        print("🔍 Scanning INBOX for delivery failures & bounce notifications...")
        total_processed += process_mailbox_bounces(mail, "INBOX", delete_messages=True)

        print("🔍 Scanning [Gmail]/All Mail for delivery failures...")
        total_processed += process_mailbox_bounces(mail, '"[Gmail]/All Mail"', delete_messages=True)

        print("🔍 Scanning [Gmail]/Spam for delivery failures...")
        total_processed += process_mailbox_bounces(mail, '"[Gmail]/Spam"', delete_messages=True)

        print("🔍 Scanning [Gmail]/Trash to learn & permanently expunge bounce notifications...")
        total_processed += process_mailbox_bounces(mail, '"[Gmail]/Trash"', delete_messages=True)

        print("🔍 Purging outbound sent messages to bounced recipients...")
        delete_sent_messages_to_bounced(mail)

        print(f"✓ Bounce scanning & cleanup complete. Processed {total_processed} bounce event(s).")
    finally:
        if should_logout:
            try:
                mail.logout()
            except Exception:
                pass

    return total_processed


if __name__ == "__main__":
    count = scan_and_learn_bounces()
    sys.exit(0)
