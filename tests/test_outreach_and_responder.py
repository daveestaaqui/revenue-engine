#!/usr/bin/env python3
"""
Unit Test Suite: Form Outreach Engine & Auto-Responder / Unsubscriber
====================================================================
Tests for:
1. Anti-spam arithmetic and logic solver (solve_math_question)
2. Stealth browser parameters & anti-bot script integrity
3. Statutory inquiry message parsing (parse_statutory_inquiry)
4. Unsubscribe header & link extraction (extract_unsubscribe_details)
5. Automated bounce and receipt classification (is_automated_receipt_or_bounce)
6. Idempotency cache and target domain loaders
"""

import email
import json
import os
import sys
import unittest
from pathlib import Path

# Setup root path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "outreach"))

from outreach.form_outreach_engine import (
    solve_math_question,
    CHROMIUM_STEALTH_ARGS,
    STEALTH_INIT_SCRIPT,
)
from outreach.auto_responder_and_draft_cleaner import (
    clean_domain_str,
    load_target_domains,
    parse_statutory_inquiry,
    is_automated_receipt_or_bounce,
    extract_unsubscribe_details,
    load_unsubscribed_urls,
    save_unsubscribed_url,
    load_created_drafts,
    save_created_draft,
    STATE_NAMES,
    STRIPE_LINK,
)


class TestMathQuestionSolver(unittest.TestCase):
    """Tests arithmetic and anti-spam question parsing on legal contact forms."""

    def test_addition_variants(self):
        self.assertEqual(solve_math_question("What is 4 + 7?"), "11")
        self.assertEqual(solve_math_question("4 + 7 = "), "11")
        self.assertEqual(solve_math_question("Calculate: 15 + 25"), "40")
        self.assertEqual(solve_math_question("Please enter the sum of 8 and 12"), "20")
        self.assertEqual(solve_math_question("sum of 3 + 9"), "12")
        self.assertEqual(solve_math_question("five + three = "), "8")
        self.assertEqual(solve_math_question("two plus seven"), "9")

    def test_subtraction_variants(self):
        self.assertEqual(solve_math_question("12 - 5 = "), "7")
        self.assertEqual(solve_math_question("What is 20 minus 8?"), "12")
        self.assertEqual(solve_math_question("100 - 30"), "70")

    def test_multiplication_variants(self):
        self.assertEqual(solve_math_question("3 x 4 = ?"), "12")
        self.assertEqual(solve_math_question("5 * 6 = "), "30")
        self.assertEqual(solve_math_question("7 times 8"), "56")

    def test_anti_spam_trivia(self):
        self.assertEqual(solve_math_question("What color is the sky?"), "blue")
        self.assertEqual(solve_math_question("What color is grass?"), "green")
        self.assertEqual(solve_math_question("What is the capital of USA?"), "Washington")
        self.assertEqual(solve_math_question("What color is a fire truck?"), "red")

    def test_invalid_or_empty_prompts(self):
        self.assertIsNone(solve_math_question(""))
        self.assertIsNone(solve_math_question(None))
        self.assertIsNone(solve_math_question("Please enter your message here."))


class TestStealthConfiguration(unittest.TestCase):
    """Tests stealth launch arguments and anti-bot script."""

    def test_chromium_args(self):
        self.assertIn("--disable-blink-features=AutomationControlled", CHROMIUM_STEALTH_ARGS)
        self.assertIn("--no-sandbox", CHROMIUM_STEALTH_ARGS)

    def test_stealth_script_overrides(self):
        self.assertIn("navigator, 'webdriver'", STEALTH_INIT_SCRIPT)
        self.assertIn("window.chrome", STEALTH_INIT_SCRIPT)
        self.assertIn("navigator, 'languages'", STEALTH_INIT_SCRIPT)


class TestStatutoryInquiryParsing(unittest.TestCase):
    """Tests detection and parsing of surplusdocket.com website inquiry forms."""

    def test_standard_statutory_inquiry(self):
        subject = "OFFICIAL STATUTORY INQUIRY RECORD — Surplus Docket Public Record Request"
        body = """
================================================================================
 OFFICIAL STATUTORY INQUIRY RECORD — Surplus Docket Public Record Request
================================================================================
Timestamp: 2026-09-04T19:30:00.000Z
Inquiring Entity Name: Jonathan Vance
Inquiring Entity Email: jvance@vancelawfirm.com
Practice Jurisdiction: Texas
Subject: Surplus records for Harris and Dallas counties
Message: We are evaluating daily feed intake for post-Tyler excess proceeds.
================================================================================
"""
        inq = parse_statutory_inquiry(subject, body)
        self.assertIsNotNone(inq)
        self.assertEqual(inq["name"], "Jonathan Vance")
        self.assertEqual(inq["email"], "jvance@vancelawfirm.com")
        self.assertEqual(inq["state_code"], "TX")
        self.assertIn("evaluating daily feed", inq["message"])

    def test_modal_inquiry_format(self):
        subject = "[Surplus Docket Modal Inquiry] California excess proceeds"
        body = """
Name: Sarah Jenkins
Email: sarah@jenkinsrecovery.com
State: California
Message: Interested in Los Angeles and San Diego defaulted property surplus.
"""
        inq = parse_statutory_inquiry(subject, body)
        self.assertIsNotNone(inq)
        self.assertEqual(inq["name"], "Sarah Jenkins")
        self.assertEqual(inq["email"], "sarah@jenkinsrecovery.com")
        self.assertEqual(inq["state_code"], "CA")

    def test_non_inquiry_message(self):
        self.assertIsNone(parse_statutory_inquiry("Regular email", "Just saying hello."))


class TestUnsubscribeExtraction(unittest.TestCase):
    """Tests RFC 8058 One-Click, RFC 2369, and body unsubscribe parsing."""

    def test_rfc_8058_one_click_post(self):
        msg = email.message_from_string(
            "Subject: Marketing Updates\n"
            "List-Unsubscribe: <https://news.lawmatics.com/u/abc12345>, <mailto:unsub@lawmatics.com>\n"
            "List-Unsubscribe-Post: List-Unsubscribe=One-Click\n\n"
            "Body content"
        )
        res = extract_unsubscribe_details(msg, "Body content", "")
        self.assertEqual(res["one_click_post"], "https://news.lawmatics.com/u/abc12345")
        self.assertIn("mailto:unsub@lawmatics.com", res["mailto"])

    def test_html_and_text_body_links(self):
        msg = email.message_from_string("Subject: Firm Newsletter\n\nNewsletter")
        html = '<p>To opt out, <a href="https://example.com/optout?client=456">click here</a>.</p>'
        text = "Or visit https://example.com/manage-preferences?id=789 to unsubscribe."
        res = extract_unsubscribe_details(msg, text, html)
        self.assertIn("https://example.com/optout?client=456", res["http_urls"])
        self.assertIn("https://example.com/manage-preferences?id=789", res["http_urls"])


class TestBounceAndReceiptClassification(unittest.TestCase):
    """Tests classification of automated non-human messages vs genuine prospects."""

    def test_automated_autoreply(self):
        msg = email.message_from_string(
            "Subject: Automatic reply: Out of Office until Monday\n"
            "From: attorney@firm.com\n"
            "Auto-Submitted: auto-replied\n\n"
            "I will respond upon my return."
        )
        self.assertTrue(is_automated_receipt_or_bounce(msg, "attorney@firm.com", "Automatic reply: Out of Office until Monday"))

    def test_mailer_daemon_bounce(self):
        msg = email.message_from_string(
            "Subject: Undelivered Mail Returned to Sender\n"
            "From: MAILER-DAEMON@mail.server.com\n\n"
            "550 User not found."
        )
        self.assertTrue(is_automated_receipt_or_bounce(msg, "MAILER-DAEMON@mail.server.com", "Undelivered Mail Returned to Sender"))

    def test_dmarc_report_identification(self):
        msg = email.message_from_string(
            "Subject: Report Domain: surplusdocket.com Submitter: fastmail.com Report-ID:2026.09.15.2153048471\n"
            "From: reports@fastmaildmarc.com\n\n"
            "DMARC aggregate telemetry data."
        )
        self.assertTrue(is_automated_receipt_or_bounce(msg, "reports@fastmaildmarc.com", "Report Domain: surplusdocket.com Submitter: fastmail.com"))

        msg_google = email.message_from_string(
            "Subject: Report domain: surplusdocket.com Submitter: google.com\n"
            "From: noreply-dmarc-support@google.com\n\n"
            "Google DMARC report."
        )
        self.assertTrue(is_automated_receipt_or_bounce(msg_google, "noreply-dmarc-support@google.com", "Report domain: surplusdocket.com Submitter: google.com"))

    def test_genuine_prospect_reply(self):
        msg = email.message_from_string(
            "Subject: Re: Florida surplus & excess proceeds data\n"
            "From: Andrew Pascale <andrew@pascalelaw.com>\n\n"
            "David, can you send over sample dockets for Orange County?"
        )
        self.assertFalse(is_automated_receipt_or_bounce(msg, "andrew@pascalelaw.com", "Re: Florida surplus & excess proceeds data"))


class TestIdempotencyAndDomainLoaders(unittest.TestCase):
    """Tests target domain extraction and draft/unsubscription tracking."""

    def test_clean_domain_str(self):
        self.assertEqual(clean_domain_str("https://www.kramerlaw.com/about"), "kramerlaw.com")
        self.assertEqual(clean_domain_str("david@surplusdocket.com"), "surplusdocket.com")
        self.assertEqual(clean_domain_str("http://sub.domain.org:8080/path?query=1"), "sub.domain.org")

    def test_load_target_domains(self):
        domains = load_target_domains()
        self.assertIsInstance(domains, set)
        self.assertIn("pascalelaw.com", domains)
        self.assertIn("kramerlaw.com", domains)

    def test_idempotency_cache(self):
        import tempfile
        from unittest.mock import patch

        with tempfile.NamedTemporaryFile("w+", delete=False) as tf_unsub, tempfile.NamedTemporaryFile("w+", delete=False) as tf_drafts:
            tf_unsub.write("[]")
            tf_unsub.flush()
            tf_drafts.write("[]")
            tf_drafts.flush()

            with patch("outreach.auto_responder_and_draft_cleaner.UNSUBSCRIBED_URLS_FILE", Path(tf_unsub.name)), \
                 patch("outreach.auto_responder_and_draft_cleaner.CREATED_DRAFTS_LOG", Path(tf_drafts.name)):
                test_url = "https://test-unsub.com/optout?id=unit-test"
                save_unsubscribed_url(test_url)
                urls = load_unsubscribed_urls()
                self.assertIn(test_url, urls)

                test_draft = "test:lead@domain.com:FL"
                save_created_draft(test_draft)
                drafts = load_created_drafts()
                self.assertIn(test_draft, drafts)

            try:
                os.remove(tf_unsub.name)
                os.remove(tf_drafts.name)
            except Exception:
                pass


class TestDirectEmailAntiSpamAndDeliverability(unittest.TestCase):
    """Tests zero-spam protections, bounce blacklist, and high-conviction email list."""

    def test_bounced_and_generic_email_rejection(self):
        from outreach.generate_drafts import is_valid_direct_email

        # 1. Bounced addresses must be rejected
        self.assertFalse(is_valid_direct_email("paul@justilaw.com"))
        self.assertFalse(is_valid_direct_email("other@justilaw.com"))
        self.assertFalse(is_valid_direct_email("info@lw.com"))
        self.assertFalse(is_valid_direct_email("partner@lw.com"))

        # 2. Generic mailboxes must be rejected
        self.assertFalse(is_valid_direct_email("info@anyfirm.com"))
        self.assertFalse(is_valid_direct_email("contact@anyfirm.com"))
        self.assertFalse(is_valid_direct_email("intake@anyfirm.com"))
        self.assertFalse(is_valid_direct_email("office@anyfirm.com"))
        self.assertFalse(is_valid_direct_email("admin@anyfirm.com"))
        self.assertFalse(is_valid_direct_email("support@anyfirm.com"))
        self.assertFalse(is_valid_direct_email("inquiry@anyfirm.com"))

        # 3. High-conviction named practitioners must be accepted
        self.assertTrue(is_valid_direct_email("andrew@moherlaw.com"))
        self.assertTrue(is_valid_direct_email("dennis@evict123.com"))
        self.assertTrue(is_valid_direct_email("dcooper@kleinlaw.com"))
        self.assertTrue(is_valid_direct_email("vincent@taorminalawpa.com"))

    def test_high_conviction_attorneys_csv_integrity(self):
        import csv
        hc_file = BASE_DIR / "outreach" / "high_conviction_attorneys.csv"
        self.assertTrue(hc_file.exists(), "high_conviction_attorneys.csv must exist")

        with open(hc_file, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        self.assertGreaterEqual(len(rows), 50, "Should have at least 50 high-conviction targets")

        generic_prefixes = ("info@", "contact@", "admin@", "office@", "inquiry@", "intake@", "help@", "support@")
        allowed_states = {"FL", "TX", "CA", "GA", "NC", "TN"}
        blocked_domains = {"justilaw.com", "lw.com", "example.com"}

        for r in rows:
            em = r["Email"].lower()
            st = r["State"].upper()
            self.assertTrue(r["Name"], f"Missing name for {em}")
            self.assertTrue(r["Firm"], f"Missing firm for {em}")
            self.assertIn(st, allowed_states, f"State {st} not in core top 6")
            self.assertFalse(em.startswith(generic_prefixes), f"Generic email found: {em}")
            dom = em.split("@")[1]
            self.assertNotIn(dom, blocked_domains, f"Blocked domain found: {dom}")

    def test_record_bounced_email_persistence(self):
        import tempfile
        from unittest.mock import patch
        from outreach.generate_drafts import record_bounced_email

        with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
            tf.write('["initial@bounce.com"]')
            tf.flush()

            with patch("outreach.generate_drafts.BOUNCED_FILE", Path(tf.name)):
                record_bounced_email("testfail@unrouted-box.com")
                with open(tf.name, "r", encoding="utf-8") as rf:
                    data = json.load(rf)
                self.assertIn("testfail@unrouted-box.com", data)
                self.assertIn("unrouted-box.com", data)

            try:
                os.remove(tf.name)
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
