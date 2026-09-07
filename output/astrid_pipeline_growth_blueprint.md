# Surplus Docket: Commercial Growth & Platform Authority Master Plan

**Strategic mandate:** Position Surplus Docket as **source-linked surplus intelligence for legal teams**—not a recovery service, an automated title opinion, or a substitute for counsel.

The commercial advantage should be straightforward:

> **Find potentially relevant surplus matters earlier, review the supporting records faster, and distinguish actionable leads from unresolved procedural questions.**

This plan treats the implementation details you supplied as internal facts, not independently audited claims. Statutory copy should receive jurisdiction-specific legal review before publication.

---

## 1. Establish the Claims, Compliance & Conversion Foundation

### A. Resolve these items before scaling distribution

| Item | Required action |
|---|---|
| **“$3.2M in verified surplus funds”** | Substantiate with a dated, deduplicated register of source records. Distinguish historical sale surplus, currently reported balances, claimed funds, and funds still available. Do not publish the number until approved. |
| **“Verified”** | Publish a methodology explaining exactly what was verified, against which source, and when. Verification must not imply entitlement, recoverability, or an undisputed balance. |
| **Florida “60-day claim window”** | Remove this as a blanket statement from the mortgage page. Review current Fla. Stat. §§ 45.031–45.033, applicable amendments, court orders, and claimant-specific requirements before stating any deadline. |
| **“Lien priority screening”** | Describe as preliminary identification of recorded interests and potential review issues—not a priority determination, title examination, or title insurance product. |
| **“Chronological Evidence Graph”** | Publish the launch release only after the advertised graph functionality is live and acceptance-tested. Chronology alone does not establish legal priority. |
| **Six-state coverage** | Publish a county/source coverage matrix. “Six states” must not imply complete coverage of every county or every proceeding. |
| **Pricing** | Confirm billing cadence, Tri-State selection rules, seats, exports, API quotas, trial restrictions, taxes, and cancellation terms before publishing comparative offers. |
| **AI processing** | Verify that the configured Gemini model remains supported and meets current operational requirements. Treat model choice as replaceable infrastructure, not the principal value proposition. |

### B. Create a reusable claims register

Every material public claim should have:

```text
claim_id
approved_wording
source_or_calculation
coverage_and_exclusions
verified_at
expires_or_review_due_at
approver
approved_channels
```

Examples include fund totals, source counts, refresh frequency, feature availability, coverage, and customer results.

**Rule:** Unapproved claims cannot enter email templates, landing pages, articles, or press releases.

### C. Platform-wide positioning and disclaimer

**Primary headline**

> Source-linked surplus intelligence for legal teams.

**Supporting copy**

> Monitor covered tax-sale and foreclosure surplus records, identify potential estate-related matters, and review preliminary lien flags alongside their supporting sources.

**Short disclaimer**

> Surplus Docket provides research and workflow software, not legal advice, title opinions, or representation. Records may be incomplete or change after retrieval. Counsel must independently verify balances, ownership, standing, priority, and deadlines.

Place the disclaimer near material product claims and in sample reports—not exclusively in the footer.

---

# 2. High-Converting Attorney Outreach

## A. Segmentation and sequencing rules

The supplied pipeline totals **1,373 practices**:

| State | Practices |
|---|---:|
| Florida | 423 |
| Texas | 291 |
| California | 222 |
| Georgia | 166 |
| North Carolina | 153 |
| Tennessee | 118 |

These are **prospecting records, not customers or product-performance evidence**.

Before enrollment, add:

- Primary practice group and secondary practice group.
- State and relevant county footprint.
- Named attorney or appropriate operational contact.
- Evidence of practice fit, with source URL and verification date.
- Email validation status and prior-contact history.
- Suppression, objection, and unsubscribe status.
- Actual Surplus Docket coverage relevant to that firm.

**Sequence structure:** Three messages over approximately 12 business days: **Day 1, Day 5, Day 12**.

**Stop immediately** after a reply, opt-out, complaint, hard bounce, trial signup, or booked discussion. A firm should not receive overlapping practice-area sequences.

### Personalization standard

Use an observable professional fact:

> “Your firm lists contested probate matters among its practice areas.”

Do not invent familiarity:

> “I’ve been following your excellent work for years.”

Avoid inserting a deceased owner’s name, home address, alleged inheritance, or estimated recovery into a cold email.

---

## B. Sequence A: Tax Sale & Excess Proceeds Litigators

**Destination:**  
`https://surplusdocket.com/for/tax-sale-litigation.html`

**Core pain:** Fragmented records, proceeding-specific claim rules, uncertain availability, and lien-related triage.

### Email 1 — Source visibility

**Subject:** Tax-sale surplus records in {{state}}

Hi {{first_name}},

Your firm lists {{verified_practice_description}} among its services.

Surplus Docket organizes surplus records from covered jurisdictions so legal teams can review the source, reported amount, and retrieval date before deciding whether a matter merits investigation.

The distinction matters: a reported surplus is not the same as an available, recoverable claim.

Here is our tax-sale research workflow:  
https://surplusdocket.com/for/tax-sale-litigation.html

Would a source-linked sample from a covered {{state}} jurisdiction be useful?

{{sender_signature}}

**Proof asset:** A real, redacted record with its source, retrieval date, procedural classification, and unresolved questions.

### Email 2 — Procedure, not just a dollar figure

**Subject:** A surplus amount is only the starting point

Hi {{first_name}},

Following up on the tax-sale workflow.

The research burden often starts after finding the amount: Which proceeding produced it? Who may claim? What recorded interests require review? Has the balance changed?

Our record view is designed to keep source facts separate from preliminary screening flags and unanswered questions.

The workflow also distinguishes Florida tax-deed, Texas tax-sale, and California tax-defaulted-property procedures rather than treating them as interchangeable.

Would you prefer a sample record or the current county-coverage list?

{{sender_signature}}

### Email 3 — Low-pressure close

**Subject:** Close the loop on {{state}} coverage?

Hi {{first_name}},

One final note.

If tax-sale surplus work is relevant to your practice, the most useful first step is checking whether our covered sources match your jurisdictions—not scheduling a broad product demo.

Coverage and workflow details are here:  
https://surplusdocket.com/for/tax-sale-litigation.html

Reply with a county if you would like us to confirm current coverage. Otherwise, I will close the loop.

{{sender_signature}}

### Landing-page copy requirements

**H1:**  
> Tax-sale surplus intelligence built for legal review.

**Subhead:**  
> Review covered public records, source-linked surplus amounts, and preliminary lien flags without confusing a potential opportunity with an established claim.

**Primary CTA:** `Review a source-linked sample`  
**Secondary CTA:** `Check jurisdiction coverage`

**Authority block:**

- Florida: Fla. Stat. § 197.582.
- Texas: Tex. Tax Code §§ 34.03–34.04.
- California: Cal. Rev. & Tax Code §§ 4674–4676, as applicable.
- *Tyler v. Hennepin County*, 598 U.S. 631 (2023): explain the constitutional issue without suggesting that the decision eliminates state claim procedures or guarantees recovery.

---

## C. Sequence B: Probate & Estate Planning Litigators

**Destination:**  
`https://surplusdocket.com/for/probate-estate-surplus.html`

**Core pain:** A potentially valuable asset is disconnected from the estate file; authority, heirship, and standing remain unresolved.

### Email 1 — Potential estate assets

**Subject:** Surplus records involving deceased owners

Hi {{first_name}},

Your firm’s {{verified_probate_service}} work appears relevant to a recurring research problem: a surplus record may identify a former owner without resolving whether an estate is open or who has authority to act.

Surplus Docket helps legal teams identify records for further estate-related review. It does not determine heirship or establish a right to the funds.

Our probate workflow is here:  
https://surplusdocket.com/for/probate-estate-surplus.html

Would a redacted example showing the record-to-estate research steps be useful?

{{sender_signature}}

### Email 2 — Authority before action

**Subject:** Finding the record does not establish standing

Hi {{first_name}},

For estate-related surplus matters, the amount is only one part of the file.

Counsel may still need to determine whether administration is required, whether existing letters remain effective, whether a summary procedure is available, and whether additional interested parties must receive notice.

Our preliminary workflow highlights missing information rather than labeling someone an entitled heir.

Would your team find an estate-intake checklist more useful than a product walkthrough?

{{sender_signature}}

### Email 3 — Fit check

**Subject:** Relevant to your probate litigation intake?

Hi {{first_name}},

I will close the loop after this note.

Surplus Docket is most relevant where a firm wants to investigate potential estate assets and can independently evaluate authority, beneficiaries, creditors, and the applicable surplus procedure.

The practice-specific overview is here:  
https://surplusdocket.com/for/probate-estate-surplus.html

If this belongs with another attorney on your team, feel free to forward it. Otherwise, no response is needed.

{{sender_signature}}

### Landing-page copy requirements

**H1:**  
> Surface potential estate-related surplus matters.

**Subhead:**  
> Connect source records to an organized legal-review workflow for deceased-owner questions, representative authority, and missing documentation.

**Primary CTA:** `Review an estate-research example`  
**Secondary CTA:** `Get the probate intake checklist`

**Required clarification:**

> A deceased-owner match is a research lead, not proof of death, heirship, estate ownership, or authority to claim. Letters, summary procedures, heirship determinations, and ancillary proceedings vary by jurisdiction.

---

## D. Sequence C: Mortgage Foreclosure & Distressed Real Estate Litigators

**Destination:**  
`https://surplusdocket.com/for/mortgage-foreclosure.html`

**Core pain:** Confusing sale types, incomplete procedural history, and uncertainty over competing interests.

### Email 1 — Distinguish the proceeding

**Subject:** Foreclosure surplus: source and procedural context

Hi {{first_name}},

Your firm lists {{verified_foreclosure_service}} among its practice areas.

Surplus Docket helps legal teams review covered foreclosure-surplus records with their source context and preliminary flags for recorded interests.

A central part of the workflow is distinguishing mortgage-foreclosure surplus from tax-deed surplus before applying a deadline or priority framework.

Here is the foreclosure-specific overview:  
https://surplusdocket.com/for/mortgage-foreclosure.html

Would a sample showing that distinction be useful?

{{sender_signature}}

### Email 2 — Evidence trail

**Subject:** Review the evidence behind a lien flag

Hi {{first_name}},

A lien flag is useful only if an attorney can inspect what produced it.

Our screening workflow is intended to show the supporting record, relevant dates, and unresolved questions—not deliver an automated conclusion about priority.

That helps a reviewer distinguish a recorded interest from a satisfied lien, an incomplete chain, or an issue requiring additional docket or title research.

Would you like a redacted screening example with its source references?

{{sender_signature}}

### Email 3 — Coverage over commitment

**Subject:** Which foreclosure jurisdictions matter to your team?

Hi {{first_name}},

Last note from me.

If foreclosure-surplus review is part of your practice, we can first confirm whether our current sources cover the jurisdictions you actually handle.

There is no need to start with a broad subscription discussion.

Reply with your priority counties, or review the workflow here:  
https://surplusdocket.com/for/mortgage-foreclosure.html

{{sender_signature}}

### Landing-page copy requirements

**H1:**  
> Foreclosure surplus research with a traceable evidence trail.

**Subhead:**  
> Review covered surplus records, procedural context, and preliminary recorded-interest flags before undertaking a full legal analysis.

**Primary CTA:** `Inspect a screening example`  
**Secondary CTA:** `Check foreclosure coverage`

**Required legal block:**

- Explain Fla. Stat. §§ 45.031–45.033 separately from § 197.582.
- Distinguish owners, subordinate lienholders, assignees, and other potential claimants.
- Do not display a universal “60-day” countdown.
- State that priority may depend on legal rules and record completeness—not merely recording order.

---

## E. Deliverability and compliance operating rules

### Technical controls

| Control | Implementation |
|---|---|
| Address validation | Validate syntax, domain DNS, MX, and reputable mailbox-risk signals. MX confirms a domain can receive mail; it does not prove a specific mailbox exists or that outreach is permitted. |
| Catch-all domains | Flag as uncertain; do not classify as verified solely because the domain accepts mail. |
| Authentication | Configure SPF, DKIM, aligned DMARC, TLS, and monitored reply handling. Progress DMARC enforcement after confirming legitimate senders. |
| Sender identity | Use a clearly branded domain or subdomain and a real, accountable sender. Do not rotate lookalike domains to bypass reputation limits. |
| Format | Plain text or restrained HTML, one destination link, no first-touch attachments, URL shorteners, hidden text, or fabricated reply prefixes. |
| Tracking | Disable open pixels for cold outreach by default. Do not optimize around unreliable open rates. |
| Suppression | Maintain one global suppression service across CRM, email tools, sequences, and manual sends. |
| Stop conditions | Pause on authentication failure, provider blocks, unusual deferrals, complaint patterns, or deteriorating bounce rates. |

### Warmup and pacing

Treat **24 messages per mailbox per sending day as a ceiling, not a starting volume or an inbox guarantee**.

Illustrative ramp, contingent on clean results:

- Days 1–3: 5–8 legitimate messages/day.
- Days 4–7: 10–12/day.
- Week 2: 16–18/day.
- Week 3 onward: up to 24/day.
- Include follow-ups in the 24-message budget.
- Do not use artificial warmup networks or manufactured engagement.

At three touches per contact, **1,373 practices represent up to 4,119 messages**. At 24/day, that is approximately **172 sending days for one mailbox**, before reply-based stops. The ceiling is not 24 new prospects plus unlimited follow-ups.

**Initial operating thresholds:** Target hard bounces below 1%; investigate at 2%. Review every complaint at this volume. Provider-specific requirements may be stricter.

### Spam-risk copy rules

Avoid:

- “Guaranteed recovery,” “unclaimed money waiting for your client,” or “exclusive claim.”
- Unsupported urgency or specific recovery estimates.
- “Re:” or “Fwd:” unless the message is genuinely a reply or forward.
- Misleading “case assignment” or “client referral” language.
- Describing the 1,373-practice prospect list as a subscriber base.

There is no universal list of forbidden words. Identity, relevance, recipient response, infrastructure, and complaint rates matter more than cosmetic word substitutions.

### CAN-SPAM, privacy, and Bar ethics

Every commercial sequence needs:

- Accurate sender and routing information.
- A non-deceptive subject line and appropriate identification of commercial purpose.
- A valid physical postal address.
- A clear, functioning opt-out.
- Suppression as soon as practicable and no later than the applicable CAN-SPAM deadline of 10 business days.
- Appropriate review of applicable privacy laws, source-license restrictions, and vendor obligations.

**Suggested footer**

> {{legal_company_name}} · {{physical_postal_address}}  
> Commercial message about attorney research software. Reply “unsubscribe” or use {{unsubscribe_link}} to stop marketing emails.

**Bar-rule distinction:** Selling research software to lawyers is not automatically the same as soliciting legal clients. But lawyer participation, co-branded campaigns, referrals, and messages sent on a lawyer’s behalf can change the analysis.

Counsel should review:

- **Florida:** Rules 4-7.18 and related advertising rules, including filing and exemption questions where applicable.
- **Texas:** Rule 7.03 and related advertising and solicitation rules.
- **California, Georgia, North Carolina, Tennessee:** Applicable Rules 7.1–7.3, local requirements, and any restrictions implicated by the actual workflow.

Do not automatically add “Advertisement” based on a misapplied Bar rule—or assume lawyer-directed communications are exempt from every requirement.

**UPL safeguard:** No individualized advice to claimants, entitlement determinations, auto-generated filing instructions presented as legal advice, or nonlawyer negotiation services. A disclaimer does not cure conduct that constitutes unauthorized practice.

---

# 3. High-Authority Legal Content Engine

## A. Editorial operating standard

Authority comes from **accurate primary sources, transparent limitations, and identifiable review**, not assertive adjectives.

Every article must include:

1. Named author and a genuine attorney reviewer if attorney review is claimed.
2. Jurisdiction and “law reviewed through” date.
3. Links to official statutory text and material decisions.
4. Separate labels for legal requirements, local practices, and product capabilities.
5. A procedural checklist and source-document checklist.
6. A visible correction channel.
7. Scheduled and event-triggered legal review.
8. No fabricated cases, quotations, credentials, or customer outcomes.

**AI workflow:** AI may outline, extract, and draft. It may not publish legal analysis without editorial approval. Every citation, quotation, deadline, and priority statement must be checked against a primary source.

---

## Article 1: Georgia Tax Sale Excess Funds & Superior Court Interpleader

**Working title**

> Georgia Tax Sale Excess Funds: O.C.G.A. § 48-4-5, Competing Claims, and Superior Court Interpleader

**Slug:** `/insights/georgia-tax-sale-excess-funds-interpleader.html`  
**Length:** 2,000–2,500 words  
**Audience:** Georgia real estate litigators, creditor-rights counsel, probate litigators.

**Search description**

> A practitioner’s guide to Georgia tax-sale excess funds, claimant priority, source records, and the role of Superior Court interpleader.

### Required legal authorities

- O.C.G.A. § 48-4-5: excess-funds disposition, notice, and interpleader framework.
- O.C.G.A. § 9-11-22: interpleader.
- O.C.G.A. §§ 48-4-40 et seq.: redemption context where relevant.
- Current Georgia appellate decisions interpreting claimant interests, priority, and distribution. Include only after verification.

### Required outline

1. What creates excess funds in a Georgia tax sale.
2. Where the funds and records may be held.
3. Potential claimants and the difference between an asserted interest and established priority.
4. Administrative claim review versus contested distribution.
5. The role of Superior Court interpleader.
6. Redemption-related issues that require separate analysis.
7. Document assembly and unresolved-interest checklist.
8. What a daily feed can identify—and what it cannot resolve.

### Procedural pitfalls

- Treating a county list as proof funds remain available.
- Assuming the former owner necessarily receives the full amount.
- Ignoring assignments, recorded security interests, estate issues, or competing claims.
- Confusing tax-sale redemption with entitlement to excess funds.
- Assuming every county follows the same submission workflow.
- Missing an existing interpleader action or distribution order.
- Stating statewide fees or timing rules without reviewing the current statute and local requirements.

### Practitioner deliverables

Provide a checklist covering:

- Sale identification and tax deed.
- Excess-funds notice and reported balance.
- Relevant title and security records.
- Assignments, satisfactions, and authority documents.
- Existing court action, service, claims, and orders.
- Source and verification date for every material fact.

**Conversion bridge**

> Monitor newly identified Georgia excess-funds records and source updates from covered jurisdictions. Use the feed to build a research queue—not to replace priority analysis.

**CTA:** `View Georgia coverage and a sample record`

---

## Article 2: California Excess Proceeds & the One-Year Claim Period

**Working title**

> California Tax-Defaulted Property Excess Proceeds: Section 4675 and the One-Year Filing Rule

**Slug:** `/insights/california-excess-proceeds-section-4675.html`  
**Length:** 1,800–2,300 words

**Search description**

> Understand California excess-proceeds claims under Section 4675, including the deed-recordation trigger, claimant categories, and county procedures.

### Required legal authorities

- Cal. Rev. & Tax Code § 4675: eligible claims, filing period, and distribution framework.
- §§ 4674 and 4676: applicable notice and claims provisions.
- Other directly relevant provisions in the current excess-proceeds statutory scheme.
- Official county claim forms and instructions, explicitly labeled as local implementation.
- Probate and assignment authorities only where the article actually discusses those issues.

### Essential legal statement

> Section 4675 generally ties the one-year claim period to recordation of the tax collector’s deed to the purchaser—not merely the auction date.

Require counsel to verify the current statutory language, procedural posture, and any asserted exception before publication.

### Required outline

1. Tax-defaulted sale proceeds versus mortgage-foreclosure surplus.
2. Identifying the deed-recordation date.
3. Statutory parties of interest and distribution order.
4. Claim preparation and supporting documentation.
5. Deceased owners, entities, and assignments.
6. County review, disputes, and payment.
7. Deadline-control checklist.

### Procedural pitfalls

- Calculating the period from the sale or website-listing date.
- Treating a feed alert as formal statutory notice.
- Assuming a timely claim proves entitlement.
- Using an outdated county form.
- Failing to substantiate representative or assignment authority.
- Confusing the claim-submission deadline with the timing of distribution.
- Ignoring governing restrictions on compensated assistance or assignments where applicable.

### Practitioner deliverables

Include a deadline worksheet with:

```text
deed_recording_reference
verified_recordation_date
governing_statute_version
computed_deadline
computation_assumptions
reviewing_attorney
review_date
```

**Conversion bridge**

> Identify covered California excess-proceeds records and inspect the source documents needed to begin independent deadline review.

**CTA:** `Review a California source-linked sample`

Do not advertise “automatically guaranteed deadlines.”

---

## Article 3: Probate Surplus Recovery, Letters & Heirship

**Working title**

> Probate Surplus Recovery: When Letters of Administration, Summary Procedures, or Heirship Determinations May Be Needed

**Slug:** `/insights/probate-surplus-recovery-authority-heirship.html`  
**Length:** 2,200–2,800 words  
**Scope:** Multi-state issue spotting, with clearly separated Florida and Texas examples.

### Required legal authorities

- Florida Chapters 731–733 for relevant definitions, administration, and representative authority.
- Fla. Stat. §§ 735.201–735.206 for summary administration.
- Fla. Stat. § 197.582 or §§ 45.031–45.033, depending on the underlying surplus.
- Texas Estates Code Chapter 202 for heirship proceedings.
- Texas Estates Code Chapter 205 for small-estate affidavits, only with a precise explanation of eligibility and limitations.
- Tex. Tax Code § 34.04 for relevant tax-sale claims.

**Important:** Do not present Florida or Texas procedures as national rules.

### Required outline

1. A potential estate asset is not yet an established estate asset.
2. Determine the property interest and legally relevant date.
3. Confirm death and identity without relying solely on automated matching.
4. Check for an existing estate proceeding and active representative.
5. Distinguish letters, summary administration, heirship, and small-estate procedures.
6. Evaluate domicile, situs, and ancillary-administration questions.
7. Account for creditors, assignments, co-ownership, and disputed beneficiaries.
8. Match probate authority to the underlying surplus claim procedure.

### Procedural pitfalls

- Treating a family member as an authorized representative.
- Treating a list of potential relatives as an heirship determination.
- Assuming summary administration is available whenever a surplus amount is small.
- Ignoring all eligibility conditions, other estate assets, and exempt-property treatment.
- Assuming letters alone establish ownership of the surplus.
- Ignoring the timing of death relative to the sale and property transfers.
- Publishing sensitive family research in public samples or outreach.

### Practitioner deliverables

Provide a **potential estate-asset intake checklist**, not a universal petition template.

**Conversion bridge**

> Route potential deceased-owner matches into a structured research queue with source references and unresolved-authority questions.

**CTA:** `Get the probate surplus intake checklist`

---

## Article 4: Mortgage Foreclosure Surplus vs. Tax Deed Surplus

**Working title**

> Mortgage Foreclosure Surplus vs. Tax Deed Surplus: Different Proceedings, Different Priority Questions

**Slug:** `/insights/mortgage-foreclosure-vs-tax-deed-surplus.html`  
**Length:** 2,000–2,600 words  
**Scope:** Florida-centered comparison with separately labeled interstate notes.

### Required legal authorities

- Fla. Stat. § 45.031: judicial sale procedure and relevant notice provisions.
- Fla. Stat. § 45.032: surplus framework and claims.
- Fla. Stat. § 45.033: applicable assignments and related provisions.
- Fla. Stat. § 197.582: tax-deed surplus distribution.
- Florida Chapter 713 and relevant federal lien authorities only if addressing those priority complications.
- *Tyler v. Hennepin County*, 598 U.S. 631 (2023), for a carefully bounded constitutional discussion.

### Required outline

1. Classify the proceeding before calculating anything.
2. Identify the source of the surplus and governing law.
3. Compare potential claimants and statutory distribution frameworks.
4. Explain what recorded chronology can and cannot establish.
5. Review satisfactions, assignments, bankruptcy, federal interests, and missing records.
6. Determine applicable filing requirements from current law and case posture.
7. Build an attorney-reviewed evidence chronology.

### Required comparison table

| Question | Mortgage foreclosure | Tax deed |
|---|---|---|
| Governing framework | Judicial foreclosure and applicable surplus statutes | Tax-deed statutory framework |
| Core records | Judgment, sale documents, docket, relevant recorded interests | Tax-deed sale records, notices, deed, relevant recorded interests |
| Claim process | Proceeding- and claimant-specific | Statutory and administering-office requirements |
| Priority | Requires applicable legal analysis | Requires applicable statutory analysis |
| Deadline | Verify current law and orders | Verify current law and notices |

### Procedural pitfalls

- Reusing one claim template across different sale types.
- Assuming the oldest recording always controls.
- Treating a recorded lien as necessarily outstanding and enforceable.
- Applying an outdated “60-day” rule without checking the current framework.
- Treating *Tyler* as proof of entitlement in every surplus matter.
- Confusing a chronological graph with a legal priority opinion.

**Conversion bridge**

> Inspect the source chronology and preliminary review flags before committing attorney time to a full matter assessment.

**CTA:** `Inspect the evidence-review workflow`

---

# 4. Press Release & Media Syndication System

## A. Release controls

The following are publication-ready structures with **mandatory factual placeholders**. Remove all placeholders only after approval.

- **PR Newswire and EIN Presswire:** Paid distribution channels; syndication is not editorial endorsement.
- **Law360:** Pitch relevant reporters or editors separately. Distribution does not guarantee editorial coverage.
- Never claim “featured in Law360” based solely on a pitch or unrelated syndicated placement.
- Do not invent executive quotations. These drafts intentionally work without them.

### Required media kit

- Corporate fact sheet and media contact.
- State/county coverage matrix.
- Dated fund-total methodology.
- Redacted source-linked product screenshots.
- Product limitations and privacy summary.
- Approved spokesperson biography.
- Release-specific evidence and claims register.

---

## Release 1 — Six-State Expansion

**PUBLICATION GATE:** Verify the $3.2 million calculation, the meaning of “verified,” the as-of date, and actual six-state service coverage.

### Surplus Docket Expands to Six States, Surpassing $3.2 Million in Source-Verified Reported Surplus Funds

**Legal research platform adds multi-state monitoring for tax-sale, probate-related, and foreclosure-surplus workflows**

**[CITY, STATE], [MONTH DAY, YEAR]** — Surplus Docket, a research and workflow platform for legal teams, announced expanded coverage across Florida, Texas, California, Georgia, North Carolina, and Tennessee.

As of **[VERIFICATION DATE]**, the platform’s deduplicated **[DEFINE INCLUDED RECORD SET]** contained more than **$3.2 million in reported surplus funds**, according to the underlying **[IDENTIFY SOURCE CATEGORIES]** reviewed by Surplus Docket.

The figure measures reported amounts in the defined record set. It is not a representation of client recoveries, undisputed balances, or funds legally available to any particular claimant. Records can change after retrieval, and claims may depend on ownership, representative authority, competing interests, deadlines, and court orders.

The expansion supports three dedicated workflows: tax-sale and excess-proceeds litigation, potential estate-related surplus research, and mortgage-foreclosure surplus review.

Surplus Docket combines covered-source monitoring with source-linked records and preliminary screening tools intended to help legal teams organize initial research. A gated API is available under the platform’s designated API plan for approved workflow integrations.

Coverage varies by county, record type, and source availability. The company publishes **[COVERAGE PAGE URL]** and its verification methodology at **[METHODOLOGY URL]**.

Attorneys can review practice-specific workflows and request a source-linked sample at https://surplusdocket.com.

**About Surplus Docket**  
Surplus Docket provides surplus-record research and workflow software for legal teams. The platform supports covered-source monitoring, record organization, and preliminary issue screening. It does not provide legal representation, determine entitlement to funds, or replace independent legal and title review.

**Media contact**  
[NAME]  
[TITLE]  
[EMAIL]  
[PHONE]

**Fallback headline if the financial claim is not substantiated:**

> Surplus Docket Expands Six-State Surplus Research Coverage for Legal Teams

---

## Release 2 — Screening & Evidence Graph

**PUBLICATION GATE:** Confirm that each described evidence-graph capability is deployed, documented, and demonstrable. Otherwise describe a pilot or planned release accurately.

### Surplus Docket Launches Preliminary Lien Screening and Chronological Evidence Graph for Attorney Review

**Source-linked workflow organizes recorded events and highlights unresolved research questions without issuing automated priority opinions**

**[CITY, STATE], [MONTH DAY, YEAR]** — Surplus Docket announced the launch of its Preliminary Lien Screening and Chronological Evidence Graph workflow, designed to help legal teams review the records underlying potential surplus matters.

The workflow organizes supported source records into a chronology of relevant events, such as recorded instruments, assignments, satisfactions, sale-related documents, and available case events. Each supported event links to its underlying source reference and retrieval information.

Preliminary screening flags identify issues that may warrant additional investigation, including possible competing interests, unresolved document relationships, and missing information. These flags are research prompts, not determinations of lien validity, enforceability, ownership, or legal priority.

The distinction between chronology and priority is central to the product’s design. Recording sequence alone may not resolve the effect of statutory preferences, federal interests, bankruptcy proceedings, satisfactions, or case-specific orders.

The workflow includes **[LIST ONLY DEPLOYED CAPABILITIES: SOURCE REFERENCES, EVENT-DATE LABELS, REVIEW STATUS, AUDIT HISTORY]** to support attorney inspection and correction.

Surplus Docket’s bounded monitoring system operates within configured source, access, and workflow limits. The platform does not autonomously file claims, contact potential claimants, or issue legal opinions.

The new workflow is available to **[ELIGIBLE PLANS OR PILOT USERS]** beginning **[DATE]**. Product details and a redacted demonstration are available at **[PRODUCT PAGE URL]**.

**About Surplus Docket**  
Surplus Docket provides source-linked surplus research and workflow software for legal teams across covered jurisdictions. Its tools assist with record discovery and preliminary review while preserving the need for independent professional judgment.

**Media contact**  
[NAME]  
[TITLE]  
[EMAIL]  
[PHONE]

### Distribution sequence

1. Publish the canonical release and methodology on Surplus Docket.
2. Offer selected legal reporters a concise, individually relevant pitch.
3. Make the source-backed demo and spokesperson available.
4. Distribute through the selected paid newswire.
5. Repurpose into a product update, LinkedIn post, and subscriber briefing.
6. Measure qualified visits, sample requests, trials, and paid conversions—not syndicated placement count alone.

---

# 5. Platform & Systems Enhancements

## A. Make the record—not the model—the trusted product

### Minimum record schema

```text
record_id / matter_id / deduplication_key
state / county / proceeding_type
source_url / source_reference / document_hash
source_published_at / retrieved_at / last_rechecked_at
reported_surplus_amount / amount_status
sale_date / deed_recordation_date / event_date_type
potential_party_matches / identity_match_basis
screening_flags / supporting_evidence_ids
unresolved_questions / source_coverage_gaps
extraction_model_version / confidence / reviewer_status
legal_rule_version / attorney_review_status
```

Keep these concepts separate:

- **Extracted fact:** What a document says.
- **Derived flag:** What the software suggests reviewing.
- **Legal conclusion:** What qualified counsel determines.
- **Availability status:** Whether the reported funds have been recently checked.

An AI confidence score must never become a legal-entitlement score.

### Evidence graph requirements

- Typed nodes and relationships.
- Separate execution, recording, filing, retrieval, and effective dates.
- Direct source reference for every material event.
- Explicit “unknown” and conflicting-information states.
- Correction history without silently overwriting prior evidence.
- No inference that “not found” means “does not exist.”
- No automatic priority ranking based solely on chronology.

### AI and autonomous-system controls

- Central model routing with supported-model checks and fallback telemetry.
- Identical output schemas and validation regardless of provider.
- Treat retrieved documents as untrusted input; document text cannot authorize tool use or change system instructions.
- Allowlisted sources, bounded schedules, rate limits, retry budgets, and a kill switch.
- No autonomous claims filing, legal outreach, payments, or case-system changes.
- Human review for uncertain amounts, conflicting dates, identity matches, and material classification changes.
- Data minimization, tenant isolation, role-based access, retention controls, and documented provider processing terms.

### API entitlement controls

Enforce on the server:

- Purchased states and datasets.
- Plan-level API access.
- Tenant ownership and record-level access.
- Request quotas, export limits, and concurrency.
- Key rotation, scoped credentials, audit logs, and revocation.
- Clear handling of stale data and corrections.
- Trial restrictions and post-expiration access.

**Acceptance test:** A Tri-State account cannot retrieve unauthorized states or API data through alternate routes, exports, cached endpoints, or manipulated identifiers.

---

# 6. Trial Conversion, Annual Commitments & LTV

## A. Build a seven-day trial around a completed workflow

**Activation event:** The user selects relevant coverage, reviews a source-linked record, and saves a search or matter.

Do not define activation as merely logging in.

| Day | Experience | Suggested copy |
|---|---|---|
| 0 | Select practice area, states, counties, and preferred digest | “Configure the jurisdictions your team actually handles.” |
| 1 | Guided review of one relevant record | “Start with the source, then review the open questions.” |
| 2 | Saved search and feed setup | “Monitor this research scope without rebuilding it tomorrow.” |
| 3 | Preliminary screening walkthrough | “Inspect why this record was flagged—and what remains unknown.” |
| 4 | Invite a reviewer or export a permitted research packet | “Move one record through your team’s review process.” |
| 5 | Evidence-based activity recap | “You reviewed {{n}} records, opened {{n}} sources, and saved {{n}} matters.” |
| 6 | Transparent plan comparison | “Choose the coverage and integration level your workflow needs.” |
| 7 | Clear expiration notice | “Your trial ends {{date}}. Here is what remains accessible and how to continue.” |

**If there are no relevant live records:** Say so. Offer an explicitly labeled historical sample and disclose the coverage limitation. Do not imply live inventory exists.

Avoid unsupported “you saved 12 hours” estimates. Measure time savings through an actual study or user-confirmed comparison.

## B. Package around workflow fit

| Plan | Commercial role | Required clarity |
|---|---|---|
| **$249 Tri-State** | Focused regional practice | Billing cadence; selectable versus fixed states; switching policy; seats; exports; feed frequency |
| **$449 Six-State + API** | Multi-state teams and integrations | Billing cadence; county coverage; API quota; seats; exports; support; usage overages |

### Annual offer

If these are approved monthly prices, a **10-month-equivalent annual option** would be:

- Tri-State: **$2,490/year**.
- Six-State + API: **$4,490/year**.

These are proposed prices, not existing terms. Validate margins and support costs first.

Annual-conversion copy:

> For teams that have confirmed coverage fit, annual billing offers a lower effective price and a guided workflow setup.

Do not force annual purchase before the user can assess coverage. Disclose renewal, cancellation, refund, and data-access terms clearly.

## C. Retention features ranked by value

| Priority | Enhancement | Retention mechanism |
|---|---|---|
| P0 | Coverage and source-health dashboard | Prevents false expectations and exposes outages |
| P0 | Material-change alerts | Gives subscribers a reason to revisit saved matters |
| P0 | Saved matters and review states | Embeds the product in actual work |
| P0 | Source-linked exports with timestamps | Makes research transferable and auditable |
| P1 | Team assignments and notes | Supports collaboration |
| P1 | CRM/webhook integrations | Reduces duplicate entry |
| P1 | Review reminders with attorney-confirmed dates | Supports workflow without promising legal calendaring |
| P1 | Missing-document and contradiction queues | Focuses research effort |
| P2 | Customer-requested county expansion | Aligns acquisition spending with demonstrated demand |

### Churn intervention triggers

- No source review within 48 hours: offer guided setup.
- Searches produce no relevant coverage: disclose the gap and discuss fit.
- No saved search by Day 3: send a short configuration guide.
- Repeated empty feeds: investigate source health before sending promotional messages.
- Repeated API errors: proactive technical support.
- Cancellation: offer export and an optional reason survey, not obstructive retention steps.

---

# 7. Pipeline Expansion & Measurement

## A. Expand within coverage before adding jurisdictions

Prioritize:

1. Existing contacts with demonstrable practice fit.
2. Adjacent practices in counties with reliable, useful records.
3. Firms with a credible multi-attorney review workflow.
4. Multi-state firms whose footprint matches the six-state plan.
5. New jurisdictions only after source access, legal review, and unit economics are validated.

**Do not rank prospects using inferred recoveries, alleged client wealth, or sensitive family information.**

### Practical fit score

- 30% verified practice fit.
- 30% alignment with actual covered jurisdictions.
- 20% appropriate operational scale.
- 20% legitimate engagement signals, such as replies or sample requests.

Exclude email opens from the core score.

## B. Instrument the full funnel

```text
outreach_delivered
positive_reply
coverage_requested
sample_viewed
trial_started
jurisdiction_selected
source_document_opened
record_saved
saved_search_created
teammate_invited
api_first_success
subscription_started
annual_selected
subscription_canceled
```

Keep case and personal information out of marketing analytics.

### Executive scorecard

| Layer | Metrics |
|---|---|
| Deliverability | Hard bounces, complaints, deferrals, opt-outs |
| Acquisition | Qualified replies and trials per delivered email |
| Activation | Coverage configured, sources reviewed, saved workflow created |
| Conversion | Activated-trial-to-paid rate; overall trial-to-paid rate |
| Retention | Cohort retention, gross revenue retention, net revenue retention |
| Economics | Gross-margin-adjusted CAC payback and observed cohort LTV |
| Product trust | Source freshness, extraction errors, correction turnaround |
| API | Successful requests, integration activation, authorization failures |
| Content | Qualified visits, assisted trials, source-sample requests |

Establish baselines before assigning aggressive targets. Do not present speculative conversion rates as forecasts.

---

# 8. 90-Day Execution Roadmap

| Timing | Workstream | Owner | Definition of done |
|---|---|---|---|
| Days 1–7 | Claims and legal-risk audit | Commercial lead + counsel | Unsupported claims removed; deadline language reviewed |
| Days 1–10 | Deliverability and suppression | Revenue operations + engineering | Authentication passes; unsubscribe and stop rules tested |
| Days 1–14 | Coverage and verification transparency | Product + data operations | Public methodology and county/source matrix live |
| Days 8–21 | Landing pages and sample assets | Marketing + product | Three matched pages with real samples and explicit limitations |
| Days 8–28 | Outreach pilot | Revenue operations | Small segmented cohorts; manual reply review; no overlapping sequences |
| Days 15–35 | Trial activation | Product + customer success | Practice-specific onboarding and event instrumentation live |
| Days 15–45 | Four authority articles | Editorial + legal reviewers | Primary-source checks and approval recorded |
| Days 25–45 | Release 1 | Communications | Fund total and coverage claims fully substantiated |
| Days 30–60 | Evidence graph hardening | Engineering + product | Source traceability, unknown states, auditability, and entitlement tests pass |
| Days 45–65 | Release 2 | Communications + product | Advertised capabilities live and demonstrable |
| Days 45–75 | Annual-plan experiment | Finance + commercial | Transparent offer; cohort measurement; margin validation |
| Days 60–90 | Scale winning segments | Commercial + operations | Expansion based on paid activation, retention, and source reliability |

## Final strategic direction

Surplus Docket should not compete on the promise that AI “finds money” or “determines lien priority.”

It should compete on a more defensible proposition:

> **Relevant records. Inspectable sources. Explicit uncertainty. Faster attorney review.**

That positioning aligns outreach, legal content, press coverage, product architecture, and subscription value around the same credible promise.