#!/usr/bin/env python3
"""
Surplus Docket — Direct Gmail Drafts Uploader
=============================================
Uploads tailored cold outreach emails directly into your Gmail 'Drafts' folder
via IMAP (imap.gmail.com) so you can review each one in Gmail and send with 1 click.

Features:
- Connects securely to sandwichfitness@gmail.com using the configured App Password
- Personalizes every email according to the attorney's state, specialty, and personality vibe
- Uses real verified case records from the live surplus feed
- Validates domains and filters out dead or unverified emails
- Skips anyone previously sent to in sent_log.csv
- Appends directly to '[Gmail]/Drafts' with proper RFC-822 headers and flags
"""

import csv
import email
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
LOG_DIR = OUTREACH_DIR / "drafts_uploaded"

# Gmail Account Credentials
GMAIL_USER = os.getenv("GMAIL_USER", "sandwichfitness@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "nxgfaiebqpmobhkp")
FROM_NAME = "David Mahler"
REPLY_TO = "david@surplusdocket.com"
SITE_URL = "https://surplusdocket.com"
STRIPE_LINK = "https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X"

# State data
STATE_NAMES = {
    "FL": "Florida", "TX": "Texas", "GA": "Georgia",
    "NC": "North Carolina", "TN": "Tennessee", "CA": "California",
    "OH": "Ohio", "IL": "Illinois", "PA": "Pennsylvania",
    "AZ": "Arizona", "SC": "South Carolina", "AL": "Alabama",
    "MS": "Mississippi", "NJ": "New Jersey", "NY": "New York",
    "MD": "Maryland",
}

STATE_STATUTES = {
    "FL": "Fla. Stat. § 197.582",
    "TX": "Tex. Tax Code § 34.04",
    "GA": "O.C.G.A. § 48-4-5",
    "NC": "N.C.G.S. § 105-374",
    "TN": "T.C.A. § 67-5-2501",
    "CA": "Cal. Rev. & Tax Code § 4675",
}

STATE_WINDOWS = {
    "FL": "120-day notice window",
    "TX": "2-year limitation from sale",
    "GA": "5-year claim window",
    "NC": "10-day upset bid period",
    "TN": "Chancery Court motion procedure",
    "CA": "1-year from deed recording",
}

# Domains confirmed dead or invalid
EXCLUDED_DOMAINS = {
    "farahlawtexas.com",
    "schuenemanlaw.com",
    "vanceassetrecoverylaw.com",
    "tampasurplusfundattorneys.com",
    "mendezassociatespa.com",
    "floridatitlerecoverygroup.com",
    "miamisurplusfundattorneys.com",
    "sterlingassetrecoverylaw.com",
    "houstonsurplusfundattorneys.com",
    "callahanassociatespc.com",
    "texastitlerecoverygroup.com",
    "moralesassetrecoverylaw.com",
    "orlandosurplusfundattorneys.com",
    "walshassociatespa.com",
    "sunshinestatetitlerecoverygroup.com",
    "jacksonvillesurplusfundattorneys.com",
    "kingsleyassetrecoverylaw.com",
    "dallassurplusfundattorneys.com",
    "bennettassociatespc.com",
    "lonestartitlerecoverygroup.com",
    "navarroassetrecoverylaw.com",
    "austinsurplusfundattorneys.com",
    "palmbeachsurplusfundattorneys.com",
    "rossassociatespa.com",
    "mercerassetrecoverylaw.com",
    "gulfcoasttitlerecoverygroup.com",
    "fortworthsurplusfundattorneys.com",
    "thorntonassociatespc.com",
    "alamotitlerecoverygroup.com",
    "davenportassetrecoverylaw.com",
    "browardsurplusfundattorneys.com",
    "sinclairassociatespa.com",
    "atlantaassetrecovery.com",
    "gaexcessfundsattorneys.com",
    "vancenclegal.com",
    "charlotteforeclosurerecovery.com",
    "mercerchancery.com",
    "nashvilletaxsurplus.com",
    "thatcherdelgadolaw.com",
    "sandiegosurplusrecovery.com",
}


def load_feed_data():
    """Load real surplus case data organized by state."""
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
                "case_no": row.get("Case_or_TaxDeed_No", ""),
                "county": row.get("County", ""),
                "balance": float(row.get("Surplus_Balance_USD", 0)),
                "fee": float(row.get("Est_Finder_Fee_USD", 0)),
            })

    for state in state_cases:
        state_cases[state].sort(key=lambda x: x["balance"], reverse=True)
    return state_cases


def get_already_sent():
    """Get all emails from sent_log.csv that were actually sent (not dry-run)."""
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
    """Load verified targets from CSV, excluding dead domains."""
    if not TARGETS_CSV.exists():
        print(f"❌ Targets file not found: {TARGETS_CSV}")
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
        return "Counsel"
    parts = full_name.strip().split()
    return parts[0] if parts else "Counsel"


def build_case_reference(state, state_cases):
    """Build 2-3 real case references for a given state."""
    cases = state_cases.get(state, [])
    if not cases:
        for s in ["FL", "TX", "GA", "CA", "NC", "TN"]:
            if state_cases.get(s):
                cases = state_cases[s]
                break

    top_cases = cases[:3]
    lines = []
    for c in top_cases:
        lines.append(
            f"  - {c['case_no']} ({c['county']} County): "
            f"${c['balance']:,.0f} surplus balance"
        )
    return "\n".join(lines)


def compose_email(target, state_cases):
    """Compose a fully personalized email matching attorney vibe and state."""
    first_name = get_first_name(target.get("Name", ""))
    firm = target.get("Firm", "your firm")
    state = target.get("State", "FL").upper()
    state_full = STATE_NAMES.get(state, state)
    specialty = target.get("Specialty", "surplus fund recovery").lower()
    practice_details = target.get("Practice_Details", "")
    style_notes = target.get("Style_Notes", "").lower()

    statute = STATE_STATUTES.get(state, "")
    window = STATE_WINDOWS.get(state, "")
    case_refs = build_case_reference(state, state_cases)

    # Tone classification
    is_formal = any(x in style_notes for x in
        ["formal", "institutional", "established", "professional", "structured", "strict"])
    is_aggressive = any(x in style_notes for x in
        ["aggressive", "results-driven", "direct"])
    is_solo = any(x in style_notes for x in
        ["solo", "boutique", "approachable", "friendly", "casual", "educator", "compassionate"])

    if is_solo or is_aggressive:
        greeting = "Hey"
        closing = "Cheers,"
    elif is_formal:
        greeting = "Hi"
        closing = "Best regards,"
    else:
        greeting = "Hi"
        closing = "Best,"

    # Pain point tailoring
    if "heir" in specialty or "estate" in specialty or "probate" in specialty:
        pain = (
            f"I know heir searches on surplus cases eat up paralegal time — "
            f"especially when half the raw county list is encumbered by bank liens. "
            f"We filter all that upstream so your team only sees clean individual "
            f"and estate equity."
        )
    elif "title" in specialty or "escrow" in specialty:
        pain = (
            f"Running title on surplus cases is already tedious — it's worse when "
            f"70% of the raw list is encumbered by senior mortgages. "
            f"We pre-scrub every institutional lien before delivery."
        )
    elif "foreclosure" in specialty:
        pain = (
            f"Post-foreclosure surplus recovery moves fast, but most raw county "
            f"lists are 70% dead leads with senior bank liens that wipe the "
            f"balance. We filter those out before delivery so your team only "
            f"works actionable claims."
        )
    elif "excess proceeds" in specialty:
        pain = (
            f"Most excess proceeds lists from the county are full of corporate "
            f"lienholders that eat the entire balance. We scrub all institutional "
            f"encumbrances upstream — every record in the feed is verified "
            f"individual or estate equity."
        )
    else:
        pain = (
            f"Most firms I talk to are still pulling surplus lists manually from "
            f"county portals — then finding out halfway through skip trace that "
            f"a bank lien eats the whole balance. We scrub all institutional "
            f"liens upstream so every record is clean equity."
        )

    # Personalized opener
    if "statewide" in practice_details.lower() or "all" in practice_details.lower():
        opener_detail = (
            f"Saw that {firm} covers {state_full} statewide — "
            f"figured this might save your team some hours."
        )
    elif any(county in practice_details.lower() for county in
             ["harris", "palm beach", "miami", "fulton", "dallas", "orange", "broward"]):
        opener_detail = (
            f"Noticed {firm} works the {state_full} market — "
            f"wanted to put this on your radar."
        )
    elif is_aggressive:
        opener_detail = (
            f"Not going to waste your time with a long pitch — "
            f"here's what we do."
        )
    else:
        opener_detail = (
            f"Quick note — I run Surplus Docket and thought this "
            f"might be relevant for {firm}."
        )

    subject = f"Scrubbed {state_full} surplus leads for {firm} (verified court docket data)"

    statute_line = f"under {statute} ({window})" if (statute and window) else "under applicable state public record rules"

    body = f"""{greeting} {first_name},

{opener_detail}

We index tax deed surplus and excess proceeds records daily across court registries and scrub out all institutional liens before delivery.

{pain}

A few live cases from this week's feed:

{case_refs}

Every record is verified against official clerk dockets {statute_line}.

Daily delivery at 7 AM EST — CSV, Excel, and JSON. Flat $249/mo, cancel anytime, no contracts.

Full methodology and sample feed: {SITE_URL}
Subscribe directly: {STRIPE_LINK}

Happy to send a free sample extract if you want to see the data first — just reply here.

{closing}
Dave Mahler
Surplus Docket
{SITE_URL}"""

    return subject, body


def upload_all_drafts():
    print("=" * 70)
    print("  🚀 DIRECT GMAIL DRAFTS UPLOADER")
    print("=" * 70)
    print(f"Target Gmail: {GMAIL_USER}")

    # 1. Load data
    state_cases = load_feed_data()
    print(f"✓ Loaded live surplus feed data ({sum(len(v) for v in state_cases.values())} records)")

    # 2. Check already sent
    already_sent = get_already_sent()
    print(f"✓ Checked sent logs ({len(already_sent)} previously sent emails to skip)")

    # 3. Load targets
    targets = load_targets()
    print(f"✓ Loaded {len(targets)} verified attorney targets")

    # Filter out already sent
    eligible_targets = [t for t in targets if t["Email"].lower() not in already_sent]
    print(f"✓ {len(eligible_targets)} targets ready for Gmail Drafts creation\n")

    if not eligible_targets:
        print("No eligible targets to process.")
        return

    # 4. Connect to Gmail via IMAP
    print(f"Connecting to imap.gmail.com as {GMAIL_USER}...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASS)
        print("✅ Logged into Gmail IMAP successfully!\n")
    except Exception as e:
        print(f"❌ Failed to connect to Gmail: {e}")
        return

    # Select Drafts folder
    drafts_mailbox = "[Gmail]/Drafts"
    status, count = mail.select(drafts_mailbox)
    if status != "OK":
        # Fallback to 'Drafts'
        drafts_mailbox = "Drafts"
        status, count = mail.select(drafts_mailbox)

    print(f"Selected mailbox: '{drafts_mailbox}' (Current drafts count: {int(count[0]) if count else 0})")
    print("-" * 70)

    uploaded = 0
    failed = 0
    manifest = []

    for i, target in enumerate(eligible_targets, 1):
        to_email = target["Email"].strip()
        to_name = target.get("Name", "Counsel").strip()
        firm = target.get("Firm", "").strip()
        state = target.get("State", "").strip()

        subject, body = compose_email(target, state_cases)

        # Create MIME message
        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = f"{FROM_NAME} <{GMAIL_USER}>"
        msg["To"] = f"{to_name} <{to_email}>"
        msg["Subject"] = subject
        msg["Reply-To"] = f"Surplus Docket <{REPLY_TO}>"
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()

        try:
            # Append draft with \Draft flag and internal date
            now_epoch = time.time()
            internal_date = imaplib.Time2Internaldate(now_epoch)
            status, res = mail.append(drafts_mailbox, r"(\Draft)", internal_date, msg.as_bytes())
            
            if status == "OK":
                uploaded += 1
                print(f"  [{i:02d}/{len(eligible_targets):02d}] ✅ Uploaded to Drafts: {to_name} ({firm} - {to_email})")
                manifest.append({
                    "idx": i,
                    "name": to_name,
                    "firm": firm,
                    "email": to_email,
                    "state": state,
                    "subject": subject,
                    "status": "DRAFT_UPLOADED",
                    "timestamp": datetime.now().isoformat(),
                })
            else:
                failed += 1
                print(f"  [{i:02d}/{len(eligible_targets):02d}] ❌ IMAP error for {to_email}: {res}")
        except Exception as e:
            failed += 1
            print(f"  [{i:02d}/{len(eligible_targets):02d}] ❌ Exception for {to_email}: {e}")

    # Logout
    mail.logout()

    # Save summary report
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = LOG_DIR / "gmail_drafts_manifest.csv"
    with open(manifest_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["idx", "name", "firm", "email", "state", "subject", "status", "timestamp"])
        writer.writeheader()
        writer.writerows(manifest)

    print("\n" + "=" * 70)
    print("  🎉 GMAIL DRAFTS UPLOAD SUMMARY")
    print("=" * 70)
    print(f"  • Drafts successfully placed in Gmail: {uploaded}")
    print(f"  • Failed                             : {failed}")
    print(f"  • Manifest saved                     : {manifest_path}")
    print("\n  👉 You can now open Gmail (web or mobile), go to your 'Drafts' folder,")
    print("     review each email, make any tweaks, and hit Send!")
    print("=" * 70)


if __name__ == "__main__":
    upload_all_drafts()
