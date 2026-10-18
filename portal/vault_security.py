#!/usr/bin/env python3
"""
Surplus Docket — Cryptographic Vault Security & Subscriber Token Engine
======================================================================
Provides zero-friction, zero-password cryptographic protection for court docket dossiers.
- Unredacted dossiers are encrypted at build time using a vault key.
- Active subscribers receive unique, authenticated deep links in their 7:00 AM morning feeds.
- Clicking the link in the email instantly decrypts and unlocks the dossier with zero passwords.
- Existing subscribers can also unlock by entering their billing email (verified via SHA-256 hash).
- Non-subscribers see an institutional paywalled preview with masked titleholders and clerk PDF links.
"""

import json
import struct
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
SUBSCRIBERS_FILE = BASE_DIR / "portal" / "subscribers.json"
VAULT_FILE = BASE_DIR / "site" / "api" / "v1" / "vault.json"
AUTH_REGISTRY_FILE = BASE_DIR / "site" / "api" / "v1" / "auth_registry.json"

# Fixed salt for deterministic subscriber key derivation across system
VAULT_SALT = "SD_SURPLUS_REGISTRY_2026_LEGAL_INTELLIGENCE"


def xor_crypt(data: bytes, key: bytes) -> bytes:
    """
    CTR stream cipher using SHA-256 block keystream.
    Deterministic, fast, symmetric (encrypt == decrypt), zero external dependencies.
    """
    out = bytearray(len(data))
    num_blocks = (len(data) + 31) // 32
    for block_idx in range(num_blocks):
        counter_bytes = struct.pack(">I", block_idx)
        keystream = hashlib.sha256(key + counter_bytes).digest()
        start = block_idx * 32
        end = min(start + 32, len(data))
        for j in range(start, end):
            out[j] = data[j] ^ keystream[j - start]
    return bytes(out)


def normalize_date_token(date_str: Optional[str] = None) -> str:
    """Normalizes any human-readable or machine date string to ISO YYYY-MM-DD."""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    clean = str(date_str).strip()
    if "T" in clean:
        clean = clean.split("T")[0].strip()
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%Y%m%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(clean, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return datetime.now().strftime("%Y-%m-%d")


def get_current_vault_key(date_str: Optional[str] = None) -> str:
    """
    Derives deterministic 32-character hex vault key for the active publication cycle.
    """
    date_token = normalize_date_token(date_str)
    return hashlib.sha256(f"SD_VAULT_KEY_{date_token}_{VAULT_SALT}".encode("utf-8")).hexdigest()[:32]


def get_vault_signature(vault_key: str) -> str:
    """
    16-character public verification signature of the vault key.
    Used by browser client to verify decrypted vault key correctness.
    """
    return hashlib.sha256(f"SIG_{vault_key}_{VAULT_SALT}".encode("utf-8")).hexdigest()[:16]


def get_subscriber_user_key(email: str) -> bytes:
    """
    Derives 32-byte key for a subscriber from their normalized email and salt.
    """
    normalized = email.strip().lower()
    return hashlib.sha256(f"SUB_KEY_{normalized}_{VAULT_SALT}".encode("utf-8")).digest()


def get_subscriber_email_hash(email: str) -> str:
    """
    One-way SHA-256 hash of normalized subscriber email for zero-exposure public manifest.
    """
    normalized = email.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_subscriber_auth_token(email: str) -> str:
    """
    24-character public authentication token identifying an active subscriber.
    """
    normalized = email.strip().lower()
    return hashlib.sha256(f"SUB_TOKEN_{normalized}_{VAULT_SALT}".encode("utf-8")).hexdigest()[:24]


def get_docket_unique_auth(email: str, docket_id: str, date_str: str) -> str:
    """
    Unique authentication signature per subscriber, per docket, per daily dispatch.
    Ensures every email contains unique authenticated URLs.
    """
    normalized_email = email.strip().lower()
    normalized_docket = str(docket_id).strip().lower()
    date_token = normalize_date_token(date_str)
    seed = f"{normalized_email}:{normalized_docket}:{date_token}:{VAULT_SALT}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]


def build_subscriber_deep_url(docket_id: str, county: str, state: str,
                              subscriber_email: str, date_str: str) -> str:
    """
    Constructs the unique authenticated deep URL for a subscriber.
    Contains the vault key and docket auth token so clicking from email unlocks instantly.
    """
    import urllib.parse
    vault_key = get_current_vault_key(date_str)
    clean_docket = re.sub(r"^(parcel|case|apn|docket)\s+", "", str(docket_id), flags=re.I).strip()
    auth_token = get_docket_unique_auth(subscriber_email, clean_docket, date_str)
    sub_token = get_subscriber_auth_token(subscriber_email)

    params = {
        "docket": clean_docket,
        "county": str(county).strip(),
        "state": str(state).strip(),
        "k": vault_key,
        "auth": auth_token,
        "sub": sub_token,
    }
    return f"https://surplusdocket.com/docket.html?{urllib.parse.urlencode(params)}"


def encrypt_docket_payload(lead: Dict[str, Any], vault_key: str) -> str:
    """
    Encrypts unredacted sensitive docket dossier fields with the vault key.
    Returns hex-encoded ciphertext.
    """
    docket_id = str(lead.get("Case_or_TaxDeed_No") or lead.get("docket_id") or lead.get("Parcel_ID") or "").strip()
    raw_payload = {
        "docket_id": docket_id,
        "Case_or_TaxDeed_No": lead.get("Case_or_TaxDeed_No", ""),
        "Parcel_ID": lead.get("Parcel_ID", ""),
        "Owner_Name": lead.get("Owner_Name", ""),
        "Property_Address": lead.get("Property_Address", ""),
        "Clerk_Verification_URL": lead.get("Clerk_Verification_URL") or lead.get("Source_URL", ""),
        "Verify_Note": lead.get("Verify_Note", ""),
        "Governing_Statute": lead.get("Governing_Statute", ""),
        "Claim_Deadline_Date": lead.get("Claim_Deadline_Date", ""),
        "Claim_Urgency_Tier": lead.get("Claim_Urgency_Tier", ""),
        "Surplus_Balance_USD": lead.get("Surplus_Balance_USD", 0),
        "County": lead.get("County", ""),
        "State": lead.get("State", ""),
        "Sale_Date": lead.get("Sale_Date", ""),
    }
    json_bytes = json.dumps(raw_payload, separators=(",", ":")).encode("utf-8")
    docket_key = hashlib.sha256(vault_key.encode("utf-8") + docket_id.lower().encode("utf-8")).digest()
    cipher = xor_crypt(json_bytes, docket_key)
    return cipher.hex()


def decrypt_docket_payload(cipher_hex: str, docket_id: str, vault_key: str) -> Dict[str, Any]:
    """
    Decrypts hex-encoded dossier payload using the vault key.
    """
    cipher_bytes = bytes.fromhex(cipher_hex)
    docket_key = hashlib.sha256(vault_key.encode("utf-8") + str(docket_id).lower().encode("utf-8")).digest()
    plain_bytes = xor_crypt(cipher_bytes, docket_key)
    return json.loads(plain_bytes.decode("utf-8"))


def generate_vault_and_auth_registry(all_leads: list, subscribers: list,
                                     date_str: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Generates vault.json (encrypted dossiers) and auth_registry.json (zero-knowledge subscriber auth).
    """
    vault_key = get_current_vault_key(date_str)
    vault_sig = get_vault_signature(vault_key)
    active_subs = [s for s in subscribers if s.get("status", "").upper() == "ACTIVE"]

    # Build auth registry entries for active subscribers
    subscriber_entries = []
    for s in active_subs:
        email = s.get("email", "").strip().lower()
        if not email:
            continue
        user_key = get_subscriber_user_key(email)
        encrypted_vault_key = xor_crypt(vault_key.encode("utf-8"), user_key).hex()
        subscriber_entries.append({
            "email_hash": get_subscriber_email_hash(email),
            "sub_token": get_subscriber_auth_token(email),
            "vault_payload": encrypted_vault_key,
        })

    auth_registry = {
        "status": "ready",
        "generated_at": datetime.now().isoformat(),
        "vault_sig": vault_sig,
        "valid_vault_sigs": [vault_sig],
        "subscribers": subscriber_entries,
        "active_subscriber_count": len(subscriber_entries),
    }

    # Build encrypted vault for all leads
    dockets_map = {}
    for lead in all_leads:
        case_no = str(lead.get("Case_or_TaxDeed_No", "")).strip()
        parcel = str(lead.get("Parcel_ID", "")).strip()
        docket_id_lead = str(lead.get("docket_id", "")).strip()
        docket_id = case_no or docket_id_lead or parcel
        if not docket_id:
            continue

        cipher_hex = encrypt_docket_payload(lead, vault_key)
        entry = {
            "docket_id": docket_id,
            "State": lead.get("State", ""),
            "County": lead.get("County", ""),
            "Surplus_Balance_USD": lead.get("Surplus_Balance_USD", 0),
            "Governing_Statute": lead.get("Governing_Statute", ""),
            "Claim_Urgency_Tier": lead.get("Claim_Urgency_Tier", ""),
            "Claim_Deadline_Date": lead.get("Claim_Deadline_Date", ""),
            "Sale_Date": lead.get("Sale_Date", ""),
            "cipher": cipher_hex,
        }
        dockets_map[docket_id.lower()] = entry
        if docket_id_lead and docket_id_lead.lower() not in dockets_map:
            dockets_map[docket_id_lead.lower()] = entry
        if parcel and parcel.lower() not in dockets_map:
            dockets_map[parcel.lower()] = entry

    vault_payload = {
        "status": "subscription_gated",
        "generated_at": datetime.now().isoformat(),
        "total_dockets_vaulted": len(dockets_map),
        "dockets": dockets_map,
    }

    return vault_payload, auth_registry
