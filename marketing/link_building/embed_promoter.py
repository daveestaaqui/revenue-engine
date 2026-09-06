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
• Calculates statutory claim deadlines and fee caps across 6 states (FL § 197.582, TX § 34.04, CA § 4675, GA § 48-4-5, NC § 105-374, TN § 67-5-2510).
• 100% free, zero ads, zero cookies, zero user-registration required.
• Responsive iframe that drops into any WordPress, Webflow, or custom HTML page in 30 seconds.

Embed Snippet:
```html
<iframe src="https://surplusdocket.com/embed/surplus-calculator.html" width="100%" height="480" frameborder="0" style="border: 1px solid #1e293b; border-radius: 8px; max-width: 580px;" title="Statutory Surplus Deadline Calculator"></iframe>
<p style="font-size: 11px; color: #64748b; text-align: center; margin-top: 6px;">Powered by <a href="https://surplusdocket.com/" target="_blank" rel="noopener">Surplus Docket Legal Intelligence</a></p>
```

Feel free to embed this on your legal tools or resources page.

Best regards,
Surplus Docket Editorial Team
press@surplusdocket.com | https://surplusdocket.com
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
- Instant countdown to statutory expiration across Florida (120 days), Texas (2 years), California (1 year), Georgia (5 years), North Carolina (10-day upset bid), and Tennessee.
- Real-time statutory non-attorney fee cap benchmark calculations.
- Clean iframe embed with zero tracking cookies or signups.

Free embed code:
```html
<iframe src="https://surplusdocket.com/embed/surplus-calculator.html" width="100%" height="480" frameborder="0" style="border: 1px solid #1e293b; border-radius: 8px; max-width: 580px;" title="Statutory Surplus Deadline Calculator"></iframe>
```

Let us know if you have any questions or feature requests for additional jurisdictions!

Best,
Surplus Docket Research Desk
https://surplusdocket.com
"""
    },
    {
        "target_type": "Asset Recovery Firm Partners (Verification Badge)",
        "subject": "Official Court Registry Verification Trust Badge for Your Law Firm Website",
        "file_name": "pitch_law_firm_badge_embed.md",
        "body": """Dear Counsel,

To distinguish your practice from unregulated, predatory third-party finders following the Supreme Court's Tyler v. Hennepin County precedent, we have released an official Surplus Docket Court Registry Verification Trust Badge.

Asset recovery law firms can embed this official seal in their website footer to display verified court docket indexing credentials:

Light Theme Badge:
```html
<a href="https://surplusdocket.com/#live-docket" title="Surplus Docket Court Registry Feeds" target="_blank" rel="noopener">
  <img src="https://surplusdocket.com/embed/badge.svg" alt="Verified by Surplus Docket" width="280" height="56" style="border: none;">
</a>
```

Dark Theme Badge:
```html
<a href="https://surplusdocket.com/#live-docket" title="Surplus Docket Court Registry Feeds" target="_blank" rel="noopener">
  <img src="https://surplusdocket.com/embed/badge-dark.svg" alt="Verified by Surplus Docket" width="280" height="56" style="border: none;">
</a>
```

Badge Preview & Documentation:
https://surplusdocket.com/embed/

Sincerely,
Surplus Docket Compliance & Institutional Feeds Desk
https://surplusdocket.com
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
                "short_description": "Surplus Docket aggregates daily tax deed surplus and excess proceeds court filings for asset recovery attorneys, with automated title scrubbing and statutory deadline calculations.",
                "website_url": "https://surplusdocket.com/",
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
