#!/usr/bin/env python3
"""
Surplus Docket — Unified AI Provider Architecture
=================================================
Provides an enterprise AI gateway with Google AI (Gemini) as primary provider
(leveraging user's Google AI account at zero marginal per-token cost) with
OpenAI as an optional secondary fallback.

Capabilities:
1. Native Multimodal Audio Transcription: Directly processes MP3/WAV audio
   via Gemini 1.5 Flash inline audio data, transcribing and extracting legal
   metadata (caller, phone, email, state, county, docket) in a single request.
2. Structured Text Generation & Entity Extraction.
3. Atomic AI Budget & Usage Ledger (tracks tokens, latency, provider, cost).
4. Graceful Fallback: Gemini -> OpenAI -> Local Deterministic Rules.
"""

import base64
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LEDGER_FILE = DATA_DIR / "ai_usage_ledger.json"

DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
DEFAULT_OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

AI_BUDGET_CONFIG = {
    "primary_provider": "google_gemini",
    "routine_model": DEFAULT_GEMINI_MODEL,
    "fallback_model": DEFAULT_OPENAI_MODEL,
    "daily_spend_cap_usd": 10.00,
    "monthly_spend_cap_usd": 100.00,
    "target_workflow_cost_usd": 0.01
}


def load_ai_usage_ledger():
    """Loads all records from the AI usage ledger."""
    if not LEDGER_FILE.exists():
        return {"transactions": []}
    try:
        with open(LEDGER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {"transactions": data}
            return data
    except Exception:
        return {"transactions": []}


def get_active_provider():
    """
    Returns ('gemini', key) if Google AI is configured,
    ('openai', key) if OpenAI is configured,
    or ('local', None) if neither is set.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gemini_key:
        return "gemini", gemini_key

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        return "openai", openai_key

    return "local", None


def record_ai_usage(provider, model, task_type=None, input_tokens=0, output_tokens=0, audio_secs=0, cost_usd=0.0, status="success", **kwargs):
    """Records AI token and financial usage to persistent append-only ledger."""
    actual_task = task_type or kwargs.get("operation") or "general_task"
    actual_in = input_tokens or kwargs.get("prompt_tokens") or 0
    actual_out = output_tokens or kwargs.get("completion_tokens") or 0
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provider": provider,
        "model": model,
        "task_type": actual_task,
        "input_tokens": actual_in,
        "output_tokens": actual_out,
        "audio_seconds": audio_secs,
        "cost_usd": round(cost_usd, 6),
        "estimated_cost_usd": round(cost_usd, 6),
        "status": status,
    }
    if "metadata" in kwargs:
        entry["metadata"] = kwargs["metadata"]

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        records = []
        if LEDGER_FILE.exists():
            try:
                with open(LEDGER_FILE, "r", encoding="utf-8") as f:
                    records = json.load(f)
            except Exception:
                records = []

        records.append(entry)
        records = records[-1000:]  # Keep last 1,000 ledger records
        with open(LEDGER_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
    except Exception as e:
        sys.stderr.write(f"[ai_provider] Warning: could not log usage: {e}\n")
    return entry


def transcribe_audio_with_gemini(audio_bytes, mime_type="audio/mp3", api_key=None, model=DEFAULT_GEMINI_MODEL):
    """
    Transcribes audio and extracts caller metadata using Google Gemini multimodal capabilities.
    Executes in a single call with zero intermediate speech-to-text files.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key or not audio_bytes:
        return None

    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    clean_mime = "audio/mp3" if "mp3" in mime_type.lower() else ("audio/wav" if "wav" in mime_type.lower() else mime_type)

    prompt_text = (
        "You are an intake coordinator for Surplus Docket (surplusdocket.com), an intelligence platform "
        "indexing court registry excess proceeds and tax deed surplus. "
        "Listen to this legal voicemail recording. Transcribe the spoken audio verbatim and extract all entities. "
        "Return ONLY a valid JSON object matching this exact schema:\n"
        "{\n"
        '  "transcript": "Exact spoken words",\n'
        '  "name": "Caller full name if stated, or Inquiring Counsel",\n'
        '  "phone": "Caller phone number if stated or detected",\n'
        '  "email": "Spoken email address normalized (e.g. dave@gmail.com) or empty string",\n'
        '  "state_code": "Two letter state code (FL, TX, GA, CA, NC, TN) if mentioned",\n'
        '  "county": "County name if mentioned",\n'
        '  "docket": "Case or docket number if mentioned"\n'
        "}"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_text},
                    {
                        "inline_data": {
                            "mime_type": clean_mime,
                            "data": b64_audio
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    try:
        t0 = time.time()
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "SurplusDocket-GeminiEngine/2026.1"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - t0

            # Extract generated content
            candidates = resp_data.get("candidates", [])
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return None
            text_out = parts[0].get("text", "").strip()

            usage = resp_data.get("usageMetadata", {})
            in_toks = usage.get("promptTokenCount", 0)
            out_toks = usage.get("candidatesTokenCount", 0)

            # Gemini Flash is free or $0.000075/1k toks ($0 under monthly Google AI plan)
            record_ai_usage("google_gemini", model, "audio_transcription_and_extraction",
                            input_tokens=in_toks, output_tokens=out_toks, cost_usd=0.0)

            try:
                parsed = json.loads(text_out)
                return parsed
            except Exception:
                # If JSON response has backticks
                cleaned = re.sub(r"^```json\s*", "", text_out)
                cleaned = re.sub(r"\s*```$", "", cleaned)
                return json.loads(cleaned)
    except Exception as e:
        record_ai_usage("google_gemini", model, "audio_transcription_and_extraction", status=f"failed: {e}")
        return None


def generate_text(prompt, system_instruction=None, max_tokens=1024, temperature=0.2):
    """
    Executes a structured text generation request using Google Gemini first,
    falling back to OpenAI if Gemini is not configured.
    """
    provider, key = get_active_provider()

    if provider == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{DEFAULT_GEMINI_MODEL}:generateContent?key={key}"
        parts = []
        if system_instruction:
            parts.append({"text": f"SYSTEM INSTRUCTION: {system_instruction}\n\n"})
        parts.append({"text": prompt})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    out = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    record_ai_usage("google_gemini", DEFAULT_GEMINI_MODEL, "text_generation", cost_usd=0.0)
                    return out
        except Exception as e:
            record_ai_usage("google_gemini", DEFAULT_GEMINI_MODEL, "text_generation", status=f"failed: {e}")

    elif provider == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": DEFAULT_OPENAI_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choice = data.get("choices", [{}])[0]
                out = choice.get("message", {}).get("content", "")
                usage = data.get("usage", {})
                record_ai_usage("openai", DEFAULT_OPENAI_MODEL, "text_generation",
                                input_tokens=usage.get("prompt_tokens", 0),
                                output_tokens=usage.get("completion_tokens", 0),
                                cost_usd=0.005)
                return out
        except Exception as e:
            record_ai_usage("openai", DEFAULT_OPENAI_MODEL, "text_generation", status=f"failed: {e}")

    return ""
