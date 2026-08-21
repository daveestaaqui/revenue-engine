#!/usr/bin/env python3
"""
Automated Expired Domain Valuation & Arbitrage Runner
Scans dropping domain lists, isolates high-resale opportunities, and formats Afternic auction listings.
"""

import os
import sys
import pandas as pd
from pathlib import Path

from scanners.valuation_model import score_domain

BASE_DIR = Path("/Users/davidmahler/revenue-engine/domain_arbitrage")
DATA_DIR = BASE_DIR / "data"
LISTINGS_DIR = BASE_DIR / "listings"
LISTINGS_DIR.mkdir(parents=True, exist_ok=True)

def run_pipeline(input_file=None):
    if not input_file:
        input_file = DATA_DIR / "sample_dropping_domains.txt"

    print("==================================================================")
    print(" 🌐 DOMAIN ARBITRAGE & DROP-CATCHING ENGINE (AFTERNIC / GODADDY)")
    print("==================================================================")

    with open(input_file, "r") as f:
        domains = [line.strip() for line in f if line.strip()]

    print(f"[*] Ingested Dropping Domains: {len(domains)}")
    
    scored_domains = []
    for d in domains:
        scored = score_domain(d)
        if scored:
            scored_domains.append(scored)

    # Sort by score descending
    scored_domains.sort(key=lambda x: x["score"], reverse=True)

    df = pd.DataFrame(scored_domains)
    output_csv = LISTINGS_DIR / "High_Value_Drop_Opportunities.csv"
    df.to_csv(output_csv, index=False)

    print(f"\n✅ Qualified High-Liquidity Flips Found: {len(scored_domains)}")
    print("-" * 65)
    
    total_estimated_profit = 0.0
    for idx, item in enumerate(scored_domains, 1):
        total_estimated_profit += item["estimated_net_profit_usd"]
        print(f"[{idx}] {item['domain']}")
        print(f"    - Length: {item['length']} chars | TLD: .{item['tld']} | Score: {item['score']}")
        print(f"    - Keywords: {', '.join(item['keywords_matched'])}")
        print(f"    - Buy Wholesale:   ${item['wholesale_cost_usd']:.2f}")
        print(f"    - Suggested BIN:   ${item['suggested_buy_it_now_usd']:.2f}")
        print(f"    - Est. Net Profit: ${item['estimated_net_profit_usd']:.2f}")
        print("-" * 65)

    print(f"\n💰 Total Potential Net Resale Profit in Batch: ${total_estimated_profit:,.2f}")
    print(f"📁 Listing file generated at: {output_csv}")
    print("\n💡 Zero-Touch Execution Flow:")
    print("   1. Register top picks at wholesale ($10.50) via Namecheap/Cloudflare API.")
    print("   2. Upload High_Value_Drop_Opportunities.csv to GoDaddy Afternic.")
    print("   3. When a buyer checks out on GoDaddy, Afternic auto-transfers the domain and deposits cash to your bank.")

if __name__ == "__main__":
    run_pipeline()
