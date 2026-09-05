#!/usr/bin/env python3
"""
Surplus Docket — Subscriber Lifecycle & Intake Manager
======================================================
CLI and programmatic interface to add, list, update, and deactivate
active subscribers in portal/subscribers.json for daily 7:00 AM dispatch.
"""

import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SUBSCRIBERS_FILE = BASE_DIR / "portal" / "subscribers.json"

DEFAULT_JURISDICTIONS = ["FL", "TX", "GA", "NC", "TN", "CA"]
DEFAULT_FORMATS = ["CSV", "Excel"]


def load_subscribers(filepath=SUBSCRIBERS_FILE):
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_subscribers(subscribers, filepath=SUBSCRIBERS_FILE):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(subscribers, f, indent=2)


def add_subscriber(email, name="Counsel", firm="Legal Practice", tier="Core Plan (7-Day Evaluation)",
                   jurisdictions=None, delivery_format=None, filepath=SUBSCRIBERS_FILE):
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError(f"Invalid email address: {email}")

    subscribers = load_subscribers(filepath)
    
    # Check if subscriber already exists
    for sub in subscribers:
        if sub.get("email", "").strip().lower() == email:
            sub["status"] = "ACTIVE"
            sub["name"] = name
            sub["firm"] = firm
            sub["tier"] = tier
            sub["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_subscribers(subscribers, filepath)
            return sub, False  # updated, not created new

    # Generate unique ID
    sub_id = f"SUB-{datetime.now().strftime('%Y%m%d')}-{len(subscribers) + 1:03d}"
    new_sub = {
        "id": sub_id,
        "email": email,
        "name": name,
        "firm": firm,
        "tier": tier,
        "jurisdictions": jurisdictions or DEFAULT_JURISDICTIONS,
        "delivery_format": delivery_format or DEFAULT_FORMATS,
        "status": "ACTIVE",
        "subscribed_at": datetime.now(timezone.utc).isoformat()
    }
    subscribers.append(new_sub)
    save_subscribers(subscribers, filepath)
    return new_sub, True


def deactivate_subscriber(email, filepath=SUBSCRIBERS_FILE):
    email = email.strip().lower()
    subscribers = load_subscribers(filepath)
    found = False
    for sub in subscribers:
        if sub.get("email", "").strip().lower() == email:
            sub["status"] = "CANCELLED"
            sub["cancelled_at"] = datetime.now(timezone.utc).isoformat()
            found = True
            break
    if found:
        save_subscribers(subscribers, filepath)
    return found


def list_subscribers(status_filter=None, filepath=SUBSCRIBERS_FILE):
    subs = load_subscribers(filepath)
    if status_filter:
        subs = [s for s in subs if s.get("status", "").upper() == status_filter.upper()]
    return subs


def main():
    parser = argparse.ArgumentParser(description="Manage Surplus Docket active subscribers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Add command
    add_p = subparsers.add_parser("add", help="Add or reactivate a subscriber")
    add_p.add_argument("--email", required=True, help="Subscriber email address")
    add_p.add_argument("--name", default="Counsel", help="Attorney / Contact Name")
    add_p.add_argument("--firm", default="Legal Practice", help="Law firm or practice name")
    add_p.add_argument("--tier", default="Core Plan (7-Day Evaluation)", help="Subscription tier")

    # Deactivate command
    deact_p = subparsers.add_parser("deactivate", help="Deactivate a subscriber upon Stripe cancellation")
    deact_p.add_argument("--email", required=True, help="Subscriber email address to cancel")

    # List command
    list_p = subparsers.add_parser("list", help="List subscribers")
    list_p.add_argument("--status", choices=["ACTIVE", "CANCELLED", "ALL"], default="ALL", help="Filter by status")

    args = parser.parse_args()

    if args.command == "add":
        sub, is_new = add_subscriber(args.email, args.name, args.firm, args.tier)
        status_word = "Added new" if is_new else "Reactivated existing"
        print(f"✅ {status_word} subscriber {sub['id']}: {sub['name']} <{sub['email']}> ({sub['firm']}) — Tier: {sub['tier']}")

    elif args.command == "deactivate":
        success = deactivate_subscriber(args.email)
        if success:
            print(f"🛑 Deactivated subscriber: {args.email}")
        else:
            print(f"⚠️ Subscriber not found: {args.email}")

    elif args.command == "list":
        filter_status = None if args.status == "ALL" else args.status
        subs = list_subscribers(filter_status)
        print(f"📋 Found {len(subs)} subscriber(s):")
        for s in subs:
            status_icon = "🟢" if s.get("status") == "ACTIVE" else "🔴"
            print(f"  {status_icon} [{s.get('id')}] {s.get('name')} <{s.get('email')}> | {s.get('firm')} | Tier: {s.get('tier')} | Status: {s.get('status')}")


if __name__ == "__main__":
    main()
