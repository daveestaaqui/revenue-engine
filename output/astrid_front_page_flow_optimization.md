# Surplus Docket: Homepage Flow Redesign

**Yes. The front page should become a guided evaluation—not a catalog of everything the platform can do.**

The attorney’s decision sequence is:

> **Is this relevant to my practice? → Can I inspect the records? → What has—and has not—been checked? → Is my jurisdiction covered? → Is the subscription worth evaluating?**

The current page interrupts that sequence with repeated calculators, competing value propositions, and language that can imply legal conclusions the platform should not make.

**Recommended positioning:**
> **Relevant records. Inspectable sources. Explicit uncertainty. Faster attorney review.**

*This assessment is based on the supplied homepage structure, not a live inspection of the HTML, data, or checkout behavior.*

---

## 1. Critical Review: Where the Current Flow Breaks

| Current element | Friction or trust problem | Recommended correction |
|---|---|---|
| Broad hero followed by six state pills | Geography appears before the attorney understands practice fit. Pills may look like navigation or imply uniform coverage. | Route by practice immediately after the hero. Keep state filtering within the docket. |
| Technical specifications bar | Delivery times, file formats, and APIs appear before the user has seen a useful record. | Reduce to a compact, substantiated facts strip. Move technical depth into methodology and plans. |
| “Live” preview containing sample dockets | “Live,” “sample,” and “verified” describe different things. Combining them can undermine trust. | Label the preview according to its actual provenance and update behavior. |
| “Scrubbed equity,” “liens satisfied,” “clean equity” | These can imply a title examination, lien-priority determination, or assurance of recoverability. | Show source-backed observations, review scope, and unresolved questions—not legal clearance. |
| Toolkit banner before the main product is explained | A download becomes an exit ramp before the subscription’s value is established. | Integrate the toolkit with a single, optional attorney-review tool. |
| Two calculators | The first suggests legal precision; the second shifts the proposition toward speculative earnings. | Replace both with one source-backed **Claim Review Worksheet**. |
| Core features after the first calculator | Essential product understanding arrives too late. | Explain features through the record-review workflow immediately after the preview. |
| Coverage buried mid-page | Attorneys must scroll too far to determine whether the service is relevant. | Retain state filtering early; place authoritative coverage details directly after methodology. |
| Competitive comparison matrix | Broad superiority claims require evidence and repeat the features section. | Remove from the main page. Let a real record and transparent methodology demonstrate the difference. |
| Late *Tyler* section and “$8B+ unlocked” | The legal context arrives as a promotional catalyst rather than a carefully bounded explanation. | Put a short, sourced legal-context note inside methodology. Remove the dollar claim unless independently substantiated and precisely qualified. |
| Pricing after substantial educational content | Qualified buyers encounter too many diversions before the purchase decision. | Bring pricing forward by consolidating tools, features, and legal context. |
| “Save 20% / 2 Months Free” | The supplied annual prices represent approximately **16.7% savings**, not 20%. | Use “Two months included with annual billing” or “Save approximately 17%.” |
| “National 6-State” | “National” overstates six-state coverage. | Rename **Six-State + API**. |
| Generic security badges | “Stripe Verified Billing,” “256-Bit SSL,” and PCI language may imply unsupported endorsements or platform-wide certification. | Replace with specific, documented payment and security statements. |

### The most important trust correction

**Do not rely on footer disclaimers to qualify stronger claims higher on the page.**

If a record says “clean equity,” a later “no legal advice” notice does not restore the distinction between a screening indicator and a legal conclusion.

---

## 2. Exact Recommended Section Order

Use this order in `site/index.html`:

| Order | Section | Psychological and legal rationale |
|---:|---|---|
| 1 | **Simplified navigation** | Establishes clear routes without presenting every resource as an equal-priority decision. |
| 2 | **Hero + compact facts strip** | States the audience, product, and trial terms before asking for commitment. |
| 3 | **Three practice pathways** | Lets attorneys recognize their matter type immediately, without forcing them off the homepage. |
| 4 | **Inspectable docket preview** | Provides evidence before promotional explanation. |
| 5 | **Methodology: what the platform organizes, flags, and leaves unresolved** | Explains the evidence while preventing screening from being mistaken for legal adjudication. Includes a brief *Tyler* context note. |
| 6 | **Coverage and availability** | Answers the remaining fit question: which jurisdictions, proceedings, and sources are actually supported? |
| 7 | **Claim Review Worksheet + practitioner resources** | Demonstrates practical usefulness without speculative returns or false deadline certainty. |
| 8 | **Pricing and trial** | Converts after relevance, evidence, boundaries, and coverage have been established. |
| 9 | **Decision-focused FAQ** | Resolves final purchase objections close to the subscription CTA. |
| 10 | **Concise compliance and use limitations** | Reinforces operating boundaries and links to complete policies. |
| 11 | **Structured footer** | Supports deeper research without burdening the primary conversion path. |

**Remove standalone sections for:** the specifications bar, screening benchmark, toolkit banner, core features, comparison matrix, ROI calculator, and Supreme Court “catalyst.” Preserve useful material inside the sections above.

---

## 3. Component Specifications and Suggested Microcopy

### 1. Navigation

**Desktop structure**

- Logo
- Docket Preview
- How It Works
- Coverage
- Pricing
- Resources dropdown:
  - Practice guides
  - Practitioner toolkit
  - Methodology
  - REST API documentation
- Account / Billing
- **Start 7-Day Trial**

**Implementation requirements**

- Use “Live Docket” only if the destination actually displays current records.
- If the account link opens only Stripe’s billing portal, label it **Manage Billing**, not “Subscriber Portal.”
- Place pricing disclosure beside the hero and pricing CTAs; do not depend on navigation space to explain billing.

---

### 2. Hero

**Eyebrow**

> PUBLIC-RECORD INTELLIGENCE FOR SURPLUS PROCEEDS COUNSEL

**H1**

> Relevant surplus records. Ready for attorney review.

**Subhead**

> Review source-linked tax-sale and foreclosure surplus records across supported jurisdictions in Florida, Texas, Georgia, California, North Carolina, and Tennessee—with record details and review limitations in view.

Use this wording only to the extent those proceeding types are actually supported. Otherwise narrow it to the available datasets.

**Primary CTA**

> Start 7-Day Trial

**Adjacent disclosure**

> $0 today. $249/month beginning on day 8 unless canceled before the trial ends.

This should apply specifically to the Core plan if that is the only confirmed trial offer. Do not imply identical trial terms for the higher tier without confirming them.

**Secondary CTA**

> Inspect Docket Preview ↓

**Compact facts strip**

> Six-state coverage footprint · Source-linked public records · CSV / Excel exports · API on eligible plans

Each fact must reflect actual availability. Move the precise feed schedule into methodology and plan details.

---

### 3. Practice Pathways

**Heading**

> Start with your practice.

Use three compact, equal-weight cards. These are contextual routes, not alternative products or a required onboarding step.

| Card | Suggested description | CTA and destination |
|---|---|---|
| **Tax-Sale Litigation** | Review tax-sale surplus research considerations, governing authorities, and jurisdiction-specific claim procedures. | **Explore tax-sale practice →** `/for/tax-sale-litigation.html` |
| **Probate & Estate Surplus** | Evaluate matters involving deceased owners, estate authority, and potential heirship documentation. | **Explore estate matters →** `/for/probate-estate-surplus.html` |
| **Mortgage Foreclosure** | Review judicial foreclosure surplus issues, claimant standing, and competing lien interests. | **Explore foreclosure practice →** `/for/mortgage-foreclosure.html` |

**Boundary:** A practice guide does not prove corresponding data coverage. Each landing page should distinguish educational guidance from records or enrichment actually available in the product.

**Layout:** Three columns on desktop; three concise stacked cards on mobile. No carousel and no additional pricing CTAs.

---

### 4. Docket Preview

**Heading**

> Inspect the record before you subscribe.

**Subhead**

> Review the reported amount, inspect the underlying source, and see what remains to be established.

**Labeling rule**

Choose the correct label:

- **Live docket preview** — only for current, connected data.
- **Sample docket records** — for curated examples.
- **Illustrative record** — for synthetic demonstrations.

Never use these interchangeably.

**Recommended controls**

- Search
- State
- Proceeding type, where reliably classified
- Minimum **reported surplus**
- Reset
- Download sample CSV

**Recommended fields**

- State / county
- Proceeding type
- Case or sale reference
- Reported surplus
- Source date, where available
- Last source check
- Review status
- **Open source record**

**Expandable record panel**

- Source authority and document reference
- Extracted record details
- Observations and supporting references
- Missing information
- Conflicting information
- Stated review scope

Recommended status labels:

> Source linked · Field checked against source · Further review required

Use “field checked” only when that check actually occurred. Avoid blanket “verified” badges.

**Inline limitation**

> Reported surplus is not a determination of available funds, claimant entitlement, lien priority, or recoverable fees.

If a link opens only a clerk search portal, label it **Open clerk search**, and display the reference needed to locate the case.

---

### 5. Methodology and Review Boundaries

**Transition from preview**

> The source record is the starting point—not the legal conclusion.

**Heading**

> See what has been organized. Know what still needs review.

Replace the “underwater versus clean equity” comparison with **the same record before and after organization**:

| Source material | Organized attorney-review view |
|---|---|
| Clerk ledger entry | Normalized record details |
| Separate case references | Linked source references, where available |
| Reported dollar amount | Amount with source and date |
| Mentioned lien or discharge | Documented observation with supporting reference |
| Missing or ambiguous information | Explicit unresolved-review items |

**Three-step process**

1. **Collect and reference**  
   Identify the public source, proceeding, and retrieval date.

2. **Normalize and flag**  
   Organize fields and surface documented inconsistencies or review questions.

3. **Review and export**  
   Let counsel inspect the evidence and move selected records into the firm’s workflow.

Only describe capabilities that are implemented and auditable.

**Boundary panel**

> **The platform does not determine:** legal entitlement, lien priority, final distributable funds, or whether a claim should be filed.

Place delivery cadence, export formats, and API capabilities here as supporting workflow details. If delivery follows daylight saving time, use **7:00 a.m. Eastern Time**, not year-round “EST.” Distinguish feed delivery time from the freshness of every underlying source.

#### Where *Tyler v. Hennepin County* belongs

Use a small legal-context inset **at the end of this section**, not a standalone sales block.

> **Legal context: retained tax-sale equity**  
> In *Tyler v. Hennepin County*, 598 U.S. 631 (2023), the Supreme Court unanimously held that the owner stated a Takings Clause claim concerning the county’s retention of value beyond her tax debt. The decision does not establish eligibility for every surplus claim or replace jurisdiction-specific procedures and deadline analysis.

Link to the official opinion and the tax-sale practice guide. Do not present *Tyler* as a universal foreclosure rule or a guarantee that funds are collectible.

---

### 6. Coverage and Availability

**Heading**

> Confirm coverage for your jurisdiction and proceeding.

Replace six long statutory cards with a compact coverage table or accordion.

**Required fields**

- State
- Supported proceeding types
- Monitored counties or sources
- Update cadence
- Known limitations
- Available plan
- Last coverage review date

**Microcopy**

> Coverage varies by county, proceeding type, and source availability. A listed state does not mean every county or surplus matter is monitored.

Link to the official clerk directory as a secondary resource.

For **Tri-State Core**, name the three included states explicitly. If users choose them, state the selection rules. Do not leave “Tri-State” undefined at checkout.

---

## 4. Replace Both Calculators with One Claim Review Worksheet

### Purpose

**Help counsel structure an initial review—not estimate a windfall.**

**Heading**

> Build a source-backed claim review worksheet.

**Intro**

> Select the jurisdiction and proceeding to review potentially relevant authorities, missing facts, and filing considerations.

### Inputs

**Required first**

- State
- Proceeding type
- County, when local procedure matters

**Conditional inputs**

- Applicable event type and date
- Reported surplus amount
- Claimant capacity: former owner, estate representative, lienholder, or other
- Whether competing claims or interests are known

Do not use one generic “sale date” field for every jurisdiction. Relevant triggers may depend on a sale, deposit, notice, order, or another event.

### Outputs

1. **Potentially applicable authorities**
   - Official links
   - Applicability conditions
   - Content last-reviewed date

2. **Missing facts and documents**
   - Standing or estate-authority questions
   - Required source documents
   - Matters requiring additional investigation

3. **Deadline review**
   - Trigger event used
   - Rule and assumptions
   - A calculated candidate date only where the necessary rule and inputs are supported

4. **Fee-rule review**
   - Relevant restrictions or authorities, when applicable
   - Clear distinction between attorney compensation and restrictions on other recovery-service arrangements

5. **Competing-interest review**
   - Questions and source references
   - No automated declaration of priority

6. **Exportable worksheet**
   - Inputs
   - Sources
   - Assumptions
   - Unresolved issues
   - Generation date

### Required safeguards

- **No monthly claim-volume slider.**
- **No annual gross-fee projection.**
- **No default assumption that surplus equals recoverable client proceeds.**
- **No universal statutory fee-cap percentage.**
- **No visual “lien waterfall” that assigns legal priority automatically.**
- **No automatic subtraction of historical mortgage balances from an already reported surplus.**

When the inputs do not support a calculation, show:

> A deadline cannot be calculated from the information provided. Confirm the applicable trigger and procedural rule.

When supported:

> **Candidate date for attorney review:** [date]  
> Based on [trigger] and [authority], subject to the assumptions below.

A “candidate” label alone is insufficient: the implementation must account for applicable computation rules and exceptions or abstain from producing a date.

### Toolkit integration

Place these links beneath the worksheet:

- **Open filing checklist**
- **Review practice-specific templates**
- **Visit practitioner toolkit**

Keep the tool collapsed by default on the homepage. It should reward interested users without becoming a mandatory detour before pricing.

---

## 5. Pricing: Convert on Workflow Value

**Transition**

> If the records, sources, and coverage fit your practice, evaluate the feed in your own workflow.

**Heading**

> Choose the coverage your firm needs.

### Plan presentation

| | Tri-State Core | Six-State + API |
|---|---|---|
| Monthly | $249/month | $449/month |
| Annual | $2,490 billed annually | $4,490 billed annually |
| Coverage | Name the included states or selection rules | Name all six states |
| Data access | State actual inclusions | State actual inclusions |
| API | State availability | State actual limits and access terms |

**Annual toggle**

> Annual — two months included

Do not display “Save 20%” at these prices.

**Core trial CTA**

> Start Core 7-Day Trial

**Immediately adjacent**

> $0 today. Then $249/month beginning on day 8 unless canceled before the trial ends.

For annual selection and the higher tier, display their actual trial eligibility, billing amount, and charging date. Do not assume the monthly Core terms apply.

**Trust copy**

> Payments processed by Stripe.  
> Manage billing through the billing portal.

Use broader security or compliance claims only when documented and accurately scoped.

---

## 6. FAQ, Compliance, and Footer

### FAQ: answer purchase questions

Use five concise questions:

1. **Are these current records, sample records, or exclusive leads?**
2. **What does a screening or review status actually mean?**
3. **Which counties and proceeding types are included in my plan?**
4. **How current are the records, and how can I inspect their sources?**
5. **When does the trial convert, and how do I cancel?**

Do not hide trial terms exclusively in the FAQ.

### Compliance

Replace four promotional-looking cards with a restrained limitations panel:

> Surplus Docket organizes public-record information for professional review. Records may be incomplete, delayed, or superseded. The platform does not provide legal advice or determine claimant entitlement, lien priority, or recoverability.

Link to full methodology, permitted-use/FCRA restrictions, terms, privacy, and applicable data policies. A disclaimer does not itself establish regulatory compliance.

### Footer

Group links under:

- Practice areas
- Jurisdictions
- Product and documentation
- Company and legal

Avoid repeating the full navigation as an undifferentiated link wall.

---

## 7. Implementation Priorities

### P0 — Correct trust risks

- Remove “clean equity,” unsupported “verified,” and automatic priority conclusions.
- Correct annual savings and “National” plan naming.
- Align “live” and “sample” labels with the actual data.
- Make trial conversion terms explicit.
- Remove or substantiate security and market-size claims.

### P1 — Rebuild the narrative

- Add practice routing beneath the hero.
- Put the docket before methodology.
- Consolidate features into the methodology workflow.
- Move coverage ahead of tools and pricing.
- Fold *Tyler* into legal context.
- Eliminate the standalone comparison and ROI sections.

### P2 — Implement the worksheet and measurement

Track:

- Practice-pathway clicks
- Source-record opens
- Coverage checks
- Worksheet engagement
- Pricing views
- Trial starts and completed activations
- Trial-to-paid conversion
- Cancellations associated with coverage or expectation mismatch

Evaluate **qualified adoption**, not trial clicks alone.

---

## Bottom Line

The homepage should make a narrower, stronger promise:

> **We organize relevant public records, expose the sources, and make unresolved questions visible—so your firm can review matters more efficiently.**

The resulting conversion arc is:

**Practice fit → inspectable evidence → transparent methodology → confirmed coverage → practical review support → clearly priced evaluation.**

That is a more coherent front page—and a more defensible legal-technology business proposition.