"""
Unit tests for StaffKnowledgeEngine and Staff Truth Verification
================================================================
Verifies that Elena Brooks and all staff personas:
1. Speak 100% verified truth.
2. Dynamically load platform parameters from monetization_config.json and statutory_rules.json.
3. Automatically adhere to zero false claims rules (no 6:00 AM, no 12-month claims, no outdated pricing).
"""

import unittest
from pathlib import Path

from outreach.staff_knowledge_engine import knowledge_engine, StaffKnowledgeEngine
from outreach.auto_responder_and_draft_cleaner import (
    compose_elena_response,
    compose_elena_inquiry_response,
    DEPARTMENT_PERSONAS
)

class TestStaffKnowledgeVerification(unittest.TestCase):

    def setUp(self):
        self.engine = StaffKnowledgeEngine.get_instance()
        self.mock_cases = {
            "FL": [
                {"county": "Orange", "case_no": "2024-TD-001955", "balance": 74300.0, "sale_date": "2024-05-15"},
                {"county": "Miami-Dade", "case_no": "2024-TD-002140", "balance": 52100.0, "sale_date": "2024-06-01"},
            ],
            "TX": [
                {"county": "Harris", "case_no": "2024-TX-04812", "balance": 128500.0, "sale_date": "2024-07-09"}
            ]
        }

    def test_dynamic_monetization_loading(self):
        """Verify dynamic loading from portal/monetization_config.json."""
        core = self.engine.get_tri_state_core()
        self.assertEqual(core.get("price_monthly_usd"), 249)
        self.assertEqual(core.get("price_annual_usd"), 2490)
        self.assertEqual(core.get("trial_days"), 7)
        self.assertEqual(core.get("has_trial"), True)

        national = self.engine.get_six_state_national()
        self.assertEqual(national.get("price_monthly_usd"), 449)
        self.assertEqual(national.get("price_annual_usd"), 4490)
        self.assertEqual(national.get("trial_days"), 0)
        self.assertEqual(national.get("has_trial"), False)

        pilot = self.engine.get_single_county_pilot()
        self.assertEqual(pilot.get("price_usd"), 49)

    def test_dispatch_schedule_truth(self):
        """Verify dispatch schedule is strictly 7:00 AM EST Mon-Fri."""
        self.assertEqual(self.engine.DISPATCH_TIME, "7:00 AM EST")
        self.assertIn("7:00 AM EST", self.engine.DISPATCH_SCHEDULE)
        self.assertIn("Mon–Fri", self.engine.DISPATCH_SCHEDULE)

    def test_statutory_rules_truth(self):
        """Verify statutory knowledge matches compliance/statutory_rules.json."""
        fl_statute = self.engine.get_governing_statute("FL")
        self.assertEqual(fl_statute, "Fla. Stat. § 197.582")

        tx_statute = self.engine.get_governing_statute("TX")
        self.assertEqual(tx_statute, "Tex. Tax Code § 34.04")

        ga_statute = self.engine.get_governing_statute("GA")
        self.assertEqual(ga_statute, "O.C.G.A. § 48-4-5")

        ca_statute = self.engine.get_governing_statute("CA")
        self.assertEqual(ca_statute, "Cal. Rev. & Tax Code § 4675")

    def test_verify_statement_facts_catches_violations(self):
        """Ensure pre-flight validator rejects false claims."""
        # 1. 6:00 AM claim
        valid, viols = self.engine.verify_statement_facts("We deliver the feed at 6:00 AM EST.")
        self.assertFalse(valid)
        self.assertTrue(any("6:00 AM" in v for v in viols))

        # 2. 12-month business claim
        valid, viols = self.engine.verify_statement_facts("We have identified 700+ surplus files over the past 12 months.")
        self.assertFalse(valid)
        self.assertTrue(any("12-month" in v or "700+" in v for v in viols))

        # 3. Outdated annual pricing ($4,188)
        valid, viols = self.engine.verify_statement_facts("Annual pricing is $4,188/year.")
        self.assertFalse(valid)
        self.assertTrue(any("pricing" in v for v in viols))

        # 4. Clean verified statement
        valid, viols = self.engine.verify_statement_facts(
            "Surplus Docket delivers verified dockets every court business day at 7:00 AM EST. "
            "Our Tri-State Core Feed is $249/mo ($2,490/yr) with a 7-day practice evaluation."
        )
        self.assertTrue(valid)
        self.assertEqual(len(viols), 0)

    def test_elena_inquiry_responses_zero_violations(self):
        """Ensure all standard inquiry departments produce responses with zero false claims."""
        departments = [
            "General Publisher Inquiry",
            "7-Day Institutional Practice Evaluation",
            "Enterprise Feed Licensing",
            "Law Practice API Integration",
            "County Registry Operations Liaison",
            "Statutory Compliance Verification",
            "Public Information Liaison",
            "Inquiries & Intake Desk"
        ]

        for dept in departments:
            inquiry = {
                "name": "Jane Attorney",
                "email": "jane@examplelaw.com",
                "firm": "Example Law",
                "department": dept,
                "state_code": "FL",
                "message": "Tell me about your surplus docket feed and pricing."
            }
            subj, body, role = compose_elena_inquiry_response(inquiry, self.mock_cases)
            valid, viols = self.engine.verify_statement_facts(body)
            self.assertTrue(
                valid,
                f"Department '{dept}' produced fact violations: {viols}\nBody:\n{body}"
            )
            # Ensure proper 7:00 AM timing is mentioned for subscription/licensing inquiries
            if dept in ["General Publisher Inquiry", "7-Day Institutional Practice Evaluation", "Enterprise Feed Licensing", "Law Practice API Integration"]:
                self.assertIn("7:00 AM EST", body)
            # Ensure no 6:00 AM mentions across any department
            self.assertNotIn("6:00 AM", body)

    def test_elena_email_intents_zero_violations(self):
        """Ensure Elena Brooks email responses across various practitioner intents are compliant."""
        intents = [
            "PRICING",
            "DATA_FRESHNESS_TIMING",
            "DATA_FORMAT",
            "JURISDICTION",
            "SAMPLE_DATA",
            "TYLER_V_HENNEPIN",
            "SKIP_TRACING_CONTACT",
            "LEGAL_TOOLKIT_MOTIONS",
        ]

        target = {
            "name": "David Partner",
            "firm": "Partner Law Firm",
            "state": "FL",
            "specialty": "Probate and Estate"
        }

        for intent in intents:
            subj, body = compose_elena_response(
                intent=intent,
                target_info=target,
                sender_name="David Partner",
                sender_email="david@partnerlaw.com",
                subject_raw="Question on Surplus Docket",
                text_body="How does your service work and what are the fees?",
                state_cases=self.mock_cases
            )
            valid, viols = self.engine.verify_statement_facts(body)
            self.assertTrue(
                valid,
                f"Intent '{intent}' produced fact violations: {viols}\nBody:\n{body}"
            )
            self.assertNotIn("6:00 AM", body)


if __name__ == "__main__":
    unittest.main()
