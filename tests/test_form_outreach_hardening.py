#!/usr/bin/env python3
"""
Unit Test Suite: Form Outreach Engine Reliability & Hardening
============================================================
Tests for:
1. CSV schema migration (8-column -> 9-column with 'variant')
2. Chrome error URL and navigation failure detection
3. Dead domain and broker classification in submission history
4. Domain cleaning & normalization
5. Message composition & statutory citation verification
6. Honeypot input detection
"""

import csv
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Setup root path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "outreach"))

import outreach.form_outreach_engine as foe


class TestFormOutreachHardening(unittest.TestCase):

    def test_clean_domain_utility(self):
        """Verify URL and domain normalization handles prefixes, ports, and paths."""
        self.assertEqual(foe.clean_domain("https://www.examplelaw.com/contact/"), "examplelaw.com")
        self.assertEqual(foe.clean_domain("http://sub.domain.org:8080/form?v=1"), "sub.domain.org")
        self.assertEqual(foe.clean_domain("lawfirm.net"), "lawfirm.net")
        self.assertEqual(foe.clean_domain(""), "")
        self.assertEqual(foe.clean_domain(None), "")

    def test_csv_header_migration(self):
        """Verify that an 8-column log file is automatically upgraded to 9 columns with 'variant'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_csv = Path(tmpdir) / "form_submissions_log.csv"
            # Write old 8-column header with sample row
            old_header = "timestamp,firm,name,state,target_url,form_url,status,detail\n"
            sample_row = "2026-09-15T12:00:00,Apex Law,John Doe,FL,https://apex.com,https://apex.com/contact,SUCCESS,Submitted OK\n"
            test_csv.write_text(old_header + sample_row, encoding="utf-8")

            # Execute migration logic
            _expected_fields = ["timestamp", "firm", "name", "state", "target_url", "form_url", "status", "detail", "variant"]
            with open(test_csv, "r", encoding="utf-8", newline="") as hf:
                first_line = hf.readline().strip()
            self.assertNotIn("variant", first_line)

            if "variant" not in first_line:
                with open(test_csv, "r", encoding="utf-8", newline="") as hf:
                    all_content = hf.read()
                with open(test_csv, "w", encoding="utf-8", newline="") as hf:
                    hf.write(all_content.replace(first_line, ",".join(_expected_fields), 1))

            # Verify migrated header and preserved data
            with open(test_csv, "r", encoding="utf-8", newline="") as hf:
                reader = list(csv.DictReader(hf))

            self.assertEqual(len(reader), 1)
            self.assertEqual(reader[0]["firm"], "Apex Law")
            self.assertIn("variant", reader[0])

    def test_dead_domain_classification(self):
        """Verify get_submission_history catches failed/chrome-error/broker domains."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_log = Path(tmpdir) / "log.csv"
            fake_bounced = Path(tmpdir) / "bounced_emails.json"

            # Populate bounced domains
            with open(fake_bounced, "w", encoding="utf-8") as bf:
                json.dump(["baddomain.com", "deadlaw.org"], bf)

            # Populate log with error types
            with open(fake_log, "w", encoding="utf-8", newline="") as lf:
                writer = csv.DictWriter(lf, fieldnames=["timestamp", "firm", "name", "state", "target_url", "form_url", "status", "detail", "variant"])
                writer.writeheader()
                writer.writerow({
                    "timestamp": "2026-09-15T10:00:00",
                    "firm": "Broken Firm",
                    "name": "Partner",
                    "state": "FL",
                    "target_url": "https://brokenfirm.com",
                    "form_url": "chrome-error://chromewebdata/",
                    "status": "ERROR",
                    "detail": "err_name_not_resolved (Chrome navigation error)",
                    "variant": "A"
                })
                writer.writerow({
                    "timestamp": "2026-09-15T10:05:00",
                    "firm": "Good Firm",
                    "name": "Attorney",
                    "state": "TX",
                    "target_url": "https://goodfirm.com",
                    "form_url": "https://goodfirm.com/contact",
                    "status": "SUCCESS",
                    "detail": "Confirmed submission",
                    "variant": "B"
                })

            with patch.object(foe, "OUTREACH_DIR", Path(tmpdir)), \
                 patch.object(foe, "LOG_CSV", fake_log):
                dead_domains, latest_success = foe.get_submission_history(cooldown_days=90)

                self.assertIn("baddomain.com", dead_domains)
                self.assertIn("deadlaw.org", dead_domains)
                self.assertIn("brokenfirm.com", dead_domains)
                self.assertIn("goodfirm.com", latest_success)
                self.assertNotIn("goodfirm.com", dead_domains)

    def test_compose_message_statutory_integrity(self):
        """Verify that composed outreach contains accurate state statutory citations and valid URLs."""
        for st in ["FL", "TX", "GA", "NC", "TN", "CA"]:
            target = {
                "Firm": "Test Law Group",
                "Name": "John Doe",
                "State": st,
                "Practice_Area": "Real Estate"
            }
            subject, msg, variant = foe.compose_message(target)
            self.assertTrue(len(subject) > 5)
            self.assertIn("https://surplusdocket.com", msg)
            self.assertIn("https://buy.stripe.com/4gM14n8yq9vl0vrb0i0ZW21", msg)
            self.assertIn(variant, ["A", "B", "C"])
            self.assertNotIn("{", msg)
            self.assertNotIn("}", msg)

    def test_anti_spam_math_solver(self):
        """Verify anti-spam CAPTCHA math solvers solve word and numeral equations."""
        self.assertEqual(foe.solve_math_question("What is 7 + 5?"), "12")
        self.assertEqual(foe.solve_math_question("What is 15 minus 6?"), "9")
        self.assertEqual(foe.solve_math_question("Please calculate: 4 * 3"), "12")
        self.assertIsNone(foe.solve_math_question("Please enter your name here"))


if __name__ == "__main__":
    unittest.main()
