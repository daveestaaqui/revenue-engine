#!/usr/bin/env python3
"""
B2B Data Feed Monetization & Automated Delivery Guide
Synchronizes and manages pricing tiers, Stripe checkout endpoints, customer portal,
and automated distribution configuration.
"""

import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "portal" / "monetization_config.json"

MONETIZATION_CONFIG = {
    "single_county_pilot": {
        "tier_id": "single_county_pilot",
        "title": "Single-County 14-Day Pilot Dossier",
        "jurisdictions": ["FL", "TX", "GA", "NC", "TN", "CA"],
        "price_usd": 49,
        "has_trial": False,
        "rest_api_enabled": False,
        "checkout_url": "https://buy.stripe.com/6oU5kDc0GgXN2Dz6K20ZW23",
        "features": [
            "Target single county of your choice (e.g. Palm Beach, Harris, Fulton, Los Angeles)",
            "14-Day verified court surplus docket dossier & export",
            "Full court petition & claim motion templates included",
            "100% money-back satisfaction guarantee"
        ]
    },
    "tri_state_core": {
        "tier_id": "tri_state_core",
        "title": "Tri-State Core Feed",
        "jurisdictions": ["FL", "TX", "GA"],
        "price_monthly_usd": 249,
        "price_annual_usd": 2490,
        "has_trial": True,
        "trial_days": 7,
        "rest_api_enabled": False,
        "checkout_monthly_url": "https://buy.stripe.com/4gM14n8yq9vl0vrb0i0ZW21",
        "checkout_annual_url": "https://buy.stripe.com/6oU6oHg0SgXNce9gkC0ZW1Z",
        "features": [
            "Florida (Fla. Stat. § 197.582), Texas (Tex. Tax Code § 34.04) & Georgia (O.C.G.A. § 48-4-5)",
            "Mon–Fri 7:00 AM ET CSV & Excel delivery",
            "100% Institutional lien & senior mortgage pre-scrubbing",
            "Multi-seat firm inbox delivery (up to 3 inboxes)"
        ]
    },
    "six_state_national": {
        "tier_id": "six_state_national",
        "title": "Six-State Feed + REST API",
        "jurisdictions": ["FL", "TX", "GA", "NC", "TN", "CA"],
        "price_monthly_usd": 449,
        "price_annual_usd": 4490,
        "has_trial": False,
        "trial_days": 0,
        "rest_api_enabled": True,
        "rate_limit_per_minute": 60,
        "monthly_request_quota": 50000,
        "checkout_monthly_url": "https://buy.stripe.com/28E14n4ia7nd91X1pI0ZW22",
        "checkout_annual_url": "https://buy.stripe.com/cNidR99Cu5f5ba5c4m0ZW20",
        "features": [
            "All 6 States: FL, TX, GA + NC, TN, CA",
            "Programmatic REST JSON API Endpoint Access",
            "Priority Tier 1 instant alerts",
            "Firm-wide multi-seat delivery (up to 5 inboxes)"
        ]
    },
    "stripe_customer_portal_url": "https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00"
}

def print_monetization_overview():
    print("==================================================================")
    print(" 💵 B2B DATA SUBSCRIPTION MODEL (ZERO-TOUCH RECURRING REVENUE)")
    print("==================================================================")
    print("Live Pricing & Integration Architecture:\n")
    
    tiers = {k: v for k, v in MONETIZATION_CONFIG.items() if isinstance(v, dict)}
    for key, p in tiers.items():
        print(f"📦 Product: {p['title']} [{p['tier_id']}]")
        if "price_monthly_usd" in p:
            print(f"   - Monthly: ${p['price_monthly_usd']}/mo (Checkout: {p.get('checkout_monthly_url')})")
            print(f"   - Annual:  ${p['price_annual_usd']}/yr (Checkout: {p.get('checkout_annual_url')})")
        else:
            print(f"   - One-time: ${p.get('price_usd', 49)} (Checkout: {p.get('checkout_url')})")
        print(f"   - Jurisdictions: {', '.join(p['jurisdictions'])}")
        print(f"   - Trial: {p.get('trial_days', 0)} days (Trial active: {p.get('has_trial', False)})")
        print(f"   - REST API: {'Enabled' if p['rest_api_enabled'] else 'Disabled'}")
        print(f"   - Features: {len(p['features'])} deliverables")
        print("-" * 65)

    print(f"🔗 Customer Billing Portal: {MONETIZATION_CONFIG.get('stripe_customer_portal_url')}")
    print("\n📈 Revenue Modeling:")
    print("   - 10 Tri-State Core subscribers @ $249/mo = $2,490 / month")
    print("   - 10 Six-State National subscribers @ $449/mo = $4,490 / month")
    print("   - Combined Annualized Run Rate (ARR): $83,760 / year\n")

    # Save configuration idempotently
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(MONETIZATION_CONFIG, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✅ Configuration synchronized to: {CONFIG_FILE}")

if __name__ == "__main__":
    print_monetization_overview()
