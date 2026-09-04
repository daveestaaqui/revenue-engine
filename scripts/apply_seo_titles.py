#!/usr/bin/env python3
"""
Applies institutional, keyword-optimized titles starting with 'Surplus Docket — '
across all 36 HTML files in site/.
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = BASE_DIR / "site"

TITLE_MAP = {
    "index.html": {
        "title": "Surplus Docket — Daily Tax Deed Surplus &amp; Excess Proceeds Intelligence",
        "og_title": "Surplus Docket — Daily Tax Deed Surplus & Excess Proceeds Intelligence",
    },
    "inquiry.html": {
        "title": "Surplus Docket — Statutory Inquiries &amp; Legal Practice Intake",
        "og_title": "Surplus Docket — Statutory Inquiries & Legal Practice Intake",
    },
    "api-documentation.html": {
        "title": "Surplus Docket — REST JSON API Documentation &amp; Intake Automation",
        "og_title": "Surplus Docket — REST JSON API Documentation & Intake Automation",
    },
    "practitioner-toolkit.html": {
        "title": "Surplus Docket — Asset Recovery Practitioner Toolkit &amp; Statutory Templates",
        "og_title": "Surplus Docket — Asset Recovery Practitioner Toolkit & Statutory Templates",
    },
    "methodology.html": {
        "title": "Surplus Docket — Data Provenance &amp; Upstream Lien Scrubbing Methodology",
        "og_title": "Surplus Docket — Data Provenance & Upstream Lien Scrubbing Methodology",
    },
    "comparison.html": {
        "title": "Surplus Docket — Data Provider Comparison &amp; Architecture Audit",
        "og_title": "Surplus Docket — Data Provider Comparison & Architecture Audit",
    },
    "welcome.html": {
        "title": "Surplus Docket — Subscriber Onboarding &amp; Morning Feed Activation",
        "og_title": "Surplus Docket — Subscriber Onboarding & Morning Feed Activation",
    },
    "terms.html": {
        "title": "Surplus Docket — Terms of Service &amp; Commercial Data License",
        "og_title": "Surplus Docket — Terms of Service & Commercial Data License",
    },
    "refund-policy.html": {
        "title": "Surplus Docket — Refund &amp; Subscription Cancellation Policy",
        "og_title": "Surplus Docket — Refund & Subscription Cancellation Policy",
    },
    "404.html": {
        "title": "Surplus Docket — Docket Not Located (404 Error)",
        "og_title": "Surplus Docket — Docket Not Located (404 Error)",
    },
    "florida-tax-deed-surplus.html": {
        "title": "Surplus Docket — Florida Tax Deed Surplus &amp; Excess Proceeds (Fla. Stat. § 197.582)",
        "og_title": "Surplus Docket — Florida Tax Deed Surplus & Excess Proceeds (Fla. Stat. § 197.582)",
    },
    "texas-tax-sale-excess-proceeds.html": {
        "title": "Surplus Docket — Texas Tax Sale Excess Proceeds (Tex. Tax Code § 34.04)",
        "og_title": "Surplus Docket — Texas Tax Sale Excess Proceeds (Tex. Tax Code § 34.04)",
    },
    "georgia-tax-sale-excess-funds.html": {
        "title": "Surplus Docket — Georgia Tax Sale Excess Funds (O.C.G.A. § 48-4-5)",
        "og_title": "Surplus Docket — Georgia Tax Sale Excess Funds (O.C.G.A. § 48-4-5)",
    },
    "north-carolina-tax-foreclosure-surplus.html": {
        "title": "Surplus Docket — North Carolina Tax Foreclosure Surplus (N.C.G.S. § 105-374)",
        "og_title": "Surplus Docket — North Carolina Tax Foreclosure Surplus (N.C.G.S. § 105-374)",
    },
    "tennessee-tax-sale-excess-proceeds.html": {
        "title": "Surplus Docket — Tennessee Tax Sale Excess Proceeds (T.C.A. § 67-5-2501)",
        "og_title": "Surplus Docket — Tennessee Tax Sale Excess Proceeds (T.C.A. § 67-5-2501)",
    },
    "california-tax-defaulted-excess-proceeds.html": {
        "title": "Surplus Docket — California Tax-Defaulted Excess Proceeds (Cal. Rev. &amp; Tax Code § 4675)",
        "og_title": "Surplus Docket — California Tax-Defaulted Excess Proceeds (Cal. Rev. & Tax Code § 4675)",
    },
    "miami-dade-tax-deed-surplus.html": {
        "title": "Surplus Docket — Miami-Dade County Tax Deed Surplus &amp; Excess Proceeds",
        "og_title": "Surplus Docket — Miami-Dade County Tax Deed Surplus & Excess Proceeds",
    },
    "orange-county-tax-deed-surplus.html": {
        "title": "Surplus Docket — Orange County Tax Deed Surplus &amp; Excess Proceeds",
        "og_title": "Surplus Docket — Orange County Tax Deed Surplus & Excess Proceeds",
    },
    "palm-beach-tax-deed-surplus.html": {
        "title": "Surplus Docket — Palm Beach County Tax Deed Surplus &amp; Excess Proceeds",
        "og_title": "Surplus Docket — Palm Beach County Tax Deed Surplus & Excess Proceeds",
    },
    "hillsborough-tax-deed-surplus.html": {
        "title": "Surplus Docket — Hillsborough County Tax Deed Surplus &amp; Excess Proceeds",
        "og_title": "Surplus Docket — Hillsborough County Tax Deed Surplus & Excess Proceeds",
    },
    "broward-county-tax-deed-surplus.html": {
        "title": "Surplus Docket — Broward County Tax Deed Surplus &amp; Excess Proceeds",
        "og_title": "Surplus Docket — Broward County Tax Deed Surplus & Excess Proceeds",
    },
    "harris-county-excess-proceeds.html": {
        "title": "Surplus Docket — Harris County Excess Proceeds &amp; Tax Sale Surplus",
        "og_title": "Surplus Docket — Harris County Excess Proceeds & Tax Sale Surplus",
    },
    "dallas-county-excess-proceeds.html": {
        "title": "Surplus Docket — Dallas County Excess Proceeds &amp; Tax Sale Surplus",
        "og_title": "Surplus Docket — Dallas County Excess Proceeds & Tax Sale Surplus",
    },
    "tarrant-county-excess-proceeds.html": {
        "title": "Surplus Docket — Tarrant County Excess Proceeds &amp; Tax Sale Surplus",
        "og_title": "Surplus Docket — Tarrant County Excess Proceeds & Tax Sale Surplus",
    },
    "travis-county-excess-proceeds.html": {
        "title": "Surplus Docket — Travis County Excess Proceeds &amp; Tax Sale Surplus",
        "og_title": "Surplus Docket — Travis County Excess Proceeds & Tax Sale Surplus",
    },
    "fulton-county-excess-funds.html": {
        "title": "Surplus Docket — Fulton County Excess Funds &amp; Tax Sale Surplus",
        "og_title": "Surplus Docket — Fulton County Excess Funds & Tax Sale Surplus",
    },
    "dekalb-county-excess-funds.html": {
        "title": "Surplus Docket — DeKalb County Excess Funds &amp; Tax Sale Surplus",
        "og_title": "Surplus Docket — DeKalb County Excess Funds & Tax Sale Surplus",
    },
    "cobb-county-excess-funds.html": {
        "title": "Surplus Docket — Cobb County Excess Funds &amp; Tax Sale Surplus",
        "og_title": "Surplus Docket — Cobb County Excess Funds & Tax Sale Surplus",
    },
    "blog/index.html": {
        "title": "Surplus Docket — Legal Insights, Case Law &amp; Statutory Surplus Guides",
        "og_title": "Surplus Docket — Legal Insights, Case Law & Statutory Surplus Guides",
    },
    "blog/posts/tyler-v-hennepin-county-surplus-recovery-opportunity.html": {
        "title": "Surplus Docket — Tyler v. Hennepin County: Supreme Court Ruling Unlocks $8B+ Surplus",
        "og_title": "Surplus Docket — Tyler v. Hennepin County: Supreme Court Ruling Unlocks $8B+ Surplus",
    },
    "blog/posts/florida-tax-deed-surplus-guide-fl-197-582.html": {
        "title": "Surplus Docket — Florida Tax Deed Surplus Guide (Fla. Stat. § 197.582)",
        "og_title": "Surplus Docket — Florida Tax Deed Surplus Guide (Fla. Stat. § 197.582)",
    },
    "blog/posts/texas-tax-sale-excess-proceeds-court-registry-guide.html": {
        "title": "Surplus Docket — Texas Tax Sale Excess Proceeds: District Court Registry Guide",
        "og_title": "Surplus Docket — Texas Tax Sale Excess Proceeds: District Court Registry Guide",
    },
    "blog/posts/institutional-lien-filtering-asset-recovery.html": {
        "title": "Surplus Docket — Why Institutional Lien Pre-Filtering Multiplies Firm ROI",
        "og_title": "Surplus Docket — Why Institutional Lien Pre-Filtering Multiplies Firm ROI",
    },
    "press/index.html": {
        "title": "Surplus Docket — Press Newsroom &amp; Media Announcements",
        "og_title": "Surplus Docket — Press Newsroom & Media Announcements",
    },
    "press/releases/surplus-docket-unveils-rest-api-for-law-practice-management.html": {
        "title": "Surplus Docket — REST JSON API Release for Law Firm Intake Automation",
        "og_title": "Surplus Docket — REST JSON API Release for Law Firm Intake Automation",
    },
    "press/releases/surplus-docket-launches-autonomous-legal-intelligence-platform.html": {
        "title": "Surplus Docket — Platform Launch: Autonomous Legal Intelligence for Counsel",
        "og_title": "Surplus Docket — Platform Launch: Autonomous Legal Intelligence for Counsel",
    },
}


def apply_titles():
    updated_count = 0
    for rel_path, data in TITLE_MAP.items():
        file_path = SITE_DIR / rel_path
        if not file_path.exists():
            print(f"Skipping missing file: {file_path}")
            continue

        content = file_path.read_text(encoding="utf-8")
        
        # Replace <title>...</title>
        new_title = data["title"]
        content = re.sub(r"<title>.*?</title>", f"<title>{new_title}</title>", content, count=1)

        # Replace og:title and twitter:title if present
        og_title = data["og_title"]
        content = re.sub(r'<meta property="og:title" content=".*?"\s*/?>', f'<meta property="og:title" content="{og_title}">', content)
        content = re.sub(r'<meta name="twitter:title" content=".*?"\s*/?>', f'<meta name="twitter:title" content="{og_title}">', content)

        file_path.write_text(content, encoding="utf-8")
        updated_count += 1
        print(f"✓ Updated {rel_path} -> {new_title}")

    print(f"\nSuccessfully updated {updated_count} files.")


if __name__ == "__main__":
    apply_titles()
