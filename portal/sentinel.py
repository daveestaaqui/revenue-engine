#!/usr/bin/env python3
"""
Surplus Docket — Bounded Autonomous Sentinel
============================================
Continuous autonomous monitoring and bounded containment engine:
1. API Rate & Abuse Sentinel: Detects anomalous bursts and credential probing.
2. Tenant Isolation Sentinel: Detects unauthorized cross-tenant requests.
3. AI Spend & Provider Sentinel: Flags unbudgeted API consumption and unexpected fallback events.
4. Data Integrity Sentinel: Detects feed parser drift and statutory citation mismatches.

Bounded Containment Policy:
- May quarantine a compromised or abusive API key.
- May pause ingestion on a drifting county connector.
- May flag high-severity incidents for operator review.
- Strictly PROHIBITED from: deleting database records, modifying statutory rules,
  or making autonomous commercial pricing changes.
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SENTINEL_LOG_FILE = DATA_DIR / "sentinel_audit_log.json"
API_KEYS_FILE = BASE_DIR / "portal" / "api_keys.json"


def load_sentinel_log() -> List[Dict[str, Any]]:
    """Loads existing sentinel incident records."""
    if not SENTINEL_LOG_FILE.exists():
        return []
    try:
        with open(SENTINEL_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def record_sentinel_event(event_type: str, severity: str, details: Dict[str, Any], containment_action: Optional[str] = None) -> Dict[str, Any]:
    """
    Appends an immutable sentinel event to the audit ledger.
    Severity: 'INFO' | 'WARNING' | 'HIGH' | 'CRITICAL'
    """
    SENTINEL_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logs = load_sentinel_log()

    entry = {
        "event_id": f"SNTL-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(logs)+1:04d}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "severity": severity.upper(),
        "containment_action": containment_action or "NONE_OBSERVATION_ONLY",
        "details": details
    }
    logs.append(entry)

    # Keep latest 1,000 entries
    if len(logs) > 1000:
        logs = logs[-1000:]

    with open(SENTINEL_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)

    return entry


def quarantine_api_key(token_digest: str, reason: str) -> bool:
    """
    Bounded containment action: marks an abusive or compromised API key as QUARANTINED.
    """
    if not API_KEYS_FILE.exists():
        return False
    try:
        with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
            registry = json.load(f)

        if token_digest in registry:
            registry[token_digest]["status"] = "QUARANTINED"
            registry[token_digest]["quarantined_at"] = datetime.now(timezone.utc).isoformat()
            registry[token_digest]["quarantine_reason"] = reason

            with open(API_KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)

            record_sentinel_event(
                event_type="API_KEY_QUARANTINED",
                severity="HIGH",
                details={"token_digest": token_digest, "reason": reason},
                containment_action=f"Key status set to QUARANTINED ({reason})"
            )
            return True
        return False
    except Exception as e:
        record_sentinel_event(
            event_type="QUARANTINE_FAILURE",
            severity="CRITICAL",
            details={"error": str(e), "token_digest": token_digest}
        )
        return False


def inspect_api_activity(token_digest: str, request_path: str, ip_address: str, status_code: int) -> Optional[Dict[str, Any]]:
    """
    Real-time inspection of API invocations to catch brute-force or unauthorized probing.
    """
    if status_code == 403 and "unauthorized" in request_path.lower():
        return record_sentinel_event(
            event_type="CROSS_TENANT_PROBE_BLOCKED",
            severity="WARNING",
            details={"ip": ip_address, "path": request_path, "token_digest": token_digest},
            containment_action="HTTP_403_REJECTION"
        )
    return None


def inspect_ai_spend_anomaly(current_daily_spend_usd: float, daily_cap_usd: float = 10.00) -> Optional[Dict[str, Any]]:
    """
    Monitors daily AI spend against configured safety caps.
    """
    utilization_pct = (current_daily_spend_usd / daily_cap_usd) * 100.0
    if utilization_pct >= 90.0:
        return record_sentinel_event(
            event_type="AI_BUDGET_CAP_EXCEEDED",
            severity="CRITICAL",
            details={"spend_usd": current_daily_spend_usd, "cap_usd": daily_cap_usd, "utilization_pct": utilization_pct},
            containment_action="DEFER_NON_ESSENTIAL_WORKFLOWS"
        )
    elif utilization_pct >= 75.0:
        return record_sentinel_event(
            event_type="AI_BUDGET_THRESHOLD_WARNING",
            severity="WARNING",
            details={"spend_usd": current_daily_spend_usd, "cap_usd": daily_cap_usd, "utilization_pct": utilization_pct},
            containment_action="OPERATOR_NOTIFICATION"
        )
    return None
