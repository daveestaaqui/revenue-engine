#!/usr/bin/env python3
"""
Surplus Docket — Attorney Litigation Dossier Generator
Produces structured public record recovery dossiers for licensed legal counsel.
Exclusively designed as attorney work product; contains zero consumer retainer or UPL language.
"""

import os
from datetime import datetime
from pathlib import Path

ATTORNEY_DOSSIER_TEMPLATE = """# CONFIDENTIAL ATTORNEY WORK-PRODUCT // SURPLUS RECOVERY DOSSIER
**Prepared Exclusively for Legal Counsel of Record**
*Surplus Docket Court Records Intelligence | https://surplusdocket.com*

---

## 1. DOCKET & PROPERTY IDENTIFICATION
- **Target Claimant / Former Owner:** {owner_name}
- **Property Situs / Address:** {property_address}
- **Tax Deed / Court Case Docket:** {case_number}
- **Jurisdiction / Registry:** {state} — {custodian}
- **Governing Legal Authority:** {statute}

---

## 2. AUDITED PROCEEDS & STATUTORY RECOVERY CALCULATION
- **Gross Surplus Balance Held in Registry:** ${surplus_amount:,.2f}
- **Statutory Benchmark Recovery Rate:** {fee_rate}
- **Estimated Gross Recoverable Equity:** ${estimated_fee:,.2f}
- **Institutional Lien Status:** 100% Upstream Bank / Senior Mortgage Filter Applied (Clean Individual/Estate Equity)

---

## 3. STATUTORY PLEADING & PROCEDURAL ROADMAP
- **Primary Pleading:** {pleading}
- **Claim Window / Limitation:** {claim_window}
- **Custodian of Funds:** {custodian}
- **Statutory Priority Hierarchy:** {priority_hierarchy}

---

## 4. REQUIRED EVIDENTIARY EXHIBITS FOR COUNSEL
- [ ] Certified copy of recorded Tax Deed showing overage from clerk sale.
- [ ] Certificate of Disbursements / Clerk Surplus Ledger Sheet.
- [ ] Chain of Title abstract establishing record ownership as of date of Lis Pendens / Auction.
- [ ] Client Identification & Representation Verification / Notice of Appearance.
- [ ] Verified Motion / Petition for Disbursement filed in Registry of the Court.

---
*Legal Notice: Surplus Docket compiles structured court and public records intelligence for licensed attorneys. This dossier constitutes automated litigation research and does not constitute legal representation or legal advice.*
"""

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = str(BASE_DIR / "output")

STATUTE_PROCEDURES = {
    "FL": {
        "statute": "Florida Statute § 197.582",
        "custodian": "County Clerk of Circuit Court / Comptroller",
        "pleading": "Verified Claim / Motion for Distribution of Tax Deed Surplus Funds",
        "claim_window": "120-Day Notice Window from Clerk Mailing",
        "priority_hierarchy": "Governmental Liens -> Senior Mortgagees/Lienholders of Record -> Record Titleholder / Heirs"
    },
    "TX": {
        "statute": "Texas Property Tax Code § 34.04",
        "custodian": "District Court Registry",
        "pleading": "Petition for Distribution of Excess Proceeds under Tex. Tax Code § 34.04",
        "claim_window": "Strict 2-Year Limitation Period from Deed Recordation",
        "priority_hierarchy": "Taxing Entities -> Non-Party Lienholders -> Former Record Owner"
    },
    "GA": {
        "statute": "O.C.G.A. § 48-4-5",
        "custodian": "County Tax Commissioner / Sheriff Registry",
        "pleading": "Statutory Demand for Excess Proceeds / Superior Court Interpleader",
        "claim_window": "5-Year Statutory Interpleader Hold",
        "priority_hierarchy": "Record Owner at Time of Tax Sale -> Junior Lienholders in Priority Order"
    },
    "NC": {
        "statute": "N.C. Gen. Stat. § 105-374",
        "custodian": "Clerk of Superior Court Registry",
        "pleading": "Special Proceeding Petition for Distribution of Surplus Foreclosure Proceeds",
        "claim_window": "10-Day Statutory Upset Bid Period Following Sale Report",
        "priority_hierarchy": "Taxing Authorities -> Mortgagees of Record -> Heirs / Titleholders"
    },
    "TN": {
        "statute": "Tenn. Code Ann. § 67-5-2510",
        "custodian": "Chancery Court Clerk & Master Registry",
        "pleading": "Motion for Excess Sale Proceeds in Chancery Tax Suit",
        "claim_window": "1-Year Statutory Redemption & Claim Window",
        "priority_hierarchy": "Court Costs / Taxes -> Prior Recorded Deeds of Trust -> Former Property Owner"
    },
    "CA": {
        "statute": "California Rev. & Tax Code § 4675",
        "custodian": "County Board of Supervisors / Tax Collector",
        "pleading": "Formal Claim for Excess Proceeds under § 4675 with Assignment / Heir Affidavits",
        "claim_window": "Strict 1-Year Limitation Period from Deed Recording Date",
        "priority_hierarchy": "Holders of Recorded Liens in Legal Priority -> Any Person with Title of Record"
    }
}

def generate_claim_packet(lead, out_dir=DEFAULT_OUT_DIR):
    """Generates an Attorney Litigation Dossier for the given lead."""
    os.makedirs(out_dir, exist_ok=True)
    clean_name = "".join(c for c in lead["owner_name"] if c.isalnum() or c in " _-").strip().replace(" ", "_")
    filename = os.path.join(out_dir, f"Attorney_Dossier_{clean_name}_{lead['parcel_or_case']}.md")

    st = lead.get("state", "FL").upper()
    proc = STATUTE_PROCEDURES.get(st, {
        "statute": "Applicable State Surplus Statute",
        "custodian": "County Court Registry",
        "pleading": "Verified Motion for Distribution of Surplus Funds",
        "claim_window": "Jurisdictional Statutory Window",
        "priority_hierarchy": "Taxes -> Recorded Lienholders -> Record Titleholder"
    })

    content = ATTORNEY_DOSSIER_TEMPLATE.format(
        owner_name=lead["owner_name"],
        property_address=lead["property_address"],
        case_number=lead["parcel_or_case"],
        state=st,
        custodian=proc["custodian"],
        statute=proc["statute"],
        surplus_amount=lead["surplus_amount"],
        fee_rate=lead["statutory_fee_rate"],
        estimated_fee=lead.get("estimated_finder_fee", lead["surplus_amount"] * 0.20),
        pleading=proc["pleading"],
        claim_window=proc["claim_window"],
        priority_hierarchy=proc["priority_hierarchy"]
    )

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return filename

# Alias for semantic clarity
generate_attorney_dossier = generate_claim_packet

if __name__ == "__main__":
    print("Attorney Dossier Generator Ready.")
