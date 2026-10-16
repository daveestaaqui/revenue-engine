#!/usr/bin/env python3
"""
Create a candid salvage email draft for Cohen Asset Recovery (Alden, Phil, Adam)
acknowledging the earlier synthetic sample data issue, attaching the real verified
Florida_Surplus_Feed.csv, saving locally, and uploading to [Gmail]/Drafts via IMAP.
"""

import os
import sys
import time
import imaplib
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE, "r", encoding="utf-8") as ef:
        for line in ef:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

GMAIL_USER = os.getenv("GMAIL_USER", "sandwichfitness@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")

SUBJECT = "Re: Florida feed questions: Miami-Dade, Palm Beach, and Broward"
TO_HEADER = '"A.L.D.E.N." <alden@cohenrecoverylaw.com>'
CC_HEADER = "phil@cohenrecoverylaw.com, adam@cohenrecoverylaw.com"
FROM_HEADER = "David Mahler <david@surplusdocket.com>"
IN_REPLY_TO = "<179122056825.2170.16982405525916920611@surplusdocket.com>"
REFERENCES = (
    "<CAD4DNF_Nc-gKjn1H2vMypOzqrt9yipGDjysQ5iJ4-XtYm_cX9Q@mail.gmail.com> "
    "<0A00ED4D-E826-46B2-A4E3-13B9170AA2EA@surplusdocket.com> "
    "<179122056825.2170.16982405525916920611@surplusdocket.com>"
)

TEXT_BODY = """Hi Alden, Phil, and Adam,

I'm writing to owe your team a direct apology.

After auditing the early Florida sample CSV we sent over on September 29, I discovered that our prototype export script had pulled from an internal sandbox fixture rather than live county clerk publications. In plain terms: the sample rows we sent you contained synthetic test data rather than real court dockets.

For a legal data service, that is a fatal mistake, and if your team immediately wrote us off after checking those case numbers against the clerk portals, you were 100% right to do so.

Over the past week, I personally purged every synthetic fixture and fallback across our entire codebase and rebuilt the pipeline strictly around live, machine-verifiable county publications:

1. Direct Clerk Source Verification: Every record in our feed now carries a direct `Clerk_Verification_URL` pointing to the official county clerk PDF or spreadsheet (with `#search=<CASE_NO>` deep-linking directly to the row on the clerk's server).
2. Honest Coverage Boundaries: If a county clerk gates its surplus list behind interactive session portals or CAPTCHAs (as Miami-Dade, Palm Beach, and Broward currently do for bulk exports), we do not fabricate or extrapolate rows for them. In Florida today, our automated feed indexes Hillsborough County Clerk (`hillsclerk.com`), where both the Daily Circuit Civil Court Registry Balances PDF and Weekly Tax Deed Surplus spreadsheet are published openly.
3. Live Examples You Can Verify Right Now:
   • Case 22-CA-008975 (Hillsborough Circuit Civil) — Cindy Stuart — $226,740.20
     Direct Clerk PDF: https://publicrec.hillsclerk.com/Civil/registry_trust_balances/Registry_and_TrustAccounts_Balances_as_of_Wed_10_14_2026.pdf#search=22-CA-008975
   • Case 23-CA-016325 (Hillsborough Circuit Civil) — Thelma Mae Billing — $211,052.49
     Direct Clerk PDF: https://publicrec.hillsclerk.com/Civil/registry_trust_balances/Registry_and_TrustAccounts_Balances_as_of_Wed_10_14_2026.pdf#search=23-CA-016325
   • Tax Deed 2022-A00807 (Hillsborough Tax Deed Surplus) — $97,232.98
     Official Clerk Index: https://www.hillsclerk.com/records-and-reports/tax-deed-surplus

I've attached today's verified Florida feed (`Florida_Surplus_Feed.csv` — 157 live Hillsborough Circuit Civil and Tax Deed records totaling $1.52M) as well as our full 611-record multi-state feed (`Master_Surplus_Lead_Feed.csv`), with no strings attached.

I don't expect a second chance after a first impression like that, but I wanted to be transparent about what happened, confirm that it is fixed, and leave you with real, verifiable data. If your team ever wants complimentary access as we bring direct South Florida clerk integrations online, just reply here and I will provision your firm at no cost.

Sincerely,

David Mahler
Managing Director | Surplus Docket
david@surplusdocket.com
https://surplusdocket.com
"""

HTML_BODY = """<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #1e293b; max-width: 680px;">
<p>Hi Alden, Phil, and Adam,</p>

<p>I'm writing to owe your team a direct apology.</p>

<p>After auditing the early Florida sample CSV we sent over on September 29, I discovered that our prototype export script had pulled from an internal sandbox fixture rather than live county clerk publications. In plain terms: the sample rows we sent you contained synthetic test data rather than real court dockets.</p>

<p>For a legal data service, that is a fatal mistake, and if your team immediately wrote us off after checking those case numbers against the clerk portals, you were 100% right to do so.</p>

<p>Over the past week, I personally purged every synthetic fixture and fallback across our entire codebase and rebuilt the pipeline strictly around live, machine-verifiable county publications:</p>

<ol style="padding-left: 20px;">
  <li style="margin-bottom: 8px;"><strong>Direct Clerk Source Verification:</strong> Every record in our feed now carries a direct <code>Clerk_Verification_URL</code> pointing to the official county clerk PDF or spreadsheet (with <code>#search=&lt;CASE_NO&gt;</code> deep-linking directly to the row on the clerk's server).</li>
  <li style="margin-bottom: 8px;"><strong>Honest Coverage Boundaries:</strong> If a county clerk gates its surplus list behind interactive session portals or CAPTCHAs (as Miami-Dade, Palm Beach, and Broward currently do for bulk exports), we do not fabricate or extrapolate rows for them. In Florida today, our automated feed indexes Hillsborough County Clerk (<code>hillsclerk.com</code>), where both the Daily Circuit Civil Court Registry Balances PDF and Weekly Tax Deed Surplus spreadsheet are published openly.</li>
  <li style="margin-bottom: 8px;"><strong>Live Examples You Can Verify in One Click:</strong>
    <ul style="margin-top: 6px;">
      <li>Case <strong>22-CA-008975</strong> (Hillsborough Circuit Civil) &mdash; Cindy Stuart &mdash; <strong>$226,740.20</strong> (<a href="https://publicrec.hillsclerk.com/Civil/registry_trust_balances/Registry_and_TrustAccounts_Balances_as_of_Wed_10_14_2026.pdf#search=22-CA-008975" style="color: #1b365d;">Open Official Clerk PDF &rarr;</a> | <a href="https://surplusdocket.com/?docket=22-CA-008975#live-docket" style="color: #365134;">View on Surplus Docket &rarr;</a>)</li>
      <li>Case <strong>23-CA-016325</strong> (Hillsborough Circuit Civil) &mdash; Thelma Mae Billing &mdash; <strong>$211,052.49</strong> (<a href="https://publicrec.hillsclerk.com/Civil/registry_trust_balances/Registry_and_TrustAccounts_Balances_as_of_Wed_10_14_2026.pdf#search=23-CA-016325" style="color: #1b365d;">Open Official Clerk PDF &rarr;</a> | <a href="https://surplusdocket.com/?docket=23-CA-016325#live-docket" style="color: #365134;">View on Surplus Docket &rarr;</a>)</li>
      <li>Tax Deed <strong>2022-A00807</strong> (Hillsborough Tax Deed Surplus) &mdash; <strong>$97,232.98</strong> (<a href="https://www.hillsclerk.com/records-and-reports/tax-deed-surplus" style="color: #1b365d;">Official Clerk Tax Deed Surplus Page &rarr;</a> | <a href="https://surplusdocket.com/?docket=2022-A00807#live-docket" style="color: #365134;">View on Surplus Docket &rarr;</a>)</li>
    </ul>
  </li>
</ol>

<p>I've attached today's verified Florida feed (<code>Florida_Surplus_Feed.csv</code> &mdash; 157 live Hillsborough Circuit Civil and Tax Deed records totaling $1.52M) as well as our full 611-record multi-state feed (<code>Master_Surplus_Lead_Feed.csv</code>), with no strings attached.</p>

<p>I don't expect a second chance after a first impression like that, but I wanted to be transparent about what happened, confirm that it is fixed, and leave you with real, verifiable data. If your team ever wants complimentary access as we bring direct South Florida clerk integrations online, just reply here and I will provision your firm at no cost.</p>

<p>Sincerely,</p>

<p><strong>David Mahler</strong><br>
Managing Director | Surplus Docket<br>
<a href="mailto:david@surplusdocket.com" style="color: #1b365d;">david@surplusdocket.com</a><br>
<a href="https://surplusdocket.com" style="color: #365134;">https://surplusdocket.com</a></p>
</body>
</html>
"""


def build_mime_message() -> MIMEMultipart:
    msg = MIMEMultipart("mixed")
    msg["From"] = FROM_HEADER
    msg["To"] = TO_HEADER
    msg["Cc"] = CC_HEADER
    msg["Reply-To"] = "david@surplusdocket.com"
    msg["Subject"] = SUBJECT
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain="surplusdocket.com")
    msg["In-Reply-To"] = IN_REPLY_TO
    msg["References"] = REFERENCES

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(TEXT_BODY, "plain", "utf-8"))
    alt.attach(MIMEText(HTML_BODY, "html", "utf-8"))
    msg.attach(alt)

    for fname in ("Florida_Surplus_Feed.csv", "Master_Surplus_Lead_Feed.csv"):
        fpath = BASE_DIR / "exports" / fname
        if fpath.exists():
            part = MIMEBase("text", "csv")
            with open(fpath, "rb") as f:
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{fname}"')
            msg.attach(part)

    return msg


def main():
    out_dir = BASE_DIR / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    msg = build_mime_message()

    eml_path = out_dir / "cohen_recovery_salvage_draft.eml"
    with open(eml_path, "wb") as f:
        f.write(msg.as_bytes())
    print(f"[✓] Saved local EML draft: {eml_path}")

    md_path = out_dir / "LAWYER_SALVAGE_DRAFT.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Salvage Outreach Draft — Cohen Asset Recovery\n\n")
        f.write(f"- **To:** `{TO_HEADER}`\n")
        f.write(f"- **Cc:** `{CC_HEADER}`\n")
        f.write(f"- **From:** `{FROM_HEADER}`\n")
        f.write(f"- **Subject:** `{SUBJECT}`\n")
        f.write(f"- **In-Reply-To:** `{IN_REPLY_TO}`\n")
        f.write(f"- **Attachments:** `Florida_Surplus_Feed.csv` (157 verified records), `Master_Surplus_Lead_Feed.csv` (611 verified records)\n\n")
        f.write("## Email Body\n\n```text\n")
        f.write(TEXT_BODY.strip())
        f.write("\n```\n")
    print(f"[✓] Saved local Markdown draft: {md_path}")

    if GMAIL_APP_PASS:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_HOST, 993, timeout=20)
            mail.login(GMAIL_USER, GMAIL_APP_PASS)
            status, _ = mail.append('"[Gmail]/Drafts"', "\\Draft", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
            mail.logout()
            print(f"[✓] Uploaded threaded salvage draft to [Gmail]/Drafts (status: {status})")
        except Exception as exc:
            print(f"[!] Could not append to [Gmail]/Drafts via IMAP: {exc}")


if __name__ == "__main__":
    main()
