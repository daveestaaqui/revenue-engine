#!/usr/bin/env python3
"""
Surplus Docket — Astrid (GPT-6 Astra) Front Page Flow & Architecture Optimizer
==============================================================================
Consults Astrid (gpt-6-astra) to analyze and optimize the UX, conversion arc,
and section sequence of the Surplus Docket homepage (site/index.html).
"""

import os
import sys
import json
import urllib.request
import urllib.error

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-6-astra"

PROMPT = """
You are Astrid (GPT-6 Astra), Chief Commercial Strategist and Principal Systems Architect for Surplus Docket (https://surplusdocket.com).

The USER has explicitly asked:
"Can Astrid make the flow of the front page better?"

CURRENT HOMEPAGE STRUCTURE (site/index.html):
1. Top Navigation: Logo, Live Docket link, Methodology, REST API, Pricing, Subscriber Portal (Stripe billing login), 7-Day Trial CTA ($0 Today).
2. Hero Section (#overview):
   - H1: "Public-Record Intelligence for Surplus Proceeds Counsel"
   - Subhead: "Review indexed tax deed surplus and court-registry excess proceeds across Florida, Texas, Georgia, California, North Carolina, and Tennessee—with source-linked records organized for attorney review."
   - CTAs: "Start 7-Day Trial" ($0 today, $249/mo Day 8) and "View Live Docket ↓".
   - 6-State jurisdiction filter pills (FL, TX, GA, NC, TN, CA).
3. Data Pipeline Specifications Bar:
   - 7:00 AM EST Mon–Fri Court Delivery | Multi-State (Tri-State & 6-State) | CSV & Excel Multi-Format + REST API | 100% Public Clerk & Court Records.
4. Live Public Docket Preview (#live-docket):
   - Interactive search, state filter, minimum amount filter, "Sample CSV" download, and 10 verified sample dockets with direct county clerk verification links.
5. Senior-Lien Screening Benchmark (Side-by-side comparison):
   - Left: Unfiltered County Record (Raw Clerk Excess Ledger, underwater with 1st mortgage and code enforcement).
   - Right: Surplus Docket Scrubbed Equity Record (Verified Docket, liens satisfied, clean equity).
6. Statutory Compliance Toolkit Quick Banner:
   - "Court Motions, Retainers & Filing Checklists" with download link and link to /practitioner-toolkit.html.
7. Statutory Fee & Deadline Calculator (#calculator):
   - Interactive calculator with state statutory selector (FL, TX, GA, NC, TN, CA), sale date, surplus balance, fee cap output, filing window, deadline, and lien waterfall.
8. What You Get / Core Features (#features):
   - 3 Cards: 7:00 AM EST Morning Feed, Lien & Mortgage Scrubbing, REST API & CRM Sync.
9. Monitored Judicial Jurisdictions (#coverage):
   - 6-State cards (FL, TX, GA, NC, TN, CA) detailing county coverage and statutes + Official County Clerk & Court Registry Directory.
10. Competitive Advantage & Market Comparison Matrix:
    - Table comparing Surplus Docket vs Raw Lead Sellers / PDFs vs Generic Real Estate Tools.
11. Practice Economics & Fee Estimator (#roi-calculator):
    - Second calculator with slider for monthly claim volume (1 to 5), average balance, fee rate, projecting monthly and annual gross legal fees.
12. Tyler v. Hennepin County Supreme Court Catalyst:
    - 9-0 Unanimous SCOTUS decision card explaining Takings Clause and $8B+ unlocked nationwide.
13. Pricing Section (#pricing):
    - Monthly vs Annual toggle (Save 20% / 2 Months Free).
    - Tri-State Core Feed: $249/mo ($2,490/yr) - 7-Day Evaluation ($0 Today).
    - National 6-State + REST API: $449/mo ($4,490/yr).
    - Trust badges: Stripe Verified Billing, 256-Bit SSL, Daily Integrity Checks, PCI-DSS Level 1.
14. Frequently Asked Questions (#faq):
    - 5 Collapsible/expanded FAQ cards.
15. Compliance & Disclaimers (#compliance):
    - 4 Cards: Public Records Aggregation, No Legal Advice, FCRA Notice, Algorithmic Benchmarks.
16. Comprehensive Footer:
    - Practice hubs, state hubs, documentation, API, compliance, copyright.

RECENT CAPABILITIES THAT NEED INTEGRATION:
- 3 Dedicated Practice-Group Landing Pages:
  1. /for/tax-sale-litigation.html (Fla. Stat. § 197.582, Tex. Tax Code § 34.04, Cal. Rev. & Tax Code § 4675, Tyler v. Hennepin)
  2. /for/probate-estate-surplus.html (Deceased owners, Letters of Administration, Summary Administration, Heir research)
  3. /for/mortgage-foreclosure.html (Judicial foreclosure surplus, Fla. Stat. §§ 45.031–45.033, Junior lien priority)
- Astrid's Core Positioning Directive:
  "Surplus Docket should not compete on the promise that AI 'finds money' or 'determines lien priority.' It should compete on a more defensible proposition: Relevant records. Inspectable sources. Explicit uncertainty. Faster attorney review."

YOUR TASK AS ASTRID:
1. Conduct a rigorous, critical review of the current flow of site/index.html. Where does an attorney get confused, distracted, or lose trust?
2. Identify friction points and redundancies (e.g. duplicate calculators, misplaced narrative elements, missing practice routing).
3. Architect the OPTIMAL Narrative & Conversion Arc for the front page:
   - Provide the exact recommended order of sections from top to bottom.
   - Explain the psychological and legal rationale for why each section belongs in that exact spot.
4. Detail specific concrete changes to implement:
   - Exactly how to unify or streamline the calculators into one authoritative tool without speculative "get rich" ROI projections.
   - Exactly how to showcase the 3 practice-group pathways early in the flow.
   - Where Tyler v. Hennepin belongs to establish legal macro-credibility.
   - How to tighten the transition from evidence (docket preview) to understanding (methodology/screening) to action (pricing & trial).
5. Provide the exact component-level specifications and suggested micro-copy for the improved flow.

Format your response in crisp, executive Markdown.
"""


def main():
    if not OPENAI_API_KEY:
        print("[!] Error: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Invoking Astrid ({MODEL}) for front page flow & architecture optimization...")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Astrid, Chief Commercial Strategist and Principal Systems Architect. "
                    "You provide exceptionally rigorous, high-authority, and conversion-optimized "
                    "architectural direction for legal technology platforms."
                ),
            },
            {
                "role": "user",
                "content": PROMPT,
            },
        ],
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]

            output_file = os.path.join(
                os.path.dirname(__file__),
                "../output/astrid_front_page_flow_optimization.md",
            )
            output_file = os.path.abspath(output_file)
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"[+] Successfully saved Astrid front page flow architecture to {output_file}")
            print("\n--- ASTRID ARCHITECTURE PREVIEW ---\n")
            lines = content.strip().split("\n")
            print("\n".join(lines[:45]))
            if len(lines) > 45:
                print(f"\n... [{len(lines) - 45} more lines generated]")

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"[!] OpenAI API HTTP Error {e.code}: {e.reason}\n{error_body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[!] Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
