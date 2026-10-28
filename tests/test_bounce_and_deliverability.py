import json
import unittest
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch, MagicMock

from outreach.deliverability_guard import (
    validate_recipient_deliverability,
    load_bounced_blacklist,
    check_domain_mx,
    GENERIC_ROLE_PREFIXES,
    STRICT_DKIM_MX_PROVIDERS,
)
from outreach.bounce_processor import (
    extract_bounce_metadata,
    record_bounced_entity,
    update_sent_log_bounce,
    remove_from_verified_pool,
)


class TestDeliverabilityGuard(unittest.TestCase):
    def test_malformed_email(self):
        ok, msg = validate_recipient_deliverability("invalid-email", check_dns=False)
        self.assertFalse(ok)
        self.assertIn("Malformed", msg)

        ok2, msg2 = validate_recipient_deliverability("missingdomain@", check_dns=False)
        self.assertFalse(ok2)

    def test_generic_role_rejection(self):
        ok, msg = validate_recipient_deliverability("info@lawfirm.com", check_dns=False)
        self.assertFalse(ok)
        self.assertIn("generic department mailbox", msg)

        ok2, msg2 = validate_recipient_deliverability("contact@lawfirm.com", check_dns=False)
        self.assertFalse(ok2)
        self.assertIn("generic department mailbox", msg2)

    def test_blacklisted_email_and_domain(self):
        with patch("outreach.deliverability_guard.load_bounced_blacklist", return_value={"dead@target.com", "baddomain.com"}):
            ok, msg = validate_recipient_deliverability("dead@target.com", check_dns=False)
            self.assertFalse(ok)
            self.assertIn("blacklisted", msg)

            ok2, msg2 = validate_recipient_deliverability("anyone@baddomain.com", check_dns=False)
            self.assertFalse(ok2)
            self.assertIn("blacklisted", msg2)

    def test_valid_recipient_format(self):
        with patch("outreach.deliverability_guard.load_bounced_blacklist", return_value=set()):
            ok, msg = validate_recipient_deliverability("attorney@validfirm.com", check_dns=False)
            self.assertTrue(ok)
            self.assertEqual(msg, "Deliverable")

    def test_strict_dkim_mx_rejection(self):
        fake_dns = MagicMock()
        fake_resolver = MagicMock()
        fake_dns.resolver = fake_resolver
        fake_resolver.NXDOMAIN = type("NXDOMAIN", (Exception,), {})
        fake_resolver.NoAnswer = type("NoAnswer", (Exception,), {})
        fake_resolver.NoNameservers = type("NoNameservers", (Exception,), {})
        fake_mx = MagicMock()
        fake_mx.exchange = "mx-biz.mail.am0.yahoodns.net."
        fake_resolver.resolve.return_value = [fake_mx]
        with patch.dict("sys.modules", {"dns": fake_dns, "dns.resolver": fake_resolver}):
            ok, msg = check_domain_mx("yahoo-hosted-domain.com")
            self.assertFalse(ok)
            self.assertIn("Yahoo/AOL MX", msg)

    def test_invalid_placeholder_mx_rejection(self):
        fake_dns = MagicMock()
        fake_resolver = MagicMock()
        fake_dns.resolver = fake_resolver
        fake_resolver.NXDOMAIN = type("NXDOMAIN", (Exception,), {})
        fake_resolver.NoAnswer = type("NoAnswer", (Exception,), {})
        fake_resolver.NoNameservers = type("NoNameservers", (Exception,), {})
        fake_mx = MagicMock()
        fake_mx.exchange = "ms16397215.msv1.invalid.outlook.com."
        fake_resolver.resolve.return_value = [fake_mx]
        with patch.dict("sys.modules", {"dns": fake_dns, "dns.resolver": fake_resolver}):
            ok, msg = check_domain_mx("vondranlegal.com")
            self.assertFalse(ok)
            self.assertIn("null/invalid MX", msg)


class TestBounceProcessor(unittest.TestCase):
    def test_extract_bounce_metadata(self):
        msg = EmailMessage()
        msg["From"] = "mailer-daemon@googlemail.com"
        msg["Subject"] = "Delivery Status Notification (Failure)"
        body_text = (
            "An error occurred while trying to deliver the mail to:\n"
            "<bounced.attorney@targetlaw.com>: 550 5.1.1 The email account that you tried to reach does not exist.\n"
        )
        msg.set_content(body_text)

        recipients, diag = extract_bounce_metadata(msg)
        self.assertIn("bounced.attorney@targetlaw.com", recipients)
        self.assertIn("550", diag)

    def test_record_bounced_entity(self):
        with patch("builtins.open", unittest.mock.mock_open(read_data="[]")), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("json.dump") as mock_dump:
            res = record_bounced_entity("testattorney@badfirm.com", "550 5.1.0 Recipient not found")
            self.assertTrue(res)
            mock_dump.assert_called_once()
            args, _ = mock_dump.call_args
            self.assertIn("testattorney@badfirm.com", args[0])
            self.assertIn("badfirm.com", args[0])


if __name__ == "__main__":
    unittest.main()
