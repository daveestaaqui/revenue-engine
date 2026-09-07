## Executive assessment

**The visible changes materially improve positioning and purchase clarity, but I would not mark P0 complete yet.** The methodology example still presents a potentially misleading legal and financial conclusion—the exact kind of trust risk the revised hero is working to remove.

**P1 is directionally strong:** the hero establishes audience, product, coverage, and two clear next actions. However, I cannot confirm the complete narrative sequence from these excerpts.

I’m reviewing the supplied HTML—not the live site or full 2,666-line file. The original blueprint, complete pathways section, Tyler discussion, second comparison card, and billing JavaScript are not included.

| Area | Assessment | Recommendation |
|---|---|---|
| Attorney-specific positioning | Strong | Keep the counsel-focused headline. |
| Source-linked, qualified product description | Strong | Preserve “supported jurisdictions”; avoid implying statewide completeness. |
| Hero trial disclosure | Much improved | Explicitly identify the trial as **Core** coverage. |
| Methodology example | **P0 unresolved** | Remove automatic lien subtraction and the “underwater” conclusion. |
| Pricing clarity | Partially addressed | Synchronize price, billing interval, renewal terms, and checkout destination. |
| State navigation | Good concept; awkward grouping | Associate each state group with its plan on mobile and desktop. |
| Overall narrative order | Not fully verifiable | Make the docket evidence the first substantial section after the hero. |

---

## 1. P0: Fix the methodology example before driving more traffic

### The current example contradicts your positioning

These lines are the principal concern:

> “1st Senior Bank Mortgage (Wells Fargo): -$165,000.00”  
> “Reported Surplus After Recorded Liens: $0.00 (Underwater)”

They imply that the platform can calculate distributable surplus by subtracting recorded encumbrances from an auction-surplus figure.

**That is not a reliable universal calculation.** The effect of a mortgage or assessment depends on the sale type, jurisdiction, procedural posture, claim priority, and other facts. A recorded instrument amount also does not necessarily establish a current payoff or an allowed claim.

The commercial problem is equally important: sophisticated counsel will notice that the example moves from **record organization** into an apparent **entitlement determination**.

### Immediate HTML replacement

Replace the financial box containing the subtraction with this clearly hypothetical example:

```html
<div class="bg-slate-50 border border-slate-200 rounded-xl p-4 mb-4">
    <p class="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-3">
        Illustrative example — not a live record
    </p>

    <dl class="space-y-3 text-xs">
        <div class="flex flex-col sm:flex-row sm:justify-between gap-1 sm:gap-4">
            <dt class="text-slate-600 font-semibold">
                Surplus stated in example ledger
            </dt>
            <dd class="font-mono font-bold text-sm text-brand-navy">
                $142,500.00
            </dd>
        </div>

        <div class="flex flex-col sm:flex-row sm:justify-between gap-1 sm:gap-4
                    pt-3 border-t border-slate-200">
            <dt class="text-slate-600 font-semibold">
                Additional records requiring review
            </dt>
            <dd class="text-slate-700 sm:text-right">
                Mortgage and code-enforcement entries
            </dd>
        </div>

        <div class="flex flex-col sm:flex-row sm:justify-between gap-1 sm:gap-4
                    pt-3 border-t border-slate-200">
            <dt class="text-slate-600 font-semibold">
                Amount available to a particular claimant
            </dt>
            <dd class="font-semibold text-brand-navy sm:text-right">
                Not determined
            </dd>
        </div>
    </dl>

    <p class="mt-4 text-xs text-slate-600 leading-relaxed">
        Recorded entries do not establish current balances, claim priority,
        or entitlement to payment. Those questions require independent review.
    </p>
</div>
```

Also make these surrounding changes:

| Current | Replace with |
|---|---|
| `Unfiltered County Record` | `Source Record View` |
| `Raw Clerk Excess Ledger` | `County Surplus Ledger — Illustrative` |
| `Orange County Parcel #24-22-29-0000` | `Hypothetical entry for demonstration` |
| Red `✕` icon | Remove |
| Rose/red error styling | Neutral slate styling |

**Apply the same standard to the unseen right-hand card.** It should show information organized for review—not a “verified net recovery,” “clear title,” or “qualified claim” unless those are genuinely supported, precisely defined determinations.

If you use a real example instead, provide the actual source, relevant dates, and an accurate description of what was—and was not—reviewed. Do not combine an illustrative calculation with apparently real identifiers.

### Tyler discussion: still needs review

The excerpt does not include that copy. If it discusses *Tyler v. Hennepin County*, ensure it does not imply that the decision:

- Establishes every listed claimant’s entitlement.
- Makes all foreclosure and tax-sale procedures equivalent.
- Eliminates jurisdiction-specific deadlines, priorities, or procedural requirements.

**Keep legal context subordinate to product evidence.** It should not function as a recovery guarantee.

---

## 2. P1: Keep the hero, but resolve the six-state/Core ambiguity

The hero advertises six states, while its primary CTA opens a $249 Core checkout. The expansion note helps, but the primary purchase action should identify its scope directly.

### Exact hero changes

Replace the introductory paragraph with:

```html
<p class="text-base sm:text-lg text-slate-600 max-w-2xl mx-auto mb-8 leading-relaxed font-normal">
    Review source-linked tax-sale and foreclosure surplus records
    from supported jurisdictions in six states. See record details,
    source references, and review limitations before evaluating a potential matter.
</p>
```

Change the primary CTA text to:

```html
Start 7-Day Core Trial
```

Add this attribute to that link:

```html
aria-describedby="hero-trial-terms hero-plan-scope"
```

Replace the terms block with:

```html
<div class="text-center text-xs sm:text-sm text-slate-600 space-y-1">
    <p id="hero-trial-terms" class="font-semibold text-slate-800">
        $0 today. Then $249/month starting on day 8 unless you cancel
        before the trial ends.
    </p>

    <p id="hero-plan-scope">
        Core covers supported jurisdictions in FL, TX, and GA.
    </p>

    <p class="text-slate-500">
        Need NC, TN, CA, or API access?
        <a href="#pricing" class="font-bold text-brand-green hover:underline">
            Compare Six-State + API — $449/month &rarr;
        </a>
    </p>
</div>
```

**Use these trial terms only if the Stripe configuration matches them exactly.** The HTML alone does not establish the checkout’s trial duration or billing behavior.

I would also shorten the secondary CTA to:

```html
View Docket Preview &darr;
```

“Inspect” is defensible for attorneys, but “View” is more natural and scannable.

---

## 3. Fix the state-filter grouping

The current two-label row sits above a single six-button grid. On mobile, both plan labels remain side by side while the states wrap into two rows. That weakens the association between a plan and its states.

### Replace the label row and grid structure

Move the existing buttons into these two explicitly labeled groups, preserving their current handlers:

```html
<div class="mt-8 pt-5 border-t border-slate-200/70 max-w-2xl mx-auto">
    <p class="text-xs text-slate-600 mb-3">
        Filter the docket preview by state.
        Coverage varies by jurisdiction and record type.
    </p>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div role="group" aria-labelledby="core-state-label">
            <p id="core-state-label"
               class="text-[11px] font-semibold text-slate-500 mb-2">
                Core — FL, TX, GA
            </p>

            <div class="grid grid-cols-3 gap-2">
                <!-- Move the existing FL, TX, and GA buttons here. -->
            </div>
        </div>

        <div role="group" aria-labelledby="expanded-state-label">
            <p id="expanded-state-label"
               class="text-[11px] font-semibold text-slate-500 mb-2">
                Added in Six-State + API — NC, TN, CA
            </p>

            <div class="grid grid-cols-3 gap-2">
                <!-- Move the existing NC, TN, and CA buttons here. -->
            </div>
        </div>
    </div>
</div>
```

### Verify the interaction contract

Every state button should:

1. Apply the correct docket filter.
2. Synchronize any filter control inside the docket.
3. Scroll to the docket without hiding its heading under a sticky header.
4. Show a truthful empty state when no preview records are available.

Use this empty-state wording where appropriate:

> No preview records are currently displayed for this state. Preview availability does not establish full coverage.

Do not silently show Florida records after a visitor selects California.

---

## 4. Make billing terms consistent across the page

You currently use:

- “7-Day Trial”
- “7-Day Practice Evaluation”
- “Cancel anytime”

Standardize on **“7-day trial.”** “Practice evaluation” can be supporting language, but should not replace the billing term.

### Replace the Core monthly subtext

```html
<div id="card1-subtext"
     class="text-xs font-semibold text-slate-600 mb-5">
    7-day trial. $0 today; then $249/month unless canceled before the trial ends.
</div>
```

“Cancel anytime” alone does not explain whether cancellation prevents renewal, ends access immediately, or produces a refund. Put verified cancellation and refund details in the billing FAQ.

### Annual billing is a critical implementation check

The shown interval is hard-coded:

```html
<span class="text-slate-500 text-sm">/ month</span>
```

Make it independently updateable:

```html
<span id="card1-interval" class="text-slate-500 text-sm">
    / month
</span>
```

Do the same for the second card.

If annual pricing truly equals ten monthly payments, the totals would be **$2,490/year** and **$4,490/year**. Verify those amounts against Stripe before publishing them.

Prefer this annual display:

> **$2,490 / year**  
> Billed annually. Equivalent to $207.50/month.

The annual toggle must update **all** of the following together:

- Displayed amount.
- Billing interval.
- Trial and renewal disclosure.
- Checkout URL.
- Any cancellation wording that differs by billing cycle.

For the badge, replace:

```html
Two months included
```

with:

```html
Save 2 months with annual billing
```

Only use that claim if the verified annual price supports it.

---

## 5. Small accessibility and navigation fixes

### Give the billing switch an accessible name

Add to the existing switch:

```html
aria-label="Annual billing"
```

Keep `aria-checked` synchronized with the selected cycle.

The supplied billing controls remove focus outlines without showing a replacement. Add a visible keyboard-focus treatment:

```html
<style>
    #overview a:focus-visible,
    #overview button:focus-visible,
    #pricing a:focus-visible,
    #pricing button:focus-visible {
        outline: 3px solid #0f766e;
        outline-offset: 4px;
    }

    #live-docket,
    #pricing {
        scroll-margin-top: 6rem;
    }
</style>
```

Adjust `6rem` to your actual sticky-header height.

### Check Tailwind spacing support

`sm:py-18` is not available in every Tailwind version/configuration. If it is not defined in yours, use:

```html
<section id="pricing"
         class="py-14 sm:py-20 bg-white border-t border-slate-200">
```

---

## Recommended final page sequence

For counsel, the strongest conversion sequence is **evidence → usefulness → scope → purchase**:

1. **Hero:** what it is, who it serves, trial scope.
2. **Docket preview:** inspect records and source links.
3. **Methodology:** what is organized and what remains unverified.
4. **Workflow/pathways:** how counsel can evaluate records in practice.
5. **Coverage and API:** supported jurisdictions, record types, limitations.
6. **Pricing:** exact plan differences and billing terms.
7. **FAQ and final CTA:** access, cancellation, coverage, and review responsibilities.

If pathways currently precede the preview, keep them compact. Do not make visitors read a second sales narrative before seeing the product.

**Immediate priorities:** remove the lien-subtraction conclusion, identify the hero trial as Core, repair state grouping, and verify annual billing synchronization. Those changes will improve credibility and purchase confidence more than another layer of promotional copy.