#!/usr/bin/env python3
"""
Surplus Docket — Autonomous Stripe Subscriber Ingestion & Sync Engine
======================================================================
100% automated subscriber intake for new 7-day trials and subscriptions.
1. Direct Stripe REST API synchronization (if STRIPE_API_KEY is configured).
2. Autonomous IMAP Sentinel parsing Stripe notification emails received at
   GMAIL_USER (zero extra configuration needed, uses GMAIL_APP_PASS).
3. Automatically writes new active trials to portal/subscribers.json so they
   receive the daily 7:00 AM EST morning court feed immediately.
4. Automatically marks cancelled trials/subscriptions as CANCELLED.
"""

import os
import sys
import json
import re
import imaplib
import email
from email.header import decode_header
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from portal.manage_subscribers import add_subscriber, deactivate_subscriber, load_subscribers

# Paths
PORTAL_DIR = BASE_DIR / "portal"
PROCESSED_EVENTS_FILE = PORTAL_DIR / "processed_stripe_events.json"
SUBSCRIBERS_FILE = PORTAL_DIR / "subscribers.json"

# Credentials
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    try:
        with open(ENV_FILE, "r") as ef:
            for line in ef:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))
    except Exception:
        pass

GMAIL_USER = os.getenv("GMAIL_USER", "sandwichfitness@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")


def load_processed_events():
    if not PROCESSED_EVENTS_FILE.exists():
        return {"processed_message_ids": [], "processed_subscription_ids": []}
    try:
        with open(PROCESSED_EVENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"processed_message_ids": [], "processed_subscription_ids": []}


def save_processed_events(data):
    PROCESSED_EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def sync_via_stripe_api(api_key):
    """Directly query Stripe API for active and trialing subscriptions."""
    print("🔌 Querying Stripe REST API for active subscriptions...")
    url = "https://api.stripe.com/v1/subscriptions?status=all&limit=100&expand[]=data.customer"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            subs = data.get("data", [])
            print(f"✓ Retrieved {len(subs)} subscription records from Stripe API.")
            
            changes = 0
            for s in subs:
                status = s.get("status")
                customer = s.get("customer", {})
                if isinstance(customer, str):
                    # Customer object wasn't expanded
                    cust_email = None
                    cust_name = "Counsel"
                else:
                    cust_email = customer.get("email")
                    cust_name = customer.get("name") or "Counsel"

                if not cust_email:
                    continue

                if status in ("active", "trialing"):
                    plan_name = "Core Plan (7-Day Evaluation)"
                    items = s.get("items", {}).get("data", [])
                    if items:
                        plan_desc = items[0].get("price", {}).get("nickname") or items[0].get("plan", {}).get("nickname")
                        if plan_desc:
                            plan_name = plan_desc

                    sub_obj, is_new = add_subscriber(
                        email=cust_email,
                        name=cust_name,
                        firm=cust_name if "law" in cust_name.lower() or "llc" in cust_name.lower() else "Legal Practice",
                        tier=plan_name
                    )
                    if is_new:
                        print(f"  ✨ [Stripe API] Added new subscriber: {cust_email} ({status})")
                        changes += 1
                elif status in ("canceled", "unpaid"):
                    if deactivate_subscriber(cust_email):
                        print(f"  🛑 [Stripe API] Deactivated subscriber: {cust_email} ({status})")
                        changes += 1

            return changes

    except Exception as e:
        print(f"⚠️ Stripe API Error: {e}")
        return 0


def clean_header_text(header_val):
    if not header_val:
        return ""
    decoded_parts = decode_header(header_val)
    text = ""
    for part, enc in decoded_parts:
        if isinstance(part, bytes):
            text += part.decode(enc or "utf-8", errors="ignore")
        else:
            text += str(part)
    return text.strip()


def extract_email_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition"))
            if ctype in ("text/plain", "text/html") and "attachment" not in cdispo:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode("utf-8", errors="ignore") + "\n"
                except Exception:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="ignore")
        except Exception:
            pass
    return body


def parse_stripe_email(subject, body):
    """
    Parses customer email, customer name, and action from Stripe notification emails.
    """
    sub_lower = subject.lower()
    body_lower = body.lower()

    # Determine event type
    is_cancellation = any(w in sub_lower or w in body_lower for w in ["canceled", "cancelled", "subscription ended"])
    is_activation = any(w in sub_lower or w in body_lower for w in ["new subscription", "trial started", "started a trial", "payment received", "new customer", "payment succeeded"])

    if not is_cancellation and not is_activation:
        return None

    # Search for customer email address
    # Common Stripe email patterns:
    # "Customer: name@domain.com"
    # "Email: name@domain.com"
    # "Account: name@domain.com"
    email_matches = re.findall(r'(?:Customer|Email|Account|User|Billed to)[\s\:\-]*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', body, re.IGNORECASE)
    
    target_email = None
    if email_matches:
        for em in email_matches:
            # Filter out stripe internal addresses
            if not any(ign in em.lower() for ign in ["stripe.com", "sandwichfitness@gmail.com", "surplusdocket.com"]):
                target_email = em.strip().lower()
                break

    if not target_email:
        # Fallback: scan all emails in body
        all_emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', body)
        for em in all_emails:
            if not any(ign in em.lower() for ign in ["stripe.com", "sandwichfitness@gmail.com", "surplusdocket.com", "google.com"]):
                target_email = em.strip().lower()
                break

    if not target_email:
        return None

    # Extract Name if present
    name_match = re.search(r'(?:Customer Name|Name)[\s\:\-]+([A-Za-z0-9\s,\.\'\-]+?)(?:\n|\r|<br|$)', body, re.IGNORECASE)
    customer_name = name_match.group(1).strip() if name_match else "Counsel"

    return {
        "email": target_email,
        "name": customer_name,
        "is_cancellation": is_cancellation
    }


def sync_via_imap(user, password):
    """
    Connects to Gmail via IMAP and scans for new Stripe notification emails.
    """
    if not password:
        print("ℹ️ GMAIL_APP_PASS not configured. Skipping IMAP Stripe sync.")
        return 0

    print(f"📬 Scanning Gmail ({user}) via IMAP for incoming Stripe customer notifications...")
    events_data = load_processed_events()
    processed_ids = set(events_data.get("processed_message_ids", []))

    changes = 0
    mail = None
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user, password)
        mail.select("INBOX", readonly=True)

        # Search for messages from stripe.com
        status, data = mail.search(None, 'FROM', 'stripe.com')
        if status != "OK" or not data or not data[0]:
            print("✓ No unhandled Stripe emails found in INBOX.")
            return 0

        msg_nums = data[0].split()
        print(f"✓ Found {len(msg_nums)} Stripe notification emails to evaluate.")

        for num in msg_nums:
            status, msg_data = mail.fetch(num, "(RFC822.HEADER RFC822.TEXT)")
            if status != "OK" or not msg_data:
                continue

            raw_email = b""
            for part in msg_data:
                if isinstance(part, tuple) and len(part) > 1:
                    raw_email += part[1]

            msg = email.message_from_bytes(raw_email)
            msg_id = msg.get("Message-ID", "").strip() or str(num.decode())

            if msg_id in processed_ids:
                continue

            subject = clean_header_text(msg.get("Subject", ""))
            body = extract_email_body(msg)

            parsed = parse_stripe_email(subject, body)
            if parsed:
                cust_email = parsed["email"]
                cust_name = parsed["name"]
                if parsed["is_cancellation"]:
                    if deactivate_subscriber(cust_email):
                        print(f"  🛑 [Stripe Email] Deactivated cancelled subscriber: {cust_email}")
                        changes += 1
                else:
                    sub_obj, is_new = add_subscriber(
                        email=cust_email,
                        name=cust_name,
                        firm="Legal Practice",
                        tier="Core Plan (7-Day Evaluation)"
                    )
                    if is_new:
                        print(f"  ✨ [Stripe Email] Auto-enrolled new trial subscriber: {cust_name} <{cust_email}>")
                        changes += 1

            processed_ids.add(msg_id)

        events_data["processed_message_ids"] = list(processed_ids)[-500:]  # Keep last 500
        save_processed_events(events_data)
        return changes

    except Exception as e:
        print(f"⚠️ IMAP Stripe sync error: {e}")
        return 0
    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass


def run_sync():
    print("=" * 70)
    print(" ⚡ SURPLUS DOCKET — AUTONOMOUS STRIPE SUBSCRIBER SYNC ENGINE")
    print("=" * 70)

    total_changes = 0

    # 1. Try direct Stripe API if key is present
    if STRIPE_API_KEY:
        total_changes += sync_via_stripe_api(STRIPE_API_KEY)
    else:
        print("ℹ️ STRIPE_API_KEY not configured in env; falling back to automated IMAP Sentinel.")

    # 2. Scan via IMAP using GMAIL_APP_PASS
    total_changes += sync_via_imap(GMAIL_USER, GMAIL_APP_PASS)

    print(f"\n✅ Sync run complete. Total subscriber state modifications: {total_changes}")
    return total_changes


if __name__ == "__main__":
    run_sync()
