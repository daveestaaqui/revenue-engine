#!/usr/bin/env python3
"""
Unit tests for Surplus Docket Cryptographic Vault & Subscriber Protection
"""

import unittest
from portal.vault_security import (
    get_current_vault_key,
    get_vault_signature,
    get_subscriber_user_key,
    get_subscriber_email_hash,
    get_subscriber_auth_token,
    get_docket_unique_auth,
    build_subscriber_deep_url,
    encrypt_docket_payload,
    decrypt_docket_payload,
    generate_vault_and_auth_registry,
    xor_crypt,
)


class TestVaultSecurityAndProtection(unittest.TestCase):

    def setUp(self):
        self.vault_key = get_current_vault_key("2026-10-16")
        self.sub_email = "david@surplusdocket.com"
        self.lead = {
            "Case_or_TaxDeed_No": "SD-7102-0263",
            "Parcel_ID": "360-150-12-00",
            "Owner_Name": "DISE LEONARD L 1999 TRUST ET AL",
            "Property_Address": "Assessor Parcel 360-150-12-00, San Diego County, CA",
            "Clerk_Verification_URL": "https://www.sdttc.com/test.pdf#search=360-150-12-00",
            "Surplus_Balance_USD": 881663.35,
            "County": "San Diego",
            "State": "CA",
            "Governing_Statute": "Cal. Rev. & Tax Code § 4675",
        }

    def test_vault_key_and_signature_determinism(self):
        k1 = get_current_vault_key("2026-10-16")
        k2 = get_current_vault_key("2026-10-16")
        self.assertEqual(k1, k2)
        sig1 = get_vault_signature(k1)
        sig2 = get_vault_signature(k2)
        self.assertEqual(sig1, sig2)
        self.assertEqual(len(sig1), 16)

    def test_docket_encryption_and_decryption(self):
        cipher = encrypt_docket_payload(self.lead, self.vault_key)
        self.assertIsInstance(cipher, str)
        self.assertNotIn("DISE LEONARD", cipher)

        decrypted = decrypt_docket_payload(cipher, "SD-7102-0263", self.vault_key)
        self.assertEqual(decrypted["Owner_Name"], "DISE LEONARD L 1999 TRUST ET AL")
        self.assertEqual(decrypted["Case_or_TaxDeed_No"], "SD-7102-0263")
        self.assertEqual(decrypted["Surplus_Balance_USD"], 881663.35)

    def test_subscriber_user_key_and_vault_decryption(self):
        user_key = get_subscriber_user_key(self.sub_email)
        encrypted_vault = xor_crypt(self.vault_key.encode("utf-8"), user_key).hex()
        
        # Subscriber decrypts vault key with their own key
        decrypted_vault = xor_crypt(bytes.fromhex(encrypted_vault), user_key).decode("utf-8")
        self.assertEqual(decrypted_vault, self.vault_key)
        self.assertEqual(get_vault_signature(decrypted_vault), get_vault_signature(self.vault_key))

    def test_unauthorized_email_fails_decryption(self):
        legit_user_key = get_subscriber_user_key(self.sub_email)
        encrypted_vault = xor_crypt(self.vault_key.encode("utf-8"), legit_user_key).hex()

        # Attacker tries to decrypt with a different email key
        attacker_key = get_subscriber_user_key("attacker@random.com")
        bogus_decrypted = xor_crypt(bytes.fromhex(encrypted_vault), attacker_key).decode("utf-8", errors="ignore")
        self.assertNotEqual(bogus_decrypted, self.vault_key)
        self.assertNotEqual(get_vault_signature(bogus_decrypted), get_vault_signature(self.vault_key))

    def test_deep_url_generation_is_unique_per_email_and_docket(self):
        url1 = build_subscriber_deep_url("SD-7102-0263", "San Diego", "CA", "counsel1@firm.com", "2026-10-16")
        url2 = build_subscriber_deep_url("SD-7102-0263", "San Diego", "CA", "counsel2@firm.com", "2026-10-16")
        url3 = build_subscriber_deep_url("SD-7102-0395", "San Diego", "CA", "counsel1@firm.com", "2026-10-16")

        self.assertIn("https://surplusdocket.com/docket.html?", url1)
        self.assertIn(f"k={self.vault_key}", url1)
        self.assertIn("auth=", url1)
        self.assertIn("sub=", url1)

        # URLs must be distinct across subscribers and dockets
        self.assertNotEqual(url1, url2)
        self.assertNotEqual(url1, url3)

    def test_generate_vault_and_auth_registry(self):
        subscribers = [
            {"email": "david@surplusdocket.com", "status": "ACTIVE"},
            {"email": "cancelled@firm.com", "status": "CANCELLED"},
        ]
        leads = [self.lead]

        vault, auth = generate_vault_and_auth_registry(leads, subscribers, "2026-10-16")
        self.assertEqual(auth["active_subscriber_count"], 1)
        self.assertEqual(len(auth["subscribers"]), 1)
        self.assertEqual(auth["vault_sig"], get_vault_signature(self.vault_key))

        # Cancelled subscriber should NOT be in active registry
        cancelled_hash = get_subscriber_email_hash("cancelled@firm.com")
        registered_hashes = [s["email_hash"] for s in auth["subscribers"]]
        self.assertNotIn(cancelled_hash, registered_hashes)

        # Docket is vaulted
        self.assertIn("sd-7102-0263", vault["dockets"])
        self.assertIn("cipher", vault["dockets"]["sd-7102-0263"])


if __name__ == "__main__":
    unittest.main()
