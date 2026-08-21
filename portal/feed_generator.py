#!/usr/bin/env python3
"""
B2B Master Feed Generator & Export Portal
Processes multi-county feeds, formats high-value subscriber exports (CSV, Excel, JSON),
and calculates total deal equity volume.
"""

import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

from enrichment.processor import process_county_dataset

BASE_DIR = Path("/Users/davidmahler/revenue-engine")
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

def generate_b2b_exports():
    print("==================================================================")
    print(" 🚀 GENERATING B2B SURPLUS LEAD FEEDS (FLORIDA & TEXAS EXPANSION)")
    print("==================================================================")

    all_leads = []

    # 1. Process Florida Dataset
    fl_csv = DATA_DIR / "raw_florida_feed.csv"
    if fl_csv.exists():
        fl_raw = pd.read_csv(fl_csv).to_dict(orient="records")
        for r in fl_raw:
            county_meta = {"state": "FL", "county": r.get("COUNTY", "Orange"), "statute": "FL Statute § 197.582"}
            leads = process_county_dataset([r], county_meta)
            all_leads.extend(leads)

    # 2. Process Texas Dataset
    tx_csv = DATA_DIR / "raw_texas_feed.csv"
    if tx_csv.exists():
        tx_raw = pd.read_csv(tx_csv).to_dict(orient="records")
        for r in tx_raw:
            county_meta = {"state": "TX", "county": r.get("COUNTY", "Harris"), "statute": "TX Tax Code § 34.04"}
            leads = process_county_dataset([r], county_meta)
            all_leads.extend(leads)

    if not all_leads:
        print("[!] No records processed.")
        return

    # Sort all leads descending by surplus amount
    all_leads.sort(key=lambda x: x["Surplus_Balance_USD"], reverse=True)
    df_all = pd.DataFrame(all_leads)

    # Generate Exports
    master_csv = EXPORTS_DIR / "Master_Surplus_Lead_Feed.csv"
    master_xlsx = EXPORTS_DIR / "Master_Surplus_Lead_Feed.xlsx"
    master_json = EXPORTS_DIR / "Master_Surplus_Lead_Feed.json"

    df_all.to_csv(master_csv, index=False)
    df_all.to_excel(master_xlsx, index=False)
    
    with open(master_json, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_records": len(all_leads),
            "total_surplus_volume_usd": round(float(df_all["Surplus_Balance_USD"].sum()), 2),
            "total_finder_fees_available_usd": round(float(df_all["Est_Finder_Fee_USD"].sum()), 2),
            "data": all_leads
        }, f, indent=2)

    # State-specific exports
    df_fl = df_all[df_all["State"] == "FL"]
    df_tx = df_all[df_all["State"] == "TX"]

    df_fl.to_csv(EXPORTS_DIR / "Florida_Surplus_Feed.csv", index=False)
    df_fl.to_excel(EXPORTS_DIR / "Florida_Surplus_Feed.xlsx", index=False)

    df_tx.to_csv(EXPORTS_DIR / "Texas_Surplus_Feed.csv", index=False)
    df_tx.to_excel(EXPORTS_DIR / "Texas_Surplus_Feed.xlsx", index=False)

    total_surplus = df_all["Surplus_Balance_USD"].sum()
    total_fees = df_all["Est_Finder_Fee_USD"].sum()
    tier1_count = len(df_all[df_all["Opportunity_Tier"].str.contains("Tier 1")])

    print(f"\n✅ Total Verified Individual Leads: {len(all_leads)}")
    print(f"💰 Total Surplus Balance Monitored: ${total_surplus:,.2f}")
    print(f"💵 Total Statutory Finder Fees Available: ${total_fees:,.2f}")
    print(f"⭐ Tier 1 ($25k+ balance) Opportunities: {tier1_count}")
    print(f"\n📁 Generated Subscriber Delivery Files in: {EXPORTS_DIR}")
    print(f"   - {master_csv.name} (CSV for CRMs)")
    print(f"   - {master_xlsx.name} (Formatted Excel)")
    print(f"   - {master_json.name} (REST API / Webhook delivery)")

if __name__ == "__main__":
    generate_b2b_exports()
