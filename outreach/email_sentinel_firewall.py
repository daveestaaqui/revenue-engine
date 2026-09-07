"""Inbound email quarantine and circuit breakers.

Security contract:
* is_safe=True permits further processing; it does NOT confer instruction authority.
* Never place inbound content in an LLM system/developer message.
* Rejected content is not returned. Preserve originals only in a restricted quarantine.
* The three-argument interface cannot inspect MIME parts, SPF/DKIM/DMARC,
  Auto-Submitted, References, or Return-Path. Inspect those at the gateway.
* Sender rate limits are not authenticated identities. Enforce gateway/global limits too.

Set SURPLUS_EMAIL_STATE_DB to a protected, persistent SQLite path for shared
single-host state. The default is process-local memory, suitable for development.
Do not store this database on a network filesystem.
"""

from __future__ import annotations

import hashlib
import html
import os
import re
import sqlite3
import threading
import time
import unicodedata
from collections.abc import Callable
from email.utils import parseaddr
from html.parser import HTMLParser

Result = tuple[bool, str, str, str]

MAX_SUBJECT_CHARS = 2_048
MAX_BODY_CHARS = 100_000
MAX_BODY_BYTES = 400_000


class _TextExtractor(HTMLParser):
    """Extract all text, including normally hidden text, for inspection."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self.parts.append(" ")
        for _, val in attrs:
            if val:
                self.parts.append(val)

    def handle_endtag(self, tag: str) -> None:
        self.parts.append(" ")


def _normalize(value: str) -> str:
    # Bound decoding passes; do not recursively expand attacker-controlled input.
    for _ in range(2):
        value = html.unescape(value)
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    return "".join(
        character
        for character in value
        if character in "\n\t"
        or not unicodedata.category(character).startswith("C")
    )


def _plain_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    return re.sub(r"[ \t]+", " ", "".join(parser.parts)).strip()


def _patterns(*values: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(value, re.IGNORECASE | re.DOTALL) for value in values)


INJECTION = _patterns(
    r"\b(?:ignore|disregard|forget|override|bypass)\b.{0,80}"
    r"\b(?:previous|prior|above|system|developer|safety|all)\b.{0,60}"
    r"\b(?:instructions?|prompts?|rules?|polic(?:y|ies)|messages?)\b",
    r"\b(?:ignore|bypass|disable)\s+(?:the\s+)?"
    r"(?:guardrails?|safety\s+filters?|security\s+checks?)\b",
    r"\b(?:reveal|print|show|repeat|dump|expose|extract|send|return)\b.{0,100}"
    r"\b(?:(?:system|developer|hidden|initial)\s+(?:prompt|instructions?)|"
    r"api[\s_-]*keys?|secrets?|access[\s_-]*tokens?|environment\s+variables?)\b",
    r"\b(?:api[\s_-]*key|system\s+prompt|developer\s+prompt)\b.{0,60}"
    r"\b(?:reveal|print|send|expose|extract)\b",
    r"\b(?:jailbreak|developer\s+mode|do\s+anything\s+now)\b",
    r"\byou\s+are\s+now\b.{0,50}\b(?:unrestricted|unfiltered|DAN)\b",
    r"(?:<\|(?:im_start|system|developer)\|>|"
    r"\[\s*(?:system|developer)\s*\]|"
    r"</?(?:system|developer)(?:\s[^>]{0,100})?>)",
    r"(?m)^\s*(?:system|developer)\s*:",
    r"\b(?:decode|execute|run)\b.{0,60}\b(?:base64|encoded\s+instructions?)\b",
)

SECRETS = _patterns(
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\bsk-[A-Za-z0-9_-]{20,}\b",
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
)

DANGEROUS = _patterns(
    r"\.(?:exe|scr|com|bat|cmd|ps1|vbs|vbe|js|jse|msi|hta|lnk|"
    r"iso|img|docm|xlsm|pptm|jar)(?:\b|[\"'>])",
    r"\b(?:enable\s+(?:macros|content)|powershell|"
    r"rundll32|mshta|credential\s+harvest|ransomware)\b",
    r"\b(?:wire\s+transfer|change\s+(?:the\s+)?bank\s+account|"
    r"new\s+banking\s+instructions|gift\s+cards?|seed\s+phrase)\b",
)

DISCOUNTS = _patterns(
    # Conservative: commercial terms need approved human handling.
    r"\b(?:discount|promo\s*code|coupon|waive\s+(?:all\s+)?fees?|"
    r"free\s+representation|guaranteed\s+recovery)\b",
    r"\b\d{1,3}\s*%\s+off\b",
)

REPRESENTATION = _patterns(
    r"\b(?:you|your\s+(?:firm|company))\s+(?:are|is)\s+"
    r"(?:now\s+)?(?:my|our)\s+(?:attorney|lawyer|counsel)\b",
    r"\b(?:act|appear|file|sign|negotiate)\b.{0,50}"
    r"\b(?:as\s+(?:my|our)\s+(?:attorney|lawyer|counsel)|"
    r"on\s+(?:my|our)\s+behalf)\b",
    r"\b(?:you\s+represent\s+me|we\s+represent\s+you|"
    r"we\s+are\s+your\s+(?:lawyers?|attorneys?))\b",
)

LEGAL_ADVICE = _patterns(
    r"\b(?:give|provide|need|want|demand)\b.{0,50}\blegal\s+advice\b",
    r"\b(?:should|must|can)\s+I\s+(?:sue|file|appeal|settle|"
    r"sign|waive|claim|litigate)\b",
    r"\b(?:tell|advise)\s+me\b.{0,60}\b(?:what|how|whether)\b.{0,60}"
    r"\b(?:file|sue|appeal|claim|settle)\b",
    r"\b(?:am\s+I|are\s+we)\s+(?:legally\s+)?entitled\b",
)

LOOP_SUBJECT = re.compile(
    r"^\s*(?:(?:re|fw|fwd)\s*:\s*)*"
    r"(?:automatic\s+reply|auto(?:matic)?[- ]?response|auto[- ]?reply|"
    r"out\s+of\s+(?:the\s+)?office|undeliverable|"
    r"delivery\s+(?:status\s+notification|failure)|"
    r"returned\s+mail|mail\s+delivery\s+(?:failed|subsystem))\b",
    re.IGNORECASE,
)

LOOP_BODY = re.compile(
    r"\b(?:this\s+is\s+an?\s+(?:automated|automatic)\s+(?:reply|response)|"
    r"delivery\s+to\s+the\s+following\s+recipients\s+failed|"
    r"message\s+could\s+not\s+be\s+delivered)\b",
    re.IGNORECASE,
)


class EmailSentinel:
    def __init__(
        self,
        db_path: str = ":memory:",
        *,
        max_messages: int = 20,
        window_seconds: int = 300,
        repeat_limit: int = 3,
        max_entries: int = 100_000,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if min(max_messages, window_seconds, repeat_limit, max_entries) <= 0:
            raise ValueError("Circuit-breaker limits must be positive")
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.repeat_limit = repeat_limit
        self.max_entries = max_entries
        self.clock = clock
        self.lock = threading.Lock()
        self.db = sqlite3.connect(
            db_path, timeout=5, isolation_level=None, check_same_thread=False
        )
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS email_attempts (
                sender_hash TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                received_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS email_attempts_sender
                ON email_attempts(sender_hash, received_at);
            CREATE INDEX IF NOT EXISTS email_attempts_time
                ON email_attempts(received_at);
            """
        )

    def close(self) -> None:
        with self.lock:
            self.db.close()

    def _record(self, sender: str, subject: str, body: str) -> str | None:
        sender_hash = hashlib.sha256(sender.encode()).hexdigest()
        fingerprint = hashlib.sha256(
            (subject.casefold() + "\0" + body.casefold()).encode()
        ).hexdigest()
        now = self.clock()

        with self.lock:
            try:
                self.db.execute("BEGIN IMMEDIATE")
                self.db.execute(
                    "DELETE FROM email_attempts WHERE received_at <= ?",
                    (now - self.window_seconds,),
                )
                count, repeats = self.db.execute(
                    """
                    SELECT COUNT(*),
                           COALESCE(SUM(fingerprint = ?), 0)
                    FROM email_attempts WHERE sender_hash = ?
                    """,
                    (fingerprint, sender_hash),
                ).fetchone()

                if count >= self.max_messages:
                    category = "rate_limited"
                elif self.db.execute(
                    "SELECT COUNT(*) FROM email_attempts"
                ).fetchone()[0] >= self.max_entries:
                    category = "capacity_exceeded"
                else:
                    self.db.execute(
                        "INSERT INTO email_attempts VALUES (?, ?, ?)",
                        (sender_hash, fingerprint, now),
                    )
                    category = (
                        "loop_detected"
                        if repeats + 1 >= self.repeat_limit
                        else None
                    )
                self.db.execute("COMMIT")
                return category
            except Exception:
                if self.db.in_transaction:
                    self.db.execute("ROLLBACK")
                raise

    def sanitize_inbound_message(
        self, sender: str, subject: str, body: str
    ) -> Result:
        if not all(isinstance(value, str) for value in (sender, subject, body)):
            return False, "invalid_input", "", "Sender, subject, and body must be strings"

        if (
            len(sender) > 512
            or len(subject) > MAX_SUBJECT_CHARS
            or len(body) > MAX_BODY_CHARS
        ):
            return False, "oversized_message", "", "Message exceeds configured limits"

        try:
            if len(body.encode("utf-8")) > MAX_BODY_BYTES:
                return False, "oversized_message", "", "Message exceeds byte limit"
            sender.encode("utf-8")
            subject.encode("utf-8")
        except UnicodeError:
            return False, "invalid_input", "", "Invalid Unicode input"

        if any(unicodedata.category(c).startswith("C") for c in sender):
            return False, "invalid_sender", "", "Control characters in sender"

        _, address = parseaddr(sender)
        address = address.casefold()
        if (
            len(address) > 254
            or not re.fullmatch(
                r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
                r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
                r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?",
                address,
            )
            or "," in sender
            or ";" in sender
        ):
            return False, "invalid_sender", "", "A single valid sender is required"

        normalized_subject = _normalize(subject)
        normalized_body = _normalize(body)
        try:
            plain = _plain_text(normalized_body)
        except Exception:
            return False, "invalid_content", "", "HTML normalization failed"

        if not plain:
            return False, "invalid_content", "", "Message body is empty"

        try:
            circuit = self._record(address, normalized_subject, plain)
        except sqlite3.Error:
            return False, "state_unavailable", "", "Circuit-breaker storage unavailable"

        if circuit:
            return False, circuit, "", "Inbound circuit breaker triggered"

        local_part = address.split("@", 1)[0]
        if (
            local_part in {"mailer-daemon", "postmaster"}
            or LOOP_SUBJECT.search(normalized_subject)
            or LOOP_BODY.search(plain)
        ):
            return False, "loop_detected", "", "Automated reply or delivery notification"

        # Scan both original markup/attributes and extracted text.
        inspection = "\n".join(
            (normalized_subject, normalized_body, plain)
        )

        checks = (
            ("prompt_injection", INJECTION, "Instruction override or secret extraction"),
            ("secret_exposure", SECRETS, "Potential credential material; restricted review"),
            ("dangerous_content", DANGEROUS, "Attachment, execution, or payment risk"),
            ("commercial_terms_review", DISCOUNTS, "Unapproved commercial terms"),
            (
                "representation_review",
                REPRESENTATION,
                "Attorney authority or representation requires human review",
            ),
            ("legal_advice_review", LEGAL_ADVICE, "Individualized legal guidance requested"),
        )
        for category, patterns, reason in checks:
            if any(pattern.search(inspection) for pattern in patterns):
                return False, category, "", reason

        return (
            True,
            "safe",
            plain,
            "No configured indicator matched; content remains untrusted data",
        )


_default: EmailSentinel | None = None
_default_lock = threading.Lock()


def sanitize_inbound_message(sender: str, subject: str, body: str) -> Result:
    """Return (is_safe, category, sanitized_body, reason). Fail closed on DB errors."""
    global _default
    try:
        with _default_lock:
            if _default is None:
                _default = EmailSentinel(
                    os.environ.get("SURPLUS_EMAIL_STATE_DB", ":memory:")
                )
        return _default.sanitize_inbound_message(sender, subject, body)
    except (sqlite3.Error, OSError):
        return False, "state_unavailable", "", "Circuit-breaker storage unavailable"
