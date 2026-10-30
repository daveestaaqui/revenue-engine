<!--
PLATFORM: SUBSTACK
TITLE: Open-Source LegalTech: Introducing the OpenSurplus Statutory Calculator SDK, Python CLI & OpenAPI 3.1 Spec
CANONICAL_URL: https://surplusdocket.com/blog/posts/open-source-surplus-statute-calculator-and-openapi-sdk.html
DATE: October 30, 2026
TAGS: LegalTech, OpenSource, Python, WebComponents, OpenAPI
-->

# Open-Source LegalTech: Introducing the OpenSurplus Statutory Calculator SDK, Python CLI & OpenAPI 3.1 Spec

*Originally published on [Surplus Docket Legal Intelligence](https://surplusdocket.com/blog/posts/open-source-surplus-statute-calculator-and-openapi-sdk.html)*

---
### Why Statutory Surplus Calculation Needs Deterministic Open-Source Tooling

Across the United States, post-foreclosure tax deed and judicial excess proceeds are governed by strict statutory claim limitation windows and non-attorney fee restrictions. Missing a filing deadline under Florida Statute § 197.582(3) (120 days) or California Revenue & Taxation Code § 4675 (365 days from tax deed recordation) results in permanent forfeiture of equity.

To eliminate manual calculation errors and support university housing clinics, bar associations, and real estate litigation practices, [Surplus Docket](https://surplusdocket.com) has released the **OpenSurplus SDK v1.2.0** under the permissive MIT License.

### What Is Included in the OpenSurplus Release

1. **Zero-Dependency JavaScript SDK & `<surplus-statute-calculator>` Web Component (`https://surplusdocket.com/sdk/surplus-statute-sdk.js`):**
   Law firm websites, legal blogs, and access-to-justice portals can drop a single custom HTML element onto any page to render a Shadow DOM-isolated calculator for FL, TX, CA, GA, NC, and TN.
2. **Standalone Python 3 CLI & Module (`https://surplusdocket.com/sdk/surplus_statute_cli.py`):**
   Built using only the Python 3 standard library (`datetime`, `json`, `csv`, `argparse`), allowing legal engineers to batch-evaluate CSV dockets or run single-file CLI audits with `--json` output.
3. **OpenAPI 3.1.0 Public Specification (`https://surplusdocket.com/openapi.json`):**
   Machine-readable JSON Schema definitions for integrating live verified county surplus feeds and cryptographic verification manifests into Clio Manage, Filevine, MyCase, or custom legal AI agents.

Explore the interactive documentation and download the SDK directly at the [OpenSurplus Developer & LegalTech Hub](https://surplusdocket.com/sdk/).

---

### About the Author & Platform
This analysis was authored by the research team at **[Surplus Docket](https://surplusdocket.com)**. Surplus Docket provides real-time court docket intelligence, junior lien title scrubbing, and statutory deadline automation for legal practices in foreclosure defense, probate, and real estate litigation.

- **Interactive Calculator Widget:** [Statutory Surplus Calculator](https://surplusdocket.com/embed/surplus-calculator.html)
- **Open-Source SDK & Python CLI:** [OpenSurplus SDK v1.2.0 & Web Component](https://surplusdocket.com/sdk/)
- **OpenAPI 3.1.0 Specification:** [Public Records & Statutory Intelligence API](https://surplusdocket.com/openapi.json)
- **Public Educational Resource:** [Homeowner's Guide to Foreclosure Surplus](https://surplusdocket.com/resources/homeowner-surplus-guide.html)
- **Live Court Registry Feeds:** [Surplus Docket Intelligence](https://surplusdocket.com/#data)

*Canonical Source: [https://surplusdocket.com/blog/posts/open-source-surplus-statute-calculator-and-openapi-sdk.html](https://surplusdocket.com/blog/posts/open-source-surplus-statute-calculator-and-openapi-sdk.html)*
