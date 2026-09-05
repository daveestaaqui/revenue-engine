"""
Surplus Docket — Multi-Channel Syndication Publisher
Prepares canonical-attributed, syndication-ready markdown articles for Medium,
Substack, LinkedIn Articles, and Dev.to to capture high-authority referral traffic
and backlink equity without search engine duplicate content penalties.
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict

ARTICLES_TO_SYNDICATE = [
    {
        "slug": "statutory-deadlines-tax-deed-surplus-top-6-states",
        "title": "Navigating Statutory Deadlines in Tax Deed Surplus Recovery: A Six-State Jurisdictional Analysis",
        "canonical_url": "https://surplusdocket.com/blog/statutory-deadlines-tax-deed-surplus",
        "summary": "A comprehensive practitioner breakdown of excess proceeds recovery deadlines across Florida, Texas, California, Georgia, North Carolina, and Tennessee.",
        "tags": ["LegalTech", "Foreclosure", "RealEstateLaw", "Litigation", "CourtDocket"],
        "body": """
### The Jurisdictional Fracture in Excess Proceeds Recovery

Following a property tax foreclosure auction, surplus funds generated beyond the delinquent tax liability are held in the court or county registry. However, the procedures and statutory limitation periods governing their recovery diverge drastically across state lines.

Failure to file within the precise statutory timeframe results in complete forfeiture of the proceeds to the county general fund or state unclaimed property division.

#### 1. Florida (§ 197.582, Fla. Stat.)
Under Florida law, the Clerk of the Circuit Court must issue a formal Notice of Surplus to all persons listed in the tax deed application. All lienholders and former owners have **120 days** from the date of the notice to file a formal claim. Junior lienholders have statutory priority over former owners under Florida Statute § 197.582(3).

#### 2. Texas (§ 34.04, Tex. Tax Code)
In Texas, recovery is strictly judicial. An interested party must file a formal petition in the District Court where the tax judgment was entered within **two years** from the date of the tax foreclosure sale. All former titleholders, taxing units, and recorded lienholders must be formally served.

#### 3. California (§ 4675, Cal. Rev. & Tax. Code)
California provides a strict **one-year** limitation period from the date of the recordation of the tax deed to the purchaser. Claims are submitted to the County Auditor-Controller or Board of Supervisors. Complex priority rules govern senior mortgagees, subordinate lienholders, and former owners under § 4675(e).

#### 4. Georgia (O.C.G.A. § 48-4-5)
In Georgia, the officer conducting the tax sale (Tax Commissioner or Sheriff) distributes proceeds. While claims may be brought within **five years**, conflicting claims are frequently interpleaded into the Superior Court, requiring formal legal counsel to determine lien priority under recording acts.

#### 5. North Carolina (N.C. Gen. Stat. § 105-374)
Surplus proceeds are deposited with the Clerk of Superior Court. Parties with an interest in the real estate must file a special proceeding or motion for disbursement within **two years** of the confirmation of the foreclosure sale.

#### 6. Tennessee (Tenn. Code Ann. § 67-5-2510)
Excess proceeds resulting from a delinquent tax sale are held by the Chancery Court Clerk and Master. Motions for disbursement must be filed within **one year** from the confirmation of the sale, requiring judicial verification of unencumbered title.
"""
    },
    {
        "slug": "post-tyler-hennepin-county-title-scrubbing",
        "title": "Post-Tyler v. Hennepin County: Why Automated Junior Lien Title Scrubbing is Essential for Surplus Recovery",
        "canonical_url": "https://surplusdocket.com/blog/tyler-hennepin-junior-lien-scrubbing",
        "summary": "How automated court registry ingestion and title scrubbing eliminate catastrophic malpractice risks in excess proceeds litigation.",
        "tags": ["LegalTech", "AI", "TitleResearch", "PropertyRights", "LegalInnovation"],
        "body": """
### The Unanimous Mandate of Tyler v. Hennepin County

In *Tyler v. Hennepin County*, 598 U.S. 631 (2023), the United States Supreme Court confirmed that home equity is property protected by the Fifth Amendment's Takings Clause. When governments foreclose and retain excess proceeds above the debt, an unconstitutional taking occurs.

However, while former owners have a protected property right, their recovery is frequently subordinate to intervening recorded liens:
1. First and second mortgages
2. Homeowners association (HOA) assessment liens
3. Federal tax liens (IRS § 7425 redemption rights)
4. State tax warrants and civil judgments

### The Title Scrubbing Bottleneck in Modern Law Practice

Attorneys handling surplus funds often spend dozens of hours reviewing raw courthouse index records to confirm whether a file has unencumbered equity. If an attorney files a claim on behalf of an owner without discovering a senior judgment creditor, the claim will be contested or dismissed, resulting in wasted billable time and potential disciplinary inquiry.

Modern legal intelligence platforms like [Surplus Docket](https://surplusdocket.com) automate this verification pipeline:
- Direct ingestion of county court registries across the country
- Automated docket scrubbing for satisfaction of mortgages and lien releases
- Real-time statutory deadline calculation
- Filtering files to deliver high-equity, unencumbered registry inventory
"""
    }
]


def generate_syndicated_document(article: Dict[str, str], platform: str) -> str:
    """Formats an article for a specific publishing platform with proper canonical link hooks."""
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    
    header = f"""<!--
PLATFORM: {platform.upper()}
TITLE: {article['title']}
CANONICAL_URL: {article['canonical_url']}
DATE: {today}
TAGS: {', '.join(article['tags'])}
-->

# {article['title']}

*Originally published on [Surplus Docket Legal Intelligence]({article['canonical_url']})*

---
"""
    
    footer = f"""
---

### About the Author & Platform
This analysis was authored by the research team at **[Surplus Docket](https://surplusdocket.com)**. Surplus Docket provides real-time court docket intelligence, junior lien title scrubbing, and statutory deadline automation for legal practices in foreclosure defense, probate, and real estate litigation.

- **Interactive Calculator Widget:** [Statutory Surplus Calculator](https://surplusdocket.com/embed/surplus-calculator.html)
- **Public Educational Resource:** [Homeowner's Guide to Foreclosure Surplus](https://surplusdocket.com/resources/homeowner-surplus-guide)
- **Live Court Registry Feeds:** [Surplus Docket Intelligence](https://surplusdocket.com/data)

*Canonical Source: [{article['canonical_url']}]({article['canonical_url']})*
"""
    return header + article['body'].strip() + "\n" + footer


def build_all_syndication_files(output_dir: str = "marketing/syndicate/published") -> List[str]:
    """Builds ready-to-post articles for Medium, Substack, LinkedIn, and Dev.to."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    saved_files = []
    platforms = ["medium", "substack", "linkedin", "dev_to"]
    
    for article in ARTICLES_TO_SYNDICATE:
        for platform in platforms:
            filename = f"{article['slug']}_{platform}.md"
            filepath = out_path / filename
            content = generate_syndicated_document(article, platform)
            filepath.write_text(content, encoding="utf-8")
            saved_files.append(str(filepath))
            
    return saved_files


if __name__ == "__main__":
    files = build_all_syndication_files()
    print(f"Generated {len(files)} syndication articles across Medium, Substack, LinkedIn, and Dev.to:")
    for f in files:
        print(f"  - {f}")
