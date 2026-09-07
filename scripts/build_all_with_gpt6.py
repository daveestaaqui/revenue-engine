#!/usr/bin/env python3
"""
Surplus Docket — Build Security Firewall, Legal Rules Registry & Webhook Dispatcher
Prompts GPT-6 Astra to generate:
1. outreach/email_sentinel_firewall.py (Prompt injection defense & circuit breakers)
2. portal/legal_rules_registry.py (Canonical 6-state statutory truth table & calculation traces)
3. portal/webhook_dispatcher.py (HMAC-SHA256 signed CRM webhook delivery)
4. tests/test_astra_security_and_registry.py (Comprehensive unit tests)
"""

import os
import sys
import json
import urllib.request
import urllib.error

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-6-astra"

PROMPT = """
You are GPT-6 Astra, Principal LegalTech Architect & Security Engineer for Surplus Docket (https://surplusdocket.com).
Generate production-ready code for the following 3 architectural components and their tests:

1. `outreach/email_sentinel_firewall.py`:
   - Adversarial prompt injection & jailbreak detection (defends against 'ignore previous instructions', attempts to extract API keys/prompts, fake discounts, legal advice demands, unauthorized representation claims).
   - Inbound email circuit breakers: loop detection (auto-replies, mailer-daemon, bounces), sender rate-limiting, and dangerous attachment/keyword escalation.
   - Clean sanitize_inbound_message(sender, subject, body) function returning (is_safe, category, sanitized_body, reason).

2. `portal/legal_rules_registry.py`:
   - Canonical versioned legal rules registry for FL, TX, GA, CA, NC, and TN.
   - Maps statutory citations (Fla. Stat. § 197.582, Tex. Tax Code § 34.04, O.C.G.A. § 48-4-5, Cal. Rev. & Tax. Code § 4675, N.C. Gen. Stat. § 105-374, Tenn. Code Ann. § 67-5-2501).
   - Functions: get_rule(state, proceeding_type), calculate_statutory_deadline(state, sale_date, notice_date, confirmation_date) returning (deadline_date, governing_statute, deadline_basis, is_valid, warning).
   - Returns 'Insufficient facts to calculate — attorney review required' if required trigger facts are missing.

3. `portal/webhook_dispatcher.py`:
   - Secure webhook event delivery with HMAC-SHA256 signature (X-SurplusDocket-Signature).
   - Payload formatting for CRM endpoints (Clio / Filevine / Zapier / custom).
   - Idempotency keying, timestamp verification (anti-replay), and structured delivery payload.

4. `tests/test_astra_security_and_registry.py`:
   - Exhaustive unit tests testing prompt injection rejection, loop breaking, statutory deadline calculations, missing-fact handling, and webhook HMAC signature verification.

Format output with clear markers:
=== FILE: outreach/email_sentinel_firewall.py ===
...
=== FILE: portal/legal_rules_registry.py ===
...
=== FILE: portal/webhook_dispatcher.py ===
...
=== FILE: tests/test_astra_security_and_registry.py ===
...
"""

def generate():
    if not OPENAI_API_KEY:
        print("[!] ERROR: OPENAI_API_KEY environment variable is not set.")
        sys.exit(1)

    print(f"[*] Prompting {MODEL} to generate full security & legal engine suite...")
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

    out_file = os.path.join(os.path.dirname(__file__), "..", "output", "astra_security_and_registry.md")
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

    print(f"\n[+] Generated files saved to: {out_file}")

if __name__ == "__main__":
    generate()
