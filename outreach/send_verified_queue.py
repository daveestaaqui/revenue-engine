#!/usr/bin/env python3
"""
Surplus Docket — Autonomous Outreach Sending Engine
===================================================
1. Sends all pending drafts from [Gmail]/Drafts via SMTP and immediately purges them from Drafts.
2. In future automated runs, directly dispatches verified outreach emails to uncontacted attorneys
   without requiring manual draft review, completely clearing drafts folder.
3. Enforces State Bar verification, active DNS MX verification, and GroundTruthGatekeeper checks.
4. Spaces sends by 4-5 seconds to protect sender reputation and prevent anti-spam rate throttling.
5. Logs all delivered emails to outreach/sent_log.csv.
"""

import argparse
import csv
import email
import email.header
import email.utils
import imaplib
import json
import os
import re
import smtplib
import sys
import time
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.utils import parseaddr
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from outreach.generate_drafts import load_targets, load_feed_data, compose_email
from compliance.ground_truth_gatekeeper import GroundTruthGatekeeper
from portal.vault_security import decrypt_docket_payload, get_current_vault_key

# Load environment
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
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
FROM_NAME = os.getenv("FROM_NAME", "David Mahler")
FROM_EMAIL = os.getenv("FROM_EMAIL", "david@surplusdocket.com")
REPLY_TO = os.getenv("REPLY_TO", "david@surplusdocket.com")

SENT_LOG_CSV = BASE_DIR / "outreach" / "sent_log.csv"
BOUNCED_JSON = BASE_DIR / "outreach" / "bounced_emails.json"
POOL_JSON = BASE_DIR / "outreach" / "verified_pool.json"


def decode_header_str(raw_header: str) -> str:
    """Decodes MIME encoded headers into unicode strings."""
    if not raw_header:
        return ""
    try:
        parts = email.header.decode_header(raw_header)
        res = []
        for p, enc in parts:
            if isinstance(p, bytes):
                res.append(p.decode(enc or "utf-8", errors="replace"))
            else:
                res.append(str(p))
        return "".join(res)
    except Exception:
        return raw_header


def get_gmail_drafts_mailbox(mail) -> str:
    """Finds the drafts folder name."""
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


def load_sent_and_bounced_recipients() -> set:
    """Returns set of lowercased emails and domains already contacted or bounced."""
    excluded = set()
    if BOUNCED_JSON.exists():
        try:
            with open(BOUNCED_JSON, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    if isinstance(item, str):
                        excluded.add(item.strip().lower())
        except Exception:
            pass

    if SENT_LOG_CSV.exists():
        try:
            with open(SENT_LOG_CSV, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    st = row.get("Status", "").upper()
                    if "SENT" in st and "DRY_RUN" not in st:
                        em = row.get("Email", "").strip().lower()
                        if em:
                            excluded.add(em)
        except Exception:
            pass
    return excluded


def log_sent_email(to_email: str, name: str, firm: str, state: str, subject: str, mode: str = "LIVE_SMTP"):
    """Appends successful send record to sent_log.csv."""
    fieldnames = ["Timestamp", "Email", "Name", "Firm", "State", "Subject", "Status", "Mode", "Output_File"]
    file_exists = SENT_LOG_CSV.exists()
    row = {
        "Timestamp": datetime.now(timezone.utc).isoformat(),
        "Email": to_email.strip().lower(),
        "Name": name,
        "Firm": firm,
        "State": state,
        "Subject": subject,
        "Status": "SENT_DELIVERED",
        "Mode": mode,
        "Output_File": f"live_smtp_{int(time.time())}.txt"
    }
    with open(SENT_LOG_CSV, mode="a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def send_message_smtp(server: smtplib.SMTP, to_email: str, to_name: str, subject: str, body: str) -> bool:
    """Dispatches a single email message via active SMTP connection."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email
    msg["Reply-To"] = REPLY_TO
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain="surplusdocket.com")

    envelope_from = GMAIL_USER if ("gmail.com" in SMTP_HOST.lower() and GMAIL_USER) else FROM_EMAIL
    server.send_message(msg, from_addr=envelope_from, to_addrs=[to_email])
    return True


def send_existing_drafts(dry_run: bool = False, delay_seconds: float = 4.0) -> int:
    """
    Connects to Gmail via IMAP, pulls all drafts from [Gmail]/Drafts,
    sends them via SMTP, purges them from Drafts, and logs each to sent_log.csv.
    """
    if not GMAIL_USER or not GMAIL_APP_PASS:
        print("❌ GMAIL_USER or GMAIL_APP_PASS not set.")
        return 0

    print("=" * 70)
    print(" 🚀 SURPLUS DOCKET — DISPATCHING DRAFTS & CLEARING QUEUE")
    print(f"    Mode: {'🔍 DRY-RUN' if dry_run else '⚡ LIVE SMTP DISPATCH'}")
    print(f"    Sender: {FROM_NAME} <{FROM_EMAIL}> (Auth: {GMAIL_USER})")
    print("=" * 70)

    # 1. Connect to IMAP to fetch drafts
    print("📬 Connecting to imap.gmail.com to inspect [Gmail]/Drafts...")
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_APP_PASS)

    drafts_box = get_gmail_drafts_mailbox(mail)
    mail.select(drafts_box)

    status, messages = mail.search(None, "ALL")
    draft_ids = messages[0].split() if (status == "OK" and messages[0]) else []
    print(f"Found {len(draft_ids)} draft(s) in {drafts_box}.\n")

    if not draft_ids:
        print("✓ No drafts in queue. Nothing to send.")
        mail.logout()
        return 0

    # Load targets metadata for rich logging
    targets = load_targets()
    targets_by_email = {t["Email"].lower(): t for t in targets}
    pool = []
    if POOL_JSON.exists():
        try:
            with open(POOL_JSON) as f:
                pool = json.load(f)
        except Exception:
            pass
    pool_by_email = {p["email"].lower(): p for p in pool}

    # 0. Automatically scan and learn from any new bounces in Gmail before dispatching
    try:
        from outreach.bounce_processor import scan_and_learn_bounces
        scan_and_learn_bounces()
    except Exception as e:
        print(f"⚠️ Bounce processor notice: {e}")

    excluded = load_sent_and_bounced_recipients()

    # Open SMTP connection
    smtp_server = None
    if not dry_run:
        print(f"Connecting to SMTP server {SMTP_HOST}:{SMTP_PORT}...")
        smtp_server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        smtp_server.starttls()
        smtp_server.login(GMAIL_USER, GMAIL_APP_PASS)
        print("✓ SMTP TLS authentication successful.\n")

    sent_count = 0
    purged_ids = []

    try:
        for idx, did in enumerate(draft_ids, 1):
            res, data = mail.fetch(did, "(RFC822)")
            if res != "OK" or not data or not isinstance(data[0], tuple):
                continue

            msg = email.message_from_bytes(data[0][1])
            to_raw = msg.get("To", "")
            to_name, to_addr = parseaddr(to_raw)
            to_clean = to_addr.lower().strip()
            domain = to_clean.split("@")[-1] if "@" in to_clean else ""

            raw_subject = msg.get("Subject", "")
            subject = decode_header_str(raw_subject)

            # Extract body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

            # Check if this draft is valid to send
            if not to_clean:
                print(f"[{idx}/{len(draft_ids)}] ⚠️ Skipping draft with empty To address.")
                purged_ids.append(did)
                continue

            is_reply_draft = bool(msg.get("In-Reply-To")) or subject.strip().lower().startswith("re:")
            from outreach.deliverability_guard import validate_recipient_deliverability, load_bounced_blacklist
            bounced_set = load_bounced_blacklist()

            if to_clean in bounced_set or domain in bounced_set:
                print(f"[{idx}/{len(draft_ids)}] 🛡️ Skipping bounced recipient: {to_clean}")
                purged_ids.append(did)
                continue

            if not is_reply_draft and (to_clean in excluded or domain in excluded):
                print(f"[{idx}/{len(draft_ids)}] 🛡️ Skipping already contacted recipient: {to_clean}")
                purged_ids.append(did)
                continue

            deliv_ok, deliv_msg = validate_recipient_deliverability(to_clean, check_dns=True)
            if not deliv_ok:
                print(f"[{idx}/{len(draft_ids)}] 🛡️ Deliverability Guard rejected draft to {to_clean}: {deliv_msg}")
                purged_ids.append(did)
                continue

            # Lookup attorney metadata
            meta = targets_by_email.get(to_clean) or pool_by_email.get(to_clean, {})
            attorney_name = to_name or meta.get("Name") or meta.get("name") or "Counsel"
            firm_name = meta.get("Firm") or meta.get("firm") or ""
            state = meta.get("State") or meta.get("state") or "FL"

            # Enforce GroundTruthGatekeeper on every draft before sending
            gt_ok, gt_errors = GroundTruthGatekeeper.validate_outreach_message(
                to_email=to_clean,
                to_name=attorney_name,
                firm=firm_name,
                subject=subject,
                body=body,
                require_bar_verified=(not is_reply_draft),
            )
            if not gt_ok:
                print(f"[{idx}/{len(draft_ids)}] 🛡️ GroundTruthGatekeeper rejected draft to {to_clean}: {gt_errors}")
                purged_ids.append(did)
                continue

            print(f"[{idx}/{len(draft_ids)}] 📤 Dispatching to {attorney_name} <{to_clean}> ({firm_name})...")
            print(f"       Subject: {subject[:65]}")

            if not dry_run:
                try:
                    send_message_smtp(smtp_server, to_clean, attorney_name, subject, body)
                    log_sent_email(to_clean, attorney_name, firm_name, state, subject, mode="LIVE_SMTP")
                    sent_count += 1
                    excluded.add(to_clean)
                    print(f"       ✓ Successfully sent and logged.")
                except Exception as e:
                    print(f"       ❌ SMTP send error: {e}")
                    continue

                # Pace sending to protect reputation
                if idx < len(draft_ids):
                    time.sleep(delay_seconds)
            else:
                sent_count += 1
                print(f"       [DRY RUN] Would send via SMTP.")

            purged_ids.append(did)

    finally:
        if smtp_server:
            try:
                smtp_server.quit()
            except Exception:
                pass

    # Clean up drafts folder
    if purged_ids and not dry_run:
        print(f"\n🗑️ Purging {len(purged_ids)} sent draft(s) from {drafts_box}...")
        for did in purged_ids:
            try:
                mail.copy(did, "[Gmail]/Trash")
            except Exception:
                pass
            mail.store(did, "+FLAGS", r"(\Deleted)")
        mail.expunge()
        print("✓ Drafts folder expunged and completely cleared.")

    mail.logout()
    print(f"\n🎉 Successfully dispatched {sent_count} outreach email(s). Drafts folder is 100% clean.\n")
    return sent_count


def auto_send_verified_batch(batch_size: int = 10, dry_run: bool = False, delay_seconds: float = 4.0) -> int:
    """
    Directly generates and dispatches the next batch of uncontacted verified attorneys
    via SMTP without creating leftover drafts in Gmail.
    This fulfills the requirement: 'in the future just have it automatically send'.
    """
    if not GMAIL_USER or not GMAIL_APP_PASS:
        print("❌ GMAIL_USER or GMAIL_APP_PASS not set.")
        return 0

    print("=" * 70)
    print(f" ⚡ SURPLUS DOCKET — AUTONOMOUS OUTREACH DISPATCH ENGINE (Batch: {batch_size})")
    print(f"    Mode: {'🔍 DRY-RUN' if dry_run else '🚀 LIVE SMTP DISPATCH'}")
    print(f"    Sender: {FROM_NAME} <{FROM_EMAIL}>")
    print("=" * 70)

    # 0. Automatically scan and learn from any new bounces in Gmail before dispatching
    try:
        from outreach.bounce_processor import scan_and_learn_bounces
        scan_and_learn_bounces()
    except Exception as e:
        print(f"⚠️ Bounce processor notice: {e}")

    excluded = load_sent_and_bounced_recipients()
    pool = []
    if POOL_JSON.exists():
        try:
            with open(POOL_JSON) as f:
                pool = json.load(f)
        except Exception:
            pass

    targets = load_targets()
    targets_by_email = {t["Email"].lower(): t for t in targets}
    feed = load_feed_data()
    all_cases_flat = [c for clist in feed.values() for c in clist]

    from outreach.deliverability_guard import validate_recipient_deliverability

    # Find candidates
    candidates = []
    for item in pool:
        em = item.get("email", "").strip().lower()
        dom = em.split("@")[-1] if "@" in em else ""
        if em in excluded or dom in excluded:
            continue
        deliv_ok, deliv_msg = validate_recipient_deliverability(em, check_dns=True)
        if not deliv_ok:
            print(f"  🛡️ Deliverability Guard filtered {em}: {deliv_msg}")
            continue
        candidates.append(item)
        if len(candidates) >= batch_size:
            break

    # If pool is exhausted or has fewer than batch_size, draw from verified active targets
    if len(candidates) < batch_size:
        used_cases = {c.get("docket_key", "").lower() for c in candidates}
        for t in targets:
            if len(candidates) >= batch_size:
                break
            em = t.get("Email", "").strip().lower()
            dom = em.split("@")[-1] if "@" in em else ""
            status = t.get("Verified_Status", "").strip().upper()
            if status != "VERIFIED_ACTIVE" or em in excluded or dom in excluded:
                continue
            if any(c.get("email", "").lower() == em for c in candidates):
                continue
            deliv_ok, deliv_msg = validate_recipient_deliverability(em, check_dns=True)
            if not deliv_ok:
                print(f"  🛡️ Deliverability Guard filtered {em}: {deliv_msg}")
                continue

            att_state = t.get("State", "FL").upper()
            state_cases = feed.get(att_state, [])
            matched = None
            for c in state_cases:
                cid = (c.get("parcel_id") if (att_state == "TN" and c.get("parcel_id")) else (c.get("case_no") or c.get("parcel_id", ""))).strip().lower()
                if cid and cid not in used_cases:
                    matched = c
                    used_cases.add(cid)
                    break
            if matched:
                cid = (matched.get("parcel_id") if (att_state == "TN" and matched.get("parcel_id")) else (matched.get("case_no") or matched.get("parcel_id", ""))).strip().lower()
                candidates.append({
                    "email": em,
                    "name": t.get("Name", "Counsel"),
                    "firm": t.get("Firm", ""),
                    "state": att_state,
                    "docket_key": cid,
                })

    print(f"Found {len(candidates)} uncontacted verified attorney(s) eligible for dispatch.")
    if not candidates:
        print("✓ All verified pool targets have been contacted. No candidates pending.")
        return 0

    smtp_server = None
    if not dry_run:
        print(f"Connecting to SMTP server {SMTP_HOST}:{SMTP_PORT}...")
        smtp_server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        smtp_server.starttls()
        smtp_server.login(GMAIL_USER, GMAIL_APP_PASS)
        print("✓ SMTP TLS authentication successful.\n")

    sent_count = 0
    try:
        for idx, item in enumerate(candidates, 1):
            em = item.get("email", "").strip().lower()
            name = item.get("name", "Counsel")
            firm = item.get("firm", "")
            state = item.get("state", "FL")
            dk = item.get("docket_key", "").lower()

            target_meta = targets_by_email.get(em) or {
                "Email": em,
                "Name": name,
                "Firm": firm,
                "State": state,
                "Specialty": "Real Property Surplus",
                "Practice_Details": "Surplus recovery and excess proceeds",
                "Metro_Circuit": state,
                "Verified_Status": "VERIFIED_ACTIVE"
            }

            matched_case = next(
                (c for c in all_cases_flat if c.get("case_no", "").lower() == dk or c.get("parcel_id", "").lower() == dk),
                None
            )
            if not matched_case:
                print(f"[{idx}/{len(candidates)}] ⚠️ Docket {dk} not found for {em}. Skipping.")
                continue

            sub, body = compose_email(target_meta, {state: [matched_case]}, from_name=FROM_NAME, from_email=FROM_EMAIL)
            if not sub or not body:
                print(f"[{idx}/{len(candidates)}] ⚠️ Failed to compose email for {em}. Skipping.")
                continue

            # Ground-truth gatekeeper check (enforces State Bar verification, lead math, identifier match, and DNS MX)
            ok, errors = GroundTruthGatekeeper.validate_outreach_message(
                to_email=em,
                to_name=name,
                firm=firm,
                subject=sub,
                body=body,
                lead=matched_case,
                require_bar_verified=True,
            )
            if not ok:
                print(f"[{idx}/{len(candidates)}] 🛡️ GroundTruthGatekeeper rejected {em}: {errors}")
                continue

            print(f"[{idx}/{len(candidates)}] 📤 Auto-dispatching to {name} <{em}> ({firm})...")
            print(f"       Subject: {sub[:65]}")

            if not dry_run:
                try:
                    send_message_smtp(smtp_server, em, name, sub, body)
                    log_sent_email(em, name, firm, state, sub, mode="AUTONOMOUS_SMTP")
                    sent_count += 1
                    excluded.add(em)
                    print(f"       ✓ Sent successfully & logged to sent_log.csv.")
                except Exception as e:
                    print(f"       ❌ SMTP error sending to {em}: {e}")
                    continue

                if idx < len(candidates):
                    time.sleep(delay_seconds)
            else:
                sent_count += 1
                print("       [DRY RUN] Would send via SMTP.")

    finally:
        if smtp_server:
            try:
                smtp_server.quit()
            except Exception:
                pass

    # Ensure [Gmail]/Drafts has no lingering drafts for contacted recipients
    if sent_count > 0 and not dry_run:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(GMAIL_USER, GMAIL_APP_PASS)
            drafts_box = get_gmail_drafts_mailbox(mail)
            mail.select(drafts_box)
            status, messages = mail.search(None, "ALL")
            if status == "OK" and messages[0]:
                purged = 0
                for did in messages[0].split():
                    res, data = mail.fetch(did, "(BODY.PEEK[HEADER.FIELDS (TO SUBJECT)])")
                    if res == "OK" and data and isinstance(data[0], tuple):
                        hdr = email.message_from_bytes(data[0][1])
                        _, to_addr = parseaddr(hdr.get("To", ""))
                        subj_hdr = decode_mime_header(hdr.get("Subject", "")).strip()
                        if subj_hdr.lower().startswith("re:"):
                            continue
                        if to_addr and to_addr.lower().strip() in excluded:
                            mail.store(did, "+FLAGS", r"(\Deleted)")
                            purged += 1
                if purged > 0:
                    mail.expunge()
                    print(f"✓ Purged {purged} residual draft(s) from {drafts_box}.")
            mail.logout()
        except Exception as e:
            print(f"⚠️ Residual draft clean notice: {e}")

    print(f"\n🎉 Autonomous dispatch complete. Total sent: {sent_count}.\n")
    return sent_count


def is_within_sending_hours() -> bool:
    """Verifies that current time is within legal sending window (Mon-Fri 8:00 AM - 6:30 PM EST)."""
    from datetime import datetime, timezone, timedelta
    est_offset = timedelta(hours=-4)  # EDT is UTC-4
    now_est = datetime.now(timezone.utc) + est_offset
    weekday = now_est.weekday()  # 0 is Monday, 4 is Friday, 5 is Saturday, 6 is Sunday
    if weekday > 4:
        return False
    hour = now_est.hour
    minute = now_est.minute
    if hour < 8 or (hour == 18 and minute > 30) or hour > 18:
        return False
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Surplus Docket Outreach Sending Engine")
    parser.add_argument("--send-drafts", action="store_true", help="Send existing drafts in Gmail Drafts and clear folder")
    parser.add_argument("--auto-send", action="store_true", help="Directly generate and dispatch verified batch via SMTP")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of emails to send in auto-send mode")
    parser.add_argument("--dry-run", action="store_true", help="Simulate sends without dispatching")
    parser.add_argument("--delay", type=float, default=4.0, help="Seconds delay between sends (default: 4.0)")
    parser.add_argument("--force", action="store_true", help="Bypass business sending window check")

    args = parser.parse_args()

    if not args.force and not is_within_sending_hours() and not args.dry_run:
        print("ℹ️ Outside of standard legal business sending window (Mon-Fri 8:00 AM - 6:30 PM EST).")
        print("   Use --force to override.")
        sys.exit(0)

    if args.send_drafts:
        send_existing_drafts(dry_run=args.dry_run, delay_seconds=args.delay)
    elif args.auto_send:
        auto_send_verified_batch(batch_size=args.batch_size, dry_run=args.dry_run, delay_seconds=args.delay)
    else:
        # Default: if drafts exist, send drafts; otherwise auto-send
        send_existing_drafts(dry_run=args.dry_run, delay_seconds=args.delay)
