import csv
import io
import unittest
from copy import deepcopy
from decimal import Decimal

from portal.crm_export_engine import (
    ExportValidationError,
    export_to_clio_csv,
    export_to_filevine_csv,
)


def example_lead(**overrides):
    lead = {
        "lead_id": "DEMO-001",
        "first_name": "Example",
        "last_name": "Claimant",
        "state": "FL",
        "county": "Example County",
        "gross_surplus": Decimal("84250.00"),
        "docket_number": "00001234",
        "verified_status": "unverified",
    }
    lead.update(overrides)
    return lead


def rows(content):
    return list(csv.DictReader(io.StringIO(content, newline="")))


class CRMExportTests(unittest.TestCase):
    def test_clio_mapping_and_input_immutability(self):
        lead = example_lead()
        original = deepcopy(lead)
        result = rows(export_to_clio_csv([lead]))[0]

        self.assertEqual(result["First Name"], "Example")
        self.assertEqual(result["Matter Reference"], "DEMO-001")
        self.assertEqual(result["SD Gross Surplus USD"], "84250.00")
        self.assertEqual(result["SD Docket Number"], "00001234")
        self.assertEqual(result["SD Verified Status"], "unverified")
        self.assertEqual(lead, original)

    def test_filevine_mapping(self):
        result = rows(export_to_filevine_csv([
            example_lead(project_type="Surplus Intake")
        ]))[0]
        self.assertEqual(result["Project Type"], "Surplus Intake")
        self.assertEqual(result["Project Reference"], "DEMO-001")
        self.assertIn("Surplus review", result["Project Name"])

    def test_quotes_commas_newlines_and_unicode(self):
        value = 'Example, "Trust"\nJosé'
        result = rows(export_to_clio_csv([
            example_lead(company_name=value)
        ]))[0]
        self.assertEqual(result["Company"], value)

    def test_formula_hardening(self):
        for payload in (
            "=HYPERLINK(\"https://example.invalid\")",
            "+15551234567",
            "-1+1",
            "@SUM(1,1)",
            "\t=1+1",
            "\ufeff=1+1",
        ):
            with self.subTest(payload=payload):
                result = rows(export_to_clio_csv([
                    example_lead(company_name=payload)
                ]))[0]
                self.assertTrue(result["Company"].startswith("'"))

    def test_invalid_money_rejected(self):
        for value in (1.25, True, "-1.00", "NaN", "1.001", "1e5"):
            with self.subTest(value=value):
                with self.assertRaises(ExportValidationError):
                    export_to_clio_csv([example_lead(gross_surplus=value)])

    def test_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(ExportValidationError, "duplicate"):
            export_to_clio_csv([example_lead(), example_lead()])

    def test_verified_requires_evidence_metadata(self):
        with self.assertRaisesRegex(ExportValidationError, "requires"):
            export_to_clio_csv([example_lead(verified_status="verified")])

    def test_timezone_normalization(self):
        result = rows(export_to_clio_csv([
            example_lead(verified_at="2026-09-07T09:00:00-04:00")
        ]))[0]
        self.assertEqual(result["SD Verified At UTC"], "2026-09-07T13:00:00Z")

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ExportValidationError):
            export_to_clio_csv([
                example_lead(verified_at="2026-09-07T09:00:00")
            ])

    def test_deadline_requires_legal_basis(self):
        with self.assertRaisesRegex(ExportValidationError, "deadline_basis"):
            export_to_clio_csv([
                example_lead(statutory_deadline="2026-12-01")
            ])

    def test_zero_score_requires_model_version(self):
        with self.assertRaisesRegex(ExportValidationError, "score_model_version"):
            export_to_clio_csv([example_lead(actionability_score=0)])

    def test_unsafe_source_url_rejected(self):
        for url in ("javascript:alert(1)", "https://user:secret@example.com"):
            with self.subTest(url=url):
                with self.assertRaises(ExportValidationError):
                    export_to_clio_csv([example_lead(source_url=url)])

    def test_empty_input_has_headers(self):
        content = export_to_clio_csv([])
        self.assertIn('"Matter Description"', content)
        self.assertEqual(rows(content), [])

    def test_generator_supported(self):
        content = export_to_filevine_csv(
            example_lead(lead_id=f"DEMO-{index}") for index in range(3)
        )
        self.assertEqual(len(rows(content)), 3)

    def test_errors_do_not_echo_contact_values(self):
        with self.assertRaises(ExportValidationError) as context:
            export_to_clio_csv([
                example_lead(first_name="PRIVATE-NAME", state="INVALID")
            ])
        self.assertNotIn("PRIVATE-NAME", str(context.exception))


if __name__ == "__main__":
    unittest.main()
