"""
Unit Tests for Surplus Docket Autonomous Bug Resolver & Executive Email Sentinel
"""

import unittest
from pathlib import Path
from compliance.autonomous_bug_resolver import (
    classify_issue,
    audit_statutory_rules,
    audit_site_links_and_assets,
    verify_python_compilation,
    attempt_self_healing,
    build_email_content,
    REPO_ROOT
)


class TestAutonomousBugResolver(unittest.TestCase):

    def test_classify_issue_categories(self):
        # Broken link
        res1 = classify_issue("Broken link on pricing page", "Getting 404 on /pricing.html")
        self.assertIn("broken_link", res1["categories"])
        self.assertIn("/pricing.html", res1["mentioned_files"])

        # Statutory calculator
        res2 = classify_issue("Florida statutory fee cap incorrect", "Fla. Stat. 197.582 shows 25% instead of 20%")
        self.assertIn("statutory_calculation", res2["categories"])

        # API integration
        res3 = classify_issue("REST API endpoint error", "/api/v1/feed.json returns invalid json format")
        self.assertIn("api_integration", res3["categories"])

        # Stripe billing
        res4 = classify_issue("Checkout error on Stripe portal", "Stripe checkout portal button fails")
        self.assertIn("billing_checkout", res4["categories"])

        # General
        res5 = classify_issue("Question about coverage", "Can you explain Florida records?")
        self.assertIn("general_integrity", res5["categories"])

    def test_statutory_rules_verification(self):
        result = audit_statutory_rules()
        self.assertTrue(result["is_healthy"])
        self.assertEqual(result["status"], "verified")
        self.assertGreaterEqual(result["jurisdictions_count"], 6)
        self.assertEqual(len(result["missing_states"]), 0)

    def test_site_links_and_assets(self):
        result = audit_site_links_and_assets()
        self.assertTrue(result["is_healthy"], f"Broken links/assets found: {result['broken_links']}")
        self.assertGreaterEqual(result["html_pages_scanned"], 40)
        self.assertEqual(len(result["broken_links"]), 0)
        self.assertEqual(len(result["broken_assets"]), 0)

    def test_python_compilation(self):
        result = verify_python_compilation()
        self.assertTrue(result["is_healthy"], f"Syntax errors found: {result['errors']}")
        self.assertGreater(result["files_checked"], 50)
        self.assertEqual(len(result["errors"]), 0)

    def test_build_email_content(self):
        dummy_triage = {
            "issue_number": 42,
            "issue_title": "404 on old link",
            "resolution_status": "RESOLVED",
            "reporter": "tester",
            "categories": ["broken_link"],
            "healed_actions": [{"file": "site/test.html", "issue": "Broken link", "action": "Updated to /#pricing"}],
            "test_results": {"passed": True, "test_count": 92, "elapsed_seconds": 0.45},
            "link_results": {"html_pages_scanned": 43, "total_links_checked": 1377, "broken_links": [], "broken_assets": []},
            "python_health": {"files_checked": 473, "is_healthy": True, "errors": []}
        }
        text_content, html_content = build_email_content(dummy_triage)
        self.assertIn("SURPLUS DOCKET — AUTONOMOUS BUG RESOLUTION REPORT", text_content)
        self.assertIn("Issue Reference: #42", text_content)
        self.assertIn("Updated to /#pricing", text_content)
        self.assertIn("<!DOCTYPE html>", html_content)
        self.assertIn("Surplus Docket Intelligence Sentinel", html_content)
        self.assertIn("RESOLVED", html_content)


if __name__ == "__main__":
    unittest.main()
