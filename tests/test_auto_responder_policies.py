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

    def test_intent_classification_all_14_categories(self):
        # 1. Opt out
        self.assertEqual(analyze_prospect_intent("Re: Surplus data", "Please remove us from your list"), "OPT_OUT")
        self.assertEqual(analyze_prospect_intent("Re: Inquiry", "Not interested, pass on this"), "OPT_OUT")

        # 2. In-house paralegal
        self.assertEqual(analyze_prospect_intent("Re: Records", "We already have a paralegal who pulls these from the clerk site."), "IN_HOUSE_PARALEGAL")
        self.assertEqual(analyze_prospect_intent("Docket feed", "Our staff handles this in house and checks the county site weekly."), "IN_HOUSE_PARALEGAL")

        # 3. Contingency fee split / Ethics
        self.assertEqual(analyze_prospect_intent("Fee question", "What cut do you take of the recovery? We cannot split fees under Rule 4-5.4."), "CONTINGENCY_FEE_SPLIT")
        self.assertEqual(analyze_prospect_intent("Surplus", "Do you take a percentage or contingency fee?"), "CONTINGENCY_FEE_SPLIT")

        # 4. Tax deed vs Mortgage
        self.assertEqual(analyze_prospect_intent("Question", "Are these tax deed overages or civil mortgage foreclosures?"), "TAX_DEED_VS_MORTGAGE")
        self.assertEqual(analyze_prospect_intent("Surplus type", "Do you cover tax deed surplus or mortgage foreclosure surplus?"), "TAX_DEED_VS_MORTGAGE")

        # 5. Probate & Heir Recovery
        self.assertEqual(analyze_prospect_intent("Heirs", "What if the owner is deceased? Do you track probate and intestate heirs?"), "PROBATE_HEIR_RECOVERY")
        self.assertEqual(analyze_prospect_intent("Estate files", "Can we use this for ancillary probate estate recovery?"), "PROBATE_HEIR_RECOVERY")

        # 6. Title / Lien Scrubbing
        self.assertEqual(analyze_prospect_intent("Title search", "How do you scrub senior mortgages and HOA liens so we know there is equity?"), "TITLE_LIEN_SCRUBBING")
        self.assertEqual(analyze_prospect_intent("Encumbrances", "How do you verify equity isn't eaten by a first mortgage?"), "TITLE_LIEN_SCRUBBING")

        # 7. Data Freshness / Timing
        self.assertEqual(analyze_prospect_intent("Turnaround", "How quickly after the sale is data published? What is the lag time after auction?"), "DATA_FRESHNESS_TIMING")

        # 8. Skip Tracing / Contact Info
        self.assertEqual(analyze_prospect_intent("Contact info", "Do you provide skip tracing or phone numbers to reach the owner?"), "SKIP_TRACING_CONTACT")

        # 9. Legal Toolkit / Motions
        self.assertEqual(analyze_prospect_intent("Forms", "Do you include petition templates, affidavits, or motion pleadings?"), "LEGAL_TOOLKIT_MOTIONS")

        # 10. Jurisdiction
        self.assertEqual(analyze_prospect_intent("Coverage", "Do you cover Hillsborough and Pinellas counties in Florida?"), "JURISDICTION")
        self.assertEqual(analyze_prospect_intent("Counties", "What counties do you cover in Texas?"), "JURISDICTION")

        # 11. Data Format & CRM
        self.assertEqual(analyze_prospect_intent("CRM", "Can we import this into Clio or Filevine via CSV or API?"), "DATA_FORMAT")

        # 12. Sample Request
        self.assertEqual(analyze_prospect_intent("Sample", "Can you send me a sample of active cases?"), "SAMPLE_DATA")

        # 13. Pricing
        self.assertEqual(analyze_prospect_intent("Pricing question", "What is the cost per month and subscription terms?"), "PRICING")

        # 14. General
        self.assertEqual(analyze_prospect_intent("Inquiry", "Can you tell me more about your service?"), "GENERAL")

    def test_anti_ai_voice_elimination_of_buzzwords(self):
        """
        Rigorous anti-AI test: Verifies that Elena Brooks' drafts never contain
        formulaic AI marketing clichés or bullet headers across any intent.
        """
        banned_ai_phrases = [
            "roi perspective",
            "• key details for your practice:",
            "seamless",
            "comprehensive",
            "game-changer",
            "cutting-edge",
            "streamline",
            "leverage our",
            "navigating",
            "in today's competitive landscape",
            "groundbreaking",
            "unmatched",
        ]

        target_info = {"name": "Sarah Jenkins", "firm": "Jenkins Real Estate Law", "state": "FL"}
        intents = [
            "OPT_OUT", "IN_HOUSE_PARALEGAL", "CONTINGENCY_FEE_SPLIT",
            "TAX_DEED_VS_MORTGAGE", "PROBATE_HEIR_RECOVERY", "TITLE_LIEN_SCRUBBING",
            "DATA_FRESHNESS_TIMING", "SKIP_TRACING_CONTACT", "LEGAL_TOOLKIT_MOTIONS",
            "JURISDICTION", "DATA_FORMAT", "SAMPLE_DATA", "PRICING", "GENERAL"
        ]

        for intent in intents:
            subj, body = compose_elena_response(
                intent=intent,
                target_info=target_info,
                sender_name="Sarah Jenkins",
                sender_email="sarah@jenkinslaw.com",
                subject_raw="Re: Court Records",
                text_body="We have questions regarding your platform.",
                state_cases=self.mock_state_cases
            )
            body_lower = body.lower()
            for phrase in banned_ai_phrases:
                self.assertNotIn(
                    phrase, body_lower,
                    f"AI tell phrase '{phrase}' found in draft for intent '{intent}'"
                )

            # Check that signature is always authentic Elena Brooks
            self.assertIn("Elena Brooks", body)
            self.assertIn("Senior Docket Specialist | Surplus Docket", body)
            self.assertIn("elena.brooks@surplusdocket.com", body)
            self.assertNotIn("David Mahler", body)

    def test_in_house_paralegal_objection_handled(self):
        target_info = {"name": "Robert Vance", "firm": "Vance Law Group", "state": "FL"}
        subj, body = compose_elena_response(
            "IN_HOUSE_PARALEGAL", target_info, "Robert Vance", "robert@vancelaw.com",
            "Our research", "We already have a paralegal who pulls from the clerk site.",
            self.mock_state_cases
        )
        self.assertIn("Hi Robert,", body)
        self.assertIn("title search step", body)
        self.assertIn("first mortgages", body)
        self.assertIn("Fla. Stat. § 197.582", body)
        self.assertIn("7:00 AM EST", body)

    def test_contingency_fee_split_ethics_handled(self):
        target_info = {"name": "Claire Redfield", "firm": "Redfield Legal", "state": "FL"}
        subj, body = compose_elena_response(
            "CONTINGENCY_FEE_SPLIT", target_info, "Claire Redfield", "claire@redfieldlegal.com",
            "Fee question", "What percentage do you take? We cannot split fees.",
            self.mock_state_cases
        )
        self.assertIn("We don't take any percentage, cut, or contingency fee", body)
        self.assertIn("Florida Bar Rule 4-5.4", body)
        self.assertIn("retains 100% of your statutory", body)

    def test_probate_and_heir_recovery_handled(self):
        target_info = {"name": "Marcus Kane", "firm": "Kane Probate", "state": "TX"}
        subj, body = compose_elena_response(
            "PROBATE_HEIR_RECOVERY", target_info, "Marcus Kane", "marcus@kaneprobate.com",
            "Heir files", "What if the owner is deceased?",
            self.mock_state_cases
        )
        self.assertIn("35%", body)
        self.assertIn("deceased", body.lower())
        self.assertIn("probate", body.lower())
        self.assertIn("Tex. Tax Code § 34.04", body)

    def test_title_lien_scrubbing_handled(self):
        target_info = {"name": "Daniel Ortiz", "firm": "Ortiz Title Law", "state": "FL"}
        subj, body = compose_elena_response(
            "TITLE_LIEN_SCRUBBING", target_info, "Daniel Ortiz", "daniel@ortizlaw.com",
            "Title screening", "How do you scrub senior mortgages?",
            self.mock_state_cases
        )
        self.assertIn("upstream title examination", body.lower())
        self.assertIn("certificate of disbursements", body)
        self.assertIn("senior bank mortgage", body.lower())

    def test_skip_tracing_and_bar_solicitation_handled(self):
        target_info = {"name": "Laura Croft", "firm": "Croft Law", "state": "FL"}
        subj, body = compose_elena_response(
            "SKIP_TRACING_CONTACT", target_info, "Laura Croft", "laura@croftlaw.com",
            "Phone numbers", "Do you provide skip tracing and phone numbers?",
            self.mock_state_cases
        )
        self.assertIn("do not provide consumer phone numbers", body)
        self.assertIn("Florida Bar Rule 4-7.18", body)
        self.assertIn("direct mail", body.lower())

    def test_legal_toolkit_motions_handled(self):
        target_info = {"name": "Gary Miller", "firm": "Miller Legal", "state": "GA"}
        subj, body = compose_elena_response(
            "LEGAL_TOOLKIT_MOTIONS", target_info, "Gary Miller", "gary@millerlegal.com",
            "Motions", "Do you have motion templates or pleadings?",
            self.mock_state_cases
        )
        self.assertIn("Asset Recovery Legal Toolkit", body)
        self.assertIn("Petition for Distribution of Surplus Funds", body)
        self.assertIn("Affidavit of Claim", body)
        self.assertIn("O.C.G.A. § 48-4-5", body)

    def test_county_and_circuit_context_extraction(self):
        # County test: Hillsborough (13th Judicial Circuit)
        subj, body = compose_elena_response(
            "JURISDICTION", None, "Counsel", "attorney@tampabaylaw.com",
            "Hillsborough county coverage", "Do you have data for Hillsborough County?",
            self.mock_state_cases
        )
        self.assertIn("Hillsborough County (13th Judicial Circuit)", body)

        # County test: Harris County (Civil District Courts, Houston)
        subj, body = compose_elena_response(
            "JURISDICTION", None, "Counsel", "attorney@houstonlit.com",
            "Harris County", "Do you cover Harris County in Texas?",
            self.mock_state_cases
        )
        self.assertIn("Harris County (Harris County Civil District Courts)", body)

    def test_tyler_v_hennepin_handled(self):
        # 1. Intent analysis check
        intent = analyze_prospect_intent(
            "SCOTUS Tyler v Hennepin question",
            "How does the Supreme Court ruling in Tyler v. Hennepin County affect excess proceeds recovery under the Takings Clause?"
        )
        self.assertEqual(intent, "TYLER_V_HENNEPIN")

        # 2. Response composition check
        target_info = {"name": "Elena Rostova", "firm": "Rostova Law", "state": "FL"}
        subj, body = compose_elena_response(
            "TYLER_V_HENNEPIN", target_info, "Elena Rostova", "elena@rostovalaw.com",
            "SCOTUS Tyler v Hennepin question", "How does Tyler v Hennepin impact Florida surplus recovery?",
            self.mock_state_cases
        )
        self.assertIn("Tyler v. Hennepin County, 598 U.S. 631", body)
        self.assertIn("Takings Clause of the Fifth Amendment", body)
        self.assertIn("Fla. Stat. § 197.582", body)
        self.assertIn("County Clerk of Court / Tax Collector", body)
        self.assertIn("120-day statutory notice window", body)
        self.assertIn("Elena Brooks", body)


if __name__ == "__main__":
    unittest.main()

