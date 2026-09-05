#!/usr/bin/env python3
"""
Unit Tests: Surplus Docket Authority & Upgraded Link Building Engine
====================================================================
Tests for:
1. Directory Citations Engine & Metrics (DA distribution, submission packets).
2. Legal Digital PR Pitch Generator (press hooks, citations).
3. County Clerk & Legal Aid Outreach Letters (.gov / .org links).
4. Multi-Channel Syndication Publisher (Medium, Substack, LinkedIn, Dev.to).
5. Embeddable Widgets & Public Education Assets.
"""

from pathlib import Path
import sys
import unittest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from marketing.link_building.directory_citations import (
    load_citations,
    get_citation_metrics,
    generate_submission_packet,
    export_markdown_summary
)
from marketing.link_building.pr_pitcher import (
    PITCH_TEMPLATES,
    format_pitch_markdown,
    generate_all_pitches
)
from marketing.link_building.clerk_outreach_generator import (
    CLERK_TARGETS,
    generate_clerk_outreach_letter,
    generate_all_clerk_letters
)
from marketing.link_building.syndication_publisher import (
    ARTICLES_TO_SYNDICATE,
    generate_syndicated_document,
    build_all_syndication_files
)


class TestDirectoryCitations(unittest.TestCase):
    def test_load_citations_and_metrics(self):
        citations = load_citations()
        self.assertGreaterEqual(len(citations), 45)
        
        metrics = get_citation_metrics(citations)
        self.assertGreaterEqual(metrics["total_directories"], 45)
        self.assertGreaterEqual(metrics["average_da"], 70.0)
        self.assertGreaterEqual(metrics["da_80_plus"], 20)
        self.assertGreaterEqual(metrics["legal_specific"], 8)

    def test_submission_packet_generation(self):
        citations = load_citations()
        first = citations[0]
        packet = generate_submission_packet(first)
        self.assertIn("DIRECTORY SUBMISSION PROFILE", packet)
        self.assertIn("Surplus Docket", packet)
        self.assertIn("https://surplusdocket.com", packet)
        self.assertIn("https://surplusdocket.com/embed/", packet)

    def test_markdown_summary_export(self):
        summary = export_markdown_summary()
        self.assertIn("High-Authority Directory Citation Registry", summary)
        self.assertIn("Capterra", summary)
        self.assertIn("Justia", summary)


class TestPrPitcher(unittest.TestCase):
    def test_pitch_templates_structure(self):
        self.assertGreaterEqual(len(PITCH_TEMPLATES), 3)
        for p in PITCH_TEMPLATES:
            self.assertIn("id", p)
            self.assertIn("title", p)
            self.assertIn("hook", p)
            self.assertIn("expert_quote", p)
            self.assertIn("citeable_data", p)
            self.assertIn("resource_url", p)

    def test_format_pitch_markdown(self):
        pitch = PITCH_TEMPLATES[0]
        md = format_pitch_markdown(pitch)
        self.assertIn("# PRESS PITCH:", md)
        self.assertIn("Surplus Docket", md)
        self.assertIn("press@surplusdocket.com", md)

    def test_generate_all_pitches(self):
        files = generate_all_pitches()
        self.assertEqual(len(files), len(PITCH_TEMPLATES))
        for f in files:
            path = Path(f)
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 500)


class TestClerkOutreachGenerator(unittest.TestCase):
    def test_clerk_targets_coverage(self):
        # Must cover Top 6 jurisdictions
        states = {t["state"] for t in CLERK_TARGETS}
        for st in ["FL", "TX", "CA", "GA", "NC", "TN"]:
            self.assertIn(st, states)

    def test_generate_clerk_letter(self):
        target = CLERK_TARGETS[0]
        letter = generate_clerk_outreach_letter(target)
        self.assertIn("PUBLIC SERVICE LINK PROPOSAL", letter)
        self.assertIn("Tyler v. Hennepin County", letter)
        self.assertIn("homeowner-surplus-guide", letter)
        self.assertIn("surplus-calculator.html", letter)

    def test_generate_all_clerk_letters(self):
        files = generate_all_clerk_letters()
        self.assertEqual(len(files), 6)
        for f in files:
            p = Path(f)
            self.assertTrue(p.exists())
            self.assertGreater(p.stat().st_size, 500)


class TestSyndicationPublisher(unittest.TestCase):
    def test_articles_to_syndicate(self):
        self.assertGreaterEqual(len(ARTICLES_TO_SYNDICATE), 2)

    def test_generate_syndicated_document(self):
        art = ARTICLES_TO_SYNDICATE[0]
        doc = generate_syndicated_document(art, "medium")
        self.assertIn("PLATFORM: MEDIUM", doc)
        self.assertIn(art["canonical_url"], doc)
        self.assertIn("Surplus Docket Legal Intelligence", doc)

    def test_build_all_syndication_files(self):
        files = build_all_syndication_files()
        # 2 articles x 4 platforms = 8 files
        self.assertEqual(len(files), 8)
        for f in files:
            p = Path(f)
            self.assertTrue(p.exists())
            self.assertGreater(p.stat().st_size, 500)


class TestEmbedAssets(unittest.TestCase):
    def test_embed_files_exist(self):
        calc = BASE_DIR / "site" / "embed" / "surplus-calculator.html"
        badge = BASE_DIR / "site" / "embed" / "badge.svg"
        badge_dark = BASE_DIR / "site" / "embed" / "badge-dark.svg"
        portal = BASE_DIR / "site" / "embed" / "index.html"
        guide = BASE_DIR / "site" / "resources" / "homeowner-surplus-guide.html"

        for asset in [calc, badge, badge_dark, portal, guide]:
            self.assertTrue(asset.exists(), f"Missing asset: {asset}")
            self.assertGreater(asset.stat().st_size, 200, f"Asset is empty: {asset}")

    def test_canonical_links_present(self):
        calc_content = (BASE_DIR / "site" / "embed" / "surplus-calculator.html").read_text(encoding="utf-8")
        portal_content = (BASE_DIR / "site" / "embed" / "index.html").read_text(encoding="utf-8")
        guide_content = (BASE_DIR / "site" / "resources" / "homeowner-surplus-guide.html").read_text(encoding="utf-8")

        self.assertIn("https://surplusdocket.com", calc_content)
        self.assertIn("https://surplusdocket.com/embed/", portal_content)
        self.assertIn("https://surplusdocket.com/resources/homeowner-surplus-guide", guide_content)


class TestAutoArticleSubmitter(unittest.TestCase):
    def test_get_indexnow_key(self):
        from marketing.link_building.auto_article_submitter import get_indexnow_key
        key = get_indexnow_key()
        self.assertEqual(len(key), 32)

    def test_parse_sitemap_urls(self):
        from marketing.link_building.auto_article_submitter import parse_sitemap_urls
        urls = parse_sitemap_urls()
        self.assertGreaterEqual(len(urls), 20)
        self.assertTrue(all(u.startswith("https://surplusdocket.com") for u in urls))

    def test_submit_to_indexnow_dry_run(self):
        from marketing.link_building.auto_article_submitter import submit_to_indexnow
        res = submit_to_indexnow(["https://surplusdocket.com/"], dry_run=True)
        self.assertEqual(res["status"], "dry_run_success")
        self.assertEqual(res["urls_submitted"], 1)

    def test_ping_search_engines_dry_run(self):
        from marketing.link_building.auto_article_submitter import ping_search_engines
        pings = ping_search_engines(dry_run=True)
        self.assertIn("google", pings)
        self.assertIn("bing", pings)
        self.assertEqual(pings["google"]["status"], "dry_run_success")

    def test_run_article_and_link_pipeline_dry_run(self):
        from marketing.link_building.auto_article_submitter import run_article_and_link_pipeline
        summary = run_article_and_link_pipeline(dry_run=True)
        self.assertGreater(summary["urls_indexed"], 0)
        self.assertEqual(summary["indexnow_status"], "dry_run_success")
        self.assertIn("google", summary["search_engine_pings"])


if __name__ == "__main__":
    unittest.main()
