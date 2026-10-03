#!/usr/bin/env python3
"""
Surplus Docket — Embed Tool Promotion & Directory Packet Engine
================================================================
Generates customized submission dossiers and promotional pitches for:
1. Free embeddable statutory deadline & surplus calculator widget.
2. Official court registry verification badge.
3. Automated submission dossiers for all 45 curated high-DA directories.
"""

import os
import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LINK_BUILDING_DIR = BASE_DIR / "marketing" / "link_building"
CITATION_CSV = LINK_BUILDING_DIR / "citation_registry.csv"
PACKETS_DIR = LINK_BUILDING_DIR / "submission_packets"
EMBED_PITCHES_DIR = LINK_BUILDING_DIR / "embed_pitches"

PACKETS_DIR.mkdir(parents=True, exist_ok=True)
EMBED_PITCHES_DIR.mkdir(parents=True, exist_ok=True)

EMBED_PROFILES = [
    {
        "target_type": "LegalTech Bloggers & Legal Podcasters",
        "subject": "Free statutory deadline calculator for legal tech readers",
        "file_name": "pitch_legaltech_bloggers.md",
        "body": """Hi {Editor / Webmaster},

Follow your writing on legal technology and practice workflows.

We put together a free, open-access statutory deadline calculator for foreclosure and tax deed surplus claims across six states (FL, TX, CA, GA, NC, TN):
https://surplusdocket.com/tools.html

There are no paywalls, accounts, or tracking. Thought your readers might find it useful as a quick reference, and it's also set up so anyone can link or embed it directly if they want.

Hope it's helpful,

Elena Brooks
Surplus Docket
elena.brooks@surplusdocket.com | https://surplusdocket.com
"""
    },
    {
        "target_type": "Real Estate Investor & Tax Sale Communities",
        "subject": "Free tax deed surplus deadline calculator",
        "file_name": "pitch_real_estate_investors.md",
        "body": """Hi {Community Lead},

Wanted to share a quick free resource for your community working with tax deeds and excess funds.

We put together an open calculator that maps out statutory claim deadlines and finder fee caps across Florida, Texas, California, Georgia, North Carolina, and Tennessee:
https://surplusdocket.com/tools.html

Zero paywalls, logins, or ads. Feel free to share it with your members if you think it'd save them some time.

Best,

Elena Brooks
Surplus Docket
elena.brooks@surplusdocket.com | https://surplusdocket.com
"""
    },
    {
        "target_type": "Law School Legal Clinics & Access-to-Justice Centers",
        "subject": "Free statutory surplus calculator for clinical programs",
        "file_name": "pitch_law_school_clinics.md",
        "body": """Hi {Clinical Director & Faculty Advisors},

Came across your clinic's foreclosure and housing advocacy work.

Following Tyler v. Hennepin County, we put together a free, open-access statutory surplus calculator tracking claim deadlines and fee caps across six states ({statute_citation}):
https://surplusdocket.com/tools.html

Zero ads, accounts, or tracking. Thought it might be a handy practical reference for your students and staff assisting distressed property owners.

Hope it's helpful,

Elena Brooks
Surplus Docket
elena.brooks@surplusdocket.com | https://surplusdocket.com/tools.html
"""
    },
    {
        "target_type": "State & Local Bar Association LPM (Law Practice Management) Editors",
        "subject": "Free surplus recovery practice utilities & Clio/Filevine schemas",
        "file_name": "pitch_bar_association_lpm.md",
        "body": """Hi {Editor / Practice Management Advisor},

Follow your practice management resources for solo and small-firm practitioners.

We recently released a set of free practice utilities for attorneys handling post-foreclosure surplus claims, including multi-state statutory deadline calculation and pre-mapped Clio and Filevine intake schemas:
https://surplusdocket.com/tools.html

Everything is free and open-access with no account required. If you ever highlight member tools or tech tips in your LPM column or directory, thought this might be of interest.

Best regards,

Elena Brooks
Surplus Docket
elena.brooks@surplusdocket.com | https://surplusdocket.com
"""
    }
]


def generate_embed_pitches():
    print("Generating embed promotion pitches...")
    for p in EMBED_PROFILES:
        filepath = EMBED_PITCHES_DIR / p["file_name"]
        content = f"# 📢 Pitch: {p['target_type']}\n**Subject Line:** `{p['subject']}`\n\n---\n\n{p['body']}"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✓ {p['file_name']}")


def generate_directory_submission_packets():
    print("Generating directory submission packets...")
    if not CITATION_CSV.exists():
        print("  ⚠️ citation_registry.csv not found.")
        return

    with open(CITATION_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            name = row.get("name", "").strip()
            category = row.get("category", "LegalTech").strip()
            da = row.get("da", "70").strip()
            sub_url = row.get("submission_url", "").strip()
            slug = name.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
            
            packet_file = PACKETS_DIR / f"{slug}.json"
            packet_data = {
                "directory_name": name,
                "domain_authority": da,
                "category": category,
                "submission_url": sub_url,
                "company_name": "Surplus Docket",
                "tagline": "Real-Time Court Registry Feeds for Foreclosure Surplus Recovery",
                "short_description": "Surplus Docket aggregates daily tax deed surplus and excess proceeds court filings for asset recovery and real estate counsel, with automated public record indexing and statutory deadline calculations.",
                "website_url": "https://surplusdocket.com/",
                "tools_url": "https://surplusdocket.com/tools.html",
                "embed_tool_url": "https://surplusdocket.com/embed/surplus-calculator.html",
                "api_docs_url": "https://surplusdocket.com/api-documentation.html",
                "keywords": ["LegalTech", "Legal Software", "Tax Deed Surplus", "Excess Proceeds", "Court Dockets", "Foreclosure Intelligence"],
                "target_anchor": row.get("anchor_target", "Surplus Docket Legal Intelligence"),
                "status": "READY_FOR_SUBMISSION"
            }
            with open(packet_file, "w", encoding="utf-8") as pf:
                json.dump(packet_data, pf, indent=2)
            count += 1
            
    print(f"  ✓ Generated {count} structured submission packets in {PACKETS_DIR}")


if __name__ == "__main__":
    generate_embed_pitches()
    generate_directory_submission_packets()
