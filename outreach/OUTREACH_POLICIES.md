# Surplus Docket — Inbound Email & Draft Generation Policy
**Document ID:** SD-POL-OUTREACH-2026-V1  
**Enforcement Engine:** `outreach/auto_responder_and_draft_cleaner.py`  
**Effective Date:** September 5, 2026  
**Persona In Effect:** Elena Brooks, Senior Docket Specialist (`elena.brooks@surplusdocket.com`)

---

## 1. Objective & Philosophy
Surplus Docket provides institutional public records intelligence to legal practitioners handling tax deed and foreclosure excess proceeds. Automated draft generation exists solely to accelerate high-level, context-aware responses to **genuine law firm prospects and statutory inquiries**.

Under no circumstances should drafts ever be generated for:
1. Automated system notifications, infrastructure providers, or platforms.
2. Internal administrative or verification emails.
3. Senders not originating from our validated target database or statutory inquiry portal.

---

## 2. Policy Matrix: Inbound Message Eligibility

### Rule 2.1 — Strict Target Verification
A message is eligible for draft reply creation **ONLY IF** it satisfies at least one of the following criteria:
1. **Verified Law Firm Target:** The sender's domain or email address exists in:
   - `outreach/master_ranked_attorney_targets.csv`
   - `outreach/verified_attorney_targets.csv`
   - `outreach/form_submissions_log.csv`
2. **Verified Statutory Website Inquiry:** The message is a structured submission originating from `surplusdocket.com/inquiry.html` containing an official tracking reference (`SD-INQ-...`).

*All other senders are strictly filtered out without draft generation.*

---

### Rule 2.2 — Hard Domain & Sender Blocklist
Draft generation is **permanently blocked** if the sender matches any of the following:

| Category | Excluded Patterns / Domains |
| :--- | :--- |
| **Email & Tech Infrastructure** | `google.com`, `gmail.com`, `googlemail.com`, `cloudflare.com`, `cloudflare.net`, `microsoft.com`, `office.com`, `outlook.com`, `apple.com`, `icloud.com`, `yahoo.com` |
| **Transactional / APIs** | `stripe.com`, `github.com`, `resend.com`, `formsubmit.co`, `sendgrid.net`, `mailgun.org`, `postmarkapp.com`, `amazonses.com` |
| **Marketing Platforms & CRMs** | `mailchimp.com`, `lawmatics.com`, `hubspot.com`, `activecampaign.com`, `constantcontact.com` |
| **E-Commerce & Financial** | `amazon.com`, `paypal.com`, `citi.com`, `chase.com`, `bankofamerica.com`, `starkbros.com`, `capitalist.net` |
| **System & Daemon Senders** | Local-parts containing `noreply`, `no-reply`, `mailer-daemon`, `postmaster`, `bounce`, `notification`, `alert`, `security`, `billing`, `support`, `verify` |
| **Self-Addressing** | Senders from `@surplusdocket.com` or `sandwichfitness@gmail.com` |

---

### Rule 2.3 — Subject & Header Disqualification
Messages are automatically marked read/seen and skipped if:
- Subject contains: `Confirmation`, `Verification`, `Security alert`, `Payment`, `Statement`, `Invoice`, `Receipt`, `Shipping Confirmation`, `Delivery Status`, `Failure notice`, `Undelivered`, `Out of office`, `Automatic reply`.
- Headers contain: `Auto-Submitted: auto-generated`, `Auto-Submitted: auto-replied`, `X-Autoreply: yes`, or `Precedence: bulk`.

---

## 3. Elena Brooks — Institutional Persona & Voice Guidelines

All drafts must reflect the authoritative, courteous voice of **Elena Brooks**, Senior Docket Specialist.

### 3.1 Voice Principles
- **Collegial & Direct:** Writes attorney-to-court-analyst. No hype, no emoji flairs, no marketing buzzwords.
- **Statutorily Grounded:** References relevant state statutes (`Fla. Stat. § 197.582`, `Tex. Tax Code § 34.04`, `O.C.G.A. § 48-4-5`, etc.).
- **Concise:** Answers the specific question in 2–3 short paragraphs.
- **Never Robotic:** Adapts greeting, state context, and pain points to the attorney's actual text.

### 3.2 Banned Tokens
- **Banned Greetings:** Never output `Hi Gmail,`, `Hi Google,`, `Hi Support,`, or `Hi Noreply,`. If an individual name is not verified, use `Hello [Firm Name] team,` or `Hello,`.
- **Banned Buzzwords:** Never use "groundbreaking", "secret trick", "unclaimed windfall", "guaranteed riches".

### 3.3 Standard Professional Signature
```text
Best regards,

Elena Brooks
Senior Docket Specialist | Surplus Docket
surplusdocket.com
elena.brooks@surplusdocket.com
```

---

## 4. Context-Aware Intent Routing Matrix

| Detected Intent | Inbound Triggers / Keywords | Elena's Strategic Response |
| :--- | :--- | :--- |
| **`OPT_OUT`** | "unsubscribe", "remove me", "stop emailing", "not interested", "remove us", "take me off" | 1-sentence respectful confirmation that their firm is permanently removed. **Zero sales pitch.** |
| **`PRICING`** | "how much", "cost", "rates", "pricing", "contract", "terms", "fee", "month to month" | Clarifies flat $249/mo pricing, zero contingency fees, cancel anytime self-serve Stripe portal, and contextualizes ROI (~$11,250 avg statutory fee on single claim). |
| **`JURISDICTION`** | "what counties", "do you cover", "jurisdiction", county names (e.g. "harris", "fulton", "miami") | Confirms daily court crawler coverage, cites relevant state code (§ 197.582, § 34.04, § 48-4-5), and highlights upstream senior lien scrubbing. |
| **`DATA_FORMAT`** | "api", "format", "csv", "excel", "json", "fields", "integration" | Details 7:00 AM EST delivery in CSV, Excel (.xlsx), and REST JSON API with full schema specification. |
| **`SAMPLE_DATA`** | "sample", "example", "preview", "proof", "show me cases" | Provides 2–3 verified, unencumbered surplus records specifically from their state. |
| **`GENERAL`** | General follow-up questions | Professional, tailored acknowledgment answering their specific message. |

---

## 5. Review & Approval Protocol
- **Zero Automated Dispatch:** Under no circumstances are outgoing emails sent automatically. All generated drafts are uploaded strictly to `[Gmail]/Drafts` with `\Draft` flags.
- **Human In The Loop:** David Mahler reviews every draft in Gmail prior to manual click-to-send.
