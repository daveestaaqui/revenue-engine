#!/usr/bin/env python3
"""
Surplus Docket - Automated Marketing, RSS & SEO Engine
======================================================
1. Dynamically generates site/feed.xml (RSS 2.0 feed of indexed public dockets)
2. Updates site/sitemap.xml with live ISO timestamps and all county landing pages
3. Submits instant indexation requests via IndexNow Protocol (Bing, Yandex, Seznam)
4. Generates educational legal syndicate summaries with backlink anchors
"""

import os
import csv
import sys
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = BASE_DIR / "site"
EXPORTS_DIR = BASE_DIR / "exports"
MARKETING_DIR = BASE_DIR / "marketing"
SYNDICATE_DIR = MARKETING_DIR / "syndicate"

INDEXNOW_KEY = "0a4d3f3acd10f37db48e4681df146902"

ALL_SITE_URLS = [
    "https://surplusdocket.com/",
    "https://surplusdocket.com/palm-beach-tax-deed-surplus.html",
    "https://surplusdocket.com/broward-county-tax-deed-surplus.html",
    "https://surplusdocket.com/harris-county-excess-proceeds.html",
    "https://surplusdocket.com/miami-dade-tax-deed-surplus.html",
    "https://surplusdocket.com/orange-county-tax-deed-surplus.html",
    "https://surplusdocket.com/hillsborough-tax-deed-surplus.html",
    "https://surplusdocket.com/dallas-county-excess-proceeds.html",
    "https://surplusdocket.com/tarrant-county-excess-proceeds.html",
    "https://surplusdocket.com/travis-county-excess-proceeds.html",
    "https://surplusdocket.com/fulton-county-excess-funds.html",
    "https://surplusdocket.com/cobb-county-excess-funds.html",
    "https://surplusdocket.com/dekalb-county-excess-funds.html",
    "https://surplusdocket.com/florida-tax-deed-surplus.html",
    "https://surplusdocket.com/texas-tax-sale-excess-proceeds.html",
    "https://surplusdocket.com/georgia-tax-sale-excess-funds.html",
    "https://surplusdocket.com/north-carolina-tax-foreclosure-surplus.html",
    "https://surplusdocket.com/tennessee-tax-sale-excess-proceeds.html",
    "https://surplusdocket.com/california-tax-defaulted-excess-proceeds.html",
    "https://surplusdocket.com/practitioner-toolkit.html",
    "https://surplusdocket.com/comparison.html",
    "https://surplusdocket.com/methodology.html",
    "https://surplusdocket.com/api-documentation.html",
    "https://surplusdocket.com/blog/",
    "https://surplusdocket.com/blog/posts/florida-tax-deed-surplus-guide-fl-197-582.html",
    "https://surplusdocket.com/blog/posts/texas-tax-sale-excess-proceeds-court-registry-guide.html",
    "https://surplusdocket.com/blog/posts/institutional-lien-filtering-asset-recovery.html",
    "https://surplusdocket.com/terms.html",
    "https://surplusdocket.com/refund-policy.html",
    "https://surplusdocket.com/press/",
    "https://surplusdocket.com/press/releases/surplus-docket-launches-autonomous-legal-intelligence-platform.html",
    "https://surplusdocket.com/press/releases/surplus-docket-unveils-rest-api-for-law-practice-management.html",
]

def generate_rss_feed():
    feed_path = SITE_DIR / "feed.xml"
    master_csv = EXPORTS_DIR / "Master_Surplus_Lead_Feed.csv"

    items_xml = ""
    now_rfc822 = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    if master_csv.exists():
        with open(master_csv, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= 10:
                    break
                state = row.get("State", "US")
                county = row.get("County", "")
                docket = row.get("Case_or_TaxDeed_No", "")
                statute = row.get("Governing_Statute", "State Law")

                items_xml += f"""
    <item>
      <title>[{state} - {county}] Docket {docket} Excess Proceeds Filing</title>
      <link>https://surplusdocket.com/?docket={docket}</link>
      <guid isPermaLink="false">{docket}-{state}</guid>
      <pubDate>{now_rfc822}</pubDate>
      <description>Public tax deed surplus docket filing in {county} County, {state}. Governed by {statute}. Indexed by Surplus Docket intelligence feeds.</description>
    </item>"""

    rss_content = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Surplus Docket - Daily Tax Deed Surplus &amp; Excess Proceeds Index</title>
    <link>https://surplusdocket.com/</link>
    <description>Daily public records intelligence tracking tax deed surplus and excess proceeds court dockets across Florida, Texas, and Georgia jurisdictions.</description>
    <language>en-us</language>
    <lastBuildDate>{now_rfc822}</lastBuildDate>
    <atom:link href="https://surplusdocket.com/feed.xml" rel="self" type="application/rss+xml" />
{items_xml}
  </channel>
</rss>"""

    feed_path.write_text(rss_content.strip(), encoding="utf-8")
    print(f"  [✓] Generated RSS Syndication Feed: {feed_path.name}")

def update_sitemap():
    sitemap_path = SITE_DIR / "sitemap.xml"
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    url_entries = ""
    for u in ALL_SITE_URLS:
        priority = "1.0" if u == "https://surplusdocket.com/" else ("0.9" if "county" in u or "surplus" in u or "proceeds" in u or "funds" in u or "toolkit" in u or "api" in u else "0.8")
        freq = "daily" if "feed" in u or u == "https://surplusdocket.com/" or "blog/" in u else "weekly"
        url_entries += f"""  <url>
    <loc>{u}</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
  </url>
"""

    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9
        http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
{url_entries}</urlset>"""

    sitemap_path.write_text(sitemap_xml.strip(), encoding="utf-8")
    print(f"  [✓] Updated Sitemap with {len(ALL_SITE_URLS)} canonical URLs: {sitemap_path.name}")

def submit_indexnow():
    """Submits all site URLs to IndexNow for instant crawling across Bing and AI search engines."""
    payload = {
        "host": "surplusdocket.com",
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://surplusdocket.com/{INDEXNOW_KEY}.txt",
        "urlList": ALL_SITE_URLS
    }
    
    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "SurplusDocket-IndexNow/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            if res.status in (200, 202):
                print(f"  [✓] IndexNow Instant Ping: Successfully submitted {len(ALL_SITE_URLS)} URLs (HTTP {res.status})")
            else:
                print(f"  [•] IndexNow Response Status: {res.status}")
    except Exception as e:
        print(f"  [•] IndexNow offline notice (will sync on live CI push): {e}")

def generate_syndicate_posts():
    SYNDICATE_DIR.mkdir(parents=True, exist_ok=True)
    digest_path = SYNDICATE_DIR / "daily_legal_digest.md"

    today_str = datetime.now().strftime("%B %d, %Y")
    content = f"""# Daily Tax Deed Surplus & Excess Proceeds Digest — {today_str}

## Legal Overview for Recovery Practitioners

### 1. Florida Statutory Update (Fla. Stat. § 197.582)
In Florida tax deed sales, the Clerk of the Circuit Court retains excess auction funds subject to the 120-day claim window following statutory notice. Practitioners tracking Orange, Palm Beach, Miami-Dade, and Hillsborough counties should verify junior mortgagee and equity holder rankings prior to filing petitions.

Reference & Daily Data Feeds: [Surplus Docket Florida Hub](https://surplusdocket.com/florida-tax-deed-surplus.html)

---

### 2. Texas Court Registry Update (Tex. Tax Code § 34.04)
Texas tax sales require formal petition filing in the district court within two (2) years of the auction date. Harris and Dallas County registries index new excess deposits following sheriff sale confirmations.

Reference & Daily Data Feeds: [Surplus Docket Texas Hub](https://surplusdocket.com/texas-tax-sale-excess-proceeds.html)

---

### 3. Georgia Excess Funds Update (O.C.G.A. § 48-4-5)
Georgia tax sales allow 5-year claim windows for excess proceeds distributed by county tax commissioners across Fulton, DeKalb, Gwinnett, and Cobb counties.

Reference & Daily Data Feeds: [Surplus Docket Georgia Hub](https://surplusdocket.com/georgia-tax-sale-excess-funds.html)

---

**Data Source & Public Records Archive:** [Surplus Docket](https://surplusdocket.com/)
"""
    digest_path.write_text(content.strip(), encoding="utf-8")
    print(f"  [✓] Generated Legal Syndicate Digest: {digest_path.name}")

def main():
    print("=" * 60)
    print(" 🛰️ SURPLUS DOCKET — AUTOMATED SEO & MARKETING ENGINE")
    print("=" * 60)
    generate_rss_feed()
    update_sitemap()
    generate_syndicate_posts()
    submit_indexnow()
    print("=" * 60)

if __name__ == "__main__":
    main()
