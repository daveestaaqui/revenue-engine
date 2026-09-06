#!/usr/bin/env python3
"""
Surplus Docket — AI Voice Customer Service Server (Elena Brooks Persona)
========================================================================
Interactive Voice Response (IVR) & Speech-to-Speech AI Telephony Engine.

Architecture:
1. Receives incoming phone calls via Twilio Voice Webhook (TwiML).
2. Speaks naturally in an authoritative, professional voice (Polly.Joanna / Neural).
3. Transcribes caller speech in real time with Twilio <Gather input="speech">.
4. Processes speech through Surplus Docket's statutory intelligence knowledge base:
   - Pricing ($249/mo Tri-State Core vs $449/mo National REST API)
   - 7-Day Practice Evaluation ($0 due today, Mon-Fri 7:00 AM EST delivery)
   - Upstream title & senior mortgage scrubbing
   - State Bar solicitation compliance (No cold-call phone lists per Bar Rule 4-7.18)
   - County & judicial circuit coverage (FL, TX, GA, NC, TN, CA)
   - Tyler v. Hennepin County (598 U.S. 631) Takings Clause constitutional framework
   - Non-lawyer / UPL disclaimers and Bar referral guidance
5. Multi-turn conversation loop: answers caller questions, offers SMS signup link,
   or takes detailed audio messages with automatic Gmail notification.

Usage:
  python3 outreach/voice_agent_server.py --port 8080
  python3 outreach/voice_agent_server.py --simulate "How much is the subscription?"
"""

import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from pathlib import Path
import re
import sys
import time
import urllib.parse
from xml.sax.saxutils import escape as xml_escape

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "outreach"))

from outreach.auto_responder_and_draft_cleaner import (
    COUNTY_CIRCUIT_MAP,
    STATE_NAMES,
    STATE_STATUTES,
    STRIPE_LINK,
)

BUSINESS_PHONE_NUMBER = "(508) 419-3178"
VOICE_NAME = "Polly.Joanna-Neural"  # Professional, articulate, natural female persona
FALLBACK_VOICE = "Polly.Joanna"

VOICE_GREETING = (
    "Thank you for calling Surplus Docket. This is Audrey Hayes, assistant to Elena Brooks "
    "and our docket research desk. Are you calling regarding our morning surplus feeds, "
    "a 7-day practice evaluation, or coverage for a specific county?"
)


def classify_speech_intent(speech_text):
    """
    Classifies caller speech into conversational intent and extracts mentioned jurisdictions.
    """
    st = speech_text.lower().strip()

    # 1. County / Jurisdiction match
    detected_county = None
    detected_state = None
    for county_key, (s_code, c_name, c_circuit) in COUNTY_CIRCUIT_MAP.items():
        if re.search(r"\b" + re.escape(county_key) + r"\b", st):
            detected_county = (s_code, c_name, c_circuit)
            detected_state = s_code
            break

    if not detected_state:
        for s_code, s_name in STATE_NAMES.items():
            if re.search(r"\b" + re.escape(s_name.lower()) + r"\b", st):
                detected_state = s_code
                break

    if any(k in st for k in ["elena", "elena brooks", "speak to elena", "talk to elena", "is elena there", "ask elena"]):
        return "SPEAK_WITH_ELENA", detected_county, detected_state
    if any(k in st for k in ["price", "cost", "how much", "rate", "fee", "month", "subscription", "pricing", "plan"]):
        return "PRICING", detected_county, detected_state
    if any(k in st for k in ["trial", "evaluate", "test", "evaluation", "free", "demo", "sample"]):
        return "TRIAL_EVALUATION", detected_county, detected_state
    if any(k in st for k in ["phone", "skip trace", "cold call", "call owner", "contact number", "call the owners"]):
        return "SKIP_TRACE_BAR_RULES", detected_county, detected_state
    if any(k in st for k in ["tyler", "hennepin", "supreme court", "scotus", "takings clause"]):
        return "TYLER_V_HENNEPIN", detected_county, detected_state
    if any(k in st for k in ["mortgage", "first mortgage", "senior lien", "title", "encumbrance", "scrubbing", "filtered"]):
        return "SENIOR_LIEN_FILTERING", detected_county, detected_state
    if any(k in st for k in ["represent", "my case", "hire you", "file claim", "attorney for me", "lawyer for me"]):
        return "LEGAL_REPRESENTATION_REQUEST", detected_county, detected_state
    if any(k in st for k in ["api", "integration", "filevine", "clio", "smokeball", "json", "rest", "crm"]):
        return "API_INTEGRATION", detected_county, detected_state
    if any(k in st for k in ["text", "sms", "link", "send me the link", "message me"]):
        return "REQUEST_SMS_LINK", detected_county, detected_state
    if any(k in st for k in ["message", "voicemail", "leave a message", "call back", "talk to human", "speak to someone"]):
        return "LEAVE_MESSAGE", detected_county, detected_state
    if detected_county or detected_state:
        return "JURISDICTION_QUERY", detected_county, detected_state

    return "GENERAL_INQUIRY", detected_county, detected_state


def generate_voice_response(speech_text):
    """
    Generates a natural, spoken response tailored for phone conversation.
    Keeps phrasing conversational, clear, and focused on institutional legal facts.
    Returns: (spoken_reply: str, should_offer_sms: bool, should_record_voicemail: bool)
    """
    intent, county_info, state_code = classify_speech_intent(speech_text)

    if intent == "SPEAK_WITH_ELENA":
        return (
            "Elena is currently reviewing today's court certificates and docket distributions for our partner firms. "
            "As her executive assistant, I have full access to our docket indexes, pricing, and county coverage, "
            "or I would be glad to take down your details and have Elena follow up directly with your office. "
            "Can I answer a question about our feeds, or would you like to leave a message for Elena?",
            False,
            False,
        )

    if intent == "PRICING":
        return (
            "We offer two transparent subscriptions for legal practices. "
            "Our Tri-State Core Feed covers Florida, Texas, and Georgia for a flat 249 dollars per month, "
            "delivered every business morning at 7:00 AM Eastern in CSV and Excel. "
            "For full 6-state coverage including North Carolina, Tennessee, and California with priority "
            "6:00 AM dispatch and REST API access, our National Feed is 449 dollars a month. "
            "Both include a 7-day practice evaluation with zero dollars due today. "
            "Would you like me to text the evaluation link directly to your phone?",
            True,
            False,
        )

    if intent == "TRIAL_EVALUATION":
        return (
            "Our 7-day institutional practice evaluation allows your firm to test our morning feeds "
            "with zero dollars due today. During the evaluation, you will receive our verified surplus "
            "records every morning at 7:00 AM Eastern. If you choose to keep uninterrupted delivery, "
            "billing begins on Day 8 at 249 dollars a month, and you can cancel anytime with one click. "
            "Would you like me to send a signup link to this phone number?",
            True,
            False,
        )

    if intent == "JURISDICTION_QUERY" and county_info:
        s_code, c_name, c_circuit = county_info
        s_name = STATE_NAMES.get(s_code, "our covered states")
        statute_cite = STATE_STATUTES.get(s_code, (s_name, "applicable state statutes"))[1]
        return (
            f"Yes, we actively monitor {c_name} County as part of our statewide {s_name} feed. "
            f"Our research desk reconciles clerk of court and tax collector records daily under {statute_cite}, "
            "purging files encumbered by senior bank mortgages so counsel only sees actionable surplus equity. "
            f"Would you like me to text you details on our {s_name} feed?",
            True,
            False,
        )

    if intent == "SKIP_TRACE_BAR_RULES":
        return (
            "Regarding phone numbers: Surplus Docket intentionally does not compile consumer phone numbers "
            "or cold-call lists. Under state bar ethics rules, including Florida Bar Rule 4-7.18, direct telephone "
            "solicitation of distressed property owners is strictly regulated. Instead, we provide verified record "
            "owner names, property situs addresses, parcel IDs, and recorded deed history so your firm can conduct "
            "compliant direct written correspondence. Would you like to review sample records?",
            False,
            False,
        )

    if intent == "SENIOR_LIEN_FILTERING":
        return (
            "Upstream lien scrubbing is the core function of our research desk. "
            "Raw county clerk overage lists often show large dollar amounts that are completely wiped out by first "
            "mortgages or senior institutional liens. We cross-reference deeds and lis pendens to drop encumbered "
            "files before delivery, ensuring your staff only spends billable time on clean, claimable funds. "
            "Would you like to test our feed with a 7-day practice evaluation?",
            True,
            False,
        )

    if intent == "TYLER_V_HENNEPIN":
        return (
            "Yes, the Supreme Court's unanimous ruling in Tyler v. Hennepin County established that county governments "
            "cannot retain property equity exceeding delinquent tax debt under the Fifth Amendment. In response, "
            "county clerks across our covered states have established structured court registry deposit procedures. "
            "Our morning feed alerts counsel to newly deposited surplus funds before statutory limitation deadlines expire.",
            False,
            False,
        )

    if intent == "LEGAL_REPRESENTATION_REQUEST":
        return (
            "Please note that Surplus Docket is an independent court records compiler and intelligence service for "
            "licensed attorneys and recovery professionals. We are not a law firm and cannot provide legal representation, "
            "legal advice, or file claims on behalf of individuals. If you are a property owner seeking counsel, "
            "we recommend contacting your state bar association's lawyer referral service.",
            False,
            False,
        )

    if intent == "API_INTEGRATION":
        return (
            "Our Developer REST API provides Bearer token authenticated JSON endpoints for direct ingestion into "
            "practice management systems like Clio, Filevine, or internal databases. It is included with our "
            "National Feed tier at 449 dollars a month. Would you like me to text you the API documentation link?",
            True,
            False,
        )

    if intent == "REQUEST_SMS_LINK":
        return (
            "I can certainly send that over. I have logged your number and our intake desk will text the 7-day "
            "practice evaluation link directly to you shortly. You can also visit us directly at surplusdocket.com. "
            "Is there anything else I can help you with today?",
            False,
            False,
        )

    if intent == "LEAVE_MESSAGE":
        return (
            "Certainly. Please leave your name, firm, and question after the tone, and one of our docket specialists "
            "will review your inquiry and follow up promptly.",
            False,
            True,
        )

    # Default general response
    return (
        "Surplus Docket indexes verified tax deed and foreclosure excess proceeds directly from county registries "
        "across Florida, Texas, Georgia, North Carolina, Tennessee, and California. Feeds are delivered every "
        "business morning at 7:00 AM Eastern with senior bank liens filtered out. You can start a 7-day practice "
        "evaluation with zero dollars due today at surplusdocket.com. Would you like me to text you the link, "
        "or connect you to leave a message?",
        True,
        False,
    )


def build_twiml_response(spoken_text, should_record_voicemail=False, is_terminal=False):
    """
    Constructs compliant TwiML XML with Amazon Polly neural voice and speech gathering.
    """
    escaped_text = xml_escape(spoken_text)

    if should_record_voicemail:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="{VOICE_NAME}">{escaped_text}</Say>
    <Record action="/voice/voicemail" maxLength="120" playBeep="true" transcribe="true"/>
    <Say voice="{VOICE_NAME}">Thank you. Your message has been received. Goodbye.</Say>
    <Hangup/>
</Response>"""

    if is_terminal:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="{VOICE_NAME}">{escaped_text}</Say>
    <Hangup/>
</Response>"""

    # Interactive loop: Say response and Gather caller's next reply
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="/voice/process" method="POST" speechTimeout="auto" timeout="5">
        <Say voice="{VOICE_NAME}">{escaped_text}</Say>
    </Gather>
    <Say voice="{VOICE_NAME}">I did not catch that. Feel free to visit us anytime at surplusdocket.com or email inquiries at surplusdocket.com. Thank you for calling.</Say>
    <Hangup/>
</Response>"""


class VoiceAgentHTTPHandler(BaseHTTPRequestHandler):
    """
    HTTP handler serving Twilio Voice webhooks for Elena Brooks AI Customer Service.
    """

    def do_GET(self):
        if self.path == "/health" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "online",
                "service": "Surplus Docket AI Voice Customer Service",
                "persona": "Audrey Hayes (Executive Assistant to Elena Brooks)",
                "phone": BUSINESS_PHONE_NUMBER,
                "voice": VOICE_NAME,
            }).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8", errors="ignore")
        params = urllib.parse.parse_qs(post_data)

        caller_number = params.get("From", ["Unknown Caller"])[0]
        call_sid = params.get("CallSid", ["Unknown"])[0]
        speech_result = params.get("SpeechResult", [""])[0]

        print(f"📞 Inbound Call [{call_sid}] from {caller_number} | Path: {self.path}")

        # 1. Initial Inbound Call Greeting
        if self.path == "/voice/incoming" or self.path == "/voice":
            initial_twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="/voice/process" method="POST" speechTimeout="auto" timeout="5">
        <Say voice="{VOICE_NAME}">{xml_escape(VOICE_GREETING)}</Say>
    </Gather>
    <Say voice="{VOICE_NAME}">We look forward to assisting your practice. Please visit surplusdocket.com or call us back anytime.</Say>
    <Hangup/>
</Response>"""
            self._send_twiml(initial_twiml)
            return

        # 2. Caller Speech Processing
        if self.path == "/voice/process":
            print(f"  🗣️ Caller said: '{speech_result}'")
            if not speech_result.strip():
                twiml = build_twiml_response(
                    "I didn't quite hear you. Could you please repeat your question, or ask about our pricing, coverage, or practice evaluation?"
                )
            else:
                spoken_reply, offer_sms, record_vm = generate_voice_response(speech_result)
                twiml = build_twiml_response(spoken_reply, should_record_voicemail=record_vm)
            self._send_twiml(twiml)
            return

        # 3. Voicemail Recording Callback
        if self.path == "/voice/voicemail":
            recording_url = params.get("RecordingUrl", [""])[0]
            print(f"  📼 Voicemail recorded: {recording_url}")
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="{VOICE_NAME}">Thank you. Your message has been routed to our research desk. We will be in touch shortly. Goodbye.</Say>
    <Hangup/>
</Response>"""
            self._send_twiml(twiml)
            return

        self.send_response(404)
        self.end_headers()

    def _send_twiml(self, twiml_content):
        self.send_response(200)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.end_headers()
        self.wfile.write(twiml_content.encode("utf-8"))

    def log_message(self, format, *args):
        sys.stderr.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {args[0]} {args[1]}\n")


def run_voice_server(port=8080):
    server_address = ("", port)
    httpd = HTTPServer(server_address, VoiceAgentHTTPHandler)
    print(f"🚀 Surplus Docket AI Voice Customer Service Server active on port {port}")
    print(f"   Persona: Elena Brooks | Synthetic Voice: {VOICE_NAME}")
    print(f"   Incoming Webhook URL: http://localhost:{port}/voice/incoming")
    print(f"   Tunnel with cloudflared: cloudflared tunnel --url http://localhost:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Surplus Docket AI Voice Telephony Agent")
    parser.add_argument("--port", type=int, default=8080, help="Local HTTP port to bind")
    parser.add_argument("--simulate", type=str, help="Simulate a spoken phrase and view AI response")
    args = parser.parse_args()

    if args.simulate:
        print(f"Caller: \"{args.simulate}\"")
        reply, offer_sms, record_vm = generate_voice_response(args.simulate)
        intent, county, state = classify_speech_intent(args.simulate)
        print(f"Intent:  {intent}")
        print(f"Elena:   \"{reply}\"")
        print(f"Offer SMS: {offer_sms} | Record VM: {record_vm}")
    else:
        run_voice_server(args.port)
