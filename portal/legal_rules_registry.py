"""Versioned, immutable reference registry for TAX-SALE surplus proceedings.

Not applicable to mortgage foreclosure, bankruptcy, redemption deadlines, or
case-specific court orders.

LEGAL VALIDATION REQUIRED BEFORE LIVE USE:
The cited statutes have not been independently checked for current amendments.
Registry version identifies this software's data revision, not a legal effective
date. is_valid means computationally supported under the listed assumptions;
it is not certification of legal timeliness, entitlement, or legal advice.

Dates are local civil dates. No weekend/holiday extension, tolling, service
extension, or equitable exception is inferred. Deadline dates are conservative
calendar calculations and must be reviewed by counsel.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from types import MappingProxyType
from typing import Literal

REGISTRY_VERSION = "surplus-tax-rules/1.0.0"
INSUFFICIENT_FACTS = "Insufficient facts to calculate — attorney review required"
REVIEW_WARNING = (
    "Reference rule requires current-law and attorney validation. "
    "Calendar calculation only; no holiday/weekend, tolling, or court-order "
    "adjustments applied. Not a redemption or mortgage-foreclosure deadline."
)

DeadlineResult = tuple[date | None, str, str, bool, str]
Trigger = Literal[
    "notice_mailed_date",
    "sale_date",
    "deed_recordation_date",
    "case_specific",
]


@dataclass(frozen=True, slots=True)
class LegalRule:
    state: str
    proceeding_type: str
    citation: str
    trigger: Trigger
    calculation: str
    scope: str
    required_facts: tuple[str, ...]
    version: str = REGISTRY_VERSION
    review_status: str = "attorney_validation_required"
    verified_through: date | None = None


_RULES = (
    LegalRule(
        "FL",
        "tax_deed",
        "Fla. Stat. § 197.582",
        "notice_mailed_date",
        "120 calendar days after mailing of the statutory surplus notice",
        (
            "Statutory tax-deed surplus notice/claim procedure. notice_date must "
            "be the notice mailing date, not receipt or an unrelated notice. "
            "Claimant status and entitlement require separate review; this is "
            "not a universal extinguishment date for every interest."
        ),
        ("notice_date",),
    ),
    LegalRule(
        "TX",
        "tax_foreclosure",
        "Tex. Tax Code § 34.04",
        "sale_date",
        (
            "Petition must be filed before the second anniversary of sale; "
            "return the preceding calendar date"
        ),
        (
            "Excess-proceeds petition in the court that ordered the tax seizure "
            "or sale. The statutory word 'before' is treated as exclusive."
        ),
        ("sale_date",),
    ),
    LegalRule(
        "GA",
        "tax_sale",
        "O.C.G.A. § 48-4-5",
        "case_specific",
        "No universal claimant filing deadline encoded",
        (
            "Distribution priorities and possible interpleader require "
            "claimant and procedural facts; an administrative holding or "
            "interpleader interval is not automatically a claimant deadline."
        ),
        ("claimant_status", "procedural_posture", "court_orders"),
    ),
    LegalRule(
        "CA",
        "tax_defaulted_sale",
        "Cal. Rev. & Tax. Code § 4675",
        "deed_recordation_date",
        "One-year claim period following recordation of the tax collector's deed",
        (
            "Deed recordation, not sale, notice, or sale confirmation, is the "
            "relevant trigger. Exact cutoff and applicable exceptions require "
            "review of current law."
        ),
        ("deed_recordation_date",),
    ),
    LegalRule(
        "NC",
        "tax_foreclosure",
        "N.C. Gen. Stat. § 105-374",
        "case_specific",
        "No universal surplus-claim filing deadline encoded",
        (
            "Judicial tax-foreclosure distribution is case-specific. "
            "Sale-confirmation and upset-bid periods must not be substituted "
            "for a surplus-claim deadline."
        ),
        ("claimant_status", "procedural_posture", "court_orders"),
    ),
    LegalRule(
        "TN",
        "delinquent_tax_sale",
        "Tenn. Code Ann. § 67-5-2501",
        "case_specific",
        "No universal surplus-claim filing deadline encoded",
        (
            "The cited tax-sale provision alone is not a sufficient basis for "
            "a universal excess-proceeds deadline. Review related provisions "
            "and controlling court orders; do not substitute redemption periods."
        ),
        ("claimant_status", "procedural_posture", "court_orders"),
    ),
)

RULES = MappingProxyType(
    {(rule.state, rule.proceeding_type): rule for rule in _RULES}
)
DEFAULT_PROCEEDINGS = MappingProxyType(
    {rule.state: rule.proceeding_type for rule in _RULES}
)


def get_rule(state: str, proceeding_type: str) -> LegalRule:
    """Return a reference rule. Reject unsupported proceedings explicitly."""
    if not isinstance(state, str) or not isinstance(proceeding_type, str):
        raise ValueError("State and proceeding_type must be strings")
    key = (state.strip().upper(), proceeding_type.strip().lower())
    try:
        return RULES[key]
    except KeyError:
        raise ValueError(f"Unsupported state/proceeding: {key!r}") from None


def _add_calendar_years(value: date, years: int) -> date:
    year = value.year + years
    last_day = calendar.monthrange(year, value.month)[1]
    return date(year, value.month, min(value.day, last_day))


def calculate_statutory_deadline(
    state: str,
    sale_date: date | None,
    notice_date: date | None,
    confirmation_date: date | None,
) -> DeadlineResult:
    """Return (deadline_date, governing_statute, basis, is_valid, warning).

    Because proceeding_type is absent from this requested interface, the
    state's DEFAULT_PROCEEDINGS entry is assumed and disclosed in the warning.

    confirmation_date is never silently treated as deed recordation or notice.
    CA intentionally returns insufficient facts because the signature has no
    deed_recordation_date parameter.
    """
    if not isinstance(state, str):
        return None, "", "Unsupported state", False, "State must be a string"

    state = state.strip().upper()
    if state not in DEFAULT_PROCEEDINGS:
        return None, "", "Unsupported state", False, "Attorney review required"

    rule = get_rule(state, DEFAULT_PROCEEDINGS[state])
    warning = (
        f"Assumed proceeding: {rule.proceeding_type}. "
        f"Registry: {rule.version}. {REVIEW_WARNING}"
    )
    supplied = {
        "sale_date": sale_date,
        "notice_date": notice_date,
        "confirmation_date": confirmation_date,
    }

    for field, value in supplied.items():
        if value is not None and (
            not isinstance(value, date) or isinstance(value, datetime)
        ):
            return (
                None,
                rule.citation,
                f"Invalid {field}: supply datetime.date, not datetime/string",
                False,
                warning,
            )

    if (
        sale_date is not None
        and confirmation_date is not None
        and confirmation_date < sale_date
    ):
        return (
            None, rule.citation, "Confirmation precedes sale", False, warning
        )

    if rule.trigger == "notice_mailed_date":
        if notice_date is None:
            return (
                None, rule.citation, INSUFFICIENT_FACTS, False,
                f"{warning} Missing statutory surplus notice mailing date.",
            )
        if sale_date is not None and notice_date < sale_date:
            return (
                None, rule.citation, "Surplus notice precedes sale", False, warning
            )
        try:
            deadline = notice_date + timedelta(days=120)
        except OverflowError:
            return None, rule.citation, "Date outside supported range", False, warning
        return (
            deadline, rule.citation, rule.calculation, True,
            f"{warning} {rule.scope}",
        )

    if rule.trigger == "sale_date":
        if sale_date is None:
            return (
                None, rule.citation, INSUFFICIENT_FACTS, False,
                f"{warning} Missing tax-sale date.",
            )
        try:
            anniversary = _add_calendar_years(sale_date, 2)
            deadline = anniversary - timedelta(days=1)
        except (ValueError, OverflowError):
            return None, rule.citation, "Date outside supported range", False, warning

        leap_warning = (
            " Feb. 29 anniversary was clamped to the last day of February; "
            "counsel must confirm the governing time-computation rule."
            if sale_date.month == 2 and sale_date.day == 29
            else ""
        )
        return (
            deadline, rule.citation, rule.calculation, True,
            f"{warning} {rule.scope}{leap_warning}",
        )

    if rule.trigger == "deed_recordation_date":
        return (
            None, rule.citation, INSUFFICIENT_FACTS, False,
            f"{warning} Missing deed_recordation_date, which this interface "
            "cannot accept. Do not substitute confirmation_date.",
        )

    return (
        None, rule.citation, INSUFFICIENT_FACTS, False,
        f"{warning} {rule.scope} Required review facts: "
        + ", ".join(rule.required_facts),
    )
