#!/usr/bin/env python3
"""
Surplus Docket — Master Law Firm Conversion Pipeline Generator
=============================================================
Compiles and ranks 1,000+ law firms across 6 core states (FL, TX, GA, NC, TN, CA),
prioritized by deterministic Customer Conversion Index (CCI) scoring.
"""

import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTREACH_DIR = BASE_DIR / "outreach"
OUTPUT_CSV = OUTREACH_DIR / "master_ranked_attorney_targets.csv"
EXISTING_CSV = OUTREACH_DIR / "verified_attorney_targets.csv"

def clean_domain(url_or_email):
    if not url_or_email:
        return ""
    s = url_or_email.strip().lower()
    if "@" in s:
        s = s.split("@")[-1]
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    s = s.split("/")[0].split("?")[0].split(":")[0]
    return s

def calculate_conversion_score(target):
    """
    Computes 0-100 Customer Conversion Index (CCI):
    - Practice Specialty Alignment (max 40 pts)
    - Jurisdictional Volume & Docket Density (max 25 pts)
    - Firm Agility & Decision-Maker Velocity (max 20 pts)
    - Reachability & Intake Accessibility (max 15 pts)
    """
    score = 0.0
    spec = (target.get("Specialty", "") + " " + target.get("Practice_Details", "")).lower()
    state = target.get("State", "").upper()
    firm = target.get("Firm", "").lower()
    name = target.get("Name", "").lower()
    email = target.get("Email", "").lower()
    url = target.get("Source_URL", "").lower()

    # 1. Specialty Alignment (max 40)
    if any(k in spec for k in ["tax deed surplus", "excess proceed", "surplus fund", "overage", "unclaimed fund"]):
        score += 40.0
    elif any(k in spec for k in ["foreclosure surplus", "asset recovery", "tax foreclosure", "tax sale", "auction surplus"]):
        score += 35.0
    elif any(k in spec for k in ["foreclosure defense", "mortgage overage", "deficiency defense", "heir recovery", "probate surplus"]):
        score += 28.0
    elif any(k in spec for k in ["probate litigation", "estate heir", "trust litigation", "intestacy"]):
        score += 22.0
    elif any(k in spec for k in ["real estate litigation", "quiet title", "partition", "property law", "title dispute"]):
        score += 18.0
    elif any(k in spec for k in ["bankruptcy", "debtor rights", "consumer rights"]):
        score += 12.0
    else:
        score += 8.0

    # 2. Jurisdictional Match (max 25)
    # Core active daily feed states with highest surplus volume:
    if state in ["FL", "TX"]:
        score += 25.0
    elif state in ["GA", "NC"]:
        score += 22.0
    elif state in ["TN", "CA"]:
        score += 20.0
    elif state in ["OH", "NY", "NJ", "PA", "MI"]:
        score += 12.0
    else:
        score += 6.0

    # Metro tier bonus (+3 to +5)
    high_volume_metros = [
        "miami", "palm beach", "broward", "orange", "hillsborough", "duval", "pinellas",
        "harris", "dallas", "tarrant", "travis", "bexar", "collin", "denton", "fort bend",
        "fulton", "dekalb", "gwinnett", "cobb", "chatham",
        "mecklenburg", "wake", "guilford", "forsyth", "durham",
        "shelby", "davidson", "knox", "hamilton", "rutherford",
        "los angeles", "san diego", "orange county", "riverside", "san bernardino"
    ]
    circuit = target.get("Metro_Circuit", "").lower()
    if any(m in circuit or m in spec for m in high_volume_metros):
        score += 5.0

    # 3. Firm Agility & Decision-Maker Velocity (max 20)
    # Solo / Boutique Managing Partners have instant credit card sign-off authority
    if any(k in firm for k in ["law office of", "p.a.", "pa", "pllc", "solo", "group"]) or any(title in name for title in ["pa", "pllc"]):
        score += 20.0
    elif any(k in firm for k in ["llc", "firm", "associates", "law", "legal"]):
        score += 16.0
    elif any(k in firm for k in ["llp", "partners"]):
        score += 12.0
    else:
        score += 8.0

    # 4. Reachability & Digital Hygiene (max 15)
    if email and "@" in email and not any(e in email for e in ["gmail.com", "yahoo.com"]):
        score += 8.0
    elif email and "@" in email:
        score += 5.0
    
    if url and url.startswith("http"):
        score += 7.0
    elif url:
        score += 3.0

    return round(min(score, 99.0), 1)

def determine_priority_tier(score):
    if score >= 90.0:
        return "Tier 1: Ultra-High Probability (Surplus Boutiques)"
    elif score >= 80.0:
        return "Tier 2: High Probability (Foreclosure & Heir Recovery)"
    elif score >= 70.0:
        return "Tier 3: Strong Propensity (Real Estate & Quiet Title)"
    else:
        return "Tier 4: Expansion Candidates (Distressed Property & Debtor Counsel)"

def determine_conversion_rationale(target, score):
    state = target.get("State", "FL")
    metro = target.get("Metro_Circuit", "Primary Metro")
    
    statutes = {
        "FL": "Fla. Stat. § 197.582 (120-Day Notice Window)",
        "TX": "Tex. Tax Code § 34.04 (2-Year Court Registry Limit)",
        "GA": "O.C.G.A. § 48-4-5 (5-Year Interpleader Claims)",
        "NC": "N.C. Gen. Stat. § 105-374 (Superior Court Upset Bid Registry)",
        "TN": "Tenn. Code Ann. § 67-5-2510 (Chancery Court Excess Actions)",
        "CA": "Cal. Rev. & Tax Code § 4675 (1-Year Statutory Deadline)"
    }
    statute_ref = statutes.get(state, "Statutory Recovery Procedures")
    
    if score >= 90.0:
        return f"Immediate ROI fit: Firm actively litigates surplus/overages under {statute_ref} in {metro}. Daily scrubbed feed eliminates 15+ hours/wk of manual docket pull and senior lien verification."
    elif score >= 80.0:
        return f"High expansion fit: Existing foreclosure defense and heir practice in {metro} can monetize lost properties by filing affirmative overage petitions under {statute_ref}."
    elif score >= 70.0:
        return f"Strong ancillary fit: Real estate and quiet title litigators in {metro} with courthouse registry familiarity; contingency fees on 1 claim cover multi-year subscription."
    else:
        return f"Selective expansion: Real estate litigators in {metro} handling distressed property transfers and judicial tax foreclosure actions."
