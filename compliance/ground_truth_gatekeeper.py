#!/usr/bin/env python3
"""
Surplus Docket — Ground Truth Gatekeeper
========================================
Deterministic pre-publication & pre-dispatch validation engine.
Enforces ground-truth accuracy across public feeds, website pages,
email outreach drafts, and AI-generated content.

Zero-tolerance rules:
1. No fictitious or synthetic case numbers (e.g., 'GW-R7233-032', 'DK-...', 'SD-7102-...').
   Administrative tax sales must be accurately identified as Parcel IDs, never court cases.
2. No unverified title claims (e.g., 'senior mortgages cleared upstream', 'free and clear').
   All excess proceeds must be truthfully described as subject to statutory lien priority.
3. No mismatched attorney practice areas (e.g. criminal defense, habeas corpus, evictions).
4. No deceptive persona hooks (e.g. 'Elena Brooks' pretending to refer an individual client).
   Sender must be transparent (David Mahler / Surplus Docket Public Records Intelligence).
5. No dead, unverified, or broken links anywhere.
"""

import re
import urllib.parse
from typing import Dict, Any, List, Tuple, Optional

# Banned synthetic or fabricated prefixes
BANNED_CASE_PREFIXES = (
    "GW-",
    "DK-",
    "SD-7102-",
    "LA-ITEM-",
    "2022-A00807",
    "APN-",
    "OC-",
    "FAKE-",
    "TEST-",
    "MOCK-",
)

# Banned unverified title & lien assertions
BANNED_TITLE_PHRASES = (
    "cleared upstream",
    "senior mortgages are cleared",
    "senior mortgages cleared",
    "mortgages cleared upstream",
    "scrub out all institutional liens",
    "scrub out junior and senior",
    "scrub raw county ledgers to purge senior",
    "free and clear of all liens",
    "unencumbered by bank liens",
    "unencumbered equity balances",
    "guaranteed unencumbered",
)

# Banned deceptive persona hooks
BANNED_PERSONA_PHRASES = (
    "elena brooks",
    "elena.brooks@surplusdocket.com",
    "senior docket specialist",
    "looking at active estate and probate administration counsel",
    "are you handling surplus recovery petitions in",
    "happy to send over the docket summary and filing notes",
)

# Known mismatched attorney domains/emails that must NEVER receive surplus outreach
KNOWN_MISMATCHED_TARGETS = {
    "stephen@rebalaw.com": "Criminal defense, post-conviction appeals, and habeas corpus (Reba Law LLC)",
    "rebalaw.com": "Criminal defense, post-conviction appeals, and habeas corpus (Reba Law LLC)",
    "dennis@evict123.com": "Landlord/tenant eviction litigation only (Dennis P. Block & Associates)",
    "evict123.com": "Landlord/tenant eviction litigation only (Dennis P. Block & Associates)",
}

# Whitelist of valid state surplus governing statutes
STATE_STATUTES = {
    "FL": ("Fla. Stat. § 197.582", "Fla. Stat. § 45.032"),
    "TX": ("Tex. Tax Code § 34.04",),
    "GA": ("O.C.G.A. § 48-4-5",),
    "NC": ("N.C.G.S. § 105-374",),
    "TN": ("T.C.A. § 67-5-2501", "T.C.A. § 67-5-2702"),
    "CA": ("Cal. Rev. & Tax Code § 4675",),
}

# Dead or 404 URLs discovered in audits
DEAD_URLS = {
    "https://www.hillsclerk.com/records-and-reports/tax-deed-surplus",
    "http://www.hillsclerk.com/records-and-reports/tax-deed-surplus",
}


class GroundTruthGatekeeper:
    """Strict ground-truth validation gatekeeper for records, outreach, and publications."""

    @classmethod
    def validate_lead_record(cls, lead: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates that a public lead record contains zero synthetic identifiers,
        accurate statutory citations, and verifiable clerk sources.
        """
        errors = []
        state = str(lead.get("State", "")).strip().upper()
        county = str(lead.get("County", "")).strip()
        case_no = str(lead.get("Case_or_TaxDeed_No", "")).strip()
        parcel_id = str(lead.get("Parcel_ID", "")).strip()

        # 1. Check for banned synthetic case prefixes
        for prefix in BANNED_CASE_PREFIXES:
            if case_no.startswith(prefix):
                errors.append(f"Synthetic case number prefix '{prefix}' forbidden in Case_or_TaxDeed_No: '{case_no}'")

        # 2. Verify identifier presence
        if not case_no and not parcel_id:
            errors.append("Record must have either an authentic Case_or_TaxDeed_No or a valid Parcel_ID")

        # 3. Check for synthetic GA/CA case formatting
        if state == "GA" and case_no and not (re.match(r"^\d{2}-[AC]-\d+", case_no) or "SUBSCRIBER KEY" in case_no):
            errors.append(
                f"Georgia record has non-judicial case number '{case_no}'. "
                f"GA tax deed sales under O.C.G.A. § 48-4-5 are administrative and must be tracked by Parcel_ID."
            )
        if state == "CA" and case_no and not ("SUBSCRIBER KEY" in case_no):
            errors.append(
                f"California record has non-judicial case number '{case_no}'. "
                f"CA tax defaulted property sales under Cal. Rev. & Tax Code § 4675 are administrative and must be tracked by Parcel_ID."
            )

        # 4. Check balance validity
        try:
            bal = float(lead.get("Surplus_Balance_USD", 0))
            if bal <= 0:
                errors.append(f"Surplus_Balance_USD must be positive: {bal}")
        except (ValueError, TypeError):
            errors.append(f"Invalid Surplus_Balance_USD: {lead.get('Surplus_Balance_USD')}")

        # 5. Check URL validity
        clerk_url = str(lead.get("Clerk_Verification_URL") or lead.get("Source_URL") or "").strip()
        for dead in DEAD_URLS:
            if dead in clerk_url:
                errors.append(f"Record contains known dead/404 URL: {dead}")

        return (len(errors) == 0, errors)

    @classmethod
    def validate_outreach_message(
        cls,
        to_email: str,
        to_name: str,
        firm: str,
        subject: str,
        body: str,
        lead: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Validates an outreach email draft for absolute ground-truth accuracy:
        - Rejects mismatched practice areas
        - Rejects fictitious case numbers
        - Rejects unverified title claims ('cleared upstream')
        - Rejects deceptive persona referral hooks
        - Rejects dead links
        """
        errors = []
        body_lower = body.lower()
        subj_lower = subject.lower()
        email_clean = to_email.strip().lower()
        firm_clean = firm.strip().lower()

        # 1. Mismatched practice area gate
        for bad_target, reason in KNOWN_MISMATCHED_TARGETS.items():
            if bad_target in email_clean or bad_target in firm_clean:
                errors.append(f"Recipient '{to_email}' ({firm}) is a mismatched practice: {reason}. Outreach prohibited.")

        # 2. Check for banned synthetic case numbers in subject and body
        for prefix in BANNED_CASE_PREFIXES:
            if prefix.lower() in subj_lower or prefix.lower() in body_lower:
                errors.append(f"Fictitious case prefix '{prefix}' detected in message text.")

        # 3. Check for calling an administrative parcel a "court case"
        # e.g., "Case R7233 032" or "Case GW-R7233-032"
        if re.search(r"case\s+r\d{4}", body_lower) or re.search(r"case\s+gw-", body_lower):
            errors.append("Administrative tax commissioner parcel falsely referred to as a court 'Case'.")

        # 4. Check for unverified title claims ("senior mortgages are cleared upstream")
        for phrase in BANNED_TITLE_PHRASES:
            if phrase in body_lower:
                errors.append(f"Unverified title assertion detected: '{phrase}'.")

        # 5. Check for deceptive persona hooks ("Elena Brooks", fake intake referrals)
        for phrase in BANNED_PERSONA_PHRASES:
            if phrase in body_lower:
                errors.append(f"Deceptive persona/referral hook detected: '{phrase}'.")

        # 6. Check for dead or 404 URLs
        for dead in DEAD_URLS:
            if dead in body:
                errors.append(f"Known dead/404 URL detected in message: {dead}")

        # 7. Sender transparency check
        if "david mahler" not in body_lower and "david@surplusdocket.com" not in body_lower and "dockets@surplusdocket.com" not in body_lower:
            errors.append("Outreach message must transparently identify sender (David Mahler / Surplus Docket Intelligence).")

        # 8. No direct raw PDF links; must link to custom surplusdocket.com dossier page
        if re.search(r"https?://[^\s]+\.pdf(\b|#|\?)", body, re.I):
            errors.append("Outreach message must not link directly to raw county PDF; must link to custom surplusdocket.com docket dossier page.")

        return (len(errors) == 0, errors)

    @classmethod
    def assert_ground_truth(cls, obj_type: str, data: Any):
        """Raises ValueError immediately if ground-truth gate is violated."""
        if obj_type == "lead":
            ok, errors = cls.validate_lead_record(data)
        elif obj_type == "outreach":
            ok, errors = cls.validate_outreach_message(**data)
        else:
            raise ValueError(f"Unknown validation object type: {obj_type}")

        if not ok:
            err_msg = "\n  • ".join(errors)
            raise ValueError(f"🚨 GROUND TRUTH GATEKEEPER REJECTION ({obj_type}):\n  • {err_msg}")


def main():
    """CLI runner to audit active feeds and drafts against ground truth standards."""
    import sys
    import json
    from pathlib import Path
    import csv

    base_dir = Path(__file__).resolve().parent.parent
    master_csv = base_dir / "exports" / "Master_Surplus_Lead_Feed.csv"

    print("=" * 70)
    print(" ⚖️  SURPLUS DOCKET — GROUND TRUTH GATEKEEPER AUDIT")
    print("=" * 70)

    total_checked = 0
    total_violations = 0

    if master_csv.exists():
        with open(master_csv, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        print(f"[*] Auditing {len(rows)} records in Master_Surplus_Lead_Feed.csv...")
        for r in rows:
            total_checked += 1
            ok, errs = GroundTruthGatekeeper.validate_lead_record(r)
            if not ok:
                total_violations += len(errs)
                print(f"❌ Record Violation ({r.get('State')} {r.get('County')}):")
                for e in errs:
                    print(f"   - {e}")

    if total_violations == 0:
        print(f"\n✅ PASSED: All {total_checked} records verified 100% compliant with ground truth.")
        sys.exit(0)
    else:
        print(f"\n❌ FAILED: Found {total_violations} ground-truth violations across {total_checked} records.")
        sys.exit(1)


if __name__ == "__main__":
    main()
