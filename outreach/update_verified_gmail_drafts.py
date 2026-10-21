#!/usr/bin/env python3
"""
Surplus Docket — Synchronize & Replenish Verified Outreach Drafts in Gmail
========================================================================
Autonomously maintains a queue of 12 ground-truth-verified attorney outreach drafts in [Gmail]/Drafts.
- Inspects [Gmail]/Sent Mail, sent_log.csv, and bounced_emails.json so no contacted/bounced attorney is ever drafted.
- Keeps valid, uncontacted drafts already in [Gmail]/Drafts to avoid unnecessary churn.
- Purges outdated, invalid, bounced, or already-sent drafts.
- Automatically replenishes the queue up to target_count (default 12) with uncontacted State-Bar-verified attorneys.
- Every attorney receives a unique, real docket in their jurisdiction with an individual owner.
- Every link uses https://surplusdocket.com/docket?id=...&k=... for 100% unredacted access without sales/activation buttons.
- Runs both standalone and as a replenishment module inside auto_responder_and_draft_cleaner.py.
"""

import email
import email.header
import email.utils
import imaplib
import json
import os
import re
import sys
import time
import urllib.parse
from email.mime.text import MIMEText
from email.utils import parseaddr
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from outreach.generate_drafts import load_targets, load_feed_data, compose_email
from compliance.ground_truth_gatekeeper import GroundTruthGatekeeper
from portal.vault_security import decrypt_docket_payload, get_current_vault_key

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
FROM_NAME = "David Mahler"
FROM_EMAIL = "david@surplusdocket.com"
REPLY_TO = "david@surplusdocket.com"
POOL_JSON_FILE = BASE_DIR / "outreach" / "verified_pool.json"
SENT_LOG_CSV = BASE_DIR / "outreach" / "sent_log.csv"
BOUNCED_JSON = BASE_DIR / "outreach" / "bounced_emails.json"


def get_gmail_drafts_mailbox(mail) -> str:
    """Finds the correct Drafts folder name on the IMAP server."""
    status, folder_list = mail.list()
    if status == "OK" and folder_list:
        for f in folder_list:
            if isinstance(f, bytes):
                f = f.decode("utf-8", errors="ignore")
            if "\\Drafts" in f:
                match = re.search(r'"([^"]+)"$', f) or re.search(r'([^\s]+)$', f)
                if match:
                    return match.group(1).strip()
    return "[Gmail]/Drafts"


def load_sent_and_bounced_recipients(mail=None) -> set:
    """Collects all email addresses and domains that have been sent or bounced."""
    excluded = set()

    # 1. Bounced file
    if BOUNCED_JSON.exists():
        try:
            with open(BOUNCED_JSON, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    if isinstance(item, str):
                        excluded.add(item.strip().lower())
        except Exception:
            pass

    # 2. Sent log CSV
    if SENT_LOG_CSV.exists():
        try:
            import csv
            with open(SENT_LOG_CSV, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    st = row.get("Status", "").upper()
                    if "SENT" in st and "DRY_RUN" not in st:
                        em = row.get("Email", "").strip().lower()
                        if em:
                            excluded.add(em)
        except Exception:
            pass

    # 3. IMAP Sent Mail check if mail is connected
    if mail:
        try:
            status, _ = mail.select('"[Gmail]/Sent Mail"', readonly=True)
            if status == "OK":
                status, messages = mail.search(None, "ALL")
                if status == "OK" and messages[0]:
                    msg_ids = messages[0].split()
                    for mid in reversed(msg_ids[-100:]):
                        res, data = mail.fetch(mid, "(BODY[HEADER.FIELDS (TO CC)])")
                        if res == "OK" and data and isinstance(data[0], tuple):
                            hdr = email.message_from_bytes(data[0][1])
                            for field in ("To", "Cc"):
                                raw = hdr.get(field, "")
                                if raw:
                                    _, addr = parseaddr(raw)
                                    if addr:
                                        excluded.add(addr.lower().strip())
        except Exception as e:
            print(f"  ⚠️ Warning reading [Gmail]/Sent Mail: {e}")

    return excluded


def load_verified_pool() -> list:
    """Loads pre-verified attorney pool from outreach/verified_pool.json."""
    if POOL_JSON_FILE.exists():
        try:
            with open(POOL_JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception as e:
            print(f"  ⚠️ Warning loading {POOL_JSON_FILE}: {e}")
    return []


def build_draft_message(target: dict, lead_case: dict) -> tuple:
    """Composes and validates an outreach draft message."""
    sub, body = compose_email(target, {target["State"]: [lead_case]}, from_name=FROM_NAME, from_email=FROM_EMAIL)
    if not sub or not body:
        return None, None, ["Failed to compose email"]

    to_email = target.get("Email", "").strip().lower()
    ok, errors = GroundTruthGatekeeper.validate_outreach_message(
        to_email=to_email,
        to_name=target.get("Name", "Counsel"),
        firm=target.get("Firm", ""),
        subject=sub,
        body=body,
        lead=lead_case,
    )
    if not ok:
        return None, None, errors

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = f"{target.get('Name', 'Counsel')} <{to_email}>"
    msg["Reply-To"] = REPLY_TO
    msg["Subject"] = sub
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain="surplusdocket.com")
    return sub, msg.as_bytes(), []


def replenish_gmail_drafts_if_needed(mail, target_count=12) -> int:
    """
    Ensures [Gmail]/Drafts contains target_count verified, uncontacted drafts.
    - Purges any sent or bounced drafts.
    - Retains valid uncontacted drafts.
    - Adds fresh drafts from the verified pool until target_count is reached.
    """
    excluded_contacts = load_sent_and_bounced_recipients(mail)
    drafts_box = get_gmail_drafts_mailbox(mail)
    status, _ = mail.select(drafts_box)
    if status != "OK":
        print(f"❌ Failed to select drafts mailbox: {drafts_box}")
        return 0

    status, messages = mail.search(None, "ALL")
    draft_ids = messages[0].split() if (status == "OK" and messages[0]) else []

    current_draft_recipients = set()
    purged_count = 0

    # Purge old/invalid drafts and track current valid recipients
    for did in reversed(draft_ids):
        res, data = mail.fetch(did, "(BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT)])")
        if res == "OK" and data and isinstance(data[0], tuple):
            hdr = email.message_from_bytes(data[0][1])
            from_hdr = (hdr.get("From") or "").lower()
            to_raw = hdr.get("To") or ""
            _, to_addr = parseaddr(to_raw)
            to_clean = to_addr.lower().strip() if to_addr else ""
            raw_sub = hdr.get("Subject") or ""

            # Check if this draft should be purged
            should_purge = False
            domain = to_clean.split("@")[-1] if "@" in to_clean else ""

            if not to_clean:
                should_purge = True
            elif to_clean in excluded_contacts or domain in excluded_contacts:
                should_purge = True
            elif "elena" in from_hdr:
                should_purge = True
            elif to_clean in current_draft_recipients:
                # Duplicate draft for same recipient
                should_purge = True

            if should_purge:
                try:
                    mail.copy(did, "[Gmail]/Trash")
                except Exception:
                    pass
                mail.store(did, "+FLAGS", r"(\Deleted)")
                purged_count += 1
                print(f"  🗑️ Purged invalid/sent draft: {to_clean} | {raw_sub[:40]}")
            else:
                current_draft_recipients.add(to_clean)

    if purged_count > 0:
        mail.expunge()
        print(f"✓ Expunged {purged_count} outdated draft(s) from {drafts_box}.")

    print(f"📊 Active valid drafts currently in {drafts_box}: {len(current_draft_recipients)} (Target: {target_count})")
    needed = target_count - len(current_draft_recipients)
    if needed <= 0:
        print(f"✓ Draft queue is fully stocked ({len(current_draft_recipients)} >= {target_count}). No new drafts needed.")
        return len(current_draft_recipients)

    print(f"➕ Replenishing {needed} draft(s) to reach target of {target_count}...")
    pool = load_verified_pool()
    targets = load_targets()
    targets_by_email = {t["Email"].lower(): t for t in targets}
    feed = load_feed_data()
    all_cases_flat = [c for clist in feed.values() for c in clist]

    added_count = 0
    for item in pool:
        if added_count >= needed:
            break
        em = item.get("email", "").strip().lower()
        dom = em.split("@")[-1] if "@" in em else ""
        if em in excluded_contacts or dom in excluded_contacts or em in current_draft_recipients:
            continue

        target_meta = targets_by_email.get(em)
        if not target_meta:
            target_meta = {
                "Email": em,
                "Name": item.get("name", "Counsel"),
                "Firm": item.get("firm", ""),
                "State": item.get("state", "FL"),
                "Specialty": "Civil Litigation / Foreclosure Surplus",
                "Practice_Details": "Real property surplus recovery",
                "Metro_Circuit": item.get("state", "FL"),
                "Verified_Status": "VERIFIED_ACTIVE"
            }

        dk = item.get("docket_key", "").lower()
        matched_case = next(
            (c for c in all_cases_flat if c.get("case_no", "").lower() == dk or c.get("parcel_id", "").lower() == dk),
            None
        )
        if not matched_case:
            continue

        sub, raw_bytes, errors = build_draft_message(target_meta, matched_case)
        if not raw_bytes:
            print(f"  ⚠️ Skipping {em}: {errors}")
            continue

        append_status, _ = mail.append(drafts_box, "(\\Draft \\Seen)", imaplib.Time2Internaldate(time.time()), raw_bytes)
        if append_status == "OK":
            current_draft_recipients.add(em)
            added_count += 1
            print(f"  ✓ [{len(current_draft_recipients)}/{target_count}] Created verified draft for {em} ({item.get('name')}) — {sub[:42]}")
        else:
            print(f"  ❌ Failed to append draft for {em}")

    total_drafts = len(current_draft_recipients)
    print(f"🎉 Replenishment complete. Queue now has {total_drafts} verified draft(s) ready to send.")
    return total_drafts


def main():
    if not GMAIL_USER or not GMAIL_APP_PASS:
        print("❌ GMAIL_USER or GMAIL_APP_PASS not set.")
        return 1

    print(f"📬 Connecting to imap.gmail.com as {GMAIL_USER}...")
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    try:
        mail.login(GMAIL_USER, GMAIL_APP_PASS)
        replenish_gmail_drafts_if_needed(mail, target_count=12)
    finally:
        try:
            mail.logout()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
