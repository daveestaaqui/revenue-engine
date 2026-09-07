#!/usr/bin/env python3
"""
Surplus Docket — Design Upgrade with GPT-6 Astra
Queries OpenAI's gpt-6-astra for a subtle, institutional design upgrade across
the Surplus Docket public record intelligence platform.
"""

import os
import sys
import json
import urllib.request
import urllib.error

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-6-astra"

PROMPT = """
You are Astrid (GPT-6 Astra), Principal Design Architect & Frontend Engineer for Surplus Docket (https://surplusdocket.com).
Surplus Docket is the premier daily public records intelligence platform indexing tax deed surplus and court registry excess proceeds across Florida, Texas, Georgia, California, North Carolina, and Tennessee for licensed recovery attorneys, real estate litigators, and probate counsel.

Current Design System Context:
- Typography: Inter (body), Plus Jakarta Sans (headings).
- Colors: Prussian Navy (#1b365d, #102238, #0c1827), Relief Olive Green (#4c6d48, #365134, #edf3ec), Deckle Paper Canvas (#f8f8f4), Subtle Gold (#f59e0b).
- Audience: Senior attorneys, law firm partners, probate litigators, institutional asset recovery practices.
- Zero hype, zero guru aesthetics, 100% institutional authority and trust.

Task: Provide a "Subtle Design Upgrade" specification and concrete CSS / component styling enhancements to elevate the visual prestige, polish, readability, and responsiveness of the platform.

Specifically provide:
1. DESIGN PHILOSOPHY & REFINEMENT SPEC:
   - What subtle adjustments elevate this from a good tech site to an elite, institutional-grade legal research terminal (Bloomberg Law / LexisNexis / Carta caliber)?
   - Typography tuning (tabular nums for currency/case numbers, optical kerning, line-height balance).
   - Elevated elevation system (ambient occlusion + directional key light shadows, delicate 1px borders).
   - Micro-interaction polish (transitions, button states, card hover lift, focus rings).

2. GLOBAL CSS UTILITIES & TAILWIND EXTENSIONS:
   - Provide ready-to-inject CSS classes / style block updates:
     - .tabular-nums for all surplus amounts and case numbers.
     - .card-institutional: Subtle, prestige card styling with ambient shadow and 1px border.
     - .card-interactive: Tactile hover elevation (-1px translate, subtle border glow).
     - .badge-statutory: Refined pill badges with pulsing or static status indicators.
     - .table-terminal: Clean, Bloomberg/court-docket grade table formatting with sticky headers and zebra striping.
     - Custom scrollbar styling for docket preview tables.

3. CONCRETE COMPONENT ENHANCEMENTS:
   - Give the exact HTML/CSS enhancements for:
     a) Primary Navigation Header (frosted glass, refined border).
     b) Live Docket / Case Dossier Preview Cards (subtle borders, tabular numbers, clear visual hierarchy).
     c) Pricing Cards & Comparison Matrix (refined highlight on the 6-State Suite tier).
     d) Practitioner Toolkit Callout sections.

Be concise, precise, and provide production-ready HTML/CSS.
"""

def main():
    if not OPENAI_API_KEY:
        print("[!] ERROR: OPENAI_API_KEY is not set.")
        sys.exit(1)

    print(f"[*] Querying {MODEL} for subtle design upgrade specifications...")
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

    out_file = os.path.join(os.path.dirname(__file__), "..", "output", "gpt6_design_upgrade.md")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)

    with urllib.request.urlopen(req, timeout=180) as response, open(out_file, "w", encoding="utf-8") as f_out:
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

    print(f"\n[+] Design upgrade specifications saved to: {out_file}")

if __name__ == "__main__":
    main()
