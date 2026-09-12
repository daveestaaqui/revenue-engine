#!/usr/bin/env python3
"""
Surplus Docket — Autonomous Article Submitter & Search Engine Syndication Engine
================================================================================
Automates immediate indexing and multi-channel publication across:
1. IndexNow API (Microsoft Bing, Yandex, Naver, Seznam) for instant URL crawling.
2. Search Engine Sitemaps ping (Google, Bing).
3. Dev.to REST API for automated canonical article distribution.
4. Medium REST API for automated canonical publication.
5. Multi-channel webhook syndication (Zapier / Make / Buffer / Hootsuite / n8n).
6. Persistent submission history tracking in submission_registry.json.

Zero Local Execution Required: Designed to run 100% headlessly in GitHub Actions.
"""

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SITEMAP_PATH = BASE_DIR / "site" / "sitemap.xml"
INDEXNOW_KEY_FILE = BASE_DIR / "site" / "0a4d3f3acd10f37db48e4681df146902.txt"
REGISTRY_PATH = BASE_DIR / "marketing" / "link_building" / "submission_registry.json"
SYNDICATE_DIR = BASE_DIR / "marketing" / "syndicate" / "published"

DEFAULT_HOST = "surplusdocket.com"
DEFAULT_KEY = "0a4d3f3acd10f37db48e4681df146902"


def get_indexnow_key() -> str:
    """Reads verification key from site/0a4d3f3acd10f37db48e4681df146902.txt."""
    if INDEXNOW_KEY_FILE.exists():
        key = INDEXNOW_KEY_FILE.read_text(encoding="utf-8").strip()
        if key:
            return key
    return DEFAULT_KEY


def parse_sitemap_urls(sitemap_path: Optional[Path] = None) -> List[str]:
    """Extracts all canonical loc URLs from sitemap.xml."""
    path = sitemap_path or SITEMAP_PATH
    if not path.exists():
        return [f"https://{DEFAULT_HOST}/"]

    urls = []
    try:
        tree = ET.parse(str(path))
        root = tree.getroot()
        namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for loc in root.findall(".//ns:loc", namespace):
            if loc.text:
                urls.append(loc.text.strip())
    except Exception as e:
        print(f"[!] Warning: failed to parse sitemap XML ({e}). Using root domain.")
        urls = [f"https://{DEFAULT_HOST}/"]

    return sorted(list(set(urls)))


def submit_to_indexnow(
    url_list: List[str],
    host: str = DEFAULT_HOST,
    key: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Submits a batch of URLs to the IndexNow protocol (api.indexnow.org).
    IndexNow instantly notifies Bing, Yandex, Naver, and Seznam to crawl and index.
    """
    actual_key = key or get_indexnow_key()
    key_location = f"https://{host}/{actual_key}.txt"

    payload = {
        "host": host,
        "key": actual_key,
        "keyLocation": key_location,
        "urlList": url_list[:10000]  # Protocol supports up to 10k URLs per request
    }

    result = {
        "engine": "IndexNow",
        "endpoint": "https://api.indexnow.org/indexnow",
        "urls_submitted": len(url_list),
        "status": "pending",
        "status_code": 0,
        "response": ""
    }

    if dry_run:
        result["status"] = "dry_run_success"
        result["status_code"] = 200
        result["response"] = f"[DRY RUN] {len(url_list)} URLs queued for IndexNow submission."
        return result

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "SurplusDocket-Submitter/1.0"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status_code = resp.getcode()
            result["status_code"] = status_code
            result["status"] = "success" if status_code in (200, 202) else f"code_{status_code}"
            result["response"] = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        result["status_code"] = e.code
        # 202 Accepted is standard for IndexNow
        if e.code in (200, 202):
            result["status"] = "success"
        else:
            result["status"] = f"http_error_{e.code}"
        result["response"] = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else str(e)
    except Exception as ex:
        result["status"] = "network_error"
        result["response"] = str(ex)

    return result


def ping_search_engines(sitemap_url: str = f"https://{DEFAULT_HOST}/sitemap.xml", dry_run: bool = False) -> Dict[str, Any]:
    """Legacy compatibility API: these unauthenticated endpoints were retired."""
    return {name: {"status": "retired_use_robots_and_webmaster_tools", "sitemap_url": sitemap_url}
            for name in ("google", "bing")}


def parse_markdown_metadata(content: str) -> Dict[str, Any]:
    """Parses header comment or frontmatter metadata from syndication markdown."""
    meta = {
        "platform": "",
        "title": "",
        "canonical_url": "",
        "tags": [],
        "body": ""
    }
    header_match = re.search(r"<!--(.*?)-->", content, re.DOTALL) or re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if header_match:
        lines = header_match.group(1).strip().splitlines()
        for line in lines:
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip().lower()
                val = val.strip()
                if key == "platform":
                    meta["platform"] = val
                elif key == "title":
                    meta["title"] = val
                elif key == "canonical_url":
                    meta["canonical_url"] = val
                elif key == "tags":
                    meta["tags"] = [t.strip() for t in val.split(",") if t.strip()]

    # Extract body without the metadata block
    body_content = re.sub(r"<!--(.*?)-->", "", content, flags=re.DOTALL)
    body_content = re.sub(r"^---\s*\n(.*?)\n---", "", body_content, flags=re.DOTALL).strip()
    meta["body"] = body_content
    return meta


def submit_dev_to_article(
    article_meta: Dict[str, Any],
    api_key: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Submits an article to Dev.to REST API (POST https://dev.to/api/articles).
    Includes canonical_url to preserve SEO link equity and avoid duplicate penalties.
    """
    key = api_key or os.environ.get("DEV_TO_API_KEY", "")
    title = article_meta.get("title", "")
    canonical_url = article_meta.get("canonical_url", "")
    body = article_meta.get("body", "")
    # Dev.to supports up to 4 lowercase alphanumeric tags
    tags = [re.sub(r'[^a-zA-Z0-9]', '', t).lower() for t in article_meta.get("tags", [])][:4]

    payload = {
        "article": {
            "title": title,
            "body_markdown": body,
            "published": True,
            "canonical_url": canonical_url,
            "tags": tags,
            "series": "Surplus Docket Legal Tech"
        }
    }

    if not key or dry_run:
        status_label = "dry_run_success" if dry_run else "simulated_no_api_key"
        return {
            "platform": "dev.to",
            "title": title,
            "canonical_url": canonical_url,
            "status": status_label,
            "note": "Configured and payload verified. Set DEV_TO_API_KEY secret in GitHub Actions to publish live.",
            "payload_preview": {
                "title": title,
                "canonical_url": canonical_url,
                "tags": tags,
                "body_length": len(body)
            }
        }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://dev.to/api/articles",
        data=data,
        headers={
            "Content-Type": "application/json",
            "api-key": key,
            "User-Agent": "SurplusDocket-Submitter/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            return {
                "platform": "dev.to",
                "title": title,
                "canonical_url": canonical_url,
                "status": "success",
                "status_code": resp.getcode(),
                "published_url": resp_data.get("url", "")
            }
    except urllib.error.HTTPError as e:
        return {
            "platform": "dev.to",
            "title": title,
            "status": f"http_error_{e.code}",
            "response": e.read().decode("utf-8", errors="ignore")
        }
    except Exception as ex:
        return {
            "platform": "dev.to",
            "title": title,
            "status": "network_error",
            "error": str(ex)
        }


def submit_medium_article(
    article_meta: Dict[str, Any],
    token: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Submits an article to Medium REST API (POST https://api.medium.com/v1/users/{userId}/posts).
    Includes canonicalUrl for Google search indexing authority.
    """
    integration_token = token or os.environ.get("MEDIUM_TOKEN", "")
    title = article_meta.get("title", "")
    canonical_url = article_meta.get("canonical_url", "")
    body = article_meta.get("body", "")
    tags = article_meta.get("tags", [])[:5]

    if not integration_token or dry_run:
        status_label = "dry_run_success" if dry_run else "simulated_no_token"
        return {
            "platform": "medium",
            "title": title,
            "canonical_url": canonical_url,
            "status": status_label,
            "note": "Configured and payload verified. Set MEDIUM_TOKEN secret in GitHub Actions to publish live.",
            "payload_preview": {
                "title": title,
                "canonical_url": canonical_url,
                "tags": tags,
                "content_format": "markdown"
            }
        }

    try:
        user_req = urllib.request.Request(
            "https://api.medium.com/v1/me",
            headers={"Authorization": f"Bearer {integration_token}", "User-Agent": "SurplusDocket-Submitter/1.0"}
        )
        with urllib.request.urlopen(user_req, timeout=10) as user_resp:
            user_data = json.loads(user_resp.read().decode("utf-8"))
            user_id = user_data["data"]["id"]

        post_payload = {
            "title": title,
            "contentFormat": "markdown",
            "content": body,
            "canonicalUrl": canonical_url,
            "tags": tags,
            "publishStatus": "public"
        }
        data = json.dumps(post_payload).encode("utf-8")
        post_req = urllib.request.Request(
            f"https://api.medium.com/v1/users/{user_id}/posts",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration_token}",
                "User-Agent": "SurplusDocket-Submitter/1.0"
            },
            method="POST"
        )
        with urllib.request.urlopen(post_req, timeout=15) as post_resp:
            post_data = json.loads(post_resp.read().decode("utf-8"))
            return {
                "platform": "medium",
                "title": title,
                "canonical_url": canonical_url,
                "status": "success",
                "url": post_data.get("data", {}).get("url", "")
            }
    except Exception as ex:
        return {
            "platform": "medium",
            "title": title,
            "status": "error",
            "error": str(ex)
        }


def dispatch_webhook_syndication(
    articles: List[Dict[str, Any]],
    webhook_url: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Dispatches articles to a custom syndication webhook (e.g. Zapier, Make, n8n, Buffer)."""
    target_url = webhook_url or os.environ.get("SYNDICATION_WEBHOOK_URL", "")
    if not target_url or dry_run:
        return {
            "platform": "webhook",
            "status": "dry_run_success" if dry_run else "no_webhook_configured",
            "articles_queued": len(articles),
            "note": "Optional: set SYNDICATION_WEBHOOK_URL to distribute directly to social schedulers or RSS."
        }

    payload = {
        "source": "Surplus Docket Autonomous Submitter",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "articles": articles
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        target_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"platform": "webhook", "status": "success", "status_code": resp.getcode()}
    except Exception as ex:
        return {"platform": "webhook", "status": "error", "error": str(ex)}


def load_submission_registry() -> Dict[str, Any]:
    """Loads historical submission registry."""
    if REGISTRY_PATH.exists():
        try:
            return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_submissions": 0,
        "runs": []
    }


def save_submission_registry(registry_data: Dict[str, Any]) -> None:
    """Saves updated submission history."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(registry_data, indent=2), encoding="utf-8")


def get_published_targets(registry: Dict[str, Any]) -> set:
    """Extract set of (platform, identifier) already successfully published."""
    published = set()
    for entry in registry.get("published_articles", []):
        plat = entry.get("platform", "").lower()
        key = (entry.get("canonical_url") or entry.get("title", "")).strip().lower()
        if plat and key:
            published.add((plat, key))
    for run in registry.get("runs", []):
        for item in run.get("syndications", []):
            if item.get("status") == "success":
                plat = item.get("platform", "").lower()
                c_url = item.get("canonical_url", "").strip().lower()
                title = item.get("title", "").strip().lower()
                if plat and c_url:
                    published.add((plat, c_url))
                elif plat and title:
                    published.add((plat, title))
    return published


def run_article_and_link_pipeline(dry_run: bool = False) -> Dict[str, Any]:
    """
    Master coordinator: runs IndexNow, search engine pings, Dev.to/Medium syndication,
    and records results in submission_registry.json with deduplication.
    """
    start_time = datetime.now(timezone.utc).isoformat()
    registry = load_submission_registry()
    published_targets = get_published_targets(registry)

    urls = parse_sitemap_urls()
    print(f"[*] Ingested {len(urls)} URLs from sitemap for search engine indexing.")

    # 1. Submit to IndexNow (Bing, Yandex, Naver, Seznam)
    print("[*] Submitting URLs to IndexNow protocol...")
    indexnow_res = submit_to_indexnow(urls, dry_run=dry_run)
    print(f"    -> IndexNow Status: {indexnow_res.get('status')} (Code: {indexnow_res.get('status_code')})")

    # 2. Ping Search Engines
    print("[*] Sitemap discovery uses robots.txt and webmaster tools; legacy pings are retired.")
    ping_res = ping_search_engines(dry_run=dry_run)
    for name, stat in ping_res.items():
        print(f"    -> {name.capitalize()}: {stat.get('status')} ({stat.get('status_code', 'N/A')})")

    # 3. Read syndication articles with deduplication
    syndication_results = []
    if SYNDICATE_DIR.exists():
        for md_file in sorted(SYNDICATE_DIR.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            meta = parse_markdown_metadata(content)
            platform = meta.get("platform", "").lower()
            canon = meta.get("canonical_url", "").strip().lower()
            title = meta.get("title", "").strip().lower()

            target_plat = "dev.to" if (platform == "dev_to" or "dev_to" in md_file.name) else ("medium" if (platform == "medium" or "medium" in md_file.name) else platform)

            if not dry_run and ((target_plat, canon) in published_targets or (target_plat, title) in published_targets):
                syndication_results.append({
                    "platform": target_plat,
                    "title": meta.get("title", ""),
                    "canonical_url": meta.get("canonical_url", ""),
                    "status": "already_published",
                    "note": "Skipped submission to prevent duplicate publication on this platform."
                })
                continue

            if platform == "dev_to" or "dev_to" in md_file.name:
                dev_res = submit_dev_to_article(meta, dry_run=dry_run)
                syndication_results.append(dev_res)
            elif platform == "medium" or "medium" in md_file.name:
                med_res = submit_medium_article(meta, dry_run=dry_run)
                syndication_results.append(med_res)

    print(f"[*] Processed {len(syndication_results)} platform syndication targets.")

    # 4. Optional Webhook dispatch
    webhook_res = dispatch_webhook_syndication(syndication_results, dry_run=dry_run)

    # 5. Record run in persistent registry
    run_entry = {
        "timestamp": start_time,
        "mode": "dry_run" if dry_run else "live",
        "urls_submitted_count": min(len(urls), 10000) if not dry_run and indexnow_res.get("status") == "success" else 0,
        "urls_indexed_count": None,
        "indexnow": indexnow_res,
        "search_engine_pings": ping_res,
        "syndications": syndication_results,
        "webhook": webhook_res
    }
    registry["runs"].append(run_entry)
    registry["last_run_timestamp"] = start_time
    registry["total_submissions"] = registry.get("total_submissions", 0) + run_entry["urls_submitted_count"]
    # Update persistent published_articles list for newly successful publications
    published_list = registry.setdefault("published_articles", [])
    for r in syndication_results:
        if r.get("status") == "success":
            published_list.append({
                "platform": r.get("platform", ""),
                "title": r.get("title", ""),
                "canonical_url": r.get("canonical_url", ""),
                "published_at": start_time,
                "url": r.get("url", "")
            })
    # Retain last 30 runs to avoid file bloat
    registry["runs"] = registry["runs"][-30:]
    if not dry_run:
        save_submission_registry(registry)

    summary = {
        "timestamp": start_time,
        "urls_indexed": None,
        "urls_submitted": run_entry["urls_submitted_count"],
        "indexnow_status": indexnow_res.get("status"),
        "search_engine_pings": {k: v.get("status") for k, v in ping_res.items()},
        "syndicated_articles_count": sum(r.get("status") == "success" for r in syndication_results),
        "articles_attempted": len(syndication_results),
        "unconfigured_channels": sorted({r["platform"] for r in syndication_results if r.get("status", "").startswith("simulated_no_")}),
        "registry_saved": str(REGISTRY_PATH) if not dry_run else None
    }
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Surplus Docket Autonomous Article Submitter & Indexer")
    parser.add_argument("--dry-run", action="store_true", help="Run in simulation mode without network side effects")
    args = parser.parse_args()

    print("======================================================================")
    print(" 🚀 SURPLUS DOCKET — AUTONOMOUS ARTICLE SUBMISSION & INDEXING ENGINE")
    print("======================================================================")
    result = run_article_and_link_pipeline(dry_run=args.dry_run)
    print("\n✅ Execution Summary:")
    print(json.dumps(result, indent=2))
    if result["unconfigured_channels"]:
        print("::warning title=Syndication not configured::" + ", ".join(result["unconfigured_channels"]) + " have no publishing credentials; generated drafts are not published backlinks.")
    if not args.dry_run and result["indexnow_status"] != "success":
        raise SystemExit(1)
