# Surplus Docket: Architecture and Revenue-Engine Review

**Review date:** September 7, 2026  
**Assessment type:** Design review based on the architecture, features, and pricing supplied in your request.

**Evidence limitation:** I cannot inspect the live website, repository, deployed API, OpenAPI document, workflow configurations, or customer journeys in this environment. Accordingly, this is **not a verified production audit**. The findings below distinguish architectural implications from controls that need supporting evidence. No vulnerability or compliance failure should be inferred as confirmed.

## Executive assessment

Surplus Docket’s strongest potential positioning is **“court-source-backed surplus opportunities, qualified for an attorney’s workflow”**, rather than simply a multistate lead feed.

The principal risks are:

1. **Legal-deadline overconfidence:** A mathematically correct date can still be legally incorrect if the engine selects the wrong proceeding, trigger, rule version, or exception.
2. **Unproven lead economics:** Attorneys need evidence that opportunities are current, unclaimed, actionable, and commercially viable—not merely scraped.
3. **Automation fragility:** GitHub Actions can support collection and scheduled triage, but it is not a durable queue or a continuously available REST API runtime.
4. **Excessive email autonomy:** Inbound email is untrusted input. Incorrect classification, prompt injection, and unauthorized outbound actions can create legal and reputational exposure.
5. **Conversion friction:** State coverage, feed overlap, lead distribution, data freshness, integration effort, and cancellation terms may matter more than the headline subscription price.

**Highest-impact recommendation:** Build a defensible evidence chain:

> Court source → normalized proceeding → qualified opportunity → versioned legal calculation → attorney review → CRM outcome.

That chain improves reliability, supports premium pricing, and gives prospective customers something concrete to trust.

---

# 1. Architecture assessment

## 1.1 Recommended reference architecture

```text
County sources / court records / inbound email
                    │
         Scheduled collection adapters
              GitHub Actions
                    │
          Immutable source evidence
                    │
       Normalization + quality validation
                    │
        Durable event queue / event log
                    │
       ┌────────────┼──────────────────┐
       │            │                  │
  Lead matching  Versioned rules   Email classification
  and scoring    and calculators  with restricted tools
       │            │                  │
       └────────────┼──────────────────┘
                    │
        Canonical operational database
                    │
      Managed serverless API + webhooks
                    │
       Customer portal / case management
                    │
      Attorney feedback and outcome data
```

GitHub Actions is suitable as an **ephemeral job runner**. Durable state, queues, API serving, and audit history should live outside individual workflow runs.

### Important terminology correction

“Zero local daemons” is a useful operational claim. “100% serverless GitHub Actions” needs qualification:

- GitHub-hosted runners require no customer-operated persistent servers.
- They are still job execution environments with scheduling, runtime, concurrency, and service limits.
- Scheduled workflows are not a guarantee of immediate or precisely timed execution.
- A continuously reachable REST API needs an independently available serving layer.

If Actions only performs background work while a managed platform serves the API, describe it as:

> **Managed serverless API with GitHub Actions–orchestrated ingestion and qualification.**

That is more accurate and easier for technically sophisticated customers to evaluate.

## 1.2 Python county scraping

### Primary failure modes

County data is heterogeneous and may include HTML tables, PDFs, scanned documents, changing URLs, inconsistent names, and separate sources for sale results and subsequent disbursements.

A scraper can run successfully while producing unusable data. Examples include:

- A redesigned table silently shifts the “surplus amount” column.
- An old PDF is republished and mistaken for a new opportunity.
- A case is duplicated because its docket number has inconsistent formatting.
- A surplus appears available even though a later order authorizes distribution.
- Tax-sale and mortgage-foreclosure records are assigned the same qualification logic.

### Required enhancements

**Separate adapters from domain logic.** Each county adapter should emit a common schema rather than its own interpretation of an actionable lead.

Recommended fields include:

```text
jurisdiction
county
court
proceeding_type
source_case_number
canonical_case_id
sale_date
source_reported_surplus_amount
currency
claim_status
source_url
source_published_at
fetched_at
last_verified_at
parser_version
evidence_hash
qualification_status
qualification_reason_codes
```

Important controls:

- Preserve source artifacts, subject to lawful access and retention policies.
- Store parser version and extraction provenance.
- Use deterministic duplicate detection plus reviewed entity matching.
- Represent unknown values explicitly; do not turn missing amounts into zero.
- Quarantine schema violations and unexpected volume changes.
- Detect stale sources even when HTTP requests return successfully.
- Reconcile against later claims, disbursement orders, and updated county lists where available.
- Respect access terms, rate limits, and restrictions; do not bypass access controls.

**Critical distinction:** “County-reported surplus” is not necessarily “recoverable amount available to this claimant.”

## 1.3 REST API and case-management ingestion

An endpoint such as `/api/v1/leads` is a starting point, not evidence of integration readiness.

### Production API controls to verify

| Area | Required control |
|---|---|
| Authentication | Tenant-scoped credentials, rotation, revocation, preferably scoped permissions |
| Authorization | Server-side enforcement of state coverage, plan access, and tenant boundaries |
| Pagination | Stable cursor pagination with documented ordering |
| Incremental sync | Durable change cursor or equivalent mechanism, including withdrawal/deletion events |
| Identity | Persistent lead and case identifiers across corrections |
| Reliability | Retries, documented rate limits, structured errors, availability monitoring |
| Freshness | Record-level verification timestamps distinct from API response timestamps |
| Contract | Versioned OpenAPI document validated against actual requests and responses |
| Auditability | Request IDs, customer-visible integration status, security-conscious logs |

For webhooks, add signed payloads, event IDs, replay protection, retries, dead-letter handling, and a recovery mechanism for missed events.

### Avoid the “real-time” ambiguity

A fast API does not make scraped records real-time.

Expose separately:

- **Source freshness:** When the originating record changed or was published, if known.
- **Collection freshness:** When Surplus Docket fetched it.
- **Verification freshness:** When actionability was last checked.
- **Delivery latency:** Time from ingestion to API/webhook availability.

Market the actual guarantee: for example, “available through the API shortly after collection,” unless upstream freshness supports a stronger promise.

---

# 2. Statutory calculation and compliance safeguards

## 2.1 The fundamental rule-selection problem

**FRCP 6(a) is not a universal deadline rule for FL, TX, GA, CA, NC, or TN surplus proceedings.**

It governs time computation within its federal scope, including qualifying statutes that do not specify a computation method. State surplus matters may instead depend on:

- A surplus-specific statute.
- State civil procedure.
- Tax-foreclosure or execution-sale provisions.
- Court orders.
- Applicable local rules.
- Service rules.
- Emergency orders and court closures.
- Nonjudicial procedures that do not follow ordinary civil filing rules.

A generic “add days, skip weekends, roll forward” engine is inadequate.

## 2.2 Use a legal rules registry

Each supported calculation should carry:

```text
rule_id
jurisdiction
court
proceeding_type
deadline_type
trigger_event_type
trigger_definition
authority_citations
authority_effective_from
authority_effective_to
computation_method
holiday_calendar_version
timezone
filing_method
exceptions
reviewed_by
reviewed_at
ruleset_version
```

Store the calculation itself separately:

```text
input_facts
input_evidence_references
selected_rule_version
calculated_date_or_timestamp
assumptions
warnings
review_status
calculation_trace
```

Do not silently overwrite historical results when rules change. Recalculate affected records as new versions, retain the old result, and notify subscribers when a material date changes.

## 2.3 Specific safeguards

### A. Establish applicability before doing arithmetic

Require enough facts to identify:

- State and court.
- Proceeding type.
- Deadline type.
- Legally operative trigger.
- Relevant service or notice circumstances.
- Any case-specific order.

If required facts are missing, return:

> **Insufficient facts to calculate—attorney review required.**

A disclaimer is not a substitute for refusing an unsupported calculation.

### B. Distinguish the underlying events

Sale date, confirmation date, deposit date, notice date, service date, and order-entry date are not interchangeable.

A scraper should not infer the legally operative event merely because it found one convenient date.

### C. Handle rule-specific computation

Testing must cover, where applicable:

- Whether the triggering day is excluded.
- Calendar days versus business days.
- Weekends and qualifying legal holidays.
- Month- and year-based periods.
- Electronic versus nonelectronic filing cutoffs.
- Court timezone.
- Clerk-office inaccessibility.
- Service-related extensions only when the applicable rule permits them.

For federal calculations, **do not automatically add three days for electronic service**. FRCP 6(d) is service-method-specific and does not provide that extension for ordinary electronic service.

### D. Do not assume every statutory period rolls forward

Some claim windows, substantive limitations, or nonjudicial deadlines may not receive the extension a generic procedural engine would apply. Applicability needs legal review, not an arithmetic default.

### E. Validate local-rule and order interactions

Model applicability and conflicts rather than using a simplistic universal hierarchy. A local rule or case-specific order does not automatically override controlling law.

## 2.4 Six-state support requires a narrower support matrix

“Supports Florida” should not imply “supports every Florida county, proceeding, and deadline.”

Publish a matrix such as:

| State | Proceeding types | Counties/sources | Automated calculations | Human review required | Last legal review |
|---|---|---|---|---|---|
| FL, TX, GA, CA, NC, TN | Explicitly enumerated | Explicitly enumerated | Named calculations only | Defined exceptions | Date/version |

Have appropriately qualified counsel validate each supported calculation family.

**Recommended release gate:** No calculated deadline reaches a customer unless it has a supported rule version, traceable trigger facts, and explicit review status.

---

# 3. Autonomous email triage and circuit-breakers

## 3.1 Treat inbound messages as adversarial data

An email can contain spoofed instructions, malicious attachments, prompt injection, or misleading claims about a court deadline.

The classifier may summarize a message. It must not treat message text as authority to:

- Change system policy.
- Reveal credentials or another tenant’s information.
- Send files to an external address.
- Alter legal calculations.
- Delete evidence.
- Accept representation, negotiate, or settle a matter.

## 3.2 Separate classification from execution

A safer design has three stages:

1. **Extract:** Parse and classify using a constrained output schema.
2. **Authorize:** Apply deterministic policy outside the model.
3. **Execute:** Run only an approved action with scoped credentials and an audit record.

Routine internal labeling may be automatic. Outbound substantive communications require substantially stronger controls.

### Suggested action policy

| Action | Default |
|---|---|
| Label, summarize, route internally | Automatic after validation |
| Create an internal review task | Automatic with deduplication |
| Mark a lead potentially stale | Automatic provisional flag |
| Send approved receipt acknowledgment | Controlled automation |
| Send individualized legal advice or deadline assertions | Human approval |
| Contact a claimant or opposing party substantively | Human approval and applicable-policy checks |
| Accept representation, settle, transfer funds, or file documents | Prohibited for the triage agent |
| Permanently delete source evidence | Prohibited |

## 3.3 Required circuit-breakers

- **Action-volume breaker:** Pause outbound activity after abnormal volume.
- **Error-rate breaker:** Stop execution after repeated authorization, provider, or parsing failures.
- **Loop breaker:** Detect auto-replies, bounces, and repeated conversation events.
- **Attachment breaker:** Quarantine suspicious, encrypted, unsupported, or oversized attachments.
- **Content-risk breaker:** Escalate legal commitments, bank changes, urgent deadline claims, and threats.
- **Data-quality breaker:** Suppress factual outbound claims when the underlying lead is stale or disputed.
- **Budget breaker:** Limit model calls, attachment processing, and external-service spend.
- **Kill switch:** Provide immediate global, tenant, and mailbox-level suspension.

Persist breaker state outside Actions. A failed run or restart must not reset a safety limit.

### Durable processing requirements

Use provider message IDs, mailbox identity, event versions, and an action ledger to prevent duplicate effects. Do not rely on workflow success status alone: a send can succeed immediately before a job fails.

Use least-privilege mailbox permissions. Separate read/label permissions from send permissions where the provider supports that distinction.

---

# 4. Conversion bottlenecks for asset recovery attorneys

## 4.1 Buyers need actionability evidence

A prospective attorney is likely asking:

- Are these opportunities current?
- Is the surplus still available?
- How many other customers receive the same lead?
- Which counties are covered consistently?
- Is the amount worth the attorney’s time?
- Is the claimant identifiable and legally eligible?
- Can this fit into the firm’s intake and conflict-check workflow?

### High-impact conversion assets

**1. An annotated sample lead**

Show the actual fields, source evidence, verification timestamp, known uncertainties, and qualification rationale.

**2. A coverage-and-freshness page**

List supported counties, proceeding types, historical collection reliability, and known gaps.

**3. Clear distribution terms**

Disclose whether leads are exclusive, shared without limits, or capacity-limited. Do not imply exclusivity unless operationally enforced.

**4. A low-friction first import**

Provide CSV templates, a sandbox, and tested integration instructions. For the most-used case-management platform among actual customers, build a native connector before expanding speculative integration coverage.

**5. Verified customer economics**

Report outcomes only with a clear methodology. Distinguish a sourced lead, a contacted person, an eligible claimant, a signed client, and a completed recovery.

## 4.2 Pricing assessment

| Plan | Monthly | Annual | Effective annual monthly rate | Savings vs. 12 monthly payments |
|---|---:|---:|---:|---:|
| Tri-State Core Feed | $249 | $2,388 | $199 | $600 / 20.1% |
| 6-State + REST API | $449 | $4,188 | $349 | $1,200 / 22.3% |

### Potential friction

- **“Tri-State” is ambiguous** unless the three included states—or the selection mechanism—are explicit.
- The higher tier bundles geographic expansion with API access. A single-state firm may need automation but not six-state coverage.
- Six-state coverage may not justify an upgrade for a firm whose practice footprint is narrower.
- Annual billing requires more trust before lead quality is proven.

### Recommended tests

- State coverage as the base package, with an API add-on.
- A representative sample or constrained evaluation period.
- A transparent shared-lead policy near pricing.
- Annual upgrade offers after successful activation.
- Clear seat limits, export rights, usage limits, renewal terms, and post-cancellation data access.

Treat these as experiments, not automatic improvements. Track downstream retention and contribution margin, not checkout conversion alone.

A useful economics model is:

> Expected contribution per delivered lead  
> = probability of engagement × probability of successful recovery given engagement × expected collected fee  
> − acquisition, outreach, and matter-handling costs.

Use customer cohort evidence for those inputs; do not present hypothetical recoveries as assured ROI.

## 4.3 Legal-market controls that support conversion

Public court data can still involve sensitive personal information. Attorney customers will also care about applicable solicitation, advertising, fee-sharing, and lead-generation restrictions.

Recommended safeguards:

- Position records as opportunities requiring independent review, not guaranteed clients.
- Avoid claims that an attorney has been endorsed or recommended unless supportable.
- Keep purchasing access distinct from case acceptance.
- Provide suppression and correction workflows.
- Review applicable privacy, outreach, and professional-conduct requirements before automating claimant contact.

---

# 5. Prioritized architectural enhancements

| Priority | Enhancement | Primary benefit | Acceptance evidence |
|---|---|---|---|
| **P0** | Evidence-backed, versioned calculation engine | Reduces dangerous legal-date errors | Every released calculation has authority, inputs, trace, and review status |
| **P0** | Independent email policy engine and kill switches | Prevents unauthorized actions | Adversarial-email and duplicate-send tests pass |
| **P0** | Durable database, queue, and action ledger | Makes ephemeral jobs reliable | Crash/retry tests show no lost work or duplicate side effects |
| **P0** | Tenant isolation and credential controls | Protects customer and lead data | Cross-tenant authorization tests and rotation exercises |
| **P1** | Record-level freshness and evidence display | Improves attorney trust | Customers can inspect source and verification history |
| **P1** | Withdrawn/changed-lead propagation | Prevents stale CRM records | Downstream clients receive corrections and withdrawals |
| **P1** | Supported-proceedings and county matrix | Sets defensible expectations | Published scope matches operational monitoring |
| **P1** | OpenAPI contract testing and sandbox | Reduces integration friction | Example client completes initial and incremental sync |
| **P1** | Activation and outcome instrumentation | Reveals revenue bottlenecks | Funnel links first useful lead to retention |
| **P2** | Pricing and packaging experiments | Improves fit by firm type | Cohort analysis includes conversion, churn, and margin |

## Additional GitHub Actions hardening

- Prefer short-lived cloud credentials through OIDC where supported.
- Pin third-party actions to reviewed immutable revisions.
- Restrict workflow permissions.
- Isolate untrusted pull-request execution from production secrets.
- Protect deployment environments and production branches.
- Keep sensitive records out of public artifacts and verbose logs.
- Use workflow concurrency controls alongside database-level locking.
- Alert on missed schedules and aging backlogs, not only failed jobs.

---

# 6. Practical 90-day implementation sequence

### Days 1–30: Establish safety and truth

- Inventory every source, calculation, workflow, permission, and customer-facing claim.
- Publish accurate state/county/proceeding coverage.
- Add evidence references, verification timestamps, and unknown-value handling.
- Gate unsupported calculations.
- Limit autonomous email to low-risk actions.
- Establish durable processing state and a tested kill switch.

### Days 31–60: Strengthen delivery

- Add contract-tested API synchronization and correction events.
- Implement parser-drift and source-staleness monitoring.
- Add secure webhooks and integration diagnostics.
- Complete legal validation of the most commercially important supported calculations.
- Publish annotated sample leads and technical documentation.

### Days 61–90: Improve conversion and economics

- Instrument time to first useful lead and first successful import.
- Collect structured rejection reasons from attorneys.
- Test packaging based on observed firm needs.
- Connect qualification scores to actual customer outcomes.
- Run recovery, tenant-isolation, malicious-email, and workflow-retry exercises.

## Evidence required for a verified audit

A production assessment should examine:

- Website, pricing, onboarding, checkout, and cancellation flows.
- Python adapters, schemas, representative source artifacts, and extraction tests.
- Legal rules registry, counsel reviews, and calculation test fixtures.
- Deployed OpenAPI document and sandbox credentials.
- GitHub workflow YAML, IAM policies, secret handling, and run history.
- Email permissions, agent instructions, execution policies, and action logs.
- Availability, freshness, backlog, and incident metrics.
- Customer agreements, lead-distribution terms, and privacy/retention policies.
- Conversion, retention, lead rejection, and customer outcome cohorts.

## Bottom line

Surplus Docket’s proposed architecture is viable **if GitHub Actions remains orchestration rather than the entire runtime and state layer**.

The strongest product investment is not additional scraping volume. It is **provable actionability**: current source evidence, precise support boundaries, reviewable legal calculations, reliable CRM updates, and tightly bounded email automation.

Those capabilities directly address both sides of the business: operational risk and an attorney’s willingness to subscribe.