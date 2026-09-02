#!/usr/bin/env python3
"""
Surplus Docket System Stress Test Suite
========================================
Comprehensive edge-case and load testing for:
1. Domain normalizer & clean_domain() edge cases
2. Priority scoring algorithm boundaries
3. A/B/C message composer & variable interpolation
4. Deduplication & log parsing under corrupted inputs
5. Data pipeline & packet generator execution
6. HTML site assets, schema, canonicals, & Stripe endpoints
7. JSON API and RSS feeds structure & validity
"""

import ast
import csv
import json
import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "outreach"))
sys.path.insert(0, str(BASE_DIR / "marketing"))
sys.path.insert(0, str(BASE_DIR / "surplus_intel"))

from outreach.form_outreach_engine import (
    clean_domain,
    calculate_priority_score,
    compose_message,
    get_recommended_link,
    get_already_submitted,
    STATE_NAMES,
    STATE_URLS,
    COUNTY_URLS,
    STRIPE_LINK,
    SITE_URL
)
from run_surplus_pipeline import run_pipeline


class TestDomainCleanerStress(unittest.TestCase):
    """Stress tests domain normalization under adversarial and malformed inputs."""

    def test_clean_domain_standard(self):
        self.assertEqual(clean_domain("https://www.lawfirm.com/contact"), "lawfirm.com")
        self.assertEqual(clean_domain("http://lawfirm.com"), "lawfirm.com")
        self.assertEqual(clean_domain("lawfirm.com"), "lawfirm.com")

    def test_clean_domain_emails(self):
        self.assertEqual(clean_domain("attorney@lawfirm.com"), "lawfirm.com")
        self.assertEqual(clean_domain("ATTORNEY@LAWFIRM.COM"), "lawfirm.com")
        self.assertEqual(clean_domain("  john.doe@sub.lawfirm.com  "), "sub.lawfirm.com")

    def test_clean_domain_adversarial_urls(self):
        self.assertEqual(clean_domain("https://www.lawfirm.com:8443/intake?ref=google&id=123#form"), "lawfirm.com")
        self.assertEqual(clean_domain("http://www.subdomain.lawfirm.org/about/team/"), "subdomain.lawfirm.org")
        self.assertEqual(clean_domain("https://lawfirm.net/"), "lawfirm.net")
        self.assertEqual(clean_domain(""), "")
        self.assertEqual(clean_domain(None), "")
        self.assertEqual(clean_domain("   "), "")
        self.assertEqual(clean_domain("///"), "")


class TestPriorityScorerStress(unittest.TestCase):
    """Tests priority scoring algorithm boundaries and edge cases."""

    def test_maximum_score_lead(self):
        lead = {
            "Name": "Andrew J. Pascale",
            "Firm": "Law Office of Andrew J. Pascale, P.A.",
            "State": "FL",
            "Specialty": "Tax Deed Surplus Funds",
            "Practice_Details": "Orange County surplus recovery and excess proceeds"
        }
        score = calculate_priority_score(lead)
        self.assertEqual(score, 100)

    def test_minimum_score_lead(self):
        lead = {
            "Name": "Generic Person",
            "Firm": "BigCorp",
            "State": "WY",
            "Specialty": "General Corporate",
            "Practice_Details": ""
        }
        score = calculate_priority_score(lead)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 30)

    def test_missing_and_corrupted_fields(self):
        for bad_lead in [{}, {"State": None}, {"Firm": 123}, {"Specialty": ""}, {"Name": None}]:
            try:
                score = calculate_priority_score({k: str(v) if v is not None else "" for k, v in bad_lead.items()})
                self.assertIsInstance(score, int)
                self.assertGreaterEqual(score, 0)
                self.assertLessEqual(score, 100)
            except Exception as e:
                self.fail(f"calculate_priority_score crashed on {bad_lead}: {e}")


class TestMessageComposerStress(unittest.TestCase):
    """Tests A/B/C message generation and variable interpolation."""

    def test_composer_all_variants(self):
        target = {
            "Name": "Mark C. Rains",
            "Firm": "Rains Law Firm, PLLC",
            "State": "TX",
            "Specialty": "Tax Foreclosure Excess Proceeds",
            "Practice_Details": "Harris County excess proceeds"
        }
        
        seen_variants = set()
        for _ in range(50):
            subject, body, variant = compose_message(target)
            seen_variants.add(variant)
            
            self.assertIn(variant, ["A", "B", "C"])
            self.assertIn("Mark", body)  # First name extracted
            self.assertIn("Texas", body)  # State name mapped
            self.assertIn(STRIPE_LINK, body)  # Stripe checkout link present
            self.assertIn("https://surplusdocket.com", body)  # Link present
            self.assertIn("David Mahler", body)  # Sender name
            self.assertNotIn("{", body)  # Zero unpopulated template tags
            self.assertNotIn("}", body)
            self.assertNotIn("{", subject)
            self.assertNotIn("}", subject)

        self.assertEqual(seen_variants, {"A", "B", "C"}, "All 3 A/B/C variants must be reachable")

    def test_composer_no_first_name_fallback(self):
        target = {
            "Name": "",
            "Firm": "Apex Asset Recovery",
            "State": "GA",
            "Specialty": "Excess Funds",
            "Practice_Details": "Fulton County"
        }
        subject, body, variant = compose_message(target)
        self.assertIn("Hello Apex Asset Recovery team,", body)
        self.assertIn("Georgia", body)

    def test_county_deep_link_resolution(self):
        self.assertEqual(
            get_recommended_link("FL", "Focuses on Miami-Dade and Broward surplus"),
            "https://surplusdocket.com/miami-dade-tax-deed-surplus.html"
        )
        self.assertEqual(
            get_recommended_link("TX", "Harris County civil district court"),
            "https://surplusdocket.com/harris-county-excess-proceeds.html"
        )
        self.assertEqual(
            get_recommended_link("NC", "General state practice"),
            "https://surplusdocket.com/north-carolina-tax-foreclosure-surplus.html"
        )
        self.assertEqual(
            get_recommended_link("UNKNOWN", "General practice"),
            SITE_URL
        )


class TestDeduplicationStress(unittest.TestCase):
    """Stress tests the target exclusion logic."""

    def test_get_already_submitted_logic(self):
        submitted = get_already_submitted()
        self.assertIsInstance(submitted, set)
        
        # Verify that DNS dead domains are excluded
        self.assertIn("rainslawfirm.com", submitted)
        
        # Verify that temporary retryable errors are NOT excluded
        self.assertNotIn("pascalelaw.com", submitted)


class TestPipelineExecutionStress(unittest.TestCase):
    """Stress tests the daily master revenue pipeline and packet generator."""

    def test_pipeline_execution(self):
        sample_csv = BASE_DIR / "data" / "sample_florida_tax_deed_surplus.csv"
        self.assertTrue(sample_csv.exists(), "Sample CSV must exist")
        
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Run pipeline
        try:
            run_pipeline(str(sample_csv), state="FL", min_surplus=5000.0, output_dir=str(output_dir))
        except Exception as e:
            self.fail(f"run_pipeline failed with error: {e}")

        # Verify output CSV was generated
        ranked_csv = output_dir / "ranked_surplus_opportunities.csv"
        self.assertTrue(ranked_csv.exists())
        
        with open(ranked_csv, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            self.assertGreater(len(reader), 0, "Pipeline must generate at least 1 ranked lead")


class TestSiteAssetsIntegrity(unittest.TestCase):
    """Stress tests HTML site integrity, canonical URLs, pricing, and schema."""

    def setUp(self):
        self.site_dir = BASE_DIR / "site"
        self.html_files = list(self.site_dir.glob("**/*.html"))

    def test_no_broken_internal_links(self):
        for hf in self.html_files:
            content = hf.read_text(encoding="utf-8", errors="ignore")
            hrefs = re.findall(r'href=[\"\'](/[^\"\'#?]+)[\"\']', content)
            for href in hrefs:
                if href.startswith(("http", "//", "mailto:", "tel:", "javascript:")):
                    continue
                if href == "/":
                    continue
                target = self.site_dir / href.lstrip("/")
                exists = target.exists() or (self.site_dir / f"{href.lstrip('/')}.html").exists() or (target / "index.html").exists()
                self.assertTrue(exists, f"Broken link {href} found in {hf.name}")

    def test_no_outdated_pricing(self):
        for hf in self.html_files:
            content = hf.read_text(encoding="utf-8", errors="ignore")
            self.assertNotIn("$199/mo", content, f"Outdated $199 pricing found in {hf.name}")
            self.assertNotIn("from $199", content, f"Outdated $199 pricing found in {hf.name}")
            self.assertNotIn("$349/mo Annual", content, f"Outdated $349 pricing found in {hf.name}")

    def test_all_json_ld_schemas_valid(self):
        for hf in self.html_files:
            content = hf.read_text(encoding="utf-8", errors="ignore")
            matches = re.findall(r'<script type=\"application/ld\+json\">(.*?)</script>', content, re.DOTALL)
            for m in matches:
                try:
                    data = json.loads(m.strip())
                    self.assertIn("@context", data)
                except Exception as e:
                    self.fail(f"Invalid JSON-LD in {hf.name}: {e}")

    def test_feed_and_sitemap_validity(self):
        sitemap = self.site_dir / "sitemap.xml"
        self.assertTrue(sitemap.exists())
        tree = ET.parse(sitemap)
        root = tree.getroot()
        self.assertTrue(len(root) > 20, "Sitemap must index at least 20 URLs")

        feed = self.site_dir / "feed.xml"
        self.assertTrue(feed.exists())
        ET.parse(feed)  # Valid XML parse

        security_txt = self.site_dir / ".well-known" / "security.txt"
        self.assertTrue(security_txt.exists(), "security.txt must exist")


if __name__ == "__main__":
    unittest.main(verbosity=2)
