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
import csv
try:
    import pandas as pd
except ImportError:
    pd = None
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
    if pd is not None:
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
                "statute": str(r.get("Governing_Statute") or ""),
                "clerk_url": str(r.get("Clerk_Verification_URL") or "https://surplusdocket.com/practitioner-toolkit.html"),
                "urgency": str(r.get("Claim_Urgency_Tier") or r.get("Opportunity_Tier") or ""),
            })

        return {
            "total_records": total_records,
            "total_surplus": total_surplus,
            "top_dockets": top_dockets,
            "jurisdiction_counts": jurisdiction_counts
        }

    # Built-in csv fallback when pandas is not installed
    total_records = 0
    total_surplus = 0.0
    jurisdiction_counts = {}
    top_dockets = []
    with open(MASTER_CSV, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for r in reader:
            total_records += 1
            val_str = r.get("Surplus_Balance_USD") or r.get("AMOUNT") or 0.0
            try:
                amt = float(val_str)
            except (ValueError, TypeError):
                amt = 0.0
            total_surplus += amt
            st = str(r.get("State") or r.get("COUNTY") or "").strip().upper()
            if st:
                jurisdiction_counts[st] = jurisdiction_counts.get(st, 0) + 1
            if len(top_dockets) < 4:
                top_dockets.append({
                    "docket": str(r.get("Case_or_TaxDeed_No") or r.get("Tax_Deed_Number") or r.get("TAX_DEED_NO") or "Pending"),
                    "owner": str(r.get("Owner_Name") or r.get("DEFENDANT") or "Record Titleholder"),
                    "amount": amt,
                    "state": str(r.get("State") or "FL"),
                    "county": str(r.get("County") or r.get("COUNTY") or ""),
                    "statute": str(r.get("Governing_Statute") or ""),
                    "clerk_url": str(r.get("Clerk_Verification_URL") or "https://surplusdocket.com/practitioner-toolkit.html"),
                    "urgency": str(r.get("Claim_Urgency_Tier") or r.get("Opportunity_Tier") or ""),
                })

    return {
        "total_records": total_records,
        "total_surplus": total_surplus,
        "top_dockets": top_dockets,
        "jurisdiction_counts": jurisdiction_counts
    }


def format_firm_suffix(subscriber):
    raw_firm = (subscriber.get("firm") or "").strip()
    if raw_firm and raw_firm not in ("Surplus Docket Compliance & Research Desk", "Practice", "Legal Practice", "Firm"):
        return f" ({raw_firm})"
    return ""


def compose_email_content(subscriber, stats, date_str):
    name = subscriber.get("name", "Counsel")
    firm_suffix = format_firm_suffix(subscriber)
    total_bal_fmt = f"${stats['total_surplus']:,.2f}"
    rec_count = stats["total_records"]
    year = datetime.now().year

    dockets_text = ""
    dockets_html = ""
    for d in stats["top_dockets"]:
        urgency_label = f" [{d['urgency']}]" if d.get("urgency") else ""
        statute_label = f"\n    Statute: {d['statute']}" if d.get("statute") else ""
        clerk_label = f"\n    Registry Verification: {d['clerk_url']}" if d.get("clerk_url") else ""
        dockets_text += (
            f"• Docket {d['docket']} ({d['county']}, {d['state']}){urgency_label} — ${d['amount']:,.2f}\n"
            f"    Owner: {d['owner']}{statute_label}{clerk_label}\n\n"
        )

        urgency_val = d.get("urgency", "")
        if "Tier 1" in urgency_val:
            urgency_badge = '<span style="display: inline-block; background-color: #fef2f2; color: #991b1b; border: 1px solid #fecaca; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 9999px; font-family: -apple-system, sans-serif; letter-spacing: 0.02em;">Tier 1: High Urgency (&lt; 45d)</span>'
        elif "Tier 2" in urgency_val:
            urgency_badge = '<span style="display: inline-block; background-color: #fffbeb; color: #92400e; border: 1px solid #fde68a; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 9999px; font-family: -apple-system, sans-serif; letter-spacing: 0.02em;">Tier 2: Priority Window</span>'
        elif "Tier 3" in urgency_val:
            urgency_badge = '<span style="display: inline-block; background-color: #edf3ec; color: #365134; border: 1px solid #c2d9c0; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 9999px; font-family: -apple-system, sans-serif; letter-spacing: 0.02em;">Tier 3: Active Window</span>'
        else:
            urgency_badge = '<span style="display: inline-block; background-color: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 9999px; font-family: -apple-system, sans-serif; letter-spacing: 0.02em;">Verified Docket</span>'

        statute_markup = f'''<div style="margin-top: 4px;">
            <span style="color: #64748b; font-size: 10px; text-transform: uppercase; font-weight: 700;">Statute: </span>
            <span style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 11px; font-weight: 600; color: #1b365d; background-color: #f1f5f9; border: 1px solid #e2e8f0; padding: 2px 6px; border-radius: 4px;">{d["statute"]}</span>
        </div>''' if d.get("statute") else ''

        dockets_html += f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="docket-card" style="width: 100%; margin-bottom: 12px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(12,24,39,0.04);">
            <tr>
                <td class="docket-header-td" style="padding: 11px 16px; background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%;">
                        <tr class="docket-header-row">
                            <td align="left" valign="middle" class="docket-col-left" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                                <span style="display: inline-block; background-color: #edf3ec; color: #365134; font-size: 11px; font-weight: 800; padding: 2px 7px; border-radius: 4px; border: 1px solid #c2d9c0; margin-right: 6px;">{d['state']}</span>
                                <a href="{d['clerk_url']}" target="_blank" style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 14px; font-weight: 700; color: #1b365d; text-decoration: none; border-bottom: 1px dotted #1b365d;">{d['docket']}</a>
                                <span style="color: #64748b; font-size: 12px; font-weight: 500; margin-left: 6px;">• {d['county']} County</span>
                            </td>
                            <td align="right" valign="middle" class="docket-col-right" style="text-align: right;">
                                <span style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 16px; font-weight: 900; color: #365134;">${d['amount']:,.2f}</span>
                                <span style="font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: #94a3b8; font-family: -apple-system, sans-serif; margin-left: 3px;">Unencumbered</span>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
            <tr>
                <td class="docket-body-td" style="padding: 12px 16px; font-size: 12px; color: #475569; background-color: #ffffff;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%;">
                        <tr class="docket-body-row">
                            <td align="left" valign="middle" class="docket-body-left" style="line-height: 1.45; font-family: -apple-system, sans-serif;">
                                <span style="color: #64748b; font-size: 10px; text-transform: uppercase; font-weight: 700; letter-spacing: 0.03em;">Record Titleholder:</span> <strong style="color: #0f172a; font-size: 13px;">{d['owner']}</strong>
                                {statute_markup}
                            </td>
                            <td align="right" valign="middle" class="docket-body-right" style="text-align: right;">
                                <div style="margin-bottom: 5px;">{urgency_badge}</div>
                                <div>
                                    <a href="{d['clerk_url']}" target="_blank" class="docket-cta-btn" style="display: inline-block; font-size: 11px; font-weight: 700; color: #1b365d; text-decoration: none; background-color: #f8fafc; border: 1px solid #cbd5e1; padding: 5px 11px; border-radius: 5px;">
                                        Review Official Registry &rarr;
                                    </a>
                                </div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
        """

    text_body = f"""BENCHMARK SUMMARY ({date_str}):
• Active Verified Records: {rec_count} files
• Gross Unencumbered Surplus: {total_bal_fmt}
• Upstream Bank Lien Filtering: 100% Verified (Zero Bank Liens)
• Monitored Jurisdictions: Florida, Texas, Georgia, North Carolina, Tennessee, California

FEATURED HIGH-EQUITY DOCKETS:
{dockets_text}
Complete unencumbered docket feeds are attached to this transmission in CSV and Excel (.xlsx) formats for immediate importation into your practice management software.

RESOURCES & ACCOUNT:
• Practitioner Toolkit & Forms: https://surplusdocket.com/practitioner-toolkit.html
• Subscriber Billing & Seat Management: https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00
• REST API Documentation: https://surplusdocket.com/api-documentation.html

---
Surplus Docket Intelligence • Court Registry Ingestion Desk
surplusdocket.com • dockets@surplusdocket.com

{LEGAL_DISCLAIMER}
"""

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Surplus Docket Intelligence Dispatch</title>
    <style type="text/css">
        body, table, td, p, a, li, blockquote {{
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
        }}
        table, td {{
            mso-table-lspace: 0pt;
            mso-table-rspace: 0pt;
        }}
        img {{
            -ms-interpolation-mode: bicubic;
            border: 0;
            height: auto;
            line-height: 100%;
            outline: none;
            text-decoration: none;
        }}
        body {{
            margin: 0 !important;
            padding: 0 !important;
            background-color: #ffffff !important;
        }}
        .email-wrapper {{
            width: 100% !important;
            background-color: #ffffff !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        .email-outer-td {{
            padding: 0 !important;
            margin: 0 !important;
        }}
        .email-container {{
            width: 100% !important;
            max-width: 680px !important;
            border-radius: 0 !important;
            border: none !important;
            box-shadow: none !important;
            margin: 0 auto !important;
            background-color: #ffffff !important;
        }}
        @media only screen and (max-width: 640px) {{
            .content-cell {{
                padding: 16px 14px !important;
            }}
            .header-cell {{
                padding: 14px 14px !important;
            }}
            .nav-cell {{
                padding: 8px 14px !important;
            }}
            .nav-date {{
                display: none !important;
            }}
            .footer-cell {{
                padding: 20px 14px !important;
            }}
            .header-tag-cell {{
                display: none !important;
            }}
            .header-mobile-tag {{
                display: inline-block !important;
            }}
            .docket-col-left {{
                display: block !important;
                width: 100% !important;
                text-align: left !important;
            }}
            .docket-col-right {{
                display: block !important;
                width: 100% !important;
                text-align: left !important;
                margin-top: 6px !important;
                padding-top: 6px !important;
                border-top: 1px dashed #e2e8f0 !important;
            }}
            .docket-body-left {{
                display: block !important;
                width: 100% !important;
                text-align: left !important;
            }}
            .docket-body-right {{
                display: block !important;
                width: 100% !important;
                text-align: left !important;
                margin-top: 10px !important;
                padding-top: 8px !important;
                border-top: 1px dashed #e2e8f0 !important;
            }}
            .docket-body-right div {{
                text-align: left !important;
            }}
            .docket-cta-btn {{
                display: block !important;
                width: 100% !important;
                text-align: center !important;
                padding: 9px 0 !important;
                box-sizing: border-box !important;
            }}
            .metric-cell {{
                padding: 10px 8px !important;
            }}
            .metric-val {{
                font-size: 16px !important;
            }}
            .metric-label {{
                font-size: 9px !important;
            }}
            .deliverables-table td {{
                display: block !important;
                width: 100% !important;
                box-sizing: border-box !important;
                margin-bottom: 8px !important;
            }}
            .deliverables-spacer {{
                display: none !important;
            }}
            .btn-cta {{
                display: block !important;
                width: 100% !important;
                box-sizing: border-box !important;
                margin: 8px 0 !important;
                text-align: center !important;
                padding: 13px 16px !important;
            }}
            .btn-cta-secondary {{
                margin-left: 0 !important;
            }}
        }}
    </style>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #ffffff; margin: 0; padding: 0; color: #1e293b; line-height: 1.5; -webkit-text-size-adjust: 100%;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-wrapper" style="background-color: #ffffff; width: 100%; margin: 0; padding: 0;">
        <tr>
            <td align="center" class="email-outer-td" style="padding: 0; margin: 0;">
                <!-- Main Container: Clean, Edge-to-Edge without outer shell framing -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-container" style="max-width: 680px; width: 100%; background-color: #ffffff; border: none; border-radius: 0; box-shadow: none; margin: 0 auto;">
                    
                    <!-- Top Brand Header: High-contrast white backdrop matching website -->
                    <tr>
                        <td class="header-cell" style="background-color: #ffffff; padding: 18px 24px; border-bottom: 2px solid #1b365d;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%;">
                                <tr>
                                    <td align="left" valign="middle" style="padding: 0;">
                                        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td valign="middle" style="padding-right: 14px;">
                                                    <a href="https://surplusdocket.com" target="_blank" style="text-decoration: none; display: block;">
                                                        <!-- White container tile ensures high contrast in all clients and dark mode -->
                                                        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 4px 6px; display: inline-block; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                                                            <img src="https://surplusdocket.com/assets/logo_surplus_docket.png" alt="Surplus Docket Crest" width="46" height="36" style="display: block; width: 46px; height: auto; max-height: 38px; border: 0;" />
                                                        </div>
                                                    </a>
                                                </td>
                                                <td valign="middle" style="line-height: 1.15;">
                                                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-weight: 900; font-size: 21px; letter-spacing: -0.02em; margin: 0;">
                                                        <a href="https://surplusdocket.com" target="_blank" style="text-decoration: none;">
                                                            <span style="color: #4c6d48; font-weight: 800;">SURPLUS</span> <span style="color: #1b365d; font-weight: 900;">DOCKET</span>
                                                        </a>
                                                    </div>
                                                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 10px; font-weight: 700; color: #64748b; letter-spacing: 0.06em; text-transform: uppercase; margin-top: 3px;">
                                                        Court Registry Intelligence
                                                    </div>
                                                    <div class="header-mobile-tag" style="display: none; margin-top: 5px;">
                                                        <span style="display: inline-block; background-color: #edf3ec; border: 1px solid #c2d9c0; color: #365134; font-family: -apple-system, sans-serif; font-size: 9px; font-weight: 700; padding: 2px 8px; border-radius: 9999px;">
                                                            7:00 AM EST • DAILY BRIEFING
                                                        </span>
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td align="right" valign="middle" class="header-tag-cell" style="padding: 0;">
                                        <span style="display: inline-block; background-color: #edf3ec; border: 1px solid #c2d9c0; color: #365134; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11px; font-weight: 700; padding: 6px 14px; border-radius: 9999px; letter-spacing: 0.02em; white-space: nowrap;">
                                            7:00 AM EST • DAILY BRIEFING
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Secondary Quick Navigation Bar -->
                    <tr>
                        <td class="nav-cell" style="background-color: #f8fafc; padding: 8px 24px; border-bottom: 1px solid #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td align="left" style="color: #64748b; white-space: nowrap;">
                                        <a href="https://surplusdocket.com/practitioner-toolkit.html" target="_blank" class="nav-link" style="color: #1b365d; text-decoration: none; font-weight: 700;">Practitioner Toolkit</a>
                                        <span style="color: #cbd5e1; margin: 0 6px;">•</span>
                                        <a href="https://surplusdocket.com/api-documentation.html" target="_blank" class="nav-link" style="color: #526174; text-decoration: none;">API Docs</a>
                                        <span style="color: #cbd5e1; margin: 0 6px;">•</span>
                                        <a href="https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00" target="_blank" class="nav-link" style="color: #526174; text-decoration: none;">Billing Portal</a>
                                    </td>
                                    <td align="right" class="nav-date" style="color: #94a3b8; font-size: 11px; font-weight: 500; white-space: nowrap;">
                                        {date_str}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Main Content Body -->
                    <tr>
                        <td class="content-cell" style="padding: 20px 24px; background-color: #ffffff;">
                            <!-- Benchmark Metrics: 2x2 Grid (Flawless Flow on Both Mobile & Desktop) -->
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%; margin: 0 0 22px 0;">
                                <tr>
                                    <td width="49%" class="metric-cell" style="padding: 12px 10px; background-color: #edf3ec; border: 1px solid #c2d9c0; border-radius: 8px; text-align: center;">
                                        <div class="metric-val" style="font-size: 18px; font-weight: 900; color: #365134; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;">{total_bal_fmt}</div>
                                        <div class="metric-label" style="font-size: 10px; text-transform: uppercase; color: #4c6d48; font-weight: 700; margin-top: 3px; letter-spacing: 0.04em;">Audited Surplus Pool</div>
                                    </td>
                                    <td width="2%" style="width: 8px;"></td>
                                    <td width="49%" class="metric-cell" style="padding: 12px 10px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; text-align: center;">
                                        <div class="metric-val" style="font-size: 18px; font-weight: 900; color: #1b365d; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;">{rec_count} Files</div>
                                        <div class="metric-label" style="font-size: 10px; text-transform: uppercase; color: #64748b; font-weight: 700; margin-top: 3px; letter-spacing: 0.04em;">Verified Dockets</div>
                                    </td>
                                </tr>
                                <tr><td colspan="3" style="height: 8px; font-size: 0; line-height: 0;">&nbsp;</td></tr>
                                <tr>
                                    <td width="49%" class="metric-cell" style="padding: 12px 10px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; text-align: center;">
                                        <div class="metric-val" style="font-size: 17px; font-weight: 900; color: #1b365d; font-family: -apple-system, sans-serif;">6 Core States</div>
                                        <div class="metric-label" style="font-size: 10px; text-transform: uppercase; color: #64748b; font-weight: 700; margin-top: 3px; letter-spacing: 0.04em;">FL • TX • GA • NC • TN • CA</div>
                                    </td>
                                    <td width="2%" style="width: 8px;"></td>
                                    <td width="49%" class="metric-cell" style="padding: 12px 10px; background-color: #edf3ec; border: 1px solid #c2d9c0; border-radius: 8px; text-align: center;">
                                        <div class="metric-val" style="font-size: 17px; font-weight: 900; color: #365134; font-family: -apple-system, sans-serif;">Zero Liens</div>
                                        <div class="metric-label" style="font-size: 10px; text-transform: uppercase; color: #4c6d48; font-weight: 700; margin-top: 3px; letter-spacing: 0.04em;">Bank Liens Filtered</div>
                                    </td>
                                </tr>
                            </table>

                            <!-- Section Title -->
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 24px 0 12px 0;">
                                <tr>
                                    <td align="left" valign="middle">
                                        <div style="font-size: 12px; font-weight: 800; color: #1b365d; text-transform: uppercase; letter-spacing: 0.06em;">
                                            Featured High-Equity Dockets
                                        </div>
                                    </td>
                                    <td align="right" valign="middle">
                                        <span style="font-size: 11px; font-weight: 600; color: #64748b;">
                                            Full feed attached below
                                        </span>
                                    </td>
                                </tr>
                            </table>

                            <!-- Responsive Docket Cards (No Scrunching on Mobile) -->
                            {dockets_html}

                            <!-- Attached Deliverables Card -->
                            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 18px; margin: 22px 0 20px 0;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td style="padding-bottom: 10px;">
                                            <div style="font-size: 12px; font-weight: 800; color: #1b365d; text-transform: uppercase; letter-spacing: 0.05em;">
                                                📎 Attached Daily Court Intelligence Files
                                            </div>
                                            <div style="font-size: 12px; color: #64748b; margin-top: 4px;">
                                                Attached to this transmission are today's complete audited datasets for immediate import:
                                            </div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>
                                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="deliverables-table">
                                                <tr>
                                                    <td width="49%" style="background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 10px 14px;">
                                                        <div style="font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12px; font-weight: 700; color: #1b365d;">📄 Master_Surplus_Lead_Feed.csv</div>
                                                        <div style="font-size: 11px; color: #64748b; margin-top: 2px;">{rec_count} files • Clio, Filevine, &amp; CRM intake</div>
                                                    </td>
                                                    <td width="2%" class="deliverables-spacer" style="width: 8px;"></td>
                                                    <td width="49%" style="background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 10px 14px;">
                                                        <div style="font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12px; font-weight: 700; color: #1b365d;">📊 Master_Surplus_Lead_Feed.xlsx</div>
                                                        <div style="font-size: 11px; color: #64748b; margin-top: 2px;">Formatted workbook with urgency tiers &amp; formulas</div>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding-top: 10px; font-size: 11px; color: #64748b;">
                                            Need programmatic integration? <a href="https://surplusdocket.com/api-documentation.html" target="_blank" style="color: #1b365d; font-weight: 700; text-decoration: underline;">REST API Documentation &rarr;</a>
                                        </td>
                                    </tr>
                                </table>
                            </div>

                            <!-- Action Buttons -->
                            <div style="text-align: center; margin: 26px 0 20px 0;">
                                <a href="https://surplusdocket.com/practitioner-toolkit.html" target="_blank" class="btn-cta" style="display: inline-block; background-color: #1b365d; color: #ffffff; text-decoration: none; font-weight: 700; font-size: 13px; padding: 12px 24px; border-radius: 6px; letter-spacing: 0.02em; box-shadow: 0 2px 6px rgba(27,54,93,0.18);">
                                    Access Practitioner Toolkit &rarr;
                                </a>
                                <a href="https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00" target="_blank" class="btn-cta btn-cta-secondary" style="display: inline-block; background-color: #ffffff; color: #1b365d; border: 1px solid #1b365d; text-decoration: none; font-weight: 700; font-size: 13px; padding: 11px 20px; border-radius: 6px; letter-spacing: 0.02em; margin-left: 8px;">
                                    Subscriber Billing &amp; Seats
                                </a>
                            </div>

                            <p style="font-size: 12px; line-height: 1.6; color: #64748b; margin: 16px 0 0 0;">
                                Custom circuit filters or case management exports are available upon request. Simply reply directly to this transmission.
                            </p>

                            <!-- Signature Block -->
                            <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #475569;">
                                <strong style="color: #1b365d; font-size: 13px;">Surplus Docket Intelligence</strong><br>
                                <span style="font-size: 12px; color: #64748b;">Court Registry Ingestion &amp; Verification Desk</span><br>
                                <a href="https://surplusdocket.com" target="_blank" style="color: #4c6d48; text-decoration: none; font-weight: 600;">surplusdocket.com</a> • <a href="mailto:dockets@surplusdocket.com" style="color: #1b365d; text-decoration: none;">dockets@surplusdocket.com</a>
                            </div>
                        </td>
                    </tr>

                    <!-- Institutional Footer -->
                    <tr>
                        <td class="footer-cell" style="background-color: #ffffff; padding: 22px 24px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; line-height: 1.6;">
                            <div style="margin-bottom: 8px; font-weight: 600;">
                                <a href="https://surplusdocket.com/practitioner-toolkit.html" target="_blank" style="color: #526174; text-decoration: none;">Practitioner Toolkit</a> &nbsp;•&nbsp; 
                                <a href="https://surplusdocket.com/api-documentation.html" target="_blank" style="color: #526174; text-decoration: none;">REST API Documentation</a> &nbsp;•&nbsp; 
                                <a href="https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00" target="_blank" style="color: #1b365d; text-decoration: underline; font-weight: 700;">Subscriber Billing Portal</a>
                            </div>
                            {LEGAL_DISCLAIMER}<br>
                            &copy; {year} Surplus Docket. All rights reserved.
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
            "firm": "",
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
        text_body, html_body = compose_email_content(subscribers[0], stats, date_str)
        preview_path = BASE_DIR / "output" / "daily_email_preview.html"
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_text(html_body, encoding="utf-8")
        print(f"✓ Saved HTML email preview to: {preview_path}")
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
    server = None
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASS)
        print(f"✓ Connected and authenticated to {SMTP_HOST} as {GMAIL_USER}")

        # Pre-cache attachment bytes for high performance
        tri_state_csv = EXPORTS_DIR / "Tri_State_Core_Surplus_Feed.csv"
        tri_state_xlsx = EXPORTS_DIR / "Tri_State_Core_Surplus_Feed.xlsx"
        
        feed_cache = {}
        for fpath in (MASTER_CSV, MASTER_XLSX, tri_state_csv, tri_state_xlsx):
            if fpath.exists():
                try:
                    with open(fpath, "rb") as f:
                        feed_cache[fpath.name] = f.read()
                except Exception as e:
                    print(f"Warning caching {fpath.name}: {e}")

        for sub in subscribers:
            dest = sub.get("email")
            if not dest:
                continue

            try:
                msg = MIMEMultipart("mixed")
                msg["Subject"] = subject
                msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
                msg["To"] = dest
                msg["Reply-To"] = REPLY_TO
                msg["Date"] = email.utils.formatdate(localtime=True)
                msg["Message-ID"] = email.utils.make_msgid(domain="surplusdocket.com")

                # Nested alternative container for Plain Text & HTML Body
                body_container = MIMEMultipart("alternative")
                text_body, html_body = compose_email_content(sub, stats, date_str)
                body_container.attach(MIMEText(text_body, "plain", "utf-8"))
                body_container.attach(MIMEText(html_body, "html", "utf-8"))
                msg.attach(body_container)

                # Tier entitlement attachment filtering
                tier_str = str(sub.get("tier", "")).lower()
                sub_jur = sub.get("jurisdictions") or []
                is_national = "national" in tier_str or "six" in tier_str or "enterprise" in tier_str or len(sub_jur) > 3

                target_csv = MASTER_CSV if is_national else (tri_state_csv if tri_state_csv.exists() else MASTER_CSV)
                target_xlsx = MASTER_XLSX if is_national else (tri_state_xlsx if tri_state_xlsx.exists() else MASTER_XLSX)

                formats = sub.get("delivery_format", ["CSV", "Excel"])
                if "CSV" in formats and target_csv.name in feed_cache:
                    part = MIMEBase("text", "csv", name=target_csv.name)
                    part.set_payload(feed_cache[target_csv.name])
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", "attachment", filename=target_csv.name)
                    msg.attach(part)

                if "Excel" in formats and target_xlsx.name in feed_cache:
                    part = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet", name=target_xlsx.name)
                    part.set_payload(feed_cache[target_xlsx.name])
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", "attachment", filename=target_xlsx.name)
                    msg.attach(part)

                server.sendmail(GMAIL_USER, [dest], msg.as_string())
                firm_log = format_firm_suffix(sub)
                print(f"  ✉️ Dispatched morning feed to {sub.get('name', 'Subscriber')} <{dest}>{firm_log}")
                sent_count += 1
            except smtplib.SMTPServerDisconnected:
                print(f"  ⚠️ SMTP Disconnected; attempting reconnect for {dest}...")
                try:
                    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
                    server.starttls()
                    server.login(GMAIL_USER, GMAIL_APP_PASS)
                    server.sendmail(GMAIL_USER, [dest], msg.as_string())
                    sent_count += 1
                    print(f"  ✉️ Dispatched morning feed after reconnect to <{dest}>")
                except Exception as rec_err:
                    print(f"  ❌ Reconnect dispatch failed for {dest}: {rec_err}")
            except Exception as send_err:
                print(f"  ❌ Failed to dispatch to {dest}: {send_err}")

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
    firm_suffix = format_firm_suffix(subscriber)
    total_bal_fmt = f"${stats['total_surplus']:,.2f}"
    rec_count = stats["total_records"]
    year = datetime.now().year

    text_body = f"""Welcome {name},

Your 7-day institutional practice evaluation with Surplus Docket is active for {date_str} under $0 due today.

For the next 7 days, your practice has full access to daily 7:00 AM EST court record feeds indexing verified tax deed surplus and excess proceeds across Florida, Texas, Georgia, North Carolina, Tennessee, and California.

STARTER DATA WORKBOOKS (ATTACHED):
• Master_Surplus_Lead_Feed.csv ({rec_count} files, {total_bal_fmt} gross unencumbered equity)
• Master_Surplus_Lead_Feed.xlsx (Structured workbook with claim urgency tiers and statutory calculation formulas)

KEY PRACTICE ONBOARDING:
1. Daily Ingestion: Fresh verified filings arrive every business morning at 7:00 AM EST.
2. Statutory Toolkit: Download 1-click filing dossiers (FL § 197.582, TX § 34.04, GA § 48-4-5, CA § 4675) at https://surplusdocket.com/practitioner-toolkit.html.
3. Transparent Evaluation Terms: Day 8 rollover to the standard monthly plan ($249/mo). 1-click self-service control anytime via your Stripe Billing Portal: https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00.

QUICK LINKS:
• Practitioner Toolkit & Forms: https://surplusdocket.com/practitioner-toolkit.html
• REST API Documentation: https://surplusdocket.com/api-documentation.html
• Subscriber Billing Portal: https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00

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
        body {{
            margin: 0 !important;
            padding: 0 !important;
            background-color: #ffffff !important;
        }}
        .email-wrapper {{
            width: 100% !important;
            background-color: #ffffff !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        .email-outer-td {{
            padding: 0 !important;
            margin: 0 !important;
        }}
        .email-container {{
            width: 100% !important;
            max-width: 680px !important;
            border-radius: 0 !important;
            border: none !important;
            box-shadow: none !important;
            margin: 0 auto !important;
            background-color: #ffffff !important;
        }}
        @media only screen and (max-width: 680px) {{
            .content-cell {{ padding: 20px 16px !important; }}
            .header-cell {{ padding: 16px 16px !important; }}
            .nav-cell {{ padding: 8px 14px !important; }}
            .header-tag-cell {{ display: none !important; }}
            .deliverables-table td {{ display: block !important; width: 100% !important; box-sizing: border-box !important; margin-bottom: 8px !important; }}
            .deliverables-spacer {{ display: none !important; }}
            .btn-cta {{ display: block !important; width: 100% !important; box-sizing: border-box !important; margin: 6px 0 !important; text-align: center !important; }}
        }}
    </style>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #ffffff; margin: 0; padding: 0; color: #1e293b; line-height: 1.5; -webkit-text-size-adjust: 100%;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-wrapper" style="background-color: #ffffff; width: 100%; margin: 0; padding: 0;">
        <tr>
            <td align="center" class="email-outer-td" style="padding: 0; margin: 0;">
                <!-- Main Card Container -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-container" style="max-width: 680px; width: 100%; background-color: #ffffff; border: none; border-radius: 0; box-shadow: none; margin: 0 auto;">
                    
                    <!-- Header with Official Logo -->
                    <tr>
                        <td class="header-cell" style="background-color: #ffffff; padding: 22px 32px; border-bottom: 2px solid #1b365d;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%;">
                                <tr>
                                    <td align="left" valign="middle" style="padding: 0;">
                                        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td valign="middle" style="padding-right: 14px;">
                                                    <a href="https://surplusdocket.com" target="_blank" style="text-decoration: none; display: block;">
                                                        <img src="https://surplusdocket.com/assets/logo_surplus_docket.png" alt="Surplus Docket Crest" width="46" height="36" style="display: block; width: 46px; height: auto; max-height: 38px; border: 0;" />
                                                    </a>
                                                </td>
                                                <td valign="middle" style="line-height: 1.15;">
                                                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-weight: 900; font-size: 22px; letter-spacing: -0.02em; margin: 0;">
                                                        <a href="https://surplusdocket.com" target="_blank" style="text-decoration: none;">
                                                            <span style="color: #4c6d48; font-weight: 800;">SURPLUS</span> <span style="color: #1b365d; font-weight: 900;">DOCKET</span>
                                                        </a>
                                                    </div>
                                                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 10px; font-weight: 700; color: #64748b; letter-spacing: 0.06em; text-transform: uppercase; margin-top: 3px;">
                                                        Practice Evaluation Activation • B2B Court Feeds
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td align="right" valign="middle" class="header-tag-cell" style="padding: 0;">
                                        <span style="display: inline-block; background-color: #edf3ec; border: 1px solid #c2d9c0; color: #365134; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11px; font-weight: 700; padding: 6px 14px; border-radius: 9999px; letter-spacing: 0.02em; white-space: nowrap;">
                                            $0 DUE TODAY • 7-DAY EVALUATION
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Secondary Quick Navigation Bar -->
                    <tr>
                        <td class="nav-cell" style="background-color: #f8fafc; padding: 9px 32px; border-bottom: 1px solid #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td align="left" style="color: #64748b;">
                                        <a href="https://surplusdocket.com/practitioner-toolkit.html" target="_blank" style="color: #1b365d; text-decoration: none; font-weight: 700;">Practitioner Toolkit</a>
                                        <span style="color: #cbd5e1; margin: 0 8px;">•</span>
                                        <a href="https://surplusdocket.com/api-documentation.html" target="_blank" style="color: #526174; text-decoration: none;">API Docs</a>
                                        <span style="color: #cbd5e1; margin: 0 8px;">•</span>
                                        <a href="https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00" target="_blank" style="color: #526174; text-decoration: none;">Billing Portal</a>
                                    </td>
                                    <td align="right" style="color: #94a3b8; font-size: 11px; font-weight: 500;">
                                        {date_str}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td class="content-cell" style="padding: 28px 32px; background-color: #ffffff;">
                            <p style="font-size: 15px; margin: 0 0 12px 0; color: #102238;">Welcome <b>{name}</b>{firm_suffix},</p>
                            <p style="font-size: 13px; line-height: 1.6; color: #475569; margin: 0 0 20px 0;">
                                Your 7-day institutional practice evaluation is active. For the next 7 days, your firm has full access to verified court registry intelligence across 6 core states with senior mortgages, institutional liens, and junior municipal encumbrances filtered upstream.
                            </p>

                            <!-- Attached Deliverables Card -->
                            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px 20px; margin: 20px 0;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td style="padding-bottom: 10px;">
                                            <div style="font-size: 12px; font-weight: 800; color: #1b365d; text-transform: uppercase; letter-spacing: 0.05em;">
                                                📎 Attached Immediate Starter Datasets
                                            </div>
                                            <div style="font-size: 12px; color: #64748b; margin-top: 4px;">
                                                Today's complete audited files ({rec_count} verified dockets, {total_bal_fmt} gross equity) are attached to this transmission:
                                            </div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>
                                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="deliverables-table">
                                                <tr>
                                                    <td width="49%" style="background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 10px 14px;">
                                                        <div style="font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12px; font-weight: 700; color: #1b365d;">📄 Master_Surplus_Lead_Feed.csv</div>
                                                        <div style="font-size: 11px; color: #64748b; margin-top: 2px;">Direct CRM import for immediate case triage</div>
                                                    </td>
                                                    <td width="2%" class="deliverables-spacer" style="width: 8px;"></td>
                                                    <td width="49%" style="background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 10px 14px;">
                                                        <div style="font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12px; font-weight: 700; color: #1b365d;">📊 Master_Surplus_Lead_Feed.xlsx</div>
                                                        <div style="font-size: 11px; color: #64748b; margin-top: 2px;">Structured workbook with urgency tiers &amp; formulas</div>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                </table>
                            </div>

                            <!-- Next Steps Onboarding Box -->
                            <div style="background-color: #edf3ec; border: 1px solid #c2d9c0; border-radius: 10px; padding: 18px 20px; margin: 22px 0;">
                                <div style="font-size: 12px; font-weight: 800; color: #365134; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px;">
                                    What to Expect Over Your 7-Day Evaluation:
                                </div>
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="font-size: 12px; color: #2e442c; line-height: 1.6;">
                                    <tr>
                                        <td style="padding: 4px 0; vertical-align: top; width: 22px;">1.</td>
                                        <td style="padding: 4px 0;"><b>Daily 7:00 AM EST Feeds:</b> Fresh clerk filings delivered to this inbox every business morning before US court hours.</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 4px 0; vertical-align: top;">2.</td>
                                        <td style="padding: 4px 0;"><b>Statutory Petitions:</b> Download 1-click filing dossiers for FL, TX, GA, and CA in the <a href="https://surplusdocket.com/practitioner-toolkit.html" target="_blank" style="color: #1b365d; font-weight: 700; text-decoration: underline;">Practitioner Toolkit</a>.</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 4px 0; vertical-align: top;">3.</td>
                                        <td style="padding: 4px 0;"><b>1-Click Self-Serve Control:</b> Rollover occurs on Day 8 ($249/mo). Adjust seats, pause, or cancel anytime with zero friction via the <a href="https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00" target="_blank" style="color: #1b365d; font-weight: 700; text-decoration: underline;">Stripe Subscriber Portal</a>.</td>
                                    </tr>
                                </table>
                            </div>

                            <!-- Action Buttons -->
                            <div style="text-align: center; margin: 28px 0 22px 0;">
                                <a href="https://surplusdocket.com/practitioner-toolkit.html" target="_blank" class="btn-cta" style="display: inline-block; background-color: #1b365d; color: #ffffff; text-decoration: none; font-weight: 700; font-size: 13px; padding: 13px 26px; border-radius: 6px; letter-spacing: 0.02em; box-shadow: 0 2px 6px rgba(27,54,93,0.18);">
                                    Access Practitioner Toolkit &rarr;
                                </a>
                                <a href="https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00" target="_blank" class="btn-cta" style="display: inline-block; background-color: #ffffff; color: #1b365d; border: 1px solid #1b365d; text-decoration: none; font-weight: 700; font-size: 13px; padding: 12px 22px; border-radius: 6px; letter-spacing: 0.02em; margin-left: 8px;">
                                    Manage Subscription in Stripe
                                </a>
                            </div>

                            <p style="font-size: 12px; line-height: 1.6; color: #64748b; margin: 16px 0 0 0;">
                                If you need assistance configuring circuit filters or integrating our feeds into your case management software, simply reply directly to this email.
                            </p>

                            <!-- Signature Block -->
                            <div style="margin-top: 26px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #475569;">
                                <strong style="color: #1b365d; font-size: 13px;">Surplus Docket Intelligence</strong><br>
                                <span style="font-size: 12px; color: #64748b;">Court Registry Ingestion &amp; Verification Desk</span><br>
                                <a href="https://surplusdocket.com" target="_blank" style="color: #4c6d48; text-decoration: none; font-weight: 600;">surplusdocket.com</a> • <a href="mailto:dockets@surplusdocket.com" style="color: #1b365d; text-decoration: none;">dockets@surplusdocket.com</a>
                            </div>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #ffffff; padding: 22px 24px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; line-height: 1.6;">
                            <div style="margin-bottom: 8px; font-weight: 600;">
                                <a href="https://surplusdocket.com/practitioner-toolkit.html" target="_blank" style="color: #526174; text-decoration: none;">Practitioner Toolkit</a> &nbsp;•&nbsp; 
                                <a href="https://surplusdocket.com/api-documentation.html" target="_blank" style="color: #526174; text-decoration: none;">REST API Documentation</a> &nbsp;•&nbsp; 
                                <a href="https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00" target="_blank" style="color: #1b365d; text-decoration: underline; font-weight: 700;">Subscriber Billing Portal</a>
                            </div>
                            {LEGAL_DISCLAIMER}<br>
                            &copy; {year} Surplus Docket. All rights reserved.
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
        target = {"email": args.recipient or "david@surplusdocket.com", "name": "Counsel", "firm": ""}
        sys.exit(0 if dispatch_activation_starter_kit(target, is_dry_run=args.dry_run) else 1)

    if not args.send and not args.dry_run:
        args.dry_run = True

    sys.exit(dispatch_feed(is_dry_run=args.dry_run, recipient_override=args.recipient))

