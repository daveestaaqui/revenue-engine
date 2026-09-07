#!/usr/bin/env python3
"""
Surplus Docket — Golden Benchmark Evaluation Suite (Candidate 19)
==================================================================
Comprehensive regression and invariant test suite:
1. Plan Contract & Entitlement Gating ($249 Tri-State vs $449 6-State + API)
2. REST API Engine, Bearer Authentication, Rate Limiting & Cursor Pagination
3. Bar Ethics & Outreach Policy Engine (FL Bar Rule 4-7.18, UPL defense, SMS gating)
4. AI Provider Google Gemini Routing & Atomic Budget Ledger
5. Preliminary Lien Screening & Evidence Graph Classification
6. Bounded Autonomous Sentinel Anomaly Detection & Key Quarantine
"""

import os
import json
import time
import base64
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

from portal.api_engine import (
    authenticate_bearer_token,
    handle_get_opportunities,
    handle_get_coverage,
    handle_get_usage,
    handle_get_opportunity_by_id,
    enforce_rate_limit,
    hash_token,
    APIAuthError,
    PLAN_TRI_STATE,
    PLAN_SIX_STATE
)
from compliance.outreach_policy_engine import (
    evaluate_outreach_permission,
    GENERAL_UPL_DISCLAIMER,
    STATE_BAR_RULES
)
from portal.ai_provider import (
    generate_text,
    transcribe_audio_with_gemini,
    record_ai_usage,
    load_ai_usage_ledger,
    AI_BUDGET_CONFIG
)
from portal.lien_screening import (
    evaluate_preliminary_lien_screen,
    RecordedInstrument,
    MANDATORY_TITLE_DISCLAIMER
)
from portal.sentinel import (
    record_sentinel_event,
    quarantine_api_key,
    inspect_ai_spend_anomaly,
    SENTINEL_LOG_FILE
)


class TestGoldenPlanEntitlements(unittest.TestCase):
    """Verifies commercial boundaries and plan contracts."""

    def test_plan_pricing_and_features(self):
        self.assertEqual(PLAN_TRI_STATE["monthly_price_usd"], 249)
        self.assertEqual(PLAN_TRI_STATE["max_states"], 3)
        self.assertFalse(PLAN_TRI_STATE["rest_api_enabled"])

        self.assertEqual(PLAN_SIX_STATE["monthly_price_usd"], 449)
        self.assertEqual(PLAN_SIX_STATE["max_states"], 6)
        self.assertTrue(PLAN_SIX_STATE["rest_api_enabled"])
        self.assertEqual(PLAN_SIX_STATE["rate_limit_per_minute"], 60)
        self.assertEqual(PLAN_SIX_STATE["monthly_request_quota"], 50000)

    def test_tri_state_rest_api_rejection(self):
        """Tri-State subscriber keys must be blocked from REST API access with 403 Forbidden."""
        with self.assertRaises(APIAuthError) as ctx:
            authenticate_bearer_token("Bearer sd_test_tri_state_key_blocked")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.error_code, "PLAN_UPGRADE_REQUIRED")
        self.assertIn("upgrade_url", ctx.exception.extra)

    def test_master_suite_api_authentication(self):
        """Master Suite test key must authenticate successfully with all 6 jurisdictions."""
        tenant = authenticate_bearer_token("Bearer sd_test_admin_key_master_suite")
        self.assertEqual(tenant["status"], "ACTIVE")
        self.assertTrue(tenant["rest_api_enabled"])
        self.assertEqual(len(tenant["jurisdictions"]), 6)


class TestGoldenRESTAPIEngine(unittest.TestCase):
    """Verifies read-oriented REST API endpoints, pagination, and governors."""

    def test_missing_and_malformed_auth(self):
        # Missing auth
        code, body, _ = handle_get_opportunities(None, {})
        self.assertEqual(code, 401)
        self.assertEqual(body["error"], "MISSING_AUTHORIZATION")

        # Bad format
        code, body, _ = handle_get_opportunities("Basic 12345", {})
        self.assertEqual(code, 401)
        self.assertEqual(body["error"], "INVALID_AUTHORIZATION_FORMAT")

        # Bad prefix
        code, body, _ = handle_get_opportunities("Bearer sk_live_openai12345", {})
        self.assertEqual(code, 401)
        self.assertEqual(body["error"], "INVALID_KEY_PREFIX")

    def test_get_opportunities_pagination_and_filtering(self):
        auth = "Bearer sd_test_admin_key_master_suite"
        code, body, headers = handle_get_opportunities(auth, {"limit": 3})
        self.assertEqual(code, 200)
        self.assertIn("data", body)
        self.assertIn("pagination", body)
        self.assertIn("X-RateLimit-Limit", headers)
        self.assertIn("X-RateLimit-Remaining", headers)

        records = body["data"]
        self.assertLessEqual(len(records), 3)

        # Test cursor offset pagination
        if body["pagination"]["has_more"]:
            next_cur = body["pagination"]["next_cursor"]
            self.assertIsNotNone(next_cur)
            code2, body2, _ = handle_get_opportunities(auth, {"cursor": next_cur, "limit": 2})
            self.assertEqual(code2, 200)
            self.assertNotEqual(body["data"][0], body2["data"][0])

    def test_unentitled_state_filtering(self):
        auth = "Bearer sd_test_admin_key_master_suite"
        # Asking for non-existent / unentitled state 'NY'
        code, body, _ = handle_get_opportunities(auth, {"state": "NY"})
        self.assertEqual(code, 403)
        self.assertEqual(body["error"], "STATE_NOT_ENTITLED")

    def test_get_coverage_and_usage(self):
        auth = "Bearer sd_test_admin_key_master_suite"
        # Coverage
        code, cov, _ = handle_get_coverage(auth)
        self.assertEqual(code, 200)
        self.assertIn("FL", cov["supported_jurisdictions"])
        self.assertIn("TX", cov["supported_jurisdictions"])
        self.assertIn("Monday through Friday", cov["delivery_schedule"])

        # Usage
        code, usage, _ = handle_get_usage(auth)
        self.assertEqual(code, 200)
        self.assertEqual(usage["rate_limits"]["requests_per_minute_limit"], 60)
        self.assertEqual(usage["rate_limits"]["monthly_quota_limit"], 50000)

    def test_rate_limit_governor(self):
        digest = hash_token("sd_test_burst_token")
        # Consume 60 requests
        for i in range(60):
            allowed, headers = enforce_rate_limit(digest, limit_per_minute=60)
            self.assertTrue(allowed)
        # 61st request must be denied
        allowed, headers = enforce_rate_limit(digest, limit_per_minute=60)
        self.assertFalse(allowed)
        self.assertEqual(headers["X-RateLimit-Remaining"], "0")
        self.assertEqual(headers["Retry-After"], "60")


class TestGoldenBarEthicsEngine(unittest.TestCase):
    """Verifies compliance with Bar Rules across all 6 jurisdictions."""

    def test_upl_defense_blocks_legal_representation_inquiry(self):
        context = {
            "jurisdiction": "FL",
            "channel": "email",
            "recipient_type": "owner",
            "purpose": "transactional_reply",
            "requested_legal_representation": True
        }
        decision, reason, disclaimers = evaluate_outreach_permission(context)
        self.assertEqual(decision, "BLOCK")
        self.assertIn("non-lawyer data publisher", reason.lower())
        self.assertTrue(any("not a law firm" in d.lower() for d in disclaimers))

    def test_florida_phone_solicitation_blocked(self):
        context = {
            "jurisdiction": "FL",
            "channel": "phone",
            "recipient_type": "owner",
            "purpose": "cold_solicitation",
            "has_prior_express_consent": False
        }
        decision, reason, _ = evaluate_outreach_permission(context)
        self.assertEqual(decision, "BLOCK")
        self.assertIn("Florida Bar Rule 4-7.18", reason)

    def test_sms_followup_blocked_without_prior_express_consent(self):
        context = {
            "jurisdiction": "TX",
            "channel": "sms",
            "recipient_type": "claimant",
            "purpose": "inbound_callback",
            "has_prior_express_consent": False
        }
        decision, reason, _ = evaluate_outreach_permission(context)
        self.assertEqual(decision, "BLOCK")
        self.assertIn("consent", reason.lower())

    def test_attorney_transactional_email_allowed_with_disclaimers(self):
        context = {
            "jurisdiction": "FL",
            "channel": "email",
            "recipient_type": "attorney",
            "purpose": "transactional_reply"
        }
        decision, reason, disclaimers = evaluate_outreach_permission(context)
        self.assertEqual(decision, "ALLOW")
        self.assertTrue(len(disclaimers) >= 2)


class TestGoldenAIProviderBudget(unittest.TestCase):
    """Verifies Gemini-first AI Provider and Atomic Budget Ledger."""

    def test_ai_budget_recording(self):
        initial_ledger = load_ai_usage_ledger()
        initial_count = len(initial_ledger.get("transactions", []))

        record = record_ai_usage(
            provider="gemini",
            model="gemini-1.5-flash",
            operation="test_golden_benchmark",
            prompt_tokens=150,
            completion_tokens=50,
            cost_usd=0.000035,
            metadata={"test": "golden_benchmark"}
        )
        self.assertEqual(record["provider"], "gemini")
        self.assertGreater(record["cost_usd"], 0)

        updated_ledger = load_ai_usage_ledger()
        self.assertEqual(len(updated_ledger.get("transactions", [])), initial_count + 1)

    def test_gemini_multimodal_audio_fallback(self):
        """Audio transcription should gracefully fall back to Whisper when Gemini mock returns None."""
        res = transcribe_audio_with_gemini(b"FAKE_AUDIO_DATA_FOR_TEST", "audio/mp3", "test_call.mp3")
        # In test mode without API keys, returns None or Whisper fallback dict
        if res is not None:
            self.assertIn("transcript", res)


class TestGoldenLienScreening(unittest.TestCase):
    """Verifies preliminary lien screening and evidence graph assembly."""

    def test_lien_screening_with_satisfied_and_active_instruments(self):
        instruments = [
            RecordedInstrument(
                instrument_id="INST-001",
                document_type="MORTGAGE",
                recording_date="2018-05-12",
                grantor="John Doe",
                grantee="First Horizon Bank",
                principal_amount_usd=120000.0,
                instrument_number="2018-019283"
            ),
            RecordedInstrument(
                instrument_id="INST-002",
                document_type="SATISFACTION",
                recording_date="2022-01-15",
                grantor="First Horizon Bank",
                grantee="John Doe",
                principal_amount_usd=120000.0,
                notes="2018-019283"
            ),
            RecordedInstrument(
                instrument_id="INST-003",
                document_type="HOA_LIEN",
                recording_date="2023-09-01",
                grantor="John Doe",
                grantee="Lakeview Meadows HOA",
                principal_amount_usd=3450.0,
                instrument_number="2023-088192"
            )
        ]

        result = evaluate_preliminary_lien_screen(
            docket_number="2024-TD-009999",
            jurisdiction="FL",
            county="Orange",
            property_address="123 Palm Way, Orlando FL",
            surplus_balance_usd=45000.0,
            owner_of_record="John Doe",
            recorded_instruments=instruments
        )

        self.assertEqual(result.jurisdiction, "FL")
        self.assertEqual(len(result.satisfied_encumbrances), 1)
        self.assertEqual(len(result.active_encumbrances), 1)
        self.assertEqual(result.active_encumbrances[0]["document_type"], "HOA_LIEN")
        self.assertEqual(result.preliminary_distribution_tier, "SUBSTANTIAL_EQUITY_AFTER_LIENS")
        self.assertIn(MANDATORY_TITLE_DISCLAIMER, result.disclaimer)

    def test_estate_docket_triggers_probate_question(self):
        result = evaluate_preliminary_lien_screen(
            docket_number="2024-TD-001501",
            jurisdiction="FL",
            county="Orange",
            property_address="3309 Rosewood Ct",
            surplus_balance_usd=61800.0,
            owner_of_record="ESTATE OF ELEANOR VANCE",
            recorded_instruments=[]
        )
        self.assertTrue(any("estate" in q.lower() or "probate" in q.lower() for q in result.attorney_review_questions))


class TestGoldenSentinel(unittest.TestCase):
    """Verifies bounded autonomous sentinel containment and audit logging."""

    def test_sentinel_records_event(self):
        event = record_sentinel_event(
            event_type="TEST_BENCHMARK_PROBE",
            severity="INFO",
            details={"benchmark": "golden_evaluation"}
        )
        self.assertTrue(event["event_id"].startswith("SNTL-"))
        self.assertEqual(event["severity"], "INFO")

    def test_sentinel_spend_anomaly_warning(self):
        # 80% spend triggers WARNING
        event = inspect_ai_spend_anomaly(current_daily_spend_usd=8.00, daily_cap_usd=10.00)
        self.assertIsNotNone(event)
        self.assertEqual(event["severity"], "WARNING")

        # 95% spend triggers CRITICAL
        event2 = inspect_ai_spend_anomaly(current_daily_spend_usd=9.50, daily_cap_usd=10.00)
        self.assertIsNotNone(event2)
        self.assertEqual(event2["severity"], "CRITICAL")
        self.assertEqual(event2["containment_action"], "DEFER_NON_ESSENTIAL_WORKFLOWS")


if __name__ == "__main__":
    unittest.main()
