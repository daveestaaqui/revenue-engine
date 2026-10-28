import unittest
from pathlib import Path
from compliance.ground_truth_gatekeeper import GroundTruthGatekeeper

BASE_DIR = Path(__file__).resolve().parent.parent


class TestGroundTruthGatekeeper(unittest.TestCase):
    """
    Unit tests for the Ground Truth Gatekeeper.
    Guarantees zero tolerance for fictitious case numbers, unverified title claims,
    deceptive persona hooks, mismatched attorney targets, and broken URLs.
    """

    def test_rejects_synthetic_case_prefixes_in_leads(self):
        banned_prefixes = ["GW-R7233-032", "DK-18-112-04-04", "SD-7102-0263", "LA-ITEM-27-2061", "APN-12345"]
        for bad_case in banned_prefixes:
            lead = {
                "State": "FL",
                "County": "Orange",
                "Case_or_TaxDeed_No": bad_case,
                "Parcel_ID": "12345",
                "Surplus_Balance_USD": 50000.0,
                "Clerk_Verification_URL": "https://www.hillsclerk.com/taxdeeds",
            }
            ok, errors = GroundTruthGatekeeper.validate_lead_record(lead)
            self.assertFalse(ok, f"Expected failure for synthetic case '{bad_case}'")
            self.assertTrue(any("Synthetic case number prefix" in e for e in errors))

    def test_rejects_georgia_non_judicial_court_case_numbers(self):
        # GA tax sales under O.C.G.A. § 48-4-5 are administrative and tracked by Parcel_ID
        lead = {
            "State": "GA",
            "County": "Gwinnett",
            "Case_or_TaxDeed_No": "TAX-SALE-2024",
            "Parcel_ID": "R7233 032",
            "Surplus_Balance_USD": 768395.0,
            "Clerk_Verification_URL": "https://www.gwinnetttaxcommissioner.com",
        }
        ok, errors = GroundTruthGatekeeper.validate_lead_record(lead)
        self.assertFalse(ok)
        self.assertTrue(any("Georgia record has non-judicial case number" in e for e in errors))

    def test_rejects_california_non_judicial_court_case_numbers(self):
        # CA tax sales under Cal. Rev. & Tax Code § 4675 are administrative and tracked by Parcel_ID
        lead = {
            "State": "CA",
            "County": "San Diego",
            "Case_or_TaxDeed_No": "CA-SALE-0263",
            "Parcel_ID": "360-150-12-00",
            "Surplus_Balance_USD": 881663.0,
            "Clerk_Verification_URL": "https://www.sdttc.com",
        }
        ok, errors = GroundTruthGatekeeper.validate_lead_record(lead)
        self.assertFalse(ok)
        self.assertTrue(any("California record has non-judicial case number" in e for e in errors))

    def test_accepts_clean_administrative_records_with_parcel_id(self):
        lead_ga = {
            "State": "GA",
            "County": "Gwinnett",
            "Case_or_TaxDeed_No": "",
            "Parcel_ID": "R7233 032",
            "Surplus_Balance_USD": 768395.0,
            "Clerk_Verification_URL": "https://www.gwinnetttaxcommissioner.com",
        }
        ok, errors = GroundTruthGatekeeper.validate_lead_record(lead_ga)
        self.assertTrue(ok, f"Expected clean GA record to pass, got: {errors}")

        lead_ca = {
            "State": "CA",
            "County": "San Diego",
            "Case_or_TaxDeed_No": "",
            "Parcel_ID": "360-150-12-00",
            "Surplus_Balance_USD": 881663.0,
            "Clerk_Verification_URL": "https://www.sdttc.com",
        }
        ok, errors = GroundTruthGatekeeper.validate_lead_record(lead_ca)
        self.assertTrue(ok, f"Expected clean CA record to pass, got: {errors}")

    def test_accepts_authentic_judicial_cases(self):
        # Hillsborough Circuit Court case
        lead_fl = {
            "State": "FL",
            "County": "Hillsborough",
            "Case_or_TaxDeed_No": "24-CA-001234",
            "Parcel_ID": "",
            "Surplus_Balance_USD": 125000.0,
            "Clerk_Verification_URL": "https://www.hillsclerk.com/taxdeeds",
        }
        ok, errors = GroundTruthGatekeeper.validate_lead_record(lead_fl)
        self.assertTrue(ok, f"Expected FL judicial case to pass, got: {errors}")

        # Dallas District Court case
        lead_tx = {
            "State": "TX",
            "County": "Dallas",
            "Case_or_TaxDeed_No": "TX-22-00720",
            "Parcel_ID": "",
            "Surplus_Balance_USD": 85000.0,
            "Clerk_Verification_URL": "https://www.dallascounty.org",
        }
        ok, errors = GroundTruthGatekeeper.validate_lead_record(lead_tx)
        self.assertTrue(ok, f"Expected TX judicial case to pass, got: {errors}")

    def test_rejects_dead_hillsclerk_url(self):
        lead = {
            "State": "FL",
            "County": "Hillsborough",
            "Case_or_TaxDeed_No": "24-CA-001234",
            "Parcel_ID": "",
            "Surplus_Balance_USD": 10000.0,
            "Clerk_Verification_URL": "https://www.hillsclerk.com/records-and-reports/tax-deed-surplus",
        }
        ok, errors = GroundTruthGatekeeper.validate_lead_record(lead)
        self.assertFalse(ok)
        self.assertTrue(any("known dead/404 URL" in e for e in errors))

    def test_rejects_mismatched_attorney_targets(self):
        # Stephen M. Reba (Criminal defense / Habeas corpus)
        ok, errors = GroundTruthGatekeeper.validate_outreach_message(
            to_email="stephen@rebalaw.com",
            to_name="Stephen",
            firm="Reba Law LLC",
            subject="Gwinnett County tax sale surplus",
            body="Hi Stephen, Best regards, David Mahler surplusdocket.com david@surplusdocket.com",
        )
        self.assertFalse(ok)
        self.assertTrue(any("mismatched practice" in e for e in errors))

        # Dennis P. Block (Evictions only)
        ok, errors = GroundTruthGatekeeper.validate_outreach_message(
            to_email="dennis@evict123.com",
            to_name="Dennis",
            firm="Dennis P. Block & Associates",
            subject="Los Angeles County surplus",
            body="Hi Dennis, Best regards, David Mahler surplusdocket.com david@surplusdocket.com",
        )
        self.assertFalse(ok)
        self.assertTrue(any("mismatched practice" in e for e in errors))

    def test_rejects_unverified_title_claims(self):
        bad_phrases = [
            "Senior mortgages are cleared upstream and the claim window is open.",
            "All senior mortgages cleared upstream.",
            "We scrub raw county ledgers to purge senior liens.",
            "This property is free and clear of all liens.",
            "Guaranteed unencumbered balance.",
        ]
        for phrase in bad_phrases:
            ok, errors = GroundTruthGatekeeper.validate_outreach_message(
                to_email="counsel@propertysurplusfirm.com",
                to_name="Counsel",
                firm="Property Surplus Law Group",
                subject="Surplus Notice",
                body=f"Hi Counsel,\n\n{phrase}\n\nBest regards,\nDavid Mahler\nsurplusdocket.com\ndavid@surplusdocket.com",
            )
            self.assertFalse(ok, f"Expected rejection for phrase '{phrase}'")
            self.assertTrue(any("Unverified title assertion" in e for e in errors))

    def test_rejects_deceptive_persona_hooks(self):
        bad_personas = [
            "Elena Brooks\nSenior Docket Specialist",
            "Are you handling surplus recovery petitions in Gwinnett County? If so, happy to send over the docket summary and filing notes.",
            "elena.brooks@surplusdocket.com",
        ]
        for phrase in bad_personas:
            ok, errors = GroundTruthGatekeeper.validate_outreach_message(
                to_email="counsel@propertysurplusfirm.com",
                to_name="Counsel",
                firm="Property Surplus Law Group",
                subject="Surplus Notice",
                body=f"Hi Counsel,\n\n{phrase}\n\nBest regards,\nDavid Mahler\nsurplusdocket.com\ndavid@surplusdocket.com",
            )
            self.assertFalse(ok, f"Expected rejection for persona hook '{phrase}'")
            self.assertTrue(any("Deceptive persona" in e for e in errors))

    def test_accepts_clean_compliant_outreach(self):
        clean_subject = "Hillsborough County surplus filing — 24-CA-001234"
        clean_body = (
            "Hi Sarah,\n\n"
            "Came across Jenkins Law while reviewing active foreclosure and surplus litigation counsel in Florida.\n\n"
            "We monitor public surplus ledgers across Florida. In Hillsborough County, the county court registry "
            "lists a $125,000 unclaimed balance on Case 24-CA-001234. Under Fla. Stat. § 197.582, excess proceeds "
            "remain subject to statutory lien priority and claim verification with the clerk/tax commissioner.\n\n"
            "If your firm handles surplus recovery petitions in Hillsborough County, you can view the official public "
            "listing directly here: https://www.hillsclerk.com/taxdeeds\n\n"
            "Best regards,\n\n"
            "David Mahler\n"
            "Surplus Docket Public Records Intelligence\n"
            "surplusdocket.com\n"
            "david@surplusdocket.com"
        )
        ok, errors = GroundTruthGatekeeper.validate_outreach_message(
            to_email="sarah@jenkinslaw.com",
            to_name="Sarah",
            firm="Jenkins Law Group",
            subject=clean_subject,
            body=clean_body,
        )
        self.assertTrue(ok, f"Expected clean outreach to pass, got: {errors}")

    def test_require_bar_verified_enforcement(self):
        clean_subject = "Hillsborough County surplus filing — 24-CA-001234"
        clean_body = (
            "Hi Counsel,\n\n"
            "In Hillsborough County, the county court registry lists a $125,000.00 unclaimed balance on Case 24-CA-001234. "
            "Under Fla. Stat. § 197.582, excess proceeds remain subject to statutory lien priority.\n\n"
            "Best regards,\nDavid Mahler\nsurplusdocket.com\ndavid@surplusdocket.com"
        )
        # Unverified recipient must fail when require_bar_verified=True
        ok, errors = GroundTruthGatekeeper.validate_outreach_message(
            to_email="unverified@randomlawfirm.com",
            to_name="Counsel",
            firm="Random Law Firm",
            subject=clean_subject,
            body=clean_body,
            require_bar_verified=True,
        )
        self.assertFalse(ok)
        self.assertTrue(any("not in VERIFIED_BAR_REGISTRY" in e for e in errors))

        # Verified Bar recipient must pass when require_bar_verified=True
        ok2, errors2 = GroundTruthGatekeeper.validate_outreach_message(
            to_email="weidner@mattweidnerlaw.com",
            to_name="Matthew D. Weidner",
            firm="Matthew D. Weidner, P.A.",
            subject=clean_subject,
            body=clean_body,
            require_bar_verified=True,
        )
        self.assertTrue(ok2, f"Expected verified Bar attorney to pass, got: {errors2}")

    def test_lead_cross_check_in_outreach(self):
        lead = {
            "State": "FL",
            "County": "Hillsborough",
            "Case_or_TaxDeed_No": "24-CA-001234",
            "Parcel_ID": "",
            "Surplus_Balance_USD": 125000.0,
            "Clerk_Verification_URL": "https://www.hillsclerk.com/taxdeeds",
        }
        # Mismatched dollar amount ($999,999.00 vs $125,000.00) must fail
        bad_body = (
            "Hi Matthew,\n\n"
            "In Hillsborough County, the court registry lists a $999,999.00 balance on Case 24-CA-001234.\n\n"
            "Best regards,\nDavid Mahler\nsurplusdocket.com\ndavid@surplusdocket.com"
        )
        ok, errors = GroundTruthGatekeeper.validate_outreach_message(
            to_email="weidner@mattweidnerlaw.com",
            to_name="Matthew D. Weidner",
            firm="Matthew D. Weidner, P.A.",
            subject="Hillsborough County surplus — Case 24-CA-001234",
            body=bad_body,
            lead=lead,
        )
        self.assertFalse(ok)
        self.assertTrue(any("Outreach body dollar amount does not match lead ground-truth balance" in e for e in errors))

    def test_reconciliation_math_validation(self):
        # Mismatched itemized deductions sum must be caught by validate_lead_record
        bad_lead = {
            "State": "CA",
            "County": "San Diego",
            "Case_or_TaxDeed_No": "",
            "Parcel_ID": "360-150-12-00",
            "Surplus_Balance_USD": 881663.35,
            "Clerk_Verification_URL": "https://www.sdttc.com",
            "Financial_Reconciliation": {
                "Gross_Sale_Price_USD": 890100.00,
                "County_Deductions_USD": 8436.65,
                "Net_Excess_Proceeds_USD": 881663.35,
                "Itemized_Deductions": [
                    {"label": "Property Taxes", "amount": 5000.00},
                    {"label": "Extra Erroneous Tax", "amount": 4416.20},
                ],
            },
        }
        ok, errors = GroundTruthGatekeeper.validate_lead_record(bad_lead)
        self.assertFalse(ok)
        self.assertTrue(any("Itemized deductions sum" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
