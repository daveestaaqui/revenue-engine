#!/usr/bin/env python3
"""
Surplus Docket — Preliminary Lien Screening & Evidence Graph Engine
====================================================================
Builds chronological evidence graphs and preliminary priority classifications
for surplus opportunities, strictly separating:
1. Public record source observations (book, page, instrument, date).
2. Extracted legal facts.
3. Preliminary priority classification under state statutes.
4. Attorney review questions & potential encumbrance flags.

Statutory Frameworks:
- Florida: Fla. Stat. § 197.582 (Governmental -> Recorded Lienholders -> Titleholder)
- Texas: Tex. Tax Code § 34.04 (Taxing Units -> Lienholders in Priority -> Owner)
- California: Cal. Rev. & Tax Code § 4675 (Lienholders in Priority -> Titleholder)
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional, Any


MANDATORY_TITLE_DISCLAIMER = (
    "PRELIMINARY PUBLIC RECORDS SCREENING ONLY: This analysis is an automated index of recorded instruments "
    "from county court registries and does NOT constitute title insurance, a title guaranty, or a formal legal "
    "opinion of title priority. All priority determinations must be independently verified by licensed counsel."
)


@dataclass
class RecordedInstrument:
    instrument_id: str
    document_type: str  # MORTGAGE, HOA_LIEN, TAX_DEED, JUDGMENT, SATISFACTION, CODE_ENFORCEMENT
    recording_date: str  # YYYY-MM-DD
    grantor: str
    grantee: str
    principal_amount_usd: float
    book_page: Optional[str] = None
    instrument_number: Optional[str] = None
    source_registry_url: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class LienScreenResult:
    docket_number: str
    jurisdiction: str
    county: str
    property_address: str
    surplus_balance_usd: float
    owner_of_record: str
    instruments_examined: List[RecordedInstrument] = field(default_factory=list)
    active_encumbrances: List[Dict[str, Any]] = field(default_factory=list)
    satisfied_encumbrances: List[Dict[str, Any]] = field(default_factory=list)
    preliminary_distribution_tier: str = "TITLEHOLDER_EQUITY"
    attorney_review_questions: List[str] = field(default_factory=list)
    statutory_governing_law: str = ""
    disclaimer: str = MANDATORY_TITLE_DISCLAIMER

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_preliminary_lien_screen(
    docket_number: str,
    jurisdiction: str,
    county: str,
    property_address: str,
    surplus_balance_usd: float,
    owner_of_record: str,
    recorded_instruments: List[RecordedInstrument]
) -> LienScreenResult:
    """
    Constructs an evidence graph from recorded instruments and resolves priority.
    """
    jur = jurisdiction.strip().upper()
    statute_map = {
        "FL": "Fla. Stat. § 197.582",
        "TX": "Tex. Tax Code § 34.04",
        "GA": "O.C.G.A. § 48-4-5",
        "NC": "N.C.G.S. § 105-374",
        "TN": "T.C.A. § 67-5-2501",
        "CA": "Cal. Rev. & Tax Code § 4675"
    }
    statute = statute_map.get(jur, "Applicable State Surplus Statute")

    # Sort instruments chronologically
    sorted_instruments = sorted(
        recorded_instruments,
        key=lambda x: x.recording_date or "1900-01-01"
    )

    # Track satisfactions and releases
    satisfied_refs = set()
    for inst in sorted_instruments:
        if inst.document_type.upper() in ["SATISFACTION", "RELEASE", "DISCHARGE"]:
            if inst.notes:
                satisfied_refs.add(inst.notes.upper())
            if inst.instrument_number:
                satisfied_refs.add(inst.instrument_number.upper())
            if inst.book_page:
                satisfied_refs.add(inst.book_page.upper())

    active_liens = []
    satisfied_liens = []
    attorney_questions = []

    for inst in sorted_instruments:
        doc_type = inst.document_type.upper()
        if doc_type in ["SATISFACTION", "RELEASE", "DISCHARGE"]:
            continue

        ref_id = (inst.instrument_number or inst.book_page or inst.instrument_id).upper()
        is_satisfied = (ref_id in satisfied_refs) or any(ref in (inst.notes or "").upper() for ref in satisfied_refs)

        lien_summary = {
            "instrument_id": inst.instrument_id,
            "document_type": inst.document_type,
            "recording_date": inst.recording_date,
            "grantor": inst.grantor,
            "grantee": inst.grantee,
            "amount_usd": inst.principal_amount_usd,
            "source_registry_url": inst.source_registry_url
        }

        if is_satisfied:
            satisfied_liens.append(lien_summary)
        else:
            active_liens.append(lien_summary)

    # Analyze active liens for priority & review questions
    total_active_lien_claims = sum(l["amount_usd"] for l in active_liens)

    # Identify institutional mortgage claimants
    senior_mortgages = [l for l in active_liens if "MORTGAGE" in l["document_type"].upper()]
    hoa_liens = [l for l in active_liens if "HOA" in l["document_type"].upper() or "ASSESSMENT" in l["document_type"].upper()]
    tax_liens = [l for l in active_liens if "TAX" in l["document_type"].upper()]
    judgments = [l for l in active_liens if "JUDGMENT" in l["document_type"].upper()]

    if senior_mortgages:
        attorney_questions.append(
            f"Active recorded mortgage(s) totaling ${sum(m['amount_usd'] for m in senior_mortgages):,.2f}. "
            "Counsel should examine whether surplus notice was properly served on lender and if mortgage survived or was extinguished."
        )
    if hoa_liens:
        attorney_questions.append(
            f"Active HOA/COA assessment lien(s) totaling ${sum(h['amount_usd'] for h in hoa_liens):,.2f}. "
            "Verify whether association has filed a timely verified statement of claim in county registry."
        )
    if judgments:
        attorney_questions.append(
            f"Active judgment lien(s) indexed against '{owner_of_record}'. "
            "Verify debtor identity to eliminate false-positive common-name matches."
        )

    # Check for probate/estate issues
    if any(k in owner_of_record.upper() for k in ["ESTATE", "DECEDENT", "HEIRS", "ET AL"]):
        attorney_questions.append(
            "Claimant is an Estate or Heirs. Petition requires verified Letters of Administration, "
            "Order of Summary Administration, or determination of heirs prior to fund distribution."
        )

    # Determine preliminary distribution tier
    if not active_liens:
        tier = "CLEAN_OWNER_SURPLUS"
    elif total_active_lien_claims < surplus_balance_usd:
        tier = "SUBSTANTIAL_EQUITY_AFTER_LIENS"
    else:
        tier = "COMPETING_LIENHOLDER_DISPUTE"

    return LienScreenResult(
        docket_number=docket_number,
        jurisdiction=jur,
        county=county,
        property_address=property_address,
        surplus_balance_usd=surplus_balance_usd,
        owner_of_record=owner_of_record,
        instruments_examined=sorted_instruments,
        active_encumbrances=active_liens,
        satisfied_encumbrances=satisfied_liens,
        preliminary_distribution_tier=tier,
        attorney_review_questions=attorney_questions,
        statutory_governing_law=statute
    )
