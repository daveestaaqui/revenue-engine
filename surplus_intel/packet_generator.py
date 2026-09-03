#!/usr/bin/env python3
"""
Automated Surplus Claim & Contingency Agreement Generator
Produces legally structured recovery documentation for owners/claimants.
"""

import os
from datetime import datetime
from pathlib import Path

AGREEMENT_TEMPLATE = """# SURPLUS FUNDS RECOVERY & CONTINGENCY FEE AGREEMENT

**Date:** {date}  
**Claimant (Former Owner/Heir):** {owner_name}  
**Property Address / Parcel ID:** {property_address} (Tax Deed #{case_number})  
**Jurisdiction:** {state} - County Court Clerk / Comptroller  
**Estimated Recoverable Surplus Balance:** ${surplus_amount:,.2f}  

---

### 1. APPOINTMENT AND SCOPE
Claimant hereby retains Asset Recovery Services ("Representative") to locate, document, prepare, and file all necessary statutory claims and petitions to secure the disbursement of excess tax deed sale proceeds held in the registry of the Court/Comptroller arising from the sale of the above-referenced property.

### 2. CONTINGENCY FEE STRUCTURE (NO UPFRONT COST)
Representative operates strictly on a **contingency basis**:
- **Contingency Fee:** {fee_rate} of gross funds actually recovered and disbursed by the County Clerk.
- **Client Net Share:** Remainder of all recovered proceeds disbursed directly to Claimant.
- **Zero Out-of-Pocket Risk:** If no funds are recovered, Claimant owes $0.00. All notary, filing, and administrative costs are borne by Representative.

### 3. AUTHORIZATION TO PREPARE CLAIM
Claimant authorizes Representative to obtain public case files, title search abstracts, and submit formal statutory claim affidavits in accordance with applicable state statutes ({statute}).

---

**CLAIMANT ACKNOWLEDGMENT & SIGNATURE:**

Signature: ___________________________________  
Printed Name: {owner_name}  
Date: ________________________  
Phone / Contact: _____________________________  
"""

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = str(BASE_DIR / "output")

def generate_claim_packet(lead, out_dir=DEFAULT_OUT_DIR):
    os.makedirs(out_dir, exist_ok=True)
    clean_name = "".join(c for c in lead["owner_name"] if c.isalnum() or c in " _-").strip().replace(" ", "_")
    filename = os.path.join(out_dir, f"Claim_Packet_{clean_name}_{lead['parcel_or_case']}.md")

    statute_map = {
        "FL": "Florida Statute § 197.582",
        "TX": "Texas Property Tax Code § 34.04",
        "GA": "O.C.G.A. § 48-4-5",
        "NC": "N.C.G.S. § 105-374",
        "TN": "T.C.A. § 67-5-2501",
        "CA": "California Rev. & Tax Code § 4675"
    }

    statute = statute_map.get(lead.get("state", "FL"), "Applicable State Surplus Statute")

    content = AGREEMENT_TEMPLATE.format(
        date=datetime.now().strftime("%B %d, %Y"),
        owner_name=lead["owner_name"],
        property_address=lead["property_address"],
        case_number=lead["parcel_or_case"],
        state=lead.get("state", "FL"),
        surplus_amount=lead["surplus_amount"],
        fee_rate=lead["statutory_fee_rate"],
        statute=statute
    )

    with open(filename, "w") as f:
        f.write(content)

    return filename

if __name__ == "__main__":
    print("Packet Generator Ready.")
