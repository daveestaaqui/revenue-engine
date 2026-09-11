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


if __name__ == '__main__':
    unittest.main()
