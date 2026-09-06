#!/usr/bin/env python3
"""
Unit Test Suite: Elena Brooks Inquiry Handling, Dynamic Role Signatures & Auto-Drafting
======================================================================================
Tests:
1. Parsing of all statutory website inquiries (Cloudflare Pages API memo, FormSubmit fallback, Modal)
2. Dynamic signature and role generation based on department, role, or context
3. Department-specific inquiry responses (Trial Onboarding, Enterprise Licensing, REST API,
   Clerk Notice, Statutory Compliance, Press / Academic, General)
4. Contextual keyword handling (Bar rule phone restrictions, Tyler v. Hennepin, Non-lawyer UPL disclaimer)
5. Expansion state (NC, TN, CA) pricing alignment to National Feed ($449/mo)
6. Construction of full MIME email drafts for Gmail [Gmail]/Drafts
"""

import unittest
from email.message import Message
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "outreach"))

from outreach.auto_responder_and_draft_cleaner import (
    parse_statutory_inquiry,
    parse_google_voice_voicemail,
    extract_spoken_email,
    get_elena_role_title,
    get_elena_signature,
    get_department_persona,
    get_employee_signature,
    extract_thread_history,
    compose_elena_inquiry_response,
    compose_elena_response,
    build_inquiry_draft_email,
    is_prospect_eligible,
    load_target_directory,
    LEGAL_DISCLAIMER,
    STRIPE_LINK,
)


class TestElenaInquiryAndRoles(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.directory, cls.email_directory, cls.domains = load_target_directory()
        cls.mock_state_cases = {
            "FL": [
                {"case_no": "2024-TD-001955", "county": "Orange", "balance": 74300.0, "sale_date": "2024-05-15"},
                {"case_no": "2024-TD-001501", "county": "Orange", "balance": 61800.0, "sale_date": "2024-06-01"},
            ],
            "TX": [
                {"case_no": "TX-2024-8841", "county": "Harris", "balance": 92500.0, "sale_date": "2024-06-15"}
            ],
            "NC": [
                {"case_no": "24-CVD-1044", "county": "Mecklenburg", "balance": 48200.0, "sale_date": "2024-07-10"}
            ],
            "CA": [
                {"case_no": "2024-TC-8891", "county": "Los Angeles", "balance": 185000.0, "sale_date": "2024-08-01"}
            ],
        }

    # -------------------------------------------------------------
    # 1. Parsing Statutory Website Inquiries
    # -------------------------------------------------------------
    def test_parse_cloudflare_pages_memo_format(self):
        subject = "[Surplus Docket Inquiry] Law Practice API Integration — Holloway Legal (Marcus Holloway)"
        body = """================================================================================
SURPLUS DOCKET — LEGAL & STATUTORY CORRESPONDENCE MEMORANDUM
Tracking Ref:    SD-INQ-1788723456
Filed:           September 6, 2026 at 03:45 PM EDT
================================================================================

TRANSMITTING PRACTITIONER / PARTY:
--------------------------------------------------------------------------------
Name / Counsel:  Marcus Holloway, Esq.
Direct Email:    mholloway@hollowaylegal.com
Firm / Org:      Holloway Legal Group, P.A.
Jurisdiction:    Florida (Fla. Stat. § 197.582)
Department:      Law Practice API Integration
Docket / Parcel: 2024-TD-001955

STATEMENT OF INQUIRY:
--------------------------------------------------------------------------------
Can our engineering team connect this directly to our Filevine CRM via webhook?
--------------------------------------------------------------------------------
Surplus Docket Legal & Regulatory Inquiries Desk • https://surplusdocket.com"""

        inq = parse_statutory_inquiry(subject, body)
        self.assertIsNotNone(inq)
        self.assertEqual(inq["name"], "Marcus Holloway, Esq.")
        self.assertEqual(inq["email"], "mholloway@hollowaylegal.com")
        self.assertEqual(inq["firm"], "Holloway Legal Group, P.A.")
        self.assertEqual(inq["department"], "Law Practice API Integration")
        self.assertEqual(inq["state_code"], "FL")
        self.assertEqual(inq["docket"], "2024-TD-001955")
        self.assertEqual(inq["ref"], "SD-INQ-1788723456")
        self.assertIn("Filevine CRM via webhook", inq["message"])

    def test_parse_formsubmit_box_relay_format(self):
        subject = "[Surplus Docket Inquiry] Enterprise Feed Licensing — Vance Law (Robert Vance)"
        body = """OFFICIAL RECORD: SD-INQ-998877
PRACTITIONER NAME: Robert Vance
WORK EMAIL: robert@vancelaw.com
LAW FIRM / ENTITY: Vance Law Firm
JURISDICTION: Multi-Jurisdiction / National
DEPARTMENT: Enterprise Feed Licensing
DOCKET / PARCEL: None Specified

INQUIRY MEMORANDUM:
We are litigating surplus claims across Florida, Texas, and North Carolina. We need multi-state feed licensing.
--------------------------------------------------------------------------------"""

        inq = parse_statutory_inquiry(subject, body)
        self.assertIsNotNone(inq)
        self.assertEqual(inq["name"], "Robert Vance")
        self.assertEqual(inq["email"], "robert@vancelaw.com")
        self.assertEqual(inq["firm"], "Vance Law Firm")
        self.assertEqual(inq["department"], "Enterprise Feed Licensing")
        self.assertEqual(inq["ref"], "SD-INQ-998877")
        self.assertIn("multi-state feed licensing", inq["message"])

    def test_parse_modal_inquiry_format(self):
        subject = "[Surplus Docket Modal Inquiry] Florida Docket Request"
        body = """OFFICIAL STATUTORY INQUIRY RECORD
Inquiring Entity Name: Jessica Miller
Inquiring Entity Email: jessica@millerrecovery.com
Practice Jurisdiction: Texas
Message: We are evaluating tax sale excess proceeds in Harris and Dallas counties."""

        inq = parse_statutory_inquiry(subject, body)
        self.assertIsNotNone(inq)
        self.assertEqual(inq["name"], "Jessica Miller")
        self.assertEqual(inq["email"], "jessica@millerrecovery.com")
        self.assertEqual(inq["state_code"], "TX")
        self.assertIn("Harris and Dallas counties", inq["message"])

    # -------------------------------------------------------------
    # 2. Dynamic Role Titles and Signatures
    # -------------------------------------------------------------
    def test_dynamic_roles_by_department(self):
        test_cases = [
            ("7-Day Institutional Practice Evaluation", "Practitioner Onboarding Specialist"),
            ("Enterprise Feed Licensing", "Director of Practice Relations & Licensing"),
            ("Law Practice API Integration", "Lead Technical Specialist & API Integrations"),
            ("Clerk Docket Correction / Notice", "County Registry Operations Liaison"),
            ("Statutory Compliance Verification", "Senior Compliance & Research Specialist"),
            ("Press / Academic Research", "Public Information Liaison"),
            ("General Publisher Inquiry", "Senior Docket Specialist"),
        ]

        for dept, expected_role in test_cases:
            role_title = get_elena_role_title(department=dept)
            self.assertIn(expected_role, role_title)
            self.assertIn("Surplus Docket", role_title)

            sig = get_elena_signature(department=dept)
            self.assertIn("Elena Brooks", sig)
            self.assertIn(expected_role, sig)
            self.assertIn("elena.brooks@surplusdocket.com", sig)
            self.assertIn("surplusdocket.com", sig)
            self.assertNotIn("David Mahler", sig)
            self.assertNotIn("Esq.", sig)

    def test_explicit_role_overrides(self):
        sig_api = get_elena_signature(role="api")
        self.assertIn("Lead Technical Specialist & API Integrations", sig_api)

        sig_clerk = get_elena_signature(role="clerk")
        self.assertIn("County Registry Operations Liaison", sig_clerk)

        sig_compliance = get_elena_signature(role="compliance")
        self.assertIn("Senior Compliance & Research Specialist", sig_compliance)

        sig_general = get_elena_signature(role="general")
        self.assertIn("Senior Docket Specialist", sig_general)

    # -------------------------------------------------------------
    # 3. Department-Specific Responses & Offerings
    # -------------------------------------------------------------
    def test_7_day_evaluation_response(self):
        inquiry_info = {
            "name": "David Thorne",
            "email": "thorne@thornelaw.com",
            "firm": "Thorne Real Estate Law",
            "department": "7-Day Institutional Practice Evaluation",
            "state_code": "FL",
            "message": "We want to test your morning Florida docket."
        }
        subj, body, role = compose_elena_inquiry_response(inquiry_info, self.mock_state_cases)
        self.assertIn("7-Day Practice Evaluation", subj)
        self.assertIn("Hi David,", body)
        self.assertIn("$0 due today", body)
        self.assertIn("$249/month", body)
        self.assertIn("7:00 AM EST", body)
        self.assertIn(STRIPE_LINK, body)
        self.assertIn("Practitioner Onboarding Specialist", body)
        self.assertIn("Fla. Stat. § 197.582", body)

    def test_enterprise_licensing_response(self):
        inquiry_info = {
            "name": "Eleanor Sterling",
            "email": "esterling@nationalrecovery.com",
            "firm": "Sterling National Title",
            "department": "Enterprise Feed Licensing",
            "state_code": "FL",
            "message": "We need access across all available states."
        }
        subj, body, role = compose_elena_inquiry_response(inquiry_info, self.mock_state_cases)
        self.assertIn("Enterprise & Multi-Jurisdiction Feed Licensing", subj)
        self.assertIn("National Feed + REST API Tier ($449/month)", body)
        self.assertIn("Full 6-State Coverage: Florida, Texas, Georgia, North Carolina, Tennessee, and California", body)
        self.assertIn("6:00 AM EST", body)
        self.assertIn("Director of Practice Relations & Licensing", body)
        self.assertIn("https://buy.stripe.com/9B68wP9Cu7ndfqlfgy0ZW1Y", body)

    def test_api_integration_response(self):
        inquiry_info = {
            "name": "Marcus Holloway",
            "email": "mholloway@hollowaylegal.com",
            "firm": "Holloway Legal",
            "department": "Law Practice API Integration",
            "state_code": "FL",
            "message": "Can we ingest feeds via REST API into Filevine?"
        }
        subj, body, role = compose_elena_inquiry_response(inquiry_info, self.mock_state_cases)
        self.assertIn("REST API & Practice Management Integration", subj)
        self.assertIn("/api/v1/*.json", body)
        self.assertIn("Authorization: Bearer <API_TOKEN>", body)
        self.assertIn("https://surplusdocket.com/api-documentation.html", body)
        self.assertIn("Lead Technical Specialist & API Integrations", body)
        self.assertIn("https://buy.stripe.com/9B68wP9Cu7ndfqlfgy0ZW1Y", body)

    def test_clerk_correction_notice_response(self):
        inquiry_info = {
            "name": "Patricia Adams",
            "email": "clerk@orangecountyfl.gov",
            "firm": "Orange County Clerk of Court",
            "department": "Clerk Docket Correction / Notice",
            "state_code": "FL",
            "docket": "2024-TD-001955",
            "message": "Certificate of disbursement amended on case 2024-TD-001955."
        }
        subj, body, role = compose_elena_inquiry_response(inquiry_info, self.mock_state_cases)
        self.assertIn("County Registry Record Verification & Notice", subj)
        self.assertIn("2024-TD-001955", subj)
        self.assertIn("County Registry Operations Liaison", body)
        self.assertIn("certificate of disbursement", body)
        self.assertIn("highest judicial deference", body)

    def test_statutory_compliance_response(self):
        inquiry_info = {
            "name": "Gregory Stone",
            "email": "gstone@stonelitigation.com",
            "firm": "Stone Litigation Group",
            "department": "Statutory Compliance Verification",
            "state_code": "TX",
            "message": "How do you handle senior deed of trust filtering under Texas law?"
        }
        subj, body, role = compose_elena_inquiry_response(inquiry_info, self.mock_state_cases)
        self.assertIn("Statutory Compliance & Title Verification [Texas]", subj)
        self.assertIn("Senior Compliance & Research Specialist", body)
        self.assertIn("Tex. Tax Code § 34.04", body)
        self.assertIn("Senior Institutional Encumbrances", body)
        self.assertIn("does not provide formal legal opinions", body)

    def test_press_academic_research_response(self):
        inquiry_info = {
            "name": "Sarah Koenig",
            "email": "skoenig@lawreview.org",
            "firm": "Florida Law Review",
            "department": "Press / Academic Research",
            "state_code": "FL",
            "message": "We are examining county surplus forfeiture post-Tyler v. Hennepin."
        }
        subj, body, role = compose_elena_inquiry_response(inquiry_info, self.mock_state_cases)
        self.assertIn("Public Records & Academic Research Inquiry", subj)
        self.assertIn("Public Information Liaison", body)
        self.assertIn("Tyler v. Hennepin County, 598 U.S. 631", body)

    # -------------------------------------------------------------
    # 4. Contextual Query Handling & Bar Ethics
    # -------------------------------------------------------------
    def test_phone_skip_trace_query_explains_bar_solicitation_rules(self):
        inquiry_info = {
            "name": "Mark Alvarez",
            "email": "malvarez@alvarezlaw.com",
            "firm": "Alvarez Law",
            "department": "7-Day Institutional Practice Evaluation",
            "state_code": "FL",
            "message": "Do you provide phone numbers or skip tracing to call property owners directly?"
        }
        subj, body, role = compose_elena_inquiry_response(inquiry_info, self.mock_state_cases)
        self.assertIn("intentionally do not provide consumer phone numbers", body)
        self.assertIn("Florida Bar Rule 4-7.18", body)
        self.assertIn("compliant direct written correspondence", body)

    def test_expansion_state_quotes_national_feed(self):
        inquiry_info = {
            "name": "Brian Cole",
            "email": "bcole@colelawfirm.com",
            "firm": "Cole Legal Group",
            "department": "7-Day Institutional Practice Evaluation",
            "state_code": "NC",
            "message": "Interested in North Carolina tax foreclosure overages."
        }
        subj, body, role = compose_elena_inquiry_response(inquiry_info, self.mock_state_cases)
        self.assertIn("National Feed + REST API Tier ($449/month", body)
        self.assertIn("https://buy.stripe.com/9B68wP9Cu7ndfqlfgy0ZW1Y", body)
        self.assertNotIn("$249/month starting on Day 8", body)

    def test_intake_ropes_in_elena_when_justified_with_docket(self):
        """Inquiries with specific dockets/cases must rope in Elena Brooks on the research desk."""
        inquiry_info = {
            "name": "Thomas Sterling",
            "email": "tsterling@sterlinglegal.com",
            "firm": "Sterling Legal",
            "department": "Inquiries & Intake Desk",
            "state_code": "FL",
            "docket": "2024-TD-001955",
            "message": "We need to verify the registry balance and claim window on docket 2024-TD-001955."
        }
        subj, body, role = compose_elena_inquiry_response(inquiry_info, self.mock_state_cases)
        self.assertIn("Docket Research & Intake [2024-TD-001955]", subj)
        self.assertIn("Executive Intake Coordinator", role)
        self.assertIn("Aubrey Hayes", body)
        self.assertIn("forwarded your request to Elena Brooks on our docket research desk", body)
        self.assertIn("Elena will review your file and follow up directly", body)

    def test_intake_handles_general_pricing_without_roping_in_elena(self):
        """General questions (pricing, delivery schedule) are answered directly by Aubrey without roping in Elena."""
        inquiry_info = {
            "name": "Laura Jenkins",
            "email": "ljenkins@jenkinslaw.com",
            "firm": "Jenkins Law Group",
            "department": "Inquiries & Intake Desk",
            "state_code": "FL",
            "docket": "",
            "message": "What time are the morning CSV feeds delivered and how much is the subscription?"
        }
        subj, body, role = compose_elena_inquiry_response(inquiry_info, self.mock_state_cases)
        self.assertIn("Court Surplus Feeds [Florida]", subj)
        self.assertIn("Executive Intake Coordinator", role)
        self.assertIn("Aubrey Hayes", body)
        self.assertNotIn("forwarded your request to Elena Brooks", body)
        self.assertNotIn("I have logged your inquiry and roped in Elena Brooks", body)
        self.assertNotIn("Elena Brooks", body)
        self.assertIn("our intake desk will pull the records for your review", body)
        self.assertIn("7:00 AM EST", body)
        self.assertIn("$249/mo", body)

    # -------------------------------------------------------------
    # 5. MIME Draft Message Building & IMAP Compatibility
    # -------------------------------------------------------------
    def test_build_inquiry_draft_email(self):
        inquiry_info = {
            "name": "Victoria Reed",
            "email": "vreed@reedpropertylaw.com",
            "firm": "Reed Law Firm",
            "department": "Law Practice API Integration",
            "state_code": "FL",
            "message": "Looking to integrate via API."
        }
        draft_msg, subj, body, role = build_inquiry_draft_email(inquiry_info, self.mock_state_cases)
        self.assertIn("Marcus Chen", draft_msg["From"])
        self.assertIn("Victoria Reed", draft_msg["To"])
        self.assertIn("vreed@reedpropertylaw.com", draft_msg["To"])
        self.assertIn("Marcus Chen", draft_msg["Reply-To"])
        self.assertIn("marcus.chen@surplusdocket.com", draft_msg["Reply-To"])
        self.assertIn("REST API & Practice Management Integration", draft_msg["Subject"])
        self.assertIsNotNone(draft_msg["Message-ID"])
        self.assertIsNotNone(draft_msg["Date"])
        self.assertEqual(role, "Lead Technical Specialist & API Integrations | Surplus Docket")

    def test_build_inquiry_draft_email_personas(self):
        """Tests that drafts for different departments route to distinct employees."""
        scenarios = [
            ("7-Day Institutional Practice Evaluation", "Elena Brooks", "elena.brooks@surplusdocket.com"),
            ("Enterprise Feed Licensing", "Julian Vance", "julian.vance@surplusdocket.com"),
            ("Law Practice API Integration", "Marcus Chen", "marcus.chen@surplusdocket.com"),
            ("Clerk Docket Correction / Notice", "Rachel Holloway", "rachel.holloway@surplusdocket.com"),
            ("Statutory Compliance Verification", "Arthur Miller", "arthur.miller@surplusdocket.com"),
            ("Press / Academic Research", "Claire Montgomery", "claire.montgomery@surplusdocket.com"),
            ("General Publisher Inquiry", "Elena Brooks", "elena.brooks@surplusdocket.com"),
        ]
        for dept, exp_name, exp_email in scenarios:
            inq = {
                "name": "Test Counsel",
                "email": "counsel@testlaw.com",
                "department": dept,
                "state_code": "FL",
                "message": f"Testing {dept} routing."
            }
            draft_msg, subj, body, role = build_inquiry_draft_email(inq, self.mock_state_cases)
            self.assertIn(exp_name, draft_msg["From"])
            self.assertIn(exp_name, draft_msg["Reply-To"])
            self.assertIn(exp_email, draft_msg["Reply-To"])
            self.assertIn(exp_name, body)
            self.assertIn(exp_email, body)

    def test_extract_thread_history_and_context_continuity(self):
        """Tests thread context extraction across multi-turn email history."""
        # Turn 1: Original message inquiring about Orange County
        # Turn 2: Follow-up asking about pricing without repeating Orange County
        thread_email = """Can you confirm the cost and whether you offer invoicing for our accounting department?

On Sun, Sep 6, 2026 at 2:15 PM, Elena Brooks <elena.brooks@surplusdocket.com> wrote:
> Hi Counsel,
> Yes, we actively monitor Orange County (9th Judicial Circuit) as part of our statewide Florida feed.
>
> Best regards,
> Elena Brooks
"""
        ctx = extract_thread_history(thread_email)
        self.assertTrue(ctx["is_follow_up"])
        self.assertGreaterEqual(ctx["thread_turn_count"], 1)
        self.assertIn("Can you confirm the cost", ctx["latest_message"])
        self.assertNotIn("actively monitor Orange County", ctx["latest_message"])
        self.assertIn("Orange County", ctx["prior_history"])
        # Verify mentioned counties list detected Orange
        county_names = [c[1] for c in ctx["mentioned_counties"]]
        self.assertIn("Orange", county_names)

    def test_prospect_eligibility_accepts_statutory_inquiry(self):
        msg = Message()
        sender_email = "relay@formsubmit.co"
        subject = "[Surplus Docket Inquiry] General Publisher Inquiry — Direct (Arthur Morgan)"
        body = """SURPLUS DOCKET — LEGAL & STATUTORY CORRESPONDENCE MEMORANDUM
Name / Counsel: Arthur Morgan
Direct Email: arthur@morganlaw.com
Jurisdiction: Georgia
Department: General Publisher Inquiry
STATEMENT OF INQUIRY:
We would like to review sample excess funds records in Fulton County."""

        eligible, reason, target_info, inq_info = is_prospect_eligible(
            msg, sender_email, "FormSubmit", subject, body,
            self.directory, self.email_directory, self.domains
        )
        self.assertTrue(eligible, "Statutory inquiries must always be eligible")
        self.assertIsNotNone(inq_info)
        self.assertEqual(inq_info["email"], "arthur@morganlaw.com")
        self.assertEqual(inq_info["name"], "Arthur Morgan")
        self.assertEqual(inq_info["state_code"], "GA")


    def test_parse_google_voice_voicemail(self):
        sender_email = "voice-noreply@google.com"
        subject = "New voicemail from (508) 419-3178 at 4:15 PM"
        body = """New voicemail from (508) 419-3178:

"Hi, this is Marcus Davis with Davis Property Law. We are reviewing foreclosure surplus records in Orange County Florida. Can you follow up with pricing for our office?"

Play message: https://voice.google.com/message/12345"""

        inq = parse_google_voice_voicemail(sender_email, subject, body)
        self.assertIsNotNone(inq)
        self.assertEqual(inq["phone"], "(508) 419-3178")
        self.assertEqual(inq["state_code"], "FL")
        self.assertIn("Marcus Davis", inq["name"])
        self.assertTrue(inq["is_voicemail"])
        self.assertIn("Orange County Florida", inq["message"])

        # Test eligibility accepts it
        msg = Message()
        eligible, reason, target_info, inq_info = is_prospect_eligible(
            msg, sender_email, "Google Voice", subject, body,
            self.directory, self.email_directory, self.domains
        )
        self.assertTrue(eligible)
        self.assertEqual(inq_info["phone"], "(508) 419-3178")

    def test_extract_spoken_email_varieties(self):
        """Validates normalization of spoken emails and Google Voice STT transcriptions."""
        # STT merged format
        self.assertEqual(
            extract_spoken_email("my number I mean my email is the sandwich fitnessgmailcom If you can do that"),
            "sandwichfitness@gmail.com"
        )
        self.assertEqual(
            extract_spoken_email("My email address is sandwich fitnessgmailcom Just give me a general overview"),
            "sandwichfitness@gmail.com"
        )
        # Spoken spaces
        self.assertEqual(
            extract_spoken_email("Call me back or email me at dave miller gmail com"),
            "davemiller@gmail.com"
        )
        # Spoken dot and at
        self.assertEqual(
            extract_spoken_email("Hi this is John Doe my email is john dot doe at legalfirm dot com"),
            "john.doe@legalfirm.com"
        )
        # Literal email
        self.assertEqual(
            extract_spoken_email("Please send to sandwichfitness@gmail.com right away"),
            "sandwichfitness@gmail.com"
        )

    def test_parse_google_voice_voicemail_david_mahler_and_dave_miller(self):
        """Verifies parsing of actual user voicemails from Google Voice."""
        sender_email = "voice-noreply@google.com"

        # Message 1: Dave Miller
        sub1 = "New voicemail from (508) 517-8981 at 5:02 PM"
        body1 = """New voicemail from (508) 517-8981:

"Hi this is Dave Miller Can you just give me a general overview of your services my number I mean my email is the sandwich fitnessgmailcom If you can do that thank you"

Play message: https://voice.google.com/message/4955"""

        vm1 = parse_google_voice_voicemail(sender_email, sub1, body1)
        self.assertIsNotNone(vm1)
        self.assertEqual(vm1["name"], "Dave Miller")
        self.assertEqual(vm1["email"], "sandwichfitness@gmail.com")
        self.assertEqual(vm1["phone"], "(508) 517-8981")
        self.assertTrue(vm1["is_voicemail"])

        # Message 2: David Mahler
        sub2 = "New voicemail from (508) 517-8981 at 5:06 PM"
        body2 = """New voicemail from (508) 517-8981:

"My name my name is David Mahler My email address is sandwich fitnessgmailcom Just give me a general overview of what you offer For the you know different places in Georgia"

Play message: https://voice.google.com/message/4956"""

        vm2 = parse_google_voice_voicemail(sender_email, sub2, body2)
        self.assertIsNotNone(vm2)
        self.assertEqual(vm2["name"], "David Mahler")
        self.assertEqual(vm2["email"], "sandwichfitness@gmail.com")
        self.assertEqual(vm2["phone"], "(508) 517-8981")
        self.assertEqual(vm2["state_code"], "GA")
        self.assertEqual(vm2["jurisdiction"], "Georgia")
        self.assertTrue(vm2["is_voicemail"])

    def test_voicemail_general_overview_does_not_rope_in_elena(self):
        """
        Inbound voicemail requesting general overview of services / Georgia
        must be handled 100% by Aubrey Hayes without roping in Elena Brooks.
        """
        vm_inquiry = {
            "name": "David Mahler",
            "email": "sandwichfitness@gmail.com",
            "phone": "(508) 517-8981",
            "firm": "",
            "department": "Inquiries & Intake Desk",
            "jurisdiction": "Georgia",
            "state_code": "GA",
            "docket": "",
            "ref": "GV-VM-5085178981",
            "message": "[Phone Inquiry via Google Voice (508) 419-3178]: My name my name is David Mahler My email address is sandwich fitnessgmailcom Just give me a general overview of what you offer For the you know different places in Georgia",
            "is_voicemail": True,
        }
        subj, body, role = compose_elena_inquiry_response(vm_inquiry, self.mock_state_cases)
        self.assertIn("Court Surplus Feeds [Georgia]", subj)
        self.assertIn("Executive Intake Coordinator", role)
        self.assertIn("Aubrey Hayes", body)
        self.assertIn("O.C.G.A. § 48-4-5", body)
        self.assertNotIn("forwarded your request to Elena Brooks", body)
        self.assertNotIn("Elena Brooks", body, "Elena Brooks must NOT be mentioned when inquiry is general overview")
        self.assertIn("our intake desk will pull the records for your review", body)
        self.assertIn("Hi David,", body)

    def test_voicemail_specific_docket_ropes_in_elena(self):
        """
        Inbound voicemail with specific docket number DOES rope in Elena Brooks.
        """
        vm_inquiry = {
            "name": "David Mahler",
            "email": "sandwichfitness@gmail.com",
            "phone": "(508) 517-8981",
            "firm": "",
            "department": "Inquiries & Intake Desk",
            "jurisdiction": "Florida",
            "state_code": "FL",
            "docket": "2024-TD-001955",
            "message": "[Phone Inquiry via Google Voice (508) 419-3178]: Can you check docket 2024-TD-001955 in Orange County?",
            "is_voicemail": True,
        }
        subj, body, role = compose_elena_inquiry_response(vm_inquiry, self.mock_state_cases)
        self.assertIn("Docket Research & Intake [2024-TD-001955]", subj)
        self.assertIn("Elena Brooks on our docket research desk", body)
        self.assertIn("Elena will review your file and follow up directly", body)


if __name__ == "__main__":
    unittest.main()
