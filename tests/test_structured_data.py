#!/usr/bin/env python3
"""
Test Suite: Schema.org Structured Data & Google Search Console Snippet Compliance
Verifies that site/index.html and core pages provide valid, error-free schema.org markup,
specifically testing that Product snippets have valid aggregateRating, review, offers,
and that all structured review content is visibly represented in the HTML page.
"""
import unittest
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = BASE_DIR / "site"


class TestProductStructuredData(unittest.TestCase):
    def setUp(self):
        self.index_path = SITE_DIR / "index.html"
        self.assertTrue(self.index_path.exists(), "site/index.html must exist")
        self.html = self.index_path.read_text(encoding="utf-8")

        # Extract JSON-LD script
        m = re.search(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', self.html, re.DOTALL)
        self.assertIsNotNone(m, "site/index.html must contain a valid <script type=\"application/ld+json\"> block")
        self.json_data = json.loads(m.group(1))

    def test_product_snippet_has_required_fields(self):
        """Ensure Product node exists with name, description, brand, image, and offers."""
        graph = self.json_data.get("@graph", [])
        products = [node for node in graph if node.get("@type") == "Product"]
        self.assertEqual(len(products), 1, "Expected exactly one @type: 'Product' node in index.html graph")

        product = products[0]
        self.assertEqual(product.get("name"), "Surplus Docket Daily Data Feed")
        self.assertTrue(product.get("description"), "Product must have description")
        self.assertTrue(product.get("image"), "Product must have an image URL for Google rich results")
        self.assertTrue(product.get("sku"), "Product must have SKU identifier")
        self.assertTrue(product.get("offers"), "Product must have offers")

    def test_product_snippet_has_aggregaterating_and_reviews(self):
        """Ensure Product node contains aggregateRating and review to resolve GSC Product snippet issues."""
        graph = self.json_data.get("@graph", [])
        product = [node for node in graph if node.get("@type") == "Product"][0]

        # 1. AggregateRating checks
        agg = product.get("aggregateRating")
        self.assertIsNotNone(agg, "Product must have 'aggregateRating' to resolve GSC issue")
        self.assertEqual(agg.get("@type"), "AggregateRating")
        self.assertEqual(str(agg.get("ratingValue")), "4.9")
        self.assertEqual(int(agg.get("reviewCount")), 38)
        self.assertEqual(str(agg.get("bestRating")), "5")
        self.assertEqual(str(agg.get("worstRating")), "1")

        # 2. Review list checks
        reviews = product.get("review")
        self.assertIsInstance(reviews, list, "Product must have a list of 'review' items")
        self.assertGreaterEqual(len(reviews), 2, "Expected at least 2 reviews")

        for rev in reviews:
            self.assertEqual(rev.get("@type"), "Review")
            self.assertTrue(rev.get("name"), "Review must have a title/name")
            self.assertTrue(rev.get("reviewBody"), "Review must have reviewBody")
            self.assertTrue(rev.get("datePublished"), "Review must have datePublished")
            
            author = rev.get("author")
            self.assertIsInstance(author, dict, "Review author must be an object")
            self.assertEqual(author.get("@type"), "Person")
            self.assertTrue(author.get("name"), "Author must have a name")

            rating = rev.get("reviewRating")
            self.assertIsInstance(rating, dict, "Review rating must be an object")
            self.assertEqual(rating.get("@type"), "Rating")
            self.assertEqual(str(rating.get("ratingValue")), "5")
            self.assertEqual(str(rating.get("bestRating")), "5")

    def test_reviews_are_visibly_rendered_in_html(self):
        """Ensure that all reviews in JSON-LD structured data are visibly rendered in HTML (Google quality guideline)."""
        graph = self.json_data.get("@graph", [])
        product = [node for node in graph if node.get("@type") == "Product"][0]
        reviews = product.get("review", [])

        # Check section exists
        self.assertIn('id="reviews"', self.html, "HTML must contain a visible #reviews section")
        self.assertIn("4.9 / 5.0", self.html, "HTML must display the aggregate rating")
        self.assertIn("38 Verified Reviews", self.html, "HTML must display review count")

        for rev in reviews:
            author_name = rev["author"]["name"]
            review_snippet = rev["reviewBody"][:50]
            self.assertIn(author_name, self.html, f"Author '{author_name}' must be visible in HTML body")
            self.assertIn(review_snippet, self.html, f"Review text snippet '{review_snippet}' must be visible in HTML body")

    def test_merchant_listings_compliance(self):
        """Ensure Product node resolves all 5 Google Merchant listings issues."""
        graph = self.json_data.get("@graph", [])
        product = [node for node in graph if node.get("@type") == "Product"][0]

        # 1. Critical: Image field (must be list of image URLs)
        images = product.get("image")
        self.assertIsInstance(images, list, "Product 'image' must be a list of URLs for Merchant listings")
        self.assertGreaterEqual(len(images), 1, "Must contain at least 1 image URL")
        for img in images:
            self.assertTrue(img.startswith("https://surplusdocket.com/"), "Image must be absolute HTTPS URL")

        # 2. Brand object type
        brand = product.get("brand")
        self.assertIsInstance(brand, dict, "Product 'brand' must be an object")
        self.assertEqual(brand.get("@type"), "Brand", "Brand must have @type: 'Brand'")
        self.assertEqual(brand.get("name"), "Surplus Docket", "Brand must have name: 'Surplus Docket'")

        # 3. Offers checks
        offers = product.get("offers")
        self.assertIsInstance(offers, dict, "Product must have 'offers' object")

        # 3a. validFrom
        self.assertTrue(offers.get("validFrom"), "Offers must contain 'validFrom'")
        self.assertRegex(offers.get("validFrom"), r"^\d{4}-\d{2}-\d{2}", "validFrom must be ISO date")

        # 3b. hasMerchantReturnPolicy
        return_policy = offers.get("hasMerchantReturnPolicy")
        self.assertIsInstance(return_policy, dict, "Offers must contain 'hasMerchantReturnPolicy'")
        self.assertEqual(return_policy.get("@type"), "MerchantReturnPolicy")
        self.assertEqual(return_policy.get("applicableCountry"), "US")
        self.assertEqual(return_policy.get("returnPolicyCategory"), "https://schema.org/MerchantReturnFiniteReturnWindow")
        self.assertEqual(return_policy.get("merchantReturnDays"), 14)
        self.assertEqual(return_policy.get("returnFees"), "https://schema.org/FreeReturn")
        self.assertEqual(return_policy.get("merchantReturnLink"), "https://surplusdocket.com/refund-policy.html")

        # 3c. shippingDetails
        shipping = offers.get("shippingDetails")
        self.assertIsInstance(shipping, dict, "Offers must contain 'shippingDetails'")
        self.assertEqual(shipping.get("@type"), "OfferShippingDetails")
        
        rate = shipping.get("shippingRate")
        self.assertIsInstance(rate, dict)
        self.assertEqual(rate.get("value"), "0.00")
        self.assertEqual(rate.get("currency"), "USD")

        destination = shipping.get("shippingDestination")
        self.assertIsInstance(destination, dict)
        self.assertEqual(destination.get("addressCountry"), "US")

        delivery = shipping.get("deliveryTime")
        self.assertIsInstance(delivery, dict)
        self.assertEqual(delivery.get("@type"), "ShippingDeliveryTime")


if __name__ == "__main__":
    unittest.main()

