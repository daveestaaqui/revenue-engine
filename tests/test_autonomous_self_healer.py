#!/usr/bin/env python3
"""
Unit Tests for Astra's Autonomous Self-Healing Architecture
===========================================================
Tests cover:
1. Pipeline Self-Healer: Fuzzy column aliasing, clerk link healing, currency sanitization
2. Generic Email & Bounce Elimination: info@lw.com rejection, generic mailbox filter
3. Zero-Cost AI Circuit Breaker: 403 / 429 quota graceful heuristic fallback
4. Subscriber Self-Reconciler: Duplicate merging, tier enforcement, expired trial transitions
5. Bug Resolver Self-Healing: Sitemap auto-reconciliation, repealed statute repair
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Module Imports
from portal.pipeline_self_healer import (
    self_heal_record,
    clean_currency_value,
    heal_clerk_verification_url,
    generate_clio_matter_export,
    generate_filevine_lead_export,
    audit_and_heal_all_feeds,
    VERIFIED_COUNTY_CLERK_REGISTRIES
)
from outreach.generate_drafts import (
    is_valid_direct_email,
    get_unsubscribed_domains,
    BLOCKED_OUTREACH_DOMAINS,
    GENERIC_EMAIL_PREFIXES
)
from portal.ai_provider import (
    generate_text,
    _deterministic_text_fallback,
    ZERO_COST_MODE
)
from portal.sync_stripe_subscribers import (
    reconcile_and_repair_subscribers
)
from compliance.autonomous_bug_resolver import (
    reconcile_and_repair_sitemap,
    heal_repealed_statutes,
    attempt_self_healing
)


class TestPipelineSelfHealer(unittest.TestCase):
    """Verifies that public records with drifting schemas or malformed data are healed."""

    def test_fuzzy_column_aliasing(self):
        """Tests that raw county headers with differing column names are normalized."""
        raw_row = {
            "Docket Number": "2024-TD-009999",
            "Excess Proceeds": "$45,000.50",
            "Property Address": "742 Evergreen Terrace",
            "Jurisdiction": "Florida",
            "County Name": "Orange",
            "Sale Date": "2024-05-15",
            "Defendant": "Simpson, Homer",
        }
        normalized = self_heal_record(raw_row, default_state="FL", default_county="Orange")
        self.assertEqual(normalized["Case_or_TaxDeed_No"], "2024-TD-009999")
        self.assertEqual(normalized["Surplus_Balance_USD"], 45000.50)
        self.assertEqual(normalized["Owner_Name"], "Simpson, Homer")
        self.assertEqual(normalized["County"], "Orange")
        self.assertEqual(normalized["State"], "FL")
        self.assertIn("myorangeclerk.com", normalized["Clerk_Verification_URL"])

    def test_clean_currency_value(self):
        """Tests robust parsing of messy currency amounts including negative/parenthetical."""
        self.assertEqual(clean_currency_value("$125,400.00"), 125400.0)
        self.assertEqual(clean_currency_value("  $1,250.75  "), 1250.75)
        self.assertEqual(clean_currency_value("(500.00)"), 0.0)
        self.assertEqual(clean_currency_value("-1200"), 0.0)
        self.assertEqual(clean_currency_value("UNKNOWN"), 0.0)
        self.assertEqual(clean_currency_value(None), 0.0)
        self.assertEqual(clean_currency_value(85000), 85000.0)

    def test_heal_clerk_verification_url(self):
        """Tests healing of placeholder, broken, or missing clerk URLs."""
        # Malformed / placeholder URL gets replaced with county official root
        healed_orange = heal_clerk_verification_url("Orange", "FL", "http://example.com/broken")
        self.assertEqual(healed_orange, VERIFIED_COUNTY_CLERK_REGISTRIES[("FL", "Orange")])

        # Valid county portal URL is preserved
        valid_url = "https://www.myorangeclerk.com/Records-Search/Tax-Deed/2024-TD-1234"
        self.assertEqual(heal_clerk_verification_url("Orange", "FL", valid_url), valid_url)

        # Empty URL gets county portal
        healed_dallas = heal_clerk_verification_url("Dallas", "TX", "")
        self.assertEqual(healed_dallas, VERIFIED_COUNTY_CLERK_REGISTRIES[("TX", "Dallas")])

    def test_clio_and_filevine_generators(self):
        """Tests that legal practice exports (Clio & Filevine) generate with required headers."""
        sample_leads = [
            {
                "Case_or_TaxDeed_No": "2024-TD-001001",
                "Surplus_Balance_USD": 95000.0,
                "Owner_Name": "Arthur Pendelton",
                "Property_Address": "100 Camelot Way, Orlando, FL",
                "County": "Orange",
                "State": "FL",
                "Clerk_Verification_URL": "https://www.myorangeclerk.com/",
                "Claim_Deadline_Date": "2025-06-01",
                "Est_Finder_Fee_USD": 19000.0,
                "Statute_Citation": "Fla. Stat. § 197.582"
            }
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            clio_path = Path(tmpdir) / "Clio_Matter_Import.csv"
            filevine_path = Path(tmpdir) / "Filevine_Lead_Import.csv"

            generate_clio_matter_export(sample_leads, clio_path)
            generate_filevine_lead_export(sample_leads, filevine_path)

            self.assertTrue(clio_path.exists())
            self.assertTrue(filevine_path.exists())

            clio_content = clio_path.read_text(encoding="utf-8")
            self.assertIn("Matter Description", clio_content)
            self.assertIn("Pending Surplus USD", clio_content)
            self.assertIn("Arthur Pendelton", clio_content)

            filevine_content = filevine_path.read_text(encoding="utf-8")
            self.assertIn("Project Name", filevine_content)
            self.assertIn("Estimated Value", filevine_content)


class TestGenericEmailAndBounceFilter(unittest.TestCase):
    """Verifies that generic mailboxes and bounce-prone mega-firms are strictly excluded."""

    def test_reject_info_at_lw(self):
        """Verifies that info@lw.com (which caused previous 550 bounce) is blocked."""
        self.assertFalse(is_valid_direct_email("info@lw.com"))

    def test_reject_generic_prefixes(self):
        """Tests that all generic prefixes (info, contact, admin, support, office, etc.) are blocked."""
        test_cases = [
            "info@lawfirm.com",
            "contact@jonesday.com",
            "admin@floridalegal.com",
            "support@lawyers.org",
            "office@smithlaw.com",
            "reception@chicagolaw.com",
            "intake@recoverylaw.com",
            "inquiry@texascounsel.com",
            "general@firm.net",
            "team@probatepros.com",
        ]
        for email in test_cases:
            self.assertFalse(is_valid_direct_email(email), f"Expected {email} to be rejected as generic")

    def test_allow_direct_named_counsel_emails(self):
        """Tests that verified personal/partner attorney emails are accepted."""
        valid_emails = [
            "michael@davislaw.com",
            "dennis@evict123.com",
            "jennifer.smith@smithlawpa.com",
            "r.johnson@johnsonforeclosure.com",
            "counsel_davis@texaslitigators.com",
        ]
        for email in valid_emails:
            self.assertTrue(is_valid_direct_email(email), f"Expected {email} to be accepted as direct counsel")

    def test_bounced_emails_seed_loaded(self):
        """Verifies that outreach/bounced_emails.json is integrated into unsubscribe list."""
        bounced_and_unsub = get_unsubscribed_domains()
        self.assertIn("info@lw.com", bounced_and_unsub)


class TestOpenAIZeroCostGuardrail(unittest.TestCase):
    """Verifies that zero OpenAI spend is enforced and 403 / 429 triggers graceful fallback."""

    def test_zero_cost_mode_constant(self):
        """Verifies that ZERO_COST_MODE is activated."""
        self.assertTrue(ZERO_COST_MODE)

    def test_heuristic_fallback_extraction(self):
        """Tests deterministic heuristic extraction when OpenAI is unauthorized or exhausted."""
        prompt = (
            "Analyze surplus record in json format for John Doe in Orange County, FL. "
            "Docket number: 2024-TD-001234, surplus amount: $75,000.00. "
            "Email: counsel@floridalaw.com, phone: 407-555-0199."
        )
        result_json = _deterministic_text_fallback(prompt)
        parsed = json.loads(result_json)
        self.assertEqual(parsed.get("state"), "FL")
        self.assertEqual(parsed.get("docket"), "2024-TD-001234")
        self.assertEqual(parsed.get("surplus_amount"), "$75,000.00")
        self.assertEqual(parsed.get("email"), "counsel@floridalaw.com")
        self.assertEqual(parsed.get("phone"), "407-555-0199")

    def test_generate_text_openai_403_fallback(self):
        """Verifies generate_text does not crash on OpenAI 403 Forbidden and returns heuristic result."""
        import urllib.error
        env = {
            "OPENAI_API_KEY": "sk-test-key-which-returns-403"
        }
        # Simulate HTTP 403 error from OpenAI API
        mock_error = urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=None
        )
        with patch.dict(os.environ, env, clear=True):
            with patch("urllib.request.urlopen", side_effect=mock_error):
                result = generate_text("Analyze Case # 2024-TD-005555 surplus balance $120,000 in Dallas, TX in json")
                self.assertIsNotNone(result)
                parsed = json.loads(result)
                self.assertEqual(parsed.get("state"), "TX")
                self.assertEqual(parsed.get("docket"), "2024-TD-005555")


class TestSubscriberSelfReconciliation(unittest.TestCase):
    """Verifies automated Stripe subscriber reconciliation, deduplication, and trial expiration."""

    def test_reconcile_and_repair_subscribers(self):
        """Tests that subscriber records are casing-normalized, deduped, and expired trials transitioned."""
        raw_subscribers = [
            {
                "email": "LAWYER@FIRM.COM",  # Uppercase
                "tier": "tri_state",
                "status": "active",
                "days_active": 4
            },
            {
                "email": "lawyer@firm.com",  # Duplicate lowercase
                "tier": "tri_state",
                "status": "active",
                "days_active": 4
            },
            {
                "email": "expired_trial@probate.org",
                "tier": "tri_state_trial",
                "status": "trialing",
                "days_active": 9  # Expired (> 7.5 days)
            },
            {
                "email": "active_trial@taxlaw.net",
                "tier": "six_state_api_trial",
                "status": "trialing",
                "days_active": 3  # Healthy trial
            }
        ]
        result = reconcile_and_repair_subscribers(raw_subscribers, write_back=False)
        reconciled = result["subscribers"]

        # Should dedupe to 3 accounts
        self.assertEqual(len(reconciled), 3)

        by_email = {s["email"]: s for s in reconciled}

        # Check lowercase normalization
        self.assertIn("lawyer@firm.com", by_email)
        self.assertEqual(by_email["lawyer@firm.com"]["status"], "active")

        # Check expired trial transition
        self.assertIn("expired_trial@probate.org", by_email)
        self.assertEqual(by_email["expired_trial@probate.org"]["status"], "EXPIRED_TRIAL")

        # Check active trial remains trialing
        self.assertIn("active_trial@taxlaw.net", by_email)
        self.assertEqual(by_email["active_trial@taxlaw.net"]["status"], "trialing")


class TestAutonomousBugResolverExpansion(unittest.TestCase):
    """Verifies that sitemap auto-reconciliation and statute citation healing operate flawlessly."""

    def test_sitemap_reconciliation_in_sync(self):
        """Tests that sitemap reconciliation returns in_sync when all files are registered."""
        report = reconcile_and_repair_sitemap(dry_run=True)
        self.assertIn(report["status"], ("in_sync", "reconciled"))
        self.assertEqual(report["removed"], [])

    def test_heal_repealed_statutes_detection(self):
        """Tests that heal_repealed_statutes accurately detects and replaces T.C.A. § 67-5-2510."""
        with tempfile.TemporaryDirectory() as tmpdir:
            site_sub = Path(tmpdir) / "site"
            site_sub.mkdir(parents=True, exist_ok=True)
            sample_file = site_sub / "sample_statute_note.txt"
            sample_file.write_text(
                "Under Tennessee law, excess proceeds were governed by T.C.A. § 67-5-2510.\n"
                "Attorneys should verify claims under 67-5-2510.",
                encoding="utf-8"
            )

            # Test replacement in temp dir
            with patch("compliance.autonomous_bug_resolver.REPO_ROOT", Path(tmpdir)):
                with patch("compliance.autonomous_bug_resolver.SITE_DIR", site_sub):
                    fixes = heal_repealed_statutes(dry_run=False)
                    # When run against isolated directory containing repealed statute:
                    text_after = sample_file.read_text(encoding="utf-8")
                    # Should contain 67-5-2501
                    self.assertIn("67-5-2501", text_after)
                    self.assertEqual(len(fixes), 1)


if __name__ == "__main__":
    unittest.main()
