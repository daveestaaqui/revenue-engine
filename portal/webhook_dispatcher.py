"""Signed HTTPS webhook delivery and receiver verification.

Wire protocol:
    signature = HMAC-SHA256(
        secret,
        ASCII(timestamp) + b"\\n" + ASCII(idempotency_key) + b"\\n" + raw_body
    )
    X-SurplusDocket-Signature: v1=<lowercase hex>

Use a different >=32-byte random secret for each endpoint. Protect secrets and
SQLite files with deployment-level access controls. HTTPS allowlists are trusted
configuration, not request input.

CRM formats below are Surplus Docket adapter contracts, NOT native Clio/Filevine
create-matter APIs. Native API authentication, field IDs, consent, and provider
versioning belong in the receiving adapter.

No automatic retries: persist events in an outbox, retry transient failures with
backoff, and reuse event_id. Exactly-once business execution requires a durable
inbox transaction with the consumer's business updates.
"""

from __future__ import annotations

import hashlib
import hmac
import http.client
import ipaddress
import json
import re
import socket
import sqlite3
import ssl
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

MAX_PAYLOAD_BYTES = 256 * 1024
MAX_RESPONSE_BYTES = 64 * 1024
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
PROVIDERS = frozenset({"clio", "filevine", "zapier", "custom"})


class WebhookError(ValueError):
    pass


class VerificationError(WebhookError):
    pass


class DeliveryError(RuntimeError):
    pass


def _secret_check(secret: bytes) -> None:
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise WebhookError("Endpoint secret must contain at least 32 bytes")


def _token_check(value: str, name: str) -> None:
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise WebhookError(f"Invalid {name}")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def idempotency_key(endpoint_id: str, event_id: str) -> str:
    _token_check(endpoint_id, "endpoint_id")
    _token_check(event_id, "event_id")
    return hashlib.sha256(
        _canonical_json(["surplusdocket-webhook-v1", endpoint_id, event_id])
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class WebhookEvent:
    event_id: str
    event_type: str
    occurred_at: datetime
    data: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class Endpoint:
    endpoint_id: str
    url: str
    provider: str
    secret: bytes = field(repr=False)
    bearer_token: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        _token_check(self.endpoint_id, "endpoint_id")
        _secret_check(self.secret)
        if self.provider not in PROVIDERS:
            raise WebhookError("Unsupported CRM provider")
        if self.bearer_token is not None and (
            not self.bearer_token
            or not self.bearer_token.isascii()
            or any(ord(c) < 33 or ord(c) == 127 for c in self.bearer_token)
        ):
            raise WebhookError("Invalid bearer token")


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    endpoint_id: str
    event_id: str
    idempotency_key: str
    status_code: int
    delivered: bool
    retryable: bool


def format_payload(event: WebhookEvent, endpoint: Endpoint) -> dict[str, Any]:
    _token_check(event.event_id, "event_id")
    _token_check(event.event_type, "event_type")
    if (
        not isinstance(event.occurred_at, datetime)
        or event.occurred_at.tzinfo is None
        or event.occurred_at.utcoffset() is None
    ):
        raise WebhookError("occurred_at must be timezone-aware")
    if not isinstance(event.data, Mapping):
        raise WebhookError("Event data must be a mapping")

    # Deep JSON snapshot: caller mutations cannot change the signed payload later.
    try:
        data = json.loads(_canonical_json(dict(event.data)))
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise WebhookError("Event data must be finite, UTF-8 JSON") from exc

    if endpoint.provider == "clio":
        adapter_payload = {"event": event.event_type, "data": data}
    elif endpoint.provider == "filevine":
        adapter_payload = {"eventName": event.event_type, "eventData": data}
    elif endpoint.provider == "zapier":
        adapter_payload = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "data": data,
        }
    else:
        adapter_payload = data

    return {
        "schema_version": "1.0",
        "adapter_contract": f"surplusdocket.{endpoint.provider}.v1",
        "destination": endpoint.endpoint_id,
        "event_id": event.event_id,
        "event_type": event.event_type,
        "occurred_at": event.occurred_at.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "idempotency_key": idempotency_key(endpoint.endpoint_id, event.event_id),
        "provider": endpoint.provider,
        "payload": adapter_payload,
    }


def sign_payload(
    secret: bytes, timestamp: str, key: str, body: bytes
) -> str:
    _secret_check(secret)
    if not re.fullmatch(r"[0-9]{1,12}", timestamp) or not HEX64.fullmatch(key):
        raise WebhookError("Invalid signature metadata")
    if not isinstance(body, bytes) or len(body) > MAX_PAYLOAD_BYTES:
        raise WebhookError("Invalid payload bytes")
    signed = timestamp.encode("ascii") + b"\n" + key.encode("ascii") + b"\n" + body
    return "v1=" + hmac.new(secret, signed, hashlib.sha256).hexdigest()


def _header_map(headers: Mapping[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for name, value in headers.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise VerificationError("Headers must be strings")
        name = name.lower()
        if name in normalized:
            raise VerificationError("Duplicate header")
        normalized[name] = value
    return normalized


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError("Duplicate JSON member")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise VerificationError("Non-finite JSON number")


def verify_webhook(
    body: bytes,
    headers: Mapping[str, str],
    secret: bytes,
    endpoint_id: str,
    *,
    now: int | None = None,
    tolerance_seconds: int = 300,
) -> dict[str, Any]:
    """Authenticate raw bytes and freshness; use accept_webhook for deduplication.

    The HTTP framework must reject duplicate physical signature/timestamp/key
    headers before collapsing headers into a dictionary. Never reserialize JSON
    before verification.
    """
    _secret_check(secret)
    _token_check(endpoint_id, "endpoint_id")
    if tolerance_seconds < 0:
        raise WebhookError("Negative timestamp tolerance")
    if not isinstance(body, bytes) or len(body) > MAX_PAYLOAD_BYTES:
        raise VerificationError("Invalid payload size")

    normalized = _header_map(headers)
    timestamp = normalized.get("x-surplusdocket-timestamp", "")
    key = normalized.get("idempotency-key", "")
    signature = normalized.get("x-surplusdocket-signature", "")

    if (
        not re.fullmatch(r"[0-9]{1,12}", timestamp)
        or not HEX64.fullmatch(key)
        or not re.fullmatch(r"v1=[0-9a-f]{64}", signature)
    ):
        raise VerificationError("Malformed signature metadata")

    current = int(time.time()) if now is None else now
    if abs(current - int(timestamp)) > tolerance_seconds:
        raise VerificationError("Expired or future timestamp")

    expected = sign_payload(secret, timestamp, key, body)
    if not hmac.compare_digest(expected, signature):
        raise VerificationError("Invalid signature")

    try:
        payload = json.loads(
            body.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise VerificationError("Invalid JSON payload") from exc

    if not isinstance(payload, dict):
        raise VerificationError("Payload must be an object")
    if (
        payload.get("schema_version") != "1.0"
        or payload.get("destination") != endpoint_id
        or payload.get("idempotency_key") != key
    ):
        raise VerificationError("Envelope metadata mismatch")

    event_id = payload.get("event_id")
    event_type = payload.get("event_type")
    try:
        _token_check(event_id, "event_id")
        _token_check(event_type, "event_type")
        expected_key = idempotency_key(endpoint_id, event_id)
    except WebhookError as exc:
        raise VerificationError("Invalid event identity") from exc

    if not hmac.compare_digest(expected_key, key):
        raise VerificationError("Idempotency key mismatch")
    provider = payload.get("provider")
    if (
        not isinstance(provider, str)
        or provider not in PROVIDERS
        or payload.get("adapter_contract") != f"surplusdocket.{provider}.v1"
        or not isinstance(payload.get("payload"), dict)
    ):
        raise VerificationError("Invalid adapter contract")

    try:
        occurred_at = payload["occurred_at"]
        if not isinstance(occurred_at, str) or not occurred_at.endswith("Z"):
            raise ValueError("Expected UTC timestamp")
        parsed = datetime.fromisoformat(occurred_at[:-1] + "+00:00")
        if parsed.utcoffset() is None:
            raise ValueError("Naive timestamp")
    except (KeyError, ValueError, TypeError) as exc:
        raise VerificationError("Invalid event timestamp") from exc

    return payload


class ReplayStore:
    """Atomic, persistent, bounded-time deduplication.

    A duplicate with the same raw body returns False. Reusing an event ID with a
    different body is an error. Keep retention at least as long as outbox retries.

    claim() alone does not provide exactly-once business execution: use a durable
    inbox or combine receipt insertion and business work in your own transaction.
    """

    def __init__(self, db_path: str, *, retention_seconds: int = 7 * 86400) -> None:
        if retention_seconds <= 0:
            raise ValueError("Retention must be positive")
        self.retention_seconds = retention_seconds
        self.lock = threading.Lock()
        self.db = sqlite3.connect(
            db_path, timeout=5, isolation_level=None, check_same_thread=False
        )
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS webhook_receipts (
                key TEXT PRIMARY KEY,
                body_hash TEXT NOT NULL,
                expires_at INTEGER NOT NULL
            )
            """
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS webhook_receipts_expiry "
            "ON webhook_receipts(expires_at)"
        )

    def close(self) -> None:
        with self.lock:
            self.db.close()

    def claim(self, key: str, body: bytes, *, now: int) -> bool:
        if not HEX64.fullmatch(key):
            raise VerificationError("Invalid idempotency key")
        digest = hashlib.sha256(body).hexdigest()
        with self.lock:
            try:
                self.db.execute("BEGIN IMMEDIATE")
                self.db.execute(
                    "DELETE FROM webhook_receipts WHERE expires_at <= ?", (now,)
                )
                row = self.db.execute(
                    "SELECT body_hash FROM webhook_receipts WHERE key = ?", (key,)
                ).fetchone()
                if row is not None:
                    if not hmac.compare_digest(row[0], digest):
                        raise VerificationError("Event ID reused with a different payload")
                    is_new = False
                else:
                    self.db.execute(
                        "INSERT INTO webhook_receipts VALUES (?, ?, ?)",
                        (key, digest, now + self.retention_seconds),
                    )
                    is_new = True
                self.db.execute("COMMIT")
                return is_new
            except Exception:
                if self.db.in_transaction:
                    self.db.execute("ROLLBACK")
                raise


def accept_webhook(
    body: bytes,
    headers: Mapping[str, str],
    secret: bytes,
    endpoint_id: str,
    store: ReplayStore,
    *,
    now: int | None = None,
    tolerance_seconds: int = 300,
) -> tuple[dict[str, Any], bool]:
    """Return (authenticated_payload, is_new); duplicates must not execute again."""
    current = int(time.time()) if now is None else now
    if store.retention_seconds <= 2 * tolerance_seconds:
        raise WebhookError("Replay retention must exceed the full freshness window")
    payload = verify_webhook(
        body, headers, secret, endpoint_id,
        now=current, tolerance_seconds=tolerance_seconds,
    )
    return payload, store.claim(payload["idempotency_key"], body, now=current)


def _validated_url(url: str, allowed_hosts: frozenset[str]) -> tuple[str, str]:
    if not isinstance(url, str) or (
        not url.isascii()
        or "\\" in url
        or any(ord(c) <= 32 or ord(c) == 127 for c in url)
    ):
        raise WebhookError("URL must be ASCII without whitespace or controls")
    try:
        parts = urlsplit(url)
        host = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise WebhookError("Malformed endpoint URL") from exc
    if (
        parts.scheme != "https"
        or not host
        or host.endswith(".")
        or host.lower() not in allowed_hosts
        or parts.username is not None
        or parts.password is not None
        or port not in (None, 443)
        or parts.fragment
        or not re.fullmatch(r"[A-Za-z0-9.:-]+", host)
    ):
        raise WebhookError("Endpoint must use allowlisted HTTPS on port 443")
    target = parts.path or "/"
    if parts.query:
        target += "?" + parts.query
    return host.lower(), target


def _resolve_public(host: str) -> str:
    """Reject mixed public/private DNS answers and pin the selected address."""
    answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    addresses = sorted({answer[4][0] for answer in answers})
    if not addresses:
        raise WebhookError("Endpoint has no addresses")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        mapped = getattr(ip, "ipv4_mapped", None)
        if (
            not ip.is_global
            or ip.is_multicast
            or ip.is_reserved
            or getattr(ip, "is_site_local", False)
            or (mapped is not None and not mapped.is_global)
        ):
            raise WebhookError("Endpoint DNS includes a prohibited address")
    return addresses[0]


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, timeout: float) -> None:
        super().__init__(host, port=443, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self) -> None:
        # Connect to vetted IP, while validating TLS against the original hostname.
        raw_socket = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(
                raw_socket, server_hostname=self.host
            )
        except Exception:
            raw_socket.close()
            raise


def _post_https(
    url: str,
    body: bytes,
    headers: Mapping[str, str],
    allowed_hosts: frozenset[str],
    timeout: float,
) -> int:
    host, target = _validated_url(url, allowed_hosts)
    address = _resolve_public(host)
    connection = _PinnedHTTPSConnection(host, address, timeout)
    try:
        connection.request("POST", target, body=body, headers=dict(headers))
        response = connection.getresponse()
        # Do not follow redirects, consume unbounded bodies, or log response data.
        if len(response.read(MAX_RESPONSE_BYTES + 1)) > MAX_RESPONSE_BYTES:
            raise DeliveryError("Endpoint response exceeded size limit")
        return response.status
    finally:
        connection.close()


class WebhookDispatcher:
    def __init__(
        self, allowed_hosts: set[str] | frozenset[str], *, timeout_seconds: float = 10
    ) -> None:
        if not allowed_hosts or not 0 < timeout_seconds <= 60:
            raise WebhookError("Allowlist required; timeout must be in (0, 60]")
        self.allowed_hosts = frozenset(host.lower() for host in allowed_hosts)
        self.timeout_seconds = timeout_seconds

    def prepare(
        self, event: WebhookEvent, endpoint: Endpoint, *, now: int | None = None
    ) -> tuple[bytes, dict[str, str]]:
        _validated_url(endpoint.url, self.allowed_hosts)
        payload = format_payload(event, endpoint)
        body = _canonical_json(payload)
        if len(body) > MAX_PAYLOAD_BYTES:
            raise WebhookError("Payload exceeds size limit")
        timestamp = str(int(time.time()) if now is None else now)
        key = payload["idempotency_key"]
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SurplusDocket-Webhooks/1.0",
            "Idempotency-Key": key,
            "X-SurplusDocket-Timestamp": timestamp,
            "X-SurplusDocket-Signature": sign_payload(
                endpoint.secret, timestamp, key, body
            ),
        }
        if endpoint.bearer_token is not None:
            headers["Authorization"] = f"Bearer {endpoint.bearer_token}"
        return body, headers

    def dispatch(
        self, event: WebhookEvent, endpoint: Endpoint, *, now: int | None = None
    ) -> DeliveryResult:
        body, headers = self.prepare(event, endpoint, now=now)
        try:
            status = _post_https(
                endpoint.url, body, headers,
                self.allowed_hosts, self.timeout_seconds,
            )
        except (OSError, http.client.HTTPException) as exc:
            # Do not include URL, payload, secrets, or remote response in errors.
            raise DeliveryError("Webhook transport failed") from exc

        return DeliveryResult(
            endpoint.endpoint_id,
            event.event_id,
            headers["Idempotency-Key"],
            status,
            200 <= status < 300,
            status in {408, 425, 429} or 500 <= status < 600,
        )
