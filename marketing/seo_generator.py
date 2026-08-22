#!/usr/bin/env python3
"""
Surplus Docket - Automated Marketing, RSS & SEO Engine
======================================================
1. Dynamically generates site/feed.xml (RSS 2.0 feed of indexed public dockets)
2. Updates site/sitemap.xml with live ISO timestamps
3. Generates educational legal syndicate summaries with backlink anchors
"""

import os
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

BASE_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = BASE_DIR / "site"
EXPORTS_DIR = BASE_DIR / "exports"
MARKETING_DIR = BASE_DIR / "marketing"
SYNDICATE_DIR = MARKETING_DIR / "syndicate"


def generate_rss_feed():
    """Generates a valid RSS 2.0 XML feed of recent public court records for syndication."""
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
                balance = row.get("Surplus_Balance_USD", "0")
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
    <description>Daily public records intelligence tracking tax deed surplus and excess proceeds court dockets across Florida and Texas jurisdictions.</description>
    <language>en-us</language>
    <lastBuildDate>{now_rfc822}</lastBuildDate>
    <atom:link href="https://surplusdocket.com/feed.xml" rel="self" type="application/rss+xml" />
{items_xml}
  </channel>
</rss>"""

    feed_path.write_text(rss_content.strip(), encoding="utf-8")
    print(f"  [✓] Generated RSS Syndication Feed: {feed_path.name}")


def update_sitemap():
    """Refreshes sitemap.xml with today's date."""
    sitemap_path = SITE_DIR / "sitemap.xml"
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9
        http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
  <url>
    <loc>https://surplusdocket.com/</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://surplusdocket.com/api-documentation.html</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://surplusdocket.com/florida-tax-deed-surplus.html</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://surplusdocket.com/texas-tax-sale-excess-proceeds.html</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://surplusdocket.com/georgia-tax-sale-excess-funds.html</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://surplusdocket.com/blog/</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://surplusdocket.com/blog/posts/florida-tax-deed-surplus-guide-fl-197-582.html</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://surplusdocket.com/blog/posts/texas-tax-sale-excess-proceeds-court-registry-guide.html</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://surplusdocket.com/blog/posts/institutional-lien-filtering-asset-recovery.html</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://surplusdocket.com/api/v1/feed.json</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://surplusdocket.com/feed.xml</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>"""

    sitemap_path.write_text(sitemap_xml.strip(), encoding="utf-8")
    print(f"  [✓] Updated Sitemap with ISO date: {sitemap_path.name}")


def generate_syndicate_posts():
    """Creates copy-paste legal/industry forum snippets with canonical link anchors."""
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

**Data Source & Public Records Archive:** [Surplus Docket](https://surplusdocket.com/)
"""
    digest_path.write_text(content.strip(), encoding="utf-8")
    print(f"  [✓] Generated Legal Syndicate Digest: {digest_path.name}")


def ping_search_engines():
    """Notifies Google and Bing search indexers of newly published sitemaps and legal content."""
    import urllib.request

    sitemap_url = "https://surplusdocket.com/sitemap.xml"
    endpoints = [
        ("Google", f"https://www.google.com/ping?sitemap={sitemap_url}"),
        ("Bing", f"https://www.bing.com/ping?sitemap={sitemap_url}"),
    ]
    for engine, url in endpoints:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SurplusDocket-SEO-Bot/1.0"})
            with urllib.request.urlopen(req, timeout=8) as res:
                print(f"  [✓] Pinged {engine} Indexer (Status: {res.status})")
        except Exception as e:
            # Pings can be rate-limited or return 404 in local dry-runs, handle silently
            print(f"  [•] {engine} index ping notice: {e}")


def main():
    print("=" * 60)
    print(" 🛰️ SURPLUS DOCKET — AUTOMATED SEO & MARKETING ENGINE")
    print("=" * 60)
    generate_rss_feed()
    update_sitemap()
    generate_syndicate_posts()
    ping_search_engines()
    print("=" * 60)


if __name__ == "__main__":
    main()
