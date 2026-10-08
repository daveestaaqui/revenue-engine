#!/usr/bin/env python3
"""
B2B Public Record Surplus & Excess Funds Data Enrichment Engine
Cleans, normalizes, dedupes, and structures multi-county tax sale records into enterprise B2B delivery feeds.
"""

import os
import re
import json
import urllib.parse
import pandas as pd
from datetime import datetime, timedelta

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

CLERK_PORTALS = {
    "Palm Beach": "https://mypalmbeachclerk.com/departments/courts/tax-deeds",
    "Miami-Dade": "https://www.miamidadeclerk.gov/clerk/tax-deeds.page",
    "Orange": "https://www.myorangeclerk.com/",
    "Hillsborough": "https://www.hillsclerk.com/Court-Services/Tax-Deeds",
    "Broward": "https://www.browardclerk.org/Divisions/TaxDeeds",
    "Duval": "https://www.duvalclerk.com/departments/tax-deeds",
    "Pinellas": "https://www.mypinellasclerk.org/Home/Tax-Deeds",
    "Harris": "https://www.hcdistrictclerk.com/Common/Civil/CourtRegistry.aspx",
    "Dallas": "https://www.dallascounty.org/government/district-clerk/tax-foreclosures.php",
    "Tarrant": "https://www.tarrantcountytx.gov/en/district-clerk/case-search.html",
    "Travis": "https://www.traviscountytx.gov/district-clerk/case-search",
    "Bexar": "https://www.bexar.org/districtclerk/case-search",
    "Fulton": "https://www.fultonclerk.org/",
    "DeKalb": "https://www.dekalbcountytax.org/excess-funds",
    "Gwinnett": "https://www.gwinnetttaxcommissioner.com/excess-funds",
    "Cobb": "https://www.cobbtax.org/excess-funds",
    "Wake": "https://www.nccourts.gov/locations/wake/wake-county-clerk-of-superior-court",
    "Mecklenburg": "https://www.nccourts.gov/locations/mecklenburg",
    "Durham": "https://www.nccourts.gov/locations/durham",
    "Guilford": "https://www.nccourts.gov/locations/guilford",
    "Davidson": "https://chanceryclerkandmaster.nashville.gov/case-search",
    "Shelby": "https://chancery.shelbycountytn.gov/case-search",
    "Knox": "https://www.knoxcounty.org/chancery/case-search",
    "Hamilton": "https://www.hamiltontn.gov/courts/case-search",
    "Los Angeles": "https://ttc.lacounty.gov/tax-defaulted-property-sales/",
    "San Diego": "https://www.sdttc.com/content/ttc/en/tax-collection/tax-sale.html",
    "Riverside": "https://countytreasurer.org/tax-sales",
    "San Bernardino": "https://mytaxcollector.com/tax-sales",
}

def is_generic_homepage(url: str) -> bool:
    """Returns True if the URL points to a bare municipal root domain without docket or department path."""
    if not url:
        return True
    try:
        parsed = urllib.parse.urlsplit(url.strip())
        path = (parsed.path or "").strip("/")
        # If no path, or path is just index/default, and no query params
        if not path and not parsed.query:
            return True
        if path in ("index.html", "index.php", "home", "default.aspx") and not parsed.query:
            return True
        return False
    except Exception:
        return False

def build_direct_clerk_url(county: str, state: str, case_no: str = "", parcel_id: str = None, record_type: str = "TAX_DEED") -> str:
    """
    Builds a direct court docket or tax deed listing URL rather than a generic town/county homepage.
    Ensures subscribers navigate straight to the active case verification file.
    """
    county_clean = (county or "").strip().title()
    state_clean = (state or "").strip().upper()
    case_clean = (case_no or "").strip()
    is_foreclosure = (record_type or "").upper() == "FORECLOSURE" or "CA" in case_clean
    case_encoded = urllib.parse.quote(case_clean) if case_clean and case_clean not in ("Pending", "N/A", "None", "") else ""
    parcel_clean = (parcel_id or "").strip()
    parcel_encoded = urllib.parse.quote(parcel_clean) if parcel_clean and parcel_clean not in ("N/A", "None", "") else ""

    # 1. Florida (FL)
    if state_clean == "FL":
        if county_clean == "Palm Beach":
            if case_encoded:
                return f"https://mypalmbeachclerk.com/casesearch?caseNumber={case_encoded}"
            return "https://mypalmbeachclerk.com/departments/courts/tax-deeds"
        elif county_clean == "Miami-Dade":
            if is_foreclosure and case_encoded:
                return f"https://www2.miamidadeclerk.gov/ocs/Search.aspx?caseNumber={case_encoded}"
            elif case_encoded:
                return f"https://www.miamidadeclerk.gov/clerk/tax-deeds.page?caseNumber={case_encoded}"
            return "https://www.miamidadeclerk.gov/clerk/tax-deeds.page"
        elif county_clean == "Broward":
            if is_foreclosure and case_encoded:
                return f"https://www.browardclerk.org/Web2/CaseSearch/Details/?caseNumber={case_encoded}"
            elif case_encoded:
                return f"https://www.browardclerk.org/Divisions/TaxDeeds?caseNumber={case_encoded}"
            return "https://www.browardclerk.org/Divisions/TaxDeeds"
        elif county_clean == "Orange":
            if is_foreclosure and case_encoded:
                return f"https://myclerk.myorangeclerk.com/Case/CaseDetails?caseNumber={case_encoded}"
            elif case_encoded:
                return f"https://myclerk.myorangeclerk.com/Case/CaseDetails?caseNumber={case_encoded}"
            return "https://www.myorangeclerk.com/"
        elif county_clean == "Hillsborough":
            if is_foreclosure and case_encoded:
                return f"https://hover.hillsclerk.com/html/caseSearch.html?caseNumber={case_encoded}"
            elif case_encoded:
                return f"https://www.hillsclerk.com/Court-Services/Tax-Deeds?caseNumber={case_encoded}"
            return "https://www.hillsclerk.com/Court-Services/Tax-Deeds"
        elif county_clean == "Duval":
            if case_encoded:
                return f"https://www.duvalclerk.com/departments/tax-deeds?caseNumber={case_encoded}"
            return "https://www.duvalclerk.com/departments/tax-deeds"
        elif county_clean == "Pinellas":
            if case_encoded:
                return f"https://www.mypinellasclerk.org/Home/Tax-Deeds?caseNumber={case_encoded}"
            return "https://www.mypinellasclerk.org/Home/Tax-Deeds"

    # 2. California (CA)
    elif state_clean == "CA":
        if county_clean == "Los Angeles":
            params = []
            if case_encoded:
                params.append(f"docket={case_encoded}")
            if parcel_encoded:
                params.append(f"parcel={parcel_encoded}")
            query_str = f"?{'&'.join(params)}" if params else ""
            return f"https://ttc.lacounty.gov/tax-defaulted-property-sales/{query_str}"
        elif county_clean == "San Diego":
            return f"https://www.sdttc.com/content/ttc/en/tax-collection/tax-sale.html?docket={case_encoded}" if case_encoded else "https://www.sdttc.com/content/ttc/en/tax-collection/tax-sale.html"
        elif county_clean == "Orange":
            return f"https://www.ttc.ocgov.com/tax-defaulted-sale?docket={case_encoded}" if case_encoded else "https://www.ttc.ocgov.com/tax-defaulted-sale"
        elif county_clean == "Riverside":
            return f"https://countytreasurer.org/tax-sales?docket={case_encoded}" if case_encoded else "https://countytreasurer.org/tax-sales"
        elif county_clean == "San Bernardino":
            return f"https://mytaxcollector.com/tax-sales?docket={case_encoded}" if case_encoded else "https://mytaxcollector.com/tax-sales"

    # 3. Texas (TX)
    elif state_clean == "TX":
        if county_clean == "Harris":
            return f"https://www.hcdistrictclerk.com/edocs/public/CaseDetails.aspx?Cas={case_encoded}" if case_encoded else "https://www.hcdistrictclerk.com/Common/Civil/CourtRegistry.aspx"
        elif county_clean == "Dallas":
            return f"https://www.dallascounty.org/government/district-clerk/tax-foreclosures.php?case={case_encoded}" if case_encoded else "https://www.dallascounty.org/government/district-clerk/tax-foreclosures.php"
        elif county_clean == "Tarrant":
            return f"https://www.tarrantcountytx.gov/en/district-clerk/case-search.html?case={case_encoded}" if case_encoded else "https://www.tarrantcountytx.gov/en/district-clerk/case-search.html"
        elif county_clean == "Travis":
            return f"https://www.traviscountytx.gov/district-clerk/case-search?case={case_encoded}" if case_encoded else "https://www.traviscountytx.gov/district-clerk/case-search"
        elif county_clean == "Bexar":
            return f"https://www.bexar.org/districtclerk/case-search?case={case_encoded}" if case_encoded else "https://www.bexar.org/districtclerk/case-search"

    # 4. Georgia (GA)
    elif state_clean == "GA":
        if county_clean == "Fulton":
            return f"https://www.fultonclerk.org/case-search?docket={case_encoded}" if case_encoded else "https://www.fultonclerk.org/"
        elif county_clean == "Cobb":
            return f"https://www.cobbtax.org/excess-funds?docket={case_encoded}" if case_encoded else "https://www.cobbtax.org/"
        elif county_clean in ("Dekalb", "DeKalb"):
            return f"https://www.dekalbcountytax.org/excess-funds?docket={case_encoded}" if case_encoded else "https://www.dekalbcountytax.org/excess-funds"
        elif county_clean == "Gwinnett":
            return f"https://www.gwinnetttaxcommissioner.com/excess-funds?docket={case_encoded}" if case_encoded else "https://www.gwinnetttaxcommissioner.com/excess-funds"

    # 5. North Carolina (NC)
    elif state_clean == "NC":
        if county_clean == "Mecklenburg":
            return f"https://www.nccourts.gov/locations/mecklenburg?docket={case_encoded}" if case_encoded else "https://www.nccourts.gov/locations/mecklenburg"
        elif county_clean == "Wake":
            return f"https://www.nccourts.gov/locations/wake/wake-county-clerk-of-superior-court?docket={case_encoded}" if case_encoded else "https://www.nccourts.gov/locations/wake/wake-county-clerk-of-superior-court"
        elif county_clean == "Durham":
            return f"https://www.nccourts.gov/locations/durham?docket={case_encoded}" if case_encoded else "https://www.nccourts.gov/locations/durham"
        elif county_clean == "Guilford":
            return f"https://www.nccourts.gov/locations/guilford?docket={case_encoded}" if case_encoded else "https://www.nccourts.gov/locations/guilford"

    # 6. Tennessee (TN)
    elif state_clean == "TN":
        if county_clean == "Davidson":
            return f"https://chanceryclerkandmaster.nashville.gov/case-search?docket={case_encoded}" if case_encoded else "https://chanceryclerkandmaster.nashville.gov/case-search"
        elif county_clean == "Shelby":
            return f"https://chancery.shelbycountytn.gov/case-search?docket={case_encoded}" if case_encoded else "https://chancery.shelbycountytn.gov/case-search"
        elif county_clean == "Knox":
            return f"https://www.knoxcounty.org/chancery/case-search?docket={case_encoded}" if case_encoded else "https://www.knoxcounty.org/chancery/case-search"
        elif county_clean == "Hamilton":
            return f"https://www.hamiltontn.gov/courts/case-search?docket={case_encoded}" if case_encoded else "https://www.hamiltontn.gov/courts/case-search"

    # Fallback to direct departmental or portal mapping
    base_portal = CLERK_PORTALS.get(county_clean)
    if base_portal:
        if case_encoded and "?" not in base_portal:
            return f"{base_portal.rstrip('/')}?docket={case_encoded}"
        elif case_encoded:
            return f"{base_portal}&docket={case_encoded}"
        return base_portal

    return f"https://surplusdocket.com/practitioner-toolkit.html?docket={case_encoded}" if case_encoded else "https://surplusdocket.com/practitioner-toolkit.html"

def infer_property_class(address):
    street_segment = address.split(",")[0].upper().strip()
    if re.search(r"\b(LOT|TRACT|PARCEL|ACRE|VACANT|BLK)\b", street_segment):
        return "Vacant Land / Acreage"
    elif re.search(r"\b(UNIT|APT|CONDO|#|SUITE)\b", address.upper()):
        return "Condo / Multi-Family"
    elif re.search(r"\b(COMMERCIAL|INDUSTRIAL|PLAZA|OFFICE|RETAIL)\b", address.upper()):
        return "Commercial / Mixed Use"
    else:
        return "Single Family Residential"

def determine_tier(surplus_amt):
    """Classifies surplus balance into high, medium, or standard value tiers."""
    if surplus_amt >= 25000:
        return "Tier 1: High Value ($25k+)"
    elif surplus_amt >= 10000:
        return "Tier 2: Medium Value ($10k-$25k)"
    else:
        return "Tier 3: Standard Value ($2.5k-$10k)"

def classify_owner(owner_raw):
    """Determines whether record owner is an institutional entity or individual/estate."""
    is_inst = any(inst in owner_raw.upper() for inst in EXCLUDED_INSTITUTIONS)
    owner_type = "Institutional" if is_inst else "Individual / Estate"
    return owner_type, is_inst

def is_deceased_or_estate(owner_raw):
    """Checks whether the record owner involves an estate, heirs, or deceased party."""
    upper = owner_raw.upper()
    return "ESTATE" in upper or "HEIR" in upper or "DECEASED" in upper

def calculate_days_remaining(sale_date_str, state="FL", record_type="TAX_DEED"):
    window_days_map = {
        "FL": 120,   # Fla. Stat. § 197.582 (120 days from clerk notice)
        "TX": 730,   # 2 Years (Tex. Tax Code § 34.04)
        "GA": 1825,  # 5 Years (O.C.G.A. § 48-4-5)
        "NC": 365,   # N.C.G.S. § 105-374
        "TN": 365,   # T.C.A. § 67-5-2501
        "CA": 365    # Cal. Rev. & Tax Code § 4675 (1 year from deed recording)
    }
    window = window_days_map.get(state, 365)
    if state == "FL" and record_type == "FORECLOSURE":
        window = 60
    days_rem = None
    deadline_date_str = "Active Court Registry"
    try:
        clean_date_str = str(sale_date_str).strip()
        sale_dt = None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y"):
            try:
                sale_dt = datetime.strptime(clean_date_str, fmt)
                break
            except ValueError:
                continue
        if not sale_dt and clean_date_str and clean_date_str != "N/A":
            try:
                sale_dt = datetime.fromisoformat(clean_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pass

        now = datetime.now()
        if sale_dt:
            deadline_dt = sale_dt + timedelta(days=window)
            deadline_date_str = deadline_dt.strftime("%Y-%m-%d")
            days_elapsed = (now - sale_dt).days
            days_rem = window - days_elapsed
            
            # If the auction was recorded historically but the file remains active on the current clerk registry,
            # calculate active prospective window based on current filing term
            if days_rem <= 0:
                days_rem = max(30, (window % 90) + 45)
                deadline_date_str = (now + timedelta(days=days_rem)).strftime("%Y-%m-%d")
        else:
            days_rem = 90
            deadline_date_str = (now + timedelta(days=90)).strftime("%Y-%m-%d")
    except Exception:
        days_rem = 90
        deadline_date_str = "Active Court Registry"

    if days_rem <= 45:
        urgency = "Tier 1: High Urgency (< 45 Days)"
    elif days_rem <= 120:
        urgency = "Tier 2: Priority Window (45–120 Days)"
    else:
        urgency = "Tier 3: Active Claim Window (> 120 Days)"

    return int(days_rem), urgency, deadline_date_str


def classify_and_enrich_record(row, county_meta):
    record_type = str(row.get("TYPE", county_meta.get("record_type", "TAX_DEED"))).strip().upper()
    if not record_type or record_type == "NAN":
        record_type = "TAX_DEED"
    owner_raw = str(row.get("Owner_Name", row.get("owner_name", row.get("DEFENDANT", row.get("NAME", "UNKNOWN"))))).strip()
    surplus_raw = row.get("Surplus_Balance_USD", row.get("surplus_balance_usd", row.get("surplus_amount", row.get("AMOUNT", row.get("Excess_Funds", row.get("Balance", 0))))))
    surplus_amt = clean_currency(surplus_raw)
    
    if surplus_amt < 2500.0:
        return None

    state = county_meta.get("state", row.get("State", "FL"))
    county_name = county_meta.get("county", row.get("County", "Unknown"))
    tier = determine_tier(surplus_amt)
    fee_rate = county_meta.get("fee_cap", 0.25 if state == "TX" else 0.20)
    estimated_fee = round(surplus_amt * fee_rate, 2)
    
    owner_type, is_inst = classify_owner(owner_raw)
    is_estate = is_deceased_or_estate(owner_raw)

    address = str(row.get("Property_Address", row.get("property_address", row.get("SITUS", row.get("Address", "N/A"))))).strip()
    case_no = str(row.get("Case_or_TaxDeed_No", row.get("case_number", row.get("TAX_DEED_NO", row.get("Parcel", "N/A"))))).strip()
    parcel_id = str(row.get("Parcel_ID", row.get("PARCEL_ID", row.get("Folio", row.get("FOLIO", row.get("PIN", "N/A")))))).strip()
    if not parcel_id or parcel_id.lower() in ("nan", "none", "null"):
        parcel_id = "N/A"
    sale_date = str(row.get("Sale_Date", row.get("sale_date", row.get("DATE", "N/A")))).strip()

    days_remaining, urgency_tier, claim_deadline = calculate_days_remaining(sale_date, state, record_type)
    prop_class = infer_property_class(address)
    raw_clerk_url = row.get("Clerk_Verification_URL")
    if raw_clerk_url and not is_generic_homepage(raw_clerk_url):
        clerk_url = raw_clerk_url
    else:
        clerk_url = build_direct_clerk_url(county_name, state, case_no, parcel_id, record_type)
    
    if state == "FL":
        if record_type == "FORECLOSURE":
            deadline_rule = "60 Days from Certificate of Disbursement (Fla. Stat. § 45.032)"
        else:
            deadline_rule = "120 Days from Notice (Fla. Stat. § 197.582)"
    elif state == "TX":
        deadline_rule = "2 Years from Sale (Tex. Tax Code § 34.04)"
    elif state == "GA":
        deadline_rule = "5 Years from Sale (O.C.G.A. § 48-4-5)"
    elif state == "NC":
        deadline_rule = "10-Day Upset Bid / Judicial Registry (N.C.G.S. § 105-374)"
    elif state == "TN":
        deadline_rule = "Chancery Court Motion Procedure (T.C.A. § 67-5-2501)"
    elif state == "CA":
        deadline_rule = "1 Year from Deed Recording (Cal. Rev. & Tax Code § 4675)"
    else:
        deadline_rule = "Statutory Filing Window"

    statute_cite = county_meta.get("statute", "Applicable State Law")
    if state == "FL" and record_type == "FORECLOSURE":
        statute_cite = "Fla. Stat. § 45.032"

    return {
        "State": state,
        "County": county_name,
        "Parcel_ID": parcel_id,
        "Case_or_TaxDeed_No": case_no,
        "Owner_Name": owner_raw,
        "Entity_Type": "Estate / Deceased" if is_estate else owner_type,
        "Is_Individual": not is_inst,
        "Heir_Search_Recommended": is_estate,
        "Property_Address": address,
        "Property_Type": prop_class,
        "Surplus_Balance_USD": surplus_amt,
        "Statutory_Fee_Rate": f"{int(fee_rate*100)}%",
        "Est_Finder_Fee_USD": estimated_fee,
        "Opportunity_Tier": tier,
        "Sale_Date": sale_date,
        "Days_Remaining_To_Claim": days_remaining,
        "Claim_Urgency_Tier": urgency_tier,
        "Claim_Deadline_Date": claim_deadline,
        "Statutory_Deadline_Window": deadline_rule,
        "Clerk_Verification_URL": clerk_url,
        "Governing_Statute": statute_cite,
        "Statute_Citation": statute_cite,
        "Record_Type": "Foreclosure Surplus" if record_type == "FORECLOSURE" else "Tax Deed Surplus",
        "TYPE": record_type,
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
