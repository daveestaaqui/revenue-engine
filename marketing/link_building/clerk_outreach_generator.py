"""
Surplus Docket — County Clerk & Legal Aid Authority Link Outreach Generator
Generates non-commercial, public-interest resource letters for County Clerk of Courts,
Tax Collectors, and Legal Aid organizations across Florida, Texas, California,
Georgia, North Carolina, and Tennessee to earn elite .gov and .org backlinks.
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict

CLERK_TARGETS = [
    {
        "county": "Miami-Dade County",
        "state": "FL",
        "agency": "Clerk of the Court and Comptroller",
        "department": "Tax Deed / Foreclosure Registry Services",
        "page_context": "Tax Deed Surplus Funds & Registry Disclosures",
        "recipient_title": "Tax Deed Department Supervisor / Public Information Officer"
    },
    {
        "county": "Harris County",
        "state": "TX",
        "agency": "Office of the District Clerk",
        "department": "Post-Judgment & Excess Proceeds Registry",
        "page_context": "Tax Foreclosure Excess Proceeds Informational Page",
        "recipient_title": "District Court Registry Director"
    },
    {
        "county": "Los Angeles County",
        "state": "CA",
        "agency": "Treasurer and Tax Collector",
        "department": "Auction & Excess Proceeds Division",
        "page_context": "Public Auction Excess Proceeds Claim Guidance",
        "recipient_title": "Excess Proceeds Claims Administrator"
    },
    {
        "county": "Fulton County",
        "state": "GA",
        "agency": "Fulton County Sheriff & Superior Court Clerk",
        "department": "Tax Sale & Excess Funds Division",
        "page_context": "Tax Sale Excess Funds Public Resource Portal",
        "recipient_title": "Excess Funds Hearing Coordinator"
    },
    {
        "county": "Mecklenburg County",
        "state": "NC",
        "agency": "Clerk of Superior Court",
        "department": "Special Proceedings & Foreclosure Division",
        "page_context": "Foreclosure Surplus Funds Claims Guidelines",
        "recipient_title": "Special Proceedings Division Administrator"
    },
    {
        "county": "Shelby County",
        "state": "TN",
        "agency": "Shelby County Chancery Court Clerk & Master",
        "department": "Delinquent Tax Division",
        "page_context": "Tax Sale Surplus Distribution Information",
        "recipient_title": "Chief Deputy Clerk & Master"
    }
]


def generate_clerk_outreach_letter(target: Dict[str, str]) -> str:
    """Generates an authoritative, public-service letter proposing resource inclusion."""
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    
    return f"""# PUBLIC SERVICE LINK PROPOSAL: CONSUMER SURPLUS PROTECTION RESOURCE

**To:** {target['recipient_title']}  
**Agency:** {target['agency']}, {target['county']}, {target['state']}  
**Department:** {target['department']}  
**Date:** {today}  
**Subject:** Public Education Resource on Property Tax Foreclosure Surplus Funds & Scam Prevention (Ref: {target['county']} Web Portal)

---

Dear {target['recipient_title']},

We are writing from the Public Legal Research Initiative at Surplus Docket. 

In reviewing the public information provided on the **{target['county']} {target['page_context']}** webpage, we commend your department's ongoing efforts to ensure transparency in post-foreclosure excess proceeds administration.

Across {target['state']}, displaced property owners and probate heirs face an increasing volume of aggressive solicitations from unlicensed third-party "asset recovery finders" demanding 30% to 50% contingency fees. Many vulnerable citizens are unaware that they can file directly with your office, or that state statutes limit predatory recovery practices.

To assist taxpayers and support county clerk public education, our legal research group has published an objective, comprehensive, and non-commercial public guide:

**Resource Title:** Homeowner's Guide to Property Tax Auction Surplus Funds & Protecting Your Equity  
**URL:** [https://surplusdocket.com/resources/homeowner-surplus-guide](https://surplusdocket.com/resources/homeowner-surplus-guide)

### Key Public Information Provided in the Guide:
1. **Constitutional Basis:** Clear explanation of *Tyler v. Hennepin County*, 598 U.S. 631 (2023), confirming homeowners' constitutional rights to excess equity under the Fifth Amendment.
2. **Scam Avoidance & Fee Caps:** Explicit warnings alerting homeowners to never sign over deeds or blanket powers of attorney to unlicensed finders, highlighting statutory protections and UPL statutes.
3. **Direct Filing Options:** Instructions encouraging claimants to file directly with the county clerk without incurring finder fees.
4. **Statutory Filing Deadlines:** Exact statutory windows under {target['state']} law and an open-access statutory deadline calculator ([https://surplusdocket.com/embed/surplus-calculator.html](https://surplusdocket.com/embed/surplus-calculator.html)).

### Request for Resource Inclusion
Would your department consider linking to this public guide as a helpful external resource under the **"{target['page_context']}"** section of your official website? 

The resource contains no advertisements, pop-ups, or commercial solicitations, and is maintained solely to protect consumers and facilitate compliant court registry recovery.

Thank you for your dedicated service to the residents of {target['county']}.

Respectfully submitted,

**Public Legal Education Group**  
Surplus Docket  
Website: [https://surplusdocket.com](https://surplusdocket.com)  
Email: public-records@surplusdocket.com  
"""


def generate_all_clerk_letters(output_dir: str = "marketing/clerk_outreach") -> List[str]:
    """Generates outreach letters for all target jurisdictions."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    saved = []
    for target in CLERK_TARGETS:
        filename = f"{target['state'].lower()}_{target['county'].lower().replace(' ', '_')}_clerk_letter.md"
        filepath = out_path / filename
        content = generate_clerk_outreach_letter(target)
        filepath.write_text(content, encoding="utf-8")
        saved.append(str(filepath))
        
    return saved


if __name__ == "__main__":
    files = generate_all_clerk_letters()
    print(f"Generated {len(files)} county clerk outreach letters:")
    for f in files:
        print(f"  - {f}")
