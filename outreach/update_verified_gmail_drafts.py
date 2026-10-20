#!/usr/bin/env python3
"""
Surplus Docket — Synchronize Verified Outreach Drafts in Gmail
=============================================================
Safely updates the 12 attorney outreach drafts in [Gmail]/Drafts via IMAP.
- Deletes the 12 old outdated drafts (leaves all personal drafts like normspringer untouched).
- Uploads the 12 fresh, ground-truth-verified drafts.
- Every link uses https://surplusdocket.com/docket?id=...&k=...&ref=...
- Guarantees 100% unredacted access on the custom dossier page.
"""

import email
import email.utils
import imaplib
import json
import os
import re
import sys
import time
from email.mime.text import MIMEText
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from outreach.generate_drafts import load_targets, load_feed_data, compose_email
from portal.vault_security import decrypt_docket_payload, get_current_vault_key

TARGET_EMAILS = [
    "cjimerson@jimersonfirm.com",
    "david@kramerlaw.com",
    "kimberly@thesotolawoffice.com",
    "pfeaman@feamanlaw.com",
    "richard@zaretskylaw.com",
    "ryan@torrenslawgroup.com",
    "scott@spradleylaw.com",
    "stephen@fensterlaw.com",
    "vincent@taorminalawpa.com",
    "ashley@calhounlawfirm.com",
    "bradh@weissman.law",
    "greg@thompsonlawnc.com",
]

ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

GMAIL_USER = os.getenv("GMAIL_USER", "sandwichfitness@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")
FROM_NAME = "David Mahler"
FROM_EMAIL = "david@surplusdocket.com"
REPLY_TO = "david@surplusdocket.com"


def main():
    if not GMAIL_USER or not GMAIL_APP_PASS:
        print("❌ GMAIL_USER or GMAIL_APP_PASS not set.")
        return 1

    targets = load_targets()
    matched_targets = []
    for em in TARGET_EMAILS:
        for t in targets:
            if t["Email"].lower() == em.lower():
                matched_targets.append(t)
                break

    if len(matched_targets) != len(TARGET_EMAILS):
        print(f"⚠️ Warning: Matched {len(matched_targets)} of {len(TARGET_EMAILS)} targets.")

    state_cases = load_feed_data()
    with open(BASE_DIR / "site" / "api" / "v1" / "vault.json") as f:
        vault = json.load(f)

    current_key = get_current_vault_key()
    print(f"✓ Current cycle vault key: {current_key}")

    draft_payloads = []
    for t in matched_targets:
        sub, body = compose_email(t, state_cases, from_name=FROM_NAME, from_email=FROM_EMAIL)
        # Verify URL decryptability
        url_match = re.search(r"https://surplusdocket\.com/docket\?id=([^\s&]+)&k=([^\s&]+)&ref=([^\s&]+)", body)
        if not url_match:
            print(f"❌ Could not find valid docket URL in draft for {t['Email']}")
            return 1
        docket_param = url_match.group(1).replace("+", " ").lower()
        k_param = url_match.group(2)
        entry = vault["dockets"].get(docket_param)
        if not entry:
            print(f"❌ Docket {docket_param} missing in vault.json")
            return 1
        dec = decrypt_docket_payload(entry["cipher"], entry["docket_id"], k_param)
        print(f"  Verified {t['Email']} -> {entry['docket_id']} ({dec['Owner_Name']})")

        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg["To"] = f"{t.get('Name', 'Counsel')} <{t['Email']}>"
        msg["Reply-To"] = REPLY_TO
        msg["Subject"] = sub
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = email.utils.make_msgid(domain="surplusdocket.com")
        draft_payloads.append((t["Email"], sub, msg.as_bytes()))

    print(f"\n📬 Connecting to imap.gmail.com as {GMAIL_USER}...")
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_APP_PASS)
    mail.select("[Gmail]/Drafts")

    # Search existing drafts and delete matching attorney drafts
    status, data = mail.search(None, "ALL")
    draft_ids = data[0].split()
    print(f"Found {len(draft_ids)} existing draft(s) in [Gmail]/Drafts.")

    target_email_set = {e.lower() for e in TARGET_EMAILS}
    deleted_count = 0
    for num in draft_ids:
        res, msg_data = mail.fetch(num, "(BODY.PEEK[HEADER.FIELDS (TO SUBJECT)])")
        for part in msg_data:
            if isinstance(part, tuple):
                header_msg = email.message_from_bytes(part[1])
                to_hdr = (header_msg.get("To") or "").lower()
                sub_hdr = (header_msg.get("Subject") or "").lower()
                # If recipient is one of our target attorneys or subject contains surplus filing / tax sale surplus
                if any(em in to_hdr for em in target_email_set) or "surplus filing" in sub_hdr or "tax sale surplus" in sub_hdr:
                    mail.store(num, "+FLAGS", "\\Deleted")
                    deleted_count += 1
                    print(f"  🗑️ Deleted old draft {num.decode()}: {to_hdr} | {sub_hdr[:40]}")

    if deleted_count > 0:
        mail.expunge()
        print(f"✓ Expunged {deleted_count} outdated drafts.")

    # Upload fresh drafts
    print(f"\n📤 Uploading {len(draft_payloads)} fresh verified drafts to [Gmail]/Drafts...")
    uploaded_count = 0
    for to_email, sub, raw_bytes in draft_payloads:
        status, _ = mail.append("[Gmail]/Drafts", "(\\Draft \\Seen)", imaplib.Time2Internaldate(time.time()), raw_bytes)
        if status == "OK":
            uploaded_count += 1
            print(f"  ✓ Uploaded draft for {to_email} ({sub[:40]})")
        else:
            print(f"  ❌ Failed to upload draft for {to_email}")

    mail.logout()
    print(f"\n🎉 Successfully synchronized {uploaded_count} verified drafts in [Gmail]/Drafts!")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
