import unittest
import json
import tempfile
from pathlib import Path
from portal.manage_subscribers import add_subscriber, deactivate_subscriber, list_subscribers, load_subscribers


class TestSubscriberManagement(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.subs_file = Path(self.temp_dir.name) / "subscribers.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_add_and_list_subscriber(self):
        sub, is_new = add_subscriber(
            email="partner@floridarecoverylaw.com",
            name="Sarah Jenkins",
            firm="Jenkins & Associates P.A.",
            tier="Core Plan (7-Day Evaluation)",
            filepath=self.subs_file
        )
        self.assertTrue(is_new)
        self.assertEqual(sub["email"], "partner@floridarecoverylaw.com")
        self.assertEqual(sub["status"], "ACTIVE")

        subs = list_subscribers(filepath=self.subs_file)
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0]["name"], "Sarah Jenkins")

    def test_reactivate_existing_subscriber(self):
        add_subscriber(
            email="counsel@texaslaw.com",
            name="John Doe",
            firm="Doe Legal",
            filepath=self.subs_file
        )
        deactivate_subscriber("counsel@texaslaw.com", filepath=self.subs_file)
        subs = list_subscribers("ACTIVE", filepath=self.subs_file)
        self.assertEqual(len(subs), 0)

        # Reactivate
        sub, is_new = add_subscriber(
            email="counsel@texaslaw.com",
            name="John Doe Jr.",
            firm="Doe & Sons",
            filepath=self.subs_file
        )
        self.assertFalse(is_new)
        self.assertEqual(sub["status"], "ACTIVE")
        self.assertEqual(sub["firm"], "Doe & Sons")

    def test_invalid_email(self):
        with self.assertRaises(ValueError):
            add_subscriber(email="invalid-email", filepath=self.subs_file)


if __name__ == "__main__":
    unittest.main()
