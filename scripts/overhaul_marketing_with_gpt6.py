#!/usr/bin/env python3
"""
Surplus Docket — Overhaul Marketing, Link Building, and Outreach with GPT-6 Astra
Prompts GPT-6 Astra to generate institutional legaltech marketing, link building,
and attorney outreach assets reflecting the evidence-backed positioning.
"""

import os
import sys
import json
import urllib.request
import urllib.error

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-6-astra"

PROMPT = """
You are GPT-6 Astra, Principal LegalTech Strategist and CMO for Surplus Docket (https://surplusdocket.com).
Overhaul the marketing, link building, and attorney outreach strategy to establish Surplus Docket as the authoritative institutional court surplus data standard for law firms:

1. Institutional LegalTech Link-Building & Digital PR Blueprint:
   - High-authority legaltech directories, state bar legal tech portals (FL, TX, GA, CA, NC, TN), CLE providers, and court technology publications.
   - White-hat editorial pitch angles establishing Surplus Docket as the counter to predatory third-party "finders" (Tyler v. Hennepin compliance, senior lien scrubbing, attorney-led recovery).

2. High-Converting Attorney Outreach Master Template:
   - A concise, peer-level email template for Managing Partners and Real Estate Litigation / Probate Practice Group Leaders.
   - Highlights: Verifiable court record provenance, automated senior lien elimination, FRCP/State civil procedure deadline calculations, and 1-click Clio/Filevine CSV intake integration.
   - Zero hype, zero callback offers, 100% self-serve trial positioning.

Format the output cleanly with file markers:
=== FILE: marketing/link_building/institutional_pr_blueprint.md ===
...
=== FILE: marketing/pitches/attorney_practice_group_outreach.md ===
...
"""

def run():
    if not OPENAI_API_KEY:
        print("[!] ERROR: OPENAI_API_KEY environment variable is not set.")
        sys.exit(1)

    print(f"[*] Prompting {MODEL} to overhaul marketing & link building...")
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

    out_file = os.path.join(os.path.dirname(__file__), "..", "output", "astra_marketing_overhaul.md")
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

    print(f"\n[+] Marketing overhaul generated and saved to: {out_file}")

if __name__ == "__main__":
    run()
