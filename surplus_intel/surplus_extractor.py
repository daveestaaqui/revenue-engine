#!/usr/bin/env python3
"""
High-Speed Municipal Surplus & Excess Funds Parser
Ingests public tax sale overage lists (CSV, PDF, TXT) and outputs clean structured data.
"""

import os
import re
import json
import pandas as pd
from pypdf import PdfReader

EXCLUDED_INSTITUTIONAL_KEYWORDS = [
    "BANK", "MORTGAGE", "TRUSTEE", "SERVICING", "LLC", "INC", "CORP", 
    "ASSOCIATION", "HOA", "NATIONAL", "DEUTSCHE", "CITIBANK", "CHASE",
    "WELLS FARGO", "FANNIE MAE", "FREDDIE MAC", "INTERNAL REVENUE"
]

def clean_currency(val):
    if not val:
        return 0.0
    val_str = str(val).replace("$", "").replace(",", "").strip()
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def parse_tabular_surplus_data(file_path):
    """
    Parses CSV or Excel surplus dumps.
    """
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
    elif file_path.endswith((".xls", ".xlsx")):
        df = pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path}")

    records = []
    for _, row in df.iterrows():
        records.append(row.to_dict())
    return records

def parse_pdf_surplus_list(pdf_path):
    """
    Extracts text lines from multi-page County surplus PDF rosters.
    """
    reader = PdfReader(pdf_path)
    extracted_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            extracted_text.append(text)
    return "\n".join(extracted_text)

def process_raw_records(records, state="FL", default_fee_rate=0.20):
    processed = []
    for r in records:
        owner = str(r.get("owner_name", r.get("Owner", r.get("DEFENDANT", r.get("NAME", "UNKNOWN"))))).strip()
        surplus_amt = clean_currency(r.get("surplus_amount", r.get("Excess_Funds", r.get("AMOUNT", r.get("Balance", 0)))))
        parcel_id = str(r.get("parcel_id", r.get("Parcel", r.get("TAX_DEED_NO", r.get("Case_Number", "N/A"))))).strip()
        address = str(r.get("property_address", r.get("Address", r.get("SITUS", "N/A")))).strip()
        sale_date = str(r.get("sale_date", r.get("Sale_Date", r.get("DATE", "N/A")))).strip()

        # Classify owner type: Individual vs Entity
        is_entity = any(k in owner.upper() for k in EXCLUDED_INSTITUTIONAL_KEYWORDS)
        owner_type = "Institutional / Corporate" if is_entity else "Individual / Estate"

        potential_fee = surplus_amt * default_fee_rate

        if surplus_amt >= 1000.0:  # Ignore trivial amounts under $1k
            processed.append({
                "parcel_or_case": parcel_id,
                "owner_name": owner,
                "owner_type": owner_type,
                "property_address": address,
                "surplus_amount": surplus_amt,
                "statutory_fee_rate": f"{int(default_fee_rate * 100)}%",
                "estimated_finder_fee": round(potential_fee, 2),
                "sale_date": sale_date,
                "state": state
            })

    # Sort descending by surplus amount
    processed.sort(key=lambda x: x["surplus_amount"], reverse=True)
    return processed

if __name__ == "__main__":
    print("Surplus Extractor Ready.")
