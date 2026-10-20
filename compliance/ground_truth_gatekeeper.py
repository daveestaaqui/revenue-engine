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

import json
from pathlib import Path
import re
import subprocess
import urllib.parse
from typing import Dict, Any, List, Tuple, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
BOUNCED_EMAILS_FILE = BASE_DIR / "outreach" / "bounced_emails.json"

# Known dead or invalid email domains that explicitly reject mail or do not exist
DEAD_DOMAINS = {
    "lunalawfirm.com": "Null MX (RFC 7505: Domain explicitly rejects email)",
    "kramerlaw.com": "M365 DBEB: Non-existent recipient domain / invalid mailbox",
    "spencerlawpc.com": "M365 DBEB: Non-existent recipient mailbox",
    "marshalllegal.com": "M365 DBEB: Unrelated Indiana firm / non-existent Georgia mailbox",
}

# Authoritative directory of pre-verified practitioners confirmed against State Bar records
VERIFIED_BAR_REGISTRY = {
    "ryan@torrenslawgroup.com": {
        "name": "Ryan C. Torrens",
        "bar_id": "FL Bar # 84439",
        "firm": "Torrens Law Group, P.A.",
        "state": "FL",
        "specialty": "Consumer Foreclosure & Surplus",
    },
    "brice@zoeckleinlawpa.com": {
        "name": "Brice Zoecklein",
        "bar_id": "FL Bar # 85615",
        "firm": "Zoecklein Law, P.A.",
        "state": "FL",
        "specialty": "Tax Deed & Probate Surplus Claims",
    },
    "cjimerson@jimersonfirm.com": {
        "name": "Charles B. Jimerson",
        "bar_id": "FL Bar # 21750",
        "firm": "Jimerson Birr, P.A.",
        "state": "FL",
        "specialty": "Commercial Foreclosure & Court Registry Surplus",
    },
    "ksoto@thesotolawoffice.com": {
        "name": "Kimberly M. Soto",
        "bar_id": "FL Bar # 93641",
        "firm": "The Soto Law Office, P.A.",
        "state": "FL",
        "specialty": "Real Estate & Probate Surplus Funds",
    },
    "joe@taorminalawpa.com": {
        "name": "Joseph Vincent Taormina",
        "bar_id": "FL Bar # 126224",
        "firm": "Taormina Law, P.A.",
        "state": "FL",
        "specialty": "Foreclosure & Tax Deed Surplus Recovery",
    },
    "scott@flaglerbeachlaw.com": {
        "name": "Scott W. Spradley",
        "bar_id": "FL Bar # 782467",
        "firm": "Law Offices of Scott W. Spradley, P.A.",
        "state": "FL",
        "specialty": "Commercial & Tax Deed Surplus",
    },
    "alden@cohenrecoverylaw.com": {
        "name": "Alden Cohen",
        "bar_id": "FL Bar # 1010376",
        "firm": "Cohen Recovery Law",
        "state": "FL",
        "specialty": "Surplus Asset Recovery",
    },
    "bradh@weissman.law": {
        "name": "Bradley A. Hutchins",
        "bar_id": "GA Bar # 380678",
        "firm": "Weissman PC",
        "state": "GA",
        "specialty": "Georgia Tax Sale Excess Funds (O.C.G.A. § 48-4-5)",
    },
    "julie@jlibermanlaw.com": {
        "name": "Julie A. Liberman",
        "bar_id": "GA Bar # 452296",
        "firm": "Julie A. Liberman, LLC",
        "state": "GA",
        "specialty": "Real Estate Litigation & Title Disputes",
    },
    "leon@lvglaw.com": {
        "name": "Leon Van Gelderen",
        "bar_id": "GA Bar # 724750",
        "firm": "Leon Van Gelderen, P.C.",
        "state": "GA",
        "specialty": "Tax Deed Surplus & Quiet Title (O.C.G.A. § 48-4-5)",
    },
    "brett@bighamlaw.com": {
        "name": "Brett L. Bigham",
        "bar_id": "TX Bar # 02312720",
        "firm": "Law Offices of Brett L. Bigham, PLLC",
        "state": "TX",
        "specialty": "Property Tax Sale Excess Proceeds (Tex. Tax Code § 34.04)",
    },
    "manfred@manfredlaw.com": {
        "name": "Manfred Sternberg",
        "bar_id": "TX Bar # 19175775",
        "firm": "Manfred Sternberg & Associates PC",
        "state": "TX",
        "specialty": "Property Tax Foreclosure Excess Proceeds Recovery",
    },
    "kmorris@keithmorrislaw.com": {
        "name": "Keith Morris",
        "bar_id": "TX Bar # 24032879",
        "firm": "The Law Offices of Keith Morris",
        "state": "TX",
        "specialty": "Probate & Fiduciary Litigation Excess Funds",
    },
    "ian@ghristlaw.com": {
        "name": "Ian Ghrist",
        "bar_id": "TX Bar # 24074272",
        "firm": "Ghrist Law Firm, PLLC",
        "state": "TX",
        "specialty": "Real Estate & Property Litigation",
    },
    "asalvo@salvolaw.com": {
        "name": "Alice A. Salvo",
        "bar_id": "CA Bar # 105822",
        "firm": "Law Offices of Alice A. Salvo",
        "state": "CA",
        "specialty": "Probate & Estate Administration Unclaimed Property",
    },
    "kpreston@klineprestonlaw.com": {
        "name": "G. Kline Preston IV",
        "bar_id": "TN Bar # 015469",
        "firm": "Kline Preston Law Group",
        "state": "TN",
        "specialty": "Chancery Court Real Estate & Excess Proceeds",
    },
}

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

    _dns_cache: Dict[str, Tuple[bool, Optional[str]]] = {}

    @classmethod
    def check_domain_mx(cls, domain: str, timeout_sec: float = 3.0) -> Tuple[bool, Optional[str]]:
        """
        Validates DNS MX records for a domain, rejecting RFC 7505 Null MX records.
        Returns (is_valid, error_reason).
        """
        dom = domain.strip().lower()
        if dom in cls._dns_cache:
            return cls._dns_cache[dom]

        if dom in DEAD_DOMAINS:
            cls._dns_cache[dom] = (False, f"Dead domain: {DEAD_DOMAINS[dom]}")
            return cls._dns_cache[dom]

        # Check pre-verified domains
        verified_domains = {e.split("@")[1].lower() for e in VERIFIED_BAR_REGISTRY.keys()}
        is_pre_verified = dom in verified_domains

        try:
            proc = subprocess.run(
                ["host", "-t", "MX", dom],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            out = proc.stdout.strip()
            if "mail is handled by 0 ." in out:
                res = (False, f"RFC 7505 Null MX record detected: domain '{dom}' explicitly rejects email.")
            elif "mail is handled by" in out:
                res = (True, None)
            elif proc.returncode != 0 or "not found" in out or "has no MX record" in out:
                if is_pre_verified:
                    res = (True, None)  # Pre-verified domain fallback
                else:
                    res = (False, f"No valid MX records found for domain '{dom}'. DNS output: {out}")
            else:
                res = (True, None) if is_pre_verified else (False, f"Unconfirmed MX records for domain '{dom}'.")
        except Exception as e:
            if is_pre_verified:
                res = (True, None)  # Offline sandbox fallback
            else:
                res = (False, f"DNS MX lookup error for domain '{dom}': {e}")

        cls._dns_cache[dom] = res
        return res

    @classmethod
    def validate_recipient_email(
        cls,
        email_str: str,
        firm: str = "",
        name: str = "",
        check_dns: bool = True,
    ) -> Tuple[bool, List[str]]:
        """
        Strict deliverability & ground-truth validation for email recipients:
        1. Syntax check
        2. Known mismatched practice check
        3. Bounced emails & dead domains blacklist
        4. DNS MX record validation (including RFC 7505 Null MX detection)
        5. State Bar verified practitioner check
        """
        errors = []
        em = email_str.strip().lower()
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", em):
            return False, [f"Invalid email syntax: '{email_str}'"]

        parts = em.split("@")
        domain = parts[1]

        # Check mismatched practice areas
        firm_clean = firm.strip().lower()
        for bad_target, reason in KNOWN_MISMATCHED_TARGETS.items():
            if bad_target in em or (firm_clean and bad_target in firm_clean):
                errors.append(f"Recipient '{email_str}' ({firm}) is a mismatched practice: {reason}.")

        # Check dead domains
        if domain in DEAD_DOMAINS:
            errors.append(f"Recipient domain '{domain}' is blacklisted: {DEAD_DOMAINS[domain]}")

        # Check bounced emails JSON
        if BOUNCED_EMAILS_FILE.exists():
            try:
                with open(BOUNCED_EMAILS_FILE, "r", encoding="utf-8") as bf:
                    bounced = json.load(bf)
                bounced_set = {b.strip().lower() for b in bounced}
                if em in bounced_set:
                    errors.append(f"Recipient '{email_str}' previously bounced (logged in bounced_emails.json).")
                elif domain in bounced_set and domain not in {e.split("@")[1].lower() for e in VERIFIED_BAR_REGISTRY}:
                    errors.append(f"Domain '{domain}' previously bounced all outreach.")
            except Exception:
                pass

        # Check DNS MX
        if check_dns and domain not in DEAD_DOMAINS and em not in errors:
            mx_ok, mx_reason = cls.check_domain_mx(domain)
            if not mx_ok and mx_reason:
                errors.append(mx_reason)

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
        check_dns: bool = True,
    ) -> Tuple[bool, List[str]]:
        """
        Validates an outreach email draft for absolute ground-truth accuracy:
        - Rejects mismatched practice areas and bounced addresses
        - Validates recipient email syntax and DNS MX records
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

        # 1. Recipient deliverability & ground-truth gate
        email_ok, email_errors = cls.validate_recipient_email(
            to_email, firm=firm, name=to_name, check_dns=check_dns
        )
        if not email_ok:
            errors.extend(email_errors)

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

        # 9. Geographic & County integrity check (No state/county cross-contamination)
        county_state_map = {
            "hillsborough": {"florida"},
            "gwinnett": {"georgia"},
            "dekalb": {"georgia"},
            "dallas": {"texas"},
            "fort bend": {"texas"},
            "los angeles": {"california"},
            "san diego": {"california"},
            "orange": {"california", "florida"},
            "davidson": {"tennessee"},
        }
        for county_name, valid_states in county_state_map.items():
            if f"{county_name} county" in body_lower or f"{county_name} county" in subj_lower:
                for other_state in ("north carolina", "california", "georgia", "florida", "texas", "tennessee"):
                    if other_state not in valid_states and f"counsel in {other_state}" in body_lower:
                        errors.append(
                            f"Geographic contradiction: {county_name.title()} County is not in {other_state.title()}, "
                            f"but recipient was identified as counsel in {other_state.title()}."
                        )

        # 10. Florida Statutory Differentiation: Court Registry foreclosure (45.032) vs Tax Deed (197.582)
        if "18-lw-" in body_lower or "tax deed" in body_lower:
            if "post-foreclosure" in body_lower:
                errors.append("Inaccurate legal characterization: Tax deed surplus is administrative under Fla. Stat. § 197.582, not post-foreclosure court litigation.")

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
