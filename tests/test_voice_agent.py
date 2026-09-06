#!/usr/bin/env python3
"""
Unit Test Suite: Surplus Docket AI Voice Customer Service Server
================================================================
Tests:
1. Speech intent classification across legal topics (Pricing, Trial, County, Bar Rules, Liens)
2. Conversational voice response synthesis and statutory citations
3. TwiML XML structure, Amazon Polly voice tags, and speech gathering loops
4. Multi-turn telephony flow: speech processing, SMS offer, and voicemail fallback
"""

import unittest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "outreach"))

from outreach.voice_agent_server import (
    classify_speech_intent,
    generate_voice_response,
    build_twiml_response,
    VOICE_NAME,
    VOICE_GREETING,
)


class TestVoiceAgent(unittest.TestCase):

    def test_pricing_intent(self):
        reply, offer_sms, record_vm = generate_voice_response("How much does the monthly subscription cost?")
        self.assertIn("249 dollars per month", reply)
        self.assertIn("449 dollars a month", reply)
        self.assertIn("7-day practice evaluation", reply)
        self.assertTrue(offer_sms)
        self.assertFalse(record_vm)

    def test_county_jurisdiction_intent(self):
        reply, offer_sms, record_vm = generate_voice_response("Do you cover Orange County Florida?")
        self.assertIn("Orange County", reply)
        self.assertIn("Florida", reply)
        self.assertIn("Fla. Stat. § 197.582", reply)
        self.assertIn("senior bank mortgages", reply)
        self.assertTrue(offer_sms)

    def test_texas_county_jurisdiction(self):
        reply, offer_sms, record_vm = generate_voice_response("Are you tracking excess proceeds in Harris County?")
        self.assertIn("Harris County", reply)
        self.assertIn("Texas", reply)
        self.assertIn("Tex. Tax Code § 34.04", reply)

    def test_bar_rules_phone_rejection(self):
        reply, offer_sms, record_vm = generate_voice_response("Can you give me the owner phone numbers to cold call?")
        self.assertIn("intentionally does not compile consumer phone numbers", reply)
        self.assertIn("Florida Bar Rule 4-7.18", reply)
        self.assertIn("direct written correspondence", reply)
        self.assertFalse(offer_sms)

    def test_senior_lien_filtering_intent(self):
        reply, offer_sms, record_vm = generate_voice_response("How do you handle senior mortgages and title scrubbing?")
        self.assertIn("Upstream lien scrubbing", reply)
        self.assertIn("senior institutional liens", reply)
        self.assertIn("clean, claimable funds", reply)

    def test_upl_referral_intent(self):
        reply, offer_sms, record_vm = generate_voice_response("Can you represent me and file my surplus claim?")
        self.assertIn("not a law firm", reply)
        self.assertIn("cannot provide legal representation", reply)
        self.assertIn("lawyer referral service", reply)

    def test_twiml_generation_interactive(self):
        xml = build_twiml_response("Test speech prompt", should_record_voicemail=False)
        self.assertIn("<Response>", xml)
        self.assertIn(f'<Say voice="{VOICE_NAME}">Test speech prompt</Say>', xml)
        self.assertIn('<Gather input="speech"', xml)
        self.assertIn('action="/voice/process"', xml)

    def test_twiml_generation_voicemail(self):
        xml = build_twiml_response("Please leave a message", should_record_voicemail=True)
        self.assertIn("<Record", xml)
        self.assertIn('action="/voice/voicemail"', xml)


if __name__ == "__main__":
    unittest.main()
