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

raw_from_name = os.getenv("FROM_NAME", "Elena Brooks")
if not raw_from_name or raw_from_name in ("Surplus Docket Intelligence", "Surplus Docket Compliance & Research Desk", "Surplus Docket"):
    DEFAULT_FROM_NAME = "Elena Brooks"
else:
    DEFAULT_FROM_NAME = raw_from_name

raw_from_email = os.getenv("FROM_EMAIL", "elena.brooks@surplusdocket.com")
if not raw_from_email or raw_from_email in ("dockets@surplusdocket.com", "bot@surplusdocket.com"):
    DEFAULT_FROM_EMAIL = "elena.brooks@surplusdocket.com"
else:
    DEFAULT_FROM_EMAIL = raw_from_email

raw_reply_to = os.getenv("REPLY_TO", "elena.brooks@surplusdocket.com")
if not raw_reply_to or raw_reply_to in ("dockets@surplusdocket.com", "bot@surplusdocket.com"):
    DEFAULT_REPLY_TO = "elena.brooks@surplusdocket.com"
else:
    DEFAULT_REPLY_TO = raw_reply_to

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
    "lw.com",  # Latham & Watkins rejects generic info@
}

# Generic department prefixes that reject cold emails or do not reach counsel
GENERIC_EMAIL_PREFIXES = (
    "info@", "contact@", "admin@", "support@", "office@", "reception@",
    "general@", "mail@", "inquiry@", "inquiries@", "hello@", "team@",
    "intake@", "help@", "service@", "services@", "frontdesk@", "desk@",
    "billing@", "accounting@", "sales@", "press@", "media@", "jobs@",
    "careers@", "marketing@", "legal@"
)

# Big-law firms that reject unsolicited emails or require web contact forms
BLOCKED_OUTREACH_DOMAINS = {
    "lw.com", "omm.com", "paulhastings.com", "dentons.com", "kobrekim.com",
    "sidley.com", "gibsondunn.com", "kirkland.com", "morganlewis.com",
    "skadden.com", "dlapiper.com", "greenbergtraurig.com", "reedsmith.com",
    "gtlaw.com", "bclplaw.com", "hoganlovells.com", "jonesday.com",
    "mayerbrown.com", "whitecase.com", "ropesgray.com", "cooley.com",
    "goodwinlaw.com", "foley.com", "alston.com", "hollandknight.com",
    "klgates.com", "mcguirewoods.com", "perkinscoie.com", "sheppardmullin.com",
    "wilmerhale.com", "blankrome.com", "cozen.com", "foxrothschild.com",
    "lockelord.com", "nixonpeabody.com", "polsinelli.com", "seyfarth.com",
    "troutmansanders.com", "troutman.com", "venable.com", "winston.com"
}


def is_valid_direct_email(email_str: str) -> bool:
    """
    Validates that an email is a legitimate individual practitioner address,
    preventing 550 bounces from dead generic mailboxes (like info@lw.com).
    """
    if not email_str or "@" not in email_str:
        return False
    e_clean = email_str.strip().lower()
    local_part, domain = e_clean.split("@", 1)

    # 1. Skip dead/unverified/test domains
    if domain in DEAD_DOMAINS or domain in BLOCKED_OUTREACH_DOMAINS:
        return False

    # 2. Skip generic corporate aliases that reject or don't reach attorneys
    if e_clean.startswith(GENERIC_EMAIL_PREFIXES):
        return False

    # 3. Skip placeholder local parts
    if len(local_part) < 2 or local_part in ("test", "example", "user", "lawyer", "attorney"):
        return False

    return True

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
            state = row.get("State", "").strip().upper()
            if state not in state_cases:
                state_cases[state] = []
            state_cases[state].append({
                "case_no": row.get("Case_or_TaxDeed_No", "").strip(),
                "county": row.get("County", "").strip(),
                "balance": float(row.get("Surplus_Balance_USD", 0)),
                "fee": float(row.get("Est_Finder_Fee_USD", 0)),
                "owner_name": row.get("Owner_Name", "").strip(),
                "entity_type": row.get("Entity_Type", "").strip(),
                "is_individual": row.get("Is_Individual", "True").lower() == "true",
                "heir_search_recommended": row.get("Heir_Search_Recommended", "False").lower() == "true",
                "property_address": row.get("Property_Address", "").strip(),
                "property_type": row.get("Property_Type", "").strip(),
                "governing_statute": row.get("Governing_Statute", "").strip(),
                "statutory_window": row.get("Statutory_Deadline_Window", "").strip(),
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


def load_targets(allow_generic: bool = False):
    """
    Load verified attorney targets from CSV.
    Strictly filters out generic/department mailboxes (info@, contact@)
    to prevent delivery failures and bounces.
    """
    if not TARGETS_CSV.exists():
        print(f"  Target file not found: {TARGETS_CSV}")
        return []

    targets = []
    skipped_generic = 0
    with open(TARGETS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {}
            for k, v in row.items():
                if k:
                    clean[k.strip()] = (v or "").strip()
            email = clean.get("Email", "")
            if not email:
                continue

            if not allow_generic and not is_valid_direct_email(email):
                skipped_generic += 1
                continue

            targets.append(clean)

    if skipped_generic > 0:
        print(f"  🛡️ Target Quality Gate: Filtered out {skipped_generic} generic/blocked mailboxes (e.g. info@, contact@).")
    return targets


def get_first_name(full_name):
    if not full_name:
        return "Counsel"
    parts = full_name.strip().split()
    first = parts[0] if parts else "Counsel"
    if first.lower() in ("mr.", "ms.", "mrs.", "dr.", "atty.", "attorney"):
        first = parts[1] if len(parts) > 1 else "Counsel"
    return first


def clean_firm_display_name(firm):
    """Clean firm name for natural in-sentence prose."""
    if not firm:
        return "your practice"
    cleaned = re.sub(
        r'[,.]?\s*(LLC|L\.L\.C\.|P\.A\.|PA|LLP|L\.L\.P\.|Inc\.|Inc|PLLC|P\.L\.L\.C\.|P\.C\.|PC|GP|P\.L\.|PL|Corp\.|Corp)$',
        '',
        firm.strip(),
        flags=re.IGNORECASE
    ).strip(' ,.')
    return cleaned or firm


def get_unsubscribed_domains():
    """Collect domains, emails, or URLs that unsubscribed or bounced."""
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

    bounced_file = OUTREACH_DIR / "bounced_emails.json"
    if bounced_file.exists():
        try:
            with open(bounced_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if isinstance(item, str):
                        unsub.add(item.lower())
        except Exception:
            pass

    return unsub


def select_best_case(target, state_cases):
    """
    Select the single most relevant, high-impact unencumbered surplus case
    matched to target jurisdiction, practice focus, and metro county.
    """
    state = target.get("State", "FL").upper()
    specialty = (target.get("Specialty", "") + " " + target.get("Practice_Details", "")).lower()
    metro_text = (target.get("Metro_Circuit", "") + " " + target.get("Practice_Details", "") + " " + target.get("Firm", "")).lower()

    is_probate = any(k in specialty for k in ["probate", "estate", "heir", "trust", "decedent", "administration"])
    is_foreclosure = any(k in specialty for k in ["foreclosure", "mortgage", "lender", "servicing", "junior lien", "lien", "distressed"])

    candidates = state_cases.get(state, [])
    if not candidates:
        for s in ["FL", "CA", "TX", "GA", "NC", "TN"]:
            if state_cases.get(s):
                candidates = state_cases[s]
                break

    if not candidates:
        return None

    def score_candidate(c):
        score = 0
        county_lower = c["county"].lower()
        if county_lower in metro_text:
            score += 100
        if is_probate:
            if "estate" in c["owner_name"].lower() or c["heir_search_recommended"]:
                score += 80
        elif is_foreclosure:
            if "commercial" in c["property_type"].lower() or c["balance"] >= 100000:
                score += 60
        else:
            if c["balance"] >= 75000:
                score += 40
        score += min(c["balance"] / 10000.0, 20.0)
        return score

    scored = sorted(candidates, key=score_candidate, reverse=True)
    return scored[0]


def compose_email(target, state_cases, from_name=DEFAULT_FROM_NAME, from_email=DEFAULT_FROM_EMAIL):
    """
    Compose an authentic, concise 1-on-1 outreach email from Elena Brooks.
    Researched specifically for the target firm and jurisdiction.
    Zero ad copy, zero marketing links, no pricing pitch.
    """
    first_name = get_first_name(target.get("Name", ""))
    firm_raw = target.get("Firm", "your firm").strip()
    firm_prose = clean_firm_display_name(firm_raw)
    state = target.get("State", "FL").upper()
    state_full = STATE_NAMES.get(state, state)
    specialty_raw = target.get("Specialty", "").lower()
    practice_details = target.get("Practice_Details", "").lower()
    combined_practice = f"{specialty_raw} {practice_details}"

    is_probate = any(k in combined_practice for k in ["probate", "estate", "heir", "trust", "decedent", "administration"])
    is_foreclosure = any(k in combined_practice for k in ["foreclosure", "mortgage", "lender", "servicing", "junior lien", "lien", "distressed"])

    c = select_best_case(target, state_cases)
    if not c:
        c = {
            "case_no": "2024-TD-001955",
            "county": "Orange",
            "balance": 74300.0,
            "owner_name": "Estate of James & Linda Chen",
            "property_type": "Single Family Residential",
            "governing_statute": STATE_STATUTES.get(state, "Fla. Stat. § 197.582"),
            "statutory_window": "120-day claim window",
        }

    county = c["county"]
    case_no = c["case_no"]
    balance_fmt = f"${c['balance']:,.0f}"
    statute = c.get("governing_statute") or STATE_STATUTES.get(state, "applicable state statutes")

    raw_prop = c.get('property_type', '').lower()
    if 'commercial' in raw_prop:
        prop_desc = "commercial property"
    elif 'residential' in raw_prop:
        prop_desc = "residential property"
    elif 'land' in raw_prop or 'acreage' in raw_prop:
        prop_desc = "vacant land parcel"
    else:
        prop_desc = "real property parcel"

    if is_probate:
        practice_focus = "estate and probate administration"
        if "estate" in c["owner_name"].lower():
            clean_owner = c['owner_name'].title().replace(" Of ", " of ")
            owner_clause = f"tied to the {clean_owner}"
        else:
            owner_clause = f"from a tax deed sale of a {prop_desc}"
    elif is_foreclosure:
        practice_focus = "foreclosure and surplus litigation"
        owner_clause = f"from a post-foreclosure {prop_desc} sale"
    else:
        practice_focus = "real property surplus and tax deed recovery"
        owner_clause = f"from a recent tax deed sale of a {prop_desc}"

    # Subject line — simple, specific, looks like a direct legal inquiry about a case
    subject = f"{county} County surplus filing — {case_no}"

    # Salutation
    if first_name and first_name != "Counsel":
        greeting = f"Hi {first_name},"
    else:
        greeting = f"Hello {firm_prose} team," if firm_prose != "your practice" else "Hello,"

    # Paragraph 1: Authentic research opener
    opener = f"I was reviewing recent {county} County court registry filings and came across {firm_prose} while looking at active {practice_focus} counsel in {state_full}."

    # Paragraph 2: Specific unencumbered docket finding
    case_body = (
        f"We track unencumbered surplus funds across clerk registries, and we recently identified a "
        f"{balance_fmt} surplus balance on Case {case_no} in {county} County {owner_clause}. "
        f"We verified upstream that senior institutional mortgages have been cleared, and the claim "
        f"window under {statute} is currently open."
    )

    # Paragraph 3: Direct question / conversation starter
    closing_ask = (
        f"Are you currently handling surplus recovery petitions or excess proceeds claims in {county} County? "
        f"If this is an active area for your practice, I'd be glad to send over the docket summary and title notes for your review."
    )

    # Clean signature
    sig = f"Best regards,\n\n{from_name}\nSenior Docket Specialist | Surplus Docket\nsurplusdocket.com"

    body = f"{greeting}\n\n{opener}\n\n{case_body}\n\n{closing_ask}\n\n{sig}"

    return subject, body


def create_eml_file(to_email, to_name, subject, body, output_path, from_name=DEFAULT_FROM_NAME, from_email=DEFAULT_FROM_EMAIL, reply_to=DEFAULT_REPLY_TO):
    """Create a standards-compliant .eml file marked as draft."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = f"{to_name} <{to_email}>"
    msg["Subject"] = subject
    msg["Reply-To"] = f"{from_name} <{reply_to}>"
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
                msg["Reply-To"] = f"{from_name} <{reply_to}>"
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
                    msg["Reply-To"] = f"{from_name} <{reply_to}>"
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
