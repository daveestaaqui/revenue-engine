"""
Surplus Docket — High-DA Directory Citation Engine
Manages, audits, and generates submission profiles for 45+ top-tier LegalTech,
B2B SaaS, and business intelligence directory citations.
"""

import csv
from pathlib import Path
from typing import Dict, List, Any

DEFAULT_REGISTRY_PATH = Path(__file__).parent / "citation_registry.csv"

COMPANY_PROFILE = {
    "name": "Surplus Docket",
    "legal_name": "Surplus Docket LLC",
    "tagline": "Real-Time Court Registry Intelligence for Foreclosure Surplus Recovery",
    "short_description": (
        "Surplus Docket is a legal intelligence platform delivering automated court registry feeds, "
        "junior lien title scrubbing, and statutory deadline tracking for surplus funds and tax deed recovery attorneys."
    ),
    "long_description": (
        "Surplus Docket modernizes foreclosure surplus recovery for law firms. The platform ingests real-time "
        "court docket and excess proceeds registry records across Florida, Texas, California, Georgia, North Carolina, "
        "and Tennessee. By combining automated municipal and mortgage lien scrubbing with statutory deadline calculations "
        "(Florida § 197.582, Texas § 34.04, California § 4675), Surplus Docket empowers attorneys to surface unencumbered "
        "court registry inventory within hours of sale confirmation without manual courthouse ledger research."
    ),
    "website_url": "https://surplusdocket.com",
    "embed_url": "https://surplusdocket.com/embed/",
    "data_feed_url": "https://surplusdocket.com/data",
    "resource_guide_url": "https://surplusdocket.com/resources/homeowner-surplus-guide",
    "categories": ["LegalTech", "Legal Practice Software", "Real Estate Intelligence", "Court Docket Research"],
    "keywords": [
        "tax deed surplus", "excess proceeds", "foreclosure surplus", "court registry feeds",
        "legal intelligence", "junior lien title scrub", "probate asset recovery", "Tyler v. Hennepin County"
    ],
    "pricing_model": "Professional SaaS / Monthly Subscription ($249/mo)",
    "contact_email": "press@surplusdocket.com"
}


def load_citations(registry_path: Path = DEFAULT_REGISTRY_PATH) -> List[Dict[str, Any]]:
    """Loads all directory citations from CSV."""
    if not registry_path.exists():
        return []
    
    citations = []
    with open(registry_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            citations.append({
                "name": row["name"],
                "category": row["category"],
                "da": int(row["da"]) if row["da"].isdigit() else 50,
                "url": row["url"],
                "submission_url": row["submission_url"],
                "status": row.get("status", "READY_FOR_SUBMISSION"),
                "anchor_target": row.get("anchor_target", "Surplus Docket Legal Intelligence")
            })
    return citations


def get_citation_metrics(citations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculates summary statistics across citation inventory."""
    if not citations:
        return {
            "total_directories": 0,
            "average_da": 0,
            "da_80_plus": 0,
            "legal_specific": 0,
            "status_counts": {}
        }
        
    total = len(citations)
    avg_da = round(sum(c["da"] for c in citations) / total, 1)
    da_80_plus = sum(1 for c in citations if c["da"] >= 80)
    legal_specific = sum(1 for c in citations if c["category"] in ("LegalTech", "Legal"))
    
    status_counts = {}
    for c in citations:
        st = c["status"]
        status_counts[st] = status_counts.get(st, 0) + 1
        
    return {
        "total_directories": total,
        "average_da": avg_da,
        "da_80_plus": da_80_plus,
        "legal_specific": legal_specific,
        "status_counts": status_counts
    }


def generate_submission_packet(citation: Dict[str, Any]) -> str:
    """Generates a standardized submission packet for an operator or automation."""
    return f"""
============================================================
DIRECTORY SUBMISSION PROFILE: {citation['name']}
Target URL: {citation['submission_url']}
Category: {citation['category']} | Domain Authority: DA {citation['da']}
Target Anchor: {citation['anchor_target']}
============================================================

Entity Name: {COMPANY_PROFILE['name']}
Official URL: {COMPANY_PROFILE['website_url']}
Tagline: {COMPANY_PROFILE['tagline']}

Short Summary:
{COMPANY_PROFILE['short_description']}

Full Profile Description:
{COMPANY_PROFILE['long_description']}

Primary Reference Links:
- Embed Tools: {COMPANY_PROFILE['embed_url']}
- Court Registry Data: {COMPANY_PROFILE['data_feed_url']}
- Public Educational Guide: {COMPANY_PROFILE['resource_guide_url']}

Keywords: {', '.join(COMPANY_PROFILE['keywords'])}
Support Email: {COMPANY_PROFILE['contact_email']}
"""


def export_markdown_summary(registry_path: Path = DEFAULT_REGISTRY_PATH) -> str:
    """Exports a formatted markdown report of the citation landscape."""
    citations = load_citations(registry_path)
    metrics = get_citation_metrics(citations)
    
    lines = [
        "## 🏛️ High-Authority Directory Citation Registry",
        f"- **Total Curated Directories:** {metrics['total_directories']}",
        f"- **Average Domain Authority:** DA {metrics['average_da']}",
        f"- **Elite Tier (DA 80+):** {metrics['da_80_plus']} authoritative directories",
        f"- **LegalTech / Bar Focused:** {metrics['legal_specific']} niche directories",
        "",
        "| Directory Name | Category | DA | Submission Target | Status |",
        "| :--- | :--- | :---: | :--- | :---: |"
    ]
    
    # Sort by DA descending
    sorted_citations = sorted(citations, key=lambda x: x["da"], reverse=True)
    for c in sorted_citations[:15]: # Show top 15 in summary
        lines.append(f"| **{c['name']}** | {c['category']} | **{c['da']}** | [{c['anchor_target']}]({c['url']}) | `{c['status']}` |")
        
    if len(sorted_citations) > 15:
        lines.append(f"| *...and {len(sorted_citations) - 15} additional directories in registry* | | | | |")
        
    return "\n".join(lines)


if __name__ == "__main__":
    citations = load_citations()
    metrics = get_citation_metrics(citations)
    print(f"Loaded {metrics['total_directories']} directories. Average DA: {metrics['average_da']}. DA 80+: {metrics['da_80_plus']}.")
    print("\nSummary preview:")
    print(export_markdown_summary())
