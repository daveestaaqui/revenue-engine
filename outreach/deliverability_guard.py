#!/usr/bin/env python3
"""
Surplus Docket — Deliverability Guard & Pre-Flight Deliverability Verifier
========================================================================
Learns from historical bounces and enforces strict pre-flight delivery screening
before any outreach email can be queued or dispatched:
1. Blacklist check against outreach/bounced_emails.json and gatekeeper blacklists.
2. Generic/role-based mailbox rejection (info@, contact@, editor@, support@, etc.).
3. Live DNS MX verification: validates exchange servers, blocks null-MX (RFC 7505) and dead domains.
4. Yahoo / strict DMARC gateway detection: flags strict authentication requirements.
"""

import csv
import ipaddress
import json
import re
import socket
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

BOUNCED_JSON = BASE_DIR / "outreach" / "bounced_emails.json"
SENT_LOG_CSV = BASE_DIR / "outreach" / "sent_log.csv"

GENERIC_ROLE_PREFIXES = (
    "info@", "contact@", "admin@", "support@", "editor@", "compliance@",
    "legal@", "help@", "office@", "billing@", "sales@", "inquiries@",
    "media@", "press@", "team@", "careers@", "jobs@", "feedback@",
    "consultations@", "intake@", "reception@", "general@", "mail@"
)

# Providers known to reject unauthenticated relays with 550 5.7.9
STRICT_DKIM_MX_PROVIDERS = (
    "yahoodns.net",
    "yahoomail.com",
    "aol.com",
)


def load_bounced_blacklist() -> set:
    """Loads all blacklisted emails and domains from bounced_emails.json and sent_log.csv."""
    blacklist = set()
    if BOUNCED_JSON.exists():
        try:
            with open(BOUNCED_JSON, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    if isinstance(item, str):
                        blacklist.add(item.strip().lower())
        except Exception:
            pass
    if SENT_LOG_CSV.exists():
        try:
            with open(SENT_LOG_CSV, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    st = (row.get("Status") or "").upper()
                    if "BOUNCE" in st:
                        em = (row.get("Email") or "").strip().lower()
                        if em:
                            blacklist.add(em)
                            if "@" in em:
                                dom = em.split("@")[-1]
                                if dom not in ("gmail.com", "outlook.com", "yahoo.com"):
                                    blacklist.add(dom)
        except Exception:
            pass
    return blacklist


def check_domain_mx(domain: str) -> tuple[bool, str]:
    """
    Validates DNS MX records for the given domain.
    Rejects null MX (RFC 7505), loopback IPs, and unresolvable domains.
    """
    clean_domain = domain.strip().lower()
    if not clean_domain or "." not in clean_domain:
        return False, f"Invalid domain name: '{domain}'"

    # 1. Try dnspython if installed
    try:
        import dns.resolver
        try:
            answers = dns.resolver.resolve(clean_domain, "MX")
            if not answers:
                return False, f"No MX records found for domain '{clean_domain}'"

            mx_hosts = []
            for r in answers:
                exchange = str(r.exchange).rstrip(".").lower()
                # RFC 7505 null MX or unconfigured placeholder MX check
                if exchange in ("", ".", "0") or ".invalid." in exchange or exchange.endswith(".invalid"):
                    return False, f"Domain '{clean_domain}' publishes null/invalid MX record ({exchange})"
                mx_hosts.append(exchange)

            # Check if domain uses strict Yahoo MX without custom DKIM
            for mx in mx_hosts:
                if any(p in mx for p in STRICT_DKIM_MX_PROVIDERS):
                    return False, f"Domain '{clean_domain}' routes through Yahoo/AOL MX ({mx}) which rejects relay without custom domain DKIM"

            if not mx_hosts:
                return False, f"Domain '{clean_domain}' has no valid MX exchange hosts"
            return True, f"MX verified: {mx_hosts[0]}"
        except dns.resolver.NXDOMAIN:
            return False, f"Domain '{clean_domain}' does not exist (NXDOMAIN)"
        except (dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            return False, f"Domain '{clean_domain}' has no active MX records"
        except Exception as e:
            # Fallback to socket
            pass
    except ImportError:
        pass

    # 2. Fallback to system `host -t MX` utility for accurate MX inspection without dnspython
    try:
        proc = subprocess.run(
            ["host", "-t", "MX", clean_domain],
            capture_output=True,
            text=True,
            timeout=3.0,
        )
        out = (proc.stdout or "").strip().lower()
        if "mail is handled by 0 ." in out:
            return False, f"Domain '{clean_domain}' publishes null MX record (explicitly rejects mail)"
        if "not found: 3(nxdomain)" in out or ("host " in out and "not found" in out):
            return False, f"Domain '{clean_domain}' does not exist (NXDOMAIN)"
        if "has no mail handler" in out:
            return False, f"Domain '{clean_domain}' has no active MX records"
        mx_matches = re.findall(r"mail is handled by \d+\s+([^\s\n]+)", out)
        if mx_matches:
            mx_hosts = [m.rstrip(".") for m in mx_matches if m.rstrip(".") not in ("", "0")]
            for mx in mx_hosts:
                if ".invalid." in mx or mx.endswith(".invalid"):
                    return False, f"Domain '{clean_domain}' publishes invalid placeholder MX record ({mx})"
                if any(p in mx for p in STRICT_DKIM_MX_PROVIDERS):
                    return False, f"Domain '{clean_domain}' routes through Yahoo/AOL MX ({mx}) which rejects relay without custom domain DKIM"
            if mx_hosts:
                return True, f"MX verified: {mx_hosts[0]}"
    except Exception:
        pass

    # 3. Fallback to socket getaddrinfo
    try:
        addrinfo = socket.getaddrinfo(clean_domain, 25, proto=socket.IPPROTO_TCP)
        if not addrinfo:
            return False, f"Domain '{clean_domain}' host could not be resolved"
        ip = addrinfo[0][4][0]
        # Check loopback or private IP
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_unspecified:
            return False, f"Domain '{clean_domain}' resolves to invalid/private IP: {ip}"
        return True, f"Host verified: {clean_domain} ({ip})"
    except socket.gaierror:
        return False, f"Domain '{clean_domain}' does not resolve (gaierror)"
    except Exception as e:
        return False, f"DNS error resolving '{clean_domain}': {e}"


def validate_recipient_deliverability(email_str: str, check_dns: bool = True) -> tuple[bool, str]:
    """
    Comprehensive deliverability pre-flight check for any outreach recipient.
    Returns (True, "Deliverable") or (False, "Failure Reason").
    """
    if not email_str or "@" not in email_str:
        return False, f"Malformed email address: '{email_str}'"

    clean_email = email_str.strip().lower()
    parts = clean_email.split("@")
    if len(parts) != 2:
        return False, f"Malformed email address: '{email_str}'"

    local_part, domain = parts
    if not local_part or not domain:
        return False, f"Empty local part or domain in: '{email_str}'"

    # 1. Blacklist check against bounced_emails.json
    blacklist = load_bounced_blacklist()
    if clean_email in blacklist:
        return False, f"Email '{clean_email}' previously bounced (blacklisted in bounced_emails.json)"
    if domain in blacklist:
        return False, f"Domain '{domain}' previously bounced all outreach (blacklisted in bounced_emails.json)"

    # 2. Role-based prefix rejection
    if clean_email.startswith(GENERIC_ROLE_PREFIXES):
        return False, f"Email '{clean_email}' is a generic department mailbox (e.g. info@, contact@). Direct individual attorneys required."

    # 3. DNS MX Deliverability Verification
    if check_dns:
        mx_ok, mx_msg = check_domain_mx(domain)
        if not mx_ok:
            return False, f"Deliverability Guard rejected '{clean_email}': {mx_msg}"

    return True, "Deliverable"


if __name__ == "__main__":
    test_emails = [
        "RPZ99@Florida-Counsel.com",
        "evan@evanmrosen.com",
        "neil@tygarlaw.com",
        "brett@bighamlaw.com",
        "info@bighamlaw.com",
        "byoakum@evanspetree.com"
    ]
    print("Testing Deliverability Guard:")
    for te in test_emails:
        ok, reason = validate_recipient_deliverability(te, check_dns=True)
        status_icon = "✓" if ok else "❌"
        print(f"  {status_icon} {te}: {reason}")
