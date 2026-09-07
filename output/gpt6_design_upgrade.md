## 1. Design philosophy & refinement spec

**Make the interface quieter; make the evidence louder.** Prestige should come from predictable structure, excellent typography, and clear provenance—not decorative effects.

| Area | Refinement |
|---|---|
| Hierarchy | Navy for navigation and primary actions; olive for coverage and supporting actions. Reserve gold for a small emphasis rule—not text or large backgrounds. |
| Typography | Inter at 15–16px for content; Plus Jakarta Sans at 600–700 for headings. Use restrained negative tracking on headings, normal tracking on identifiers, and tabular lining numerals for monetary values and case numbers. |
| Readability | Body line-height: `1.55`; headings: `1.2`; dense tables: `1.4`. Keep explanatory copy around `65ch`. Avoid pale gray metadata. |
| Information architecture | In docket views, prioritize amount → jurisdiction → case identifier → record provenance. Separate record dates from indexing timestamps. Never imply indexing equals legal verification. |
| Surfaces | Paper canvas, white panels, delicate navy-tinted borders. Combine a short contact shadow with a broader downward shadow. Avoid heavy glass effects outside navigation. |
| Interaction | `140–180ms` transitions. Interactive panels lift exactly `1px`; passive panels do not move. Use visible keyboard focus and clear pressed/disabled states. |
| Status | Text labels accompany every colored indicator. Static by default; pulse only for a genuinely active process—not to imply freshness. |
| Responsive behavior | Collapse card layouts naturally. Preserve comparison-table columns with keyboard-accessible horizontal scrolling instead of squeezing or hiding legal data. |

Load Inter and Plus Jakarta Sans once through your existing font pipeline, preferably self-hosted WOFF2 with `font-display: swap`.

## 2. Ready-to-inject CSS

Wrap the application in `.sd-app`. This stylesheet is standalone; no Tailwind runtime is required.

```css
:root {
  --sd-navy: #1b365d;
  --sd-navy-deep: #102238;
  --sd-ink: #0c1827;
  --sd-olive: #4c6d48;
  --sd-olive-deep: #365134;
  --sd-olive-soft: #edf3ec;
  --sd-paper: #f8f8f4;
  --sd-gold: #f59e0b;
  --sd-white: #fff;
  --sd-muted: #526174;

  --sd-line: rgb(27 54 93 / 15%);
  --sd-line-strong: rgb(27 54 93 / 28%);
  --sd-radius: 12px;

  /* Contact occlusion + directional ambient shadow */
  --sd-shadow:
    0 1px 2px rgb(12 24 39 / 5%),
    0 8px 24px -12px rgb(12 24 39 / 16%);
  --sd-shadow-raised:
    0 2px 3px rgb(12 24 39 / 6%),
    0 14px 30px -14px rgb(12 24 39 / 22%);

  --sd-ease: cubic-bezier(.2, .7, .2, 1);
}

.sd-app {
  margin: 0;
  color: var(--sd-ink);
  background: var(--sd-paper);
  font-family: Inter, system-ui, sans-serif;
  font-size: 1rem;
  line-height: 1.55;
  font-kerning: normal;
  font-optical-sizing: auto;
}

.sd-app *,
.sd-app *::before,
.sd-app *::after {
  box-sizing: border-box;
}

.sd-app :where(h1, h2, h3, p, dl) { margin: 0; }

.sd-app :where(h1, h2, h3) {
  color: var(--sd-navy-deep);
  font-family: "Plus Jakarta Sans", Inter, sans-serif;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -.025em;
  text-wrap: balance;
}

.sd-app h1 { font-size: clamp(2rem, 4vw, 3.25rem); }
.sd-app h2 { font-size: clamp(1.5rem, 2.5vw, 2rem); }
.sd-app h3 { font-size: 1.125rem; }

.sd-app a {
  color: var(--sd-navy);
  text-underline-offset: .2em;
  text-decoration-thickness: 1px;
}

.sd-app :where(a, button, input, select, textarea, [tabindex]):focus-visible {
  outline: 2px solid var(--sd-navy);
  outline-offset: 3px;
}

.sd-shell {
  width: min(100% - 2rem, 76rem);
  margin-inline: auto;
}

.sd-section { padding-block: clamp(2rem, 5vw, 4rem); }
.sd-stack > * + * { margin-block-start: 1rem; }
.sd-muted { color: var(--sd-muted); }
.sd-prose { max-width: 65ch; }
.sd-small { font-size: .875rem; }

.sd-eyebrow {
  color: var(--sd-muted);
  font-size: .75rem;
  font-weight: 600;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.tabular-nums {
  font-variant-numeric: lining-nums tabular-nums;
  letter-spacing: 0;
}

.sd-case-id {
  font-size: .875rem;
  overflow-wrap: anywhere;
}

.sd-amount {
  color: var(--sd-navy-deep);
  font-size: clamp(1.75rem, 3vw, 2.25rem);
  font-weight: 600;
  line-height: 1.15;
  white-space: nowrap;
}

.sd-grid {
  display: grid;
  gap: 1.25rem;
  grid-template-columns:
    repeat(auto-fit, minmax(min(100%, 19rem), 1fr));
}

.sd-grid > * { min-width: 0; }

.card-institutional {
  padding: clamp(1.25rem, 2.5vw, 1.75rem);
  background: var(--sd-white);
  border: 1px solid var(--sd-line);
  border-radius: var(--sd-radius);
  box-shadow: var(--sd-shadow);
}

/* Apply only to panels containing a meaningful interactive destination. */
.card-interactive {
  transition:
    transform 160ms var(--sd-ease),
    box-shadow 160ms var(--sd-ease),
    border-color 160ms var(--sd-ease);
}

.card-interactive:focus-within {
  border-color: var(--sd-line-strong);
  box-shadow: var(--sd-shadow-raised);
}

@media (hover: hover) and (pointer: fine) {
  .card-interactive:hover {
    transform: translateY(-1px);
    border-color: var(--sd-line-strong);
    box-shadow: var(--sd-shadow-raised);
  }
}

.badge-statutory {
  display: inline-flex;
  align-items: center;
  gap: .45rem;
  width: fit-content;
  padding: .25rem .625rem;
  border: 1px solid rgb(76 109 72 / 25%);
  border-radius: 999px;
  background: var(--sd-olive-soft);
  color: var(--sd-olive-deep);
  font-size: .75rem;
  font-weight: 600;
  line-height: 1.4;
}

.badge-statutory__dot {
  flex: 0 0 .375rem;
  width: .375rem;
  height: .375rem;
  border-radius: 50%;
  background: currentColor;
}

/* Opt-in only for a real active operation. */
.badge-statutory--active .badge-statutory__dot {
  animation: sd-status 2s ease-in-out infinite;
}

@keyframes sd-status {
  50% { opacity: .45; }
}

.sd-button {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  gap: .5rem;
  min-height: 44px;
  padding: .625rem 1rem;
  border: 1px solid var(--sd-navy);
  border-radius: 8px;
  background: var(--sd-navy);
  color: white;
  font: inherit;
  font-size: .875rem;
  font-weight: 600;
  line-height: 1.4;
  text-align: center;
  text-decoration: none;
  cursor: pointer;
  transition:
    background-color 140ms var(--sd-ease),
    border-color 140ms var(--sd-ease),
    transform 140ms var(--sd-ease);
}

.sd-app a.sd-button { color: white; }

.sd-button--secondary,
.sd-app a.sd-button--secondary {
  background: white;
  color: var(--sd-navy);
  border-color: var(--sd-line-strong);
}

@media (hover: hover) {
  .sd-button:hover {
    background: var(--sd-navy-deep);
    border-color: var(--sd-navy-deep);
  }

  .sd-button--secondary:hover {
    background: var(--sd-paper);
    border-color: var(--sd-navy);
  }
}

.sd-button:active:not(:disabled) { transform: translateY(1px); }

.sd-button:disabled {
  color: var(--sd-muted);
  background: #eef0f2;
  border-color: var(--sd-line);
  cursor: not-allowed;
}

/* Header: opaque fallback; restrained translucency when supported. */
.sd-header {
  position: sticky;
  top: 0;
  z-index: 40;
  background: var(--sd-paper);
  border-bottom: 1px solid var(--sd-line);
  box-shadow: 0 1px 0 rgb(255 255 255 / 80%);
}

@supports ((backdrop-filter: blur(12px)) or
           (-webkit-backdrop-filter: blur(12px))) {
  .sd-header {
    background: rgb(248 248 244 / 94%);
    -webkit-backdrop-filter: blur(12px);
    backdrop-filter: blur(12px);
  }
}

.sd-header__inner,
.sd-nav,
.sd-card-top {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: .75rem 1.5rem;
}

.sd-header__inner {
  min-height: 76px;
  padding-block: .75rem;
  justify-content: space-between;
}

.sd-brand {
  font-family: "Plus Jakarta Sans", Inter, sans-serif;
  font-weight: 700;
  letter-spacing: -.025em;
  text-decoration: none;
}

.sd-nav { gap: .25rem; }

.sd-nav a {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  padding: .5rem .75rem;
  border-radius: 6px;
  font-size: .875rem;
  text-decoration: none;
}

.sd-nav a:hover { background: rgb(27 54 93 / 5%); }

.sd-nav a[aria-current="page"] {
  background: rgb(27 54 93 / 7%);
  font-weight: 600;
  text-decoration: underline;
}

.sd-card-top { justify-content: space-between; }

.sd-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.sd-meta dt {
  color: var(--sd-muted);
  font-size: .8125rem;
}

.sd-meta dd {
  margin: .25rem 0 0;
  font-size: .875rem;
  font-weight: 500;
}

.sd-card-footer {
  padding-top: 1rem;
  border-top: 1px solid var(--sd-line);
}

/* Shared docket / comparison table container. */
.docket-scroll {
  max-height: 32rem;
  overflow: auto;
  isolation: isolate;
  border: 1px solid var(--sd-line);
  border-radius: 10px;
  background: white;
  scrollbar-width: thin;
  scrollbar-color: #778698 var(--sd-paper);
  scrollbar-gutter: stable;
}

.docket-scroll::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

.docket-scroll::-webkit-scrollbar-track {
  background: var(--sd-paper);
}

.docket-scroll::-webkit-scrollbar-thumb {
  background: #778698;
  border: 2px solid var(--sd-paper);
  border-radius: 999px;
}

.docket-scroll::-webkit-scrollbar-thumb:hover {
  background: var(--sd-muted);
}

.table-terminal {
  width: 100%;
  min-width: 42rem;
  border-collapse: separate;
  border-spacing: 0;
  font-size: .875rem;
  line-height: 1.4;
}

.table-terminal caption {
  padding: 1rem;
  color: var(--sd-muted);
  text-align: left;
  font-size: .8125rem;
}

.table-terminal :where(th, td) {
  padding: .875rem 1rem;
  border-bottom: 1px solid var(--sd-line);
  text-align: left;
  vertical-align: top;
}

.table-terminal thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #f1f3f4;
  color: var(--sd-navy-deep);
  font-size: .8125rem;
  font-weight: 600;
  box-shadow: 0 1px 0 var(--sd-line);
}

.table-terminal tbody th { font-weight: 500; }
.table-terminal tbody tr:nth-child(even) { background: #fafbf9; }
.table-terminal tbody tr:hover { background: #f0f4ef; }
.table-terminal tbody tr:focus-within { background: #f0f4ef; }
.table-terminal tbody tr:last-child > * { border-bottom: 0; }

.table-terminal .numeric {
  text-align: right;
  white-space: nowrap;
  font-variant-numeric: lining-nums tabular-nums;
}

.table-terminal .suite-column {
  background: var(--sd-olive-soft);
  color: var(--sd-olive-deep);
}

/* Suite emphasis: no scale-up, oversized ribbon, or promotional glow. */
.sd-pricing-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.sd-pricing-card .sd-button { margin-top: auto; }

.sd-pricing-card--suite {
  border-color: rgb(76 109 72 / 45%);
  box-shadow: inset 0 3px 0 var(--sd-olive), var(--sd-shadow);
}

.sd-feature-list {
  margin: 0;
  padding-inline-start: 1.125rem;
}

.sd-feature-list li + li { margin-top: .5rem; }

.sd-toolkit {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 1.5rem;
  border-inline-start: 3px solid var(--sd-olive);
  background: linear-gradient(110deg, white, #f3f6f1);
}

@media (max-width: 44rem) {
  /* Avoid a tall sticky header obscuring mobile content. */
  .sd-header { position: relative; }
  .sd-nav { flex-basis: 100%; }
  .sd-toolkit { grid-template-columns: 1fr; }
  .sd-toolkit .sd-button { justify-self: start; }
}

@media (prefers-reduced-motion: reduce) {
  .sd-app *,
  .sd-app *::before,
  .sd-app *::after {
    animation: none !important;
    transition: none !important;
    scroll-behavior: auto !important;
  }

  .sd-app .card-interactive:hover,
  .sd-app .sd-button:active {
    transform: none;
  }
}

@media (forced-colors: active) {
  .card-institutional,
  .badge-statutory,
  .docket-scroll,
  .sd-button {
    border-color: CanvasText;
  }

  .sd-app :focus-visible { outline-color: Highlight; }
}
```

### Optional Tailwind v3 extension

Merge into the existing configuration. Tailwind already provides `tabular-nums`; the CSS above additionally requests lining numerals.

```js
// tailwind.config.js — merge into your existing configuration
module.exports = {
  theme: {
    extend: {
      colors: {
        prussian: {
          DEFAULT: "#1b365d",
          deep: "#102238",
          ink: "#0c1827",
        },
        relief: {
          DEFAULT: "#4c6d48",
          deep: "#365134",
          soft: "#edf3ec",
        },
        deckle: "#f8f8f4",
        gold: "#f59e0b",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        heading: ["Plus Jakarta Sans", "Inter", "sans-serif"],
      },
      boxShadow: {
        institutional: "var(--sd-shadow)",
        "institutional-raised": "var(--sd-shadow-raised)",
      },
      borderRadius: {
        institutional: "12px",
      },
      transitionTimingFunction: {
        institutional: "cubic-bezier(.2,.7,.2,1)",
      },
    },
  },
};
```

## 3. Concrete component enhancements

The following markup uses the stylesheet above. **Routes are illustrative integration targets; the docket is explicitly synthetic.** Bind pricing and product entitlements to your actual catalog before publishing.

### A. Primary navigation

Retains visible navigation on mobile without requiring a JavaScript menu.

```html
<!-- Apply class="sd-app" to <body> or your application root. -->
<header class="sd-header">
  <div class="sd-shell sd-header__inner">
    <a class="sd-brand" href="/" aria-label="Surplus Docket home">
      Surplus Docket
    </a>

    <nav class="sd-nav" aria-label="Primary">
      <a href="/docket" aria-current="page">Docket</a>
      <a href="/coverage">Coverage</a>
      <a href="/toolkit">Practitioner Toolkit</a>
      <a href="/pricing">Pricing</a>
    </nav>

    <a class="sd-button sd-button--secondary" href="/login">
      Sign in
    </a>
  </div>
</header>
```

Set `aria-current="page"` from the router rather than hard-coding it across pages.

### B. Case dossier preview and terminal table

Use a neutral preview label until actual ingestion timestamps and source links are available.

```html
<section class="sd-shell sd-section sd-stack"
         aria-labelledby="docket-heading">
  <div class="sd-stack">
    <p class="sd-eyebrow">Record intelligence</p>
    <h2 id="docket-heading">Case dossier preview</h2>
    <p class="sd-muted sd-small">
      Illustrative records only. Not an available claim or verified balance.
    </p>
  </div>

  <div class="sd-grid">
    <article class="card-institutional sd-stack"
             aria-labelledby="sample-case-title">
      <div class="sd-card-top">
        <p class="sd-eyebrow">Florida · Tax deed surplus</p>
        <span class="badge-statutory">
          <span class="badge-statutory__dot" aria-hidden="true"></span>
          Sample record
        </span>
      </div>

      <div>
        <p class="sd-small sd-muted">Reported surplus</p>
        <p class="sd-amount tabular-nums">$148,250.00</p>
      </div>

      <h3 id="sample-case-title">Example County</h3>

      <dl class="sd-meta">
        <div>
          <dt>Case identifier</dt>
          <dd class="tabular-nums sd-case-id">SAMPLE-2026-001042</dd>
        </div>
        <div>
          <dt>Record category</dt>
          <dd>Tax deed sale</dd>
        </div>
        <div>
          <dt>Source record date</dt>
          <dd><time datetime="2026-08-31">Aug 31, 2026</time></dd>
        </div>
        <div>
          <dt>Index timestamp</dt>
          <dd>
            <time datetime="2026-09-01T10:30:00Z">
              Sep 1, 2026 · 10:30 UTC
            </time>
          </dd>
        </div>
      </dl>

      <p class="sd-card-footer sd-small sd-muted">
        Production dossiers should link to the originating public record
        and distinguish reported amounts from confirmed availability.
      </p>
    </article>
  </div>

  <p id="docket-scroll-help" class="sd-small sd-muted">
    Scroll horizontally to view all fields on smaller screens.
  </p>

  <div class="docket-scroll" role="region"
       aria-label="Illustrative docket records"
       aria-describedby="docket-scroll-help" tabindex="0">
    <table class="table-terminal">
      <caption>Preview dataset — synthetic records</caption>
      <thead>
        <tr>
          <th scope="col">Case identifier</th>
          <th scope="col">Jurisdiction</th>
          <th scope="col">Category</th>
          <th scope="col" class="numeric">Reported surplus</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row" class="tabular-nums">SAMPLE-2026-001042</th>
          <td>Example County, FL</td>
          <td>Tax deed</td>
          <td class="numeric">$148,250.00</td>
        </tr>
        <tr>
          <th scope="row" class="tabular-nums">SAMPLE-2026-001043</th>
          <td>Example County, TX</td>
          <td>Court registry</td>
          <td class="numeric">$62,400.00</td>
        </tr>
      </tbody>
    </table>
  </div>
</section>
```

For production dossier cards, add `.card-interactive` **only when you add a real dossier link**. Keep the card as an article; do not turn a container containing multiple controls into a nested-link target.

### C. Pricing cards and comparison matrix

Highlight breadth of coverage rather than using “most popular,” artificial urgency, or oversized discounts. The secondary tier below is a layout example, not an asserted product offering.

```html
<section class="sd-shell sd-section sd-stack"
         aria-labelledby="pricing-heading">
  <h2 id="pricing-heading">Coverage for your practice</h2>

  <div class="sd-grid">
    <article class="card-institutional card-interactive sd-pricing-card">
      <p class="sd-eyebrow">Focused coverage</p>
      <h3>Single-State Access</h3>
      <p class="sd-muted">
        A focused jurisdictional workspace for a state-based practice.
      </p>
      <!-- Render the actual price and billing cadence from your catalog. -->
      <ul class="sd-feature-list">
        <li>One supported state</li>
        <li>Jurisdiction-specific research scope</li>
      </ul>
      <a class="sd-button sd-button--secondary"
         href="/pricing/single-state">
        View single-state terms
      </a>
    </article>

    <article class="card-institutional card-interactive
                    sd-pricing-card sd-pricing-card--suite">
      <span class="badge-statutory">Six-state coverage</span>
      <h3>6-State Suite</h3>
      <p class="sd-muted">
        A unified research scope for multi-jurisdictional practices.
      </p>
      <!-- Use .tabular-nums on the catalog-bound price. -->
      <ul class="sd-feature-list">
        <li>Florida, Texas, and Georgia</li>
        <li>California, North Carolina, and Tennessee</li>
      </ul>
      <a class="sd-button" href="/pricing/six-state">
        View 6-State Suite terms
      </a>
    </article>
  </div>

  <div class="docket-scroll" role="region"
       aria-label="Coverage comparison; scroll horizontally if needed"
       tabindex="0">
    <table class="table-terminal">
      <caption>Coverage comparison</caption>
      <thead>
        <tr>
          <th scope="col">Coverage</th>
          <th scope="col">Single-State Access</th>
          <th scope="col" class="suite-column">6-State Suite</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row">Jurisdictions</th>
          <td>One selected state</td>
          <td class="suite-column">All six supported states</td>
        </tr>
        <tr>
          <th scope="row">Geographic scope</th>
          <td>Selected jurisdiction</td>
          <td class="suite-column">
            Florida, Texas, Georgia, California,
            North Carolina, Tennessee
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</section>
```

For the full matrix, use explicit **“Included,” “Not included,” or a stated limit** rather than unexplained checkmarks. Display billing cadence adjacent to price, not in a tooltip.

### D. Practitioner Toolkit callout

```html
<aside class="sd-shell sd-section" aria-labelledby="toolkit-heading">
  <div class="card-institutional sd-toolkit">
    <div class="sd-stack">
      <p class="sd-eyebrow">Practice resources</p>
      <h2 id="toolkit-heading">Practitioner Toolkit</h2>
      <p class="sd-prose sd-muted">
        Access reference materials for surplus and excess-proceeds research.
        Confirm current requirements against the governing authority and
        originating public record.
      </p>
    </div>

    <a class="sd-button sd-button--secondary" href="/toolkit">
      Explore the toolkit <span aria-hidden="true">→</span>
    </a>
  </div>
</aside>
```

**Release checks:** test keyboard navigation, 200% zoom, 320px viewport width, long case identifiers, unusually large amounts, reduced motion, and source-link availability. These details contribute more to institutional trust than additional visual ornament.