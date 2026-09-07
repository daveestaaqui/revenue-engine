#!/usr/bin/env python3
"""
Unit Tests for Unified AI Provider Architecture (portal/ai_provider.py)
Tests:
1. Provider detection (Gemini vs OpenAI vs Local)
2. Multimodal audio transcription via Google Gemini
3. Text generation via Gemini and OpenAI
4. Ledger usage recording
"""

import json
import os
import unittest
from unittest.mock import patch, MagicMock

from portal.ai_provider import (
    get_active_provider,
    record_ai_usage,
    transcribe_audio_with_gemini,
    generate_text,
    LEDGER_FILE,
)


class TestAIProvider(unittest.TestCase):

    def test_get_active_provider_gemini_priority(self):
        """Verifies that Google Gemini is prioritized over OpenAI when configured."""
        env = {
            "GEMINI_API_KEY": "AIzaSyFakeGeminiKey123",
            "OPENAI_API_KEY": "sk-fake-openai-key"
        }
        with patch.dict(os.environ, env, clear=True):
            prov, key = get_active_provider()
            self.assertEqual(prov, "gemini")
            self.assertEqual(key, "AIzaSyFakeGeminiKey123")

    def test_get_active_provider_openai_fallback(self):
        """Verifies that OpenAI is used if Gemini key is not set."""
        env = {
            "OPENAI_API_KEY": "sk-fake-openai-key"
        }
        with patch.dict(os.environ, env, clear=True):
            prov, key = get_active_provider()
            self.assertEqual(prov, "openai")
            self.assertEqual(key, "sk-fake-openai-key")

    def test_get_active_provider_local_default(self):
        """Verifies local default when neither key is set."""
        with patch.dict(os.environ, {}, clear=True):
            prov, key = get_active_provider()
            self.assertEqual(prov, "local")
            self.assertIsNone(key)

    def test_transcribe_audio_with_gemini_mocked(self):
        """Tests that transcribe_audio_with_gemini correctly parses Gemini's multimodal response."""
        mock_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps({
                                    "transcript": "Hello, this is Attorney Sarah Jenkins in Fulton County Georgia.",
                                    "name": "Sarah Jenkins",
                                    "phone": "508-555-1212",
                                    "email": "sarah@jenkinslaw.com",
                                    "state_code": "GA",
                                    "county": "Fulton",
                                    "docket": "2024-CV-12345"
                                })
                            }
                        ]
                    }
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 120,
                "candidatesTokenCount": 45
            }
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = transcribe_audio_with_gemini(b"fake_audio", mime_type="audio/mp3", api_key="fake-gemini-key")
            self.assertIsNotNone(res)
            self.assertEqual(res["name"], "Sarah Jenkins")
            self.assertEqual(res["state_code"], "GA")
            self.assertEqual(res["county"], "Fulton")
            self.assertEqual(res["email"], "sarah@jenkinslaw.com")
            self.assertIn("Attorney Sarah Jenkins", res["transcript"])

    def test_record_ai_usage(self):
        """Verifies that record_ai_usage logs correctly to data/ai_usage_ledger.json."""
        record_ai_usage("google_gemini", "gemini-1.5-flash", "unit_test", input_tokens=50, output_tokens=25, cost_usd=0.0)
        self.assertTrue(LEDGER_FILE.exists())
        with open(LEDGER_FILE, "r", encoding="utf-8") as f:
            ledger = json.load(f)
            self.assertTrue(len(ledger) > 0)
            last = ledger[-1]
            self.assertEqual(last["provider"], "google_gemini")
            self.assertEqual(last["task_type"], "unit_test")


if __name__ == "__main__":
    unittest.main()
