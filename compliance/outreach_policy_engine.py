#!/usr/bin/env python3
"""
Surplus Docket — Bar Ethics & Outreach Policy Engine
===================================================
Enforces deterministic ethics compliance for legal communications:
1. Florida Bar Rule 4-7.18 (Direct contact & solicitation prohibitions)
2. State Bar Advertising Rules (TX Rule 7.03, GA Rule 7.3, CA Rule 7.3, NC Rule 7.3, TN Rule 7.3)
3. Non-Lawyer Technology Provider Boundary (UPL Defense)
4. Gated SMS Follow-up & Prior Express Consent Verification
"""

import re
from typing import Dict, List, Tuple

STATE_BAR_RULES = {
    "FL": {
        "rule": "Florida Bar Rule 4-7.18",
        "title": "Direct Contact with Prospective Clients",
        "phone_solicitation_allowed": False,
        "written_mail_allowed": True,
        "mandated_disclosure": "Surplus Docket is an independent court records compiler for licensed counsel, not a law firm. Petitions must be filed by licensed Florida counsel.",
    },
    "TX": {
        "rule": "Texas Disciplinary Rules of Professional Conduct Rule 7.03",
        "title": "Prohibited Solicitations and Payments",
        "phone_solicitation_allowed": False,
        "written_mail_allowed": True,
        "mandated_disclosure": "Surplus Docket operates strictly as a public records data service under Texas Tax Code § 34.04.",
    },
    "GA": {
        "rule": "Georgia Rules of Professional Conduct Rule 7.3",
        "title": "Direct Contact with Prospective Clients",
        "phone_solicitation_allowed": False,
        "written_mail_allowed": True,
        "mandated_disclosure": "Court registry monitoring platform under O.C.G.A. § 48-4-5.",
    },
    "CA": {
        "rule": "California Rules of Professional Conduct Rule 7.3",
        "title": "Solicitation of Clients",
        "phone_solicitation_allowed": False,
        "written_mail_allowed": True,
        "mandated_disclosure": "Public records research under Cal. Rev. & Tax Code § 4675.",
    },
    "NC": {
        "rule": "North Carolina Rules of Professional Conduct Rule 7.3",
        "title": "Direct Contact with Potential Clients",
        "phone_solicitation_allowed": False,
        "written_mail_allowed": True,
        "mandated_disclosure": "Tax foreclosure surplus feed under N.C. Gen. Stat. § 105-374.",
    },
    "TN": {
        "rule": "Tennessee Rules of Professional Conduct Rule 7.3",
        "title": "Solicitation of Clients",
        "phone_solicitation_allowed": False,
        "written_mail_allowed": True,
        "mandated_disclosure": "Chancery and circuit court excess proceeds index under Tenn. Code Ann. § 67-5-2510.",
    },
}

GENERAL_UPL_DISCLAIMER = (
    "Surplus Docket is a specialized court records research platform and data publisher, not a law firm. "
    "We do not provide legal representation, legal advice, or file surplus recovery claims. "
    "All surplus recovery claims must be evaluated and filed by licensed legal counsel in the applicable jurisdiction."
)


def evaluate_outreach_permission(context: Dict) -> Tuple[str, str, List[str]]:
    """
    Evaluates proposed communication against jurisdiction ethics and statutory rules.
    
    Context fields:
    - jurisdiction: Two-letter state code (e.g. 'FL', 'TX', 'GA')
    - channel: 'email' | 'sms' | 'phone' | 'mail'
    - recipient_type: 'attorney' | 'claimant' | 'owner' | 'court_clerk'
    - purpose: 'transactional_reply' | 'inbound_callback' | 'drip_marketing' | 'cold_solicitation'
    - has_prior_express_consent: bool (relevant for SMS/phone)
    - requested_legal_representation: bool
    
    Returns:
    - decision: 'ALLOW' | 'HOLD_FOR_REVIEW' | 'BLOCK'
    - reason: Detailed rationale referencing state bar code
    - required_disclaimers: Mandatory text blocks to attach to outgoing draft
    """
    jur = (context.get("jurisdiction") or "").strip().upper()
    channel = (context.get("channel") or "email").lower()
    recipient_type = (context.get("recipient_type") or "attorney").lower()
    purpose = (context.get("purpose") or "transactional_reply").lower()
    consent = bool(context.get("has_prior_express_consent"))
    wants_legal_rep = bool(context.get("requested_legal_representation"))

    disclaimers = [GENERAL_UPL_DISCLAIMER]

    # 1. Non-Lawyer Boundary (Unauthorized Practice of Law Defense)
    if wants_legal_rep:
        return (
            "BLOCK",
            "Inquirer requested legal representation or claim filing. As a non-lawyer data publisher, "
            "Surplus Docket is statutorily prohibited from representing claimants or filing petitions.",
            disclaimers
        )

    # 2. Cold Phone/SMS Solicitation Prohibitions (Rule 4-7.18 / Rule 7.3)
    if channel in ["sms", "phone"]:
        if purpose in ["cold_solicitation", "drip_marketing"]:
            rule_info = STATE_BAR_RULES.get(jur, {})
            rule_name = rule_info.get("rule", "State Bar Rule 7.3")
            return (
                "BLOCK",
                f"Direct telephonic/SMS solicitation of surplus leads is strictly prohibited under {rule_name}. "
                "Only direct written mail or opt-in electronic communications are permissible.",
                disclaimers
            )

        if channel == "sms" and not consent:
            return (
                "BLOCK",
                "SMS requires prior express consent under TCPA and Surplus Docket Communication Policy. "
                "Inbound voicemail without affirmative SMS opt-in cannot be messaged via SMS.",
                disclaimers
            )

    # 3. Specific State Disclaimers
    if jur in STATE_BAR_RULES:
        state_rule = STATE_BAR_RULES[jur]
        disclaimers.append(state_rule["mandated_disclosure"])

    # 4. Inbound Callback & Transactional Responses to Attorneys
    if recipient_type == "attorney" or purpose in ["transactional_reply", "inbound_callback"]:
        return (
            "ALLOW",
            f"Authorized transactional response under {STATE_BAR_RULES.get(jur, {}).get('rule', 'standard legal publisher exemptions')}.",
            disclaimers
        )

    # 5. Default fallback to review
    return (
        "HOLD_FOR_REVIEW",
        "Communication parameters require manual review by intake supervisor before dispatch.",
        disclaimers
    )


if __name__ == "__main__":
    test_ctx = {
        "jurisdiction": "FL",
        "channel": "sms",
        "recipient_type": "attorney",
        "purpose": "inbound_callback",
        "has_prior_express_consent": True,
        "requested_legal_representation": False
    }
    dec, rsn, disc = evaluate_outreach_permission(test_ctx)
    print(f"Decision: {dec}\nReason: {rsn}\nDisclaimers: {len(disc)}")
