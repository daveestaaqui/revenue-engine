import unittest
from portal.sync_stripe_subscribers import parse_stripe_email


class TestStripeSubscriberSync(unittest.TestCase):
    def test_parse_stripe_new_trial_email(self):
        subject = "A customer started a trial: Sarah Jenkins"
        body = """
        Hello,
        A customer has started a 7-day free trial on your Core Plan.
        Customer Name: Sarah Jenkins
        Customer: partner@floridarecoverylaw.com
        Plan: Core Plan (7-Day Evaluation)
        Amount: $0.00
        """
        parsed = parse_stripe_email(subject, body)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["email"], "partner@floridarecoverylaw.com")
        self.assertEqual(parsed["name"], "Sarah Jenkins")
        self.assertFalse(parsed["is_cancellation"])

    def test_parse_stripe_new_subscription_email(self):
        subject = "New subscription created from Robert Callahan"
        body = """
        New Subscription Notification
        Account: rcallahan@callahanlaw.com
        Customer Name: Robert Callahan
        Billed to: rcallahan@callahanlaw.com
        Amount: $249.00
        """
        parsed = parse_stripe_email(subject, body)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["email"], "rcallahan@callahanlaw.com")
        self.assertEqual(parsed["name"], "Robert Callahan")
        self.assertFalse(parsed["is_cancellation"])

    def test_parse_stripe_cancellation_email(self):
        subject = "Subscription canceled: Sarah Jenkins"
        body = """
        The following subscription has been canceled:
        Customer: partner@floridarecoverylaw.com
        Status: Canceled
        """
        parsed = parse_stripe_email(subject, body)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["email"], "partner@floridarecoverylaw.com")
        self.assertTrue(parsed["is_cancellation"])

    def test_ignore_unrelated_email(self):
        subject = "Your daily summary"
        body = "Hello, here is a random newsletter."
        parsed = parse_stripe_email(subject, body)
        self.assertIsNone(parsed)


if __name__ == "__main__":
    unittest.main()
