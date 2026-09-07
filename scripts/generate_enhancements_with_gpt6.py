#!/usr/bin/env python3
"""
Surplus Docket — Implement P0/P1 Architectural Enhancements with GPT-6 Astra
Prompts GPT-6 Astra to generate the code for:
1. Annotated Evidence-Backed Lead Dossier component
2. County Coverage & Statutory Verification Matrix
3. Clio & Filevine Case Management CSV export generator
"""

import os
import sys
import json
import urllib.request
import urllib.error

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-6-astra"

PROMPT = """
You are GPT-6 Astra, Principal LegalTech Architect for Surplus Docket (https://surplusdocket.com).
Generate production-ready code to implement the P0 and P1 enhancements from your audit report:

1. HTML Component (Tailwind CSS matching the brand navy/green theme):
   - 'Annotated Evidence-Backed Lead Dossier': Demonstrates verifiable evidence chain (Court Record, Docket Number, Gross Surplus, Title/Senior Lien Scrubbing, Governing Statute Citation, Statutory Window, Actionability Score, and Verified Status).
   - 'County Coverage & Statutory Authority Matrix': Clean table of supported counties across FL, TX, GA, NC, TN, and CA with their governing statutory citations (Fla. Stat. § 197.582, Tex. Tax Code § 34.04, O.C.G.A. § 48-4-5, Cal. Rev. & Tax. Code § 4675, N.C. Gen. Stat. § 105-374, Tenn. Code Ann. § 67-5-2501).

2. Python utility `portal/crm_export_engine.py`:
   - Functions `export_to_clio_csv(leads)` and `export_to_filevine_csv(leads)` that map normalized surplus leads into standard Clio Manage and Filevine contact/matter intake CSV columns.

Format the output cleanly with clear file markers like:
=== FILE: site/components/annotated_lead_dossier.html ===
...
=== FILE: portal/crm_export_engine.py ===
...
"""

def generate():
    if not OPENAI_API_KEY:
        print("[!] ERROR: OPENAI_API_KEY environment variable is not set.")
        sys.exit(1)

    print(f"[*] Prompting {MODEL} to generate P0/P1 enhancements...")
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

    out_file = os.path.join(os.path.dirname(__file__), "..", "output", "astra_generated_enhancements.md")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)

    with urllib.request.urlopen(req, timeout=120) as response, open(out_file, "w", encoding="utf-8") as f_out:
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

    print(f"\n[+] Enhancements successfully generated and saved to: {out_file}")

if __name__ == "__main__":
    generate()
