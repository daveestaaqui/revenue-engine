/**
 * OpenSurplus SDK v1.2.0 — Multi-State Statutory Deadline & Fee Cap Engine
 * =========================================================================
 * Open-source JavaScript SDK & <surplus-statute-calculator> Web Component
 * by Surplus Docket Public Records Intelligence (https://surplusdocket.com).
 *
 * License: MIT
 * Repository & Docs: https://surplusdocket.com/sdk/
 */
(function (global) {
  "use strict";

  const JURISDICTIONS = {
    FL: {
      state: "FL",
      name: "Florida",
      statute: "Fla. Stat. § 197.582",
      judicialStatute: "Fla. Stat. § 45.032",
      triggerEvent: "Clerk Notice of Surplus Date",
      windowDays: 120,
      windowLabel: "120 days from Clerk's statutory notice",
      feeCapPct: 0.20,
      venue: "Clerk of the Circuit Court (Tax Deed Division)",
      feedUrl: "https://surplusdocket.com/florida-tax-deed-surplus.html",
    },
    TX: {
      state: "TX",
      name: "Texas",
      statute: "Tex. Tax Code § 34.04",
      triggerEvent: "Sheriff / Constable Tax Sale Date",
      windowDays: 730,
      windowLabel: "2 years from date of tax foreclosure sale",
      feeCapPct: 0.25,
      venue: "District Court Registry (Original Tax Suit Cause No.)",
      feedUrl: "https://surplusdocket.com/texas-tax-sale-excess-proceeds.html",
    },
    CA: {
      state: "CA",
      name: "California",
      statute: "Cal. Rev. & Tax Code § 4675",
      triggerEvent: "Tax Deed to Purchaser Recordation Date",
      windowDays: 365,
      windowLabel: "1 year from recordation of the tax deed to purchaser",
      feeCapPct: 0.20,
      venue: "County Auditor-Controller / Board of Supervisors",
      feedUrl: "https://surplusdocket.com/california-tax-defaulted-excess-proceeds.html",
    },
    GA: {
      state: "GA",
      name: "Georgia",
      statute: "O.C.G.A. § 48-4-5",
      triggerEvent: "Tax Commissioner / Sheriff Sale Date",
      windowDays: 1825,
      windowLabel: "5 years from tax sale date (Superior Court Interpleader)",
      feeCapPct: 0.20,
      venue: "County Tax Commissioner / Superior Court Registry",
      feedUrl: "https://surplusdocket.com/georgia-tax-sale-excess-funds.html",
    },
    NC: {
      state: "NC",
      name: "North Carolina",
      statute: "N.C.G.S. § 105-374",
      triggerEvent: "Confirmation of Foreclosure Sale Date",
      windowDays: 730,
      windowLabel: "Special proceeding before Clerk of Superior Court",
      feeCapPct: 0.20,
      venue: "Clerk of Superior Court Special Proceedings",
      feedUrl: "https://surplusdocket.com/north-carolina-tax-foreclosure-surplus.html",
    },
    TN: {
      state: "TN",
      name: "Tennessee",
      statute: "T.C.A. § 67-5-2501",
      triggerEvent: "Chancery Court Confirmation of Sale Date",
      windowDays: 365,
      windowLabel: "Chancery Court Clerk & Master motion procedure",
      feeCapPct: 0.20,
      venue: "Chancery Court Clerk and Master",
      feedUrl: "https://surplusdocket.com/tennessee-tax-sale-excess-proceeds.html",
    },
  };

  function calculateDeadline(stateCode, triggerDateStr, surplusBalanceUSD) {
    const code = String(stateCode || "FL").trim().toUpperCase();
    const rule = JURISDICTIONS[code];
    if (!rule) {
      throw new Error("Unsupported jurisdiction: " + code);
    }
    const bal = Math.max(0, Number(surplusBalanceUSD) || 0);
    const start = triggerDateStr ? new Date(triggerDateStr + "T00:00:00Z") : new Date();
    const deadline = new Date(start.getTime() + rule.windowDays * 86400000);
    const now = new Date();
    const daysRemaining = Math.ceil((deadline.getTime() - now.getTime()) / 86400000);

    return {
      jurisdiction: rule.name,
      state: rule.state,
      governingStatute: rule.statute,
      triggerEvent: rule.triggerEvent,
      triggerDate: start.toISOString().slice(0, 10),
      statutoryDeadlineDate: deadline.toISOString().slice(0, 10),
      daysRemaining: daysRemaining,
      status: daysRemaining > 0 ? "OPEN_WINDOW" : "EXPIRED_OR_ESCHEATED",
      surplusBalanceUSD: Number(bal.toFixed(2)),
      statutoryFeeBenchmarkUSD: Number((bal * rule.feeCapPct).toFixed(2)),
      feeBenchmarkPct: rule.feeCapPct * 100,
      filingVenue: rule.venue,
      verificationFeedUrl: rule.feedUrl,
      attributionUrl: "https://surplusdocket.com/sdk/",
    };
  }

  const SurplusStatuteSDK = {
    version: "1.2.0",
    JURISDICTIONS: JURISDICTIONS,
    calculateDeadline: calculateDeadline,
  };

  global.SurplusStatuteSDK = SurplusStatuteSDK;

  if (typeof customElements !== "undefined" && !customElements.get("surplus-statute-calculator")) {
    class SurplusStatuteCalculator extends HTMLElement {
      connectedCallback() {
        const defaultState = (this.getAttribute("state") || "FL").toUpperCase();
        const today = new Date().toISOString().slice(0, 10);
        this.innerHTML = `
          <div style="font-family:Inter,-apple-system,sans-serif;border:1px solid #cbd5e1;border-radius:12px;padding:18px;background:#ffffff;max-width:520px;color:#1e293b;box-shadow:0 2px 8px rgba(15,23,42,0.06);">
            <div style="font-weight:800;font-size:15px;color:#1b365d;margin-bottom:4px;">Statutory Surplus Deadline &amp; Fee Benchmark Calculator</div>
            <div style="font-size:12px;color:#64748b;margin-bottom:12px;">Deterministic statutory rules for FL, TX, CA, GA, NC &amp; TN excess proceeds.</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">
              <label style="font-size:11px;font-weight:600;">Jurisdiction
                <select class="sd-state" style="width:100%;margin-top:4px;padding:6px;border:1px solid #cbd5e1;border-radius:6px;font-size:12px;">
                  <option value="FL" ${defaultState === "FL" ? "selected" : ""}>Florida (§ 197.582)</option>
                  <option value="TX" ${defaultState === "TX" ? "selected" : ""}>Texas (§ 34.04)</option>
                  <option value="CA" ${defaultState === "CA" ? "selected" : ""}>California (§ 4675)</option>
                  <option value="GA" ${defaultState === "GA" ? "selected" : ""}>Georgia (§ 48-4-5)</option>
                  <option value="NC" ${defaultState === "NC" ? "selected" : ""}>North Carolina (§ 105-374)</option>
                  <option value="TN" ${defaultState === "TN" ? "selected" : ""}>Tennessee (§ 67-5-2501)</option>
                </select>
              </label>
              <label style="font-size:11px;font-weight:600;">Sale / Notice Date
                <input type="date" class="sd-date" value="${today}" style="width:100%;margin-top:4px;padding:6px;border:1px solid #cbd5e1;border-radius:6px;font-size:12px;" />
              </label>
            </div>
            <label style="font-size:11px;font-weight:600;display:block;margin-bottom:10px;">Reported Surplus Balance (USD)
              <input type="number" class="sd-bal" value="125000" step="100" style="width:100%;margin-top:4px;padding:6px;border:1px solid #cbd5e1;border-radius:6px;font-size:12px;" />
            </label>
            <div class="sd-output" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px;font-size:12px;line-height:1.5;"></div>
            <div style="margin-top:10px;font-size:11px;color:#64748b;display:flex;justify-content:space-between;align-items:center;">
              <span>OpenSurplus SDK v1.2</span>
              <a href="https://surplusdocket.com/tools.html" target="_blank" rel="noopener" style="color:#4c6d48;font-weight:700;text-decoration:none;">Powered by Surplus Docket &rarr;</a>
            </div>
          </div>
        `;
        const update = () => {
          const st = this.querySelector(".sd-state").value;
          const dt = this.querySelector(".sd-date").value;
          const bal = this.querySelector(".sd-bal").value;
          const res = calculateDeadline(st, dt, bal);
          this.querySelector(".sd-output").innerHTML = `
            <div><strong>Governing Statute:</strong> ${res.governingStatute}</div>
            <div><strong>Filing Venue:</strong> ${res.filingVenue}</div>
            <div><strong>Claim Deadline:</strong> ${res.statutoryDeadlineDate} (${res.daysRemaining} days remaining)</div>
            <div><strong>Statutory Fee Benchmark (${res.feeBenchmarkPct}%):</strong> $${res.statutoryFeeBenchmarkUSD.toLocaleString()}</div>
            <div style="margin-top:4px;"><a href="${res.verificationFeedUrl}" target="_blank" rel="noopener" style="color:#1b365d;font-weight:600;">Inspect Live ${res.jurisdiction} Registry Dockets &rarr;</a></div>
          `;
        };
        this.querySelectorAll("select, input").forEach((el) => el.addEventListener("input", update));
        update();
      }
    }
    customElements.define("surplus-statute-calculator", SurplusStatuteCalculator);
  }
})(typeof window !== "undefined" ? window : globalThis);
