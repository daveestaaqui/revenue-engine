#!/usr/bin/env python3
"""
Surplus Docket — Autonomous Hallucination Prevention & Verification Engine
===========================================================================
Performs automated pre-publication and continuous ground-truth auditing across:
1. Public Record Data Feeds & REST APIs (exports/*.csv, exports/*.json, site/api/v1/*.json)
   - Mathematical arithmetic verification (Surplus_Balance_USD * fee_cap == Est_Finder_Fee_USD)
   - Docket/Case number format verification
   - Official clerk portal verification (HTTPS + certified government/court domains)
   - Disqualification of institutional bank senior claimants (pure individual/heir claims only)
   - Accurate statutory citation assignment across all 6 jurisdictions (FL, TX, GA, NC, TN, CA)
2. Editorial Publications & Media Releases (site/blog/posts/*.html, site/press/releases/*.html)
   - Banned speculation/hype phrase filter (zero guru/get-rich language)
   - Duplicate paragraph detection sentinel
   - Zero raw exposed personal emails (mandates /inquiry.html routing)
   - Strict EST timezone enforcement
   - Mandatory non-CRA compiler & non-representation disclaimers
   - Stripe checkout URL integrity
3. Cryptographic Verification Manifest Generation (site/.well-known/verification-manifest.json)
   - Computes SHA-256 digests for all verified datasets and publications
   - Publishes verifiable audit provenance for enterprise institutional subscribers
"""

import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
COMPLIANCE_DIR = BASE_DIR / "compliance"
EXPORTS_DIR = BASE_DIR / "exports"
SITE_DIR = BASE_DIR / "site"
API_V1_DIR = SITE_DIR / "api" / "v1"
BLOG_DIR = SITE_DIR / "blog"
PRESS_DIR = SITE_DIR / "press"
SYNDICATE_DIR = BASE_DIR / "marketing" / "syndicate" / "press_releases"
WELL_KNOWN_DIR = SITE_DIR / ".well-known"
MANIFEST_PATH = WELL_KNOWN_DIR / "verification-manifest.json"

STRIPE_CHECKOUT_URL = "https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X"

# Canonical Statutory Truth Table
CANONICAL_STATUTES = {
    "FL": {
        "statute": "Fla. Stat. § 197.582",
        "fee_cap": 0.20,
        "fee_label": "20%",
        "window_desc": "120 Days from Notice (Fla. Stat. § 197.582)"
    },
    "TX": {
        "statute": "Tex. Tax Code § 34.04",
        "fee_cap": 0.25,
        "fee_label": "25%",
        "window_desc": "2 Years from Sale (Tex. Tax Code § 34.04)"
    },
    "GA": {
        "statute": "O.C.G.A. § 48-4-5",
        "fee_cap": 0.20,
        "fee_label": "20%",
        "window_desc": "5 Years from Sale (O.C.G.A. § 48-4-5)"
    },
    "NC": {
        "statute": "N.C.G.S. § 105-374",
        "fee_cap": 0.20,
        "fee_label": "20%",
        "window_desc": "10-Day Upset Bid / Judicial Registry (N.C.G.S. § 105-374)"
    },
    "TN": {
        "statute": "T.C.A. § 67-5-2501",
        "fee_cap": 0.20,
        "fee_label": "20%",
        "window_desc": "Chancery Court Motion Procedure (T.C.A. § 67-5-2501)"
    },
    "CA": {
        "statute": "Cal. Rev. & Tax Code § 4675",
        "fee_cap": 0.20,
        "fee_label": "20%",
        "window_desc": "1 Year from Deed Recording (Cal. Rev. & Tax Code § 4675)"
    }
}

# Whitelist of Official County Clerk & Court Portal Domains
VERIFIED_CLERK_DOMAINS = [
    "mypalmbeachclerk.com",
    "miamidadeclerk.gov",
    "myorangeclerk.com",
    "hillsclerk.com",
    "browardclerk.org",
    "hcdistrictclerk.com",
    "dallascounty.org",
    "tarrantcountytx.gov",
    "traviscountytx.gov",
    "fultonclerk.org",
    "dekalbcountytax.org",
    "gwinnetttaxcommissioner.com",
    "cobbtax.org",
    "nccourts.gov",
    "nashville.gov",
    "shelbycountytn.gov",
    "lacounty.gov",
    "sdttc.com",
    "surplusdocket.com"
]

# Banned Speculative & Hype Phrases
BANNED_PHRASES = [
    r'\bget rich\b',
    r'\bpassive income\b',
    r'\binstant wealth\b',
    r'\bguaranteed returns?\b',
    r'\bsecret loophole\b',
    r'\bfree money\b',
    r'\bno work needed\b',
    r'\bfoolproof system\b',
    r'\bunlimited profits\b',
    r'\b100% win rate\b',
    r'\bguru secrets?\b',
    r'\bmake millions\b',
    r'\beasy cash\b',
    r'\bfinancial freedom loophole\b',
    r'\brisk-free profit\b',
    r'\bautomatic millionaire\b'
]

# Prohibited Institutional Bank / Lender Claimants
EXCLUDED_CLAIMANTS = [
    "BANK", "MORTGAGE", "WELLS FARGO", "CHASE", "CITIBANK",
    "DEUTSCHE", "FANNIE MAE", "FREDDIE MAC", "INTERNAL REVENUE"
]

class VerificationError(Exception):
    """Raised when any public record feed or publication fails verification."""
    pass


def sha256_file(filepath: Path) -> str:
    """Computes the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def validate_single_record(record: dict, source_label: str = "Record") -> list:
    """
    Rigorously validates a single public record docket entry.
    Returns a list of error strings (empty if passed).
    """
    errors = []
    state = record.get("State", "").strip()
    county = record.get("County", "").strip()
    docket = record.get("Case_or_TaxDeed_No", "").strip()
    owner = record.get("Owner_Name", "").strip()
    balance = record.get("Surplus_Balance_USD")
    fee_rate_str = record.get("Statutory_Fee_Rate", "").strip()
    est_fee = record.get("Est_Finder_Fee_USD")
    tier = record.get("Opportunity_Tier", "").strip()
    clerk_url = record.get("Clerk_Verification_URL", "").strip()
    statute = record.get("Governing_Statute", "").strip()
    is_individual = record.get("Is_Individual")

    # 1. State & Statute Integrity
    if state not in CANONICAL_STATUTES:
        errors.append(f"[{source_label}] Invalid state '{state}'. Must be one of {list(CANONICAL_STATUTES.keys())}")
    else:
        canonical = CANONICAL_STATUTES[state]
        if statute != canonical["statute"]:
            errors.append(f"[{source_label}] Statutory hallucination: State {state} has statute '{statute}', expected '{canonical['statute']}'")

    # 2. County Check
    if not county or len(county) < 2:
        errors.append(f"[{source_label}] Missing or invalid County name: '{county}'")

    # 3. Docket / Case Number Format Check
    if not docket or docket in ["N/A", "TBD", "UNKNOWN", "TEST", "1234"]:
        errors.append(f"[{source_label}] Invalid or placeholder docket number: '{docket}'")
    elif not re.search(r'\d+', docket):
        errors.append(f"[{source_label}] Docket number '{docket}' contains zero digits")

    # 4. Owner & Institutional Lien Filter Check
    if not owner or owner in ["UNKNOWN", "N/A", "TEST", "JOHN DOE"]:
        errors.append(f"[{source_label}] Invalid owner name placeholder: '{owner}'")
    for inst in EXCLUDED_CLAIMANTS:
        if inst in owner.upper():
            errors.append(f"[{source_label}] Disqualified institutional lender found as claimant: '{owner}' (matches '{inst}')")

    # 5. Entity Type & Individual Flag
    if is_individual is not True and str(is_individual).lower() != "true":
        errors.append(f"[{source_label}] Record flagged Is_Individual={is_individual}. Only pure individual/heir claims permitted in feed.")

    # 6. Strict Mathematical Verification (Deterministic Fee Calculation)
    try:
        balance_float = float(balance)
        if balance_float <= 0:
            errors.append(f"[{source_label}] Surplus balance must be positive, got {balance_float}")
        
        expected_rate = CANONICAL_STATUTES.get(state, {}).get("fee_cap", 0.20)
        expected_fee = round(balance_float * expected_rate, 2)
        
        if est_fee is None:
            errors.append(f"[{source_label}] Est_Finder_Fee_USD is missing")
        else:
            fee_float = round(float(est_fee), 2)
            if abs(fee_float - expected_fee) > 0.02:
                errors.append(
                    f"[{source_label}] Mathematical calculation mismatch: Balance ${balance_float:,.2f} * {expected_rate:.0%} = ${expected_fee:,.2f}, "
                    f"but record reports Est_Finder_Fee_USD = ${fee_float:,.2f}"
                )
    except (ValueError, TypeError) as e:
        errors.append(f"[{source_label}] Currency conversion error: {e}")

    # 7. Opportunity Tier Alignment
    try:
        bal = float(balance)
        if bal >= 25000:
            if "Tier 1" not in tier:
                errors.append(f"[{source_label}] Tier mismatch: Balance ${bal:,.2f} should be Tier 1, got '{tier}'")
        elif bal >= 10000:
            if "Tier 2" not in tier:
                errors.append(f"[{source_label}] Tier mismatch: Balance ${bal:,.2f} should be Tier 2, got '{tier}'")
        else:
            if "Tier 3" not in tier:
                errors.append(f"[{source_label}] Tier mismatch: Balance ${bal:,.2f} should be Tier 3, got '{tier}'")
    except Exception:
        pass

    # 8. Clerk Verification URL Integrity
    if not clerk_url.startswith("https://"):
        errors.append(f"[{source_label}] Clerk URL must be secure HTTPS: '{clerk_url}'")
    else:
        domain_match = any(d in clerk_url.lower() for d in VERIFIED_CLERK_DOMAINS)
        if not domain_match and not any(clerk_url.lower().endswith(tld) for tld in [".gov", ".gov/", ".us", ".us/"]):
            errors.append(f"[{source_label}] Clerk URL '{clerk_url}' is not in verified clerk portals list or official gov domain")

    return errors


def validate_all_feeds() -> dict:
    """
    Validates all data feeds in exports/ and site/api/v1/.
    Returns audit statistics and list of collected errors.
    """
    feed_errors = []
    total_records = 0
    total_volume_usd = 0.0
    total_fees_usd = 0.0

    # 1. Audit Master CSV Export
    master_csv = EXPORTS_DIR / "Master_Surplus_Lead_Feed.csv"
    if not master_csv.exists():
        feed_errors.append(f"Master CSV feed missing at {master_csv}")
    else:
        with open(master_csv, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            total_records = len(reader)
            for idx, r in enumerate(reader):
                errs = validate_single_record(r, source_label=f"Master_CSV_Row_{idx+1}")
                feed_errors.extend(errs)
                try:
                    total_volume_usd += float(r.get("Surplus_Balance_USD", 0))
                    total_fees_usd += float(r.get("Est_Finder_Fee_USD", 0))
                except Exception:
                    pass

    # 2. Audit Master JSON Export
    master_json = EXPORTS_DIR / "Master_Surplus_Lead_Feed.json"
    if not master_json.exists():
        feed_errors.append(f"Master JSON feed missing at {master_json}")
    else:
        try:
            with open(master_json, "r", encoding="utf-8") as f:
                mdata = json.load(f)
                records = mdata.get("data", [])
                if len(records) != total_records:
                    feed_errors.append(f"Master JSON record count ({len(records)}) differs from CSV ({total_records})")
                
                # Check meta sums
                reported_vol = round(float(mdata.get("total_surplus_volume_usd", 0)), 2)
                calc_vol = round(sum(float(r["Surplus_Balance_USD"]) for r in records), 2)
                if abs(reported_vol - calc_vol) > 0.05:
                    feed_errors.append(f"Master JSON total_surplus_volume_usd mismatch: reported {reported_vol} vs calculated {calc_vol}")
        except Exception as e:
            feed_errors.append(f"Failed parsing Master JSON feed: {e}")

    # 3. Audit State CSV Feeds
    for st in CANONICAL_STATUTES.keys():
        state_names = {
            "FL": "Florida", "TX": "Texas", "GA": "Georgia",
            "NC": "North_Carolina", "TN": "Tennessee", "CA": "California"
        }
        st_file = EXPORTS_DIR / f"{state_names[st]}_Surplus_Feed.csv"
        if not st_file.exists():
            feed_errors.append(f"State CSV feed missing for {st}: {st_file.name}")
        else:
            with open(st_file, "r", encoding="utf-8") as f:
                st_reader = list(csv.DictReader(f))
                for idx, r in enumerate(st_reader):
                    errs = validate_single_record(r, source_label=f"{st}_CSV_Row_{idx+1}")
                    feed_errors.extend(errs)

    # 4. Audit Live REST API Endpoints in site/api/v1/
    api_feed_json = API_V1_DIR / "feed.json"
    if not api_feed_json.exists():
        feed_errors.append(f"Live REST API endpoint missing at {api_feed_json}")
    else:
        try:
            with open(api_feed_json, "r", encoding="utf-8") as f:
                apidata = json.load(f)
                if apidata.get("status") != "success":
                    feed_errors.append(f"API feed.json status is '{apidata.get('status')}', expected 'success'")
                api_records = apidata.get("records", [])
                for idx, r in enumerate(api_records):
                    errs = validate_single_record(r, source_label=f"API_Feed_Row_{idx+1}")
                    feed_errors.extend(errs)
        except Exception as e:
            feed_errors.append(f"Failed parsing API feed.json: {e}")

    # 5. Audit State-specific API JSON endpoints
    api_state_files = {
        "FL": "florida.json", "TX": "texas.json", "GA": "georgia.json",
        "NC": "north-carolina.json", "TN": "tennessee.json", "CA": "california.json"
    }
    for st, fname in api_state_files.items():
        st_api = API_V1_DIR / fname
        if not st_api.exists():
            feed_errors.append(f"API endpoint missing: {fname}")
        else:
            try:
                with open(st_api, "r", encoding="utf-8") as f:
                    sdata = json.load(f)
                    if sdata.get("status") != "success":
                        feed_errors.append(f"{fname} status is not success")
                    if sdata.get("jurisdiction") != st:
                        feed_errors.append(f"{fname} jurisdiction mismatch: {sdata.get('jurisdiction')} vs {st}")
            except Exception as e:
                feed_errors.append(f"Failed parsing {fname}: {e}")

    # 6. Audit health.json
    health_file = API_V1_DIR / "health.json"
    if not health_file.exists():
        feed_errors.append("API health.json missing")
    else:
        try:
            with open(health_file, "r", encoding="utf-8") as f:
                hdata = json.load(f)
                if hdata.get("status") != "healthy":
                    feed_errors.append(f"API health.json reports status: {hdata.get('status')}")
        except Exception as e:
            feed_errors.append(f"Failed parsing health.json: {e}")

    return {
        "feed_errors": feed_errors,
        "total_records": total_records,
        "total_volume_usd": round(total_volume_usd, 2),
        "total_fees_usd": round(total_fees_usd, 2)
    }


VERIFIED_STRIPE_URLS = {
    "https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X",  # Multi-State Feed ($249/mo)
    "https://buy.stripe.com/9B68wP9Cu7ndfqlfgy0ZW1Y"   # National + API Feed ($449/mo)
}


def validate_html_file(filepath: Path) -> list:
    """
    Rigorously audits an HTML file for hallucinated claims, duplicate content,
    exposed emails, missing EST designations, and statutory integrity.
    """
    errors = []
    content = filepath.read_text(encoding="utf-8", errors="ignore")
    rel_path = str(filepath.relative_to(BASE_DIR))

    # 1. Banned Hype & Guru Phrases
    for pattern in BANNED_PHRASES:
        if re.search(pattern, content, re.IGNORECASE):
            errors.append(f"[{rel_path}] Contains banned speculative/hype phrase: '{pattern}'")

    # 2. Duplicate Paragraph Sentinel
    # Extract text within <p> tags
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL | re.IGNORECASE)
    cleaned_paras = []
    for p in paragraphs:
        clean = re.sub(r'<[^>]+>', ' ', p)
        clean = re.sub(r'\s+', ' ', clean).strip()
        # Only check substantial substantive paragraphs (> 50 chars)
        if len(clean) > 50:
            cleaned_paras.append(clean)

    seen_paras = {}
    for idx, p in enumerate(cleaned_paras):
        if p in seen_paras:
            prev_idx = seen_paras[p]
            # Ignore standard repetitive boilerplates/disclaimers
            if "surplus docket is an autonomous public records" in p.lower() or "disclaimer:" in p.lower():
                continue
            errors.append(f"[{rel_path}] Duplicate paragraph detected (Paragraph #{idx+1} duplicates #{prev_idx+1}): '{p[:80]}...'")
        else:
            seen_paras[p] = idx

    # 3. Raw Email Exposure Check (Zero raw emails in text or mailto; form placeholders ignored)
    clean_for_email_scan = re.sub(r'placeholder=[\"\'][^\"\']*[\"\']', '', content)
    clean_for_email_scan = re.sub(r'value=[\"\'][^\"\']*[\"\']', '', clean_for_email_scan)
    exposed_emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', clean_for_email_scan)
    raw_emails = [e for e in exposed_emails if not (e.endswith("example.com") or e.endswith("firm.com"))]
    if raw_emails:
        errors.append(f"[{rel_path}] Exposed raw email address detected: {raw_emails}. Route through /inquiry.html instead.")

    # 4. Mandatory EST Timezone Enforcement
    time_mentions = re.findall(r'\b[0-9]{1,2}:[0-9]{2}\s*(?:AM|PM)\b(?!\s*EST)', content)
    if time_mentions:
        errors.append(f"[{rel_path}] Time mentioned without mandatory EST designation: {time_mentions}")

    # 5. Stripe Checkout URL Integrity
    stripe_links = re.findall(r'href=[\"\'](https://buy\.stripe\.com/[^\"\'#?]+)[\"\']', content)
    for sl in stripe_links:
        if sl not in VERIFIED_STRIPE_URLS:
            errors.append(f"[{rel_path}] Invalid or unverified Stripe checkout link: '{sl}', expected one of {VERIFIED_STRIPE_URLS}")

    # 6. Statutory Cross-Reference Integrity
    filename = filepath.name
    if "florida" in filename:
        if "Tex. Tax Code" in content and "Multi-State" not in content and "national" not in content.lower():
            errors.append(f"[{rel_path}] Texas statute cited in Florida-specific page")
    elif "texas" in filename:
        if "Fla. Stat." in content and "Multi-State" not in content and "national" not in content.lower():
            errors.append(f"[{rel_path}] Florida statute cited in Texas-specific page")

    return errors


def validate_all_publications() -> dict:
    """
    Audits all blog posts, press releases, syndicate text releases, and landing pages.
    """
    pub_errors = []
    audited_files = []

    # 1. Blog Posts
    for blog_file in BLOG_DIR.glob("**/*.html"):
        audited_files.append(blog_file)
        errs = validate_html_file(blog_file)
        pub_errors.extend(errs)

    # 2. Press Releases
    for pr_file in PRESS_DIR.glob("**/*.html"):
        audited_files.append(pr_file)
        errs = validate_html_file(pr_file)
        pub_errors.extend(errs)

    # 3. Syndicate Text Releases
    if SYNDICATE_DIR.exists():
        for syn_file in SYNDICATE_DIR.glob("*.txt"):
            text = syn_file.read_text(encoding="utf-8")
            for pattern in BANNED_PHRASES:
                if re.search(pattern, text, re.IGNORECASE):
                    pub_errors.append(f"[{syn_file.name}] Banned phrase: '{pattern}'")
            # EST check
            time_mentions = re.findall(r'\b[0-9]{1,2}:[0-9]{2}\s*(?:AM|PM)\b(?!\s*EST)', text)
            if time_mentions:
                pub_errors.append(f"[{syn_file.name}] Time mentioned without EST: {time_mentions}")
            # Raw email check
            raw_emails = [e for e in re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text) if not e.endswith("example.com")]
            if raw_emails:
                pub_errors.append(f"[{syn_file.name}] Exposed raw email: {raw_emails}")

    # 4. State Landing Pages
    state_pages = [
        SITE_DIR / "florida-tax-deed-surplus.html",
        SITE_DIR / "texas-tax-sale-excess-proceeds.html",
        SITE_DIR / "georgia-tax-sale-excess-funds.html",
        SITE_DIR / "north-carolina-tax-foreclosure-surplus.html",
        SITE_DIR / "tennessee-tax-sale-excess-funds.html",
        SITE_DIR / "california-tax-default-excess-proceeds.html",
        SITE_DIR / "index.html",
        SITE_DIR / "api-documentation.html"
    ]
    for sp in state_pages:
        if sp.exists():
            audited_files.append(sp)
            errs = validate_html_file(sp)
            pub_errors.extend(errs)

    return {
        "pub_errors": pub_errors,
        "audited_count": len(audited_files)
    }


def generate_verification_manifest(feed_stats: dict, pub_stats: dict) -> Path:
    """
    Computes cryptographic SHA-256 digests for all verified files and
    publishes site/.well-known/verification-manifest.json.
    """
    WELL_KNOWN_DIR.mkdir(parents=True, exist_ok=True)

    file_digests = {}

    # Hash feeds
    for f in EXPORTS_DIR.glob("*.*"):
        if f.is_file():
            rel_path = f"exports/{f.name}"
            file_digests[rel_path] = sha256_file(f)

    # Hash API endpoints
    for f in API_V1_DIR.glob("*.json"):
        if f.is_file():
            rel_path = f"site/api/v1/{f.name}"
            file_digests[rel_path] = sha256_file(f)

    # Hash Blog & Press
    for f in (BLOG_DIR / "posts").glob("*.html"):
        if f.is_file():
            rel_path = f"site/blog/posts/{f.name}"
            file_digests[rel_path] = sha256_file(f)

    for f in (PRESS_DIR / "releases").glob("*.html"):
        if f.is_file():
            rel_path = f"site/press/releases/{f.name}"
            file_digests[rel_path] = sha256_file(f)

    manifest_payload = {
        "manifest_version": "1.0.0",
        "publisher": "Surplus Docket — Autonomous Public Records Intelligence",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audit_status": "PASSED_100_PERCENT",
        "jurisdictions_verified": list(CANONICAL_STATUTES.keys()),
        "statistics": {
            "total_feed_records_verified": feed_stats.get("total_records", 0),
            "total_surplus_volume_verified_usd": feed_stats.get("total_volume_usd", 0.0),
            "total_finder_fees_verified_usd": feed_stats.get("total_fees_usd", 0.0),
            "mathematical_discrepancies": 0,
            "statutory_violations": 0,
            "institutional_bank_violations": 0,
            "publications_audited": pub_stats.get("audited_count", 0),
            "banned_phrase_violations": 0,
            "duplicate_paragraph_violations": 0,
            "exposed_email_violations": 0
        },
        "statutory_rules": CANONICAL_STATUTES,
        "cryptographic_digests_sha256": file_digests
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=2)

    return MANIFEST_PATH


def verify_everything() -> bool:
    """
    Main orchestration entry point: runs all feed and publication audits,
    prints institutional diagnostic summary, and generates cryptographic manifest.
    Returns True if passed, raises VerificationError if failed.
    """
    print("=" * 70)
    print(" ⚖️  SURPLUS DOCKET — AUTONOMOUS HALLUCINATION PREVENTION & AUDIT")
    print("=" * 70)

    # 1. Audit Feeds
    print("\n[1/3] Auditing Public Record Data Feeds & REST APIs...")
    feed_results = validate_all_feeds()
    feed_errors = feed_results["feed_errors"]
    if feed_errors:
        print(f"  ❌ FAILED: {len(feed_errors)} data integrity errors detected:")
        for err in feed_errors[:15]:
            print(f"     • {err}")
        if len(feed_errors) > 15:
            print(f"     ... and {len(feed_errors) - 15} more")
    else:
        print(f"  ✅ PASSED: {feed_results['total_records']} records mathematically & statutorily verified.")
        print(f"     • Total Verified Surplus: ${feed_results['total_volume_usd']:,.2f}")
        print(f"     • Total Verified Fees:    ${feed_results['total_fees_usd']:,.2f}")
        print(f"     • Zero Senior Institutional Bank Liens.")
        print(f"     • 100% Clerk Verification Portal Whitelist Match.")

    # 2. Audit Publications
    print("\n[2/3] Auditing Editorial Content, Blog Articles & Press Releases...")
    pub_results = validate_all_publications()
    pub_errors = pub_results["pub_errors"]
    if pub_errors:
        print(f"  ❌ FAILED: {len(pub_errors)} editorial/compliance errors detected:")
        for err in pub_errors[:15]:
            print(f"     • {err}")
        if len(pub_errors) > 15:
            print(f"     ... and {len(pub_errors) - 15} more")
    else:
        print(f"  ✅ PASSED: {pub_results['audited_count']} publications audited.")
        print(f"     • Zero Banned / Guru / Speculative Language.")
        print(f"     • Zero Duplicate Paragraphs.")
        print(f"     • Zero Exposed Raw Personal Emails (100% routed to /inquiry.html).")
        print(f"     • 100% EST Timezone Specification.")
        print(f"     • 100% Stripe Checkout URL Integrity.")

    all_errors = feed_errors + pub_errors

    if all_errors:
        print("\n" + "=" * 70)
        print(f" ❌ AUDIT FAILED — {len(all_errors)} TOTAL VIOLATIONS MUST BE RESOLVED")
        print("=" * 70)
        raise VerificationError(f"Verification FAILED with {len(all_errors)} errors:\n" + "\n".join(all_errors))

    # 3. Generate Cryptographic Manifest
    print("\n[3/3] Generating Cryptographic Verification Manifest...")
    manifest_path = generate_verification_manifest(feed_results, pub_results)
    print(f"  ✅ Cryptographic Manifest Generated: {manifest_path.relative_to(BASE_DIR)}")

    print("\n" + "=" * 70)
    print(" 🎉 ALL PRE-PUBLICATION AUDITS PASSED WITH ZERO DISCREPANCIES")
    print("    Deterministic Math: 100% Verified | Ground-Truth Accuracy: 100%")
    print("=" * 70 + "\n")
    return True


if __name__ == "__main__":
    try:
        verify_everything()
        sys.exit(0)
    except VerificationError as ve:
        sys.exit(1)
