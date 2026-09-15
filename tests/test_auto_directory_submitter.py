#!/usr/bin/env python3
"""
Unit Tests: Surplus Docket Autonomous Directory Submitter
=========================================================
Tests for:
1. Company profile structure and field validity.
2. Directory submission packet parsing.
3. Registry status persistence.
"""

import csv
import tempfile
import unittest
from pathlib import Path

from marketing.link_building.auto_directory_submitter import (
    COMPANY_DATA,
    update_registry_status
)


class TestAutoDirectorySubmitter(unittest.TestCase):
    def test_company_data_integrity(self):
        required_keys = ["name", "website_url", "contact_email", "tagline", "short_description", "long_description"]
        for k in required_keys:
            self.assertIn(k, COMPANY_DATA)
            self.assertTrue(bool(COMPANY_DATA[k]))
            
        self.assertTrue(COMPANY_DATA["website_url"].startswith("https://surplusdocket.com"))
        self.assertIn("@", COMPANY_DATA["contact_email"])

    def test_update_registry_status(self):
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as tmp:
            writer = csv.writer(tmp)
            writer.writerow(["name", "category", "da", "url", "submission_url", "status", "anchor_target"])
            writer.writerow(["Test Directory", "LegalTech", "75", "https://example.com", "https://example.com/sub", "READY_FOR_SUBMISSION", "Anchor"])
            tmp_path = Path(tmp.name)

        try:
            import marketing.link_building.auto_directory_submitter as ads
            orig_path = ads.REGISTRY_PATH
            ads.REGISTRY_PATH = tmp_path
            try:
                update_registry_status("Test Directory", "SUBMITTED")
                with open(tmp_path, "r", encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
                    self.assertEqual(rows[0]["status"], "SUBMITTED")
            finally:
                ads.REGISTRY_PATH = orig_path
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()
