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

    def test_subscribers_json_includes_both_destinations(self):
        """Ensure both sandwichfitness@gmail.com and david@surplusdocket.com are registered and active."""
        subscribers_path = BASE_DIR / "portal" / "subscribers.json"
        self.assertTrue(subscribers_path.exists())

        with open(subscribers_path, "r", encoding="utf-8") as f:
            subs = json.load(f)

        emails = [s.get("email") for s in subs if s.get("status") == "ACTIVE"]
        self.assertIn("david@surplusdocket.com", emails)
        self.assertIn("sandwichfitness@gmail.com", emails)

        for s in subs:
            if s.get("email") in ("david@surplusdocket.com", "sandwichfitness@gmail.com"):
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
        self.assertIn("sandwichfitness@gmail.com", active_emails)

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

        # Off-peak minute headstarts
        self.assertIn("'42 10 * * 1-5'", primary_wf)
        self.assertIn("'48 10 * * 1-5'", primary_wf)
        self.assertIn("'53 10 * * 1-5'", primary_wf)

        # Sentinel 7:00 AM failover step
        self.assertIn("7:00 AM EST Morning Court Feed Autonomous Failover Check", sentinel_wf)
        self.assertIn("portal/dispatch_morning_feed.py", sentinel_wf)


if __name__ == "__main__":
    unittest.main()
