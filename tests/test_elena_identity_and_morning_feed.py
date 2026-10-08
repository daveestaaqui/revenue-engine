import unittest
import os
import json
import re
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

BASE_DIR = Path(__file__).resolve().parent.parent


class TestElenaIdentityAndOutreach(unittest.TestCase):
    """Verifies that Elena Brooks' identity and email address are strictly enforced."""

    def test_generate_drafts_defaults(self):
        """Verify generate_drafts.py defaults to Elena Brooks with correct email."""
        from outreach import generate_drafts

        self.assertEqual(generate_drafts.DEFAULT_FROM_NAME, "Elena Brooks")
        self.assertEqual(generate_drafts.DEFAULT_FROM_EMAIL, "elena.brooks@surplusdocket.com")
        self.assertEqual(generate_drafts.DEFAULT_REPLY_TO, "elena.brooks@surplusdocket.com")

    def test_compose_email_signature(self):
        """Verify compose_email generates authentic Elena signature with her email."""
        from outreach.generate_drafts import compose_email

        target = {
            "Name": "Sarah Jenkins",
            "Firm": "Jenkins Law Group",
            "State": "FL",
            "Specialty": "Foreclosure",
            "County": "Orange",
        }
        state_cases = {
            "FL": [{"case_no": "2024-TD-001234", "county": "Orange", "balance": 45000.0, "owner": "John Smith"}]
        }
        subject, body = compose_email(target, state_cases, from_name="Elena Brooks", from_email="elena.brooks@surplusdocket.com")

        self.assertIn("Elena Brooks", body)
        self.assertIn("Senior Docket Specialist | Surplus Docket", body)
        self.assertIn("elena.brooks@surplusdocket.com", body)
        self.assertNotIn("sandwichfitness@gmail.com", body)
        self.assertNotIn("David Mahler", body)
        self.assertNotIn("david@surplusdocket.com", body)

    def test_create_eml_file_identity_enforcement(self):
        """Verify create_eml_file strictly uses Elena's From and Reply-To headers and strips personal leaks."""
        from outreach.generate_drafts import create_eml_file
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            eml_path = Path(tmpdir) / "test_draft.eml"
            body = (
                "Hi Sarah,\n\nTesting draft.\n\nBest regards,\nElena Brooks\n"
                "Senior Docket Specialist | Surplus Docket\nsurplusdocket.com\nelena.brooks@surplusdocket.com"
            )
            create_eml_file(
                to_email="sarah@jenkinslaw.com",
                to_name="Sarah Jenkins",
                subject="Orange County Surplus Docket",
                body=body,
                output_path=eml_path,
                from_name="Elena Brooks",
                from_email="elena.brooks@surplusdocket.com",
                reply_to="elena.brooks@surplusdocket.com",
            )

            raw_eml = eml_path.read_text(encoding="utf-8")
            self.assertIn("From: Elena Brooks <elena.brooks@surplusdocket.com>", raw_eml)
            self.assertIn("Reply-To: Elena Brooks <elena.brooks@surplusdocket.com>", raw_eml)
            self.assertNotIn("sandwichfitness@gmail.com", raw_eml)
            self.assertNotIn("david@surplusdocket.com", raw_eml)

    def test_auto_responder_send_response_email_sanitization(self):
        """Verify send_response_email sanitizes Elena's headers so personal emails are never exposed."""
        from outreach.auto_responder_and_draft_cleaner import send_response_email

        msg = MIMEText("Sample reply body", "plain", "utf-8")
        msg["From"] = "Elena Brooks <sandwichfitness@gmail.com>"
        msg["Reply-To"] = "sandwichfitness@gmail.com"
        msg["To"] = "counsel@firm.com"

        # dry_run=True exercises header rewrite without connecting to network
        success, detail = send_response_email(msg, "sandwichfitness@gmail.com", "counsel@firm.com", dry_run=True)
        self.assertTrue(success)
        self.assertEqual(msg["From"], "Elena Brooks <elena.brooks@surplusdocket.com>")
        self.assertEqual(msg["Reply-To"], "Elena Brooks <elena.brooks@surplusdocket.com>")

    def test_tool_outreach_defaults_and_pitches(self):
        """Verify tool outreach engine uses Elena Brooks and elena.brooks@surplusdocket.com."""
        from marketing.link_building import tool_outreach_engine

        self.assertEqual(tool_outreach_engine.DEFAULT_FROM_NAME, "Elena Brooks")
        self.assertEqual(tool_outreach_engine.DEFAULT_FROM_EMAIL, "elena.brooks@surplusdocket.com")
        self.assertEqual(tool_outreach_engine.DEFAULT_REPLY_TO, "elena.brooks@surplusdocket.com")

        # Check embed pitches markdown signatures
        pitches_dir = BASE_DIR / "marketing" / "link_building" / "embed_pitches"
        for p in pitches_dir.glob("pitch_*.md"):
            content = p.read_text(encoding="utf-8")
            if "Elena Brooks" in content:
                self.assertIn("elena.brooks@surplusdocket.com", content, f"Missing email in {p.name}")
                self.assertNotIn("sandwichfitness@gmail.com", content, f"Personal email leak in {p.name}")


class TestMorningFeedDeliverySystem(unittest.TestCase):
    """Verifies morning feed subscribers, redundancy, and dispatch execution."""

    def test_subscribers_json_primary_destination(self):
        """Ensure david@surplusdocket.com is registered and active, and sandwichfitness is not duplicated."""
        subscribers_path = BASE_DIR / "portal" / "subscribers.json"
        self.assertTrue(subscribers_path.exists())

        with open(subscribers_path, "r", encoding="utf-8") as f:
            subs = json.load(f)

        emails = [s.get("email") for s in subs if s.get("status") == "ACTIVE"]
        self.assertIn("david@surplusdocket.com", emails)
        self.assertNotIn("sandwichfitness@gmail.com", emails)

        for s in subs:
            if s.get("email") == "david@surplusdocket.com":
                self.assertEqual(s.get("status"), "ACTIVE")
                self.assertIn("CSV", s.get("delivery_format", []))
                self.assertIn("Excel", s.get("delivery_format", []))
                self.assertGreaterEqual(len(s.get("jurisdictions", [])), 3)

    def test_dispatch_morning_feed_dry_run_executes(self):
        """Verify dispatch_morning_feed dry run runs with exit code 0."""
        from portal.dispatch_morning_feed import dispatch_feed, load_active_subscribers

        active_subs = load_active_subscribers()
        active_emails = [s["email"] for s in active_subs]
        self.assertIn("david@surplusdocket.com", active_emails)
        self.assertNotIn("sandwichfitness@gmail.com", active_emails)

        res = dispatch_feed(is_dry_run=True)
        self.assertEqual(res, 0)

    def test_workflow_concurrency_and_schedules(self):
        """Verify GitHub Actions workflows have non-colliding concurrency and off-peak schedules."""
        primary_wf = (BASE_DIR / ".github" / "workflows" / "dispatch_morning_feed.yml").read_text()
        backup_wf = (BASE_DIR / ".github" / "workflows" / "dispatch_morning_feed_backup.yml").read_text()
        sentinel_wf = (BASE_DIR / ".github" / "workflows" / "elena_inbox_sentinel.yml").read_text()

        # Primary concurrency
        self.assertIn("group: dispatch-morning-feed-primary", primary_wf)
        self.assertIn("cancel-in-progress: true", primary_wf)

        # Backup concurrency
        self.assertIn("group: dispatch-morning-feed-backup", backup_wf)
        self.assertIn("cancel-in-progress: true", backup_wf)

        # Simplified EDT/EST dual-trigger schedule
        self.assertIn("'0 11 * * 1-5'", primary_wf)
        self.assertIn("'0 12 * * 1-5'", primary_wf)

        # Sentinel 7:00 AM failover step
        self.assertIn("7:00 AM EST Morning Court Feed Autonomous Failover Check", sentinel_wf)
        self.assertIn("portal/dispatch_morning_feed.py", sentinel_wf)

    def test_dispatch_window_guard_blocks_early_morning_afternoon_and_weekend(self):
        """Verify dispatch_feed blocks live sends outside morning window (e.g. 5:55 AM, 3:35 PM, or weekend)."""
        from portal.dispatch_morning_feed import dispatch_feed
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from unittest.mock import patch

        # Case 1: Monday at 5:55 AM EDT (early morning - must NEVER dispatch before 7:00 AM)
        early_morning = datetime(2026, 10, 5, 5, 55, 0, tzinfo=ZoneInfo("America/New_York"))
        with patch("portal.dispatch_morning_feed.datetime") as mock_dt:
            mock_dt.now.return_value = early_morning
            res = dispatch_feed(is_dry_run=False, recipient_override=None, force=False)
            self.assertEqual(res, 0)

        # Case 2: Tuesday at 6:45 AM EDT (pre-market - blocked)
        pre_market = datetime(2026, 10, 6, 6, 45, 0, tzinfo=ZoneInfo("America/New_York"))
        with patch("portal.dispatch_morning_feed.datetime") as mock_dt:
            mock_dt.now.return_value = pre_market
            res = dispatch_feed(is_dry_run=False, recipient_override=None, force=False)
            self.assertEqual(res, 0)

        # Case 3: Monday at 3:35 PM EDT (afternoon - blocked)
        afternoon_time = datetime(2026, 10, 5, 15, 35, 0, tzinfo=ZoneInfo("America/New_York"))
        with patch("portal.dispatch_morning_feed.datetime") as mock_dt:
            mock_dt.now.return_value = afternoon_time
            res = dispatch_feed(is_dry_run=False, recipient_override=None, force=False)
            self.assertEqual(res, 0)

        # Case 4: Monday at 10:15 AM EDT (after 10:00 AM cutoff - blocked)
        late_morning = datetime(2026, 10, 5, 10, 15, 0, tzinfo=ZoneInfo("America/New_York"))
        with patch("portal.dispatch_morning_feed.datetime") as mock_dt:
            mock_dt.now.return_value = late_morning
            res = dispatch_feed(is_dry_run=False, recipient_override=None, force=False)
            self.assertEqual(res, 0)

        # Case 5: Saturday at 7:00 AM EDT (weekend - blocked)
        weekend_time = datetime(2026, 10, 10, 7, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        with patch("portal.dispatch_morning_feed.datetime") as mock_dt:
            mock_dt.now.return_value = weekend_time
            res = dispatch_feed(is_dry_run=False, recipient_override=None, force=False)
            self.assertEqual(res, 0)

    def test_sentinel_morning_failover_window(self):
        """Verify sentinel_morning_failover strictly respects the 7:05 AM - 10:00 AM EST failover window."""
        from portal.sentinel_morning_failover import check_and_failover
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from unittest.mock import patch, MagicMock

        # Case 1: Early morning at 5:55 AM EDT (must NOT trigger)
        early_time = datetime(2026, 10, 6, 5, 55, 0, tzinfo=ZoneInfo("America/New_York"))
        with patch("portal.sentinel_morning_failover.datetime") as mock_dt, \
             patch("portal.sentinel_morning_failover.subprocess.run") as mock_sub:
            mock_dt.now.return_value = early_time
            res = check_and_failover()
            self.assertEqual(res, 0)
            mock_sub.assert_not_called()

        # Case 2: At 7:01 AM EDT (must NOT trigger, letting primary 7:00 AM workflow run)
        primary_window = datetime(2026, 10, 6, 7, 1, 0, tzinfo=ZoneInfo("America/New_York"))
        with patch("portal.sentinel_morning_failover.datetime") as mock_dt, \
             patch("portal.sentinel_morning_failover.subprocess.run") as mock_sub:
            mock_dt.now.return_value = primary_window
            res = check_and_failover()
            self.assertEqual(res, 0)
            mock_sub.assert_not_called()

        # Case 3: Afternoon at 3:35 PM EDT (must NOT trigger)
        afternoon_time = datetime(2026, 10, 5, 15, 35, 0, tzinfo=ZoneInfo("America/New_York"))
        with patch("portal.sentinel_morning_failover.datetime") as mock_dt, \
             patch("portal.sentinel_morning_failover.subprocess.run") as mock_sub:
            mock_dt.now.return_value = afternoon_time
            res = check_and_failover()
            self.assertEqual(res, 0)
            mock_sub.assert_not_called()

        # Case 4: Inside window at 7:15 AM EDT when feed is already dispatched
        failover_time = datetime(2026, 10, 6, 7, 15, 0, tzinfo=ZoneInfo("America/New_York"))
        with patch("portal.sentinel_morning_failover.datetime") as mock_dt, \
             patch("portal.sentinel_morning_failover.json.load", return_value={"last_dispatched_date": "2026-10-06", "status": "SUCCESS"}), \
             patch("portal.sentinel_morning_failover.subprocess.run") as mock_sub:
            mock_dt.now.return_value = failover_time
            res = check_and_failover()
            self.assertEqual(res, 0)
            mock_sub.assert_not_called()

        # Case 5: Inside window at 7:15 AM EDT when feed is NOT yet dispatched (triggers failover)
        with patch("portal.sentinel_morning_failover.datetime") as mock_dt, \
             patch("portal.sentinel_morning_failover.json.load", return_value={"last_dispatched_date": "2026-10-05", "status": "SUCCESS"}), \
             patch("portal.sentinel_morning_failover.subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0)
            mock_dt.now.return_value = failover_time
            res = check_and_failover()
            self.assertEqual(res, 0)
            mock_sub.assert_called_once()

    def test_morning_feed_links_are_direct_listings_not_generic_homepages(self):
        """Verify that morning feed featured dockets link directly to case listings, not generic town/county homepages."""
        from portal.dispatch_morning_feed import get_feed_statistics, compose_email_content
        from enrichment.processor import is_generic_homepage, build_direct_clerk_url

        # 1. Test direct URL builder across multiple jurisdictions
        url_fl = build_direct_clerk_url("Palm Beach", "FL", "2024-TD-004501")
        self.assertIn("caseNumber=2024-TD-004501", url_fl)
        self.assertFalse(is_generic_homepage(url_fl))

        url_ca = build_direct_clerk_url("Los Angeles", "CA", "2024-CA-008120")
        self.assertIn("docket=2024-CA-008120", url_ca)
        self.assertFalse(is_generic_homepage(url_ca))

        url_tx = build_direct_clerk_url("Harris", "TX", "2024-TX-04812")
        self.assertIn("Cas=2024-TX-04812", url_tx)
        self.assertFalse(is_generic_homepage(url_tx))

        url_ga = build_direct_clerk_url("Fulton", "GA", "2024-GA-003810")
        self.assertIn("docket=2024-GA-003810", url_ga)
        self.assertFalse(is_generic_homepage(url_ga))

        # 2. Test active feed statistics top dockets
        stats = get_feed_statistics()
        self.assertGreater(len(stats["top_dockets"]), 0)
        for docket in stats["top_dockets"]:
            url = docket["clerk_url"]
            self.assertTrue(url.startswith("https://"))
            self.assertFalse(is_generic_homepage(url), f"URL '{url}' for docket {docket['docket']} is a generic homepage!")
            # Must contain docket/case identifier in query or path
            self.assertTrue(
                "?" in url or "dockets" in url or "details" in url.lower() or "casesearch" in url.lower(),
                f"URL '{url}' does not deep-link directly to case record"
            )

        # 3. Test email composition renders direct listing links and CTA
        sub = {"name": "Test Counsel", "firm": "Test Law LLP", "email": "test@testlaw.com"}
        text_feed, html_feed = compose_email_content(sub, stats, "October 08, 2026")
        self.assertIn("Open Direct Docket Listing &rarr;", html_feed)
        for docket in stats["top_dockets"]:
            self.assertIn(docket["clerk_url"], html_feed)
            self.assertIn(docket["clerk_url"], text_feed)


if __name__ == "__main__":
    unittest.main()


