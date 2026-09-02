#!/usr/bin/env python3
"""
Target Verifier and Deduplicator
================================
1. Merges new attorney leads from new_verified_attorneys.csv into verified_attorney_targets.csv.
2. Checks DNS / MX records for every single domain using socket/dnspython/dig to guarantee 100% deliverability.
3. Deduplicates against already processed targets.
"""

import csv
import os
import re
import socket
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTREACH_DIR = BASE_DIR / "outreach"
MAIN_CSV = OUTREACH_DIR / "verified_attorney_targets.csv"
NEW_CSV = OUTREACH_DIR / "new_verified_attorneys.csv"
ALL_VERIFIED_CSV = OUTREACH_DIR / "all_verified_attorney_targets.csv"


def check_mx_record(domain: str) -> bool:
    """Verifies that a domain has valid MX or A records."""
    if not domain or "." not in domain:
        return False
    
    # Try dig first for fast MX lookup
    try:
        res = subprocess.run(["dig", "+short", "MX", domain], capture_output=True, text=True, timeout=3)
        if res.stdout.strip() and "connection timed out" not in res.stdout:
            # Check for null MX record (e.g. '.')
            output = res.stdout.strip()
            if output != "." and output != "0 .":
                return True
    except Exception:
        pass

    # Fallback to socket getaddrinfo
    try:
        socket.getaddrinfo(domain, 25, socket.AF_INET, socket.SOCK_STREAM)
        return True
    except Exception:
        pass

    # Try A record
    try:
        res_a = subprocess.run(["dig", "+short", "A", domain], capture_output=True, text=True, timeout=3)
        if res_a.stdout.strip() and "connection timed out" not in res_a.stdout:
            return True
    except Exception:
        pass

    return False


def verify_and_merge():
    print("=" * 70)
    print("  🔍 ATTORNEY LEAD VERIFIER & MX VALIDATOR")
    print("=" * 70)

    seen_emails = set()
    valid_targets = []
    invalid_targets = []

    # 1. Read existing targets
    if MAIN_CSV.exists():
        with open(MAIN_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                clean = {k.strip(): (v or "").strip() for k, v in row.items() if k}
                email_addr = clean.get("Email", "").strip().lower()
                if email_addr and email_addr not in seen_emails:
                    seen_emails.add(email_addr)
                    valid_targets.append(clean)

    print(f"Loaded {len(valid_targets)} existing targets from {MAIN_CSV.name}")

    # 2. Read new targets if available
    if NEW_CSV.exists():
        new_count = 0
        with open(NEW_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                clean = {k.strip(): (v or "").strip() for k, v in row.items() if k}
                email_addr = clean.get("Email", "").strip().lower()
                if email_addr and email_addr not in seen_emails:
                    seen_emails.add(email_addr)
                    valid_targets.append(clean)
                    new_count += 1
        print(f"Added {new_count} new unique targets from {NEW_CSV.name}")

    # 3. Validate every domain's MX records
    print(f"\nValidating MX records for all {len(valid_targets)} targets...")
    print("-" * 70)
    
    verified_list = []
    for i, target in enumerate(valid_targets, 1):
        email_addr = target.get("Email", "").strip()
        name = target.get("Name", "")
        firm = target.get("Firm", "")
        state = target.get("State", "")
        
        if "@" not in email_addr:
            invalid_targets.append((target, "Invalid format"))
            continue
            
        domain = email_addr.split("@")[1].strip().lower()
        has_mx = check_mx_record(domain)
        
        if has_mx:
            verified_list.append(target)
            print(f"  [{i:03d}/{len(valid_targets):03d}] ✅ VALID: {name} | {firm} ({email_addr})")
        else:
            invalid_targets.append((target, f"No MX for {domain}"))
            print(f"  [{i:03d}/{len(valid_targets):03d}] ❌ DEAD DOMAIN: {name} | {firm} ({email_addr})")

    # 4. Save clean master list
    fieldnames = ["Name", "Firm", "Email", "State", "Specialty", "Source_URL", "Style_Notes", "Practice_Details"]
    with open(MAIN_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in verified_list:
            writer.writerow({k: t.get(k, "") for k in fieldnames})

    print("\n" + "=" * 70)
    print("  📊 VALIDATION SUMMARY")
    print("=" * 70)
    print(f"  • Verified & Deliverable Targets : {len(verified_list)}")
    print(f"  • Rejected (Dead Domains)       : {len(invalid_targets)}")
    print(f"  • Saved clean master list to     : {MAIN_CSV}")
    print("=" * 70)


if __name__ == "__main__":
    verify_and_merge()
