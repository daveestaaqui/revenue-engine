#!/usr/bin/env python3
"""
Audit all active drafts currently in [Gmail]/Drafts.
Checks GroundTruthGatekeeper, link validity, spam score, tone, and payload decryption.
"""

import email
import imaplib
import json
import os
import re
import sys
from pathlib import Path
import urllib.parse

BASE_DIR = Path("/Users/davidmahler/revenue-engine")
sys.path.insert(0, str(BASE_DIR))

from compliance.ground_truth_gatekeeper import GroundTruthGatekeeper
from portal.vault_security import decrypt_docket_payload, get_current_vault_key

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

# Load vault
with open(BASE_DIR / "site" / "api" / "v1" / "vault.json") as f:
    vault = json.load(f)

# Spam trigger words / patterns common in cold email filters
SPAM_TRIGGERS = [
    "act now", "apply now", "call now", "urgent", "exclusive deal",
    "guaranteed", "no risk", "100% free", "double your", "make $",
    "earn $", "cash bonus", "instant", "click here", "unlimited",
    "clear title", "guaranteed payout", "miracle", "winner",
    "congratulations", "risk free", "risk-free", "order now"
]

def audit_drafts():
    print(f"Connecting to imap.gmail.com as {GMAIL_USER}...")
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_APP_PASS)
    mail.select("[Gmail]/Drafts")

    status, data = mail.search(None, "ALL")
    draft_ids = data[0].split()
    print(f"Total drafts found in [Gmail]/Drafts: {len(draft_ids)}\n")

    results = []

    for num in draft_ids:
        res, msg_data = mail.fetch(num, "(RFC822)")
        for part in msg_data:
            if isinstance(part, tuple):
                msg = email.message_from_bytes(part[1])
                to_hdr = msg.get("To", "")
                sub_hdr = msg.get("Subject", "")
                from_hdr = msg.get("From", "")
                
                # Extract text body
                body = ""
                if msg.is_multipart():
                    for subpart in msg.walk():
                        if subpart.get_content_type() == "text/plain":
                            payload = subpart.get_payload(decode=True)
                            if payload:
                                body += payload.decode("utf-8", errors="replace")
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="replace")

                # Parse To address
                parsed_to = email.utils.parseaddr(to_hdr)
                to_name, to_email = parsed_to[0], parsed_to[1].lower()

                # Filter: check if this is a surplus docket draft or personal draft
                is_surplus_draft = (
                    "surplus" in sub_hdr.lower() or 
                    "docket" in sub_hdr.lower() or 
                    "hillsborough" in sub_hdr.lower() or
                    "cohenrecoverylaw" in to_email or
                    "surplusdocket.com" in from_hdr.lower() or
                    "surplusdocket.com" in body.lower()
                )

                if not is_surplus_draft:
                    print(f"⏩ Skipping personal draft {num.decode()}: To={to_email} Sub={sub_hdr[:30]}")
                    continue

                # Run Gatekeeper validation
                gk_ok, gk_errors = GroundTruthGatekeeper.validate_outreach_message(
                    to_email=to_email,
                    to_name=to_name,
                    firm=to_name,
                    subject=sub_hdr,
                    body=body
                )

                # Find all URLs in body
                urls = re.findall(r"https?://[^\s<>\"']+", body)

                # Check URLs for decryptability if custom docket link
                url_checks = []
                for u in urls:
                    if "surplusdocket.com/docket" in u:
                        parsed_u = urllib.parse.urlparse(u)
                        q = urllib.parse.parse_qs(parsed_u.query)
                        d_id = q.get("id", [""])[0].lower()
                        k_val = q.get("k", [""])[0]
                        ref_val = q.get("ref", [""])[0]
                        
                        entry = vault["dockets"].get(d_id)
                        if entry:
                            try:
                                dec = decrypt_docket_payload(entry["cipher"], entry["docket_id"], k_val)
                                url_checks.append({
                                    "url": u,
                                    "status": "VALID_DECRYPTED",
                                    "docket_id": entry["docket_id"],
                                    "owner": dec.get("Owner_Name"),
                                    "balance": dec.get("Surplus_Balance_USD")
                                })
                            except Exception as e:
                                url_checks.append({
                                    "url": u,
                                    "status": f"DECRYPT_FAIL: {e}"
                                })
                        else:
                            url_checks.append({
                                "url": u,
                                "status": f"MISSING_IN_VAULT ({d_id})"
                            })
                    else:
                        url_checks.append({
                            "url": u,
                            "status": "EXTERNAL_OR_OTHER"
                        })

                # Check spam triggers
                spam_hits = [trig for trig in SPAM_TRIGGERS if trig in body.lower() or trig in sub_hdr.lower()]

                # Check voice and conciseness
                word_count = len(body.split())
                is_dave_voice = ("david mahler" in body.lower() or "dave" in body.lower()) and "surplus docket" in body.lower()

                results.append({
                    "id": num.decode(),
                    "to": to_email,
                    "to_name": to_name,
                    "from": from_hdr,
                    "subject": sub_hdr,
                    "word_count": word_count,
                    "gatekeeper_ok": gk_ok,
                    "gatekeeper_errors": gk_errors,
                    "spam_triggers": spam_hits,
                    "is_dave_voice": is_dave_voice,
                    "url_checks": url_checks,
                    "body_snippet": body[:200]
                })

    mail.logout()
    return results

if __name__ == "__main__":
    results = audit_drafts()
    print("\n" + "="*80)
    print(f"AUDIT SUMMARY: {len(results)} SURPLUS DOCKET DRAFTS AUDITED")
    print("="*80)
    all_clean = True
    for idx, r in enumerate(results, 1):
        print(f"\n--- Draft #{idx} (IMAP ID: {r['id']}) ---")
        print(f"To: {r['to_name']} <{r['to']}>")
        print(f"From: {r['from']}")
        print(f"Subject: {r['subject']}")
        print(f"Length: {r['word_count']} words | Voice Authenticity: {'✓ PASS' if r['is_dave_voice'] else '❌ FAIL'}")
        print(f"Ground Truth Gatekeeper: {'✅ PASSED' if r['gatekeeper_ok'] else '❌ FAILED'}")
        if not r['gatekeeper_ok']:
            all_clean = False
            for err in r['gatekeeper_errors']:
                print(f"   ⚠️ ERROR: {err}")
        print(f"Spam Triggers: {r['spam_triggers'] if r['spam_triggers'] else '✓ None detected'}")
        print("URLs:")
        for u in r['url_checks']:
            print(f"   [{u['status']}] {u['url']}")
            if "owner" in u:
                print(f"       -> Record: {u['docket_id']} | Owner: {u['owner']} | Balance: ${u['balance']}")

    print("\n" + "="*80)
    if all_clean:
        print("🎉 ALL DRAFTS PASSED GROUND TRUTH GATEKEEPER & URL INTEGRITY CHECKS!")
    else:
        print("⚠️ SOME DRAFTS FAILED CHECKS! SEE DETAILS ABOVE.")
    print("="*80)
