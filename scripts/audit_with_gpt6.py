#!/usr/bin/env python3
"""
Surplus Docket — Autonomous System Audit using GPT-6 Astra
Queries OpenAI's GPT-6 Astra model to conduct an architectural, security,
and conversion audit of the Surplus Docket revenue engine.
"""

import os
import sys
import json
import urllib.request
import urllib.error

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-6-astra"

AUDIT_PROMPT = """
You are an expert Principal LegalTech Architect and SaaS Systems Auditor.
Conduct a comprehensive review of the Surplus Docket revenue engine (https://surplusdocket.com):

1. Architecture:
   - Python-based county surplus scraping & statutory civil procedure calculators (FL, TX, GA, CA, NC, TN).
   - Real-time REST API endpoints (/api/v1/leads, OpenAPI schema) for case management ingestion.
   - 100% serverless GitHub Actions automation (0 local daemons) for inbox triage and lead qualification.
   - Dual-tier pricing structure (Tri-State Core Feed at $249/mo or $2,388/yr; 6-State + REST API at $449/mo or $4,188/yr).

2. Evaluation Goals:
   - Analyze potential conversion bottlenecks for asset recovery attorneys.
   - Evaluate statutory calculation compliance safeguards (FRCP 6(a), local rules).
   - Review autonomous email triage circuit-breakers.
   - Provide concrete, high-impact architectural enhancements.
"""

def run_audit():
    if not OPENAI_API_KEY:
        print("[!] ERROR: OPENAI_API_KEY environment variable is not set.")
        sys.exit(1)

    print(f"[*] Connecting to OpenAI API with model: {MODEL}...")
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": "You are a Principal LegalTech Systems Architect and SaaS Systems Auditor.\n\n" + AUDIT_PROMPT}
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

    out_path = os.path.join(os.path.dirname(__file__), "..", "output", "gpt6_audit_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    print("\n" + "=" * 60)
    print(" 🌟 STREAMING GPT-6 ASTRA ARCHITECTURAL AUDIT REPORT")
    print("=" * 60 + "\n")

    try:
        with urllib.request.urlopen(req, timeout=120) as response, open(out_path, "w", encoding="utf-8") as f_out:
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
        print("\n\n" + "=" * 60)
        print(f" Audit report saved to: {out_path}")
        print("=" * 60)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"[!] HTTP Error {e.code}: {error_body}")
        if e.code == 429 and "credit_balance_exhausted" in error_body:
            print("\n[!] Notice: Your OpenAI account has exhausted its prepaid credits.")
            print("[!] Please add credits at: https://platform.openai.com/settings/organization/billing/")
    except Exception as e:
        print(f"[!] Unexpected error: {e}")

if __name__ == "__main__":
    run_audit()
