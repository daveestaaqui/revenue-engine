#!/usr/bin/env python3
"""
Surplus Docket — External Dispatch Trigger
==========================================
This script provides a lightweight HTTP-callable mechanism for external
cron services (cron-job.org, easycron.com, etc.) to trigger the morning
feed dispatch via GitHub Actions repository_dispatch.

Usage:
    # Direct trigger via GitHub CLI:
    gh api repos/daveestaaqui/revenue-engine/dispatches -f event_type=dispatch_morning_feed

    # Or via curl with a Personal Access Token:
    curl -X POST https://api.github.com/repos/daveestaaqui/revenue-engine/dispatches \
      -H "Authorization: token YOUR_PAT" \
      -H "Accept: application/vnd.github.v3+json" \
      -d '{"event_type": "dispatch_morning_feed"}'

The dispatch_morning_feed.py script's idempotency guard ensures no
duplicate emails are ever sent, even if triggered multiple times.
"""
import os
import sys
import json
from pathlib import Path

try:
    import urllib.request
    import urllib.error
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
REPO = os.getenv("GITHUB_REPO", "daveestaaqui/revenue-engine")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


def trigger_dispatch(event_type="dispatch_morning_feed"):
    """Trigger a GitHub Actions repository_dispatch event."""
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN environment variable required.")
        return False

    url = f"https://api.github.com/repos/{REPO}/dispatches"
    payload = json.dumps({"event_type": event_type}).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"✅ Repository dispatch triggered: {event_type} (HTTP {resp.status})")
            return True
    except urllib.error.HTTPError as e:
        print(f"❌ GitHub API error: HTTP {e.code} — {e.read().decode()}")
        return False
    except Exception as e:
        print(f"❌ Error triggering dispatch: {e}")
        return False


def check_and_trigger():
    """Check if morning feed was already dispatched; if not, trigger it."""
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        now_et = datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        now_et = datetime.now()

    # Only on weekdays
    if now_et.weekday() >= 5:
        print(f"ℹ️ Weekend ({now_et.strftime('%A')}). No morning feed to dispatch.")
        return True

    date_key = now_et.strftime("%Y-%m-%d")
    log_file = BASE_DIR / "portal" / "daily_dispatch_log.json"

    if log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                log_data = json.load(f)
            if log_data.get("last_dispatched_date") == date_key and log_data.get("status") == "SUCCESS":
                print(f"✅ Morning feed already dispatched for {date_key}. No action needed.")
                return True
        except Exception:
            pass

    print(f"🚨 Morning feed NOT yet dispatched for {date_key}. Triggering GitHub Actions...")
    return trigger_dispatch()


if __name__ == "__main__":
    sys.exit(0 if check_and_trigger() else 1)
