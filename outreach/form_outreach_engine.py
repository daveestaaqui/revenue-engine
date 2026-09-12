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
import json
import os
import tempfile
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
MASTER_TARGETS_CSV = OUTREACH_DIR / "master_ranked_attorney_targets.csv"
LEGACY_TARGETS_CSV = OUTREACH_DIR / "verified_attorney_targets.csv"
TARGETS_CSV = MASTER_TARGETS_CSV if MASTER_TARGETS_CSV.exists() else LEGACY_TARGETS_CSV
LOG_CSV = OUTREACH_DIR / "form_submissions_log.csv"
SCREENSHOTS_DIR = OUTREACH_DIR / "form_screenshots"

# Sender Info (Default: Surplus Docket Intelligence)
SENDER_NAME = "Surplus Docket Intelligence"
SENDER_FIRST_NAME = "Docket"
SENDER_LAST_NAME = "Intelligence"
SENDER_TITLE = "Court Registry Ingestion Desk"
SENDER_EMAIL = "dockets@surplusdocket.com"
SENDER_PHONE = "508-888-0000"
SITE_URL = "https://surplusdocket.com"
STRIPE_LINK = "https://buy.stripe.com/4gM14n8yq9vl0vrb0i0ZW21"

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


def get_recommended_link(state_code, practice_details, specialty=""):
    spec_lower = (specialty or "").lower()
    details_lower = (practice_details or "").lower()

    # Specialty-specific practice landing pages
    if any(k in spec_lower or k in details_lower for k in ["probate", "estate", "heir", "trust", "administration"]):
        return "https://surplusdocket.com/for/probate-estate-surplus.html"
    if any(k in spec_lower or k in details_lower for k in ["foreclosure", "mortgage", "heloc", "junior lien", "lien"]):
        return "https://surplusdocket.com/for/mortgage-foreclosure.html"

    # County deep links
    for county_kw, url in COUNTY_URLS.items():
        if county_kw in details_lower:
            return url

    # State deep links
    if state_code in STATE_URLS:
        return STATE_URLS[state_code]
    return SITE_URL


# Regulatory & Non-Legal-Advice Disclaimer for Web Form Submissions
FORM_LEGAL_DISCLAIMER = """---
Legal Notice: Surplus Docket is a specialized legal technology and public court records intelligence service, not a law firm. We do not provide legal advice, legal counsel, or legal representation. Feeds and docket records are compiled exclusively for research and intelligence purposes for licensed attorneys."""


def compose_message(target):
    full_name = target.get("Name", "").strip()
    first_name = full_name.split()[0] if full_name else ""
    firm = target.get("Firm", "").strip()
    state_code = target.get("State", "FL").strip().upper()
    state_name = STATE_NAMES.get(state_code, state_code)
    practice_details = target.get("Practice_Details", "")
    specialty = target.get("Specialty", "")

    greeting = f"Hi {first_name}," if first_name else f"Hello {firm} team,"
    recommended_link = get_recommended_link(state_code, practice_details, specialty)

    if target.get("is_refresh"):
        quarter_num = ((datetime.now().month - 1) // 3) + 1
        subject = f"Q{quarter_num} Surplus Docket Intelligence Update — {state_name} Court Registries"
        body = f"""{greeting}

I'm following up from the research desk at Surplus Docket with our quarterly court registry update for {state_name}.

Since our previous outreach, our automated crawlers have indexed substantial new tax deed surplus and excess proceeds filings across {state_name} county courts. As a reminder, we audit and filter out senior mortgages and institutional bank encumbrances upstream so your attorneys only receive clean, actionable equity balances.

You can inspect current live dockets and county metrics here:
{recommended_link}

Your practice can evaluate live morning filings anytime with a 7-day complimentary evaluation ($0 due today, daily 7:00 AM EST feeds, cancel anytime via Stripe portal):
{STRIPE_LINK}

Best regards,

Surplus Docket Intelligence
Court Registry Ingestion Desk | Surplus Docket
surplusdocket.com
dockets@surplusdocket.com"""
        body = f"{body}\n\n{FORM_LEGAL_DISCLAIMER}"
        return subject, body, "Q"

    variants = ["A", "B", "C"]
    chosen_variant = random.choice(variants)
    
    if chosen_variant == "A":
        subject = f"{state_name} surplus & excess proceeds intelligence"
        body = f"""{greeting}

I'm reaching out from the public records research desk at Surplus Docket. We index tax deed surplus and excess proceeds dockets daily across {state_name}.

Most county surplus lists are a headache to work through because the majority of files are encumbered by senior mortgages or bank liens that wipe out the funds. We pull the dockets daily and filter out those institutional liens upstream, so your practice is only looking at clean individual and estate claims.

You can inspect the live {state_name} feed and sample cases directly here:
{recommended_link}

We deliver the standardized feed every morning at 7:00 AM EST (CSV, Excel, JSON). If your practice would like to evaluate live morning filings with a 7-day complimentary practice evaluation ($0 due today, cancel anytime via Stripe portal):
{STRIPE_LINK}

Best regards,

Surplus Docket Intelligence
Court Registry Ingestion Desk | Surplus Docket
surplusdocket.com
dockets@surplusdocket.com"""

    elif chosen_variant == "B":
        subject = f"Post-Tyler surplus recovery data — {state_name}"
        body = f"""{greeting}

Since the Supreme Court's unanimous ruling in Tyler v. Hennepin County, the surplus recovery landscape has fundamentally changed. Counties that previously retained foreclosure overages are now legally obligated to distribute them — and statutory claim filing deadlines are running.

Our data intelligence desk indexes {state_name} tax deed surplus and excess proceeds cases daily. We pull the dockets directly from county registries and filter out institutional encumbrances upstream, so your attorneys only see clean, collectible balances with verified claim windows.

You can review the live {state_name} feed here:
{recommended_link}

We offer a 7-day complimentary practice evaluation for counsel of record ($0 due today with card on file, 7 business days of live 7:00 AM EST morning feeds, cancel anytime via Stripe portal):
{STRIPE_LINK}

Best regards,

Surplus Docket Intelligence
Court Registry Ingestion Desk | Surplus Docket
surplusdocket.com
dockets@surplusdocket.com"""

    else:  # Variant C — Astrid Procedural & Encumbrance Screening Angle
        subject = f"{state_name} court registry surplus & encumbrance screening"
        body = f"""{greeting}

Surplus Docket organizes surplus records from covered {state_name} court registries so legal teams can review source documents, reported amounts, and preliminary lien flags without confusing raw listings with established claims.

Our daily feed distinguishes between administrative tax deed overages and judicial foreclosure funds, helping your attorneys inspect the evidence trail, verify claimant standing, and track statutory response deadlines.

Inspect our source-linked workflow and sample dockets here:
{recommended_link}

Your office can evaluate live morning filings with a 7-day complimentary practice evaluation ($0 due today, $249/mo flat thereafter, cancel anytime via Stripe portal):
{STRIPE_LINK}

Best regards,

Surplus Docket Intelligence
Court Registry Ingestion Desk | Surplus Docket
surplusdocket.com
dockets@surplusdocket.com"""

    body = f"{body}\n\n{FORM_LEGAL_DISCLAIMER}"
    return subject, body, chosen_variant


CHROMIUM_STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-infobars",
    "--disable-dev-shm-usage",
    "--disable-browser-side-navigation",
    "--disable-gpu",
]

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});
"""


def solve_math_question(prompt_text):
    """
    Parses and solves anti-spam arithmetic and logic questions found on contact forms.
    Examples:
    - 'What is 4 + 7?' -> '11'
    - '12 - 3 = ' -> '9'
    - '3 * 4 = ?' -> '12'
    - 'Please enter the sum of 6 and 8' -> '14'
    - 'What color is the sky?' -> 'blue'
    """
    if not prompt_text:
        return None
    text = prompt_text.lower().strip()

    # Addition: e.g. "4 + 7", "what is 4 + 7", "sum of 4 and 7", "4 plus 7"
    m = re.search(r"(\d+)\s*(?:\+|\bplus\b)\s*(\d+)", text)
    if m:
        return str(int(m.group(1)) + int(m.group(2)))
    m = re.search(r"sum\s+of\s+(\d+)\s+(?:and|\+)\s+(\d+)", text)
    if m:
        return str(int(m.group(1)) + int(m.group(2)))

    # Subtraction: e.g. "12 - 5", "12 minus 5"
    m = re.search(r"(\d+)\s*(?:-|\bminus\b)\s*(\d+)", text)
    if m:
        return str(int(m.group(1)) - int(m.group(2)))

    # Multiplication: e.g. "3 * 4", "3 x 4", "3 times 4"
    m = re.search(r"(\d+)\s*(?:\*|x|\btimes\b)\s*(\d+)", text)
    if m:
        return str(int(m.group(1)) * int(m.group(2)))

    # Word-number addition: e.g. "one plus three", "two + four"
    word_to_num = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12
    }
    for w1, n1 in word_to_num.items():
        for w2, n2 in word_to_num.items():
            if f"{w1} + {w2}" in text or f"{w1} plus {w2}" in text:
                return str(n1 + n2)

    # Common anti-spam trivia
    if "color" in text and ("sky" in text or "ocean" in text):
        return "blue"
    if "color" in text and ("grass" in text or "tree" in text):
        return "green"
    if "color" in text and ("fire truck" in text or "apple" in text or "blood" in text):
        return "red"
    if "capital" in text and ("usa" in text or "united states" in text or "america" in text):
        return "Washington"

    return None


async def is_honeypot(locator):
    """
    Checks whether an input element is a hidden bot honeypot trap.
    """
    try:
        if not await locator.is_visible(timeout=300):
            return True
        box = await locator.bounding_box()
        if not box or box["width"] <= 2 or box["height"] <= 2:
            return True
        hidden_state = await locator.evaluate("""el => {
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return 'hidden';
            if (parseInt(style.left) < -1000 || parseInt(style.top) < -1000) return 'offscreen';
            if (el.getAttribute('aria-hidden') === 'true' || el.getAttribute('tabindex') === '-1') return 'inaccessible';
            const attr = (el.name || '') + ' ' + (el.id || '') + ' ' + (el.className || '');
            return attr.toLowerCase();
        }""")
        if hidden_state in ('hidden', 'offscreen', 'inaccessible'):
            return True
        honeypot_terms = ['honeypot', 'honey_pot', 'wpforms-hp', 'gform_honeypot', 'akismet', 'botcheck', 'no_bot']
        if any(term in hidden_state for term in honeypot_terms):
            return True
        return False
    except Exception:
        return False


async def handle_human_verification_widgets(page):
    """
    Detects and interacts with human verification checkbox challenges:
    - Cloudflare Turnstile (challenges.cloudflare.com)
    - Google reCAPTCHA v2 checkbox (recaptcha/api2/anchor)
    - hCaptcha checkbox (hcaptcha.com)
    """
    try:
        # 1. Cloudflare Turnstile
        turnstile_frames = [f for f in page.frames if "challenges.cloudflare.com" in f.url or "turnstile" in f.url]
        for f in turnstile_frames:
            try:
                target = f.locator("input[type='checkbox'], .ctp-checkbox-label, #cf-stage, body").first
                if await target.is_visible(timeout=1000):
                    await target.hover()
                    await asyncio.sleep(0.3)
                    await target.click()
                    await asyncio.sleep(2.0)
            except Exception:
                pass

        # 2. Google reCAPTCHA v2 Checkbox
        recaptcha_frames = [f for f in page.frames if "google.com/recaptcha" in f.url and "anchor" in f.url]
        for f in recaptcha_frames:
            try:
                anchor = f.locator("#recaptcha-anchor, .recaptcha-checkbox-border").first
                if await anchor.is_visible(timeout=1000):
                    aria_checked = await anchor.get_attribute("aria-checked")
                    if aria_checked != "true":
                        await anchor.hover()
                        await asyncio.sleep(0.4)
                        await anchor.click()
                        await asyncio.sleep(2.5)
            except Exception:
                pass

        # 3. hCaptcha Checkbox
        hcaptcha_frames = [f for f in page.frames if "hcaptcha.com" in f.url and "checkbox" in f.url]
        for f in hcaptcha_frames:
            try:
                cb = f.locator("#checkbox, .anchor").first
                if await cb.is_visible(timeout=1000):
                    await cb.hover()
                    await asyncio.sleep(0.3)
                    await cb.click()
                    await asyncio.sleep(2.0)
            except Exception:
                pass
    except Exception:
        pass


async def handle_dropdowns_and_radios(ctx):
    """
    Intelligently selects practice area / consultation dropdowns and radio buttons.
    """
    # 1. Dropdowns (<select>)
    try:
        selects = ctx.locator("select")
        sel_count = await selects.count()
        for idx in range(sel_count):
            sel = selects.nth(idx)
            if not await sel.is_visible(timeout=300) or await is_honeypot(sel):
                continue
            
            # Read options
            options = await sel.locator("option").all()
            if not options:
                continue

            chosen_val = None
            priority_terms = ["surplus", "excess proceeds", "tax deed", "foreclosure", "real estate", "litigation", "civil", "property", "consultation", "other", "general"]
            
            for opt in options:
                val = await opt.get_attribute("value") or ""
                text = (await opt.inner_text()).lower().strip()
                if any(term in text or term in val.lower() for term in priority_terms):
                    chosen_val = val or text
                    break
            
            if chosen_val:
                try:
                    await sel.select_option(value=chosen_val)
                except Exception:
                    try:
                        await sel.select_option(label=chosen_val)
                    except Exception:
                        pass
            elif len(options) > 1:
                try:
                    await sel.select_option(index=1)
                except Exception:
                    pass
    except Exception:
        pass

    # 2. Radio buttons
    try:
        radios = ctx.locator("input[type='radio']")
        r_count = await radios.count()
        if r_count > 0:
            for idx in range(r_count):
                r = radios.nth(idx)
                if not await r.is_visible(timeout=300) or await is_honeypot(r):
                    continue
                name = (await r.get_attribute("name") or "").lower()
                val = (await r.get_attribute("value") or "").lower()
                label_text = ""
                try:
                    r_id = await r.get_attribute("id")
                    if r_id:
                        lbl = ctx.locator(f"label[for='{r_id}']").first
                        if await lbl.is_visible(timeout=200):
                            label_text = (await lbl.inner_text()).lower()
                except Exception:
                    pass

                # If asking "existing client?", select "No" or "New Client"
                if "client" in name or "existing" in name or "client" in label_text:
                    if "no" in val or "new" in val or "no" in label_text or "new" in label_text:
                        await r.check(timeout=500)
                        break
    except Exception:
        pass


async def handle_anti_spam_math_questions(ctx):
    """
    Detects math captcha or verification inputs, solves the arithmetic question, and fills it.
    """
    captcha_selectors = [
        "input[name*='captcha' i]",
        "input[name*='math' i]",
        "input[name*='quiz' i]",
        "input[name*='question' i]",
        "input[id*='captcha' i]",
        "input[id*='math' i]",
        "input[placeholder*='=']",
        "input[name*='verify' i]",
        "input[name*='sum' i]",
        "input[name*='security' i]",
    ]
    for sel in captcha_selectors:
        try:
            locs = await ctx.locator(sel).all()
            for loc in locs:
                if not await loc.is_visible(timeout=300) or await is_honeypot(loc):
                    continue
                prompt_text = await loc.get_attribute("placeholder") or ""
                if not prompt_text or "=" not in prompt_text:
                    loc_id = await loc.get_attribute("id")
                    if loc_id:
                        lbl = ctx.locator(f"label[for='{loc_id}']").first
                        if await lbl.is_visible(timeout=300):
                            prompt_text = await lbl.inner_text()
                if not prompt_text:
                    prompt_text = await loc.evaluate("el => el.parentElement ? el.parentElement.innerText : ''")

                ans = solve_math_question(prompt_text)
                if ans:
                    await loc.fill(ans)
                    print(f"     🧮 Solved anti-spam challenge '{prompt_text.strip()}': {ans}")
                    break
        except Exception:
            continue


async def has_form_elements(page):
    """Checks if page or any of its child frames contains visible contact form fields."""
    try:
        for frame in page.frames:
            try:
                # Textarea
                if await frame.locator("textarea").count() > 0:
                    return True
                # Email inputs
                if await frame.locator("input[type='email'], input[name*='email' i], [name*='ZW1haWw'], input[placeholder*='email' i], input.wpforms-field-email, input.ginput_email").count() > 0:
                    return True
                # Forms with submit buttons
                if await frame.locator("form button[type='submit'], form input[type='submit']").count() > 0:
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


async def find_contact_page(page, base_url, explicit_form_url=None):
    """Attempts to locate the Contact or Consultation page on the firm's website."""
    from urllib.parse import urlparse
    base_netloc = urlparse(base_url).netloc.replace("www.", "")

    # 1. First priority: if target already has an explicit Form_URL, navigate directly
    if explicit_form_url and explicit_form_url.startswith("http"):
        try:
            resp = await page.goto(explicit_form_url, timeout=12000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
            if resp and resp.status < 400 and await has_form_elements(page):
                return page.url
        except Exception:
            pass

    # 2. Check if current page (e.g. homepage) already contains a visible contact form
    try:
        if page.url != base_url:
            resp = await page.goto(base_url, timeout=10000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
        if await has_form_elements(page):
            return page.url
    except Exception:
        pass

    # 3. Look for dedicated Contact / Consultation links on the page
    contact_patterns = [
        "a[href*='contact' i]",
        "a[href*='consult' i]",
        "a[href*='get-in-touch' i]",
        "a[href*='intake' i]",
        "a[href*='reach-us' i]",
        "a[href*='locations' i]",
        "a:has-text('Contact Us')",
        "a:has-text('Contact')",
        "a:has-text('Free Consultation')",
        "a:has-text('Consultation')",
        "a:has-text('Get in Touch')",
        "a:has-text('Schedule')",
    ]

    candidate_links = []
    for sel in contact_patterns:
        try:
            locators = await page.locator(sel).all()
            for loc in locators[:6]:
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
                    if target not in candidate_links:
                        candidate_links.append(target)
        except Exception:
            continue

    for target in candidate_links[:5]:
        try:
            resp = await page.goto(target, timeout=10000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1200)
            if resp and resp.status < 400 and await has_form_elements(page):
                return page.url
        except Exception:
            continue

    # 4. Try direct navigation to standard contact paths
    for path in ["/contact", "/contact-us/", "/contact-us", "/contact/", "/free-consultation", "/consultation", "/get-in-touch", "/contact-us-lawyer/", "/contact-us-lawyer", "/locations"]:
        try:
            target = base_url.rstrip("/") + path
            resp = await page.goto(target, timeout=9000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1200)
            if resp and resp.status < 400 and await has_form_elements(page):
                return page.url
        except Exception:
            continue

    return page.url or base_url


async def fill_and_submit_form(page, target, is_dry_run=False):
    """Intelligently detects form fields across main page and iframes, fills them, and optionally submits."""
    subject, body, variant = compose_message(target)
    firm = target.get("Firm", "")

    # Wait for dynamic frames/scripts to initialize
    await page.wait_for_timeout(1000)

    # 0. Attempt human verification widgets first (Cloudflare Turnstile, reCAPTCHA, etc.)
    await handle_human_verification_widgets(page)

    # Scroll page to trigger lazy loaded forms
    try:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
        await asyncio.sleep(0.3)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 2 / 3)")
        await asyncio.sleep(0.3)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.3)
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
            # 1. Message field (textarea or wide input across WP, Gravity, CF7, Elementor, Lawmatics)
            msg_selectors = [
                "textarea",
                "textarea[name^='input_']",
                "textarea[name*='wpforms']",
                "textarea[name*='your-message' i]",
                "textarea[name*='form_fields' i]",
                "textarea[name*='item_meta' i]",
                "textarea[name*='Y2FzZV9ibHVyYg']",
                "input[name*='Y2FzZV9ibHVyYg']",
                "div[contenteditable='true']",
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
            ]
            msg_elem = None
            for sel in msg_selectors:
                loc = ctx.locator(sel).first
                if await loc.is_visible(timeout=500):
                    if await is_honeypot(loc):
                        continue
                    msg_elem = loc
                    break

            if not msg_elem:
                # Try label matching for message (including parent container and sibling inputs)
                for lbl_sel in [
                    "label:has-text('Message')", "label:has-text('Comments')",
                    "label:has-text('Description')", "label:has-text('Inquiry')",
                    "label:has-text('Case Description')", "label:has-text('How Can We Help')"
                ]:
                    try:
                        lbl = ctx.locator(lbl_sel).first
                        if await lbl.is_visible(timeout=200):
                            for_id = await lbl.get_attribute("for")
                            if for_id:
                                candidate = ctx.locator(f"#{for_id}, [name='{for_id}']").first
                                if await candidate.is_visible(timeout=200) and not await is_honeypot(candidate):
                                    msg_elem = candidate
                                    break
                            candidate = lbl.locator("textarea, input").first
                            if await candidate.is_visible(timeout=200) and not await is_honeypot(candidate):
                                msg_elem = candidate
                                break
                            # Sibling textarea in parent wrapper (.form-group, .gfield, .wpforms-field, etc.)
                            try:
                                candidate = lbl.locator("xpath=..//textarea").first
                                if await candidate.is_visible(timeout=200) and not await is_honeypot(candidate):
                                    msg_elem = candidate
                                    break
                            except Exception:
                                pass
                    except Exception:
                        pass

            # Universal Message Fallback: any visible non-honeypot textarea in context
            if not msg_elem:
                try:
                    all_textareas = await ctx.locator("textarea").all()
                    for ta in all_textareas:
                        if await ta.is_visible(timeout=200) and not await is_honeypot(ta):
                            msg_elem = ta
                            break
                except Exception:
                    pass

            # 2. Email field (standard, WordPress, CF7, Gravity, WPForms, Elementor, Lawmatics)
            email_selectors = [
                "input[type='email']",
                "input[autocomplete='email']",
                "input[name*='email' i]",
                "input[id*='email' i]",
                "input[placeholder*='email' i]",
                "input[placeholder*='e-mail' i]",
                "input[placeholder*='mail' i]",
                "input[class*='email' i]",
                "input[aria-label*='email' i]",
                "input[aria-label*='e-mail' i]",
                "input[name*='your-email' i]",
                "input[name*='ZW1haWw']",
                "input[id*='ZW1haWw']",
                "input.wpforms-field-email",
                "input[name*='wpforms'][name*='email' i]",
                "input.ginput_email",
                "div.ginput_container_email input",
                "input[name*='form_fields'][type='email']",
                "input[name*='item_meta'][type='email']",
            ]
            email_elem = None
            for sel in email_selectors:
                loc = ctx.locator(sel).first
                if await loc.is_visible(timeout=500):
                    if await is_honeypot(loc):
                        continue
                    email_elem = loc
                    break

            if not email_elem:
                # Try label matching for email (for ID, child, and parent container sibling)
                for lbl_sel in ["label:has-text('Email')", "label:has-text('E-mail')", "label:has-text('Your Email')", "label:has-text('Email Address')"]:
                    try:
                        lbl = ctx.locator(lbl_sel).first
                        if await lbl.is_visible(timeout=200):
                            for_id = await lbl.get_attribute("for")
                            if for_id:
                                candidate = ctx.locator(f"#{for_id}, [name='{for_id}']").first
                                if await candidate.is_visible(timeout=200) and not await is_honeypot(candidate):
                                    email_elem = candidate
                                    break
                            candidate = lbl.locator("input").first
                            if await candidate.is_visible(timeout=200) and not await is_honeypot(candidate):
                                email_elem = candidate
                                break
                            # Sibling input in parent container (.form-group, .gfield, .wpforms-field, etc.)
                            try:
                                candidate = lbl.locator("xpath=..//input[not(@type='hidden') and not(@type='submit') and not(@type='checkbox') and not(@type='radio')]").first
                                if await candidate.is_visible(timeout=200) and not await is_honeypot(candidate):
                                    email_elem = candidate
                                    break
                            except Exception:
                                pass
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

            # 3. Name fields (First / Last or Full Name across Gravity, WPForms, CF7, Elementor)
            try:
                first_name_loc = ctx.locator(
                    "input[name*='first' i], input[id*='first' i], input[placeholder*='first' i], "
                    "input[name*='fname' i], input[id*='fname' i], input[autocomplete='given-name'], "
                    "input[name*='Zmlyc3RfbmFtZQ'], input.wpforms-field-name-first, input[name$='.3']"
                ).first
                last_name_loc = ctx.locator(
                    "input[name*='last' i], input[id*='last' i], input[placeholder*='last' i], "
                    "input[name*='lname' i], input[id*='lname' i], input[autocomplete='family-name'], "
                    "input[name*='bGFzdF9uYW1l'], input.wpforms-field-name-last, input[name$='.6']"
                ).first

                if await first_name_loc.is_visible(timeout=300) and await last_name_loc.is_visible(timeout=300):
                    if not await is_honeypot(first_name_loc) and not await is_honeypot(last_name_loc):
                        await first_name_loc.fill(SENDER_FIRST_NAME)
                        await last_name_loc.fill(SENDER_LAST_NAME)
                else:
                    name_selectors = [
                        "input[name*='your-name' i]",
                        "input[autocomplete='name']",
                        "input[name='name' i]", "input[id='name' i]",
                        "input[name*='full_name' i]", "input[name*='fullname' i]",
                        "input[name*='contact_name' i]", "input[placeholder*='name' i]",
                        "input[aria-label*='name' i]", "input.wpforms-field-name",
                        "div.ginput_container_name input[type='text']",
                        "input[name*='name' i]"
                    ]
                    name_filled = False
                    for sel in name_selectors:
                        loc = ctx.locator(sel).first
                        if await loc.is_visible(timeout=300) and not await is_honeypot(loc):
                            await loc.fill(SENDER_NAME)
                            name_filled = True
                            break

                    if not name_filled:
                        # Label matching for Name
                        for n_lbl in ["label:has-text('Name')", "label:has-text('Full Name')", "label:has-text('Your Name')"]:
                            try:
                                lbl = ctx.locator(n_lbl).first
                                if await lbl.is_visible(timeout=200):
                                    for_id = await lbl.get_attribute("for")
                                    if for_id:
                                        cand = ctx.locator(f"#{for_id}, [name='{for_id}']").first
                                        if await cand.is_visible(timeout=200) and not await is_honeypot(cand):
                                            await cand.fill(SENDER_NAME)
                                            break
                                    cand = lbl.locator("xpath=..//input[not(@type='hidden') and not(@type='submit') and not(@type='checkbox') and not(@type='radio')]").first
                                    if await cand.is_visible(timeout=200) and not await is_honeypot(cand):
                                        await cand.fill(SENDER_NAME)
                                        break
                            except Exception:
                                pass
            except Exception:
                pass

            # 4. Phone field (optional)
            clean_phone_digits = re.sub(r"\D", "", SENDER_PHONE)
            phone_selectors = [
                "input[type='tel']", "input[autocomplete='tel']",
                "input[name*='phone' i]", "input[id*='phone' i]", "input[placeholder*='phone' i]",
                "input[name*='your-tel' i]", "input[name*='your-phone' i]",
                "input[name*='cGhvbmU']", "input.wpforms-field-phone",
                "div.ginput_container_phone input", "input[name*='tel' i]"
            ]
            for sel in phone_selectors:
                try:
                    loc = ctx.locator(sel).first
                    if await loc.is_visible(timeout=300) and not await is_honeypot(loc):
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
            subject_selectors = [
                "input[name*='subject' i]", "input[id*='subject' i]", "input[placeholder*='subject' i]",
                "input[name*='your-subject' i]", "[name*='cHJhY3RpY2VfYXJlYQ']"
            ]
            for sel in subject_selectors:
                try:
                    loc = ctx.locator(sel).first
                    if await loc.is_visible(timeout=300) and not await is_honeypot(loc):
                        await loc.fill(subject)
                        break
                except Exception:
                    pass

            # 6. Practice Area Dropdowns & Radio selections
            await handle_dropdowns_and_radios(ctx)

            # 7. Anti-Spam Arithmetic / Logic Challenge Solvers
            await handle_anti_spam_math_questions(ctx)

            # 8. Consent & Disclaimer Checkboxes (mandatory on many law firm forms)
            try:
                cb_locators = await ctx.locator("input[type='checkbox']").all()
                for cb in cb_locators:
                    if not await cb.is_visible(timeout=100) or await is_honeypot(cb):
                        continue
                    is_req = await cb.get_attribute("required") is not None or await cb.get_attribute("aria-required") == "true"
                    cb_name = (await cb.get_attribute("name") or "").lower()
                    cb_id = (await cb.get_attribute("id") or "").lower()
                    cb_text = ""
                    if cb_id:
                        try:
                            lbl = ctx.locator(f"label[for='{cb_id}']").first
                            if await lbl.is_visible(timeout=100):
                                cb_text = (await lbl.inner_text()).lower()
                        except Exception:
                            pass
                    if not cb_text:
                        try:
                            cb_text = (await cb.evaluate("el => el.parentElement ? el.parentElement.innerText : ''")).lower()
                        except Exception:
                            pass

                    keywords = ["agree", "consent", "disclaimer", "terms", "privacy", "policy", "accept", "ack", "relationship", "sms", "communication"]
                    if is_req or any(k in cb_name or k in cb_id or k in cb_text for k in keywords):
                        if not await cb.is_checked():
                            await cb.check(timeout=500)
            except Exception:
                pass

            break
        except Exception:
            continue

    if not filled_any or not target_context:
        return False, "Could not find compatible contact form fields on page.", variant

    # 9. Handle any active human verification challenge (Turnstile, reCAPTCHA v2)
    await handle_human_verification_widgets(page)

    # Take screenshot of filled form
    safe_firm = re.sub(r"[^a-zA-Z0-9]", "_", firm)[:30]
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    screenshot_directory = SCREENSHOTS_DIR / "preview" if is_dry_run else SCREENSHOTS_DIR
    screenshot_directory.mkdir(parents=True, exist_ok=True)
    screenshot_path = screenshot_directory / f"{safe_firm}_{int(time.time())}.png"
    await page.screenshot(path=str(screenshot_path), full_page=False)

    if is_dry_run:
        return True, f"DRY_RUN: Form filled successfully. Screenshot: {screenshot_path.name}", variant

    # 10. Multi-step progression check (if form has 'Next' or 'Continue' before submit)
    for next_sel in ["button:has-text('Next')", "input[value*='Next' i]", "button:has-text('Continue')", "a:has-text('Next')"]:
        try:
            n_loc = target_context.locator(next_sel).first
            if await n_loc.is_visible(timeout=300) and not await is_honeypot(n_loc):
                await n_loc.click(timeout=2000)
                await page.wait_for_timeout(1500)
                break
        except Exception:
            pass

    # 11. Submit Button in target context
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
    
    before_submission = (await page.inner_text("body")).lower()
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

    confirmations = ("thank you for contacting", "your message has been sent", "we have received your message", "form has been submitted")
    after_submission = (await page.inner_text("body")).lower()
    if not any(cue in after_submission and cue not in before_submission for cue in confirmations):
        return False, "UNCONFIRMED: Submission attempted; delivery requires manual review. Do not retry automatically.", variant
    await page.screenshot(path=str(screenshot_path), full_page=False)
    return True, f"SUCCESS: Confirmation detected. Proof saved to {screenshot_path.name}", variant


async def process_target(browser, target, is_dry_run=False):
    source_url = target.get("Source_URL", "").strip()
    explicit_form_url = target.get("Form_URL", "").strip()
    firm = target.get("Firm", "")
    variant = ""
    
    if not source_url or not source_url.startswith("http"):
        return {"status": "SKIPPED", "detail": "Invalid Source_URL", "variant": ""}

    context = await browser.new_context(
        ignore_https_errors=True,
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
        locale="en-US",
        timezone_id="America/New_York",
    )
    await context.add_init_script(STEALTH_INIT_SCRIPT)
    page = await context.new_page()
    try:
        # Check initial domain broker
        for bp in ["hugedomains.com", "dan.com", "sedo.com", "afternic.com", "godaddy.com/domainsearch"]:
            if bp in source_url.lower() or bp in explicit_form_url.lower():
                return {"status": "ERROR", "detail": "Domain expired / parked broker page", "variant": ""}

        print(f"  🌐 Visiting {firm} ({source_url})...")
        # Locate contact form page (using explicit Form_URL first if available)
        form_url = await find_contact_page(page, source_url, explicit_form_url=explicit_form_url)
        print(f"     Found form page: {form_url}")

        # Check if landed on domain broker page
        for bp in ["hugedomains.com", "dan.com", "sedo.com", "afternic.com", "godaddy.com/domainsearch"]:
            if bp in page.url.lower():
                return {"status": "ERROR", "form_url": page.url, "detail": "Domain expired / redirected to broker", "variant": ""}

        # Fill and submit (compose_message is called inside, variant determined there)
        ok, detail, variant = await fill_and_submit_form(page, target, is_dry_run=is_dry_run)
        if ok and is_dry_run:
            status = "DRY_RUN"
        elif ok:
            status = "SUCCESS"
        else:
            status = "UNCONFIRMED" if detail.startswith("UNCONFIRMED:") else "FAILED"
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


def get_submission_history(cooldown_days=90):
    """
    Analyzes LOG_CSV to categorize contacted domains:
    - dead_domains: set of domains that had fatal DNS/broker errors (permanently excluded)
    - latest_success: dict mapping clean domain -> latest live SUCCESS datetime
    """
    dead_domains = set()
    latest_success = {}

    if LOG_CSV.exists():
        with open(LOG_CSV, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                status = row.get("status", "").upper()
                detail = row.get("detail", "").lower()
                t_url = row.get("target_url", "")
                f_url = row.get("form_url", "")
                d1 = clean_domain(t_url)
                d2 = clean_domain(f_url)
                timestamp_str = row.get("timestamp", "")

                # Permanently exclude dead / broker domains
                if "ERROR" in status and any(err in detail for err in ["err_name_not_resolved", "broker", "hugedomains", "expired", "dan.com", "sedo.com"]):
                    if d1: dead_domains.add(d1)
                    if d2: dead_domains.add(d2)
                    continue

                # Live successful submissions
                if status in ("SUCCESS", "UNCONFIRMED") and "dry_run" not in detail:
                    dt = None
                    if timestamp_str:
                        try:
                            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                            if dt.tzinfo:
                                dt = dt.replace(tzinfo=None)
                        except Exception:
                            try:
                                dt = datetime.strptime(timestamp_str[:10], "%Y-%m-%d")
                            except Exception:
                                pass
                    if not dt:
                        dt = datetime.now()

                    for dom in [d1, d2]:
                        if dom:
                            if dom not in latest_success or dt > latest_success[dom]:
                                latest_success[dom] = dt

    return dead_domains, latest_success


def get_already_submitted(cooldown_days=90):
    """
    Returns a set of all normalized domains that should be EXCLUDED from current batches:
    - dead/broker domains (permanently excluded)
    - domains submitted successfully within cooldown_days (default: 90 days)
    """
    dead_domains, latest_success = get_submission_history(cooldown_days=cooldown_days)
    now = datetime.now()
    excluded = set(dead_domains)
    for dom, dt in latest_success.items():
        if (now - dt).days < cooldown_days:
            excluded.add(dom)
    return excluded


def browser_name():
    override = os.getenv("OUTREACH_BROWSER")
    name = override or ("chromium" if os.getenv("CI") == "true" or sys.platform != "darwin" else "webkit")
    if name not in ("chromium", "webkit"):
        raise ValueError("OUTREACH_BROWSER must be chromium or webkit")
    return name


async def launch_browser(playwright):
    name = browser_name()
    options = {"headless": True}
    if name == "chromium":
        options["args"] = CHROMIUM_STEALTH_ARGS
    return await getattr(playwright, name).launch(**options)


def summarize_results(results, dry_run=False):
    successes = sum(r.get("status") == ("DRY_RUN" if dry_run else "SUCCESS") for r in results)
    return {"mode": "dry_run" if dry_run else "live", "attempted": len(results),
            "confirmed_submissions": 0 if dry_run else successes,
            "previews": successes if dry_run else 0, "unsuccessful": len(results)-successes,
            "exit_code": 1 if results and not successes else 0}


async def browser_smoke():
    """Exercise real form filling against an owned in-memory fixture only."""
    global SCREENSHOTS_DIR
    with tempfile.TemporaryDirectory() as directory:
        SCREENSHOTS_DIR = Path(directory)
        async with async_playwright() as playwright:
            browser = await launch_browser(playwright)
            context = await browser.new_context()
            await context.route("**/*", lambda route: route.abort())
            page = await context.new_page()
            await page.set_content("""<form onsubmit="window.submitted=true; return false">
              <input name="name" placeholder="Name"><input name="email" type="email">
              <textarea name="message"></textarea><button type="submit">Send</button></form>""")
            ok, detail, _ = await fill_and_submit_form(page, {"Firm": "Owned Test Fixture", "State": "FL"}, is_dry_run=True)
            assert ok and detail.startswith("DRY_RUN"), detail
            assert not await page.evaluate("Boolean(window.submitted)"), "Dry run submitted the form"
            await browser.close()
    print(json.dumps({"browser": browser_name(), "dry_run_fixture": "passed", "external_submissions": 0}))


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
        raise FileNotFoundError(TARGETS_CSV)

    dead_domains, latest_success = get_submission_history(cooldown_days=90)
    now = datetime.now()
    print(f"✓ Found {len(dead_domains)} permanently dead domains and {len(latest_success)} historical live submissions")

    # 1. Load verified real domains & firms from verified_attorney_targets.csv
    verified_domains = set()
    verified_firms = set()
    if LEGACY_TARGETS_CSV.exists():
        with open(LEGACY_TARGETS_CSV, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                u = r.get("Source_URL", "")
                d = clean_domain(u) or clean_domain(r.get("Email", ""))
                if d: verified_domains.add(d)
                fn = r.get("Firm", "").strip().lower()
                if fn: verified_firms.add(fn)

    eligible_targets = []
    with open(TARGETS_CSV, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            clean = {k.strip(): (v or "").strip() for k, v in r.items() if k}
            url = clean.get("Source_URL", "").lower().strip()
            state = clean.get("State", "").upper()
            dom = clean_domain(url) or clean_domain(clean.get("Email", "")) or clean_domain(clean.get("Contact_Email", ""))
            
            if not dom or dom in dead_domains:
                continue

            days_since = None
            is_refresh = False
            if dom in latest_success:
                days_since = (now - latest_success[dom]).days
                if days_since < 90:
                    continue  # Active within 90-day cooldown window
                is_refresh = True

            if state_filter and state != state_filter.upper():
                continue
            if url and url.startswith("http"):
                clean["domain"] = dom
                is_ver = (clean.get("Verified_Status") == "VERIFIED_ACTIVE") or (dom in verified_domains) or (clean.get("Firm", "").strip().lower() in verified_firms)
                clean["is_verified"] = is_ver
                clean["is_refresh"] = is_refresh
                clean["days_since"] = days_since if days_since is not None else 9999
                raw_score = clean.get("Conversion_Score")
                clean["priority_score"] = float(raw_score) if raw_score else calculate_priority_score(clean)
                eligible_targets.append(clean)

    # Deduplicate candidate list by domain
    unique_candidates = {}
    for t in eligible_targets:
        d = t["domain"]
        if d not in unique_candidates:
            unique_candidates[d] = t
        else:
            prev = unique_candidates[d]
            # Priority tuple: (0 if refresh else 1, 1 if verified else 0, priority_score)
            prev_rank = (0 if prev["is_refresh"] else 1, 1 if prev["is_verified"] else 0, prev["priority_score"])
            curr_rank = (0 if t["is_refresh"] else 1, 1 if t["is_verified"] else 0, t["priority_score"])
            if curr_rank > prev_rank:
                unique_candidates[d] = t

    # Rank: 100% FRESH uncontacted firms first, verified firms first, then longest elapsed refresh, then priority score
    ranked_targets = sorted(
        unique_candidates.values(),
        key=lambda x: (
            0 if x["is_refresh"] else 1,
            1 if x.get("is_verified") else 0,
            x["days_since"] if x["is_refresh"] else 0,
            x["priority_score"]
        ),
        reverse=True
    )
    candidate_list = ranked_targets[:limit]

    fresh_count = sum(1 for t in candidate_list if not t.get("is_refresh"))
    refresh_count = sum(1 for t in candidate_list if t.get("is_refresh"))
    verified_count = sum(1 for t in candidate_list if t.get("is_verified"))
    total_fresh = sum(1 for t in unique_candidates.values() if not t.get("is_refresh"))
    total_refresh = sum(1 for t in unique_candidates.values() if t.get("is_refresh"))

    print(f"✓ Found {len(unique_candidates)} total actionable law firms in database ({total_fresh} FRESH UNTOUCHED, {total_refresh} 90-DAY REFRESH)")
    print(f"✓ Selected top {len(candidate_list)} targets for this batch: {fresh_count} FRESH, {refresh_count} 90-DAY REFRESH ({verified_count} VERIFIED REAL FIRMS)\n")

    if not candidate_list:
        print("No eligible targets remaining.")
        return

    print("Target Queue Priority Breakdown:")
    for idx, cand in enumerate(candidate_list, 1):
        v_tag = "[VERIFIED REAL]" if cand.get("is_verified") else "[UNVERIFIED]"
        r_tag = f"[90D REFRESH - {cand['days_since']}d]" if cand.get("is_refresh") else "[FRESH UNCONTACTED]"
        print(f"  [{idx:02d}] {v_tag} {r_tag} Score: {cand['priority_score']} | {cand['Name']} | {cand['Firm']} ({cand['State']}) — {cand['Specialty']}")
    print("-" * 75 + "\n")

    results = []
    async with async_playwright() as p:
        browser = await launch_browser(p)
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

    # Preview data must never enter the production outreach ledger.
    log_path = OUTREACH_DIR / "preview_artifacts" / "form_submissions_log.csv" if is_dry_run else LOG_CSV
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = log_path.exists()
    with open(log_path, "a", encoding="utf-8", newline="") as f:
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

    summary = summarize_results(results, is_dry_run)
    success_count = summary["previews"] if is_dry_run else summary["confirmed_submissions"]
    print("\n" + "=" * 75)
    print(f"  🏁 BATCH COMPLETE: {success_count}/{len(candidate_list)} processed successfully")
    print(f"  Log saved to: {log_path}")
    print(json.dumps(summary, sort_keys=True))
    print("=" * 75)
    return summary["exit_code"]


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "--preview" in sys.argv
    limit_val = 24
    for arg in sys.argv:
        if arg.startswith("--limit="):
            limit_val = int(arg.split("=")[1])
    
    if limit_val < 1 or limit_val > 100:
        raise SystemExit("Batch limit must be between 1 and 100")
    if "--browser-smoke" in sys.argv:
        if not dry_run:
            raise SystemExit("--browser-smoke requires --dry-run")
        asyncio.run(browser_smoke())
    else:
        raise SystemExit(asyncio.run(run_engine(is_dry_run=dry_run, limit=limit_val)) or 0)
