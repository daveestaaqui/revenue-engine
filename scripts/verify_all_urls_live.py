#!/usr/bin/env python3
"""
Thoroughly verify live HTTP responses for external clerk and platform URLs.
"""

import sys
import urllib.request
import urllib.error
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
}

TEST_URLS = [
    ("Hillsborough Civil PDF 1", "https://publicrec.hillsclerk.com/Civil/registry_trust_balances/Registry_and_TrustAccounts_Balances_as_of_Wed_10_14_2026.pdf"),
    ("Hillsborough Civil Directory", "https://publicrec.hillsclerk.com/Civil/registry_trust_balances/"),
    ("Hillsborough Tax Deeds Index", "https://www.hillsclerk.com/taxdeeds"),
    ("Hillsborough Official Homepage", "https://www.hillsclerk.com/"),
    ("Surplus Docket Homepage", "https://surplusdocket.com"),
    ("Surplus Docket Live Docket", "https://surplusdocket.com/#live-docket"),
    ("Surplus Docket Docket Page", "https://surplusdocket.com/docket.html"),
    ("Stripe Evaluation Checkout", "https://buy.stripe.com/4gM14n8yq9vl0vrb0i0ZW21"),
    ("Stripe Customer Portal", "https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00"),
]

def check_url(label, url):
    # Remove #search fragment for HTTP check
    base_url = url.split('#')[0]
    req = urllib.request.Request(base_url, headers=HEADERS, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            print(f"✅ {label}: HTTP {resp.status} - {url}")
            return True
    except urllib.error.HTTPError as e:
        if e.code in (403, 405): # Method not allowed for HEAD, try GET
            req_get = urllib.request.Request(base_url, headers=HEADERS, method="GET")
            try:
                with urllib.request.urlopen(req_get, timeout=15, context=ctx) as resp2:
                    print(f"✅ {label}: HTTP {resp2.status} (via GET) - {url}")
                    return True
            except Exception as e2:
                print(f"❌ {label}: HTTP GET failed: {e2} - {url}")
                return False
        print(f"❌ {label}: HTTP {e.code} - {url}")
        return False
    except Exception as e:
        print(f"❌ {label}: Connection error: {e} - {url}")
        return False

if __name__ == "__main__":
    results = [check_url(label, url) for label, url in TEST_URLS]
    print(f"\nSummary: {sum(results)} / {len(results)} URLs verified successfully.")
    if not all(results):
        sys.exit(1)
