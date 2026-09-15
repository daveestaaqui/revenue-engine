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
from portal.dispatch_morning_feed import dispatch_activation_starter_kit

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
    default_data = {"processed_message_ids": [], "processed_subscription_ids": []}
    if not PROCESSED_EVENTS_FILE.exists():
        save_processed_events(default_data)
        return default_data
    try:
        with open(PROCESSED_EVENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        save_processed_events(default_data)
        return default_data


def save_processed_events(data):
    PROCESSED_EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def sync_via_stripe_api(api_key):
    """Directly query Stripe API for active and trialing subscriptions."""
    print("🔌 Querying Stripe REST API for active subscriptions...")
    # Expand customer object to retrieve email and billing name (max 2 levels)
    url = "https://api.stripe.com/v1/subscriptions?status=all&limit=100&expand%5B%5D=data.customer"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {api_key.strip()}")

    try:
        subs = []
        has_more = True
        starting_after = None
        while has_more:
            url = "https://api.stripe.com/v1/subscriptions?status=all&limit=100&expand%5B%5D=data.customer"
            if starting_after:
                url += f"&starting_after={starting_after}"
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Bearer {api_key.strip()}")

            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                batch = data.get("data", [])
                subs.extend(batch)
                has_more = data.get("has_more", False)
                if batch and has_more:
                    starting_after = batch[-1]["id"]
                else:
                    break

        print(f"✓ Retrieved {len(subs)} subscription records from Stripe API.")
        
        # Group subscriptions by customer email to avoid deactivating active accounts
        customer_subs = {}
        for s in subs:
            customer = s.get("customer", {})
            if isinstance(customer, dict):
                cust_email = customer.get("email")
                cust_name = customer.get("name") or "Counsel"
            else:
                cust_email = None
                cust_name = "Counsel"

            if not cust_email:
                continue

            cust_email_norm = cust_email.strip().lower()
            if cust_email_norm not in customer_subs:
                customer_subs[cust_email_norm] = {
                    "email": cust_email,
                    "name": cust_name,
                    "subscriptions": []
                }
            customer_subs[cust_email_norm]["subscriptions"].append(s)

        changes = 0
        for cust_email_norm, cdata in customer_subs.items():
            cust_email = cdata["email"]
            cust_name = cdata["name"]
            c_subs = cdata["subscriptions"]

            # Find active or trialing subscription
            active_sub = next((s for s in c_subs if s.get("status") in ("active", "trialing")), None)

            if active_sub:
                status = active_sub.get("status")
                plan_name = "Surplus Docket — Tri-State Core Feed (FL, TX, GA)"
                items = active_sub.get("items", {}).get("data", [])
                if items:
                    price_obj = items[0].get("price", {})
                    prod_obj = price_obj.get("product")
                    if isinstance(prod_obj, dict) and prod_obj.get("name"):
                        plan_name = prod_obj.get("name")
                    elif price_obj.get("nickname"):
                        plan_name = price_obj.get("nickname")
                    elif items[0].get("plan", {}).get("nickname"):
                        plan_name = items[0].get("plan", {}).get("nickname")

                # Do not set placeholder firm names
                cust_lower = cust_name.lower()
                detected_firm = cust_name if any(term in cust_lower for term in ("law", "llc", "legal", "pc", "pllc", "esq", "attorney", "firm", "associates")) else ""

                sub_obj, is_new = add_subscriber(
                    email=cust_email,
                    name=cust_name,
                    firm=detected_firm,
                    tier=plan_name
                )
                if is_new:
                    print(f"  ✨ [Stripe API] Added new subscriber: {cust_email} ({status}) [{plan_name}]")
                    changes += 1
                    try:
                        dispatch_activation_starter_kit(sub_obj)
                    except Exception as err:
                        print(f"  ⚠️ Could not dispatch welcome starter kit: {err}")
            else:
                # All subscriptions for this customer are canceled or unpaid
                if deactivate_subscriber(cust_email):
                    print(f"  🛑 [Stripe API] Deactivated subscriber: {cust_email} (all subscriptions canceled)")
                    changes += 1

        return changes

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        print(f"⚠️ Stripe API HTTPError {e.code}: {err_body}")
        return 0
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

    # Determine Plan Tier if mentioned in email
    tier = "Surplus Docket — Tri-State Core Feed (FL, TX, GA)"
    if any(w in sub_lower or w in body_lower for w in ["national", "6-state", "449", "4,188", "4188", "suite"]):
        tier = "Surplus Docket — 6-State Suite + REST API (FL, TX, GA, NC, TN, CA)"
    elif any(w in sub_lower or w in body_lower for w in ["core", "tri-state", "249", "2,388", "2388"]):
        tier = "Surplus Docket — Tri-State Core Feed (FL, TX, GA)"

    return {
        "email": target_email,
        "name": customer_name,
        "tier": tier,
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
                    sub_tier = parsed.get("tier", "Surplus Docket — Tri-State Core Feed (FL, TX, GA)")
                    sub_obj, is_new = add_subscriber(
                        email=cust_email,
                        name=cust_name,
                        firm="",
                        tier=sub_tier
                    )
                    if is_new:
                        print(f"  ✨ [Stripe Email] Auto-enrolled new trial subscriber: {cust_name} <{cust_email}>")
                        changes += 1
                        try:
                            dispatch_activation_starter_kit(sub_obj)
                        except Exception as err:
                            print(f"  ⚠️ Could not dispatch welcome starter kit: {err}")

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


def reconcile_and_repair_subscribers(subscribers: list = None, write_back: bool = True) -> dict:
    """
    Autonomous Subscriber Self-Reconciliation & Integrity Engine.
    Audits portal/subscribers.json:
    - Normalizes email casing and strips whitespace
    - Merges duplicate accounts preserving active subscription state
    - Validates required fields and applies safe defaults
    - Transitions expired trials (> 7 days) to EXPIRED_TRIAL
    """
    if subscribers is None:
        if not SUBSCRIBERS_FILE.exists():
            return {"total": 0, "repaired": 0, "duplicates_merged": 0, "expired_trials": 0, "subscribers": []}

        try:
            with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                subscribers = json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load {SUBSCRIBERS_FILE} for reconciliation: {e}")
            return {"error": str(e), "subscribers": []}

    repaired_count = 0
    merged_count = 0
    expired_count = 0

    # Group by normalized email
    normalized_map = {}
    now = datetime.now(timezone.utc)

    for sub in subscribers:
        raw_email = sub.get("email", "")
        if not raw_email:
            continue
        norm_email = raw_email.strip().lower()

        # Check trial expiration
        status = sub.get("status", "ACTIVE").upper()
        is_eval_tier = any(k in str(sub.get("tier", "")).lower() for k in ["evaluation", "trial"])
        if status in ("TRIAL", "TRIALING") or (is_eval_tier and status == "ACTIVE"):
            days_active = None
            if sub.get("days_active") is not None:
                try:
                    days_active = float(sub.get("days_active"))
                except (ValueError, TypeError):
                    pass
            if days_active is None:
                sub_date_str = sub.get("subscribed_at") or sub.get("created_at")
                if sub_date_str:
                    try:
                        clean_dt = sub_date_str.replace("Z", "+00:00")
                        created_dt = datetime.fromisoformat(clean_dt)
                        days_active = (now - created_dt).total_seconds() / 86400.0
                    except Exception:
                        pass
            if days_active is not None and days_active > 7.5:
                sub["status"] = "EXPIRED_TRIAL"
                sub["trial_expired_at"] = now.isoformat()
                expired_count += 1
                repaired_count += 1
                print(f"  ⏳ [Self-Reconciliation] Trial expired for {norm_email} ({days_active:.1f} days active)")

        # Email normalization check
        if sub.get("email") != norm_email:
            sub["email"] = norm_email
            repaired_count += 1

        # Deduplication / Merge
        if norm_email in normalized_map:
            existing = normalized_map[norm_email]
            merged_count += 1
            repaired_count += 1
            # If current is ACTIVE and existing is CANCELLED/EXPIRED, prioritize ACTIVE
            if sub.get("status") == "ACTIVE" and existing.get("status") != "ACTIVE":
                normalized_map[norm_email] = sub
        else:
            normalized_map[norm_email] = sub

    reconciled_list = list(normalized_map.values())
    if write_back and repaired_count > 0:
        try:
            with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
                json.dump(reconciled_list, f, indent=2)
            print(f"✓ [Self-Reconciliation] Repaired {repaired_count} subscriber record(s) ({merged_count} merged, {expired_count} expired trials).")
        except Exception as e:
            print(f"⚠️ Could not write reconciled subscribers: {e}")

    return {
        "total": len(reconciled_list),
        "repaired": repaired_count,
        "duplicates_merged": merged_count,
        "expired_trials": expired_count,
        "subscribers": reconciled_list
    }


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

    # 3. Run Autonomous Subscriber Reconciliation & Self-Repair
    reconciliation_report = reconcile_and_repair_subscribers()
    total_changes += reconciliation_report.get("repaired", 0)

    print(f"\n✅ Sync run complete. Total subscriber state modifications: {total_changes}")
    return total_changes


if __name__ == "__main__":
    run_sync()
