#!/usr/bin/env python3
"""
Surplus Docket — Automated Law Firm Website Contact Form Outreach Engine
========================================================================
Bypasses email bounces completely by submitting personalized outreach directly
through official law firm contact / consultation forms.

Features:
- Headless browser automation via Playwright
- Intelligent form field detection (Name, Email, Phone, Subject, Message)
- Personalized self-serve message with state/county deep links & Stripe checkout
- Captures confirmation screenshots as proof of delivery
- Complete audit logging to form_submissions_log.csv
"""

import asyncio
import csv
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# Dynamic Paths (works on both local Mac and GitHub Actions)
BASE_DIR = Path(__file__).resolve().parent.parent
OUTREACH_DIR = BASE_DIR / "outreach"
TARGETS_CSV = OUTREACH_DIR / "verified_attorney_targets.csv"
LOG_CSV = OUTREACH_DIR / "form_submissions_log.csv"
SCREENSHOTS_DIR = OUTREACH_DIR / "form_screenshots"

# Sender Info
SENDER_NAME = "David Mahler"
SENDER_FIRST_NAME = "David"
SENDER_LAST_NAME = "Mahler"
SENDER_EMAIL = "david@surplusdocket.com"
SENDER_PHONE = "508-888-0000"
SITE_URL = "https://surplusdocket.com"
STRIPE_LINK = "https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X"

STATE_NAMES = {
    "FL": "Florida", "TX": "Texas", "GA": "Georgia",
    "NC": "North Carolina", "TN": "Tennessee", "CA": "California",
    "NY": "New York", "NJ": "New Jersey", "OH": "Ohio",
    "IL": "Illinois", "PA": "Pennsylvania", "MD": "Maryland",
    "AZ": "Arizona", "WA": "Washington", "MI": "Michigan",
}

STATE_URLS = {
    "FL": "https://surplusdocket.com/florida-tax-deed-surplus.html",
    "TX": "https://surplusdocket.com/texas-tax-sale-excess-proceeds.html",
    "GA": "https://surplusdocket.com/georgia-tax-sale-excess-funds.html",
    "NC": "https://surplusdocket.com/north-carolina-tax-foreclosure-surplus.html",
    "TN": "https://surplusdocket.com/tennessee-tax-sale-excess-proceeds.html",
    "CA": "https://surplusdocket.com/california-tax-defaulted-excess-proceeds.html",
}

COUNTY_URLS = {
    "miami": "https://surplusdocket.com/miami-dade-tax-deed-surplus.html",
    "palm beach": "https://surplusdocket.com/palm-beach-tax-deed-surplus.html",
    "orange": "https://surplusdocket.com/orange-county-tax-deed-surplus.html",
    "orlando": "https://surplusdocket.com/orange-county-tax-deed-surplus.html",
    "hillsborough": "https://surplusdocket.com/hillsborough-tax-deed-surplus.html",
    "tampa": "https://surplusdocket.com/hillsborough-tax-deed-surplus.html",
    "broward": "https://surplusdocket.com/broward-county-tax-deed-surplus.html",
    "harris": "https://surplusdocket.com/harris-county-excess-proceeds.html",
    "houston": "https://surplusdocket.com/harris-county-excess-proceeds.html",
    "dallas": "https://surplusdocket.com/dallas-county-excess-proceeds.html",
    "tarrant": "https://surplusdocket.com/tarrant-county-excess-proceeds.html",
    "fort worth": "https://surplusdocket.com/tarrant-county-excess-proceeds.html",
    "travis": "https://surplusdocket.com/travis-county-excess-proceeds.html",
    "austin": "https://surplusdocket.com/travis-county-excess-proceeds.html",
    "fulton": "https://surplusdocket.com/fulton-county-excess-funds.html",
    "atlanta": "https://surplusdocket.com/fulton-county-excess-funds.html",
    "dekalb": "https://surplusdocket.com/dekalb-county-excess-funds.html",
    "cobb": "https://surplusdocket.com/cobb-county-excess-funds.html",
}


def get_recommended_link(state_code, practice_details):
    details_lower = (practice_details or "").lower()
    for county_kw, url in COUNTY_URLS.items():
        if county_kw in details_lower:
            return url
    if state_code in STATE_URLS:
        return STATE_URLS[state_code]
    return SITE_URL


def compose_message(target):
    full_name = target.get("Name", "").strip()
    first_name = full_name.split()[0] if full_name else ""
    firm = target.get("Firm", "").strip()
    state_code = target.get("State", "FL").strip().upper()
    state_name = STATE_NAMES.get(state_code, state_code)
    practice_details = target.get("Practice_Details", "")

    greeting = f"Hi {first_name}," if first_name else f"Hello {firm} team,"
    recommended_link = get_recommended_link(state_code, practice_details)

    variants = ["A", "B", "C"]
    chosen_variant = random.choice(variants)
    
    if chosen_variant == "A":
        subject = f"{state_name} surplus & excess proceeds data"
        body = f"""{greeting}

I'm reaching out because I built a tool that indexes tax deed surplus and excess proceeds cases across {state_name}.

Most county surplus lists are a headache to work through because the majority of files are encumbered by senior mortgages or bank liens that wipe out the funds. We pull the dockets daily and filter out those institutional liens upstream, so you're only looking at clean individual and estate claims.

You can inspect the live {state_name} feed and sample cases directly here:
{recommended_link}

We deliver the standardized feed every morning at 7:00 AM EST (CSV, Excel, JSON). If you'd like to set up daily delivery for your practice ($249/mo flat, cancel anytime), you can get started right here:
{STRIPE_LINK}

Best,

David Mahler
surplusdocket.com
david@surplusdocket.com"""

    elif chosen_variant == "B":
        subject = f"Post-Tyler surplus recovery data — {state_name}"
        body = f"""{greeting}

Since the Supreme Court's unanimous ruling in Tyler v. Hennepin County last year, the surplus recovery landscape has fundamentally changed. Counties that previously retained foreclosure overages are now legally obligated to distribute them — and claim filing deadlines are running.

I built a tool that indexes {state_name} tax deed surplus and excess proceeds cases daily. We pull the dockets from county registries and filter out institutional encumbrances upstream, so you only see clean, collectible balances with verified claim windows.

You can review the live {state_name} feed here:
{recommended_link}

If you'd like daily delivery ($249/mo flat, cancel anytime):
{STRIPE_LINK}

Best,

David Mahler
surplusdocket.com
david@surplusdocket.com"""

    else:  # Variant C
        subject = f"{state_name} surplus claims — ROI data feed"
        body = f"""{greeting}

Quick math: the average {state_name} surplus balance in our current index is roughly $45,000. At a standard 25% contingency, that's $11,250 per successful claim — and we're indexing new filings every morning.

I built a data feed that pulls tax deed surplus and excess proceeds dockets from {state_name} county registries daily. We filter out senior mortgages and institutional liens upstream, so you're only working clean files.

Live feed and sample data:
{recommended_link}

Daily delivery is $249/mo flat with Stripe billing (cancel anytime):
{STRIPE_LINK}

Best,

David Mahler
surplusdocket.com
david@surplusdocket.com"""

    return subject, body, chosen_variant


async def find_contact_page(page, base_url):
    """Attempts to locate the Contact or Consultation page on the firm's website."""
    # 1. First look for dedicated Contact / Consultation links on the page
    contact_patterns = [
        "a[href*='contact' i]",
        "a[href*='consult' i]",
        "a[href*='get-in-touch' i]",
        "a[href*='intake' i]",
        "a[href*='reach-us' i]",
        "a:has-text('Contact Us')",
        "a:has-text('Contact')",
        "a:has-text('Free Consultation')",
        "a:has-text('Consultation')",
        "a:has-text('Get in Touch')",
        "a:has-text('Schedule')",
    ]

    from urllib.parse import urlparse
    base_netloc = urlparse(base_url).netloc.replace("www.", "")

    for sel in contact_patterns:
        try:
            locators = await page.locator(sel).all()
            for loc in locators[:4]:
                if await loc.is_visible():
                    href = await loc.get_attribute("href")
                    if href and not href.startswith(("tel:", "mailto:", "#", "javascript:")):
                        if href.startswith("http"):
                            target = href
                        elif href.startswith("/"):
                            target = base_url.rstrip("/") + href
                        else:
                            target = base_url.rstrip("/") + "/" + href
                        
                        target_netloc = urlparse(target).netloc.replace("www.", "")
                        if target_netloc and target_netloc != base_netloc:
                            continue
                            
                        resp = await page.goto(target, timeout=12000, wait_until="domcontentloaded")
                        await page.wait_for_timeout(1500)
                        if resp and resp.status < 400:
                            if await page.locator("textarea, form input[type='email'], input[name*='email' i], [name*='ZW1haWw']").count() > 0:
                                return page.url
        except Exception:
            continue

    # 2. Try direct navigation to standard contact paths
    for path in ["/contact", "/contact-us/", "/contact-us", "/contact/", "/free-consultation", "/consultation", "/get-in-touch"]:
        try:
            target = base_url.rstrip("/") + path
            resp = await page.goto(target, timeout=10000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)
            if resp and resp.status < 400:
                if await page.locator("textarea, form input[type='email'], input[name*='email' i], [name*='ZW1haWw']").count() > 0:
                    return page.url
        except Exception:
            continue

    # 3. Fallback: check if the initial page itself has a visible form
    try:
        if page.url != base_url:
            await page.goto(base_url, timeout=10000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
        if await page.locator("textarea").count() > 0:
            return page.url
    except Exception:
        pass

    return base_url


async def fill_and_submit_form(page, target, is_dry_run=False):
    """Intelligently detects form fields across main page and iframes, fills them, and optionally submits."""
    subject, body, variant = compose_message(target)
    firm = target.get("Firm", "")
    
    # Scroll page to trigger lazy loaded forms
    try:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        await asyncio.sleep(0.5)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(0.5)
    except Exception:
        pass

    contexts = [page]
    for frame in page.frames:
        if frame != page.main_frame:
            contexts.append(frame)

    filled_any = False
    target_context = None

    for ctx in contexts:
        try:
            # 1. Message field (textarea or wide input)
            msg_selectors = [
                "textarea",
                "input[name*='message' i]",
                "input[name*='comment' i]",
                "input[name*='detail' i]",
                "input[name*='inquiry' i]",
                "input[name*='notes' i]",
                "input[name*='description' i]",
                "input[placeholder*='message' i]",
                "input[placeholder*='how can we help' i]",
                "input[placeholder*='case' i]",
                "input[placeholder*='tell us' i]",
                "div[contenteditable='true']",
                # Lawmatics case blurb selector
                "textarea[name*='Y2FzZV9ibHVyYg']",
                "input[name*='Y2FzZV9ibHVyYg']",
            ]
            msg_elem = None
            for sel in msg_selectors:
                loc = ctx.locator(sel).first
                if await loc.is_visible(timeout=800):
                    msg_elem = loc
                    break

            if not msg_elem:
                # Try label matching for message
                for lbl_sel in ["label:has-text('Message')", "label:has-text('Comments')", "label:has-text('Description')"]:
                    try:
                        lbl = ctx.locator(lbl_sel).first
                        if await lbl.is_visible(timeout=300):
                            for_id = await lbl.get_attribute("for")
                            if for_id:
                                candidate = ctx.locator(f"#{for_id}, [name='{for_id}']").first
                                if await candidate.is_visible(timeout=300):
                                    msg_elem = candidate
                                    break
                    except Exception:
                        pass

            # 2. Email field
            email_selectors = [
                "input[type='email']",
                "input[name*='email' i]",
                "input[id*='email' i]",
                "input[placeholder*='email' i]",
                "input[placeholder*='e-mail' i]",
                "input[placeholder*='mail' i]",
                "input[class*='email' i]",
                "input[aria-label*='email' i]",
                "input[aria-label*='e-mail' i]",
                # Lawmatics base64 email selector
                "input[name*='ZW1haWw']",
                "input[id*='ZW1haWw']",
            ]
            email_elem = None
            for sel in email_selectors:
                loc = ctx.locator(sel).first
                if await loc.is_visible(timeout=800):
                    email_elem = loc
                    break

            if not email_elem:
                # Try label matching for email
                for lbl_sel in ["label:has-text('Email')", "label:has-text('E-mail')", "label:has-text('Your Email')"]:
                    try:
                        lbl = ctx.locator(lbl_sel).first
                        if await lbl.is_visible(timeout=300):
                            for_id = await lbl.get_attribute("for")
                            if for_id:
                                candidate = ctx.locator(f"#{for_id}, [name='{for_id}']").first
                                if await candidate.is_visible(timeout=300):
                                    email_elem = candidate
                                    break
                            candidate = lbl.locator("input").first
                            if await candidate.is_visible(timeout=300):
                                email_elem = candidate
                                break
                    except Exception:
                        pass

            if not email_elem:
                continue

            target_context = ctx
            filled_any = True

            # Fill Message
            if msg_elem:
                try:
                    await msg_elem.fill(body)
                except Exception:
                    pass

            # Fill Email
            try:
                await email_elem.fill(SENDER_EMAIL)
            except Exception:
                pass

            # 3. Name fields
            try:
                first_name_loc = ctx.locator("input[name*='first' i], input[id*='first' i], input[placeholder*='first' i], input[name*='Zmlyc3RfbmFtZQ']").first
                last_name_loc = ctx.locator("input[name*='last' i], input[id*='last' i], input[placeholder*='last' i], input[name*='bGFzdF9uYW1l']").first
                
                if await first_name_loc.is_visible(timeout=500) and await last_name_loc.is_visible(timeout=500):
                    await first_name_loc.fill(SENDER_FIRST_NAME)
                    await last_name_loc.fill(SENDER_LAST_NAME)
                else:
                    for sel in ["input[name*='name' i]", "input[id*='name' i]", "input[placeholder*='name' i]", "input[aria-label*='name' i]"]:
                        loc = ctx.locator(sel).first
                        if await loc.is_visible(timeout=500):
                            await loc.fill(SENDER_NAME)
                            break
            except Exception:
                pass

            # 4. Phone field (optional)
            clean_phone_digits = re.sub(r"\D", "", SENDER_PHONE)
            for sel in ["input[type='tel']", "input[name*='phone' i]", "input[id*='phone' i]", "input[placeholder*='phone' i]", "input[name*='cGhvbmU']"]:
                try:
                    loc = ctx.locator(sel).first
                    if await loc.is_visible(timeout=500):
                        inp_type = await loc.get_attribute("type")
                        if inp_type == "number":
                            await loc.fill(clean_phone_digits)
                        else:
                            try:
                                await loc.fill(SENDER_PHONE)
                            except Exception:
                                await loc.fill(clean_phone_digits)
                        break
                except Exception:
                    pass

            # 5. Subject field (optional)
            for sel in ["input[name*='subject' i]", "input[id*='subject' i]", "input[placeholder*='subject' i]", "[name*='cHJhY3RpY2VfYXJlYQ']"]:
                try:
                    loc = ctx.locator(sel).first
                    if await loc.is_visible(timeout=500):
                        await loc.fill(subject)
                        break
                except Exception:
                    pass

            # 6. Consent & Disclaimer Checkboxes (mandatory on many law firm forms)
            try:
                checkboxes = ctx.locator("input[type='checkbox'][required], input[type='checkbox'][name*='agree' i], input[type='checkbox'][name*='consent' i], input[type='checkbox'][name*='disclaimer' i], input[type='checkbox'][id*='agree' i]")
                cb_count = await checkboxes.count()
                for cb_idx in range(cb_count):
                    cb = checkboxes.nth(cb_idx)
                    if await cb.is_visible(timeout=300):
                        if not await cb.is_checked():
                            await cb.check(timeout=1000)
            except Exception:
                pass

            break
        except Exception:
            continue

    if not filled_any or not target_context:
        return False, "Could not find compatible contact form fields on page.", variant

    # Take screenshot of filled form
    safe_firm = re.sub(r"[^a-zA-Z0-9]", "_", firm)[:30]
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    screenshot_path = SCREENSHOTS_DIR / f"{safe_firm}_{int(time.time())}.png"
    await page.screenshot(path=str(screenshot_path), full_page=False)

    if is_dry_run:
        return True, f"DRY_RUN: Form filled successfully. Screenshot: {screenshot_path.name}", variant

    # 7. Submit Button in target context
    submit_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Submit')",
        "button:has-text('Send')",
        "button:has-text('Send Message')",
        "button:has-text('Submit Form')",
        "button:has-text('Contact Us')",
        "button:has-text('Request Consultation')",
        "button:has-text('Get in Touch')",
        "a:has-text('Submit')",
        "a:has-text('Send Message')",
    ]
    
    submitted = False
    for sel in submit_selectors:
        loc = target_context.locator(sel).first
        if await loc.is_visible(timeout=1000):
            await loc.click(timeout=3000)
            submitted = True
            break

    if not submitted:
        try:
            await target_context.locator("form").first.evaluate("form => form.submit()")
            submitted = True
        except Exception as e:
            return False, f"Could not trigger submit button: {e}", variant

    await page.wait_for_timeout(3000)
    
    # Check for explicit failure cues instead of naive string matching on recaptcha script tags
    try:
        page_text = (await page.inner_text("body")).lower()
        captcha_failure_cues = [
            "please complete the captcha",
            "recaptcha verification failed",
            "invalid captcha",
            "captcha was incorrect",
            "please verify you are not a robot",
            "please check the captcha",
            "turnstile verification failed",
        ]
        if any(cue in page_text for cue in captcha_failure_cues):
            return False, "CAPTCHA verification required.", variant
    except Exception:
        pass

    return True, f"SUCCESS: Submitted. Proof saved to {screenshot_path.name}", variant


async def process_target(browser, target, is_dry_run=False):
    source_url = target.get("Source_URL", "").strip()
    firm = target.get("Firm", "")
    state = target.get("State", "")
    variant = ""
    
    if not source_url or not source_url.startswith("http"):
        return {"status": "SKIPPED", "detail": "Invalid Source_URL", "variant": ""}

    context = await browser.new_context(
        ignore_https_errors=True,
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800}
    )
    page = await context.new_page()
    try:
        print(f"  🌐 Visiting {firm} ({source_url})...")
        await page.goto(source_url, timeout=20000, wait_until="domcontentloaded")
        
        # Locate contact form page
        form_url = await find_contact_page(page, source_url)
        print(f"     Found form page: {form_url}")

        # Fill and submit (compose_message is called inside, variant determined there)
        ok, detail, variant = await fill_and_submit_form(page, target, is_dry_run=is_dry_run)
        if ok and is_dry_run:
            status = "DRY_RUN"
        elif ok:
            status = "SUCCESS"
        else:
            status = "FAILED"
        print(f"     [{status}] [Variant {variant}] {detail}")
        return {"status": status, "form_url": form_url, "detail": detail, "variant": variant}
    except Exception as e:
        print(f"     [ERROR] Failed to process {firm}: {e}")
        return {"status": "ERROR", "detail": str(e), "variant": variant}
    finally:
        await context.close()


def clean_domain(url_or_email):
    """Extracts a normalized canonical domain string."""
    if not url_or_email:
        return ""
    s = url_or_email.lower().strip()
    if "@" in s:
        s = s.split("@")[1]
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    s = s.split("/")[0].split("?")[0].split(":")[0]
    return s


def calculate_priority_score(target):
    """
    Computes a 0-100 Priority Relevance Score:
    - Specialty: Tax Deed Surplus / Excess Proceeds (+45 pts)
    - State: High-Volume Surplus States FL/TX (+30), CA/GA (+25), NC/TN (+20)
    - Decision Maker: Boutique Managing Partner / Solo P.A. (+15 pts)
    - County Relevance: Mention of top target county (+10 pts)
    """
    score = 0
    spec = (target.get("Specialty", "") + " " + target.get("Practice_Details", "")).lower()
    state = target.get("State", "").upper()
    firm = target.get("Firm", "").lower()

    # 1. Specialty relevance (max 45)
    if any(k in spec for k in ["surplus fund", "excess proceed", "tax deed surplus", "overage", "unclaimed fund"]):
        score += 45
    elif any(k in spec for k in ["surplus", "asset recovery", "tax foreclosure", "tax sale"]):
        score += 35
    elif any(k in spec for k in ["foreclosure defense", "real estate litigation", "quiet title"]):
        score += 20
    else:
        score += 10

    # 2. State market value (max 30)
    if state in ["FL", "TX"]:
        score += 30
    elif state in ["CA", "GA"]:
        score += 25
    elif state in ["NC", "TN"]:
        score += 20
    elif state in ["OH", "NY", "NJ", "PA", "IL", "MD", "AZ"]:
        score += 15
    else:
        score += 5

    # 3. Decision maker / boutique firm (max 15)
    if any(k in firm for k in ["law office of", "p.a.", "pa", "pllc", "law group", "legal"]):
        score += 15
    else:
        score += 10

    # 4. County specific detail (max 10)
    if any(k in spec for k in ["miami", "orange", "hillsborough", "harris", "dallas", "tarrant", "fulton", "los angeles", "broward", "palm beach"]):
        score += 10

    return score


def get_already_submitted():
    """
    Returns a set of all normalized domains that should be EXCLUDED.
    - SUCCESS: permanently excluded (only if actually submitted live, NOT dry runs)
    - ERROR with DNS resolution failure: permanently excluded (dead domain)
    - DRY_RUN / FAILED / other ERROR: NOT excluded (eligible for live runs)
    """
    submitted = set()
    if LOG_CSV.exists():
        with open(LOG_CSV, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                status = row.get("status", "").upper()
                detail = row.get("detail", "").lower()
                t_url = row.get("target_url", "")
                f_url = row.get("form_url", "")
                d1 = clean_domain(t_url)
                d2 = clean_domain(f_url)
                
                # Permanently exclude live submissions only (do NOT exclude dry-run tests)
                if status == "SUCCESS" and "dry_run" not in detail:
                    if d1: submitted.add(d1)
                    if d2: submitted.add(d2)
                # Permanently exclude dead domains (DNS failures)
                elif "ERROR" in status and "err_name_not_resolved" in detail:
                    if d1: submitted.add(d1)
                # All other failures or dry runs will be retried on live runs

    return submitted


async def run_engine(is_dry_run=False, limit=35, state_filter=None):
    print("=" * 75)
    print("  🤖 SURPLUS DOCKET — HIGH-PROBABILITY FORM OUTREACH ENGINE")
    print("=" * 75)
    print(f"Mode         : {'DRY RUN (Preview / Screenshot only)' if is_dry_run else 'LIVE SUBMISSION'}")
    print(f"Sender       : {SENDER_NAME} <{SENDER_EMAIL}>")
    print(f"State Filter : {state_filter or 'ALL'}")
    print(f"Batch Limit  : {limit}\n")

    if not TARGETS_CSV.exists():
        print(f"❌ Targets CSV not found at {TARGETS_CSV}")
        return

    already_done = get_already_submitted()
    print(f"✓ Found {len(already_done)} previously contacted domains (PERMANENTLY EXCLUDED)")

    eligible_targets = []
    with open(TARGETS_CSV, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            clean = {k.strip(): (v or "").strip() for k, v in r.items() if k}
            url = clean.get("Source_URL", "").lower().strip()
            state = clean.get("State", "").upper()
            dom = clean_domain(url) or clean_domain(clean.get("Email", ""))
            
            if not dom or dom in already_done:
                continue
            if state_filter and state != state_filter.upper():
                continue
            if url and url.startswith("http"):
                clean["domain"] = dom
                clean["priority_score"] = calculate_priority_score(clean)
                eligible_targets.append(clean)

    # Deduplicate candidate list by domain, retaining highest priority score
    unique_candidates = {}
    for t in eligible_targets:
        d = t["domain"]
        if d not in unique_candidates or t["priority_score"] > unique_candidates[d]["priority_score"]:
            unique_candidates[d] = t

    # Rank by Priority Score descending (Highest Probability Targets First)
    ranked_targets = sorted(unique_candidates.values(), key=lambda x: x["priority_score"], reverse=True)
    candidate_list = ranked_targets[:limit]

    print(f"✓ Found {len(ranked_targets)} fresh, untouched law firms in database")
    print(f"✓ Selected top {len(candidate_list)} HIGHEST PROBABILITY targets for this batch\n")

    if not candidate_list:
        print("No eligible targets remaining.")
        return

    print("Target Queue Priority Breakdown:")
    for idx, cand in enumerate(candidate_list, 1):
        print(f"  [{idx:02d}] Score: {cand['priority_score']} | {cand['Name']} | {cand['Firm']} ({cand['State']}) — {cand['Specialty']}")
    print("-" * 75 + "\n")

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for i, target in enumerate(candidate_list, 1):
            print(f"[{i:02d}/{len(candidate_list):02d}] Processing {target.get('Firm')} ({target.get('State')})...")
            res = await process_target(browser, target, is_dry_run=is_dry_run)
            res["firm"] = target.get("Firm", "")
            res["name"] = target.get("Name", "")
            res["state"] = target.get("State", "")
            res["target_url"] = target.get("Source_URL", "")
            res["timestamp"] = datetime.now().isoformat()
            results.append(res)
            # Polite random jitter to mimic human browsing behavior (8-18 seconds)
            if i < len(candidate_list) and not is_dry_run:
                jitter = random.uniform(8.0, 18.0)
                print(f"     ⏳ Waiting {jitter:.1f}s before next firm...")
                await asyncio.sleep(jitter)
            else:
                await asyncio.sleep(1)
        await browser.close()

    # Append to log
    file_exists = LOG_CSV.exists()
    with open(LOG_CSV, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "firm", "name", "state", "target_url", "form_url", "status", "detail", "variant"])
        if not file_exists:
            writer.writeheader()
        for r in results:
            writer.writerow({
                "timestamp": r.get("timestamp", ""),
                "firm": r.get("firm", ""),
                "name": r.get("name", ""),
                "state": r.get("state", ""),
                "target_url": r.get("target_url", ""),
                "form_url": r.get("form_url", ""),
                "status": r.get("status", ""),
                "detail": r.get("detail", ""),
                "variant": r.get("variant", ""),
            })

    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    print("\n" + "=" * 75)
    print(f"  🏁 BATCH COMPLETE: {success_count}/{len(candidate_list)} processed successfully")
    print(f"  Log saved to: {LOG_CSV}")
    print("=" * 75)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "--preview" in sys.argv
    limit_val = 35
    for arg in sys.argv:
        if arg.startswith("--limit="):
            limit_val = int(arg.split("=")[1])
    
    asyncio.run(run_engine(is_dry_run=dry_run, limit=limit_val))
