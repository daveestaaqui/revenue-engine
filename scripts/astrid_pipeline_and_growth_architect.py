#!/usr/bin/env python3
"""
Surplus Docket — Astrid (GPT-6 Astra) Pipeline, Content & Outreach Architecture
==============================================================================
Invokes Astrid (gpt-6-astra) to architect:
1. High-Converting Attorney Outreach Framework (Personalized practice-area messaging for 1,373 verified firms)
2. Authoritative Legal Content & Blog Strategy (SEO, E-E-A-T, statutory breakdown)
3. National Legal Media & Digital PR Press Release Syndication
4. High-Yield Pipeline Expansion & Conversion Mechanics
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

Surplus Docket has just successfully implemented:
- Transitioned to Google AI (Gemini 1.5 Flash) as primary AI engine (with OpenAI as secondary fallback).
- Gated REST API engine ($249 Tri-State vs $449 6-State + API).
- 3 Dedicated Practice-Group Landing Pages:
  1. /for/tax-sale-litigation.html (Fla. Stat. § 197.582, Tex. Tax Code § 34.04, Cal. Rev. & Tax Code § 4675, Tyler v. Hennepin)
  2. /for/probate-estate-surplus.html (Deceased owners, Letters of Administration, Summary Administration, Heir research)
  3. /for/mortgage-foreclosure.html (Judicial foreclosure surplus, Fla. Stat. § 45.032, 60-day claim window, Junior lien priority)
- Bounded Autonomous Sentinel and Preliminary Lien Screening Engine.
- Expanded pipeline: 1,373 verified, active law practices across FL (423), TX (291), CA (222), GA (166), NC (153), and TN (118).

USER DIRECTIVE:
Deliver a comprehensive, implementation-ready master plan and copy specifications to make every element of the platform maximally effective:

1. HIGH-CONVERTING ATTORNEY OUTREACH UPGRADE:
   - Provide 3 distinct, highly tailored email sequences (Subject lines, opening hooks, pain points, data proof, and non-salesy calls-to-action) matching our 3 practice areas:
     A. Tax Sale & Excess Proceeds Litigators -> Directing to /for/tax-sale-litigation.html
     B. Probate & Estate Planning Litigators -> Directing to /for/probate-estate-surplus.html
     C. Mortgage Foreclosure & Distressed Real Estate Litigators -> Directing to /for/mortgage-foreclosure.html
   - Detail the deliverability rules: MX validation, warmup pacing (24/day), eliminating spam triggers, Bar ethics compliance (Florida Bar Rule 4-7.18, Texas Rule 7.03, etc.), and UPL disclaimers.

2. HIGH-AUTHORITY LEGAL BLOG & CONTENT ENGINE:
   - Provide 4 full, authoritative article specifications that establish undeniable legal authority:
     1. Georgia Tax Sale Excess Funds (O.C.G.A. § 48-4-5) & Superior Court Interpleader
     2. California Tax-Defaulted Property Excess Proceeds (Cal. Rev. & Tax Code § 4675) & 1-Year Limitation
     3. Probate Surplus Recovery: Letters of Administration & Heirship Petitions
     4. Mortgage Foreclosure Surplus vs. Tax Deed Surplus: Procedural & Priority Distinctions
   - For each article, provide key statutory sections, procedural pitfalls, practitioner takeaways, and conversion bridges to our daily feeds.

3. EFFECTIVE PRESS RELEASE & MEDIA SYNDICATION SYSTEM:
   - Provide 2 institutional, newswire-grade press releases for national legal syndication (Law360, PR Newswire, EIN Presswire):
     1. Multi-State Expansion to 6 Jurisdictions Surpassing $3.2M in Verified Surplus Funds.
     2. Launch of Upstream Lien Priority Screening and Chronological Evidence Graph Engine.

4. PIPELINE EXPANSION & LEAD CONVERSION ENHANCEMENTS:
   - Recommend next-phase enhancements to maximize customer lifetime value (LTV), retain subscribers, and convert 7-day trial users to annual commitments.

Format your response in crisp, executive Markdown.
"""

def main():
    if not OPENAI_API_KEY:
        print("[!] ERROR: OPENAI_API_KEY is not set.")
        sys.exit(1)

    print(f"[*] Tasking Astrid ({MODEL}) with Pipeline, Outreach & Content Architecture...")
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": PROMPT}
        ],
        "stream": True
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
    )

    out_file = os.path.join(os.path.dirname(__file__), "..", "output", "astrid_pipeline_growth_blueprint.md")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)

    try:
        with urllib.request.urlopen(req, timeout=600) as response, open(out_file, "w", encoding="utf-8") as f_out:
            for line in response:
                line_str = line.decode("utf-8").strip()
                if not line_str.startswith("data: "):
                    continue
                data_str = line_str[6:]
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta:
                        sys.stdout.write(delta)
                        sys.stdout.flush()
                        f_out.write(delta)
                except json.JSONDecodeError:
                    continue
        print(f"\n\n[+] Successfully saved Astrid growth blueprint to {out_file}")
    except Exception as e:
        print(f"[!] API call failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
