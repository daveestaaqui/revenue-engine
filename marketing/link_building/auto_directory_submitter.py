#!/usr/bin/env python3
"""
Surplus Docket — Autonomous High-DA Directory Submitter
======================================================
Automates submission of Surplus Docket's business, LegalTech, and SaaS profiles
to top-tier directories (LegalTech Hub, Launched.io, BetaList, SaaSHub, etc.)
using headless Playwright automation.

Capabilities:
1. Automated form field discovery (company, URL, email, tagline, description, categories).
2. Cookie banner & modal dismissal.
3. OAuth/login detection (flags platforms requiring single sign-on).
4. Full page proof-of-fill screenshots.
5. Bidirectional status tracking updating citation_registry.csv.
"""

import argparse
import asyncio
import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = BASE_DIR / "marketing" / "link_building" / "citation_registry.csv"
ARTIFACTS_DIR = BASE_DIR / "marketing" / "link_building" / "submission_artifacts"
PACKETS_DIR = BASE_DIR / "marketing" / "link_building" / "submission_packets"

COMPANY_DATA = {
    "name": "Surplus Docket",
    "legal_name": "Surplus Docket LLC",
    "tagline": "Real-Time Court Registry Intelligence for Foreclosure Surplus Recovery",
    "short_description": (
        "Surplus Docket is a legal intelligence platform delivering automated court registry feeds, "
        "subordinate encumbrance screening, and statutory deadline tracking for surplus funds and tax deed recovery attorneys."
    ),
    "long_description": (
        "Surplus Docket modernizes foreclosure surplus recovery for law firms. The platform ingests real-time "
        "court docket and excess proceeds registry records across Florida, Texas, California, Georgia, North Carolina, "
        "and Tennessee. By combining automated municipal and mortgage lien screening with statutory deadline calculations "
        "(Florida § 197.582, Texas § 34.04, California § 4675), Surplus Docket empowers attorneys to surface unencumbered "
        "court registry inventory within hours of sale confirmation without manual courthouse ledger research."
    ),
    "website_url": "https://surplusdocket.com/",
    "embed_url": "https://surplusdocket.com/embed/surplus-calculator.html",
    "contact_email": "contact@surplusdocket.com",
    "categories": ["LegalTech", "Legal Software", "Real Estate Intelligence", "B2B SaaS"],
    "pricing": "$249/mo (Subscription SaaS)"
}


async def dismiss_banners(page):
    """Dismisses cookie and consent overlays."""
    selectors = [
        "#onetrust-accept-btn-handler", ".cookie-accept", ".accept-cookies",
        "#accept-cookies", "button:has-text('Accept All')", "button:has-text('Accept Cookies')",
        "button:has-text('Accept')", "button:has-text('I Agree')", "button:has-text('Got It')",
        ".close-modal", ".modal-close", "button[aria-label='Close']"
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=250):
                await loc.click(timeout=1000)
                await page.wait_for_timeout(200)
        except Exception:
            pass


async def submit_to_directory(page, citation: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
    """Submits company profile to a single directory citation form."""
    url = citation.get("submission_url", "")
    name = citation.get("name", "Unknown Directory")
    res = {
        "directory": name,
        "url": url,
        "status": "failed",
        "fields_filled": [],
        "notes": "",
        "screenshot": ""
    }

    if not url or not url.startswith("http"):
        res["notes"] = "Invalid URL"
        return res

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())

    try:
        print(f"[*] Navigating to {name}: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(2000)
        await dismiss_banners(page)

        body_text = (await page.inner_text("body")).lower()

        # Check if page strictly requires login / OAuth
        oauth_cues = ["sign in with google", "continue with google", "log in with linkedin", "create an account to submit", "sign in to submit"]
        if any(c in body_text for c in oauth_cues) and not await page.locator("input[type='text'], input[type='url'], textarea").count():
            res["status"] = "REQUIRES_ACCOUNT_OAUTH"
            res["notes"] = "Directory requires registered user account or OAuth login before submission form is visible."
            screenshot_path = ARTIFACTS_DIR / f"{slug}_oauth_wall.png"
            await page.screenshot(path=str(screenshot_path))
            res["screenshot"] = str(screenshot_path)
            return res

        # Field discovery and population
        filled = []

        # 1. Company / Startup / Product Name
        name_selectors = [
            "input[name*='company']", "input[name*='name']", "input[name*='title']",
            "input[name*='product']", "input[name*='startup']", "input[id*='name']",
            "input[placeholder*='Company' i]", "input[placeholder*='Product' i]", "input[placeholder*='Name' i]"
        ]
        for sel in name_selectors:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=300):
                await loc.fill(COMPANY_DATA["name"])
                filled.append("company_name")
                break

        # 2. Website URL
        url_selectors = [
            "input[type='url']", "input[name*='url']", "input[name*='website']",
            "input[name*='link']", "input[placeholder*='http' i]", "input[placeholder*='website' i]"
        ]
        for sel in url_selectors:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=300):
                await loc.fill(COMPANY_DATA["website_url"])
                filled.append("website_url")
                break

        # 3. Email Address
        email_selectors = [
            "input[type='email']", "input[name*='email']", "input[id*='email']",
            "input[placeholder*='email' i]"
        ]
        for sel in email_selectors:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=300):
                await loc.fill(COMPANY_DATA["contact_email"])
                filled.append("contact_email")
                break

        # 4. Tagline / Short Pitch
        tag_selectors = [
            "input[name*='tagline']", "input[name*='headline']", "input[name*='pitch']",
            "input[name*='short']", "input[placeholder*='tagline' i]", "input[placeholder*='headline' i]"
        ]
        for sel in tag_selectors:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=300):
                await loc.fill(COMPANY_DATA["tagline"])
                filled.append("tagline")
                break

        # 5. Long Description / About
        desc_selectors = [
            "textarea[name*='desc']", "textarea[name*='about']", "textarea[name*='detail']",
            "textarea[name*='pitch']", "textarea[placeholder*='describe' i]", "textarea"
        ]
        for sel in desc_selectors:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=300):
                await loc.fill(COMPANY_DATA["long_description"])
                filled.append("long_description")
                break

        res["fields_filled"] = filled
        screenshot_path = ARTIFACTS_DIR / f"{slug}_populated.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)
        res["screenshot"] = str(screenshot_path)

        if len(filled) >= 2:
            if dry_run:
                res["status"] = "SIMULATED_SUCCESS"
                res["notes"] = f"Verified {len(filled)} form fields populated ({', '.join(filled)}). Dry run completed."
            else:
                # Live submission attempt
                submit_selectors = [
                    "button[type='submit']", "input[type='submit']",
                    "button:has-text('Submit')", "button:has-text('Add')",
                    "button:has-text('Create')", "button:has-text('Continue')"
                ]
                submitted = False
                for s_sel in submit_selectors:
                    sub_loc = page.locator(s_sel).first
                    if await sub_loc.is_visible(timeout=500):
                        try:
                            await sub_loc.click(timeout=3000)
                            submitted = True
                            break
                        except Exception:
                            try:
                                await sub_loc.click(force=True, timeout=1500)
                                submitted = True
                                break
                            except Exception:
                                pass
                if submitted:
                    await page.wait_for_timeout(3000)
                    res["status"] = "SUBMITTED"
                    res["notes"] = f"Successfully submitted profile to {name}."
                else:
                    res["status"] = "POPULATED_READY_TO_SUBMIT"
                    res["notes"] = "Form fields populated, submit button required manual confirmation."
        else:
            res["status"] = "UNSUPPORTED_FORM_LAYOUT"
            res["notes"] = f"Only detected {len(filled)} matchable fields. May require bespoke profile claim flow."

    except Exception as e:
        res["status"] = "NETWORK_OR_TIMEOUT_ERROR"
        res["notes"] = str(e)[:150]

    return res


def update_registry_status(name: str, new_status: str):
    """Persists updated directory status to citation_registry.csv."""
    if not REGISTRY_PATH.exists():
        return
    rows = []
    fieldnames = []
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for r in reader:
            if r["name"].strip().lower() == name.strip().lower():
                r["status"] = new_status
            rows.append(r)
    if fieldnames:
        with open(REGISTRY_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


async def run_directory_pipeline(limit: int = 5, dry_run: bool = True, target_name: Optional[str] = None):
    """Runs automated directory submission across curated high-DA directory citations."""
    if not PLAYWRIGHT_AVAILABLE:
        print("[!] Playwright is not installed. Run 'pip install playwright && playwright install chromium'.")
        return []

    citations = []
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            citations.append(r)

    # Filter target if specified
    if target_name:
        citations = [c for c in citations if target_name.lower() in c["name"].lower()]

    targets = citations[:limit]
    print(f"[*] Starting Autonomous Directory Submissions ({len(targets)} targets, dry_run={dry_run})...")

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        for c in targets:
            name = c["name"]
            st = await submit_to_directory(page, c, dry_run=dry_run)
            results.append(st)
            print(f"  -> [{st['status']}] {name}: {st['notes']}")
            if st["status"] in ("SUBMITTED", "REQUIRES_ACCOUNT_OAUTH"):
                update_registry_status(name, st["status"])

        await browser.close()

    summary_file = ARTIFACTS_DIR / "directory_submission_summary.json"
    summary_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"[*] Directory submission run complete. Summary saved to: {summary_file}")
    return results


def main():
    parser = argparse.ArgumentParser(description="Surplus Docket Autonomous Directory Submitter")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run in dry-run mode (populate and verify without submitting)")
    parser.add_argument("--live", dest="dry_run", action="store_false", help="Run in LIVE submission mode")
    parser.add_argument("--limit", type=int, default=3, help="Max directories to process in this run")
    parser.add_argument("--directory", type=str, default=None, help="Process a specific directory by name")
    args = parser.parse_args()

    asyncio.run(run_directory_pipeline(limit=args.limit, dry_run=args.dry_run, target_name=args.directory))


if __name__ == "__main__":
    main()
