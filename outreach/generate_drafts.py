#!/usr/bin/env python3
"""
Surplus Docket — Personalized Draft Email Generator
====================================================
Generates individualized .eml draft files that can be opened directly in
Apple Mail or any email client for review and one-click sending.

Each email is:
- Written in Dave's authentic voice (direct, conversational, data-first)
- Customized with state-specific real surplus case data from the live feed
- Personalized to the attorney's specialty, firm type, and practice area
- De-duplicated against the sent_log.csv to avoid re-contacting anyone

Output: Individual .eml files in outreach/drafts/ ready to open and send.
"""

import argparse
import csv
import email
import email.utils
import json
import os
import random
import re
import smtplib
import sys
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTREACH_DIR = BASE_DIR / "outreach"
TARGETS_CSV = OUTREACH_DIR / "master_ranked_attorney_targets.csv"
if not TARGETS_CSV.exists():
    TARGETS_CSV = OUTREACH_DIR / "verified_attorney_targets.csv"

SENT_LOG_CSV = OUTREACH_DIR / "sent_log.csv"
DRAFTS_DIR = OUTREACH_DIR / "drafts"
FEED_CSV = BASE_DIR / "exports" / "Master_Surplus_Lead_Feed.csv"
UNSUBSCRIBED_FILE = OUTREACH_DIR / "unsubscribed_urls.json"

# Optional local .env loading
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as ef:
            for line in ef:
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

DEFAULT_FROM_NAME = os.getenv("FROM_NAME", "Surplus Docket Intelligence")
DEFAULT_FROM_EMAIL = os.getenv("FROM_EMAIL", "dockets@surplusdocket.com")
DEFAULT_REPLY_TO = os.getenv("REPLY_TO", "dockets@surplusdocket.com")

# Domains confirmed dead, unverified, or historical test entries
DEAD_DOMAINS = {
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
    "example.com",
}

STATE_NAMES = {
    "FL": "Florida", "TX": "Texas", "GA": "Georgia",
    "NC": "North Carolina", "TN": "Tennessee", "CA": "California",
    "OH": "Ohio", "IL": "Illinois", "PA": "Pennsylvania",
    "AZ": "Arizona", "SC": "South Carolina", "AL": "Alabama",
    "MS": "Mississippi", "NJ": "New Jersey", "NY": "New York",
    "MD": "Maryland",
}

STRIPE_LINK = "https://buy.stripe.com/4gM14n8yq9vl0vrb0i0ZW21"
SITE_URL = "https://surplusdocket.com"

PRACTICE_URLS = {
    "tax_sale": "https://surplusdocket.com/for/tax-sale-litigation.html",
    "probate": "https://surplusdocket.com/for/probate-estate-surplus.html",
    "foreclosure": "https://surplusdocket.com/for/mortgage-foreclosure.html",
}


def get_target_practice_group(specialty, practice_details=""):
    combined = f"{specialty} {practice_details}".lower()
    if any(k in combined for k in ["probate", "estate", "heir", "trust", "administration", "decedent"]):
        return "probate", PRACTICE_URLS["probate"]
    elif any(k in combined for k in ["foreclosure", "mortgage", "heloc", "junior lien", "lien"]):
        return "foreclosure", PRACTICE_URLS["foreclosure"]
    else:
        return "tax_sale", PRACTICE_URLS["tax_sale"]

# State-specific statutory references
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


def get_already_contacted():
    """Read sent_log.csv to find emails that were actually SENT (not dry-run)."""
    contacted = set()
    if not SENT_LOG_CSV.exists():
        return contacted

    with open(SENT_LOG_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get("Status", "").strip()
            email = row.get("Email", "").strip().lower()
            if "SENT" in status and "DRY_RUN" not in status:
                contacted.add(email)
    return contacted


def load_targets():
    """Load verified attorney targets from CSV."""
    if not TARGETS_CSV.exists():
        print(f"  Target file not found: {TARGETS_CSV}")
        return []

    targets = []
    with open(TARGETS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {}
            for k, v in row.items():
                if k:
                    clean[k.strip()] = (v or "").strip()
            email = clean.get("Email", "")
            # Skip dead domains
            domain = email.split("@")[1] if "@" in email else ""
            if domain in DEAD_DOMAINS:
                continue
            if email:
                targets.append(clean)
    return targets


def get_first_name(full_name):
    if not full_name:
        return "Counsel"
    parts = full_name.strip().split()
    first = parts[0] if parts else "Counsel"
    if first.lower() in ("mr.", "ms.", "mrs.", "dr.", "atty.", "attorney"):
        first = parts[1] if len(parts) > 1 else "Counsel"
    return first


def get_unsubscribed_domains():
    """Collect domains or URLs that unsubscribed."""
    unsub = set()
    if UNSUBSCRIBED_FILE.exists():
        try:
            with open(UNSUBSCRIBED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if isinstance(item, str):
                        unsub.add(item.lower())
        except Exception:
            pass
    return unsub


def build_case_reference(state, state_cases):
    """Build 2-3 real case references for a given state."""
    cases = state_cases.get(state, [])
    if not cases:
        # Fallback to the closest covered states
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


def compose_email(target, state_cases, from_name=DEFAULT_FROM_NAME, from_email=DEFAULT_FROM_EMAIL):
    """Compose a fully personalized, professional outreach email."""
    first_name = get_first_name(target.get("Name", ""))
    firm = target.get("Firm", "your firm")
    state = target.get("State", "FL").upper()
    state_full = STATE_NAMES.get(state, state)
    specialty = target.get("Specialty", "surplus fund recovery").lower()
    practice_details = target.get("Practice_Details", "")
    style_notes = target.get("Style_Notes", "").lower()

    statute = STATE_STATUTES.get(state, "applicable state statutes")
    window = STATE_WINDOWS.get(state, "statutory claim window")
    case_refs = build_case_reference(state, state_cases)

    # Determine tone
    is_formal = any(x in style_notes for x in
        ["formal", "institutional", "established", "professional", "structured", "strict"])
    is_aggressive = any(x in style_notes for x in
        ["aggressive", "results-driven", "direct"])
    is_solo = any(x in style_notes for x in
        ["solo", "boutique", "approachable", "friendly", "casual"])

    if is_solo or is_aggressive:
        greeting = "Hey"
        closing = "Cheers,"
    elif is_formal:
        greeting = "Hi"
        closing = "Best regards,"
    else:
        greeting = "Hi"
        closing = "Best,"

    # Build the pain-point paragraph based on specialty
    if "heir" in specialty or "estate" in specialty or "probate" in specialty:
        pain = (
            "I know heir searches on surplus cases eat up paralegal time — "
            "especially when half the raw county list is encumbered by senior mortgages. "
            "We filter all that upstream so your team only sees clean individual "
            "and estate equity."
        )
    elif "title" in specialty or "escrow" in specialty:
        pain = (
            "Running title on surplus cases is already tedious — it's worse when "
            "70% of the raw list is encumbered by senior mortgages. "
            "We pre-scrub every institutional lien before delivery."
        )
    elif "foreclosure" in specialty:
        pain = (
            "Post-foreclosure surplus recovery moves fast, but most raw county "
            "lists are 70% dead leads with senior bank liens that wipe the "
            "balance. We filter those out before delivery so your team only "
            "works actionable claims."
        )
    elif "excess proceeds" in specialty:
        pain = (
            "Most excess proceeds lists from the county are full of corporate "
            "lienholders that eat the entire balance. We scrub all institutional "
            "encumbrances upstream — every record in the feed is verified "
            "individual or estate equity."
        )
    else:
        pain = (
            "Most firms I talk to are still pulling surplus lists manually from "
            "county portals — then finding out halfway through skip trace that "
            "a bank lien eats the whole balance. We scrub all institutional "
            "liens upstream so every record is clean equity."
        )

    # Personalize the opener based on what we know about the firm
    if "statewide" in practice_details.lower() or "all" in practice_details.lower():
        opener_detail = f"Saw that {firm} covers {state_full} statewide — figured this might save your team some hours."
    elif any(county in practice_details.lower() for county in
             ["harris", "palm beach", "miami", "fulton", "dallas", "orange"]):
        opener_detail = f"Noticed {firm} works the {state_full} market — wanted to put this on your radar."
    elif is_aggressive:
        opener_detail = "Not going to waste your time with a long pitch — here's what we do."
    else:
        if "David" in from_name:
            opener_detail = f"Quick note — I run Surplus Docket and thought this might be relevant for {firm}."
        else:
            opener_detail = f"Quick note from Surplus Docket — thought this might be relevant for {firm}."

    practice_group, practice_url = get_target_practice_group(specialty, practice_details)

    # Build subject — practice-aligned, non-spammy
    if practice_group == "probate":
        subject = f"{state_full} surplus records involving estate & heir matters — {firm}"
    elif practice_group == "foreclosure":
        subject = f"{state_full} foreclosure surplus & junior lien docket intelligence — {firm}"
    else:
        subject = f"Scrubbed {state_full} tax sale surplus records for {firm} (verified court docket data)"

    # Signature block
    if from_name == "Elena Brooks":
        sig = f"Elena Brooks\nSurplus Docket\n{SITE_URL}"
    elif "David" in from_name:
        sig = f"David Mahler\nSurplus Docket\n{SITE_URL}"
    else:
        sig = f"{from_name}\nSurplus Docket\n{SITE_URL} • {from_email}"

    # Compose body
    body = f"""{greeting} {first_name},

{opener_detail}

We index tax deed surplus and excess proceeds records daily across court registries and scrub out all institutional liens before delivery.

{pain}

A few live cases from this week's feed:

{case_refs}

Every record is verified against official clerk dockets{(' under ' + statute + ' (' + window + ')') if statute else ''}.

Daily delivery at 7:00 AM EST — CSV, Excel, and JSON. Flat $249/mo, cancel anytime, no contracts.

Dedicated practice workflow: {practice_url}
Technical methodology: {SITE_URL}/methodology.html
Subscribe directly: {STRIPE_LINK}

Happy to send a free sample extract if you want to see the data first — just reply here.

{closing}
{sig}

---
Legal Notice & Regulatory Disclaimer: Surplus Docket is a specialized legal technology and court records intelligence service, not a law firm. Surplus Docket provides research and workflow software, not legal advice, title opinions, or representation. Records may be incomplete or change after retrieval. Counsel must independently verify balances, ownership, standing, priority, and deadlines."""

    return subject, body


def create_eml_file(to_email, to_name, subject, body, output_path, from_name=DEFAULT_FROM_NAME, from_email=DEFAULT_FROM_EMAIL, reply_to=DEFAULT_REPLY_TO):
    """Create a standards-compliant .eml file marked as draft."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = f"{to_name} <{to_email}>"
    msg["Subject"] = subject
    msg["Reply-To"] = f"Surplus Docket <{reply_to}>"
    msg["X-Unsent"] = "1"  # Marks as draft in Apple Mail
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain="surplusdocket.com")

    output_path.write_text(msg.as_string(), encoding="utf-8")


def log_sent_status(log_path: Path, entry: dict):
    """Logs generation/send status to CSV log tracker."""
    fieldnames = ["Timestamp", "Email", "Name", "Firm", "State", "Subject", "Status", "Mode", "Output_File"]
    file_exists = log_path.exists()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, mode="a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(entry)


def main():
    parser = argparse.ArgumentParser(description="Surplus Docket — Autonomous Outreach Drafts & Live SMTP Dispatcher")
    parser.add_argument("--limit", type=int, default=12, help="Number of outreach emails to process per batch (default: 12)")
    parser.add_argument("--state", type=str, default="", help="Filter by state abbreviation (FL, TX, GA, CA, NC, TN)")
    parser.add_argument("--send", "--live", action="store_true", help="Perform live SMTP sending (default: dry-run draft generation)")
    parser.add_argument("--dry-run", action="store_true", help="Force preview/draft mode without live sending")
    parser.add_argument("--test-recipient", type=str, default="", help="Send 1 test message to this email to verify delivery end-to-end")
    parser.add_argument("--from-name", type=str, default="", help="Override sender display name")
    parser.add_argument("--from-email", type=str, default="", help="Override sender email address")
    parser.add_argument("--reply-to", type=str, default="", help="Override reply-to email address")

    args = parser.parse_args()

    from_name = args.from_name or DEFAULT_FROM_NAME
    from_email = args.from_email or DEFAULT_FROM_EMAIL
    reply_to = args.reply_to or DEFAULT_REPLY_TO

    is_live = args.send and not args.dry_run

    print("=" * 70)
    print("  SURPLUS DOCKET — LEGAL OUTREACH AUTOMATION SYSTEM")
    print("=" * 70)
    print(f"  Mode           : {'🚀 LIVE SMTP DISPATCH' if is_live else '📝 DRAFT GENERATION (Dry-Run)'}")
    print(f"  From Sender    : {from_name} <{from_email}>")
    print(f"  Reply-To       : {reply_to}")
    print(f"  SMTP Host      : {SMTP_HOST}:{SMTP_PORT}")
    print(f"  Target Ledger  : {TARGETS_CSV.name}")
    print("=" * 70)

    # 1. Load feed data
    print("\n  Loading live surplus feed data...")
    state_cases = load_feed_data()
    total_cases = sum(len(v) for v in state_cases.values())
    print(f"✓ Loaded {total_cases} verified surplus cases across {len(state_cases)} states.")

    # 2. Load targets
    print("\n  Loading verified attorney targets...")
    targets = load_targets()
    print(f"✓ Found {len(targets)} verified practice targets.")

    if args.state:
        targets = [t for t in targets if t.get("State", "").strip().upper() == args.state.upper()]
        print(f"✓ Filtered to {len(targets)} targets in state: {args.state.upper()}")

    # 3. Check already-contacted
    already_contacted = get_already_contacted()
    unsubscribed = get_unsubscribed_domains()
    print(f"✓ Skipping {len(already_contacted)} previously dispatched recipients.")

    available_targets = []
    for t in targets:
        em = t.get("Email", "").strip().lower()
        if em in already_contacted:
            continue
        dom = em.split("@")[1] if "@" in em else ""
        if dom in unsubscribed or any(u in em for u in unsubscribed):
            continue
        available_targets.append(t)

    print(f"✓ Available uncontacted targets remaining: {len(available_targets)}")

    if not available_targets and not args.test_recipient:
        print("ℹ️ All targets have already been contacted. Outreach pipeline is complete.")
        return 0

    # 4. Handle test recipient
    if args.test_recipient:
        sample_target = available_targets[0] if available_targets else {
            "Name": "Counsel",
            "Firm": "Sample Litigation Practice",
            "State": args.state or "FL",
            "Specialty": "Tax Deed Surplus Recovery",
            "Practice_Details": "Statewide real property litigation and excess proceeds.",
            "Style_Notes": "institutional",
        }
        subject, body = compose_email(sample_target, state_cases, from_name, from_email)
        print(f"\n[TEST MODE] Sending verification email to: {args.test_recipient}")
        print(f"  Subject: {subject}\n")

        if not GMAIL_APP_PASS and is_live:
            print("❌ GMAIL_APP_PASS is not configured. Cannot send live email.")
            return 1

        if is_live:
            try:
                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
                server.starttls()
                server.login(GMAIL_USER, GMAIL_APP_PASS)
                msg = MIMEMultipart()
                msg["From"] = f"{from_name} <{from_email}>"
                msg["To"] = args.test_recipient
                msg["Subject"] = f"[TEST] {subject}"
                msg["Reply-To"] = reply_to
                msg["Date"] = email.utils.formatdate(localtime=True)
                msg["Message-ID"] = email.utils.make_msgid(domain="surplusdocket.com")
                msg.attach(MIMEText(body, "plain", "utf-8"))

                server.sendmail(GMAIL_USER, [args.test_recipient], msg.as_string())
                server.quit()
                print(f"✅ Test verification email dispatched successfully to {args.test_recipient} via {SMTP_HOST}!")
                return 0
            except Exception as e:
                print(f"❌ SMTP Error during test send: {e}")
                return 1
        else:
            print("  [DRY RUN] Previewing test email body (First 300 chars):")
            print(body[:300] + "...\n")
            return 0

    # 5. Batch selection
    batch_size = args.limit if args.limit > 0 else len(available_targets)
    batch = available_targets[:batch_size]
    print(f"\n📋 Processing current batch of {len(batch)} targets (Paced allocation)...\n")

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    server = None
    if is_live:
        if not GMAIL_APP_PASS:
            print("❌ ERROR: GMAIL_APP_PASS is not configured. Run with --dry-run or set GMAIL_APP_PASS.")
            return 1
        try:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASS)
            print(f"✓ Connected & authenticated to {SMTP_HOST} as {GMAIL_USER}\n")
        except Exception as e:
            print(f"❌ Failed to connect to SMTP server: {e}")
            return 1

    manifest = []
    sent_count = 0
    generated_count = 0

    try:
        for idx, target in enumerate(batch, 1):
            to_email = target["Email"].strip().lower()
            name = target.get("Name", "Counsel").strip()
            firm = target.get("Firm", "").strip()
            state = target.get("State", "").strip()

            subject, body = compose_email(target, state_cases, from_name, from_email)

            safe_name = re.sub(r"[^a-zA-Z0-9]", "_", to_email.split("@")[0])
            domain = to_email.split("@")[1].replace(".", "_") if "@" in to_email else "unknown"
            filename = f"{idx:03d}_{safe_name}_at_{domain}.eml"
            eml_path = DRAFTS_DIR / filename

            # Always write draft artifact
            create_eml_file(to_email, name, subject, body, eml_path, from_name, from_email, reply_to)
            generated_count += 1

            manifest.append({
                "idx": idx,
                "email": to_email,
                "name": name,
                "firm": firm,
                "state": state,
                "subject": subject,
                "file": filename,
            })

            if is_live:
                try:
                    msg = MIMEMultipart()
                    msg["From"] = f"{from_name} <{from_email}>"
                    msg["To"] = f"{name} <{to_email}>"
                    msg["Subject"] = subject
                    msg["Reply-To"] = reply_to
                    msg["Date"] = email.utils.formatdate(localtime=True)
                    msg["Message-ID"] = email.utils.make_msgid(domain="surplusdocket.com")
                    msg.attach(MIMEText(body, "plain", "utf-8"))

                    server.sendmail(GMAIL_USER, [to_email], msg.as_string())
                    sent_count += 1
                    status = "SENT"
                    print(f"  [{idx:02d}/{len(batch):02d}] ✉️ SENT: {firm} <{to_email}> ({state})")

                    log_sent_status(SENT_LOG_CSV, {
                        "Timestamp": datetime.now().isoformat(),
                        "Email": to_email,
                        "Name": name,
                        "Firm": firm,
                        "State": state,
                        "Subject": subject,
                        "Status": status,
                        "Mode": "live",
                        "Output_File": str(filename),
                    })

                    # Pacing delay between live sends (natural human cadence)
                    if idx < len(batch):
                        pause_sec = random.uniform(6.0, 14.0)
                        time.sleep(pause_sec)

                except Exception as err:
                    print(f"  [{idx:02d}/{len(batch):02d}] ❌ FAILED: {firm} <{to_email}>: {err}")
                    log_sent_status(SENT_LOG_CSV, {
                        "Timestamp": datetime.now().isoformat(),
                        "Email": to_email,
                        "Name": name,
                        "Firm": firm,
                        "State": state,
                        "Subject": subject,
                        "Status": f"FAILED: {err}",
                        "Mode": "live",
                        "Output_File": str(filename),
                    })
            else:
                # Dry run — do not mutate production sent_log.csv
                print(f"  [{idx:02d}/{len(batch):02d}] 📝 DRAFT: {firm} <{to_email}> ({state}) -> {filename}")

    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass

    # Update manifest
    manifest_path = DRAFTS_DIR / "_MANIFEST.csv"
    with open(manifest_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["idx", "email", "name", "firm", "state", "subject", "file"])
        writer.writeheader()
        writer.writerows(manifest)

    print("\n" + "=" * 70)
    print("  BATCH OUTREACH SUMMARY")
    print("=" * 70)
    print(f"  Drafts Generated : {generated_count} in {DRAFTS_DIR}")
    if is_live:
        print(f"  Emails Dispatched: {sent_count} / {len(batch)} via {SMTP_HOST}")
    print(f"  Activity Ledger  : {SENT_LOG_CSV}")
    print(f"  Manifest File    : {manifest_path}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
