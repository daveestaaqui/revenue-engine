# 1. Executive Summary & Google AI Transition Architecture

**Recommendation: make Gemini the primary AI provider, but do not base Surplus Docket’s economics on the assumption that a $20 Google AI subscription includes production API usage.**

Surplus Docket should sell **verified, timely, attorney-ready surplus opportunities with traceable evidence**, not simply scraped records or AI summaries. Its strongest product is the combination of:

- Reliable public-record coverage.
- Clear ownership, lien, and procedural uncertainty.
- Fast delivery into an attorney’s existing workflow.
- Defensible outreach controls.
- Predictable subscription and API economics.

**Scope limitation:** No repository, infrastructure configuration, analytics, billing exports, or authenticated application access was provided. This is an implementation-ready **target-state audit and prioritized specification**, not a claim that I inspected the live application. File paths below are proposed paths; map them to the existing stack before implementation.

## Critical commercial and technical corrections

| Assumption | Planning correction |
|---|---|
| “My $20 Google AI plan covers Gemini API calls.” | Consumer Google AI subscriptions and developer API billing are generally separate products. Verify the actual account’s API access, project billing, quotas, and terms. Do not infer API credits from the subscription. |
| “Gemini means zero marginal API cost.” | An eligible API free tier may cover some development or production usage, subject to current terms and limits. Production must still have usage accounting, hard budgets, and a paid-capacity decision. |
| “Use Gemini 1.5 Flash / Pro / 2.0 Flash permanently.” | These are historical model families, not durable deployment identifiers. Verify currently available, supported models at deployment. Select a supported Flash-class model first and a supported higher-capability Gemini model for escalation. |
| “Every AI task must cost less than $0.01.” | Define the unit. Target **under $0.01 of AI-provider cost per completed routine workflow** over a measured workload, counting retries and escalations. Long audio or difficult documents may exceed it. |
| “Google Voice provides a normal programmable voicemail/SMS API.” | Do not assume a supported general-purpose Google Voice API exists for these workflows. Use supported account-specific delivery/export paths, or route business telephony through a provider with documented APIs. |
| “Automation should eliminate all human review.” | Automate routine work completely. **Legal uncertainty, disputed ownership, suspicious recordings, and sensitive outreach should stop for review rather than become autonomous legal decisions.** |

## Recommended architecture

```text
Public-record sources                 Voicemail / inbound messages
        │                                          │
        ▼                                          ▼
Source adapters                        Supported intake adapters
        └─────────────────┬────────────────────────┘
                          ▼
              Private object storage
              Checksums + source metadata
                          │
                          ▼
              Managed queue / job ledger
                          │
                          ▼
              Serverless processing workers
                          │
              ┌───────────▼────────────┐
              │ AI provider gateway  │
              │                      │
              │ Gemini Flash-class   │ Primary
              │ Gemini higher tier   │ Selective escalation
              │ OpenAI               │ Explicit opt-in fallback
              └───────────┬────────────┘
                          ▼
          Schema validation + evidence attachment
                          │
                          ▼
       State-specific rules + lien/ownership review
                          │
                          ▼
          Tenant-scoped application and REST API
                          │
              ┌───────────┴────────────┐
              ▼                        ▼
       Attorney action memo     Approved notifications
                                and permitted follow-up
```

### Provider contract

Keep provider-specific SDK calls outside business logic:

```ts
interface AIProvider {
  analyzeText(input: TextAnalysisRequest): Promise<AnalysisResult>;
  analyzeAudio(input: AudioAnalysisRequest): Promise<AnalysisResult>;
  analyzeDocument(input: DocumentAnalysisRequest): Promise<AnalysisResult>;
}

interface AnalysisResult {
  data: unknown;
  evidence: EvidenceReference[];
  usage: {
    inputTokens?: number;
    outputTokens?: number;
    audioSeconds?: number;
    estimatedCostUsd: number;
    pricingVersion: string;
  };
  provenance: {
    provider: "gemini" | "openai";
    model: string;
    promptVersion: string;
    schemaVersion: string;
    sourceIds: string[];
  };
}
```

### Default routing policy

```yaml
primary_provider: gemini

models:
  routine: ${GEMINI_ROUTINE_MODEL}
  escalation: ${GEMINI_ESCALATION_MODEL}
  secondary: ${OPENAI_FALLBACK_MODEL}

routing:
  prefer_supported_flash_class: true
  allow_gemini_escalation: true
  allow_openai_fallback: false
  require_tenant_approval_for_cross_provider_fallback: true

budgets:
  routine_workflow_ai_cost_target_usd: 0.01
  reserve_before_request: true
  retry_limit: 2
  enforce_project_daily_cap: true
  enforce_tenant_monthly_cap: true

failure_behavior:
  missing_provider_configuration: fail_deployment
  quota_exhausted: defer_with_explicit_status
  invalid_structured_output: validate_then_bounded_retry
  legal_uncertainty: human_review
```

**Native voicemail processing:** send supported audio directly to Gemini for transcription and structured extraction. Whisper is not a required dependency. For large or unsupported files, perform serverless transcoding or segmentation first. Validate timestamps and critical transcript fields instead of assuming that native multimodal output is exact.

**Zero local daemons:** use managed queues, object storage, a database, and serverless workers. GitHub Actions should handle CI/CD, reconciliations, and nonurgent scheduled dispatch—not serve as the sole real-time processing engine.

---

# 2. End-to-End System Audit (Business, Data, Automation, Conversion)

## A. Business and monetization

### Recommended product contract

| Package | Included | Required boundaries |
|---|---|---|
| **Tri-State — $249/month** | Customer chooses three supported states; verified opportunity feed; evidence-backed summaries; inbound action memos | Define geographic coverage, freshness, seats, exports, and included AI usage. No enterprise REST API. |
| **Six-State + REST API — $449/month** | FL, TX, GA, CA, NC, TN; all Tri-State capabilities; REST API; incremental synchronization | Publish API quotas, fair-use limits, availability expectations, and any AI usage limits. |
| **Optional services** | Additional seats, approved integration setup, higher API volume, carefully scoped onboarding | Transparent fixed fees. Avoid default compensation tied to a law firm’s legal fee or recovery. |

**Pricing gap:** the premium plan adds three states and API access for only $200 more per month. That can work if API requests mostly read already-computed data. It is dangerous if every request triggers fresh scraping, document retrieval, or model inference.

**Required design:** API reads serve persisted results. Reprocessing is a separate, quota-controlled asynchronous operation.

### Commercial metrics

Track:

1. Visitor → sample coverage view.
2. Sample view → account.
3. Account → checkout.
4. Checkout → paid subscription.
5. Paid subscription → first saved or exported opportunity.
6. First opportunity → reported attorney review or engagement.
7. Renewal, expansion, and churn by state coverage.
8. Contribution margin by tenant and plan.

Do not present attorney engagement or client recovery as proven outcomes unless customers actually report them and their use in marketing is appropriate.

### Revenue interpretation

- Twenty Tri-State subscriptions produce **$4,980 MRR**.
- Twenty Six-State subscriptions produce **$8,980 MRR**.
- A 10/10 split produces **$6,980 MRR**.

These are arithmetic scenarios, not forecasts. Demand, data availability, retention, and operating costs remain unverified.

## B. Data acquisition and public-record reliability

The core competitive risk is **incorrect or stale opportunity data**, not lack of model sophistication.

Every opportunity should preserve:

```text
Source authority and URL
Retrieval timestamp
County and state
Case and parcel identifiers
Proceeding type
Document checksum
Extraction and rule versions
Sale/event date
Reported surplus amount, if any
Potential claimant identities
Known lien evidence
Known coverage gaps
Review status
```

### Critical distinctions

- Tax-sale surplus and mortgage-foreclosure surplus are not interchangeable.
- A docket entry is not necessarily proof that funds remain available.
- An assessed value is not a reliable substitute for actual sale proceeds.
- Missing lien evidence is not evidence that no lien exists.
- A name match is not sufficient to identify the entitled claimant.
- A recorded release may require additional analysis before an encumbrance is treated as extinguished.
- A public-record document can be authentic while its extracted interpretation is wrong.

**Product terminology:** prefer “preliminary public-record lien screening” over “clean title” or “guaranteed recoverable surplus.”

## C. Automation and serverless operations

| Layer | Target state | Main failure mode |
|---|---|---|
| Source collection | County-specific adapters with checkpoints and documented access rules | Silent source-layout changes |
| Processing | Queue-triggered, idempotent jobs | Duplicate processing and charges |
| AI extraction | Versioned schemas and bounded retries | Valid-looking hallucinations |
| Rules | Counsel-reviewed state/proceeding packs | Using the wrong legal workflow |
| Delivery | Transactional outbox and delivery ledger | Lost or duplicate notifications |
| Recovery | Dead-letter queues, replay controls, backups | Infinite retries or irreversible corruption |
| Observability | Freshness, queue age, spend, exception rate | “Healthy” infrastructure with stale data |

GitHub Actions schedules can be delayed or constrained. A production freshness commitment requires a scheduler and queue architecture designed for that commitment.

## D. Audio-first conversion

A valuable inbound experience is:

1. A caller leaves a voicemail.
2. The original recording is stored privately.
3. Gemini produces a transcript and structured intake.
4. Critical details receive validation.
5. The application produces an **internal action memo**.
6. The system checks identity uncertainty, consent, suppression, and outreach rules.
7. A permitted acknowledgment is sent—or the item stops for review.

The memo should contain:

- Caller identity and callback number, with uncertainty.
- Property/case references.
- Stated purpose.
- Potential urgency.
- Evidence-linked facts.
- Missing information.
- Proposed administrative next step.
- Whether any external response is permitted.

It should **not** independently advise the caller about legal entitlement or claim deadlines.

## E. Legal and ethics controls

### Florida Rule 4-7.18

Do not reduce this rule to a single global “30-day delay.” Solicitation restrictions, communication channels, advertising obligations, recipient circumstances, exceptions, and related rules require current, context-specific analysis.

Implement a **versioned, counsel-approved decision table**, with rule citations and effective dates. The default for an unmodeled situation should be hold—not “send.”

### *Tyler v. Hennepin County*

The Supreme Court’s 2023 decision supports an important constitutional principle concerning government retention of value beyond a tax debt. It does **not** establish that every surplus lead is recoverable, that all foreclosure types are equivalent, or that state-specific claims procedures and deadlines disappear.

Use it in carefully reviewed educational material, not as an automatic entitlement engine.

### UPL and professional boundaries

Surplus Docket should provide records, workflow tools, and evidence-backed factual summaries. Licensed professionals should decide legal entitlement, representation, filing strategy, and disputed priority.

A disclaimer alone does not cure a product that functionally gives personalized legal advice.

### Other controls

Include current, counsel-reviewed requirements for:

- SMS consent and revocation.
- Telephone solicitation and applicable calling restrictions.
- Recording and transcription notices.
- Advertising and referral arrangements.
- Data protection and vendor processing.
- Retention and deletion.
- Attorney confidentiality.
- Public-record access restrictions.

## F. Digital PR and integrations

**Near-term conversion:** practice-group landing pages with authentic coverage samples are likely faster to implement than three deep practice-management integrations.

**Long-term differentiation:** publish original, methodologically defensible surplus-data reports and provide citation-worthy source material.

**Integration sequence:** REST API first, webhook delivery second, one customer-backed practice-management integration third. Do not simultaneously build Clio, Filevine, and Smokeball without validated access and paid demand.

---

# 3. 50 Candidate Changes Ideation Matrix

| # | Title | Subsystem | Description |
|---:|---|---|---|
| 1 | Enforced plan entitlements | Monetization | Encode the $249 three-state and $449 six-state/API plans as server-enforced capabilities. |
| 2 | Evidence-first sample-to-checkout funnel | Conversion | Show authentic, appropriately redacted sample opportunities and coverage before checkout. |
| 3 | Paid attorney design-partner cohort | Revenue | Recruit a small paid cohort to validate coverage, workflow value, and willingness to renew. |
| 4 | Activation and ROI telemetry | Analytics | Measure first useful opportunity, exports, attorney-reported outcomes, and retention. |
| 5 | Geographic demand and coverage map | Packaging | Show county availability and freshness; collect requests without promising unsupported coverage. |
| 6 | Annual billing and transparent upgrades | Monetization | Add annual terms and prorated upgrades after retention is demonstrated. |
| 7 | Gemini-first provider abstraction | AI infrastructure | Replace direct model calls with capability-based Gemini routing and optional OpenAI fallback. |
| 8 | Atomic AI budget and quota governor | AI economics | Reserve estimated spend before execution; meter retries, escalations, and per-tenant usage. |
| 9 | Native multimodal voicemail processing | Audio AI | Send supported recordings directly to Gemini for transcript and structured intake. |
| 10 | Evidence-grounded extraction schemas | Data quality | Require typed outputs, explicit unknowns, and source references for material facts. |
| 11 | Golden-set evaluation and release gates | AI quality | Block model and prompt changes that regress critical extraction or compliance outcomes. |
| 12 | Privacy and retention control plane | Governance | Minimize collection, control retention, and implement auditable deletion and legal holds. |
| 13 | County source adapter framework | Ingestion | Standardize collection, provenance, throttling, checkpoints, and parser health. |
| 14 | Docket-event change detection | Ingestion | Detect material changes without repeatedly processing unchanged records. |
| 15 | Preliminary title and lien screening | Records intelligence | Build evidence-backed ownership and lien timelines with explicit coverage limits. |
| 16 | Six-state legal workflow packs | Legal automation | Separate rules by state, proceeding type, source, effective date, and counsel approval. |
| 17 | Recoverability scenario ranges | Valuation | Present bounded scenarios with disclosed inputs rather than guaranteed recovery estimates. |
| 18 | Idempotent jobs and transactional outbox | Reliability | Prevent duplicate charges, records, notifications, and external side effects. |
| 19 | Serverless orchestration and reconciliation | Operations | Use managed workers and queues; GitHub Actions deploys and checks system health. |
| 20 | Exception recovery and dead-letter console | Operations | Classify failures and support controlled replay without infinite retry loops. |
| 21 | Coverage freshness commitments | Product trust | Publish measured county-level freshness and stop describing stale data as current. |
| 22 | Secure software supply chain | DevSecOps | Pin dependencies/actions, scan secrets, sign artifacts, and minimize build privileges. |
| 23 | Attorney action memos | Intake workflow | Convert inbound audio and case evidence into an internal, reviewable next-action packet. |
| 24 | Supported Google Voice intake bridge | Telephony | Use validated account-supported delivery methods, with a programmable-provider alternative. |
| 25 | Consent-aware SMS follow-up gate | Communications | Separate permission checks from message generation and block unapproved sends. |
| 26 | Human-approved outbound call tasks | Outreach | Create compliant call tasks instead of autonomous cold-calling agents. |
| 27 | Reply classification and task routing | Communications | Categorize inbound replies and route them without letting model text authorize actions. |
| 28 | Solicitation and ethics policy engine | Compliance | Evaluate jurisdiction, recipient, channel, relationship, consent, and required review. |
| 29 | UPL-safe product boundary controls | Legal product | Prevent automated legal conclusions, advice, and unreviewed filing actions. |
| 30 | Accurate *Tyler* educational labels | Legal content | Explain the decision’s scope without implying universal entitlement or deadlines. |
| 31 | Unified suppression and rights workflow | Privacy/outreach | Propagate opt-outs, access requests, and appropriate deletion across systems. |
| 32 | Tenant isolation and authorization | Security | Enforce account, state, record, object-storage, export, and API access boundaries. |
| 33 | Bounded autonomous Sentinel | Security operations | Detect and contain predefined security events without granting unrestricted AI control. |
| 34 | Tamper-evident activity ledger | Auditability | Preserve attributable evidence of rule, data, permission, and communication decisions. |
| 35 | Tested backup and incident recovery | Resilience | Exercise restore, credential compromise, source failure, and provider-outage procedures. |
| 36 | Versioned enterprise REST API | Enterprise | Provide stable, tenant-scoped access to persisted opportunities and evidence metadata. |
| 37 | Signed webhooks and replay | Enterprise | Deliver opportunity changes with signatures, identifiers, retries, and replay controls. |
| 38 | Clio intake connector | Practice management | Build a supported, customer-validated contact/matter integration with approval controls. |
| 39 | Filevine intake connector | Practice management | Map approved opportunities into supported project/contact workflows. |
| 40 | Smokeball workflow connector | Practice management | Validate vendor access first; provide supported integration or safe structured export. |
| 41 | Controlled bulk exports | Enterprise | Offer asynchronous exports with scoped permissions, expiry, and download auditing. |
| 42 | Evidence packet manifests | Attorney workflow | Package source documents, retrieval metadata, hashes, and limitations into an export. |
| 43 | Original surplus-data reports | Digital PR | Publish aggregated research with methodology, caveats, and privacy controls. |
| 44 | Attorney-reviewed legal resource library | SEO/education | Maintain useful state-specific resources with dates, citations, and accountable review. |
| 45 | Practice-group conversion pages | Conversion | Build focused pages for relevant practice groups with real coverage and sample work products. |
| 46 | Editorial backlink outreach | Digital PR | Pitch original research to appropriate publishers without purchased-link schemes. |
| 47 | Ethics-reviewed partner channel | Distribution | Create fixed-fee or otherwise approved partner arrangements without improper fee sharing. |
| 48 | Conservative entity resolution | Data intelligence | Link people, parcels, and cases using multiple identifiers and explicit uncertainty. |
| 49 | Attorney-controlled claim workflow | Case operations | Track evidence, review, deadlines, and status without autonomous legal filings. |
| 50 | Tenant contribution-margin dashboard | Economics | Combine subscription revenue, AI, sources, storage, telephony, and support costs. |

---

# 4. Critique Agent Evaluation & Scoring

## Evaluation method

This is a **structured red-team review using five evaluator perspectives**, not a claim that independent agents or external legal reviewers were actually run.

Each candidate receives a 1–5 score:

- **R — Immediate revenue:** speed and directness of commercial impact.
- **A — Automation:** reduction of recurring toil, including safe recovery.
- **L — Legal precision:** contribution to defensibility and bounded behavior.
- **C — Cost efficiency:** likely economics without assuming bundled API credits.
- **T — Technical quality:** robustness, maintainability, and implementation practicality.

Suggested composite:

\[
S = 6R + 4A + 5L + 3C + 2T
\]

Maximum: 100. Scores are planning judgments, not measurements.

**Selection is dependency-aware, not mechanically sorted by score.** Foundational controls can outrank commercially attractive features. A low legal score is a deployment risk flag, not a finding of illegality.

**★ = selected for the Top 20.** Unselected safeguards are not permission to omit minimum privacy, backup, or security requirements; some are mandatory acceptance conditions within selected work.

## Candidate-by-candidate critique

| # | R | A | L | C | T | Principal trade-off or failure mode |
|---:|:-:|:-:|:-:|:-:|:-:|---|
| **1 ★** | 5 | 4 | 4 | 5 | 5 | Revenue leakage if entitlements exist only in the UI. |
| **2 ★** | 5 | 4 | 4 | 5 | 4 | Misleading samples or excessive disclosure can destroy trust. |
| 3 | 5 | 2 | 4 | 4 | 4 | Fast learning, but founder-led onboarding is not hands-off. |
| 4 | 4 | 4 | 4 | 5 | 4 | Attribution is weak unless downstream outcomes are voluntarily reported. |
| 5 | 3 | 4 | 4 | 5 | 4 | Coverage claims can outrun actual source reliability. |
| 6 | 4 | 5 | 4 | 5 | 4 | Annual commitments amplify refund and trust problems if coverage is poor. |
| **7 ★** | 3 | 5 | 4 | 5 | 5 | Legacy model IDs, capability mismatches, and hidden fallback charges. |
| **8 ★** | 4 | 5 | 4 | 5 | 5 | Nonatomic limits overspend under concurrency; hard caps can delay work. |
| **9 ★** | 4 | 5 | 3 | 4 | 4 | Wrong numbers or names can trigger harmful follow-up. |
| **10 ★** | 4 | 5 | 5 | 4 | 5 | Schema-valid output can still be false; evidence must be checked. |
| **11 ★** | 3 | 5 | 5 | 4 | 5 | Overfitting to a small test set creates false assurance. |
| 12 | 2 | 4 | 5 | 4 | 5 | Deletion conflicts with backups, legal holds, and audit needs. |
| **13 ★** | 5 | 5 | 4 | 4 | 5 | County variability and access constraints prevent one universal scraper. |
| 14 | 4 | 5 | 4 | 5 | 4 | Weak change detection can miss material docket updates. |
| **15 ★** | 5 | 4 | 4 | 3 | 4 | Expensive source access; incomplete records can resemble clean title. |
| **16 ★** | 4 | 4 | 5 | 3 | 4 | Requires qualified review and ongoing legal maintenance. |
| 17 | 4 | 4 | 2 | 3 | 3 | False precision can become misleading valuation or legal advice. |
| **18 ★** | 3 | 5 | 4 | 5 | 5 | Exactly-once effects require cooperation from downstream systems. |
| **19 ★** | 4 | 5 | 4 | 5 | 5 | Scheduled CI alone cannot guarantee timely production processing. |
| 20 | 3 | 5 | 4 | 4 | 5 | Blind replay can repeat destructive or chargeable actions. |
| 21 | 4 | 4 | 5 | 4 | 4 | An advertised SLA becomes a liability if dependencies are unmeasured. |
| 22 | 2 | 5 | 4 | 5 | 5 | Scanners without enforced policy create noise rather than protection. |
| **23 ★** | 5 | 5 | 4 | 4 | 4 | Internal suggestions can drift into legal conclusions. |
| **24 ★** | 4 | 4 | 4 | 4 | 3 | Account-specific Voice delivery may not expose usable audio. |
| **25 ★** | 5 | 5 | 3 | 3 | 4 | A callback request is not blanket permission for marketing texts. |
| 26 | 3 | 2 | 4 | 3 | 4 | Human review improves control but limits scale. |
| 27 | 4 | 5 | 3 | 4 | 4 | Misclassified opt-outs or urgency can create significant harm. |
| **28 ★** | 4 | 4 | 5 | 4 | 5 | Stale rules or broad exceptions undermine every outreach safeguard. |
| 29 | 3 | 4 | 5 | 5 | 4 | Disclaimers alone cannot constrain product behavior. |
| 30 | 3 | 4 | 5 | 5 | 4 | Overbroad constitutional claims misstate recoverability. |
| 31 | 3 | 4 | 5 | 4 | 4 | Suppression must survive deletion without retaining unnecessary data. |
| **32 ★** | 4 | 5 | 5 | 4 | 5 | Cross-tenant leakage can occur through caches, exports, and storage URLs. |
| **33 ★** | 3 | 5 | 5 | 4 | 4 | An overprivileged security agent becomes a new attack surface. |
| 34 | 3 | 5 | 5 | 4 | 4 | “Immutable” logs can retain sensitive content indefinitely. |
| 35 | 3 | 4 | 5 | 3 | 5 | Backups are unproven until restores succeed. |
| **36 ★** | 5 | 5 | 4 | 4 | 5 | Unlimited API usage or model-on-read behavior erodes margins. |
| 37 | 4 | 5 | 4 | 4 | 5 | Retry storms and duplicate events burden customers. |
| 38 | 4 | 4 | 4 | 3 | 3 | Access approval and customer-specific mappings slow launch. |
| 39 | 4 | 4 | 4 | 3 | 3 | Deep customization can become a services business. |
| 40 | 3 | 3 | 4 | 3 | 2 | Unsupported integration assumptions can make the project infeasible. |
| 41 | 4 | 5 | 3 | 4 | 4 | Bulk exfiltration risk increases sharply. |
| 42 | 4 | 4 | 5 | 4 | 4 | Hashes prove file integrity, not correctness of legal interpretation. |
| 43 | 3 | 4 | 4 | 4 | 4 | Strong long-term authority; slower and uncertain immediate revenue. |
| 44 | 3 | 3 | 4 | 3 | 4 | Stale legal pages create maintenance and accuracy burdens. |
| **45 ★** | 5 | 4 | 4 | 5 | 5 | Generic AI pages will not compensate for weak coverage or proof. |
| 46 | 3 | 2 | 4 | 4 | 4 | Earned backlinks are uncertain and require editorial relationships. |
| 47 | 4 | 3 | 2 | 4 | 3 | Referral compensation and professional-conduct issues require review. |
| 48 | 4 | 5 | 3 | 3 | 3 | False matches can contaminate many downstream records. |
| 49 | 4 | 4 | 3 | 3 | 3 | Deadline and filing automation can cross into legal judgment. |
| 50 | 4 | 5 | 4 | 5 | 4 | Incomplete cost attribution hides unprofitable tenants. |

## Cross-cutting critique findings

### 1. Revenue before breadth—but not before truth

Better checkout, actionable memos, and the premium API can monetize existing value quickly. They must not advertise six-state completeness where county coverage remains partial.

### 2. “Self-healing” needs a stopping condition

Automated recovery should fix transient transport, quota, and parser problems where safe. It should not guess at legal rules, solve access restrictions through evasion, or retry communications indefinitely.

### 3. Low AI cost is achievable only with workload control

Use:

- Persisted results.
- Content-hash deduplication.
- Bounded output sizes.
- Selective escalation.
- Audio duration limits.
- Request reservations and tenant quotas.
- Cached public-document analysis only where permissions allow reuse.

Do not substitute consumer-interface automation for a supported API to avoid billing.

### 4. Title intelligence requires a confidence boundary

The attractive commercial promise is reduced attorney research time. The unsafe promise is “AI-certified clear title.”

### 5. Backlinks and integrations are second-wave multipliers

Original research and one well-chosen integration can become durable advantages. They are weaker first moves than reliable data, enforceable pricing, and a working inbound workflow.

---

# 5. The Top 20 Selected Changes

**Ranking basis:** commercial leverage, risk reduction, and dependency value. This is a ranked portfolio, not a literal deployment sequence.

**Reference implementation:** TypeScript application, PostgreSQL, private object storage, managed queue, and serverless workers. Provider and cloud choices can vary. All paths below are proposed; no claim is made that these files currently exist.

## 1. Enforce the $249 / $449 Product Contract — Candidate 1

**Blueprint**

Create immutable plan versions:

```json
{
  "tri_state_v1": {
    "monthlyPriceUsd": 249,
    "selectedStateCount": 3,
    "restApi": false
  },
  "six_state_api_v1": {
    "monthlyPriceUsd": 449,
    "states": ["FL", "TX", "GA", "CA", "NC", "TN"],
    "restApi": true
  }
}
```

- Store tenant state selections and billing status.
- Enforce entitlements in queries, exports, downloads, and API handlers.
- Lock ordinary state-selection changes to the next billing period; audit support overrides.
- Make webhook handling idempotent.
- Define grace, delinquency, cancellation, and refund behavior explicitly.

**Files**

`src/billing/plans.ts`  
`src/billing/webhooks.ts`  
`src/auth/entitlements.ts`  
`db/migrations/001_plan_entitlements.sql`

**Acceptance criteria**

- Monthly checkout prices are exactly $249 and $449.
- A Tri-State customer cannot access a fourth state through any route.
- Tri-State API-key creation is rejected.
- Duplicate or reordered billing events do not grant incorrect access.
- Every advertised quota is visible before purchase.

## 2. Ship an Evidence-First Conversion Funnel — Candidate 2

**Blueprint**

Create `/coverage`, `/sample-opportunity`, and `/pricing`.

Display:

- Actual county coverage.
- Last successful source retrieval.
- An appropriately redacted opportunity.
- Evidence references and uncertainty labels.
- What each plan includes and excludes.

Record consent-appropriate funnel events:

```text
coverage_viewed
sample_viewed
checkout_started
subscription_activated
first_opportunity_saved
```

**Files**

`src/app/coverage/page.tsx`  
`src/app/sample-opportunity/page.tsx`  
`src/app/pricing/page.tsx`  
`src/analytics/events.ts`

**Acceptance criteria**

- No fabricated or unlabeled synthetic success stories.
- Coverage claims derive from the source registry.
- Test purchase reaches correct entitlements.
- Product analytics exclude raw caller and claimant information.
- Establish a two-week baseline before claiming conversion improvement.

## 3. Replace Direct OpenAI Calls with a Gemini-First Gateway — Candidate 7

**Blueprint**

Implement text, document, and native audio capabilities behind the provider interface.

- Select model IDs through environment configuration.
- Validate model availability and required capabilities during deployment.
- Make Gemini the default.
- Disable OpenAI fallback unless both project and tenant policies allow it.
- Defer work transparently if no approved provider is available.
- Verify vendor data-use and retention terms before sending sensitive production data.

**Files**

`src/ai/provider.ts`  
`src/ai/providers/gemini.ts`  
`src/ai/providers/openai.ts`  
`src/ai/router.ts`  
`config/ai-policy.yaml`

**Acceptance criteria**

- Normal production tasks invoke Gemini.
- Audio tasks do not require Whisper.
- No OpenAI request occurs with fallback disabled.
- Every result records provider, model, schema, prompt, and usage.
- Unsupported or retired model configuration fails deployment rather than silently changing models.
- Repository scanning finds no remaining direct provider calls outside adapters.

## 4. Implement an Atomic AI Budget Governor — Candidate 8

**Blueprint**

Add an append-only usage ledger and spend reservations.

For each workflow:

1. Estimate the next request using a versioned price catalog.
2. Reserve tenant and project budget transactionally.
3. Execute the request.
4. Reconcile actual usage.
5. Account for every retry and escalation.
6. Release unused reservation.
7. Defer further processing when limits are reached.

Separate AI cost from telephony, source access, storage, and payment fees.

**Files**

`src/ai/budget.ts`  
`src/ai/pricing.ts`  
`src/ai/usage-ledger.ts`  
`config/ai-prices.yaml`  
`db/migrations/002_ai_usage.sql`

**Acceptance criteria**

- Concurrent reservation tests cannot oversubscribe configured budgets.
- Usage reconciliation includes failed billable requests where the provider exposes them.
- No “free subscription quota” is assumed without verified account entitlement.
- A representative 1,000-workflow benchmark measures mean and p95 AI cost.
- The under-$0.01 target is advertised only if the defined routine workload actually meets it.

## 5. Install the Solicitation and Ethics Policy Engine — Candidate 28

**Blueprint**

Create a deterministic policy input:

```ts
type OutreachContext = {
  jurisdiction: string;
  channel: "sms" | "email" | "phone" | "mail";
  purpose: "transactional" | "marketing" | "solicitation";
  relationshipStatus: string;
  consentEvidenceIds: string[];
  recipientRestrictions: string[];
  relevantEventDates: Record<string, string>;
};
```

Return:

```text
ALLOW
HOLD_FOR_REVIEW
BLOCK
```

Every decision includes rule-pack version, reasons, missing facts, and required disclosures.

**Files**

`src/compliance/outreach-policy.ts`  
`config/legal/outreach/*.yaml`  
`src/compliance/decision-log.ts`  
`tests/compliance/outreach-policy.test.ts`

**Acceptance criteria**

- Unmodeled circumstances default to hold.
- Florida policies reference current counsel-reviewed rules, including relevant Rule 4-7.18 provisions.
- No global “30-day rule” substitutes for a decision table.
- Generated text cannot override a blocked decision.
- Expired or withdrawn rule packs prevent affected automated sends.

## 6. Enforce Tenant Isolation Everywhere — Candidate 32

**Blueprint**

- Require `tenant_id` on tenant-owned records.
- Apply database row-level security where supported.
- Use tenant-scoped cache keys and object authorization.
- Hash API keys and implement explicit scopes.
- Give workers only necessary service permissions.
- Keep private recordings and documents out of public buckets.

**Files**

`src/auth/tenant-context.ts`  
`src/auth/api-keys.ts`  
`src/storage/authorized-download.ts`  
`db/migrations/003_tenant_isolation.sql`

**Acceptance criteria**

- Adversarial tests cover API, search, exports, storage, background jobs, and caches.
- Knowing another tenant’s object ID does not grant access.
- Download links expire within a configured short lifetime.
- Privileged cross-tenant operations are separately authorized and audited.
- Production logs redact secrets and sensitive content.

## 7. Standardize County Ingestion and Provenance — Candidate 13

**Blueprint**

Define:

```ts
interface SourceAdapter {
  discover(cursor?: string): Promise<DiscoveryBatch>;
  fetch(record: SourceRecord): Promise<SourceArtifact>;
  normalize(artifact: SourceArtifact): Promise<NormalizedRecord>;
  healthCheck(): Promise<SourceHealth>;
}
```

Maintain a registry containing authority, proceeding type, access method, permitted cadence, coverage, and parser version.

Start with the highest-value verified counties—not an unsupported six-state completeness claim.

**Files**

`src/ingest/source-adapter.ts`  
`src/ingest/adapters/`  
`config/sources.yaml`  
`db/migrations/004_source_provenance.sql`

**Acceptance criteria**

- Each ingested record retains retrieval time, source reference, and checksum.
- Unchanged artifacts are not repeatedly processed.
- Parser-drift fixtures trigger quarantine.
- Access restrictions and rate limits are respected.
- County freshness is measurable independently from worker uptime.

## 8. Build Six-State, Proceeding-Specific Rule Packs — Candidate 16

**Blueprint**

Create separate packs for FL, TX, GA, CA, NC, and TN, subdivided by relevant proceeding type.

Required fields:

```text
Jurisdiction
Proceeding type
Authority citations
Effective date
Review date
Qualified reviewer
Required facts
Permitted classifications
Mandatory warnings
Deadline logic, if approved
Uncertainty and escalation rules
```

AI may draft research assistance; it must not activate a rule pack.

**Files**

`config/legal/states/{FL,TX,GA,CA,NC,TN}/`  
`src/legal/rule-pack-loader.ts`  
`src/legal/classifier.ts`  
`tests/legal/fixtures/`

**Acceptance criteria**

- No published state workflow lacks approved citations and review metadata.
- Tax and mortgage foreclosure fixtures produce distinct workflows.
- Missing event dates do not produce guessed deadlines.
- *Tyler* is never treated as automatic proof of recoverability.
- Unapproved packs remain research-only and cannot authorize outreach.

## 9. Deliver Evidence-Backed Preliminary Lien Screening — Candidate 15

**Blueprint**

Produce a chronological evidence graph:

```text
Property / parcel
   ├── ownership documents
   ├── recorded encumbrances
   ├── releases / satisfactions
   ├── docket events
   └── unresolved identity or priority questions
```

Separate:

1. Source observations.
2. Extracted facts.
3. Potential relevance.
4. Attorney review questions.

Do not label a property “clear” solely because searches return no matches.

**Files**

`src/records/lien-screen.ts`  
`src/records/evidence-graph.ts`  
`src/records/coverage-limitations.ts`  
`src/components/LienScreenPanel.tsx`

**Acceptance criteria**

- Every lien entry links to source evidence.
- Name-only matches remain uncertain.
- Missing source coverage produces a visible limitation.
- The interface states that screening is not title insurance or a legal priority opinion.
- Human reviewers can reject facts without destroying the original evidence.

## 10. Require Typed, Evidence-Grounded AI Extraction — Candidate 10

**Blueprint**

Use versioned JSON schemas with:

- Nullable unknown fields.
- Required evidence references for material facts.
- Verbatim excerpts where appropriate.
- Explicit distinction between reported and inferred values.
- Rule-based checks for dates, currency, identifiers, and phone numbers.

Prefer deterministic extraction when available. Use an LLM for interpretation, not tasks that a reliable parser already solves.

**Files**

`src/ai/schemas/opportunity.schema.json`  
`src/ai/schemas/voicemail.schema.json`  
`src/ai/validate.ts`  
`src/ai/evidence-checks.ts`

**Acceptance criteria**

- Invalid outputs do not enter canonical opportunity tables.
- Unsupported financial amounts and dates are rejected or marked unknown.
- Extraction disagreement routes to review.
- Evidence references resolve to accessible, authorized artifacts.
- A syntactically valid JSON object alone never qualifies a record as verified.

## 11. Add Idempotency and a Transactional Outbox — Candidate 18

**Blueprint**

Create deterministic job keys using:

```text
tenant scope
source artifact hash
operation
schema version
prompt/rule version
```

Write record changes and outgoing events in one database transaction. Deliver externally from the outbox with stable identifiers.

**Files**

`src/jobs/idempotency.ts`  
`src/events/outbox.ts`  
`src/events/dispatcher.ts`  
`db/migrations/005_jobs_and_outbox.sql`

**Acceptance criteria**

- Replaying the same ingestion event 100 times creates one canonical processing result.
- Downstream delivery uses provider idempotency keys where supported.
- Ambiguous external-send timeouts reconcile against the delivery ledger before retry.
- A crash between database commit and delivery does not lose the event.
- Exactly-once delivery is not claimed where the downstream provider cannot support it.

## 12. Move Operations to Managed Serverless Processing — Candidate 19

**Blueprint**

- Managed scheduler dispatches time-sensitive jobs.
- Managed queue feeds serverless workers.
- GitHub Actions runs tests, deploys, and performs scheduled reconciliation.
- Workloads use short-lived cloud credentials.
- Transient failures use bounded exponential backoff with jitter.
- Permanent or unknown failures enter a dead-letter queue.

**Files**

`infra/queues.tf`  
`infra/workers.tf`  
`infra/scheduler.tf`  
`.github/workflows/ci.yml`  
`.github/workflows/deploy.yml`  
`.github/workflows/reconcile.yml`

**Acceptance criteria**

- Production operation requires no developer laptop or local daemon.
- Source outages do not create retry storms.
- Queue age and freshness violations alert operators.
- Dead-letter replay preserves idempotency.
- A backup restoration drill succeeds before production launch.
- Deployment workflows use minimum permissions and protected environments.

## 13. Implement Native Gemini Audio Intake — Candidate 9

**Blueprint**

1. Accept supported audio through a private upload/intake endpoint.
2. Validate type, duration, size, and safe decoding.
3. Store the original privately.
4. Submit audio to Gemini directly.
5. Generate transcript and structured intake.
6. Validate high-impact fields.
7. Remove temporary provider-side files where supported and required.

Set an initial **10-minute processing limit**; longer recordings enter segmentation or review rather than unlimited inference.

**Files**

`src/audio/ingest.ts`  
`src/audio/normalize.ts`  
`src/audio/gemini-transcribe.ts`  
`src/audio/critical-field-checks.ts`

**Acceptance criteria**

- No Whisper dependency in the primary pipeline.
- Supported-format tests include noisy and accented speech.
- Uncertain phone numbers are not silently corrected.
- Audio-borne instructions cannot invoke tools or change system policy.
- Recording notices, vendor terms, and retention policy are approved before real caller deployment.
- Transcription quality is measured on a consented evaluation set.

## 14. Validate and Build the Google Voice Intake Bridge — Candidate 24

**Blueprint**

Perform an account-specific feasibility test first.

Preferred order:

1. Supported voicemail delivery containing a usable audio artifact.
2. A supported message/export ingestion path.
3. A business number or routing arrangement through a documented programmable telephony provider.

If email ingestion is used, use supported mailbox APIs with narrow permissions. Do not assume a voicemail notification contains downloadable audio.

**Files**

`src/integrations/voice/intake-adapter.ts`  
`src/integrations/mail/voicemail-ingest.ts`  
`src/integrations/telephony/webhooks.ts`  
`docs/voice-intake-runbook.md`

**Acceptance criteria**

- A real test voicemail reaches private storage through a documented supported path.
- Duplicate notifications create one intake event.
- No browser-session scraping, password automation, or CAPTCHA bypass.
- Where Google Voice cannot provide reliable audio intake, the application clearly reports the limitation.
- Any replacement routing passes an end-to-end test before the existing number is changed.

## 15. Generate Attorney-Ready Action Memos — Candidate 23

**Blueprint**

Compose a memo from validated intake and authorized case data.

Sections:

```text
Why the caller contacted the firm
Confirmed identifiers
Facts linked to evidence
Uncertain or missing information
Potential urgency requiring review
Administrative next action
External-contact permission status
```

Keep memo creation separate from any outbound action.

**Files**

`src/intake/action-memo.ts`  
`src/ai/prompts/action-memo.md`  
`src/components/ActionMemo.tsx`  
`src/intake/review-actions.ts`

**Acceptance criteria**

- Material statements resolve to transcript or record evidence.
- Uncertain case matches remain unlinked or explicitly provisional.
- Memos contain no unreviewed entitlement or deadline conclusions.
- Attorneys can approve, edit, dismiss, or request clarification.
- Internal memo creation never automatically authorizes SMS.

## 16. Gate SMS Follow-Up with Consent and Policy — Candidate 25

**Blueprint**

Create a communication authorization record distinct from the generated message.

Required data:

```text
Recipient and verified destination
Purpose and channel
Consent evidence and scope
Suppression status
Applicable policy decision
Template version
Approval, if required
Delivery identifier
```

Use approved templates for narrow acknowledgments. Handle opt-outs deterministically and independently of the model.

**Files**

`src/communications/authorize-send.ts`  
`src/communications/sms.ts`  
`src/communications/suppression.ts`  
`config/communications/templates.yaml`

**Acceptance criteria**

- Missing necessary permission blocks the send.
- A voicemail alone is not interpreted as blanket marketing consent.
- Supported opt-out signals update suppression before later sends.
- Quiet-hour and jurisdictional controls use reviewed policies.
- No SMS contains sensitive case details by default.
- Provider delivery receipts and uncertain-send states are recorded.

## 17. Launch the $449 Plan’s Versioned REST API — Candidate 36

**Blueprint**

Initial read-oriented endpoints:

```http
GET /v1/opportunities
GET /v1/opportunities/{id}
GET /v1/opportunities/{id}/evidence
GET /v1/coverage
GET /v1/usage
```

Implement:

- Scoped, hashed API keys.
- Cursor pagination.
- `updated_after` filtering.
- UTC timestamps.
- Stable error schemas.
- Tenant and state authorization.
- Rate and monthly usage limits.

**Proposed initial allowance:** 60 requests/minute and 50,000 requests/month, subject to prelaunch load and margin validation and disclosure before purchase.

**Files**

`src/api/v1/`  
`src/api/rate-limit.ts`  
`openapi/surplus-docket.v1.yaml`  
`docs/api/quickstart.md`

**Acceptance criteria**

- Only entitled subscriptions can create active API keys.
- API reads do not trigger model calls or live scraping.
- Cross-tenant tests pass.
- Limits return documented `429` responses.
- Pagination remains stable during normal updates.
- OpenAPI contract tests run in CI.

## 18. Publish High-Intent Practice-Group Landing Pages — Candidate 45

**Blueprint**

Launch three focused pages, subject to actual coverage:

- Tax-sale surplus and related litigation.
- Foreclosure surplus and real-estate litigation.
- Probate/heir-related record research supporting surplus matters.

Each page includes:

- The practice-specific workflow.
- Real geographic coverage.
- A redacted memo or evidence-screen example.
- Time-saving capabilities without unsupported quantified claims.
- Clear $249/$449 calls to action.

**Files**

`src/app/for/[practice]/page.tsx`  
`content/practice-groups/`  
`src/components/CoverageProof.tsx`  
`src/components/PlanCTA.tsx`

**Acceptance criteria**

- No guaranteed recoveries, manufactured testimonials, or implied bar endorsements.
- All samples match product capabilities.
- Pages contain substantive distinct content, not keyword substitutions.
- Conversion events are measurable.
- Educational references to *Tyler* are reviewed and limited in scope.

## 19. Block Regressions with a Golden Evaluation Suite — Candidate 11

**Blueprint**

Maintain a versioned, consented or appropriately de-identified benchmark containing at least:

- 50 voicemail samples.
- 100 public-record documents.
- 30 ambiguous ownership/lien cases.
- 30 outreach-policy fixtures.
- 20 prompt-injection and cross-tenant access attempts.

Use dual-reviewed labels for high-impact legal or identity cases. Keep a held-out set separate from prompt tuning.

**Files**

`evals/datasets/manifest.json`  
`evals/run.ts`  
`evals/metrics.ts`  
`evals/baselines/`  
`.github/workflows/ai-evals.yml`

**Acceptance criteria**

- Every production model or prompt change runs the benchmark.
- Zero known prohibited sends in policy fixtures.
- Zero successful cross-tenant accesses in the security suite.
- Report critical-field precision, recall, and abstention—not only overall accuracy.
- The adjudicated set shows no unsupported surplus amounts or deadlines accepted as verified.
- Release approval considers latency and cost alongside quality.

Passing these tests is a release gate, not proof of universal correctness.

## 20. Deploy a Bounded Autonomous Sentinel — Candidate 33

**Blueprint**

Monitor:

- Authentication anomalies.
- API abuse and bulk-download spikes.
- Cross-tenant denial patterns.
- Source freshness failures.
- Queue backlog.
- AI spend anomalies.
- Unexpected fallback-provider use.
- Dependency and secret alerts.

Allow only predefined containment actions:

```text
Disable a specific API key
Pause a connector
Suspend an outbound campaign
Reduce a processing budget
Quarantine a suspicious artifact
```

Require human authorization for broad destructive or policy-changing actions.

**Files**

`src/security/sentinel.ts`  
`src/security/playbooks/`  
`config/security/sentinel-policy.yaml`  
`src/security/security-audit.ts`  
`.github/workflows/security.yml`

**Acceptance criteria**

- Sentinel cannot rewrite legal rules, grant itself permissions, or delete tenants.
- Containment actions are attributable, logged, and reversible where possible.
- High-severity alerts reach a tested owner channel.
- False-positive drills demonstrate recovery.
- Adversarial document/audio text cannot instruct Sentinel.
- Security logs minimize sensitive data and follow retention policy.

---

## Recommended implementation sequence

| Phase | Deliverables | Exit condition |
|---|---|---|
| **Foundation** | Gemini gateway, budgets, tenant isolation, idempotency, serverless runtime, evaluation harness | Safe processing with verified provider access and bounded cost |
| **Data credibility** | Source adapters, state packs, typed extraction, preliminary lien screening | Evidence-backed opportunities with honest coverage and review boundaries |
| **Revenue activation** | Enforced plans, sample funnel, practice pages, read-oriented REST API | Successful paid onboarding and first useful customer action |
| **Audio conversion** | Validated Voice intake, native audio, action memos, ethics and SMS gates | One fully tested inbound-to-approved-response workflow |
| **Operational hardening** | Sentinel, restore drills, spend/freshness dashboards, controlled exception recovery | Measured reliability and contribution margin |

**Bottom line:** move the AI execution layer to Gemini now, but preserve a truthful distinction between the consumer subscription and developer API capacity. The winning commercial offer is **trustworthy surplus intelligence delivered into attorney workflows**—with automation that stops safely when the evidence or permission is insufficient.