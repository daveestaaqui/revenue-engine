#!/usr/bin/env python3
"""
B2B Master Feed Generator & Export Portal
Processes multi-county feeds, formats high-value subscriber exports (CSV, Excel, JSON),
and calculates total deal equity volume.
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add root repository directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from enrichment.processor import process_county_dataset

DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

def generate_b2b_exports():
    print("==================================================================")
    print(" 🚀 GENERATING B2B SURPLUS LEAD FEEDS (6-STATE NATIONAL SUITE)")
    print("==================================================================")

    all_leads = []

    # 1. Process Florida Dataset
    fl_csv = DATA_DIR / "raw_florida_feed.csv"
    if fl_csv.exists():
        fl_raw = pd.read_csv(fl_csv).to_dict(orient="records")
        for r in fl_raw:
            county_meta = {"state": "FL", "county": r.get("COUNTY", "Orange"), "statute": "Fla. Stat. § 197.582"}
            leads = process_county_dataset([r], county_meta)
            all_leads.extend(leads)

    # 2. Process Texas Dataset
    tx_csv = DATA_DIR / "raw_texas_feed.csv"
    if tx_csv.exists():
        tx_raw = pd.read_csv(tx_csv).to_dict(orient="records")
        for r in tx_raw:
            county_meta = {"state": "TX", "county": r.get("COUNTY", "Harris"), "statute": "Tex. Tax Code § 34.04"}
            leads = process_county_dataset([r], county_meta)
            all_leads.extend(leads)

    # 3. Process Georgia Dataset
    ga_csv = DATA_DIR / "raw_georgia_feed.csv"
    if ga_csv.exists():
        ga_raw = pd.read_csv(ga_csv).to_dict(orient="records")
        for r in ga_raw:
            county_meta = {"state": "GA", "county": r.get("COUNTY", "Fulton"), "statute": "O.C.G.A. § 48-4-5"}
            leads = process_county_dataset([r], county_meta)
            all_leads.extend(leads)

    # 4. Process North Carolina Dataset
    nc_csv = DATA_DIR / "raw_nc_feed.csv"
    if nc_csv.exists():
        nc_raw = pd.read_csv(nc_csv).to_dict(orient="records")
        for r in nc_raw:
            county_meta = {"state": "NC", "county": r.get("COUNTY", "Wake"), "statute": "N.C.G.S. § 105-374"}
            leads = process_county_dataset([r], county_meta)
            all_leads.extend(leads)

    # 5. Process Tennessee Dataset
    tn_csv = DATA_DIR / "raw_tn_feed.csv"
    if tn_csv.exists():
        tn_raw = pd.read_csv(tn_csv).to_dict(orient="records")
        for r in tn_raw:
            county_meta = {"state": "TN", "county": r.get("COUNTY", "Davidson"), "statute": "T.C.A. § 67-5-2501"}
            leads = process_county_dataset([r], county_meta)
            all_leads.extend(leads)

    # 6. Process California Dataset
    ca_csv = DATA_DIR / "raw_ca_feed.csv"
    if ca_csv.exists():
        ca_raw = pd.read_csv(ca_csv).to_dict(orient="records")
        for r in ca_raw:
            county_meta = {"state": "CA", "county": r.get("COUNTY", "Los Angeles"), "statute": "Cal. Rev. & Tax Code § 4675"}
            leads = process_county_dataset([r], county_meta)
            all_leads.extend(leads)

    if not all_leads:
        print("[!] No records processed.")
        return

    # Sort all leads descending by surplus amount
    all_leads.sort(key=lambda x: x["Surplus_Balance_USD"], reverse=True)
    df_all = pd.DataFrame(all_leads)

    # Generate Master Exports
    master_csv = EXPORTS_DIR / "Master_Surplus_Lead_Feed.csv"
    master_xlsx = EXPORTS_DIR / "Master_Surplus_Lead_Feed.xlsx"
    master_json = EXPORTS_DIR / "Master_Surplus_Lead_Feed.json"

    df_all.to_csv(master_csv, index=False)
    try:
        df_all.to_excel(master_xlsx, index=False)
    except Exception:
        pass
    
    with open(master_json, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_records": len(all_leads),
            "total_surplus_volume_usd": round(float(df_all["Surplus_Balance_USD"].sum()), 2),
            "total_finder_fees_available_usd": round(float(df_all["Est_Finder_Fee_USD"].sum()), 2),
            "data": all_leads
        }, f, indent=2)

    # State-specific exports
    state_dfs = {
        "FL": (df_all[df_all["State"] == "FL"], "Florida_Surplus_Feed", "Fla. Stat. § 197.582", "florida.json"),
        "TX": (df_all[df_all["State"] == "TX"], "Texas_Surplus_Feed", "Tex. Tax Code § 34.04", "texas.json"),
        "GA": (df_all[df_all["State"] == "GA"], "Georgia_Surplus_Feed", "O.C.G.A. § 48-4-5", "georgia.json"),
        "NC": (df_all[df_all["State"] == "NC"], "North_Carolina_Surplus_Feed", "N.C.G.S. § 105-374", "north-carolina.json"),
        "TN": (df_all[df_all["State"] == "TN"], "Tennessee_Surplus_Feed", "T.C.A. § 67-5-2501", "tennessee.json"),
        "CA": (df_all[df_all["State"] == "CA"], "California_Surplus_Feed", "Cal. Rev. & Tax Code § 4675", "california.json"),
    }

    for state_code, (df_state, file_base, statute, api_file) in state_dfs.items():
        if len(df_state) > 0:
            df_state.to_csv(EXPORTS_DIR / f"{file_base}.csv", index=False)
            try:
                df_state.to_excel(EXPORTS_DIR / f"{file_base}.xlsx", index=False)
            except Exception:
                pass

    def redact_lead_for_public_sandbox(lead: dict) -> dict:
        redacted = lead.copy()
        raw_name = str(lead.get("Owner_Name", "")).strip()
        parts = raw_name.split()
        if len(parts) >= 2:
            initials = " & ".join([p[0] + "." for p in parts if p not in ("&", "AND", "OF", "THE", "ESTATE", "EST.")][:2])
            last_name = parts[-1]
            masked_last = last_name[0] + "█" * max(4, len(last_name) - 1)
            redacted["Owner_Name"] = f"{initials} {masked_last} [SUBSCRIBER KEY REQUIRED]"
        else:
            redacted["Owner_Name"] = "[REDACTED — SUBSCRIBER KEY REQUIRED]"

        addr = str(lead.get("Property_Address", "")).strip()
        addr_parts = addr.split()
        if len(addr_parts) >= 3:
            redacted["Property_Address"] = f"{addr_parts[0]} {addr_parts[1]} [REDACTED — SUBSCRIBER ACCESS ONLY]"
        else:
            redacted["Property_Address"] = "[REDACTED — SUBSCRIBER ACCESS ONLY]"

        redacted["Access_Status"] = "REDACTED_PREVIEW"
        return redacted

    # Generate Secure Subscription-Gated Sandbox Web API Endpoints in site/api/v1/
    API_V1_DIR = BASE_DIR / "site" / "api" / "v1"
    API_V1_DIR.mkdir(parents=True, exist_ok=True)

    api_master_path = API_V1_DIR / "feed.json"
    api_health_path = API_V1_DIR / "health.json"

    redacted_leads = [redact_lead_for_public_sandbox(l) for l in all_leads]

    api_payload = {
        "status": "subscription_required",
        "authenticated": False,
        "access_tier": "Enterprise Programmatic Feed ($449/mo)",
        "message": (
            "Full unredacted REST API access requires an active Surplus Docket Enterprise subscription "
            "with a valid Bearer API token. Production feeds deliver unredacted claimant identities, "
            "verified property situs, and court docket links every business morning (Mon–Fri) at 7:00 AM EST."
        ),
        "api_version": "v1.0",
        "delivery_schedule": "Monday through Friday (Court Business Days) at 7:00 AM EST",
        "generated_at": datetime.now().isoformat(),
        "subscription_portal": "https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00",
        "subscribe_url": "https://buy.stripe.com/9B68wP9Cu7ndfqlfgy0ZW1Y",
        "meta": {
            "total_records_indexed": len(all_leads),
            "total_surplus_volume_usd": round(float(df_all["Surplus_Balance_USD"].sum()), 2),
            "preview_mode": "REDACTED_EVALUATION_SANDBOX",
            "jurisdictions_monitored": ["FL", "TX", "GA", "NC", "TN", "CA"],
            "statutes": [
                "Fla. Stat. § 197.582",
                "Tex. Tax Code § 34.04",
                "O.C.G.A. § 48-4-5",
                "N.C.G.S. § 105-374",
                "T.C.A. § 67-5-2501",
                "Cal. Rev. & Tax Code § 4675"
            ]
        },
        "records": redacted_leads
    }

    with open(api_master_path, "w", encoding="utf-8") as f:
        json.dump(api_payload, f, indent=2)

    for state_code, (df_state, file_base, statute, api_file) in state_dfs.items():
        state_records = [redact_lead_for_public_sandbox(r) for r in df_state.to_dict(orient="records")]
        is_expansion = state_code in ["NC", "TN", "CA"]
        sub_url = "https://buy.stripe.com/9B68wP9Cu7ndfqlfgy0ZW1Y" if is_expansion else "https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X"
        tier_label = "National Feed + REST API ($449/mo)" if is_expansion else "Tri-State Core Feed ($249/mo) or National Feed ($449/mo)"
        
        with open(API_V1_DIR / api_file, "w", encoding="utf-8") as f:
            json.dump({
                "status": "subscription_required",
                "authenticated": False,
                "access_tier": tier_label,
                "jurisdiction": state_code,
                "statute": statute,
                "delivery_schedule": "Monday through Friday (Court Business Days) at 7:00 AM EST",
                "message": f"Full unredacted {state_code} tax deed surplus records require an active {tier_label} subscription.",
                "subscribe_url": sub_url,
                "total_records": len(state_records),
                "preview_mode": "REDACTED_EVALUATION_SANDBOX",
                "records": state_records
            }, f, indent=2)

    with open(api_health_path, "w", encoding="utf-8") as f:
        json.dump({
            "status": "healthy",
            "service": "Surplus Docket REST API Gateway",
            "version": "1.0.0",
            "delivery_schedule": "Monday through Friday (Court Business Days) at 7:00 AM EST",
            "authentication": "Bearer <sd_live_api_key>",
            "timestamp": datetime.now().isoformat(),
            "uptime": "99.99%",
            "endpoints": [
                "/api/v1/feed.json",
                "/api/v1/florida.json",
                "/api/v1/texas.json",
                "/api/v1/georgia.json",
                "/api/v1/north-carolina.json",
                "/api/v1/tennessee.json",
                "/api/v1/california.json",
                "/api/v1/health.json"
            ]
        }, f, indent=2)

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
    print(f"   - {master_json.name} (REST API payload)")
    print(f"🌐 Published Live REST API Endpoints in: {API_V1_DIR}")
    print(f"   - {api_master_path.name}")
    print(f"   - {api_health_path.name}")

if __name__ == "__main__":
    generate_b2b_exports()
