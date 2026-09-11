import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from outreach.form_outreach_engine import browser_name, summarize_results
from marketing.link_building import auto_article_submitter as articles


class ReliabilityTests(unittest.TestCase):
    def test_platform_browser_selection(self):
        with patch.dict(os.environ, {}, clear=True), patch('sys.platform', 'darwin'):
            self.assertEqual(browser_name(), 'webkit')
        with patch.dict(os.environ, {'CI': 'true'}, clear=True), patch('sys.platform', 'darwin'):
            self.assertEqual(browser_name(), 'chromium')

    def test_total_failure_is_not_a_green_batch(self):
        result = summarize_results([{'status': 'FAILED'}, {'status': 'UNCONFIRMED'}])
        self.assertEqual(result['confirmed_submissions'], 0)
        self.assertEqual(result['exit_code'], 1)

    def test_preview_does_not_claim_delivery(self):
        result = summarize_results([{'status': 'DRY_RUN'}], True)
        self.assertEqual(result['confirmed_submissions'], 0)
        self.assertEqual(result['previews'], 1)
        self.assertEqual(result['exit_code'], 0)

    def test_retired_pings_make_no_network_requests(self):
        with patch.object(articles.urllib.request, 'urlopen', side_effect=AssertionError('unexpected network')):
            result = articles.ping_search_engines()
        self.assertTrue(all(r['status'].startswith('retired') for r in result.values()))

    def test_syndication_dry_run_leaves_registry_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / 'registry.json'
            registry.write_text('{"runs": [], "total_submissions": 9}')
            original = registry.read_bytes()
            with patch.object(articles, 'REGISTRY_PATH', registry), patch.object(articles, 'SYNDICATE_DIR', Path(directory)), patch.object(articles.urllib.request, 'urlopen', side_effect=AssertionError('unexpected network')):
                result = articles.run_article_and_link_pipeline(dry_run=True)
            self.assertEqual(registry.read_bytes(), original)
            self.assertEqual(result['urls_submitted'], 0)
            self.assertEqual(result['syndicated_articles_count'], 0)
            self.assertIsNone(result['urls_indexed'])

    def test_email_firm_suppression_and_formatting(self):
        from portal.dispatch_morning_feed import format_firm_suffix as feed_suffix, compose_email_content
        from portal.trial_retention_sentinel import format_firm_suffix as sentinel_suffix, compose_day3_email

        # Compliance & Research Desk or generic placeholders must NOT appear in suffix
        self.assertEqual(feed_suffix({"firm": "Surplus Docket Compliance & Research Desk"}), "")
        self.assertEqual(feed_suffix({"firm": "Practice"}), "")
        self.assertEqual(feed_suffix({"firm": "Legal Practice"}), "")
        self.assertEqual(feed_suffix({"firm": ""}), "")
        self.assertEqual(feed_suffix({}), "")

        self.assertEqual(sentinel_suffix({"firm": "Surplus Docket Compliance & Research Desk"}), "")
        self.assertEqual(sentinel_suffix({"firm": "Practice"}), "")
        self.assertEqual(sentinel_suffix({}), "")

        # Legitimate firm name is properly formatted
        self.assertEqual(feed_suffix({"firm": "Smith & Jones Law, P.A."}), " (Smith & Jones Law, P.A.)")
        self.assertEqual(sentinel_suffix({"firm": "Smith & Jones Law, P.A."}), " (Smith & Jones Law, P.A.)")

        # Verify generated email content never includes Surplus Docket Compliance & Research Desk
        stats = {"total_surplus": 100000.0, "total_records": 5, "top_dockets": []}
        sub = {"name": "David Mahler", "firm": "Surplus Docket Compliance & Research Desk"}
        text, html = compose_email_content(sub, stats, "September 11, 2026")
        self.assertNotIn("Surplus Docket Compliance & Research Desk", html)
        self.assertNotIn("()", html)
        self.assertIn("Good morning <b>David Mahler</b>,", html)

        text_d3, html_d3 = compose_day3_email(sub)
        self.assertNotIn("Surplus Docket Compliance & Research Desk", html_d3)
        self.assertNotIn("()", html_d3)
        self.assertIn("Dear <b>David Mahler</b>,", html_d3)

    def test_publication_deduplication(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / 'registry.json'
            registry.write_text(json.dumps({
                "runs": [
                    {
                        "syndications": [
                            {
                                "platform": "medium",
                                "title": "Existing Post",
                                "canonical_url": "https://surplusdocket.com/blog/test.html",
                                "status": "success"
                            }
                        ]
                    }
                ],
                "total_submissions": 1
            }))
            synd_dir = Path(directory) / 'syndicate'
            synd_dir.mkdir()
            (synd_dir / 'medium_test.md').write_text(
                "---\ntitle: Existing Post\nplatform: medium\ncanonical_url: https://surplusdocket.com/blog/test.html\n---\nBody",
                encoding="utf-8"
            )
            with patch.object(articles, 'REGISTRY_PATH', registry), \
                 patch.object(articles, 'SYNDICATE_DIR', synd_dir), \
                 patch.object(articles, 'submit_to_indexnow', return_value={"status": "dry_run_success", "status_code": 200}), \
                 patch.object(articles, 'submit_medium_article', side_effect=AssertionError("Should not call publish for duplicate")):
                summary = articles.run_article_and_link_pipeline(dry_run=False)
            self.assertEqual(summary["syndicated_articles_count"], 0)
            loaded_reg = json.loads(registry.read_text())
            latest_run = loaded_reg["runs"][-1]
            self.assertEqual(latest_run["syndications"][0]["status"], "already_published")


if __name__ == '__main__':
    unittest.main()
