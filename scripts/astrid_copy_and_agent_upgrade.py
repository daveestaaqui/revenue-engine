#!/usr/bin/env python3
"""
Surplus Docket — Copy Critique & Employee Capability Upgrade with GPT-6 Astra
Tasks Astrid (gpt-6-astra) to:
1. Conduct an Agent Critique Stage generating 5 iterations of website copy across
   key conversion surfaces, critiquing each, and selecting the Best of 5.
2. Upgrade employee behaviors & capabilities (Elena Brooks, Aubrey Hayes, etc.)
   for handling inquiries, legal precision, and audio-first voicemail responses.
"""

import os
import sys
import json
import urllib.request
import urllib.error

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-6-astra"

PROMPT = """
You are Astrid (GPT-6 Astra), Principal Legal Copywriter & Autonomous Systems Architect for Surplus Docket (https://surplusdocket.com).
Surplus Docket is the premier daily public records intelligence platform indexing tax deed surplus and court registry excess proceeds across Florida, Texas, Georgia, California, North Carolina, and Tennessee for licensed recovery attorneys, real estate litigators, and probate counsel.

TASK 1: WEBSITE COPY OPTIMIZATION — AGENT CRITIQUE STAGE (BEST OF 5)
Run a rigorous 5-iteration generation & critique stage for the following core website sections:
1. Hero Headline & Sub-headline
2. Senior Lien & Institutional Title Scrubbing Section (The core technical differentiator)
3. Pricing & 7-Day Practice Evaluation Offer Callout
4. Practitioner Toolkit & CRM Sync Section

For each section:
- Generate 5 distinct candidate iterations (Variation A, B, C, D, E).
- Critique each candidate on: Legal Precision, Institutional Authority/Prestige (Bloomberg/Lexis caliber), Clarity, Conversion Velocity, and Bar Compliance (zero hype/guru language).
- Select the clear WINNER (Best of 5) and explain why it won.
- Provide the final production-ready copy ready to be placed in `site/index.html` and `site/practitioner-toolkit.html`.

TASK 2: EMPLOYEE BEHAVIOR & CAPABILITY UPGRADE
Upgrade the behavioral prompts, capabilities, and response logic for our core institutional roles:
1. Elena Brooks (Senior Docket Specialist / Practitioner Onboarding):
   - Scope: 7-day trials, specific county dockets, lien priority reconciliation, Florida/Texas/Georgia/California/North Carolina/Tennessee statutory guidance.
   - Upgrade: Must behave like a seasoned court docket clerk and legal data specialist. Exacting accuracy, no conversational filler, listens directly to caller recordings, explains statutory claim windows (Fla. Stat. § 197.582, Tex. Tax Code § 34.04, O.C.G.A. § 48-4-5, Cal. Rev. & Tax Code § 4675, N.C. Gen. Stat. § 105-374, Tenn. Code Ann. § 67-5-2510).
2. Aubrey Hayes (Executive Intake Coordinator):
   - Scope: General inquiries, pricing, delivery schedules, preliminary voicemail review.
   - Upgrade: Objective, calm, efficient. Refuses to give legal advice or make unverified promises. Escalate dockets to Elena conditionally.
3. Audio-First Voicemail Response Handling:
   - Detail how Elena and Aubrey should listen to and process the actual caller audio (via Whisper transcription of the MP3/WAV attachment) rather than relying on automated Google Voice transcripts.
   - Explain how they should address the caller: explicitly confirming audio review, extracting difficult-to-transcribe docket numbers and spoken email addresses, and preparing action memos for unstated emails.

Provide concrete copy, prompt instructions, and implementation specs.
"""

def main():
    if not OPENAI_API_KEY:
        print("[!] ERROR: OPENAI_API_KEY is not set.")
        sys.exit(1)

    print(f"[*] Tasking {MODEL} with copy critique and employee upgrade...")
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

    out_file = os.path.join(os.path.dirname(__file__), "..", "output", "astrid_copy_and_agent_upgrade.md")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)

    with urllib.request.urlopen(req, timeout=300) as response, open(out_file, "w", encoding="utf-8") as f_out:
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

    print(f"\n[+] Output saved to: {out_file}")

if __name__ == "__main__":
    main()
