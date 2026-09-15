#!/usr/bin/env python3
"""
Surplus Docket — Automated RSS Feed Generator
Generates site/feed.xml and site/rss.xml from all published legal guides and press releases using stdlib only.
Enables instant search engine indexing, feed syndication (Ping-O-Matic), and RSS aggregator distribution.
"""

import html
import os
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = BASE_DIR / "site"
BLOG_DIR = SITE_DIR / "blog" / "posts"
PRESS_DIR = SITE_DIR / "press" / "releases"
FEED_PATH = SITE_DIR / "feed.xml"
RSS_PATH = SITE_DIR / "rss.xml"


def extract_article_info(filepath: Path) -> dict:
    try:
        content = filepath.read_text(encoding="utf-8")
        
        # Title
        m_title = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
        if m_title:
            raw_title = html.unescape(m_title.group(1).strip())
            title = re.sub(r"^Surplus Docket\s*[—–-]\s*", "", raw_title)
        else:
            title = filepath.stem.replace("-", " ").title()
            
        # Description
        m_desc = (
            re.search(r'<meta\s+name=["\']description["\']\s+content="([^"]*)"', content, re.IGNORECASE) or
            re.search(r'<meta\s+name=["\']description["\']\s+content=\'([^\']*)\'', content, re.IGNORECASE) or
            re.search(r'<meta\s+content="([^"]*)"\s+name=["\']description["\']', content, re.IGNORECASE) or
            re.search(r'<meta\s+property=["\']og:description["\']\s+content="([^"]*)"', content, re.IGNORECASE) or
            re.search(r'<meta\s+property=["\']og:description["\']\s+content=\'([^\']*)\'', content, re.IGNORECASE)
        )
        description = html.unescape(m_desc.group(1).strip()) if m_desc else ""
        
        # Canonical URL
        m_canon = (
            re.search(r'<link\s+rel=["\']canonical["\']\s+href="([^"]*)"', content, re.IGNORECASE) or
            re.search(r'<link\s+rel=["\']canonical["\']\s+href=\'([^\']*)\'', content, re.IGNORECASE) or
            re.search(r'<meta\s+property=["\']og:url["\']\s+content="([^"]*)"', content, re.IGNORECASE)
        )
        if m_canon:
            url = m_canon.group(1).strip()
        else:
            rel_path = filepath.relative_to(SITE_DIR)
            url = f"https://surplusdocket.com/{rel_path}"
            
        # Published date
        m_time = re.search(r'<meta\s+property=["\']article:published_time["\']\s+content=["\'](.*?)["\']', content, re.IGNORECASE)
        if m_time:
            try:
                date_str = m_time.group(1).strip()
                pub_dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            except Exception:
                pub_dt = datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc)
        else:
            pub_dt = datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc)
            
        return {
            "title": title,
            "description": description,
            "url": url,
            "pubDate": pub_dt,
            "guid": url
        }
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None


def generate_rss():
    articles = []
    
    # Process blog posts
    if BLOG_DIR.exists():
        for p in sorted(BLOG_DIR.glob("*.html")):
            info = extract_article_info(p)
            if info:
                articles.append(info)
                
    # Process press releases
    if PRESS_DIR.exists():
        for p in sorted(PRESS_DIR.glob("*.html")):
            info = extract_article_info(p)
            if info:
                articles.append(info)
                
    # Sort by pubDate descending
    articles.sort(key=lambda x: x["pubDate"], reverse=True)
    
    now_rfc = format_datetime(datetime.now(timezone.utc))
    
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        '  <channel>',
        '    <title>Surplus Docket — Legal Intelligence &amp; Court Registry Feeds</title>',
        '    <link>https://surplusdocket.com/</link>',
        '    <description>Real-time court docket intelligence, statutory surplus fund recovery analysis, and municipal lien screening for foreclosure counsel.</description>',
        '    <language>en-us</language>',
        f'    <lastBuildDate>{now_rfc}</lastBuildDate>',
        '    <atom:link href="https://surplusdocket.com/feed.xml" rel="self" type="application/rss+xml" />'
    ]
    
    for art in articles:
        pub_rfc = format_datetime(art["pubDate"])
        clean_title = html.escape(art["title"])
        clean_desc = html.escape(art["description"])
        xml_lines.extend([
            '    <item>',
            f'      <title>{clean_title}</title>',
            f'      <link>{art["url"]}</link>',
            f'      <guid isPermaLink="true">{art["guid"]}</guid>',
            f'      <pubDate>{pub_rfc}</pubDate>',
            f'      <description>{clean_desc}</description>',
            '    </item>'
        ])
        
    xml_lines.extend([
        '  </channel>',
        '</rss>'
    ])
    
    rss_content = "\n".join(xml_lines)
    FEED_PATH.write_text(rss_content, encoding="utf-8")
    RSS_PATH.write_text(rss_content, encoding="utf-8")
    print(f"Generated {FEED_PATH} and {RSS_PATH} with {len(articles)} items.")


if __name__ == "__main__":
    generate_rss()
