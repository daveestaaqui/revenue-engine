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
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
SUBSCRIBERS_FILE = BASE_DIR / "portal" / "subscribers.json"

CORE_JURISDICTIONS = ["FL", "TX", "GA"]
NATIONAL_JURISDICTIONS = ["FL", "TX", "GA", "NC", "TN", "CA"]
DEFAULT_JURISDICTIONS = NATIONAL_JURISDICTIONS
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

    # Automatically keep site/api/v1/auth_registry.json synchronized when updating production subscribers
    if Path(filepath).resolve() == SUBSCRIBERS_FILE.resolve():
        try:
            from portal.vault_security import generate_vault_and_auth_registry, AUTH_REGISTRY_FILE
            master_json = BASE_DIR / "exports" / "Master_Surplus_Lead_Feed.json"
            leads = []
            if master_json.exists():
                with open(master_json, "r", encoding="utf-8") as mj:
                    data = json.load(mj)
                    leads = data.get("data", [])
            _, auth_registry = generate_vault_and_auth_registry(leads, subscribers)
            AUTH_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(AUTH_REGISTRY_FILE, "w", encoding="utf-8") as af:
                json.dump(auth_registry, af, indent=2)
        except Exception:
            pass


def get_jurisdictions_for_tier(tier):
    tier_lower = tier.lower()
    if any(k in tier_lower for k in ("national", "6-state", "master", "api", "enterprise")):
        return NATIONAL_JURISDICTIONS.copy()
    return CORE_JURISDICTIONS.copy()


def add_subscriber(email, name="Counsel", firm="", tier="Core Plan (7-Day Evaluation)",
                   jurisdictions=None, delivery_format=None, status="ACTIVE", filepath=SUBSCRIBERS_FILE):
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError(f"Invalid email address: {email}")

    subscribers = load_subscribers(filepath)
    
    assigned_jurisdictions = jurisdictions or get_jurisdictions_for_tier(tier)

    # Check if subscriber already exists
    for sub in subscribers:
        if sub.get("email", "").strip().lower() == email:
            sub["status"] = status or "ACTIVE"
            sub["name"] = name
            sub["firm"] = firm
            sub["tier"] = tier
            sub["jurisdictions"] = assigned_jurisdictions
            sub["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_subscribers(subscribers, filepath)
            return sub, False  # updated, not created new

    # Generate collision-safe unique ID
    existing_ids = {s.get("id", "") for s in subscribers}
    seq = len(subscribers) + 1
    while True:
        sub_id = f"SUB-{datetime.now().strftime('%Y%m%d')}-{seq:03d}"
        if sub_id not in existing_ids:
            break
        seq += 1

    new_sub = {
        "id": sub_id,
        "email": email,
        "name": name,
        "firm": firm,
        "tier": tier,
        "jurisdictions": assigned_jurisdictions,
        "delivery_format": delivery_format or DEFAULT_FORMATS,
        "status": status or "ACTIVE",
        "subscribed_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
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
    add_p.add_argument("--firm", default="", help="Law firm or practice name")
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
