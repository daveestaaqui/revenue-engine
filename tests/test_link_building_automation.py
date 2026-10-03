#!/usr/bin/env python3
"""
Unit Tests for Autonomous Link Building & Tool Outreach Engine
============================================================
Tests queue prioritization, directory payload generation, target de-duplication,
email draft personalization, and audit logging.
"""

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from marketing.link_building.auto_directory_submitter import (
    select_submission_targets,
    submit_to_directory_http_fallback,
    COMPANY_DATA
)
from marketing.link_building.tool_outreach_engine import (
    load_targets,
    select_outreach_targets,
    build_personalized_email,
    save_outreach_draft,
    log_outreach_event,
    update_target_status
)


class TestLinkBuildingAutomation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_directory_queue_prioritization(self):
        """Verify directories are prioritized by READY status and DA descending."""
        sample_citations = [
            {"name": "Low DA Pending", "da": "45", "status": "READY_FOR_SUBMISSION"},
            {"name": "High DA Ready", "da": "92", "status": "READY_FOR_SUBMISSION"},
            {"name": "Mid DA Ready", "da": "75", "status": "READY_FOR_SUBMISSION"},
            {"name": "High DA Already Submitted", "da": "95", "status": "SUBMITTED"},
            {"name": "Populated Mid", "da": "70", "status": "POPULATED_READY_TO_SUBMIT"},
        ]

        targets = select_submission_targets(sample_citations, limit=3)
        self.assertEqual(len(targets), 3)
        # First should be the highest DA READY directory
        self.assertEqual(targets[0]["name"], "High DA Ready")
        self.assertEqual(targets[1]["name"], "Mid DA Ready")
        self.assertEqual(targets[2]["name"], "Low DA Pending")

    def test_directory_filter_by_name(self):
        """Verify target_name parameter correctly filters specific directory."""
        sample_citations = [
            {"name": "Lawyerist Legal Tech Directory", "da": "68", "status": "READY_FOR_SUBMISSION"},
            {"name": "Justia Legal Resources", "da": "92", "status": "READY_FOR_SUBMISSION"},
        ]
        targets = select_submission_targets(sample_citations, limit=5, target_name="lawyerist")
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["name"], "Lawyerist Legal Tech Directory")

    def test_company_data_integrity(self):
        """Verify company submission data contains canonical URLs and tools hub link."""
        self.assertIn("https://surplusdocket.com/", COMPANY_DATA["website_url"])
        self.assertIn("tools.html", COMPANY_DATA["tools_url"])
        self.assertIn("surplus-calculator.html", COMPANY_DATA["embed_url"])
        self.assertTrue(COMPANY_DATA["name"])
        self.assertTrue(COMPANY_DATA["contact_email"])

    def test_tool_outreach_targets_exist(self):
        """Verify the curated tool outreach target registry contains active targets."""
        targets = load_targets()
        self.assertGreaterEqual(len(targets), 15)
        for t in targets:
            self.assertTrue(t.get("organization"))
            self.assertIn("@", t.get("contact_email"))
            self.assertIn(t.get("target_type"), [
                "law_school_clinic", "bar_association_lpm", "legaltech_blogger", "real_estate_community"
            ])

    def test_tool_outreach_personalization(self):
        """Verify personalized pitch emails contain target names, tools link, and statutes."""
        target_clinic = {
            "name": "Prof. Jane Smith",
            "organization": "UF Levin Housing Clinic",
            "contact_email": "jane@ufl.edu",
            "target_type": "law_school_clinic",
            "jurisdiction": "FL",
            "da": "89"
        }

        subject, text_body, html_body = build_personalized_email(target_clinic)
        self.assertIn("Jane Smith", text_body)
        self.assertIn("UF Levin Housing Clinic", text_body)
        self.assertIn("https://surplusdocket.com/tools.html", text_body)
        self.assertIn("Tyler v. Hennepin County", text_body)
        self.assertIn("Fla. Stat.", html_body)

    def test_tool_outreach_draft_saving(self):
        """Verify .eml draft creation with proper MIME headers."""
        target = {
            "name": "LPM Advisor",
            "organization": "Texas Bar LPM",
            "contact_email": "lpm@texasbar.com",
            "target_type": "bar_association_lpm",
            "jurisdiction": "TX",
            "da": "86"
        }
        subject, text, html = build_personalized_email(target)
        eml_file = save_outreach_draft(target, subject, text, html)

        self.assertTrue(eml_file.exists())
        content = eml_file.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("lpm@texasbar.com", content)
        self.assertIn("Subject:", content)
        eml_file.unlink(missing_ok=True)

    def test_tool_outreach_logging(self):
        """Verify transmission logging to CSV."""
        log_file = self.temp_dir / "test_outreach_log.csv"
        target = {
            "name": "Clinical Director",
            "organization": "Stanford Clinic",
            "contact_email": "clinic@law.stanford.edu",
            "target_type": "law_school_clinic",
            "jurisdiction": "CA",
            "da": "93"
        }
        log_outreach_event(
            target,
            subject="Test Subject",
            status="DRAFTED_DRY_RUN",
            notes="Audit test log entry",
            message_id="msg-12345",
            log_path=log_file
        )

        self.assertTrue(log_file.exists())
        with open(log_file, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            self.assertEqual(len(reader), 1)
            self.assertEqual(reader[0]["recipient_email"], "clinic@law.stanford.edu")
            self.assertEqual(reader[0]["status"], "DRAFTED_DRY_RUN")
            self.assertEqual(reader[0]["message_id"], "msg-12345")


if __name__ == "__main__":
    unittest.main()
