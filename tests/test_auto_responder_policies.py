#!/usr/bin/env python3
"""
Unit Test Suite: Policy Enforcement & Voice Consistency
========================================================
Tests for:
1. Policy SD-POL-OUTREACH-2026-V1 enforcement in auto_responder_and_draft_cleaner.py
2. Zero tolerance for platform/system/automated senders (Google, Cloudflare, Stripe, etc.)
3. Verification of Elena Brooks' voice, greeting rules, and context-aware responses
4. Target directory lookups and intent classification
"""

import email
from email.message import Message
import unittest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "outreach"))

from outreach.auto_responder_and_draft_cleaner import (
    SYSTEM_BLOCKLIST_DOMAINS,
    SYSTEM_SENDER_PATTERNS,
    SYSTEM_SUBJECT_BLOCKLIST,
    BANNED_FIRST_NAMES,
    clean_domain_str,
    load_target_directory,
    is_automated_receipt_or_bounce,
    is_prospect_eligible,
    analyze_prospect_intent,
    compose_elena_response,
    FROM_NAME,
    SENDER_EMAIL
)


class TestAutoResponderPolicies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory, cls.email_directory, cls.domains = load_target_directory()
        cls.mock_state_cases = {
            "FL": [
                {"case_no": "2024-TD-001", "county": "Palm Beach", "balance": 120000.0, "sale_date": "2024-05-01"}
            ],
            "TX": [
                {"case_no": "TX-2024-88", "county": "Harris", "balance": 85000.0, "sale_date": "2024-06-15"}
            ]
        }

    def test_google_gmail_confirmation_strictly_rejected(self):
        msg = Message()
        sender_email = "gmail-noreply@google.com"
        subject = "Re: Gmail Confirmation - Send Mail as elena.brooks@surplusdocket.com"
        text_body = "You have requested to add elena.brooks@surplusdocket.com to your Gmail account."

        eligible, reason, target_info, inq_info = is_prospect_eligible(
            msg, sender_email, "Gmail Team", subject, text_body,
            self.directory, self.email_directory, self.domains
        )
        self.assertFalse(eligible, "Google confirmation emails must NEVER be eligible for drafts")
        self.assertIn("automated", reason.lower())

    def test_cloudflare_notification_strictly_rejected(self):
        msg = Message()
        sender_email = "noreply@email.cloudflare.net"
        subject = "Cloudflare Email Routing: Missing email from sandwichfitness@gmail.com to elena.brooks@surplusdocket.com?"
        text_body = "Are you missing an email sent from sandwichfitness@gmail.com to elena.brooks@surplusdocket.com?"

        eligible, reason, target_info, inq_info = is_prospect_eligible(
            msg, sender_email, "Cloudflare", subject, text_body,
            self.directory, self.email_directory, self.domains
        )
        self.assertFalse(eligible, "Cloudflare notifications must NEVER be eligible for drafts")

    def test_mailer_daemon_bounce_rejected(self):
        msg = Message()
        msg["Auto-Submitted"] = "auto-replied"
        sender_email = "mailer-daemon@googlemail.com"
        subject = "Delivery Status Notification (Failure)"
        text_body = "550 5.1.1 Address does not exist"

        eligible, reason, target_info, inq_info = is_prospect_eligible(
            msg, sender_email, "Mail Delivery Subsystem", subject, text_body,
            self.directory, self.email_directory, self.domains
        )
        self.assertFalse(eligible, "Bounces must be rejected")

    def test_unknown_third_party_rejected(self):
        msg = Message()
        sender_email = "info@starkbros.com"
        subject = "Stark Bro's Shipping Confirmation"
        text_body = "Your apple trees are on their way."

        eligible, reason, target_info, inq_info = is_prospect_eligible(
            msg, sender_email, "Stark Bro's", subject, text_body,
            self.directory, self.email_directory, self.domains
        )
        self.assertFalse(eligible, "E-commerce and non-target senders must be rejected")

    def test_self_sent_messages_rejected(self):
        msg = Message()
        sender_email = "sandwichfitness@gmail.com"
        subject = "Surplus Docket Routing Verification [5cc4d79f]"
        text_body = "Self test message"

        eligible, reason, target_info, inq_info = is_prospect_eligible(
            msg, sender_email, "David Mahler", subject, text_body,
            self.directory, self.email_directory, self.domains
        )
        self.assertFalse(eligible, "Self-sent emails must be rejected")

    def test_statutory_inquiry_accepted(self):
        msg = Message()
        sender_email = "contact@formsubmit.co"
        subject = "Surplus Docket Public Record Request [FL]"
        text_body = (
            "OFFICIAL STATUTORY INQUIRY RECORD\n"
            "Inquiring Entity Name: Arthur Pendelton\n"
            "Inquiring Entity Email: arthur@pendeltonlegal.com\n"
            "Practice Jurisdiction: Florida\n"
            "Message: Requesting information on Miami-Dade tax deed overages."
        )
        eligible, reason, target_info, inq_info = is_prospect_eligible(
            msg, sender_email, "FormSubmit", subject, text_body,
            self.directory, self.email_directory, self.domains
        )
        self.assertTrue(eligible, "Valid statutory inquiries must be eligible")
        self.assertIsNotNone(inq_info)
        self.assertEqual(inq_info["email"], "arthur@pendeltonlegal.com")

    def test_verified_law_firm_reply_accepted(self):
        msg = Message()
        # Gomez Law is in master_ranked_attorney_targets.csv
        sender_email = "jason@gomezlawfl.com"
        subject = "Thanks for Reaching Out to Gomez Law!"
        text_body = "Hello Elena, how much is your Florida surplus feed per month?"

        eligible, reason, target_info, inq_info = is_prospect_eligible(
            msg, sender_email, "Gomez Law", subject, text_body,
            self.directory, self.email_directory, self.domains
        )
        self.assertTrue(eligible, "Target law firm replies must be eligible")
        self.assertIsNotNone(target_info)

    def test_banned_greetings_prevented(self):
        target_info = {"name": "Gmail Team", "firm": "Google Inc", "state": "CA"}
        subj, body = compose_elena_response(
            "GENERAL", target_info, "Gmail Team", "gmail-noreply@google.com",
            "Re: Inquiry", "Hello", self.mock_state_cases
        )
        self.assertNotIn("Hi Gmail,", body, "'Hi Gmail' must NEVER appear in greetings")
        self.assertNotIn("Hi Google,", body)

    def test_intent_classification(self):
        self.assertEqual(analyze_prospect_intent("Re: Surplus data", "Please remove us from your list"), "OPT_OUT")
        self.assertEqual(analyze_prospect_intent("Pricing question", "What is the cost per month?"), "PRICING")
        self.assertEqual(analyze_prospect_intent("Coverage", "Do you cover Harris and Dallas counties in Texas?"), "JURISDICTION")
        self.assertEqual(analyze_prospect_intent("Integration", "Can we receive this via JSON API or Excel?"), "DATA_FORMAT")
        self.assertEqual(analyze_prospect_intent("Sample", "Can you send me a sample of active cases?"), "SAMPLE_DATA")

    def test_elena_brooks_voice_and_signature(self):
        target_info = {"name": "Mark Thornton", "firm": "Thornton Asset Law", "state": "TX"}
        subj, body = compose_elena_response(
            "PRICING", target_info, "Mark Thornton", "mark@thorntonlaw.com",
            "Cost question", "How much does the Texas surplus feed cost?", self.mock_state_cases
        )
        self.assertIn("Hi Mark,", body)
        self.assertIn("$249/month", body)
        self.assertIn("Elena Brooks", body)
        self.assertIn("Senior Docket Specialist | Surplus Docket", body)
        self.assertIn("elena.brooks@surplusdocket.com", body)
        self.assertNotIn("David Mahler", body)


if __name__ == "__main__":
    unittest.main()
