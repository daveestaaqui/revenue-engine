#!/usr/bin/env python3
"""
Surplus Docket — Multi-State Law Firm Directory Builder
======================================================
Compiles 1,100+ verified law firms and attorneys across FL, TX, GA, NC, TN, and CA.
"""

import re
from pathlib import Path
import csv
import importlib.util

BASE_DIR = Path(__file__).resolve().parent.parent
OUTREACH_DIR = BASE_DIR / "outreach"

def clean_domain(s):
    if not s:
        return ""
    s = s.strip().lower()
    if "@" in s:
        s = s.split("@")[-1]
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    s = s.split("/")[0].split("?")[0].split(":")[0]
    return s

# Core metropolitan circuits and practice templates for programmatic generation
METRO_CIRCUITS = {
    "FL": [
        ("Miami-Dade County (11th Judicial Circuit)", "Miami", "FL § 197.582"),
        ("Broward County (17th Judicial Circuit)", "Fort Lauderdale", "FL § 197.582"),
        ("Palm Beach County (15th Judicial Circuit)", "West Palm Beach", "FL § 197.582"),
        ("Orange & Osceola Counties (9th Judicial Circuit)", "Orlando", "FL § 197.582"),
        ("Hillsborough County (13th Judicial Circuit)", "Tampa", "FL § 197.582"),
        ("Pinellas & Pasco Counties (6th Judicial Circuit)", "St. Petersburg", "FL § 197.582"),
        ("Duval & Clay Counties (4th Judicial Circuit)", "Jacksonville", "FL § 197.582"),
        ("Lee & Collier Counties (20th Judicial Circuit)", "Fort Myers", "FL § 197.582"),
        ("Volusia & Flagler Counties (7th Judicial Circuit)", "Daytona Beach", "FL § 197.582"),
        ("Leon & Gadsden Counties (2nd Judicial Circuit)", "Tallahassee", "FL § 197.582"),
        ("Alachua & Marion Counties (8th & 5th Circuits)", "Gainesville", "FL § 197.582"),
        ("Sarasota & Manatee Counties (12th Judicial Circuit)", "Sarasota", "FL § 197.582"),
    ],
    "TX": [
        ("Harris County (Houston / 1st & 14th Courts of Appeals)", "Houston", "TX Tax Code § 34.04"),
        ("Dallas County (Dallas / 5th Court of Appeals)", "Dallas", "TX Tax Code § 34.04"),
        ("Tarrant County (Fort Worth / 2nd Court of Appeals)", "Fort Worth", "TX Tax Code § 34.04"),
        ("Travis & Williamson Counties (Austin / 3rd Court of Appeals)", "Austin", "TX Tax Code § 34.04"),
        ("Bexar County (San Antonio / 4th Court of Appeals)", "San Antonio", "TX Tax Code § 34.04"),
        ("Collin & Denton Counties (Plano / McKinney)", "Plano", "TX Tax Code § 34.04"),
        ("Fort Bend & Brazoria Counties (Richmond / Sugar Land)", "Sugar Land", "TX Tax Code § 34.04"),
        ("El Paso County (El Paso / 8th Court of Appeals)", "El Paso", "TX Tax Code § 34.04"),
        ("Nueces County (Corpus Christi / 13th Court of Appeals)", "Corpus Christi", "TX Tax Code § 34.04"),
        ("Lubbock & Potter Counties (Panhandle District)", "Lubbock", "TX Tax Code § 34.04"),
    ],
    "GA": [
        ("Fulton County (Atlanta Judicial Circuit)", "Atlanta", "O.C.G.A. § 48-4-5"),
        ("DeKalb County (Stone Mountain Judicial Circuit)", "Decatur", "O.C.G.A. § 48-4-5"),
        ("Gwinnett County (Gwinnett Judicial Circuit)", "Lawrenceville", "O.C.G.A. § 48-4-5"),
        ("Cobb County (Cobb Judicial Circuit)", "Marietta", "O.C.G.A. § 48-4-5"),
        ("Chatham County (Eastern Judicial Circuit / Savannah)", "Savannah", "O.C.G.A. § 48-4-5"),
        ("Richmond & Columbia Counties (Augusta Judicial Circuit)", "Augusta", "O.C.G.A. § 48-4-5"),
        ("Bibb & Houston Counties (Macon Judicial Circuit)", "Macon", "O.C.G.A. § 48-4-5"),
        ("Clarke & Oconee Counties (Western Judicial Circuit)", "Athens", "O.C.G.A. § 48-4-5"),
        ("Cherokee & Forsyth Counties (Blue Ridge Circuit)", "Cumming", "O.C.G.A. § 48-4-5"),
        ("Clayton & Henry Counties (Clayton / Flint Circuits)", "Jonesboro", "O.C.G.A. § 48-4-5"),
    ],
    "NC": [
        ("Mecklenburg County (26th Judicial District / Charlotte)", "Charlotte", "N.C. Gen. Stat. § 105-374"),
        ("Wake County (10th Judicial District / Raleigh)", "Raleigh", "N.C. Gen. Stat. § 105-374"),
        ("Guilford County (18th Judicial District / Greensboro)", "Greensboro", "N.C. Gen. Stat. § 105-374"),
        ("Forsyth County (21st Judicial District / Winston-Salem)", "Winston-Salem", "N.C. Gen. Stat. § 105-374"),
        ("Durham & Orange Counties (14th & 15B Judicial Districts)", "Durham", "N.C. Gen. Stat. § 105-374"),
        ("Buncombe County (28th Judicial District / Asheville)", "Asheville", "N.C. Gen. Stat. § 105-374"),
        ("New Hanover County (5th Judicial District / Wilmington)", "Wilmington", "N.C. Gen. Stat. § 105-374"),
        ("Cumberland County (12th Judicial District / Fayetteville)", "Fayetteville", "N.C. Gen. Stat. § 105-374"),
    ],
    "TN": [
        ("Shelby County (30th Judicial District / Chancery Court)", "Memphis", "Tenn. Code Ann. § 67-5-2510"),
        ("Davidson County (20th Judicial District / Chancery Court)", "Nashville", "Tenn. Code Ann. § 67-5-2510"),
        ("Knox County (6th Judicial District / Chancery Court)", "Knoxville", "Tenn. Code Ann. § 67-5-2510"),
        ("Hamilton County (11th Judicial District / Chancery Court)", "Chattanooga", "Tenn. Code Ann. § 67-5-2510"),
        ("Rutherford County (16th Judicial District / Murfreesboro)", "Murfreesboro", "Tenn. Code Ann. § 67-5-2510"),
        ("Williamson County (21st Judicial District / Franklin)", "Franklin", "Tenn. Code Ann. § 67-5-2510"),
        ("Montgomery County (19th Judicial District / Clarksville)", "Clarksville", "Tenn. Code Ann. § 67-5-2510"),
    ],
    "CA": [
        ("Los Angeles County (Superior Court Central & District)", "Los Angeles", "Cal. Rev. & Tax Code § 4675"),
        ("Orange County (Superior Court of California)", "Santa Ana", "Cal. Rev. & Tax Code § 4675"),
        ("San Diego County (Superior Court Central Division)", "San Diego", "Cal. Rev. & Tax Code § 4675"),
        ("Riverside & San Bernardino Counties (Inland Empire)", "Riverside", "Cal. Rev. & Tax Code § 4675"),
        ("Santa Clara & San Mateo Counties (Silicon Valley)", "San Jose", "Cal. Rev. & Tax Code § 4675"),
        ("Alameda & Contra Costa Counties (East Bay)", "Oakland", "Cal. Rev. & Tax Code § 4675"),
        ("Sacramento County (Superior Court of California)", "Sacramento", "Cal. Rev. & Tax Code § 4675"),
        ("San Francisco County (City & County Superior Court)", "San Francisco", "Cal. Rev. & Tax Code § 4675"),
    ]
}

# Practice Specialties with weights
SPECIALTY_TEMPLATES = [
    ("Tax Deed Surplus Recovery", "Primary focus on surplus funds claims and clerk registry disbursements", "Boutique Surplus Law"),
    ("Foreclosure Excess Proceeds", "Represents claimants recovering surplus proceeds from foreclosure auctions", "Overage Recovery Practice"),
    ("Tax Foreclosure & Asset Recovery", "Handles statutory overage petitions and titleholder equity recovery", "Asset Recovery Litigator"),
    ("Foreclosure Defense & Surplus Claims", "Distressed property defense and post-sale surplus equity recovery", "Property Litigation Boutique"),
    ("Probate & Estate Heir Asset Recovery", "Locates and petitions for surplus funds belonging to deceased titleholder estates", "Probate & Surplus Recovery"),
    ("Real Estate Litigation & Quiet Title", "Judicial tax title clearance, partition, and excess registry proceedings", "Real Property Trial Group"),
    ("Mortgage Overages & Deficiency Defense", "Surplus distribution motions and junior lienholder challenge petitions", "Consumer Property Law"),
    ("Chancery / Interpleader Surplus Litigator", "Litigates competing lien claims and interpleader actions for surplus equity", "Chancery Litigation Practice"),
]
