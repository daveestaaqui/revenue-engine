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

import csv
import json
import os
import random
import re
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTREACH_DIR = BASE_DIR / "outreach"
TARGETS_CSV = OUTREACH_DIR / "verified_attorney_targets.csv"
SENT_LOG_CSV = OUTREACH_DIR / "sent_log.csv"
DRAFTS_DIR = OUTREACH_DIR / "drafts"
FEED_CSV = BASE_DIR / "exports" / "Master_Surplus_Lead_Feed.csv"

FROM_EMAIL = "elena.brooks@surplusdocket.com"
FROM_NAME = "Elena Brooks"
REPLY_TO = "elena.brooks@surplusdocket.com"

# Domains confirmed dead via MX lookup — exclude from generation
DEAD_DOMAINS = {
    "farahlawtexas.com",
    "schuenemanlaw.com",
}

STATE_NAMES = {
    "FL": "Florida", "TX": "Texas", "GA": "Georgia",
    "NC": "North Carolina", "TN": "Tennessee", "CA": "California",
    "OH": "Ohio", "IL": "Illinois", "PA": "Pennsylvania",
    "AZ": "Arizona", "SC": "South Carolina", "AL": "Alabama",
    "MS": "Mississippi", "NJ": "New Jersey", "NY": "New York",
    "MD": "Maryland",
}

STRIPE_LINK = "https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X"
SITE_URL = "https://surplusdocket.com"

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
    return parts[0] if parts else "Counsel"


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


def compose_email(target, state_cases):
    """Compose a fully personalized email in Dave's authentic voice."""
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

    # Personalize the opener based on what we know about the firm
    if "statewide" in practice_details.lower() or "all" in practice_details.lower():
        opener_detail = (
            f"Saw that {firm} covers {state_full} statewide — "
            f"figured this might save your team some hours."
        )
    elif any(county in practice_details.lower() for county in
             ["harris", "palm beach", "miami", "fulton", "dallas", "orange"]):
        # They mention a specific county we cover
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

    # Build subject — specific, non-spammy
    subject = (
        f"Scrubbed {state_full} surplus leads for {firm} "
        f"(verified court docket data)"
    )

    # Compose body
    body = f"""{greeting} {first_name},

{opener_detail}

We index tax deed surplus and excess proceeds records daily across court registries and scrub out all institutional liens before delivery.

{pain}

A few live cases from this week's feed:

{case_refs}

Every record is verified against official clerk dockets{(' under ' + statute + ' (' + window + ')') if statute else ''}.

Daily delivery at 7 AM EST — CSV, Excel, and JSON. Flat $249/mo, cancel anytime, no contracts.

Full methodology and sample feed: {SITE_URL}
Subscribe directly: {STRIPE_LINK}

Happy to send a free sample extract if you want to see the data first — just reply here.

{closing}
Elena Brooks
Senior Docket Specialist | Surplus Docket
{SITE_URL}

---
Legal Notice & Regulatory Disclaimer: Surplus Docket is a specialized legal technology and court records intelligence service, not a law firm. Surplus Docket does not provide legal advice, legal counsel, or legal representation, and no attorney-client relationship is formed by this correspondence. All docket records, statutory references, and procedural timelines are compiled exclusively for informational and intelligence purposes for licensed attorneys and recovery professionals."""

    return subject, body


def create_eml_file(to_email, to_name, subject, body, output_path):
    """Create a standards-compliant .eml file marked as draft."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = f"{to_name} <{to_email}>"
    msg["Subject"] = subject
    msg["Reply-To"] = f"Surplus Docket <{REPLY_TO}>"
    msg["X-Unsent"] = "1"  # Marks as draft in Apple Mail
    msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S -0400")

    output_path.write_text(msg.as_string(), encoding="utf-8")


def main():
    print("=" * 70)
    print("  SURPLUS DOCKET — PERSONALIZED DRAFT EMAIL GENERATOR")
    print("=" * 70)

    # 1. Load feed data
    print("\n  Loading live surplus feed data...")
    state_cases = load_feed_data()
    total_cases = sum(len(v) for v in state_cases.values())
    print(f"  Loaded {total_cases} verified cases across {len(state_cases)} states")

    # 2. Load targets
    print("\n  Loading verified attorney targets...")
    targets = load_targets()
    print(f"  Found {len(targets)} targets (dead domains excluded)")

    if not targets:
        print("  No targets found.")
        return

    # 3. Check already-contacted
    print("\n  Checking for previously contacted emails...")
    already_contacted = get_already_contacted()
    print(f"  Found {len(already_contacted)} previously sent (non-dry-run) emails to skip")

    # 4. Filter
    new_targets = []
    skipped = []
    for t in targets:
        email = t.get("Email", "").strip().lower()
        if email in already_contacted:
            skipped.append(email)
        else:
            new_targets.append(t)

    if skipped:
        print(f"  Skipping {len(skipped)} already-contacted addresses:")
        for s in skipped:
            print(f"    - {s}")

    print(f"\n  {len(new_targets)} new drafts to generate")

    # 5. Generate drafts
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    for old_file in DRAFTS_DIR.glob("*.eml"):
        old_file.unlink()
    for old_file in DRAFTS_DIR.glob("*.csv"):
        old_file.unlink()

    print(f"\n  Generating .eml drafts in: {DRAFTS_DIR}")
    print("-" * 70)

    generated = 0
    manifest = []

    for i, target in enumerate(new_targets, 1):
        email = target["Email"]
        name = target.get("Name", "Counsel")
        firm = target.get("Firm", "")
        state = target.get("State", "")

        subject, body = compose_email(target, state_cases)

        safe_name = re.sub(r"[^a-zA-Z0-9]", "_", email.split("@")[0])
        domain = email.split("@")[1].replace(".", "_") if "@" in email else "unknown"
        filename = f"{i:03d}_{safe_name}_at_{domain}.eml"
        output_path = DRAFTS_DIR / filename

        create_eml_file(email, name, subject, body, output_path)
        generated += 1

        manifest.append({
            "idx": i,
            "email": email,
            "name": name,
            "firm": firm,
            "state": state,
            "subject": subject,
            "file": filename,
        })

        print(f"  [{i:03d}] {firm} ({email}) — {state}")

    # 6. Write manifest
    manifest_path = DRAFTS_DIR / "_MANIFEST.csv"
    with open(manifest_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["idx", "email", "name", "firm", "state", "subject", "file"])
        writer.writeheader()
        writer.writerows(manifest)

    # 7. Summary
    print("\n" + "=" * 70)
    print("  DRAFT GENERATION COMPLETE")
    print("=" * 70)
    print(f"  Drafts Generated      : {generated}")
    print(f"  Skipped (already sent) : {len(skipped)}")
    print(f"  Output Directory       : {DRAFTS_DIR}")
    print(f"  Manifest CSV           : {manifest_path}")
    print(f"")
    print(f"  TO REVIEW:")
    print(f"    • Open any .eml file — it opens as an editable draft")
    print(f"    • Or: open {DRAFTS_DIR} in Finder and double-click")
    print(f"    • Each email has X-Unsent:1 header (Apple Mail draft mode)")
    print("=" * 70)


if __name__ == "__main__":
    main()
