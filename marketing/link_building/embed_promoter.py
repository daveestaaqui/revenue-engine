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
        "subject": "Free Embeddable Statutory Surplus & Court Deadline Calculator for Your Readers",
        "file_name": "pitch_legaltech_bloggers.md",
        "body": """Hi {Editor / Webmaster},

Noticed your coverage on foreclosure trends and legal technology resources.

We recently open-sourced an interactive, embeddable statutory deadline calculator designed specifically for asset recovery, foreclosure defense, and probate law practitioners:

Live Embed Hub: https://surplusdocket.com/embed/
Direct Calculator Widget: https://surplusdocket.com/embed/surplus-calculator.html

What it does for your site visitors:
• Calculates statutory claim deadlines and fee caps across 6 states (FL § 197.582, TX § 34.04, CA § 4675, GA § 48-4-5, NC § 105-374, TN § 67-5-2501).
• 100% free, zero ads, zero cookies, zero user-registration required.
• Responsive iframe that drops into any WordPress, Webflow, or custom HTML page in 30 seconds.

Embed Snippet:
```html
<iframe src="https://surplusdocket.com/embed/surplus-calculator.html" width="100%" height="480" frameborder="0" style="border: 1px solid #1e293b; border-radius: 8px; max-width: 580px;" title="Statutory Surplus Deadline Calculator"></iframe>
<p style="font-size: 11px; color: #64748b; text-align: center; margin-top: 6px;">Powered by <a href="https://surplusdocket.com/" target="_blank" rel="noopener">Surplus Docket Legal Intelligence</a></p>
```

Feel free to embed this on your legal tools or resources page.

Best regards,
Elena Brooks
Director of Practice Relations & Legal Technology
elena.brooks@surplusdocket.com | https://surplusdocket.com
"""
    },
    {
        "target_type": "Real Estate Investor & Tax Sale Communities",
        "subject": "Free Interactive Tax Deed Surplus Calculator Widget",
        "file_name": "pitch_real_estate_investors.md",
        "body": """Hi {Community Lead},

Wanted to share a free tool that solves a common headache for tax deed investors and excess funds researchers:

Calculating statutory claim deadlines and statutory maximum fee caps across different states after a foreclosure auction.

We built a free, embeddable calculator that your members or readers can use right on your site:
https://surplusdocket.com/embed/

Key Features:
- Instant countdown to statutory expiration across Florida (120 days), Texas (2 years), California (1 year), Georgia (5 years), North Carolina (post-confirmation special proceedings), and Tennessee.
- Real-time statutory non-attorney fee cap benchmark calculations.
- Clean iframe embed with zero tracking cookies or signups.

Free embed code:
```html
<iframe src="https://surplusdocket.com/embed/surplus-calculator.html" width="100%" height="480" frameborder="0" style="border: 1px solid #1e293b; border-radius: 8px; max-width: 580px;" title="Statutory Surplus Deadline Calculator"></iframe>
```

Let us know if you have any questions or feature requests for additional jurisdictions!

Best regards,
Elena Brooks
Director of Practice Relations & Legal Technology
elena.brooks@surplusdocket.com | https://surplusdocket.com
"""
    },
    {
        "target_type": "Law School Legal Clinics & Access-to-Justice Centers",
        "subject": "Free Open-Access Statutory Surplus & Due Process Calculator for Clinical Programs",
        "file_name": "pitch_law_school_clinics.md",
        "body": """Dear Clinical Director & Faculty Advisors,

We follow your clinical advocacy assisting distressed homeowners and heir-property claimants in post-foreclosure equity protection.

Following the Supreme Court's ruling in Tyler v. Hennepin County (598 U.S. 631), our engineering team developed a free, zero-tracking public tool suite for statutory surplus calculations, deadline verification, and legal motions:

• Free Practice Tools Hub: https://surplusdocket.com/tools.html
• Statutory Deadline & Recovery Calculator: https://surplusdocket.com/embed/surplus-calculator.html
• Practitioner Toolkit (Verified Motions & Petitions): https://surplusdocket.com/practitioner-toolkit.html

Key Clinical Utilities:
- Multi-jurisdiction statutory deadline calculation across Florida, Texas, California, Georgia, North Carolina, and Tennessee.
- Verification of statutory finder fee caps (preventing predatory fee exploitation against vulnerable heirs).
- Clean, open-access embed widget requiring zero user logins or tracking cookies.

Embed Code for Clinical Resources / Student Guides:
```html
<iframe src="https://surplusdocket.com/embed/surplus-calculator.html" width="100%" height="480" frameborder="0" style="border: 1px solid #1e293b; border-radius: 8px; max-width: 580px;" title="Statutory Surplus Deadline Calculator"></iframe>
<p style="font-size: 11px; color: #64748b; text-align: center; margin-top: 6px;">Powered by <a href="https://surplusdocket.com/tools.html" target="_blank" rel="noopener">Surplus Docket Practice Tools</a></p>
```

We provide full complimentary access to our verified court feeds for non-profit clinics and academic researchers.

Sincerely,
Elena Brooks
Director of Practice Relations & Legal Technology
elena.brooks@surplusdocket.com | https://surplusdocket.com/tools.html
"""
    },
    {
        "target_type": "State & Local Bar Association LPM (Law Practice Management) Editors",
        "subject": "Resource Contribution: Open-Access Surplus Recovery Tools & Clio/Filevine CRM Schemas",
        "file_name": "pitch_bar_association_lpm.md",
        "body": """Hi {Editor / Practice Management Advisor},

We frequently read your practice management technology reviews and practice guides for solo and small-firm practitioners.

With increasing judicial activity surrounding foreclosure surplus recovery and court registry interpleader actions, we've developed and released a free suite of practice utilities for real estate, probate, and civil litigation members:

• Free Practice Tools Hub: https://surplusdocket.com/tools.html
• Pre-mapped Clio & Filevine CRM intake schemas: https://surplusdocket.com/tools.html#crm
• Embeddable Statutory Deadline & Fee Benchmark Calculator: https://surplusdocket.com/embed/surplus-calculator.html

These tools allow bar members to:
1. Instantly calculate statutory filing deadlines across FL (§ 197.582 / § 45.032), TX (§ 34.04), GA (§ 48-4-5), CA (§ 4675), NC, and TN.
2. Directly ingest court docket data into Clio Manage or Filevine with standardized matter references.
3. Access verified statutory claim motion templates compliant with local rules.

We would welcome contributing a brief practice tip or resource mention to your LPM newsletter or technology directory.

Best regards,
Elena Brooks
Director of Practice Relations & Legal Technology
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
