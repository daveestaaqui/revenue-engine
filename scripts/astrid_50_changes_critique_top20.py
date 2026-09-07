#!/usr/bin/env python3
"""
Surplus Docket — Astrid (GPT-6 Astra) 50 Potential Changes & Critique Agent
Tasks Astrid to:
1. Conduct an end-to-end business and automation analysis of Surplus Docket.
2. Architect a Google AI (Gemini) integration so the system operates under the user's
   $20/mo Google AI account rather than consuming temporary OpenAI credits.
3. Generate 50 concrete potential changes across business, automation, conversion, data, and compliance.
4. Run an adversarial Critique Agent stage evaluating all 50 candidates.
5. Select and prioritize the TOP 20 changes with actionable implementation specifications.
"""

import os
import sys
import json
import urllib.request
import urllib.error

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-6-astra"

PROMPT = """
You are Astrid (GPT-6 Astra), Principal Systems Architect & Chief Commercial Strategist for Surplus Docket (https://surplusdocket.com).

CONTEXT & USER DIRECTIVE:
The owner has a $20/month Google AI account (Google Gemini Advanced / Gemini API) and is currently using OpenAI only temporarily.
You must:
1. Transition the core AI infrastructure to support Google AI (Gemini 1.5 Flash / Pro / 2.0 Flash) as the primary provider, supporting native multimodal audio voicemail transcription (bypassing the need for Whisper) and intelligent extraction, with OpenAI remaining only as an optional secondary fallback.
2. Analyze the whole Surplus Docket project end-to-end from a business, revenue, and automation perspective.
3. Generate 50 potential high-leverage changes across the platform:
   - Business & Monetization ($249/mo Tri-State, $449/mo 6-State + REST API)
   - Core Automation & Serverless Operations (GitHub Actions, Zero Local Daemons)
   - Audio-First Voicemail & Inbound Outreach (Google Voice, Action Memos, SMS Follow-up)
   - Google AI / Gemini Provider Abstraction (Multimodal audio, LLM categorization, zero marginal API cost)
   - Public Records Title & Senior Lien Scrubbing (FL, TX, GA, CA, NC, TN)
   - Digital PR, Legal Backlinks & Attorney Practice-Group Conversions
   - Enterprise REST API & Practice Management (Clio, Filevine, Smokeball)
   - Autonomous Sentinel Security & Bar Ethics Compliance
4. Run a rigorous CRITIQUE AGENT STAGE that systematically reviews all 50 candidates on:
   - Immediate Revenue & Conversion Velocity
   - Automation Completeness (Hands-off, self-healing, zero manual toil)
   - Statutory & Legal Ethics Precision (Rule 4-7.18, Tyler v. Hennepin, UPL defense)
   - Cost Efficiency (Maximizing Google AI subscription quota to keep marginal fees < $0.01)
   - Technical Elegance & Robustness
5. Select and rank the WINNING TOP 20 changes with exact specifications ready for immediate implementation.

FORMAT YOUR RESPONSE IN STRUCTURED MARKDOWN:
# 1. Executive Summary & Google AI Transition Architecture
# 2. End-to-End System Audit (Business, Data, Automation, Conversion)
# 3. 50 Candidate Changes Ideation Matrix (Numbered 1 through 50 with Title, Subsystem, and Description)
# 4. Critique Agent Evaluation & Scoring (Evaluating each category, trade-offs, and failure modes)
# 5. The Top 20 Selected Changes (Ranked 1 to 20 with precise implementation blueprints, files to modify, and acceptance criteria)
"""

def main():
    if not OPENAI_API_KEY:
        print("[!] ERROR: OPENAI_API_KEY is not set.")
        sys.exit(1)

    print(f"[*] Tasking {MODEL} with 50-change ideation, critique agent, and top 20 selection...")
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

    out_file = os.path.join(os.path.dirname(__file__), "..", "output", "astrid_50_changes_critique_top20.md")
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
        print(f"\n\n[+] Successfully saved output to {out_file}")
    except Exception as e:
        print(f"[!] API call failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
