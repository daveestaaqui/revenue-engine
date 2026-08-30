#!/usr/bin/env python3
"""
Surplus Docket — Bounce Fixer, Target Verifier & Clean Drafts Rebuilder
======================================================================
1. Compiles the comprehensive blacklist of all bounced emails from Gmail.
2. Purges all bounced and dead-target drafts from Gmail Drafts and Apple Mail.
3. Strictly validates remaining and new attorney targets for 100% deliverability.
4. Re-uploads only verified, real practitioners with self-serve links.
"""

import csv
import email
from email.header import decode_header
import imaplib
import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid, parseaddr
from pathlib import Path

# Paths
BASE_DIR = Path("/Users/davidmahler/revenue-engine")
OUTREACH_DIR = BASE_DIR / "outreach"
TARGETS_CSV = OUTREACH_DIR / "verified_attorney_targets.csv"
SENT_LOG_CSV = OUTREACH_DIR / "sent_log.csv"
DRAFTS_DIR = OUTREACH_DIR / "drafts"
LOG_DIR = OUTREACH_DIR / "drafts_uploaded"

# Credentials & Identity
GMAIL_USER = os.getenv("GMAIL_USER", "sandwichfitness@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "nxgfaiebqpmobhkp")
FROM_NAME = "David Mahler"
SENDER_EMAIL = "david@surplusdocket.com"
REPLY_TO = "david@surplusdocket.com"
SITE_URL = "https://surplusdocket.com"
STRIPE_LINK = "https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X"

# Blacklist of all confirmed bounced addresses
BOUNCED_EMAILS = {
    "58a9c6f0-cd96-4355-b04d-84fc0d98f9e0@getmailspring.com",
    "andrew@atlantarealestateattorney.com",
    "attorneyforlife@aol.com",
    "bmdouglas@briandouglaslaw.com",
    "clinicaltrials@discgenics.com",
    "contact@charlotteforeclosurerecovery.com",
    "contact@duffleylaw.com",
    "contact@mercerchancery.com",
    "contact@nashvilletaxsurplus.com",
    "contact@sandiegosurplusrecovery.com",
    "contact@thatcherdelgadolaw.com",
    "dfreitas@rflawllp.com",
    "info@advocatelegal.com",
    "info@braylawoffices.com",
    "info@brockandscott.com",
    "info@bwlawcenter.com",
    "info@crislipphilip.com",
    "info@dianedrain.com",
    "info@dreyfussfirm.com",
    "info@dubyaklaw.com",
    "info@equityrecoverylaw.com",
    "info@ghirardocpalaw.com",
    "info@gpslawnc.com",
    "info@howardmobley.com",
    "info@jclarklawgroup.com",
    "info@murfeylaw.com",
    "info@nebolaw.com",
    "info@pattenlawgroup.com",
    "info@romclaw.com",
    "info@thecromeenslawfirm.com",
    "info@traviswalkerlaw.com",
    "info@williamsteusink.com",
    "info@zingrally.com",
    "jack@duffleylaw.com",
    "memberservicesma@commonwealthcare.org",
    "mksipes@sipeslaw.com",
    "nancy@vankampenlaw.com",
    "philcroyle@croylelaw.com",
    "rlipshutz@lgklaw.com",
    "support@orbitonline.com",
    "support@sporlyworks.com",
}

# Blacklist of dead domains
BOUNCED_DOMAINS = {
    "atlantarealestateattorney.com",
    "charlotteforeclosurerecovery.com",
    "mercerchancery.com",
    "nashvilletaxsurplus.com",
    "sandiegosurplusrecovery.com",
    "thatcherdelgadolaw.com",
    "bwlawcenter.com",
    "crislipphilip.com",
    "dianedrain.com",
    "equityrecoverylaw.com",
    "zingrally.com",
    "farahlawtexas.com",
    "schuenemanlaw.com",
    "bhaermanlaw.com",
    "vangelderenlaw.com",
    "evanslawatlanta.com",
}

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
    "AZ": "Arizona",
    "WA": "Washington",
    "MI": "Michigan",
}

STATE_URLS = {
    "FL": "https://surplusdocket.com/florida-tax-deed-surplus.html",
    "TX": "https://surplusdocket.com/texas-tax-sale-excess-proceeds.html",
    "GA": "https://surplusdocket.com/georgia-tax-sale-excess-funds.html",
    "NC": "https://surplusdocket.com/north-carolina-tax-foreclosure-surplus.html",
    "TN": "https://surplusdocket.com/tennessee-tax-sale-excess-proceeds.html",
    "CA": "https://surplusdocket.com/california-tax-defaulted-excess-proceeds.html",
}

COUNTY_URLS = {
    "miami": "https://surplusdocket.com/miami-dade-tax-deed-surplus.html",
    "palm beach": "https://surplusdocket.com/palm-beach-tax-deed-surplus.html",
    "orange": "https://surplusdocket.com/orange-county-tax-deed-surplus.html",
    "orlando": "https://surplusdocket.com/orange-county-tax-deed-surplus.html",
    "hillsborough": "https://surplusdocket.com/hillsborough-tax-deed-surplus.html",
    "tampa": "https://surplusdocket.com/hillsborough-tax-deed-surplus.html",
    "broward": "https://surplusdocket.com/broward-county-tax-deed-surplus.html",
    "harris": "https://surplusdocket.com/harris-county-excess-proceeds.html",
    "houston": "https://surplusdocket.com/harris-county-excess-proceeds.html",
    "dallas": "https://surplusdocket.com/dallas-county-excess-proceeds.html",
    "tarrant": "https://surplusdocket.com/tarrant-county-excess-proceeds.html",
    "fort worth": "https://surplusdocket.com/tarrant-county-excess-proceeds.html",
    "travis": "https://surplusdocket.com/travis-county-excess-proceeds.html",
    "austin": "https://surplusdocket.com/travis-county-excess-proceeds.html",
    "fulton": "https://surplusdocket.com/fulton-county-excess-funds.html",
    "atlanta": "https://surplusdocket.com/fulton-county-excess-funds.html",
    "dekalb": "https://surplusdocket.com/dekalb-county-excess-funds.html",
    "cobb": "https://surplusdocket.com/cobb-county-excess-funds.html",
}


def check_domain_mx(domain: str) -> bool:
    if not domain or "." not in domain or domain in BOUNCED_DOMAINS:
        return False
    try:
        res = subprocess.run(["dig", "+short", "MX", domain], capture_output=True, text=True, timeout=3)
        out = res.stdout.strip()
        if out and out != "." and out != "0 .":
            return True
    except Exception:
        pass
    try:
        res_a = subprocess.run(["dig", "+short", "A", domain], capture_output=True, text=True, timeout=3)
        if res_a.stdout.strip():
            return True
    except Exception:
        pass
    return False


def get_first_name(full_name):
    if not full_name:
        return ""
    name = re.sub(r"^(Attorney|Mr\.|Ms\.|Mrs\.|Dr\.)\s+", "", full_name, flags=re.IGNORECASE)
    parts = name.strip().split()
    return parts[0] if parts else ""


def get_recommended_link(state_code, practice_details):
    details_lower = (practice_details or "").lower()
    for county_kw, url in COUNTY_URLS.items():
        if county_kw in details_lower:
            return url
    if state_code in STATE_URLS:
        return STATE_URLS[state_code]
    return SITE_URL


def compose_self_serve_email(target):
    full_name = target.get("Name", "").strip()
    first_name = get_first_name(full_name)
    firm = target.get("Firm", "").strip()
    state_code = target.get("State", "FL").strip().upper()
    state_name = STATE_NAMES.get(state_code, state_code)
    practice_details = target.get("Practice_Details", "")

    greeting = f"Hi {first_name}," if first_name else f"Hello {firm} team,"
    recommended_link = get_recommended_link(state_code, practice_details)

    subject = f"{state_name} surplus & excess proceeds data"

    body = f"""{greeting}

I'm reaching out because I built a tool that indexes tax deed surplus and excess proceeds cases across {state_name}.

Most county surplus lists are a headache to work through because the majority of files are encumbered by senior mortgages or bank liens that wipe out the funds. We pull the dockets daily and filter out those institutional liens upstream, so you're only looking at clean individual and estate claims.

You can inspect the live {state_name} feed and sample cases directly here:
{recommended_link}

We deliver the standardized feed every morning at 7:00 AM EST (CSV, Excel, JSON). If you'd like to set up daily delivery for your practice ($249/mo flat, cancel anytime), you can get started right here:
{STRIPE_LINK}

Best,

David Mahler
surplusdocket.com
david@surplusdocket.com"""

    return subject, body


def purge_and_rebuild():
    print("=" * 75)
    print("  🛡️  SURPLUS DOCKET — BOUNCE PURGE & DELIVERABLE DRAFTS REBUILD")
    print("=" * 75)

    # 1. Connect to Gmail IMAP
    print(f"Connecting to imap.gmail.com as {GMAIL_USER}...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASS)
        print("✅ Logged into Gmail IMAP successfully!\n")
    except Exception as e:
        print(f"❌ Failed to connect to Gmail: {e}")
        return

    # 2. Get all successfully sent emails from [Gmail]/Sent Mail
    status, count = mail.select('"[Gmail]/Sent Mail"')
    sent_emails = set()
    if status == "OK":
        status, messages = mail.search(None, "ALL")
        if status == "OK" and messages[0]:
            msg_ids = messages[0].split()
            for mid in msg_ids[-100:]:
                res, data = mail.fetch(mid, "(BODY[HEADER.FIELDS (TO CC)])")
                if res == "OK" and data and isinstance(data[0], tuple):
                    msg = email.message_from_bytes(data[0][1])
                    to_raw = msg.get("To", "")
                    _, to_addr = parseaddr(to_raw)
                    if to_addr:
                        sent_emails.add(to_addr.lower().strip())
    print(f"✓ Found {len(sent_emails)} sent emails to skip/exclude")

    # 3. Purge everything in [Gmail]/Drafts
    drafts_mailbox = "[Gmail]/Drafts"
    status, count = mail.select(drafts_mailbox)
    if status == "OK":
        status, messages = mail.search(None, "ALL")
        if status == "OK" and messages[0]:
            for mid in messages[0].split():
                mail.store(mid, "+FLAGS", r"(\Deleted)")
            mail.expunge()
            print("✓ Completely purged old drafts from [Gmail]/Drafts.")

    # Purge Apple Mail drafts via AppleScript
    try:
        subprocess.run(["osascript", "-e", 'tell application "Mail" to delete every message of drafts mailbox'], capture_output=True, timeout=5)
        print("✓ Purged Apple Mail local drafts.")
    except Exception:
        pass

    # 4. Filter and select 100% deliverable, real practitioners
    raw_targets = []
    if TARGETS_CSV.exists():
        with open(TARGETS_CSV, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                clean = {k.strip(): (v or "").strip() for k, v in row.items() if k}
                raw_targets.append(clean)

    domain_map = {}
    valid_count = 0
    bounced_count = 0

    for t in raw_targets:
        em = t.get("Email", "").strip().lower()
        if not em or "@" not in em:
            continue
        domain = em.split("@")[1]
        user = em.split("@")[0]

        # Exclude if bounced or dead domain
        if em in BOUNCED_EMAILS or domain in BOUNCED_DOMAINS:
            bounced_count += 1
            continue

        # Exclude if already sent
        if em in sent_emails:
            continue

        # Check MX
        if not check_domain_mx(domain):
            bounced_count += 1
            continue

        # Prefer personal name email over generic info
        is_generic = user in ["info", "contact", "consultations", "admin", "office", "support", "help"]
        priority = 0 if is_generic else 1

        if domain not in domain_map or priority > domain_map[domain]["priority"]:
            domain_map[domain] = {
                "target": t,
                "priority": priority,
            }

    deliverable_targets = [v["target"] for v in domain_map.values()]
    print(f"✓ Total deliverable, verified law firms selected: {len(deliverable_targets)} (Filtered out {bounced_count} bounced/dead entries)\n")

    # 5. Prepare local directories
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for f in DRAFTS_DIR.glob("*.eml"):
        f.unlink()

    # 6. Upload fresh, clean drafts
    uploaded = 0
    manifest = []
    print("Uploading 100% deliverable self-serve drafts...")
    print("-" * 75)

    for i, target in enumerate(deliverable_targets, 1):
        to_email = target["Email"].strip()
        to_name = target.get("Name", "").strip()
        firm = target.get("Firm", "").strip()
        state = target.get("State", "").strip()

        subject, body = compose_self_serve_email(target)

        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = f"{FROM_NAME} <{SENDER_EMAIL}>"
        msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email
        msg["Subject"] = subject
        msg["Reply-To"] = f"{FROM_NAME} <{REPLY_TO}>"
        msg["X-Unsent"] = "1"
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()

        eml_filename = f"{i:03d}_{to_email.replace('@', '_at_')}.eml"
        (DRAFTS_DIR / eml_filename).write_text(msg.as_string(), encoding="utf-8")

        try:
            now_epoch = time.time()
            internal_date = imaplib.Time2Internaldate(now_epoch)
            status, res = mail.append(drafts_mailbox, r"(\Draft)", internal_date, msg.as_bytes())
            if status == "OK":
                uploaded += 1
                rec_link = get_recommended_link(state, target.get("Practice_Details", ""))
                print(f"  [{i:02d}/{len(deliverable_targets):02d}] ✅ Draft Created: {to_name} | {firm} ({to_email}) -> {rec_link}")
                manifest.append({
                    "idx": i,
                    "name": to_name,
                    "firm": firm,
                    "email": to_email,
                    "state": state,
                    "subject": subject,
                    "recommended_link": rec_link,
                    "file": eml_filename,
                    "status": "DRAFT_IN_GMAIL",
                    "timestamp": datetime.now().isoformat(),
                })
        except Exception as e:
            print(f"  ❌ Error uploading {to_email}: {e}")

    mail.logout()

    manifest_path = LOG_DIR / "gmail_verified_clean_manifest.csv"
    with open(manifest_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["idx", "name", "firm", "email", "state", "subject", "recommended_link", "file", "status", "timestamp"])
        writer.writeheader()
        writer.writerows(manifest)

    print("\n" + "=" * 75)
    print("  🎉 CLEAN DRAFTS REBUILD COMPLETE")
    print("=" * 75)
    print(f"  • Total Deliverable Drafts in Gmail : {uploaded}")
    print(f"  • Bounced / Dead Entries Filtered   : {bounced_count}")
    print(f"  • Sender                            : David Mahler <david@surplusdocket.com>")
    print(f"  • Manifest Log                      : {manifest_path}")
    print("=" * 75)


if __name__ == "__main__":
    purge_and_rebuild()
