#!/usr/bin/env python3
"""
Surplus Docket — Sentinel 7:00 AM EST Morning Court Feed Autonomous Failover Check
Checks if morning feed for today has already been dispatched.
If outside failover window or already dispatched, logs status and exits 0.
If within window and not yet dispatched, executes portal/dispatch_morning_feed.py.
"""
import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def check_and_failover():
    try:
        from zoneinfo import ZoneInfo
        now_et = datetime.now(ZoneInfo('America/New_York'))
    except Exception:
        now_et = datetime.now()

    # Only run failover on weekdays (0=Mon, 4=Fri) between 5:30 AM and 11:00 AM EST
    in_window = (now_et.weekday() < 5 and (
        (now_et.hour == 5 and now_et.minute >= 30) or
        (6 <= now_et.hour <= 10)
    ))

    if not in_window:
        print(f"ℹ️ Sentinel Failover Check: Outside 5:30-11:00 AM EST dispatch failover window ({now_et.strftime('%A %I:%M %p EST')}).")
        return 0

    date_key = now_et.strftime('%Y-%m-%d')
    log_file = BASE_DIR / 'portal' / 'daily_dispatch_log.json'
    dispatched = False
    if log_file.exists():
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                d = json.load(f)
                if d.get('last_dispatched_date') == date_key and d.get('status') == 'SUCCESS':
                    dispatched = True
        except Exception:
            pass

    if not dispatched:
        print(f"🚨 Sentinel Failover: Morning feed not dispatched for {date_key} by {now_et.strftime('%I:%M %p EST')}. Triggering autonomous dispatch...")
        feed_script = BASE_DIR / 'portal' / 'dispatch_morning_feed.py'
        res = subprocess.run([sys.executable, str(feed_script), '--send'], check=True)
        return res.returncode
    else:
        print(f"✅ Sentinel Failover Check: Morning feed already successfully dispatched for {date_key}.")
        return 0


if __name__ == '__main__':
    sys.exit(check_and_failover())
