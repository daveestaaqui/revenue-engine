#!/usr/bin/env python3
"""
OpenSurplus CLI & Python SDK (v1.2.0)
=====================================
Zero-dependency Python library and CLI for computing statutory surplus claim
deadlines, fee caps, and court registry venues across FL, TX, CA, GA, NC, and TN.

Documentation & Web SDK: https://surplusdocket.com/sdk/
Public Records Feeds:    https://surplusdocket.com/
License: MIT
"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

JURISDICTIONS: Dict[str, Dict[str, Any]] = {
    "FL": {
        "name": "Florida",
        "statute": "Fla. Stat. § 197.582",
        "trigger_event": "Clerk Notice of Surplus Date",
        "window_days": 120,
        "fee_cap_pct": 0.20,
        "venue": "Clerk of the Circuit Court (Tax Deed Division)",
        "feed_url": "https://surplusdocket.com/florida-tax-deed-surplus.html",
    },
    "TX": {
        "name": "Texas",
        "statute": "Tex. Tax Code § 34.04",
        "trigger_event": "Sheriff / Constable Tax Sale Date",
        "window_days": 730,
        "fee_cap_pct": 0.25,
        "venue": "District Court Registry (Original Tax Suit Cause No.)",
        "feed_url": "https://surplusdocket.com/texas-tax-sale-excess-proceeds.html",
    },
    "CA": {
        "name": "California",
        "statute": "Cal. Rev. & Tax Code § 4675",
        "trigger_event": "Tax Deed to Purchaser Recordation Date",
        "window_days": 365,
        "fee_cap_pct": 0.20,
        "venue": "County Auditor-Controller / Board of Supervisors",
        "feed_url": "https://surplusdocket.com/california-tax-defaulted-excess-proceeds.html",
    },
    "GA": {
        "name": "Georgia",
        "statute": "O.C.G.A. § 48-4-5",
        "trigger_event": "Tax Commissioner / Sheriff Sale Date",
        "window_days": 1825,
        "fee_cap_pct": 0.20,
        "venue": "County Tax Commissioner / Superior Court Registry",
        "feed_url": "https://surplusdocket.com/georgia-tax-sale-excess-funds.html",
    },
    "NC": {
        "name": "North Carolina",
        "statute": "N.C.G.S. § 105-374",
        "trigger_event": "Confirmation of Foreclosure Sale Date",
        "window_days": 730,
        "fee_cap_pct": 0.20,
        "venue": "Clerk of Superior Court Special Proceedings",
        "feed_url": "https://surplusdocket.com/north-carolina-tax-foreclosure-surplus.html",
    },
    "TN": {
        "name": "Tennessee",
        "statute": "T.C.A. § 67-5-2501",
        "trigger_event": "Chancery Court Confirmation of Sale Date",
        "window_days": 365,
        "fee_cap_pct": 0.20,
        "venue": "Chancery Court Clerk and Master",
        "feed_url": "https://surplusdocket.com/tennessee-tax-sale-excess-proceeds.html",
    },
}


def calculate_statutory_deadline(state: str, event_date: str, balance_usd: float) -> Dict[str, Any]:
    """Computes deterministic statutory claim window and fee benchmark."""
    code = state.strip().upper()
    if code not in JURISDICTIONS:
        raise ValueError(f"Unsupported state '{code}'. Supported: {', '.join(JURISDICTIONS.keys())}")
    rule = JURISDICTIONS[code]
    dt = datetime.strptime(event_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    deadline = dt + timedelta(days=rule["window_days"])
    now = datetime.now(timezone.utc)
    days_remaining = (deadline - now).days

    return {
        "state": code,
        "jurisdiction": rule["name"],
        "governing_statute": rule["statute"],
        "trigger_event": rule["trigger_event"],
        "trigger_date": dt.strftime("%Y-%m-%d"),
        "statutory_deadline_date": deadline.strftime("%Y-%m-%d"),
        "days_remaining": days_remaining,
        "status": "OPEN_WINDOW" if days_remaining > 0 else "EXPIRED_OR_ESCHEATED",
        "surplus_balance_usd": round(float(balance_usd), 2),
        "statutory_fee_benchmark_usd": round(float(balance_usd) * rule["fee_cap_pct"], 2),
        "fee_benchmark_pct": int(rule["fee_cap_pct"] * 100),
        "filing_venue": rule["venue"],
        "verification_feed_url": rule["feed_url"],
        "sdk_source": "https://surplusdocket.com/sdk/",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenSurplus Statutory Deadline & Fee Calculator CLI")
    parser.add_argument("--state", required=True, choices=list(JURISDICTIONS.keys()), help="2-letter state code")
    parser.add_argument("--date", "--sale-date", dest="date", required=True, help="Trigger event date (YYYY-MM-DD)")
    parser.add_argument("--balance", "--surplus", dest="balance", type=float, default=100000.0, help="Surplus balance in USD")
    parser.add_argument("--claim-type", default="tax_deed", choices=["tax_deed", "judicial"], help="Claim type (tax_deed or judicial)")
    parser.add_argument("--json", action="store_true", help="Output formatted JSON")
    args = parser.parse_args()
    result = calculate_statutory_deadline(args.state, args.date, args.balance)
    result["claim_type"] = args.claim_type
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
