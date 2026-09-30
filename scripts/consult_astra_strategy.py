#!/usr/bin/env python3
"""
Consult GPT-4o (Astra) for a targeted, zero-waste strategic plan:
1. Website accuracy & 100% delivery alignment (zero-refund guarantee).
2. Distributing & embedding available tools (calculators, badges, toolkits) for high-DA backlinks.
3. Expanded link building & high-conviction legal/tech directory strategy.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "output" / "astra_strategic_execution_plan.md"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-4o"

SYSTEM_PROMPT = """You are Astra, Principal LegalTech Architect and SaaS Systems Auditor for Surplus Docket (https://surplusdocket.com).
Your goal is to provide a concise, rigorous, and highly actionable execution plan focused on three critical business objectives:
1. WEBSITE ACCURACY & ZERO REFUND RISK: Ensure everything on the website is completely accurate, verifiable, and strictly delivered to subscribers so nobody has cause for a refund.
2. FREE TOOL PROMOTION & EMBED EXPANSION: Leverage our interactive tools (Statutory Surplus Calculator widget at /embed/surplus-calculator.html, Practitioner Toolkit at /practitioner-toolkit.html, Clio/Filevine CRM export formats, statutory rule registries) to earn high-authority backlinks.
3. HIGH-QUALITY LINK BUILDING & DIRECTORY EXPANSION: Recommend high-DA legal tech directories, bar association resource hubs, and syndication pathways that yield real SEO and referral value.

Be direct, pragmatic, and specific. Focus on concrete execution steps."""

USER_PROMPT = """Here is our current platform context:
- Product: Surplus Docket (court surplus registry intelligence for licensed legal counsel across FL, TX, GA, CA, NC, TN).
- Core Offer: Tri-State Core Feed ($249/mo, 7-day free trial), Six-State National Feed ($449/mo), and Single-County Pilot Dossier ($49 one-time).
- Deliverables: Daily Mon-Fri 7:00 AM ET morning dispatch with CSV and Excel attachments pre-scrubbed for senior liens; REST API endpoints (/api/v1/); legal petitory dossier templates.
- Available Assets & Tools:
  1. Interactive Statutory Surplus & Finder Fee Calculator (`/embed/surplus-calculator.html`) with embed codes and badge widgets (`/embed/index.html`).
  2. Practitioner Toolkit with statutory claim forms for FL (§ 197.582 & § 45.032), TX (§ 34.04), GA (§ 48-4-5), CA (§ 4675) at `/practitioner-toolkit.html`.
  3. Pre-formatted CRM Intake exports: Clio_Matter_Import.csv, Filevine_Lead_Import.csv.
  4. 26 county landing pages (Miami-Dade, Palm Beach, Broward, Harris, Dallas, Fulton, Cobb, Los Angeles, etc.).
  5. 75 curated directories registry in `marketing/link_building/citation_registry.csv`.

Deliver a structured execution plan covering:
1. Exact website copy & delivery audit checkpoints to eliminate any possible refund trigger (what must be matched in the daily feed, onboarding emails, and portal).
2. How to package and distribute our interactive tools (calculator, toolkit, badges) to maximize organic backlinks from legal blogs, law school clinics, and legaltech blogs.
3. 5-7 highest-impact link building targets and syndication plays we should execute immediately.
4. Top 3 highest-priority execution items for today."""

def main():
    if not OPENAI_API_KEY:
        print("[!] ERROR: OPENAI_API_KEY is not set.")
        sys.exit(1)

    print(f"[*] Consulting Astra ({MODEL})...")
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT}
        ],
        "temperature": 0.3,
        "max_tokens": 2000
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content = res_data["choices"][0]["message"]["content"]
            usage = res_data.get("usage", {})
            print(f"[✓] Received response from Astra. Tokens used: {usage.get('total_tokens', 'N/A')}")
            
            OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT_FILE.write_text(content, encoding="utf-8")
            print(f"[✓] Plan saved to: {OUTPUT_FILE}")
            print("\n" + "=" * 60)
            print(content[:600] + "...\n")
            print("=" * 60)
            return content
    except Exception as e:
        print(f"[!] Error querying Astra: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
