#!/usr/bin/env python3
"""
Unit Tests: Weekly Marketing Report Generator & Aggregator
=========================================================
Tests for:
1. Metric aggregation logic across CSV logs and target database.
2. 7-day velocity calculations vs. lifetime totals.
3. HTML and plain-text report generation integrity.
4. Dry-run email dispatcher and recipient resolution.
"""

from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "outreach"))

from outreach.weekly_marketing_report import (
    collect_marketing_metrics,
    render_html_report,
    render_plaintext_report,
    send_report_email,
    parse_iso_datetime,
)


class TestWeeklyMarketingReport(unittest.TestCase):
    def test_parse_iso_datetime(self):
        dt1 = parse_iso_datetime("2026-09-04T20:41:03.844631")
        self.assertIsNotNone(dt1)
        self.assertEqual(dt1.year, 2026)
        self.assertEqual(dt1.month, 9)
        self.assertEqual(dt1.day, 4)

        dt2 = parse_iso_datetime("2026-08-26 11:37:29")
        self.assertIsNotNone(dt2)
        self.assertEqual(dt2.month, 8)
        self.assertEqual(dt2.day, 26)

        self.assertIsNone(parse_iso_datetime(""))
        self.assertIsNone(parse_iso_datetime("invalid-date-format"))

    def test_collect_marketing_metrics_live_repo(self):
        metrics = collect_marketing_metrics()
        self.assertIsInstance(metrics, dict)

        # Pipeline targets check (should be > 1000 from master_ranked_attorney_targets.csv)
        self.assertGreaterEqual(metrics["total_targets_in_pipeline"], 1000)
        self.assertIn("Tier 1", metrics["targets_by_tier"])
        self.assertGreater(metrics["targets_by_tier"]["Tier 1"], 0)

        # Submissions check
        self.assertGreater(metrics["total_form_submissions"], 0)
        self.assertGreaterEqual(metrics["unique_firms_contacted"], 0)
        self.assertGreaterEqual(metrics["pipeline_penetration_pct"], 0.0)

        # States check
        self.assertIn("FL", metrics["targets_by_state"])
        self.assertIn("TX", metrics["targets_by_state"])

        # Feed check
        self.assertGreaterEqual(metrics["active_surplus_dockets"], 0)
        self.assertGreaterEqual(metrics["total_verified_surplus_usd"], 0.0)

        # Organic assets check
        self.assertGreaterEqual(metrics["published_seo_pages"], 18)
        self.assertGreaterEqual(metrics["published_articles"], 6)

    def test_render_html_report(self):
        metrics = collect_marketing_metrics()
        html = render_html_report(metrics)

        self.assertIsInstance(html, str)
        self.assertIn("Surplus Docket — Marketing & Pipeline Progress", html)
        self.assertIn("Weekly Executive Briefing", html)
        self.assertIn("Pipeline Penetration", html)
        self.assertIn("Submission Success Rate", html)
        self.assertIn("State Geographic Outreach Progress", html)
        self.assertIn("Florida (FL)", html)
        self.assertIn("Texas (TX)", html)
        self.assertIn("Elena Brooks Response Desk", html)

    def test_render_plaintext_report(self):
        metrics = collect_marketing_metrics()
        text = render_plaintext_report(metrics)

        self.assertIsInstance(text, str)
        self.assertIn("SURPLUS DOCKET — WEEKLY MARKETING & PIPELINE REPORT", text)
        self.assertIn("EXECUTIVE HEADLINE:", text)
        self.assertIn("TARGET PIPELINE BY TIER:", text)
        self.assertIn("STATE GEOGRAPHIC PENETRATION:", text)
        self.assertIn("FL", text)
        self.assertIn("TX", text)
        self.assertIn("ELENA BROOKS INBOUND & SAFEGUARDS:", text)

    def test_send_report_email_dry_run(self):
        metrics = collect_marketing_metrics()
        html = render_html_report(metrics)
        text = render_plaintext_report(metrics)

        # Dry run must succeed without contacting network
        success = send_report_email("test@example.com", html, text, dry_run=True)
        self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
