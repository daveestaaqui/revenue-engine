#!/usr/bin/env python3
"""
Builds and uploads the ground-truth reconciled reply draft for Kayo Manson-Tompkins.
Safely escapes all shell parameters by executing directly in Python.
"""
import os
import email.message
import email.utils
import imaplib
from pathlib import Path
import dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
dotenv.load_dotenv(BASE_DIR / ".env")

msg = email.message.EmailMessage()
msg["From"] = "David Mahler <david@surplusdocket.com>"
msg["To"] = "Kayo Manson-Tompkins <kmtompkins@steelellp.com>"
msg["Subject"] = "RE: San Diego County tax sale excess proceeds — Parcel 360-150-12-00"
msg["Reply-To"] = "David Mahler <david@surplusdocket.com>"
msg["In-Reply-To"] = "<BL0PR05MB5123B07302B6E39C52A52ABBD4652@BL0PR05MB5123.namprd05.prod.outlook.com>"
msg["References"] = "<179269230088.1922.1178984248152311732@surplusdocket.com> <BL0PR05MB5123B07302B6E39C52A52ABBD4652@BL0PR05MB5123.namprd05.prod.outlook.com>"
msg["Date"] = email.utils.formatdate(localtime=True)
msg["Message-ID"] = email.utils.make_msgid(domain="surplusdocket.com")

body = """Hi Kayo,

Yes, the physical property address for Parcel 360-150-12-00 is:

4850 Jennifer Ct
San Diego, CA 92117
(Clairemont neighborhood, San Diego County)

Key property and official county accounting details from the San Diego County Treasurer-Tax Collector records:
• Property Type: Single-Family Residence (approx. 1,120 sq. ft., built 1958)
• Reported Prior Titleholder: DISE LEONARD L 1999 TRUST 07-27-99 ET AL
• Sale Authority / Item: SDTTC Public Auction PA-7102, Item 0263
• Tax Deed Recording Date: April 22, 2026 (Document #2026-0111958)
• Official Auction Sale Price (Winning Bid): $890,100.00
• Statutory Taxes & County Deductions: -$8,436.65
• Net Unclaimed Excess Proceeds Deposited: $881,663.35
• Governing Statute: Cal. Rev. & Tax Code § 4675 (1-year claim deadline from deed recording)
• Statutory 20% Benchmark Recovery for Counsel: $176,332.67

Official Ground Truth Reconciliation Note:
On Page 9 of the official San Diego County Final Report of Sale (PA-7102, Item 0263), the prominent column lists the gross winning auction bid of $890,100.00. Under California Revenue & Taxation Code §§ 4672-4674, the county withheld current taxes and statutory costs totaling $8,436.65 (including current taxes of $5,270.39, Teeter funds of $1,284.38, doc transfer tax of $979.55, redemption fee of $506.00, personal contact fee of $461.74, and county fees of $434.50). The remaining balance of exactly $881,663.35 was deposited into the county trust fund as the net unclaimed excess proceeds subject to claim under § 4675.

You can inspect the full verified docket dossier, official reconciliation breakdown, and the direct county tax collector PDF report on our portal here:
https://surplusdocket.com/docket.html?docket=360-150-12-00&county=San+Diego&state=CA&k=a65adddbec62f259d76736470f06a3b7

We have also updated our docket intelligence system and live feeds so that full property street addresses and gross-to-net accounting breakdowns are populated across our files and included in all future docket notifications.

Please let me know if your office plans to petition for these proceeds or if you need the direct county claim documentation.

Best regards,

David Mahler
Surplus Docket Public Records Intelligence
surplusdocket.com
david@surplusdocket.com

---
Legal Notice & Regulatory Disclaimer: Surplus Docket is a specialized legal technology and court records intelligence service, not a law firm. Surplus Docket does not provide legal advice, legal counsel, or legal representation, and no attorney-client relationship is formed by this correspondence. All docket records, statutory references, and procedural timelines are compiled exclusively for informational and intelligence purposes for licensed attorneys and recovery professionals. Surplus recovery petitions, motions, and pleadings must be prepared and filed by a licensed attorney admitted to practice in the appropriate jurisdiction."""

msg.set_content(body)

# Save .eml
eml_path = BASE_DIR / "outreach" / "drafts" / "REPLY_kmtompkins_4850_Jennifer_Ct.eml"
eml_bytes = msg.as_bytes()
with open(eml_path, "wb") as f:
    f.write(eml_bytes)
print(f"Saved {len(eml_bytes)} bytes to {eml_path}")

# Upload to Gmail Drafts
user = os.getenv("GMAIL_USER")
pwd = os.getenv("GMAIL_APP_PASS")
if user and pwd:
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user, pwd)
        mail.select('"[Gmail]/Drafts"')
        
        # Delete existing drafts to kmtompkins
        res, data = mail.search(None, "ALL")
        if data[0]:
            for mid in data[0].split():
                h_res, h_data = mail.fetch(mid, "(BODY[HEADER.FIELDS (TO SUBJECT)])")
                h_msg = email.message_from_bytes(h_data[0][1])
                if "kmtompkins" in str(h_msg.get("To", "")):
                    print(f"Deleting old draft {mid.decode()}...")
                    mail.store(mid, "+FLAGS", "\\Deleted")
            mail.expunge()

        # Upload verified draft
        res, append_data = mail.append('"[Gmail]/Drafts"', "\\Draft", None, eml_bytes)
        print(f"Draft upload to Gmail: {res} {append_data}")
        mail.logout()
    except Exception as e:
        print(f"IMAP error: {e}")
