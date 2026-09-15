# Contributing to Surplus Docket™

Welcome to the Surplus Docket codebase. This document details engineering standards, architectural structure, and verification guidelines for developing on the Surplus Docket autonomous intelligence platform.

---

## 🏛️ Architecture Overview

The system is structured into five decoupled operational domains:

1. **`site/`** — Static front-end hosted on GitHub Pages (`surplusdocket.com`). Includes jurisdictional hubs, practitioner calculators, blog posts, press releases, sitemaps, and legal pages (`terms.html`, `privacy.html`, `refund-policy.html`).
2. **`portal/`** — Subscriber lifecycle, Stripe webhook integration, morning feed generation (`feed_generator.py`), and transactional email dispatchers (`dispatch_morning_feed.py`, `trial_retention_sentinel.py`).
3. **`outreach/`** — Autonomous law firm discovery, ranking, headless Playwright form submission (`form_outreach_engine.py`), and IMAP inbox sentinel (`auto_responder_and_draft_cleaner.py`).
4. **`marketing/`** — Link building (`auto_directory_submitter.py`, `citation_registry.csv`), SEO sitemaps, IndexNow/Ping-O-Matic syndication, and programmatic county page generators.
5. **`compliance/`** — Statutory rule monitors, UPL compliance sentinels, and autonomous self-healing engines (`autonomous_bug_resolver.py`).

---

## 🛡️ Core Engineering Principles

### 1. 100% Test Pass Rate Mandate
Every commit must pass the full test suite before pushing to `main`:
```bash
python3 -m unittest discover -s tests
```
Never disable assertions, delete tests, or commit regressions.

### 2. Zero-Spam / Zero-Bounce Policy
Outreach must comply strictly with anti-spam standards:
- Always run DNS pre-validation before visiting target firm domains.
- Never email dead, non-resolving, or parked broker domains.
- All outbound communications must include statutory disclaimers and honor unsubscribe requests immediately.

### 3. Static & Canonical Quality
All public HTML pages must pass the automated validator:
```bash
python3 scripts/site_health_check.py
```
- Every page must have unique meta descriptions, OpenGraph tags, and canonical links.
- Error/utility pages (e.g. `404.html`) must specify `noindex` and must never self-canonicalize.
- Every legal and transactional link must point to verified live targets.

### 4. Asynchronous & Non-Blocking Execution
- Never call blocking I/O (e.g., synchronous `socket.gethostbyname`) inside an `asyncio` event loop.
- Use `await loop.run_in_executor(None, fn, *args)` when wrapping synchronous networking.
- Use structured logging (`logger = logging.getLogger(__name__)`) instead of unstructured `print()` statements in production services.

### 5. Dependency Supply Chain Hygiene
- Dependencies in `requirements.txt` must be strictly pinned using exact versions (`==`) to guarantee deterministic CI builds.
- Never commit credentials, private keys, or API tokens. Secrets must always be injected via GitHub Actions environment variables (`secrets.GMAIL_APP_PASS`, `secrets.STRIPE_API_KEY`, etc.).

---

## 🧪 Running Tests Locally

Run the complete test suite:
```bash
python3 -m unittest discover -s tests
```

Run specific test suites:
```bash
python3 -m unittest tests/test_form_outreach_hardening.py
python3 -m unittest tests/test_outreach_and_responder.py
python3 -m unittest tests/test_sync_stripe_subscribers.py
```

Run static site health audit:
```bash
python3 scripts/site_health_check.py
```

---

## 🚀 Git & CI/CD Workflow

All automated workflows run via GitHub Actions (`.github/workflows/`):
- Workflows that commit to `main` must use concurrency groups and the clean-before-rebase retry pattern:
  ```bash
  git checkout -- . || true
  git clean -fd || true
  for attempt in 1 2 3; do
    git pull --rebase origin main && git push && break || { sleep 5; }
  done
  ```
- Always ensure working trees are clean prior to pulling or rebasing.
