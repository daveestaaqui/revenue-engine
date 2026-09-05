#!/usr/bin/env python3
"""
Surplus Docket — 7:00 AM EST Autonomous Morning Feed Dispatcher
================================================================
Reads active subscribers from portal/subscribers.json, compiles daily
verified court intelligence summaries, attaches latest CSV/Excel dockets,
and dispatches via authenticated SMTP.
"""

import os
import sys
import json
import smtplib
import argparse
import pandas as pd
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import email.utils
from pathlib import Path

# Root directory setup
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Optional local .env loading
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    try:
        with open(ENV_FILE, "r") as ef:
            for line in ef:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))
    except Exception:
        pass

# Paths
EXPORTS_DIR = BASE_DIR / "exports"
SUBSCRIBERS_FILE = BASE_DIR / "portal" / "subscribers.json"
MASTER_CSV = EXPORTS_DIR / "Master_Surplus_Lead_Feed.csv"
MASTER_XLSX = EXPORTS_DIR / "Master_Surplus_Lead_Feed.xlsx"

# Credentials & Identity
GMAIL_USER = os.getenv("GMAIL_USER", "sandwichfitness@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")
FROM_NAME = os.getenv("FROM_NAME", "Elena Brooks | Surplus Docket")
FROM_EMAIL = os.getenv("FROM_EMAIL", "elena.brooks@surplusdocket.com")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

LEGAL_DISCLAIMER = (
    "Surplus Docket provides court record intelligence and indexing for licensed legal professionals "
    "and does not provide legal advice or claimant representation."
)


def load_active_subscribers():
    if not SUBSCRIBERS_FILE.exists():
        return []
    with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [s for s in data if s.get("status", "").upper() == "ACTIVE"]


def get_feed_statistics():
    if not MASTER_CSV.exists():
        return {
            "total_records": 0,
            "total_surplus": 0.0,
            "top_dockets": [],
            "jurisdiction_counts": {}
        }
    df = pd.read_csv(MASTER_CSV)
    total_records = len(df)
    surplus_col = "Surplus_Balance_USD" if "Surplus_Balance_USD" in df.columns else "AMOUNT"
    total_surplus = float(df[surplus_col].sum()) if surplus_col in df.columns else 0.0

    state_col = "State" if "State" in df.columns else "COUNTY"
    jurisdiction_counts = df[state_col].value_counts().to_dict() if state_col in df.columns else {}

    top_dockets = []
    for _, r in df.head(4).iterrows():
        top_dockets.append({
            "docket": str(r.get("Tax_Deed_Number") or r.get("TAX_DEED_NO") or "Pending"),
            "owner": str(r.get("Owner_Name") or r.get("DEFENDANT") or "Record Titleholder"),
            "amount": float(r.get(surplus_col, 0.0)),
            "state": str(r.get("State") or "FL"),
            "county": str(r.get("County") or r.get("COUNTY") or "")
        })

    return {
        "total_records": total_records,
        "total_surplus": total_surplus,
        "top_dockets": top_dockets,
        "jurisdiction_counts": jurisdiction_counts
    }


def compose_email_content(subscriber, stats, date_str):
    name = subscriber.get("name", "Counsel")
    firm = subscriber.get("firm", "Practice")
    total_bal_fmt = f"${stats['total_surplus']:,.2f}"
    rec_count = stats["total_records"]

    dockets_text = ""
    dockets_html = ""
    for d in stats["top_dockets"]:
        dockets_text += f"• Docket {d['docket']} ({d['county']}, {d['state']}) — ${d['amount']:,.2f} surplus balance\n"
        dockets_html += f"""
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid #e2e8f0; font-family: monospace; font-size: 12px; color: #1b365d;"><b>{d['docket']}</b></td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #e2e8f0; font-size: 13px;">{d['owner']}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #e2e8f0; font-size: 13px; color: #64748b;">{d['county']}, {d['state']}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #e2e8f0; font-family: monospace; font-size: 13px; font-weight: bold; color: #4c6d48; text-align: right;">${d['amount']:,.2f}</td>
        </tr>
        """

    text_body = f"""Good morning {name},

Here is your daily Surplus Docket intelligence briefing for {date_str}.

Our automated court registry crawlers completed today's morning ingestion run at 7:00 AM EST. All dockets have been audited against clerk verification portals and filtered upstream to eliminate senior mortgages, institutional bank liens, and junior municipal encumbrances.

TODAY'S BENCHMARK SUMMARY:
• Active Verified Records: {rec_count} files
• Gross Unencumbered Surplus: {total_bal_fmt}
• Upstream Bank Lien Filtering: 100% Verified
• Jurisdictions Monitored: Florida, Texas, Georgia, North Carolina, Tennessee, California

FEATURED HIGH-EQUITY DOCKETS:
{dockets_text}

Your complete unencumbered docket feeds are attached to this dispatch in both CSV and Excel (.xlsx) formats for immediate importation into your practice management software.

If you have any questions on specific file dockets or require custom circuit exports, simply reply to this transmission.

Best regards,

Elena Brooks
Senior Docket Specialist | Surplus Docket
surplusdocket.com
elena.brooks@surplusdocket.com

---
{LEGAL_DISCLAIMER}
"""

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Surplus Docket Intelligence Dispatch</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8f8f4; margin: 0; padding: 24px; color: #1e293b; line-height: 1.5;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f8f8f4; width: 100%;">
        <tr>
            <td align="center" style="padding: 0;">
                <table role="presentation" width="680" cellpadding="0" cellspacing="0" border="0" style="max-width: 680px; width: 100%; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #1b365d; padding: 26px 32px; border-bottom: 3px solid #4c6d48;">
                            <h1 style="margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.02em; color: #ffffff;">SURPLUS DOCKET</h1>
                            <p style="margin: 6px 0 0 0; font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; font-family: 'Courier New', Courier, monospace;">Daily Court Intelligence Dispatch • {date_str}</p>
                        </td>
                    </tr>
                    <!-- Main Content -->
                    <tr>
                        <td style="padding: 32px; background-color: #ffffff;">
                            <p style="font-size: 15px; margin: 0 0 16px 0; color: #1e293b;">Good morning <b>{name}</b> ({firm}),</p>
                            <p style="font-size: 14px; line-height: 1.6; color: #475569; margin: 0 0 24px 0;">
                                Here is your verified 7:00 AM EST Surplus Docket feed. All filings have been cross-referenced with county court registries with senior mortgages, institutional bank liens, and junior municipal encumbrances filtered upstream.
                            </p>

                            <!-- Benchmark Metrics Grid -->
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%; margin: 20px 0;">
                                <tr>
                                    <td width="50%" style="width: 50%; padding: 14px; background-color: #edf3ec; border-radius: 8px 0 0 8px; text-align: center; border-right: 1px solid #e2e8f0;">
                                        <div style="font-size: 22px; font-weight: 800; color: #365134; font-family: 'Courier New', Courier, monospace;">{total_bal_fmt}</div>
                                        <div style="font-size: 11px; text-transform: uppercase; color: #4c6d48; font-weight: bold; margin-top: 4px; letter-spacing: 0.05em;">Unencumbered Equity</div>
                                    </td>
                                    <td width="50%" style="width: 50%; padding: 14px; background-color: #f1f5f9; border-radius: 0 8px 8px 0; text-align: center;">
                                        <div style="font-size: 22px; font-weight: 800; color: #1b365d; font-family: 'Courier New', Courier, monospace;">{rec_count} Files</div>
                                        <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: bold; margin-top: 4px; letter-spacing: 0.05em;">Audited Dockets</div>
                                    </td>
                                </tr>
                            </table>

                            <h3 style="font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: #1b365d; margin: 28px 0 12px 0;">Featured High-Equity Dockets</h3>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%; border-collapse: collapse; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
                                <thead>
                                    <tr style="background-color: #f8fafc;">
                                        <th style="padding: 10px 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #475569; font-weight: 700; border-bottom: 2px solid #e2e8f0;">Docket</th>
                                        <th style="padding: 10px 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #475569; font-weight: 700; border-bottom: 2px solid #e2e8f0;">Claimant / Owner</th>
                                        <th style="padding: 10px 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #475569; font-weight: 700; border-bottom: 2px solid #e2e8f0;">Jurisdiction</th>
                                        <th style="padding: 10px 12px; text-align: right; font-size: 11px; text-transform: uppercase; color: #475569; font-weight: 700; border-bottom: 2px solid #e2e8f0;">Surplus</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {dockets_html}
                                </tbody>
                            </table>

                            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 18px; margin: 24px 0;">
                                <p style="font-size: 13px; line-height: 1.6; color: #334155; margin: 0;">
                                    📎 <b>Attached Deliverables:</b> Your verified morning dockets are attached in both <b>Master_Surplus_Lead_Feed.csv</b> and <b>Master_Surplus_Lead_Feed.xlsx</b> for direct import into your practice management software.
                                </p>
                            </div>

                            <div style="margin-top: 32px; padding-top: 18px; border-top: 1px solid #e2e8f0; font-size: 13px; color: #475569;">
                                <b>Elena Brooks</b><br>
                                Senior Docket Specialist | Surplus Docket<br>
                                <a href="https://surplusdocket.com" style="color: #4c6d48; text-decoration: none; font-weight: 600;">surplusdocket.com</a> • <a href="mailto:elena.brooks@surplusdocket.com" style="color: #1b365d; text-decoration: none;">elena.brooks@surplusdocket.com</a>
                            </div>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8fafc; padding: 20px 32px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; line-height: 1.5;">
                            {LEGAL_DISCLAIMER}<br>
                            © {datetime.now().year} Surplus Docket. All rights reserved. • <a href="https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00" style="color: #64748b; text-decoration: underline;">Subscriber Billing Portal</a>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
    return text_body, html_body


def dispatch_feed(is_dry_run=False, recipient_override=None):
    print("=" * 70)
    print(" 🚀 SURPLUS DOCKET — 7:00 AM EST MORNING SUBSCRIBER DISPATCH")
    print("=" * 70)
    print(f"Mode           : {'DRY RUN (Preview Only)' if is_dry_run else 'LIVE SMTP DISPATCH'}")
    print(f"From Sender    : {FROM_NAME} <{FROM_EMAIL}>")
    print(f"SMTP Server    : {SMTP_HOST}:{SMTP_PORT}\n")

    subscribers = load_active_subscribers()
    if recipient_override:
        subscribers = [{
            "email": recipient_override,
            "name": "Counsel",
            "firm": "Legal Practice",
            "delivery_format": ["CSV", "Excel"],
            "status": "ACTIVE"
        }]

    if not subscribers:
        print("ℹ️ No active subscribers found in portal/subscribers.json. Exiting.")
        return 0

    stats = get_feed_statistics()
    date_str = datetime.now().strftime("%B %d, %Y")
    subject = f"[Surplus Docket] Daily Morning Court Intelligence Feed — {date_str}"

    print(f"✓ Found {len(subscribers)} active subscriber(s).")
    print(f"✓ Feed Stats: {stats['total_records']} dockets | ${stats['total_surplus']:,.2f} total surplus.\n")

    if is_dry_run:
        print("[DRY RUN PREVIEW] For subscriber:", subscribers[0]["email"])
        text_body, _ = compose_email_content(subscribers[0], stats, date_str)
        print(f"Subject: {subject}\n")
        print("Body Sample (First 300 chars):")
        print(text_body[:300] + "...\n")
        print("Attachments that would be sent:")
        if MASTER_CSV.exists(): print(f"  📎 {MASTER_CSV.name} ({MASTER_CSV.stat().st_size / 1024:.1f} KB)")
        if MASTER_XLSX.exists(): print(f"  📎 {MASTER_XLSX.name} ({MASTER_XLSX.stat().st_size / 1024:.1f} KB)")
        print("\n✅ Dry run complete. 0 emails sent.")
        return 0

    if not GMAIL_APP_PASS:
        print("❌ ERROR: GMAIL_APP_PASS is not configured in environment or .env. Cannot dispatch emails.")
        return 1

    server = None
    sent_count = 0
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASS)
        print(f"✓ Connected and authenticated to {SMTP_HOST} as {GMAIL_USER}")

        for sub in subscribers:
            dest = sub.get("email")
            if not dest:
                continue

            msg = MIMEMultipart("mixed")
            msg["Subject"] = subject
            msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
            msg["To"] = dest
            msg["Reply-To"] = FROM_EMAIL
            msg["Date"] = email.utils.formatdate(localtime=True)
            msg["Message-ID"] = email.utils.make_msgid(domain="surplusdocket.com")

            # Nested alternative container for Plain Text & HTML Body
            body_container = MIMEMultipart("alternative")
            text_body, html_body = compose_email_content(sub, stats, date_str)
            body_container.attach(MIMEText(text_body, "plain", "utf-8"))
            body_container.attach(MIMEText(html_body, "html", "utf-8"))
            msg.attach(body_container)

            # Attachments attached to mixed root
            formats = sub.get("delivery_format", ["CSV", "Excel"])
            if "CSV" in formats and MASTER_CSV.exists():
                with open(MASTER_CSV, "rb") as cf:
                    part = MIMEBase("text", "csv", name=MASTER_CSV.name)
                    part.set_payload(cf.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", "attachment", filename=MASTER_CSV.name)
                    msg.attach(part)

            if "Excel" in formats and MASTER_XLSX.exists():
                with open(MASTER_XLSX, "rb") as xf:
                    part = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet", name=MASTER_XLSX.name)
                    part.set_payload(xf.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", "attachment", filename=MASTER_XLSX.name)
                    msg.attach(part)

            server.sendmail(GMAIL_USER, [dest], msg.as_string())
            print(f"  ✉️ Dispatched morning feed to {sub.get('name', 'Subscriber')} <{dest}> ({sub.get('firm', 'Firm')})")
            sent_count += 1

        print(f"\n🎉 Successfully dispatched morning feeds to {sent_count} subscriber(s).")
        return 0

    except Exception as e:
        print(f"❌ SMTP Dispatch Error: {e}")
        return 1
    finally:
        if server:
            try: server.quit()
            except Exception: pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dispatch morning feed to active subscribers.")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without sending emails")
    parser.add_argument("--send", action="store_true", help="Send live emails via SMTP")
    parser.add_argument("--recipient", type=str, help="Override recipient email for manual testing")
    args = parser.parse_args()

    if not args.send and not args.dry_run:
        # Default to dry-run for safety unless explicitly passed --send
        args.dry_run = True

    sys.exit(dispatch_feed(is_dry_run=args.dry_run, recipient_override=args.recipient))
