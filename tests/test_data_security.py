#!/usr/bin/env python3
"""
Test Suite: Data Security, Anti-Leak & Truth-In-Advertising Enforcement
========================================================================
Validates that:
1. Full unredacted lead data (claimant names, property situs addresses, direct court filings)
   is strictly secured outside the public web tree (exports/) and only dispatched to
   authenticated paying subscribers.
2. Public static REST API endpoints in site/api/v1/ return 'subscription_required',
   authenticated=False, and masked sandbox records.
3. Downloadable sample CSV files in site/assets/ contain redacted addresses and names.
4. No real raw claimant names from production datasets leak anywhere into site/.
5. Feed delivery frequency is explicitly stated as Monday through Friday (Mon–Fri / Court Business Days)
   to prevent false advertising.
"""

import json
import csv
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = BASE_DIR / "site"
EXPORTS_DIR = BASE_DIR / "exports"
DATA_DIR = BASE_DIR / "data"


class TestDataSecurityAndAntiLeak(unittest.TestCase):

    def test_unredacted_exports_outside_site_tree(self):
        """Ensure full lead exports are strictly outside site/ to prevent static web scraping."""
        self.assertTrue(EXPORTS_DIR.exists())
        self.assertFalse(
            str(EXPORTS_DIR.resolve()).startswith(str(SITE_DIR.resolve())),
            "exports/ must never be a subdirectory of site/"
        )
        
        # Verify unredacted master files do not exist inside site/
        for forbidden in ["Master_Surplus_Lead_Feed.csv", "Master_Surplus_Lead_Feed.xlsx", "Master_Surplus_Lead_Feed.json"]:
            self.assertFalse(
                (SITE_DIR / forbidden).exists(),
                f"Forbidden unredacted file found in site root: {forbidden}"
            )
            self.assertFalse(
                (SITE_DIR / "assets" / forbidden).exists(),
                f"Forbidden unredacted file found in site/assets: {forbidden}"
            )

    def test_zero_real_claimant_names_in_public_site_files(self):
        """Scans public site files to ensure no unredacted full real claimant names are leaked."""
        master_csv = EXPORTS_DIR / "Master_Surplus_Lead_Feed.csv"
        if not master_csv.exists():
            self.skipTest("Master_Surplus_Lead_Feed.csv not found")

        real_names = set()
        with open(master_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Owner_Name", "").strip()
                if name and len(name) > 6 and "ESTATE OF" not in name.upper() and "ET AL" not in name.upper():
                    real_names.add(name)

        self.assertGreater(len(real_names), 10, "Should have real names to check against")

        # Scan site/api/v1/*.json and site/assets/*.csv
        files_to_scan = list((SITE_DIR / "api" / "v1").glob("*.json")) + list((SITE_DIR / "assets").glob("*.csv"))
        for f in files_to_scan:
            content = f.read_text(encoding="utf-8")
            for name in real_names:
                self.assertNotIn(
                    name, 
                    content, 
                    f"DATA LEAK DETECTED: Real claimant name '{name}' found in public file {f.relative_to(BASE_DIR)}"
                )

    def test_public_api_endpoints_subscription_gated(self):
        """Validates that public API endpoints return status='subscription_required' with masked records."""
        api_endpoints = [
            "feed.json", "florida.json", "texas.json", "georgia.json",
            "north-carolina.json", "tennessee.json", "california.json"
        ]
        for ep in api_endpoints:
            ep_path = SITE_DIR / "api" / "v1" / ep
            self.assertTrue(ep_path.exists(), f"Endpoint {ep} missing")
            data = json.loads(ep_path.read_text(encoding="utf-8"))
            
            self.assertEqual(
                data.get("status"), 
                "subscription_required", 
                f"{ep} status must be 'subscription_required'"
            )
            self.assertIs(
                data.get("authenticated"), 
                False, 
                f"{ep} authenticated flag must be False"
            )
            self.assertIn(
                "Monday through Friday", 
                data.get("delivery_schedule", ""), 
                f"{ep} delivery_schedule must specify Monday through Friday"
            )

            records = data.get("records", [])
            self.assertGreater(len(records), 0, f"{ep} should contain specimen sandbox records")
            for idx, r in enumerate(records):
                owner = r.get("Owner_Name", "")
                addr = r.get("Property_Address", "")
                self.assertTrue(
                    "█" in owner or "[" in owner,
                    f"{ep} row {idx+1} owner name is not redacted: '{owner}'"
                )
                self.assertTrue(
                    "[" in addr or "REDACTED" in addr.upper(),
                    f"{ep} row {idx+1} address is not redacted: '{addr}'"
                )

    def test_sample_csv_downloads_are_redacted(self):
        """Verify downloadable sample CSVs in site/assets/ do not leak addresses or claimant names."""
        sample_files = ["sample_docket.csv", "sample_surplus_docket.csv", "sample_surplus_docket_feed.csv"]
        for sf in sample_files:
            sf_path = SITE_DIR / "assets" / sf
            self.assertTrue(sf_path.exists(), f"Sample CSV {sf} missing")
            with open(sf_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    owner = row.get("Owner_Name_Redacted", "")
                    addr = row.get("Property_Address", "")
                    self.assertTrue(
                        "█" in owner or "[" in owner,
                        f"{sf} row {idx+1} owner is not masked: '{owner}'"
                    )
                    self.assertTrue(
                        "[" in addr or "REDACTED" in addr.upper(),
                        f"{sf} row {idx+1} address is not masked: '{addr}'"
                    )

    def test_truth_in_advertising_delivery_schedule(self):
        """Verify explicit Monday through Friday (court business days) schedule across core pages."""
        # Index hero / subtext
        index_content = (SITE_DIR / "index.html").read_text(encoding="utf-8")
        self.assertIn("Mon–Fri", index_content, "index.html must specify Mon–Fri delivery")
        self.assertIn("Monday through Friday", index_content, "index.html FAQ must explain Mon-Fri schedule")
        
        # API documentation
        api_doc_content = (SITE_DIR / "api-documentation.html").read_text(encoding="utf-8")
        self.assertIn("Monday through Friday", api_doc_content, "api-documentation.html must state Mon-Fri schedule")

        # Welcome page
        welcome_content = (SITE_DIR / "welcome.html").read_text(encoding="utf-8")
        self.assertIn("Monday through Friday", welcome_content, "welcome.html must state Mon-Fri schedule")

    def test_subscriber_dispatch_policy(self):
        """Verify that dispatch_morning_feed only sends full files to ACTIVE status subscribers."""
        from portal.dispatch_morning_feed import load_active_subscribers
        active = load_active_subscribers()
        self.assertIsInstance(active, list)
        for sub in active:
            self.assertEqual(sub.get("status", "").upper(), "ACTIVE")


if __name__ == "__main__":
    unittest.main()
