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
FROM_NAME = os.getenv("FROM_NAME", "Surplus Docket Intelligence")
FROM_EMAIL = os.getenv("FROM_EMAIL", "dockets@surplusdocket.com")
REPLY_TO = os.getenv("REPLY_TO", "dockets@surplusdocket.com")
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
            "docket": str(r.get("Case_or_TaxDeed_No") or r.get("Tax_Deed_Number") or r.get("TAX_DEED_NO") or "Pending"),
            "owner": str(r.get("Owner_Name") or r.get("DEFENDANT") or "Record Titleholder"),
            "amount": float(r.get(surplus_col, 0.0)),
            "state": str(r.get("State") or "FL"),
            "county": str(r.get("County") or r.get("COUNTY") or ""),
            "statute": str(r.get("Governing_Statute") or "")
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
        dockets_text += f"• Docket {d['docket']} ({d['county']}, {d['state']}) — ${d['amount']:,.2f} | Owner: {d['owner']}\n"
        dockets_html += f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%; margin-bottom: 10px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
            <tr>
                <td style="padding: 10px 14px; background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%;">
                        <tr>
                            <td align="left" style="font-family: 'Courier New', Courier, monospace; font-size: 13px; font-weight: 700; color: #1b365d;">
                                {d['docket']}
                                <span style="display: inline-block; background-color: #edf3ec; color: #365134; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; margin-left: 6px; font-family: -apple-system, sans-serif;">{d['county']}, {d['state']}</span>
                            </td>
                            <td align="right" style="font-family: 'Courier New', Courier, monospace; font-size: 14px; font-weight: 800; color: #4c6d48; white-space: nowrap;">
                                ${d['amount']:,.2f}
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
            <tr>
                <td style="padding: 10px 14px; font-size: 12px; color: #475569; background-color: #ffffff;">
                    <span style="color: #64748b; font-size: 11px; text-transform: uppercase; font-weight: 600;">Titleholder:</span> <strong style="color: #0f172a;">{d['owner']}</strong>
                    {f'<br><span style="color: #94a3b8; font-size: 10px; font-family: monospace;">Statute: {d["statute"]}</span>' if d.get("statute") else ''}
                </td>
            </tr>
        </table>
        """

    text_body = f"""Good morning {name},

Here is your daily Surplus Docket court intelligence briefing for {date_str}.

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

Surplus Docket Intelligence
Court Registry Ingestion Desk | Surplus Docket
surplusdocket.com • dockets@surplusdocket.com

---
{LEGAL_DISCLAIMER}
"""

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Surplus Docket Intelligence Dispatch</title>
    <style type="text/css">
        @media only screen and (max-width: 600px) {{
            .email-wrapper {{ width: 100% !important; padding: 6px !important; }}
            .email-container {{ width: 100% !important; max-width: 100% !important; }}
            .content-cell {{ padding: 18px 14px !important; }}
            .header-cell {{ padding: 18px 14px !important; }}
            .dispatch-tag {{ display: none !important; }}
            .metric-cell {{ display: block !important; width: 100% !important; border-right: none !important; border-bottom: 1px solid #e2e8f0 !important; border-radius: 6px !important; margin-bottom: 8px !important; }}
        }}
    </style>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8f8f4; margin: 0; padding: 16px 8px; color: #1e293b; line-height: 1.5; -webkit-text-size-adjust: 100%;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-wrapper" style="background-color: #f8f8f4; width: 100%;">
        <tr>
            <td align="center" style="padding: 0;">
                <!-- Main Card Container: Fixed at 580px max for mobile-safe rendering -->
                <table role="presentation" width="580" cellpadding="0" cellspacing="0" border="0" class="email-container" style="max-width: 580px; width: 100%; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                    <!-- Header with Official Logo -->
                    <tr>
                        <td class="header-cell" style="background-color: #1b365d; padding: 22px 28px; border-bottom: 3px solid #4c6d48;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%;">
                                <tr>
                                    <td align="left" valign="middle" style="padding: 0;">
                                        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td valign="middle" style="padding-right: 12px;">
                                                    <img src="https://surplusdocket.com/assets/logo_surplus_docket.png" alt="Surplus Docket Logo" width="38" height="30" style="display: block; width: 38px; height: auto; max-height: 32px; border: 0;" />
                                                </td>
                                                <td valign="middle" style="line-height: 1.1;">
                                                    <div style="font-family: Georgia, 'Times New Roman', serif; font-weight: 900; font-size: 20px; letter-spacing: -0.01em; margin: 0;">
                                                        <span style="color: #4c6d48;">SURPLUS</span> <span style="color: #ffffff;">DOCKET</span>
                                                    </div>
                                                    <div style="font-family: 'Courier New', Courier, monospace; font-size: 9px; text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8; margin-top: 4px;">
                                                        Court Intelligence &amp; Public Records Desk
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td align="right" valign="middle" class="dispatch-tag" style="padding: 0;">
                                        <span style="display: inline-block; background-color: #102238; color: #94a3b8; font-family: 'Courier New', Courier, monospace; font-size: 10px; font-weight: 600; padding: 5px 9px; border-radius: 6px; border: 1px solid #233a5e; letter-spacing: 0.04em;">
                                            7:00 AM EST
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Main Content Body -->
                    <tr>
                        <td class="content-cell" style="padding: 28px; background-color: #ffffff;">
                            <p style="font-size: 15px; margin: 0 0 14px 0; color: #1e293b;">Good morning <b>{name}</b> ({firm}),</p>
                            <p style="font-size: 13px; line-height: 1.6; color: #475569; margin: 0 0 20px 0;">
                                Here is your verified daily Surplus Docket intelligence feed for <b>{date_str}</b>. All filings have been cross-referenced with county court registries with senior mortgages, institutional bank liens, and junior municipal encumbrances filtered upstream.
                            </p>

                            <!-- Benchmark Metrics Grid (Mobile fluid) -->
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%; margin: 18px 0;">
                                <tr>
                                    <td class="metric-cell" width="50%" style="width: 50%; padding: 14px 10px; background-color: #edf3ec; border-radius: 8px 0 0 8px; text-align: center; border-right: 1px solid #e2e8f0;">
                                        <div style="font-size: 21px; font-weight: 800; color: #365134; font-family: 'Courier New', Courier, monospace;">{total_bal_fmt}</div>
                                        <div style="font-size: 10px; text-transform: uppercase; color: #4c6d48; font-weight: 700; margin-top: 4px; letter-spacing: 0.05em;">Unencumbered Equity</div>
                                    </td>
                                    <td class="metric-cell" width="50%" style="width: 50%; padding: 14px 10px; background-color: #f1f5f9; border-radius: 0 8px 8px 0; text-align: center;">
                                        <div style="font-size: 21px; font-weight: 800; color: #1b365d; font-family: 'Courier New', Courier, monospace;">{rec_count} Files</div>
                                        <div style="font-size: 10px; text-transform: uppercase; color: #64748b; font-weight: 700; margin-top: 4px; letter-spacing: 0.05em;">Audited Dockets</div>
                                    </td>
                                </tr>
                            </table>

                            <h3 style="font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: #1b365d; margin: 24px 0 10px 0; font-weight: 800;">
                                Featured High-Equity Dockets
                            </h3>
                            
                            <!-- Mobile Fluid Docket Cards -->
                            {dockets_html}

                            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; margin: 20px 0;">
                                <p style="font-size: 12px; line-height: 1.6; color: #334155; margin: 0;">
                                    📎 <b>Attached Deliverables:</b> Your complete morning dockets are attached in both <b>Master_Surplus_Lead_Feed.csv</b> and <b>Master_Surplus_Lead_Feed.xlsx</b> for direct importation into your practice management software.
                                </p>
                            </div>

                            <div style="margin-top: 28px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #475569;">
                                <strong style="color: #1b365d; font-size: 13px;">Surplus Docket Intelligence</strong><br>
                                <span style="font-size: 12px; color: #64748b;">Court Registry Ingestion &amp; Verification Desk</span><br>
                                <a href="https://surplusdocket.com" style="color: #4c6d48; text-decoration: none; font-weight: 600;">surplusdocket.com</a> • <a href="mailto:dockets@surplusdocket.com" style="color: #1b365d; text-decoration: none;">dockets@surplusdocket.com</a>
                            </div>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8fafc; padding: 18px 24px; border-top: 1px solid #e2e8f0; font-size: 10px; color: #94a3b8; text-align: center; line-height: 1.5;">
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
        print(f"❌ Error during morning feed dispatch: {e}")
        return 1
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass


def compose_activation_email(subscriber, stats, date_str):
    name = subscriber.get("name", "Counsel")
    firm = subscriber.get("firm", "Practice")
    total_bal_fmt = f"${stats['total_surplus']:,.2f}"
    rec_count = stats["total_records"]

    text_body = f"""Welcome {name},

Your 7-day institutional practice evaluation with Surplus Docket is officially activated for {date_str}.

We have initialized your subscription seat under $0 due today. For the next 7 days, your firm will receive daily 7:00 AM EST public record intelligence feeds indexing verified tax deed surplus and excess proceeds filings across Florida, Texas, Georgia, North Carolina, Tennessee, and California.

STARTER DATA DELIVERABLES (ATTACHED):
We have attached today's active court intelligence files to this transmission so you can begin immediate case triage:
• Master_Surplus_Lead_Feed.csv ({rec_count} files, {total_bal_fmt} gross unencumbered equity)
• Master_Surplus_Lead_Feed.xlsx (Structured workbook with claim urgency tiers and statutory calculation formulas)

WHAT TO EXPECT NEXT:
1. Daily Dockets: Fresh verified dockets will arrive every business morning at 7:00 AM EST at this email address.
2. Practitioner Toolkit: Access statutory petition dossiers for FL § 197.582, TX § 34.04, GA § 48-4-5, and CA § 4675 anytime at https://surplusdocket.com/practitioner-toolkit.html.
3. Transparent Evaluation Terms: Day 8 rollover to the standard monthly plan ($249/mo). If you ever need to adjust seats, pause, or cancel, you have 1-click self-service access via your Stripe Subscriber Portal: https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00.

If you require custom circuit filters or have specific county requirements, simply reply directly to this transmission.

Best regards,

Surplus Docket Intelligence
Court Registry Ingestion Desk | Surplus Docket
surplusdocket.com • dockets@surplusdocket.com

---
{LEGAL_DISCLAIMER}
"""

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Practice Evaluation Activated — Surplus Docket</title>
    <style type="text/css">
        @media only screen and (max-width: 600px) {{
            .email-wrapper {{ width: 100% !important; padding: 6px !important; }}
            .email-container {{ width: 100% !important; max-width: 100% !important; }}
            .content-cell {{ padding: 18px 14px !important; }}
            .header-cell {{ padding: 18px 14px !important; }}
        }}
    </style>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8f8f4; margin: 0; padding: 16px 8px; color: #1e293b; line-height: 1.5; -webkit-text-size-adjust: 100%;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-wrapper" style="background-color: #f8f8f4; width: 100%;">
        <tr>
            <td align="center" style="padding: 0;">
                <table role="presentation" width="580" cellpadding="0" cellspacing="0" border="0" class="email-container" style="max-width: 580px; width: 100%; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                    <!-- Header -->
                    <tr>
                        <td class="header-cell" style="background-color: #1b365d; padding: 22px 28px; border-bottom: 3px solid #4c6d48;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%;">
                                <tr>
                                    <td align="left" valign="middle">
                                        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td valign="middle" style="padding-right: 12px;">
                                                    <img src="https://surplusdocket.com/assets/logo_surplus_docket.png" alt="Surplus Docket Logo" width="38" height="30" style="display: block; width: 38px; height: auto; max-height: 32px; border: 0;" />
                                                </td>
                                                <td valign="middle" style="line-height: 1.1;">
                                                    <div style="font-family: Georgia, 'Times New Roman', serif; font-weight: 900; font-size: 20px; letter-spacing: -0.01em; margin: 0;">
                                                        <span style="color: #4c6d48;">SURPLUS</span> <span style="color: #ffffff;">DOCKET</span>
                                                    </div>
                                                    <div style="font-family: 'Courier New', Courier, monospace; font-size: 9px; text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8; margin-top: 4px;">
                                                        Practice Evaluation Activation
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td align="right" valign="middle">
                                        <span style="display: inline-block; background-color: #365134; color: #ffffff; font-family: 'Courier New', Courier, monospace; font-size: 10px; font-weight: 700; padding: 5px 9px; border-radius: 6px; letter-spacing: 0.04em;">
                                            $0 DUE TODAY
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Body -->
                    <tr>
                        <td class="content-cell" style="padding: 28px; background-color: #ffffff;">
                            <p style="font-size: 15px; margin: 0 0 14px 0; color: #1e293b;">Welcome <b>{name}</b> ({firm}),</p>
                            <p style="font-size: 13px; line-height: 1.6; color: #475569; margin: 0 0 18px 0;">
                                Your 7-day institutional practice evaluation is officially activated. For the next 7 days, your practice has access to verified court registry intelligence across 6 core states with senior mortgages, institutional bank liens, and junior municipal encumbrances filtered upstream.
                            </p>

                            <!-- Starter Deliverables Card -->
                            <div style="background-color: #edf3ec; border: 1px solid #c2d9c0; border-radius: 8px; padding: 16px; margin: 20px 0;">
                                <div style="font-size: 13px; font-weight: 700; color: #365134; margin-bottom: 6px;">
                                    📎 Attached Immediate Starter Dockets:
                                </div>
                                <p style="font-size: 12px; line-height: 1.5; color: #2e442c; margin: 0;">
                                    Attached to this activation transmission are today's complete audited files: <b>Master_Surplus_Lead_Feed.csv</b> and <b>Master_Surplus_Lead_Feed.xlsx</b> ({rec_count} verified files, {total_bal_fmt} gross equity).
                                </p>
                            </div>

                            <!-- Next Steps Box -->
                            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 20px 0;">
                                <div style="font-size: 12px; font-weight: 700; color: #1b365d; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">
                                    What to Expect:
                                </div>
                                <ul style="margin: 0; padding-left: 18px; font-size: 12px; color: #475569; line-height: 1.6;">
                                    <li><b>Daily 7:00 AM EST Feeds:</b> Delivered directly to your inbox every business morning.</li>
                                    <li><b>Statutory Petitions:</b> Download 1-click filing dossiers in the <a href="https://surplusdocket.com/practitioner-toolkit.html" style="color: #4c6d48; font-weight: 600;">Practitioner Toolkit</a>.</li>
                                    <li><b>Self-Serve Account Control:</b> Manage seats or cancel anytime at $0 billed via the <a href="https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00" style="color: #1b365d; font-weight: 600;">Subscriber Portal</a>.</li>
                                </ul>
                            </div>

                            <p style="font-size: 12px; line-height: 1.6; color: #64748b; margin: 18px 0 0 0;">
                                If you need assistance configuring circuit filters or integrating our feeds into your case management software, simply reply directly to this email.
                            </p>

                            <div style="margin-top: 28px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #475569;">
                                <strong style="color: #1b365d; font-size: 13px;">Surplus Docket Intelligence</strong><br>
                                <span style="font-size: 12px; color: #64748b;">Court Registry Ingestion &amp; Verification Desk</span><br>
                                <a href="https://surplusdocket.com" style="color: #4c6d48; text-decoration: none; font-weight: 600;">surplusdocket.com</a> • <a href="mailto:dockets@surplusdocket.com" style="color: #1b365d; text-decoration: none;">dockets@surplusdocket.com</a>
                            </div>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8fafc; padding: 18px 24px; border-top: 1px solid #e2e8f0; font-size: 10px; color: #94a3b8; text-align: center; line-height: 1.5;">
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


def dispatch_activation_starter_kit(subscriber, is_dry_run=False):
    dest = subscriber.get("email")
    if not dest:
        print("⚠️ No email provided for activation starter kit.")
        return False

    stats = get_feed_statistics()
    date_str = datetime.now().strftime("%B %d, %Y")
    subject = f"[Surplus Docket] Practice Evaluation Activated — Starter Dockets & Circuit Feeds"

    text_body, html_body = compose_activation_email(subscriber, stats, date_str)

    if is_dry_run:
        print(f"[DRY RUN] Activation Starter Kit would be sent to: {dest}")
        return True

    if not GMAIL_APP_PASS:
        print("⚠️ GMAIL_APP_PASS not set. Skipping activation starter kit.")
        return False

    server = None
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASS)

        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg["To"] = dest
        msg["Reply-To"] = REPLY_TO
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = email.utils.make_msgid(domain="surplusdocket.com")

        body_container = MIMEMultipart("alternative")
        body_container.attach(MIMEText(text_body, "plain", "utf-8"))
        body_container.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(body_container)

        if MASTER_CSV.exists():
            with open(MASTER_CSV, "rb") as cf:
                p_csv = MIMEBase("text", "csv", name=MASTER_CSV.name)
                p_csv.set_payload(cf.read())
                encoders.encode_base64(p_csv)
                p_csv.add_header("Content-Disposition", "attachment", filename=MASTER_CSV.name)
                msg.attach(p_csv)

        if MASTER_XLSX.exists():
            with open(MASTER_XLSX, "rb") as xf:
                p_xlsx = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet", name=MASTER_XLSX.name)
                p_xlsx.set_payload(xf.read())
                encoders.encode_base64(p_xlsx)
                p_xlsx.add_header("Content-Disposition", "attachment", filename=MASTER_XLSX.name)
                msg.attach(p_xlsx)

        server.sendmail(GMAIL_USER, [dest], msg.as_string())
        print(f"  ✉️ Dispatched immediate Day 0 Activation Starter Kit to: {dest}")
        return True
    except Exception as e:
        print(f"❌ Error dispatching activation starter kit: {e}")
        return False
    finally:
        if server:
            try: server.quit()
            except Exception: pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dispatch morning feed to active subscribers.")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without sending emails")
    parser.add_argument("--send", action="store_true", help="Send live emails via SMTP")
    parser.add_argument("--recipient", type=str, help="Override recipient email for manual testing")
    parser.add_argument("--welcome", action="store_true", help="Send immediate Day 0 welcome starter kit")
    args = parser.parse_args()

    if args.welcome:
        target = {"email": args.recipient or "david@surplusdocket.com", "name": "Counsel", "firm": "Legal Practice"}
        sys.exit(0 if dispatch_activation_starter_kit(target, is_dry_run=args.dry_run) else 1)

    if not args.send and not args.dry_run:
        args.dry_run = True

    sys.exit(dispatch_feed(is_dry_run=args.dry_run, recipient_override=args.recipient))

