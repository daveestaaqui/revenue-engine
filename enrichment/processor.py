#!/usr/bin/env python3
"""
B2B Public Record Surplus & Excess Funds Data Enrichment Engine
Cleans, normalizes, dedupes, and structures multi-county tax sale records into enterprise B2B delivery feeds.
"""

import os
import re
import json
import pandas as pd
from datetime import datetime

EXCLUDED_INSTITUTIONS = [
    "BANK", "MORTGAGE", "TRUSTEE", "SERVICING", "LLC", "INC", "CORP", 
    "ASSOCIATION", "HOA", "NATIONAL", "DEUTSCHE", "CITIBANK", "CHASE",
    "WELLS FARGO", "FANNIE MAE", "FREDDIE MAC", "INTERNAL REVENUE",
    "CAPITAL", "INVESTMENTS", "HOLDINGS", "FUNDING", "LENDING"
]

def clean_currency(val):
    if val is None or pd.isna(val):
        return 0.0
    val_str = str(val).replace("$", "").replace(",", "").strip()
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def classify_and_enrich_record(row, county_meta):
    owner_raw = str(row.get("owner_name", row.get("DEFENDANT", row.get("NAME", "UNKNOWN")))).strip()
    surplus_raw = row.get("surplus_amount", row.get("AMOUNT", row.get("Excess_Funds", row.get("Balance", 0))))
    surplus_amt = clean_currency(surplus_raw)
    
    if surplus_amt < 2500.0:
        return None

    # Check if institutional entity
    is_inst = any(inst in owner_raw.upper() for inst in EXCLUDED_INSTITUTIONS)
    owner_type = "Institutional" if is_inst else "Individual / Estate"
    is_estate = "ESTATE" in owner_raw.upper() or "HEIR" in owner_raw.upper() or "DECEASED" in owner_raw.upper()

    # Priority Tier
    if surplus_amt >= 25000:
        tier = "Tier 1: High Value ($25k+)"
    elif surplus_amt >= 10000:
        tier = "Tier 2: Medium Value ($10k-$25k)"
    else:
        tier = "Tier 3: Standard Value ($2.5k-$10k)"

    state = county_meta.get("state", "FL")
    fee_rate = 0.20 if state in ["FL", "GA"] else 0.25
    estimated_fee = round(surplus_amt * fee_rate, 2)

    address = str(row.get("property_address", row.get("SITUS", row.get("Address", "N/A")))).strip()
    case_no = str(row.get("case_number", row.get("TAX_DEED_NO", row.get("Parcel", "N/A")))).strip()
    sale_date = str(row.get("sale_date", row.get("DATE", "N/A"))).strip()

    return {
        "State": state,
        "County": county_meta.get("county", "Unknown"),
        "Case_or_TaxDeed_No": case_no,
        "Owner_Name": owner_raw,
        "Entity_Type": "Estate / Deceased" if is_estate else owner_type,
        "Is_Individual": not is_inst,
        "Property_Address": address,
        "Surplus_Balance_USD": surplus_amt,
        "Statutory_Fee_Rate": f"{int(fee_rate*100)}%",
        "Est_Finder_Fee_USD": estimated_fee,
        "Opportunity_Tier": tier,
        "Sale_Date": sale_date,
        "Governing_Statute": county_meta.get("statute", "Applicable State Law"),
        "Enriched_Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def process_county_dataset(raw_records, county_meta):
    enriched = []
    for r in raw_records:
        item = classify_and_enrich_record(r, county_meta)
        if item and item["Is_Individual"]:
            enriched.append(item)

    enriched.sort(key=lambda x: x["Surplus_Balance_USD"], reverse=True)
    return enriched
