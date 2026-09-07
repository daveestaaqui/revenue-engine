"""Validated, formula-hardened surplus-lead CSV intake exports.

Python: 3.11+
Dependencies: standard library only.

These are versioned, mapping-ready INTAKE schemas, not claims of universal
vendor-native import compatibility. Both combine contact and matter/project
data. Depending on the tenant, importers must split contact and matter/project
creation and resolve their relationship using SD Lead ID.

Before deployment:
- Map these headers against the tenant's current import template.
- Configure destination custom fields for the SD-prefixed columns.
- Sandbox-test contact matching, project/matter creation, and duplicate handling.
- Do not map Gross Surplus USD to a trust balance, invoice, or awarded amount.
- Disable automated outreach or matter opening based solely on these exports.

Required normalized input fields:
    lead_id: non-empty string; unique within an export
    state: two-letter supported state code
    county: non-empty string
    first_name and last_name, OR company_name: non-empty strings

All other fields are optional. None becomes an empty CSV field.
Strings are not guessed from arbitrary Python objects.

Selected typed fields:
    gross_surplus: Decimal, int, or plain decimal string; never float
    actionability_score: int from 0 through 100
    statutory_deadline: datetime.date or YYYY-MM-DD string
    verified_at: timezone-aware datetime or ISO-8601 datetime string
    verified_status: unverified | verified | stale | rejected
    title_review_status / senior_lien_status:
        pending | clear | flagged | not_applicable

No statute, deadline, verification status, or entitlement is inferred.

Security:
- No filesystem/network access, logging, or persistence.
- All cells are quoted; dangerous spreadsheet prefixes receive an apostrophe.
- Apostrophe hardening changes those cell values. A mapped importer may remove
  exactly one protective apostrophe after parsing, only when passing the value
  directly to a non-spreadsheet destination. Do not reopen stripped data in Excel.
- Output is sensitive data; authorize exports and encrypt storage/transport.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Iterable, Mapping
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlsplit


SCHEMA_VERSION = "surplus-docket-intake/1.0"
SUPPORTED_STATES = frozenset({"FL", "TX", "GA", "NC", "TN", "CA"})
MAX_ROWS = 100_000
MAX_CELL_LENGTH = 32_000

# Printable Unicode is allowed. Tabs/newlines are handled by CSV quoting and
# formula hardening; other ASCII controls are rejected.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MONEY = re.compile(r"\d{1,15}(?:\.\d{1,2})?")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

CONTACT_COLUMNS = (
    ("First Name", "first_name"),
    ("Last Name", "last_name"),
    ("Company", "company_name"),
    ("Email", "email"),
    ("Phone", "phone"),
    ("Address 1", "address_line1"),
    ("Address 2", "address_line2"),
    ("City", "city"),
    ("State", "state"),
    ("Zip", "postal_code"),
    ("Country", "country"),
)

EVIDENCE_COLUMNS = (
    ("SD Export Schema", "schema_version"),
    ("SD Lead ID", "lead_id"),
    ("SD County", "county"),
    ("SD Sale Type", "sale_type"),
    ("SD Court / Record Custodian", "court_name"),
    ("SD Docket Number", "docket_number"),
    ("SD Gross Surplus USD", "gross_surplus"),
    ("SD Source URL", "source_url"),
    ("SD Source Record ID", "source_record_id"),
    ("SD Governing Statute", "governing_statute"),
    ("SD Statutory Deadline", "statutory_deadline"),
    ("SD Deadline Basis", "deadline_basis"),
    ("SD Title Review Status", "title_review_status"),
    ("SD Senior Lien Status", "senior_lien_status"),
    ("SD Verified Status", "verified_status"),
    ("SD Verified At UTC", "verified_at"),
    ("SD Verified By", "verified_by"),
    ("SD Actionability Score", "actionability_score"),
    ("SD Score Model Version", "score_model_version"),
)

CLIO_COLUMNS = CONTACT_COLUMNS + (
    ("Matter Description", "intake_name"),
    ("Matter Reference", "lead_id"),
    ("Practice Area", "practice_area"),
    ("Responsible Attorney", "assigned_attorney"),
) + EVIDENCE_COLUMNS

FILEVINE_COLUMNS = CONTACT_COLUMNS + (
    ("Project Name", "intake_name"),
    ("Project Type", "project_type"),
    ("Project Reference", "lead_id"),
    ("Assigned Attorney", "assigned_attorney"),
) + EVIDENCE_COLUMNS

_TEXT_FIELDS = (
    "lead_id", "state", "county", "first_name", "last_name", "company_name",
    "email", "phone", "address_line1", "address_line2", "city", "postal_code",
    "country", "sale_type", "court_name", "docket_number", "source_url",
    "source_record_id", "governing_statute", "deadline_basis", "verified_by",
    "score_model_version", "practice_area", "project_type", "assigned_attorney",
)


class ExportValidationError(ValueError):
    """Invalid normalized input. Messages intentionally omit lead/PII values."""


def _text(value: Any, field: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ExportValidationError(f"{field}: expected a string")
    if len(value) > MAX_CELL_LENGTH:
        raise ExportValidationError(f"{field}: exceeds cell length limit")
    if _CONTROL_CHARS.search(value):
        raise ExportValidationError(f"{field}: contains prohibited control characters")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ExportValidationError(f"{field}: invalid Unicode") from None
    return value.strip()


def _choice(
    lead: Mapping[str, Any],
    field: str,
    choices: frozenset[str],
    default: str,
) -> str:
    value = _text(lead.get(field), field).lower() or default
    if value not in choices:
        raise ExportValidationError(f"{field}: unsupported status")
    return value


def _money(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ExportValidationError(
            "gross_surplus: use Decimal, integer, or decimal string; floats prohibited"
        )
    raw = str(value).strip()
    if len(raw) > 18 or not _MONEY.fullmatch(raw):
        raise ExportValidationError(
            "gross_surplus: expected nonnegative USD with at most two decimal places"
        )
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        raise ExportValidationError("gross_surplus: invalid decimal") from None
    return format(amount, ".2f")


def _deadline(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        raise ExportValidationError("statutory_deadline: use a date, not datetime")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and _DATE.fullmatch(value):
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError:
            pass
    raise ExportValidationError("statutory_deadline: expected a valid YYYY-MM-DD date")


def _timestamp(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            raise ValueError
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, OverflowError):
        raise ExportValidationError(
            "verified_at: expected a timezone-aware ISO-8601 datetime"
        ) from None


def _score(value: Any) -> str:
    if value is None or value == "":
        return ""
    if type(value) is not int or not 0 <= value <= 100:
        raise ExportValidationError("actionability_score: expected integer 0–100")
    return str(value)


def _validate_source_url(value: str) -> None:
    if not value:
        return
    try:
        parsed = urlsplit(value)
        # Accessing .port also validates malformed/out-of-range ports.
        _ = parsed.port
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or "\\" in value
            or any(character.isspace() for character in value)
        ):
            raise ValueError
    except ValueError:
        raise ExportValidationError(
            "source_url: expected an absolute HTTP(S) URL without credentials"
        ) from None
    # Syntax validation only. This does not verify provenance or authorize
    # fetching the URL. Any future fetcher needs independent SSRF protections.


def _normalize(lead: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(lead, Mapping):
        raise ExportValidationError("expected a mapping")

    row = {field: _text(lead.get(field), field) for field in _TEXT_FIELDS}
    for field in ("lead_id", "state", "county"):
        if not row[field]:
            raise ExportValidationError(f"{field}: required")

    row["state"] = row["state"].upper()
    if row["state"] not in SUPPORTED_STATES:
        raise ExportValidationError("state: unsupported state code")

    if not row["company_name"] and not (row["first_name"] and row["last_name"]):
        raise ExportValidationError(
            "contact: provide first_name and last_name, or company_name"
        )

    _validate_source_url(row["source_url"])
    row["gross_surplus"] = _money(lead.get("gross_surplus"))
    row["statutory_deadline"] = _deadline(lead.get("statutory_deadline"))
    row["verified_at"] = _timestamp(lead.get("verified_at"))
    row["actionability_score"] = _score(lead.get("actionability_score"))
    row["verified_status"] = _choice(
        lead,
        "verified_status",
        frozenset({"unverified", "verified", "stale", "rejected"}),
        "unverified",
    )
    for field in ("title_review_status", "senior_lien_status"):
        row[field] = _choice(
            lead,
            field,
            frozenset({"pending", "clear", "flagged", "not_applicable"}),
            "pending",
        )

    if row["statutory_deadline"] and not (
        row["governing_statute"] and row["deadline_basis"]
    ):
        raise ExportValidationError(
            "statutory_deadline: requires governing_statute and deadline_basis"
        )

    if row["actionability_score"] and not row["score_model_version"]:
        raise ExportValidationError(
            "actionability_score: requires score_model_version"
        )

    # These are minimum metadata requirements, not independent verification.
    # Some official surplus records have no court docket; source_record_id
    # remains required, while docket_number remains optional.
    if row["verified_status"] == "verified":
        required = (
            "source_url", "source_record_id", "court_name",
            "verified_at", "verified_by", "governing_statute", "sale_type",
        )
        for field in required:
            if not row[field]:
                raise ExportValidationError(
                    f"verified_status: verified requires {field}"
                )
        if not row["gross_surplus"]:
            raise ExportValidationError(
                "verified_status: verified requires gross_surplus"
            )

    row["schema_version"] = SCHEMA_VERSION

    # Avoid exposing claimant names in generated matter/project titles.
    row["intake_name"] = _text(
        f"Surplus review | {row['state']} | {row['county']} | {row['lead_id']}",
        "intake_name",
    )
    return row


def _spreadsheet_safe(value: str) -> str:
    """Harden formula-like cells, including formulas behind whitespace/BOM."""
    probe = value.lstrip()
    while probe.startswith("\ufeff"):
        probe = probe[1:].lstrip()
    if probe.startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def _export(
    leads: Iterable[Mapping[str, Any]],
    columns: tuple[tuple[str, str], ...],
) -> str:
    if isinstance(leads, (str, bytes, Mapping)):
        raise ExportValidationError("leads: expected an iterable of mappings")
    try:
        iterator = iter(leads)
    except TypeError:
        raise ExportValidationError("leads: expected an iterable of mappings") from None

    seen: set[str] = set()

    # No partial CSV is returned if any row fails validation.
    with io.StringIO(newline="") as buffer:
        writer = csv.writer(
            buffer,
            delimiter=",",
            quotechar='"',
            quoting=csv.QUOTE_ALL,
            lineterminator="\r\n",
        )
        writer.writerow(header for header, _ in columns)

        for index, lead in enumerate(iterator, start=1):
            if index > MAX_ROWS:
                raise ExportValidationError("leads: row limit exceeded")
            try:
                row = _normalize(lead)
                if row["lead_id"] in seen:
                    raise ExportValidationError("lead_id: duplicate within export")
                seen.add(row["lead_id"])
                writer.writerow(
                    _spreadsheet_safe(row[field]) for _, field in columns
                )
            except ExportValidationError as exc:
                raise ExportValidationError(f"row {index}: {exc}") from None

        return buffer.getvalue()


def export_to_clio_csv(leads: Iterable[Mapping[str, Any]]) -> str:
    """Return Clio-oriented contact/matter intake CSV as Unicode text.

    Preserves input order. Empty input returns the header row.
    Does not assign Clio-internal IDs or automatically create/open matters.
    """
    return _export(leads, CLIO_COLUMNS)


def export_to_filevine_csv(leads: Iterable[Mapping[str, Any]]) -> str:
    """Return Filevine-oriented contact/project intake CSV as Unicode text.

    Project Type must match a configured destination project template.
    No Filevine API field selectors or internal IDs are inferred.
    """
    return _export(leads, FILEVINE_COLUMNS)
