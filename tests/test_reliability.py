import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timedelta

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
        self.assertNotIn("Good morning", html)
        self.assertNotIn("Good morning", text)
        self.assertIn("Audited Surplus Pool", html)
        self.assertIn("BENCHMARK SUMMARY", text)

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

    def test_drafts_and_outreach_reliability(self):
        from outreach.generate_drafts import compose_email, get_first_name, create_eml_file

        # 1. First name extraction
        self.assertEqual(get_first_name("John Doe"), "John")
        self.assertEqual(get_first_name("Atty. Sarah Jenkins"), "Sarah")
        self.assertEqual(get_first_name(""), "Counsel")

        # 2. compose_email hygiene
        target = {
            "Name": "Sarah Jenkins",
            "Firm": "Jenkins & Associates, P.A.",
            "Email": "sarah@jenkinslaw.com",
            "State": "FL",
            "Specialty": "tax sale surplus",
            "Practice_Details": "Statewide surplus funds",
            "Style_Notes": "professional",
        }
        subject, body = compose_email(target, {}, from_name="Surplus Docket Intelligence", from_email="dockets@surplusdocket.com")

        # Must greet target by their name
        self.assertIn("Hi Sarah,", body)
        self.assertNotIn("David Mahler", body)

        # Must NOT contain banned desk phrasing
        self.assertNotIn("Compliance & Research Desk", body)
        self.assertNotIn("research desk", body)
        self.assertNotIn("Court Registry Ingestion Desk", body)

        # 3. EML creation
        with tempfile.TemporaryDirectory() as temp_dir:
            eml_path = Path(temp_dir) / "test.eml"
            create_eml_file("sarah@jenkinslaw.com", "Sarah Jenkins", subject, body, eml_path)
            content = eml_path.read_text(encoding="utf-8")
            self.assertIn("X-Unsent: 1", content)
            self.assertIn("sarah@jenkinslaw.com", content)

    def test_lifecycle_emails_and_plaintext_fallback(self):
        from portal.trial_retention_sentinel import (
            compose_day1_email,
            compose_day3_email,
            compose_day6_email,
            compose_day10_email,
        )
        from portal.dispatch_morning_feed import compose_email_content

        sub = {"name": "Alex Mercer", "firm": "Mercer Legal Group, PLLC"}
        
        # Day 1 Quick-Start
        t1, h1 = compose_day1_email(sub)
        self.assertIn("Dear Alex Mercer", t1)
        self.assertIn("Practice Quick-Start", h1)
        self.assertIn("Evaluation Day 1 of 7", h1)

        # Day 6 Courtesy Notice
        t6, h6 = compose_day6_email(sub)
        self.assertIn("evaluation of Surplus Docket", t6)
        self.assertIn("Courtesy Notice", h6)

        # Day 10 Win-Back
        t10, h10 = compose_day10_email(sub)
        self.assertIn("SINGLE-CASE ROI", t10)
        self.assertIn("https://buy.stripe.com/4gM14n8yq9vl0vrb0i0ZW21", t10)
        self.assertIn("Priority Reactivation", h10)

        # Plaintext docket feed formatting verification
        stats = {
            "total_surplus": 150000.0,
            "total_records": 1,
            "top_dockets": [{
                "docket": "2026-TD-001234",
                "owner": "Jane Doe",
                "amount": 75000.0,
                "state": "FL",
                "county": "Orange",
                "statute": "Fla. Stat. § 197.582",
                "clerk_url": "https://www.myorangeclerk.com/dockets/1234",
                "urgency": "Tier 1: High Urgency (< 45d)",
            }]
        }
        text_feed, html_feed = compose_email_content(sub, stats, "September 15, 2026")
        self.assertIn("Docket 2026-TD-001234 (Orange, FL) [Tier 1: High Urgency (< 45d)]", text_feed)
        self.assertIn("Statute: Fla. Stat. § 197.582", text_feed)
        self.assertIn("Registry Verification: https://www.myorangeclerk.com/dockets/1234", text_feed)

    def test_statutory_enrichment_deadline(self):
        from enrichment.processor import calculate_days_remaining
        
        # 30 days ago in FL (window is 120 days -> ~90 days remaining, Tier 2)
        sale_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        days, tier, deadline = calculate_days_remaining(sale_date, "FL")
        self.assertGreater(days, 0)
        self.assertIn("Tier", tier)
        self.assertEqual(len(deadline), 10)

        # 100 days ago in FL (window is 120 days -> ~20 days remaining, Tier 1)
        sale_date_urgent = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
        days_urg, tier_urg, _ = calculate_days_remaining(sale_date_urgent, "FL")
        self.assertLessEqual(days_urg, 45)
        self.assertIn("Tier 1", tier_urg)

    def test_enrichment_processor_helpers(self):
        from enrichment.processor import determine_tier, classify_owner, is_deceased_or_estate, classify_and_enrich_record
        
        # Test tier determination
        self.assertEqual(determine_tier(50000.0), "Tier 1: High Value ($25k+)")
        self.assertEqual(determine_tier(15000.0), "Tier 2: Medium Value ($10k-$25k)")
        self.assertEqual(determine_tier(5000.0), "Tier 3: Standard Value ($2.5k-$10k)")

        # Test owner classification
        owner_type, is_inst = classify_owner("Wells Fargo Bank N.A.")
        self.assertEqual(owner_type, "Institutional")
        self.assertTrue(is_inst)

        owner_type_ind, is_inst_ind = classify_owner("John & Sarah Miller")
        self.assertEqual(owner_type_ind, "Individual / Estate")
        self.assertFalse(is_inst_ind)

        # Test estate / deceased detection
        self.assertTrue(is_deceased_or_estate("Estate of Eleanor Vance"))
        self.assertTrue(is_deceased_or_estate("Robert Vance, Deceased"))
        self.assertTrue(is_deceased_or_estate("Unknown Heirs of Thomas Vance"))
        self.assertFalse(is_deceased_or_estate("David Smith"))

        # Test record enrichment
        row = {
            "Owner_Name": "Robert Smith",
            "Surplus_Balance_USD": 45000.0,
            "Property_Address": "123 Main St, Miami, FL",
            "Case_or_TaxDeed_No": "2024-TD-001000",
            "Sale_Date": "2026-06-01"
        }
        meta = {
            "county": "Miami-Dade",
            "state": "FL",
            "statute": "Fla. Stat. § 197.582",
            "fee_cap": 0.20
        }
        enriched = classify_and_enrich_record(row, meta)
        self.assertIsNotNone(enriched)
        self.assertEqual(enriched["Surplus_Balance_USD"], 45000.0)
        self.assertEqual(enriched["Est_Finder_Fee_USD"], 9000.0)
        self.assertEqual(enriched["Governing_Statute"], "Fla. Stat. § 197.582")
        self.assertEqual(enriched["Statute_Citation"], "Fla. Stat. § 197.582")
        self.assertIn("Claim_Deadline_Date", enriched)

        # Test filter for sub-$2500 balance
        small_row = {"Owner_Name": "Robert Smith", "Surplus_Balance_USD": 1500.0}
        self.assertIsNone(classify_and_enrich_record(small_row, meta))

    def test_monetization_config_and_welcome_page(self):
        from portal.setup_b2b_monetization import MONETIZATION_CONFIG, CONFIG_FILE, print_monetization_overview
        
        # Verify monetization tiers
        self.assertIn("single_county_pilot", MONETIZATION_CONFIG)
        self.assertIn("tri_state_core", MONETIZATION_CONFIG)
        self.assertIn("six_state_national", MONETIZATION_CONFIG)
        self.assertEqual(MONETIZATION_CONFIG["single_county_pilot"]["price_usd"], 49)
        self.assertEqual(MONETIZATION_CONFIG["tri_state_core"]["price_monthly_usd"], 249)
        self.assertEqual(MONETIZATION_CONFIG["six_state_national"]["price_monthly_usd"], 449)
        self.assertTrue(MONETIZATION_CONFIG["single_county_pilot"]["checkout_url"].startswith("https://buy.stripe.com/"))
        self.assertTrue(MONETIZATION_CONFIG["tri_state_core"]["checkout_monthly_url"].startswith("https://buy.stripe.com/"))
        self.assertTrue(MONETIZATION_CONFIG["six_state_national"]["checkout_monthly_url"].startswith("https://buy.stripe.com/"))
        self.assertTrue(MONETIZATION_CONFIG["stripe_customer_portal_url"].startswith("https://billing.stripe.com/"))

        # Verify welcome.html does not bounce paying customers
        welcome_path = Path(__file__).resolve().parent.parent / "site" / "welcome.html"
        welcome_content = welcome_path.read_text(encoding="utf-8")
        self.assertNotIn("window.location.replace('/#pricing')", welcome_content)
        self.assertNotIn('style="display:none;"', welcome_content)
        self.assertIn("Verified Subscriber", welcome_content)


if __name__ == '__main__':
    unittest.main()


