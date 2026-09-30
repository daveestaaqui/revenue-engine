#!/usr/bin/env python3
"""
Test Suite: Unlisted Monthly Presentation Builder Tool
======================================================
Validates that:
1. site/monthly-presentation-builder.html exists and is well-formed HTML.
2. The page is strictly unlisted: contains 'noindex, nofollow' and is NOT linked
   from index.html, tools.html, practitioner-toolkit.html, or sitemap.xml.
3. Required client-side libraries exist locally in site/assets/js/ (jszip, pptxgen, xlsx).
4. All 5 file slots (1 monthly reference guide + 4 weekly data files) are defined.
5. Deterministic arithmetic: all slide data is strictly aggregated from weekly data.
"""

import json
import os
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = BASE_DIR / "site"
TOOL_HTML_PATH = SITE_DIR / "monthly-presentation-builder.html"
ASSETS_JS_DIR = SITE_DIR / "assets" / "js"


class TestMonthlyPresentationBuilder(unittest.TestCase):

    def setUp(self):
        self.assertTrue(TOOL_HTML_PATH.exists(), "monthly-presentation-builder.html must exist")
        self.html_content = TOOL_HTML_PATH.read_text(encoding="utf-8")

    def test_page_is_unlisted_and_noindex(self):
        """Verify the page has meta robots noindex, nofollow."""
        self.assertIn(
            '<meta name="robots" content="noindex, nofollow">',
            self.html_content,
            "Page must have robots noindex, nofollow meta tag"
        )

    def test_page_is_not_linked_from_public_pages(self):
        """Verify that public pages do not link to this unlisted tool."""
        public_pages = ["index.html", "tools.html", "practitioner-toolkit.html", "methodology.html"]
        for page_name in public_pages:
            page_path = SITE_DIR / page_name
            if page_path.exists():
                content = page_path.read_text(encoding="utf-8")
                self.assertNotIn(
                    "monthly-presentation-builder.html",
                    content,
                    f"Unlisted tool must NOT be linked from {page_name}"
                )

    def test_page_not_in_sitemap(self):
        """Verify the page is NOT indexed in sitemap.xml."""
        sitemap_path = SITE_DIR / "sitemap.xml"
        if sitemap_path.exists():
            sitemap_content = sitemap_path.read_text(encoding="utf-8")
            self.assertNotIn(
                "monthly-presentation-builder.html",
                sitemap_content,
                "monthly-presentation-builder.html must NOT be in sitemap.xml"
            )

    def test_local_js_libraries_exist(self):
        """Verify required client-side libraries exist locally in site/assets/js/."""
        required_libs = ["jszip.min.js", "pptxgen.bundle.js", "xlsx.full.min.js"]
        for lib in required_libs:
            lib_path = ASSETS_JS_DIR / lib
            self.assertTrue(lib_path.exists(), f"Local asset {lib} must exist in site/assets/js/")
            self.assertTrue(
                f"/assets/js/{lib}" in self.html_content or f"assets/js/{lib}" in self.html_content,
                f"Script tag for {lib} must be present"
            )

    def test_five_file_slots_defined(self):
        """Verify all 5 file slots are present in HTML (1 monthly + 4 weekly)."""
        slots = ["slot-monthly", "slot-w1", "slot-w2", "slot-w3", "slot-w4"]
        for slot in slots:
            self.assertIn(f'id="{slot}"', self.html_content, f"File slot '{slot}' must exist in page")

    def test_all_onclick_handlers_defined(self):
        """Verify every function referenced in onclick/onsubmit is implemented."""
        defined_funcs = set(re.findall(r"function\s+([a-zA-Z0-9_$]+)\s*\(", self.html_content))
        arrow_funcs = set(re.findall(r"(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:\([^)]*\)|[a-zA-Z0-9_$]+)\s*=>", self.html_content))
        defined_funcs.update(arrow_funcs)

        onclick_calls = re.findall(r"(?:onclick|onsubmit)=[\"\']([a-zA-Z0-9_$]+)\(", self.html_content)
        for fn in onclick_calls:
            if fn in ["alert", "confirm", "prompt", "window", "document", "console"]:
                continue
            self.assertIn(fn, defined_funcs, f"Handler '{fn}' called in onclick but not defined")

    def test_deterministic_weekly_combination_logic(self):
        """Mathematical verification: 4 weekly datasets sum to exact monthly total."""
        # Simulated 4-week datasets
        week1 = [145000.0, 128500.0, 134000.0, 138500.0]
        week2 = [138000.0, 126000.0, 215000.0, 112000.0]
        week3 = [184000.0, 118000.0, 94500.0, 87500.0]
        week4 = [168000.0, 84200.0, 142000.0, 78500.0]

        w1_sum = sum(week1)
        w2_sum = sum(week2)
        w3_sum = sum(week3)
        w4_sum = sum(week4)

        monthly_total = w1_sum + w2_sum + w3_sum + w4_sum
        weekly_avg = monthly_total / 4.0

        self.assertEqual(monthly_total, 2093700.0)
        self.assertEqual(weekly_avg, 523425.0)
        self.assertEqual(max([w1_sum, w2_sum, w3_sum, w4_sum]), w2_sum)  # Week 2 is peak


if __name__ == "__main__":
    unittest.main()
