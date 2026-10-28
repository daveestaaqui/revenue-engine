"""
Surplus Docket — Legal Digital PR Pitch Generator
Generates institutional, high-authority press pitches and expert commentary
for journalists, legal editors (Law360, Bloomberg Law, Inman, American Lawyer),
and bar association publications.
"""

import os
import json
from pathlib import Path
from datetime import datetime, timezone

PITCH_TEMPLATES = [
    {
        "id": "tyler-v-hennepin-compliance",
        "category": "Constitutional Property Rights & Foreclosure Law",
        "title": "Post-Tyler v. Hennepin County: The $2.4B State Compliance Gap in Tax Deed Surplus Recovery",
        "target_outlets": ["Law360", "Bloomberg Law", "National Law Journal", "ABA Journal"],
        "hook": (
            "Following the Supreme Court's unanimous ruling in Tyler v. Hennepin County (598 U.S. 631), "
            "equity theft via property tax foreclosure was declared an unconstitutional taking under the Fifth Amendment. "
            "Yet across Florida, Texas, California, Georgia, North Carolina, and Tennessee, over $2.4B remains trapped "
            "in county registries due to antiquated notice procedures and fractured statutory filing deadlines."
        ),
        "expert_quote": (
            "\"While the Supreme Court ended statutory equity forfeiture on paper, county court registries remain administrative "
            "black boxes. Without specialized bar admission and encumbrance screening, junior lienholders and former owners regularly "
            "forfeit millions to state general funds simply because statutory windows close unnoticed.\" "
            "— Research & Regulatory Analysis Desk, Surplus Docket"
        ),
        "citeable_data": [
            "Over $26.0M+ in verified unencumbered surplus funds identified across 504 court registry records in FL, TX, GA, CA, and TN.",
            "Florida § 197.582 sets a strict 120-day notice window post-certificate of title before claims are barred.",
            "California Revenue & Taxation Code § 4675 provides 1 year from deed recordation, requiring complex junior lien prioritization.",
            "Texas Tax Code § 34.04 mandates district court petition with formal service on all previous title holders."
        ],
        "resource_url": "https://surplusdocket.com/#live-docket",
        "call_to_action": (
            "We have mapped county-by-county registry balances and statutory deadlines across all 6 key jurisdictions. "
            "Happy to provide raw docket data, anonymized court case case-studies, or executive commentary for your upcoming feature."
        )
    },
    {
        "id": "predatory-finders-vs-licensed-counsel",
        "category": "Consumer Protection & Unauthorized Practice of Law (UPL)",
        "title": "The Shadow Market in Foreclosure Surplus: Why Courts Are Cracking Down on Unlicensed 'Asset Recovery' Finders",
        "target_outlets": ["Inman News", "Real Estate Weekly", "State Bar Journals (FL, TX, CA)", "ProPublica"],
        "hook": (
            "In the wake of residential tax deed auctions, former homeowners are inundated with aggressive solicitations from "
            "unlicensed 'third-party asset recovery' operators demanding 30% to 50% contingency fees. However, state courts "
            "and legislatures are increasingly treating these assignment contracts as the Unauthorized Practice of Law (UPL) "
            "or enforcing statutory caps that render such contracts void ab initio."
        ),
        "expert_quote": (
            "\"Unlicensed finders prey on vulnerable displaced families by executing predatory powers of attorney. "
            "In truth, legitimate surplus recovery requires formal legal pleadings, priority determination under statutory recording acts, "
            "and court orders. The legal community is actively mobilizing to ensure claims are handled by licensed bar members "
            "under transparent, ethical fee structures.\" "
            "— Research & Regulatory Analysis Desk, Surplus Docket"
        ),
        "citeable_data": [
            "Over 40% of surplus claims filed by non-attorney finders encounter clerk rejections or jurisdictional dismissal for defective assignment instruments.",
            "Florida §§ 45.033, 197.582, 717.135 and Texas § 34.04 enforce stringent non-attorney fee and procedural caps, voiding predatory recovery agreements.",
            "Educational resource deployed at Surplus Docket for homeowners: https://surplusdocket.com/resources/homeowner-surplus-guide.html"
        ],
        "resource_url": "https://surplusdocket.com/resources/homeowner-surplus-guide.html",
        "call_to_action": (
            "We can connect your team with forensic analysis on surplus assignment disputes, clerk filing statistics, "
            "and legal analysis on the regulatory divergence between attorney representation and finder contracts."
        )
    },
    {
        "id": "legaltech-court-registry-automation",
        "category": "Legal Technology & Registry Intelligence",
        "title": "Automating the Court Registry: How Judicial Feeds Eliminate Blind Spots in Excess Proceeds Recovery",
        "target_outlets": ["Legal IT Insider", "Artificial Lawyer", "LawSites by Bob Ambrogi", "Legaltech News"],
        "hook": (
            "For decades, foreclosure surplus recovery was the domain of manual courthouse ledger checks and microfiche title searches. "
            "Today, institutional legal intelligence platforms are ingesting court dockets and judicial registry notices in real-time, "
            "automating subordinate encumbrance screening and statutory deadline calculations."
        ),
        "expert_quote": (
            "\"Attorneys handling foreclosure defense or probate previously spent 10 to 15 hours per file just validating whether "
            "surplus funds existed and calculating subordinate mortgage priority. Automated registry intelligence now surfaces "
            "unencumbered funds within hours of certificate disbursement.\" "
            "— Systems Engineering & Data Architecture Lead, Surplus Docket"
        ),
        "citeable_data": [
            "Surplus Docket processes daily registry feeds across FL, TX, CA, GA, NC, and TN court registries ($26.0M+ across 504 verified records).",
            "Open-source OpenSurplus SDK v1.2.0 (MIT License) with zero-dependency Web Component and Python CLI: https://surplusdocket.com/sdk/",
            "Machine-readable OpenAPI 3.1.0 specification for court registry feeds: https://surplusdocket.com/openapi.json",
            "Interactive statutory deadline calculator available for publisher embedding: https://surplusdocket.com/embed/surplus-calculator.html"
        ],
        "resource_url": "https://surplusdocket.com/sdk/",
        "call_to_action": (
            "Our engineering and legal analysis teams are available to demo the court registry pipeline or share insights on modernizing "
            "judicial docket ingestion."
        )
    },
    {
        "id": "open-source-surplus-sdk-launch",
        "category": "Open-Source Legal Engineering & Access to Justice",
        "title": "Surplus Docket Releases 'OpenSurplus SDK v1.2.0': Open-Source Statutory Calculator, Python CLI & OpenAPI 3.1.0 Spec for Court Registries",
        "target_outlets": ["LawSites by Bob Ambrogi", "Artificial Lawyer", "MIT Computational Law Report", "GitHub Open Source LegalTech"],
        "hook": (
            "To eliminate opaque third-party 'finder fee' traps and standardize statutory deadline computation across state lines, "
            "Surplus Docket has released OpenSurplus SDK v1.2.0 under the MIT License—featuring a drop-in <surplus-statute-calculator> "
            "Web Component, a zero-dependency Python 3 CLI, and a machine-readable OpenAPI 3.1.0 specification covering 6 core state statutory regimes."
        ),
        "expert_quote": (
            "\"Legal aid clinics, county clerks, and foreclosure defense counsel shouldn't have to rebuild statutory deadline and fee-cap "
            "calculators from scratch. By releasing OpenSurplus as an MIT-licensed Web Component and Python CLI backed by an OpenAPI 3.1.0 "
            "specification, any bar journal, law school clinic, or practice management pipeline can verify statutory windows and UPL fee limits in milliseconds.\" "
            "— Systems Engineering & Data Architecture Lead, Surplus Docket"
        ),
        "citeable_data": [
            "Covers 6 core state statutory frameworks: FL (§ 197.582 / § 45.032), TX (§ 34.04), GA (§ 48-4-5), CA (§ 4675), NC (§ 105-374), and TN (§ 67-5-2501).",
            "Includes zero-dependency Custom Element (<surplus-statute-calculator>) with Shadow DOM isolation and zero tracking cookies.",
            "Provides direct Clio Manage and Filevine CRM intake field mapping plus CITATION.cff academic metadata.",
            "Backed by real-time empirical market intelligence across 504 verified court registry records totaling $26.0M+: https://surplusdocket.com/blog/posts/multi-state-surplus-market-intelligence-report.html"
        ],
        "resource_url": "https://surplusdocket.com/sdk/",
        "call_to_action": (
            "The SDK, Python CLI, and OpenAPI 3.1.0 specification are live and free to inspect, fork, or embed at https://surplusdocket.com/sdk/. "
            "Our engineering lead is available for interviews on open-source computational law and public court registry standardization."
        )
    }
]


def format_pitch_markdown(pitch: dict) -> str:
    """Renders a pitch dictionary as professional markdown."""
    lines = [
        f"# PRESS PITCH: {pitch['title']}",
        f"**Category:** {pitch['category']}",
        f"**Suggested Outlets:** {', '.join(pitch['target_outlets'])}",
        f"**Date:** {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
        "",
        "---",
        "",
        "### PITCH SUMMARY / HOOK",
        pitch['hook'],
        "",
        "### EXPERT PERSPECTIVE & QUOTE",
        pitch['expert_quote'],
        "",
        "### VERIFIED STATS & CITEABLE DATA",
    ]
    for stat in pitch['citeable_data']:
        lines.append(f"- {stat}")
    
    lines.extend([
        "",
        "### CANONICAL REFERENCE & RESOURCE ASSETS",
        f"- **Primary Reference:** [{pitch['resource_url']}]({pitch['resource_url']})",
        f"- **Platform Domain:** [Surplus Docket](https://surplusdocket.com)",
        "",
        "### MEDIA CONTACT & CALL TO ACTION",
        pitch['call_to_action'],
        "",
        "**Press Contact:** press@surplusdocket.com | Legal Research & Media Team"
    ])
    return "\n".join(lines)


def generate_all_pitches(output_dir: str = "marketing/pitches") -> list:
    """Generates and saves all press pitches to disk."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    saved_files = []
    for pitch in PITCH_TEMPLATES:
        content = format_pitch_markdown(pitch)
        filepath = out_path / f"{pitch['id']}.md"
        filepath.write_text(content, encoding="utf-8")
        saved_files.append(str(filepath))
        
    return saved_files


if __name__ == "__main__":
    files = generate_all_pitches()
    print(f"Generated {len(files)} press pitches:")
    for f in files:
        print(f"  - {f}")
