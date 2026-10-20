# Salvage Outreach Draft: Cohen Asset Recovery

**Thread Context**: In reply to Alden Cohen's Sept 29 question regarding Florida feed data in Miami-Dade, Palm Beach, and Broward.
**Recipients**: `alden@cohenrecoverylaw.com`, CC: `phil@cohenrecoverylaw.com, adam@cohenrecoverylaw.com`
**Status**: Saved in `[Gmail]/Drafts` via IMAP. Ready for manual review and send.

---

### Email Headers:
* **To**: "A.L.D.E.N." <alden@cohenrecoverylaw.com>
* **Cc**: phil@cohenrecoverylaw.com, adam@cohenrecoverylaw.com
* **From**: David Mahler <david@surplusdocket.com>
* **Subject**: Re: Florida feed questions: Miami-Dade, Palm Beach, and Broward
* **In-Reply-To**: `<179122056825.2170.16982405525916920611@surplusdocket.com>`
* **Attachments**: `Florida_Surplus_Feed.csv` (157 records), `Master_Surplus_Lead_Feed.csv` (611 records)

---

### Message Body:

Hi Alden, Phil, and Adam,

I'm writing to owe your team a direct apology.

After auditing the early Florida sample CSV we sent over on September 29, I discovered that our prototype export script had pulled from an internal sandbox fixture rather than live county clerk publications. In plain terms: the sample rows we sent you contained synthetic test data rather than real court dockets.

For a legal data service, that is a fatal mistake, and if your team immediately wrote us off after checking those case numbers against the clerk portals, you were 100% right to do so.

Over the past week, I personally purged every synthetic fixture and fallback across our entire codebase and rebuilt the pipeline strictly around live, machine-verifiable county publications:

1. Direct Clerk Source Verification: Every record in our feed now carries a direct verification source linking directly to the clerk's docket and official documents on the clerk's server.
2. Honest Coverage Boundaries: If a county clerk gates its surplus list behind interactive session portals or CAPTCHAs (as Miami-Dade, Palm Beach, and Broward currently do for bulk exports), we do not fabricate or extrapolate rows for them. In Florida today, our automated feed indexes Hillsborough County Clerk (hillsclerk.com), where both the Daily Circuit Civil Court Registry Balances and Weekly Tax Deed Surplus listings are published openly.
3. Live Examples You Can Verify Right Now:
   • Case 22-CA-008975 (Hillsborough Circuit Civil) — Cindy Stuart — $226,740.20
     Verified Docket Dossier: https://surplusdocket.com/docket?id=22-CA-008975&k=a65adddbec62f259d76736470f06a3b7&ref=d3ec19d55239
   • Case 23-CA-016325 (Hillsborough Circuit Civil) — Thelma Mae Billing — $211,052.49
     Verified Docket Dossier: https://surplusdocket.com/docket?id=23-CA-016325&k=a65adddbec62f259d76736470f06a3b7&ref=80f7befa0c84
   • Tax Deed File 18-LW-000360 (Hillsborough Tax Deed Surplus) — $521,651.56
     Verified Docket Dossier: https://surplusdocket.com/docket?id=18-LW-000360&k=a65adddbec62f259d76736470f06a3b7&ref=31e3a7e9cdb3

I've attached today's verified Florida feed (Florida_Surplus_Feed.csv — 157 live Hillsborough Circuit Civil and Tax Deed records totaling $1.52M) as well as our full 611-record multi-state feed (Master_Surplus_Lead_Feed.csv totaling $30.3M), with no strings attached.

I don't expect a second chance after a first impression like that, but I wanted to be transparent about what happened, confirm that it is fixed, and leave you with real, verifiable data. If your team ever wants complimentary access as we bring direct South Florida clerk integrations online, just reply here and I will provision your firm at no cost.

Sincerely,

David Mahler
Managing Director | Surplus Docket
david@surplusdocket.com
https://surplusdocket.com

