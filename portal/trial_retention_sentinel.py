#!/usr/bin/env python3
"""
Surplus Docket — Institutional 7-Day Trial Retention Sentinel
=============================================================
Automated lifecycle communication engine for 7-day trial evaluation seats:
- Day 3: Statutory Claim Windows & Practitioner Toolkit Advisory
- Day 6: Transparent Evaluation Summary & 1-Click Rollover Notice

Executes daily via GitHub Actions runner to ensure seamless subscriber onboarding,
statutory guidance, and commercial transparency.
"""

import os
import sys
import json
import argparse
import smtplib
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load Environment Variables from .env if present
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as ef:
            for line in ef:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))
    except Exception:
        pass

PORTAL_DIR = BASE_DIR / "portal"
SUBSCRIBERS_FILE = PORTAL_DIR / "subscribers.json"
LIFECYCLE_LOG_FILE = PORTAL_DIR / "trial_lifecycle_log.json"

GMAIL_USER = os.getenv("GMAIL_USER", "sandwichfitness@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "dockets@surplusdocket.com")
FROM_NAME = os.getenv("FROM_NAME", "Surplus Docket Intelligence")
REPLY_TO = "dockets@surplusdocket.com"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

STRIPE_PORTAL_URL = "https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00"
STRIPE_CHECKOUT_URL = "https://buy.stripe.com/4gM14n8yq9vl0vrb0i0ZW21"
TOOLKIT_URL = "https://surplusdocket.com/practitioner-toolkit.html"
LOGO_URL = "https://surplusdocket.com/assets/logo_surplus_docket.png"

LEGAL_DISCLAIMER = (
    "DISCLAIMER: Surplus Docket is an automated public court records intelligence indexing platform. "
    "We provide direct clerk filings and unencumbered surplus calculations for legal practitioners. "
    "Surplus Docket does not provide legal representation or legal advice."
)


def load_lifecycle_log():
    if not LIFECYCLE_LOG_FILE.exists():
        return {}
    try:
        with open(LIFECYCLE_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_lifecycle_log(log_data):
    LIFECYCLE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LIFECYCLE_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2)


def format_firm_suffix(subscriber):
    raw_firm = (subscriber.get("firm") or "").strip()
    if raw_firm and raw_firm not in ("Surplus Docket Compliance & Research Desk", "Practice", "Legal Practice", "Firm"):
        return f" ({raw_firm})"
    return ""


def compose_day1_email(subscriber):
    name = subscriber.get("name", "Counsel")
    firm_suffix = format_firm_suffix(subscriber)
    year = datetime.now().year

    text_body = f"""Dear {name},

Welcome to Surplus Docket. Your 7-day practice evaluation seat is active and your court registry intelligence feeds are initialized.

Every business morning at 7:00 AM EST, your practice receives audited court registry filings across Florida, Texas, Georgia, California, North Carolina, and Tennessee.

QUICK-START: 3 ESSENTIAL PRACTICE STEPS:
1. DAILY FEED DELIVERY:
Your morning feed arrives directly in your inbox with attached CSV and Excel (.xlsx) files. Senior mortgages, institutional liens, and junior municipal encumbrances have been verified and filtered upstream.

2. CASE MANAGEMENT IMPORT:
Our CSV feeds are pre-formatted for direct one-click import into Clio, Filevine, MyCase, and PracticePanther, complete with parcel IDs, defendant names, and official clerk docket links.

3. PRACTITIONER TOOLKIT & STATUTORY PETITIONS:
Access verified claim petitions, surplus motions, and clerk submission guidelines directly from our Practitioner Toolkit:
{TOOLKIT_URL}

NEED CUSTOM COUNTY FILTERS?
If your firm focuses on specific circuits or counties, reply directly to this transmission. Our ingestion team will tailor your morning feed.

MANAGE YOUR EVALUATION SEAT:
• Practitioner Toolkit & Forms: {TOOLKIT_URL}
• Subscriber Billing & Seat Management: {STRIPE_PORTAL_URL}

Best regards,

Surplus Docket Intelligence
Court Registry Ingestion Desk | Surplus Docket
surplusdocket.com • dockets@surplusdocket.com

---
{LEGAL_DISCLAIMER}
Manage Subscription in Stripe Portal: {STRIPE_PORTAL_URL}
"""

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome Counsel — Practice Quick-Start</title>
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
            background-color: #f8f8f4 !important;
        }}
        .email-wrapper {{
            width: 100% !important;
            background-color: #f8f8f4 !important;
            margin: 0 !important;
            padding: 24px 12px !important;
        }}
        .email-outer-td {{
            padding: 0 !important;
            margin: 0 !important;
        }}
        .email-container {{
            width: 100% !important;
            max-width: 660px !important;
            border-radius: 12px !important;
            border: 1px solid #e2e8f0 !important;
            box-shadow: 0 4px 20px -4px rgba(27,54,93,0.08) !important;
            margin: 0 auto !important;
            background-color: #ffffff !important;
            overflow: hidden !important;
        }}
        @media only screen and (max-width: 640px) {{
            .email-wrapper {{
                padding: 12px 6px !important;
            }}
            .email-container {{
                width: 100% !important;
                max-width: 100% !important;
                border-radius: 10px !important;
            }}
            .content-cell {{
                padding: 22px 18px !important;
            }}
            .header-cell {{
                padding: 16px 18px !important;
            }}
            .nav-cell {{
                padding: 9px 14px !important;
                text-align: center !important;
            }}
            .footer-cell {{
                padding: 20px 16px !important;
            }}
            .header-tag-cell {{
                display: none !important;
            }}
            .btn-cta {{
                display: block !important;
                width: 100% !important;
                box-sizing: border-box !important;
                margin: 8px 0 !important;
                text-align: center !important;
                padding: 14px 16px !important;
                font-size: 13px !important;
                border-radius: 8px !important;
            }}
            .btn-cta-secondary {{
                margin-left: 0 !important;
            }}
        }}
    </style>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8f8f4; margin: 0; padding: 0; color: #1e293b; line-height: 1.5; -webkit-text-size-adjust: 100%;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-wrapper" style="background-color: #f8f8f4; width: 100%; margin: 0; padding: 24px 12px;">
        <tr>
            <td align="center" class="email-outer-td" style="padding: 0; margin: 0;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-container" style="max-width: 660px; width: 100%; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 4px 20px -4px rgba(27,54,93,0.08); margin: 0 auto; overflow: hidden;">
                    <tr>
                        <td class="header-cell" style="background-color: #ffffff; padding: 20px 28px; border-bottom: 2px solid #1b365d;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%;">
                                <tr>
                                    <td align="left" valign="middle" style="padding: 0;">
                                        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td valign="middle" style="padding-right: 14px;">
                                                    <a href="https://surplusdocket.com" target="_blank" style="text-decoration: none; display: block;">
                                                        <img src="{LOGO_URL}" alt="Surplus Docket Crest" width="46" height="36" style="display: block; width: 46px; height: auto; max-height: 38px; border: 0;" />
                                                    </a>
                                                </td>
                                                <td valign="middle" style="line-height: 1.15;">
                                                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-weight: 900; font-size: 22px; letter-spacing: -0.02em; margin: 0;">
                                                        <a href="https://surplusdocket.com" target="_blank" style="text-decoration: none;">
                                                            <span style="color: #4c6d48; font-weight: 800;">SURPLUS</span> <span style="color: #1b365d; font-weight: 900;">DOCKET</span>
                                                        </a>
                                                    </div>
                                                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 10px; font-weight: 700; color: #64748b; letter-spacing: 0.06em; text-transform: uppercase; margin-top: 3px;">
                                                        Court Registry Intelligence
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td align="right" valign="middle" class="header-tag-cell" style="padding: 0;">
                                        <a href="{STRIPE_PORTAL_URL}" target="_blank" style="text-decoration: none;">
                                            <span style="display: inline-block; background-color: #edf3ec; color: #365134; border: 1px solid #c2d9c0; font-size: 11px; font-weight: 800; padding: 6px 14px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">
                                                Evaluation Day 1 of 7
                                            </span>
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td class="content-cell" style="padding: 26px 30px; background-color: #ffffff;">
                            <p style="font-size: 15px; margin: 0 0 12px 0; color: #102238;">Dear <b>{name}</b>{firm_suffix},</p>
                            <p style="font-size: 13px; line-height: 1.6; color: #475569; margin: 0 0 20px 0;">
                                Welcome to Surplus Docket. Your 7-day practice evaluation seat is active and your court registry intelligence feeds are configured. Below are the key steps to integrate our unencumbered surplus intelligence into your practice workflow immediately.
                            </p>
                            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px 20px; margin: 20px 0;">
                                <div style="font-size: 12px; font-weight: 800; color: #1b365d; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;">
                                    🚀 Practice Quick-Start Overview:
                                </div>
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="font-size: 12px; color: #334155; line-height: 1.6;">
                                    <tr>
                                        <td style="padding: 6px 0; font-weight: 700; width: 140px; color: #1b365d;">Daily 7:00 AM Delivery:</td>
                                        <td style="padding: 6px 0;">Freshly audited court filings delivered every weekday morning with attached CSV &amp; Excel sheets.</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; font-weight: 700; color: #1b365d;">Zero Bank Liens:</td>
                                        <td style="padding: 6px 0;">Upstream verification filters senior mortgages and tax deeds so only recoverable surplus reaches your desk.</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; font-weight: 700; color: #1b365d;">Clio / Filevine Ready:</td>
                                        <td style="padding: 6px 0;">Pre-mapped matter exports allow instant intake and conflict checks without manual data entry.</td>
                                    </tr>
                                </table>
                            </div>
                            <div style="text-align: center; margin: 28px 0 22px 0;">
                                <a href="{TOOLKIT_URL}" target="_blank" class="btn-cta" style="display: inline-block; background-color: #1b365d; color: #ffffff; text-decoration: none; font-weight: 700; font-size: 13px; padding: 13px 26px; border-radius: 8px; letter-spacing: 0.02em; box-shadow: 0 2px 6px rgba(27,54,93,0.18);">
                                    Access Practitioner Toolkit &rarr;
                                </a>
                                <a href="{STRIPE_PORTAL_URL}" target="_blank" class="btn-cta btn-cta-secondary" style="display: inline-block; background-color: #ffffff; color: #1b365d; border: 1.5px solid #1b365d; text-decoration: none; font-weight: 700; font-size: 13px; padding: 12px 22px; border-radius: 8px; letter-spacing: 0.02em; margin-left: 8px;">
                                    Manage Subscription Portal
                                </a>
                            </div>
                            <div style="margin-top: 26px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #475569;">
                                <strong style="color: #1b365d; font-size: 13px;">Surplus Docket Intelligence</strong><br>
                                <span style="font-size: 12px; color: #64748b;">Court Registry Ingestion Desk | Surplus Docket</span><br>
                                <a href="https://surplusdocket.com" target="_blank" style="color: #4c6d48; text-decoration: none; font-weight: 600;">surplusdocket.com</a> • <a href="mailto:dockets@surplusdocket.com" style="color: #1b365d; text-decoration: none;">dockets@surplusdocket.com</a>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td class="footer-cell" style="background-color: #f8fafc; padding: 22px 28px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; line-height: 1.6;">
                            <div style="margin-bottom: 8px; font-weight: 600;">
                                <a href="{TOOLKIT_URL}" target="_blank" style="color: #526174; text-decoration: none;">Practitioner Toolkit</a> &nbsp;•&nbsp; 
                                <a href="{STRIPE_PORTAL_URL}" target="_blank" style="color: #1b365d; text-decoration: underline; font-weight: 700;">Subscriber Billing Portal</a>
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


def compose_day3_email(subscriber):
    name = subscriber.get("name", "Counsel")
    firm_suffix = format_firm_suffix(subscriber)
    year = datetime.now().year

    text_body = f"""Dear {name},

As your practice enters Day 3 of your 7-day evaluation with Surplus Docket, here is key statutory guidance on how asset recovery counsel leverage our daily court intelligence feeds.

Every record in your morning feed is indexed against strict statutory claim windows before funds escheat to county or state general revenue:

CORE STATUTORY CLAIM WINDOWS:
• Florida (Fla. Stat. § 197.582): 120-day strict deadline from clerk's formal notice of surplus. Claims filed after 120 days are barred.
• Texas (Tex. Tax Code § 34.04): 2-year limitation period from the date the deed is filed for record.
• Georgia (O.C.G.A. § 48-4-5): 5-year priority distribution window for lienholders and former owners.
• California (Cal. Rev. & Tax Code § 4675): 1-year strict claim window following deed recordation.
• North Carolina (N.C. Gen. Stat. § 105-374) & Tennessee (Tenn. Code § 67-5-2501): Statutory recovery rules with mandatory lienholder ranking.

HOW TO USE URGENCY TIERS IN YOUR MASTER FEED:
• Tier 1 (< 45 Days Remaining): High-urgency files at imminent risk of escheatment.
• Tier 2 (45–120 Days): Optimal petition intake window for title research and verified petition filing.
• Tier 3 (> 120 Days): Active claim window for medium-term case pipeline growth.

PRACTITIONER TOOLKIT & STATUTORY PETITIONS:
Download verified motion templates, notice of appearance forms, and clerk claim petitions directly from our Practitioner Toolkit:
{TOOLKIT_URL}

QUICK LINKS:
• Practitioner Toolkit & Statutory Forms: {TOOLKIT_URL}
• Subscriber Billing & Seat Management: {STRIPE_PORTAL_URL}

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
    <title>Practice Advisory — Statutory Claim Windows</title>
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
            background-color: #f8f8f4 !important;
        }}
        .email-wrapper {{
            width: 100% !important;
            background-color: #f8f8f4 !important;
            margin: 0 !important;
            padding: 24px 12px !important;
        }}
        .email-outer-td {{
            padding: 0 !important;
            margin: 0 !important;
        }}
        .email-container {{
            width: 100% !important;
            max-width: 660px !important;
            border-radius: 12px !important;
            border: 1px solid #e2e8f0 !important;
            box-shadow: 0 4px 20px -4px rgba(27,54,93,0.08) !important;
            margin: 0 auto !important;
            background-color: #ffffff !important;
            overflow: hidden !important;
        }}
        @media only screen and (max-width: 640px) {{
            .email-wrapper {{
                padding: 12px 6px !important;
            }}
            .email-container {{
                width: 100% !important;
                max-width: 100% !important;
                border-radius: 10px !important;
            }}
            .content-cell {{
                padding: 22px 18px !important;
            }}
            .header-cell {{
                padding: 16px 18px !important;
            }}
            .nav-cell {{
                padding: 9px 14px !important;
                text-align: center !important;
            }}
            .footer-cell {{
                padding: 20px 16px !important;
            }}
            .header-tag-cell {{
                display: none !important;
            }}
            .btn-cta {{
                display: block !important;
                width: 100% !important;
                box-sizing: border-box !important;
                margin: 8px 0 !important;
                text-align: center !important;
                padding: 14px 16px !important;
                font-size: 13px !important;
                border-radius: 8px !important;
            }}
            .btn-cta-secondary {{
                margin-left: 0 !important;
            }}
        }}
    </style>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8f8f4; margin: 0; padding: 0; color: #1e293b; line-height: 1.5; -webkit-text-size-adjust: 100%;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-wrapper" style="background-color: #f8f8f4; width: 100%; margin: 0; padding: 24px 12px;">
        <tr>
            <td align="center" class="email-outer-td" style="padding: 0; margin: 0;">
                <!-- Main Card Container -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-container" style="max-width: 660px; width: 100%; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 4px 20px -4px rgba(27,54,93,0.08); margin: 0 auto; overflow: hidden;">
                    
                    <!-- Top Brand Header -->
                    <tr>
                        <td class="header-cell" style="background-color: #ffffff; padding: 20px 28px; border-bottom: 2px solid #1b365d;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%;">
                                <tr>
                                    <td align="left" valign="middle" style="padding: 0;">
                                        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td valign="middle" style="padding-right: 14px;">
                                                    <a href="https://surplusdocket.com" target="_blank" style="text-decoration: none; display: block;">
                                                        <img src="{LOGO_URL}" alt="Surplus Docket Crest" width="46" height="36" style="display: block; width: 46px; height: auto; max-height: 38px; border: 0;" />
                                                    </a>
                                                </td>
                                                <td valign="middle" style="line-height: 1.15;">
                                                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-weight: 900; font-size: 22px; letter-spacing: -0.02em; margin: 0;">
                                                        <a href="https://surplusdocket.com" target="_blank" style="text-decoration: none;">
                                                            <span style="color: #4c6d48; font-weight: 800;">SURPLUS</span> <span style="color: #1b365d; font-weight: 900;">DOCKET</span>
                                                        </a>
                                                    </div>
                                                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 10px; font-weight: 700; color: #64748b; letter-spacing: 0.06em; text-transform: uppercase; margin-top: 3px;">
                                                        Court Registry Intelligence
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td align="right" valign="middle" class="header-tag-cell" style="padding: 0;">
                                        <a href="{TOOLKIT_URL}" target="_blank" style="text-decoration: none;">
                                            <span style="display: inline-block; background-color: #edf3ec; border: 1px solid #c2d9c0; color: #365134; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11px; font-weight: 700; padding: 6px 14px; border-radius: 9999px; letter-spacing: 0.02em; white-space: nowrap;">
                                                DAY 3 • STATUTORY ADVISORY
                                            </span>
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Secondary Quick Navigation Bar -->
                    <tr>
                        <td class="nav-cell" style="background-color: #f8fafc; padding: 9px 28px; border-bottom: 1px solid #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td align="left" style="color: #64748b;">
                                        <a href="{TOOLKIT_URL}" target="_blank" style="color: #1b365d; text-decoration: none; font-weight: 700;">Practitioner Toolkit</a>
                                        <span style="color: #cbd5e1; margin: 0 8px;">•</span>
                                        <a href="{STRIPE_PORTAL_URL}" target="_blank" style="color: #526174; text-decoration: none;">Billing Portal</a>
                                    </td>
                                    <td align="right" style="color: #94a3b8; font-size: 11px; font-weight: 500;">
                                        Evaluation Day 3 of 7
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td class="content-cell" style="padding: 26px 30px; background-color: #ffffff;">
                            <p style="font-size: 15px; margin: 0 0 12px 0; color: #102238;">Dear <b>{name}</b>{firm_suffix},</p>
                            <p style="font-size: 13px; line-height: 1.6; color: #475569; margin: 0 0 20px 0;">
                                As your practice enters Day 3 of your 7-day evaluation with Surplus Docket, here is key guidance on how leading asset recovery counsel leverage the statutory countdown metrics embedded in your morning court feed.
                            </p>

                            <!-- Stat Windows Card -->
                            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px 20px; margin: 20px 0;">
                                <div style="font-size: 12px; font-weight: 800; color: #1b365d; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;">
                                    Jurisdictional Statutory Claim Deadlines:
                                </div>
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="font-size: 12px; color: #334155; line-height: 1.6;">
                                    <tr>
                                        <td style="padding: 6px 0; font-weight: 700; width: 110px; color: #1b365d;">Florida:</td>
                                        <td style="padding: 6px 0;"><b>120 Days</b> strict window under Fla. Stat. § 197.582 from clerk notice.</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; font-weight: 700; color: #1b365d;">Texas:</td>
                                        <td style="padding: 6px 0;"><b>2 Years</b> statutory limitation from deed recordation (Tex. Tax Code § 34.04).</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; font-weight: 700; color: #1b365d;">Georgia:</td>
                                        <td style="padding: 6px 0;"><b>5-Year</b> priority claims window under O.C.G.A. § 48-4-5.</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; font-weight: 700; color: #1b365d;">California:</td>
                                        <td style="padding: 6px 0;"><b>1 Year</b> strict forfeiture bar (Cal. Rev. &amp; Tax Code § 4675).</td>
                                    </tr>
                                </table>
                            </div>

                            <!-- Urgency Tiers Card -->
                            <div style="background-color: #edf3ec; border: 1px solid #c2d9c0; border-radius: 10px; padding: 18px 20px; margin: 20px 0;">
                                <div style="font-size: 12px; font-weight: 800; color: #365134; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px;">
                                    ⚡ How to Filter by Urgency Tier in Your Feed:
                                </div>
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="font-size: 12px; color: #2e442c; line-height: 1.6;">
                                    <tr>
                                        <td style="padding: 4px 0; vertical-align: top; width: 20px;">•</td>
                                        <td style="padding: 4px 0;"><b>Tier 1 (&lt; 45 Days Remaining):</b> High-urgency files at imminent risk of escheatment. Priority for owner contact.</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 4px 0; vertical-align: top;">•</td>
                                        <td style="padding: 4px 0;"><b>Tier 2 (45–120 Days):</b> Optimal statutory window for title research and verified petition filing.</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 4px 0; vertical-align: top;">•</td>
                                        <td style="padding: 4px 0;"><b>Tier 3 (&gt; 120 Days):</b> Active claim window for medium-term case pipeline growth.</td>
                                    </tr>
                                </table>
                            </div>

                            <!-- Action Buttons -->
                            <div style="text-align: center; margin: 28px 0 22px 0;">
                                <a href="{TOOLKIT_URL}" target="_blank" class="btn-cta" style="display: inline-block; background-color: #1b365d; color: #ffffff; text-decoration: none; font-weight: 700; font-size: 13px; padding: 13px 26px; border-radius: 8px; letter-spacing: 0.02em; box-shadow: 0 2px 6px rgba(27,54,93,0.18);">
                                    Access Practitioner Motion Dossiers &rarr;
                                </a>
                                <a href="{STRIPE_PORTAL_URL}" target="_blank" class="btn-cta btn-cta-secondary" style="display: inline-block; background-color: #ffffff; color: #1b365d; border: 1.5px solid #1b365d; text-decoration: none; font-weight: 700; font-size: 13px; padding: 12px 22px; border-radius: 8px; letter-spacing: 0.02em; margin-left: 8px;">
                                    Subscriber Billing Portal
                                </a>
                            </div>

                            <p style="font-size: 12px; line-height: 1.6; color: #64748b; margin: 16px 0 0 0;">
                                Custom circuit filters or case management exports are available upon request. Simply reply directly to this transmission.
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
                        <td class="footer-cell" style="background-color: #f8fafc; padding: 22px 28px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; line-height: 1.6;">
                            <div style="margin-bottom: 8px; font-weight: 600;">
                                <a href="{TOOLKIT_URL}" target="_blank" style="color: #526174; text-decoration: none;">Practitioner Toolkit</a> &nbsp;•&nbsp; 
                                <a href="{STRIPE_PORTAL_URL}" target="_blank" style="color: #1b365d; text-decoration: underline; font-weight: 700;">Subscriber Billing Portal</a>
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


def compose_day6_email(subscriber):
    name = subscriber.get("name", "Counsel")
    firm_suffix = format_firm_suffix(subscriber)
    year = datetime.now().year

    text_body = f"""Dear {name},

We are writing with an institutional courtesy notice regarding your 7-day evaluation of Surplus Docket.

Your practice evaluation seat will complete its 7-day introductory period tomorrow. In alignment with our commitment to full commercial transparency, here is your account status:

EVALUATION SUMMARY:
• Coverage: Verified tax deed surplus filings across FL, TX, GA, NC, TN, and CA.
• Upstream Filtration: Senior mortgages and institutional liens audited.
• Delivery: Daily 7:00 AM EST court feeds directly to your inbox.

SEAMLESS ROLLOVER TERMS (DAY 8):
To ensure your daily litigation pipeline is never interrupted, your subscription will transition seamlessly on Day 8 to the standard Core Plan ($249/month). 

1-CLICK SELF-SERVE CONTROL:
• If you wish to continue receiving daily feeds, no action is required.
• To add practice seats, change payment methods, pause, or cancel, you have 1-click self-service access anytime via your Stripe Subscriber Portal:
{STRIPE_PORTAL_URL}

KEY GUARANTEES:
• Zero cancellation penalties or lock-in contracts.
• 1-click cancellation directly inside the Stripe billing portal.
• Uninterrupted data delivery as long as your evaluation remains active.

Best regards,

Surplus Docket Intelligence
Court Registry Ingestion Desk | Surplus Docket
surplusdocket.com • dockets@surplusdocket.com

---
{LEGAL_DISCLAIMER}
Manage Subscription in Stripe Portal: {STRIPE_PORTAL_URL}
"""

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Courtesy Notice — Practice Evaluation Summary</title>
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
            background-color: #f8f8f4 !important;
        }}
        .email-wrapper {{
            width: 100% !important;
            background-color: #f8f8f4 !important;
            margin: 0 !important;
            padding: 24px 12px !important;
        }}
        .email-outer-td {{
            padding: 0 !important;
            margin: 0 !important;
        }}
        .email-container {{
            width: 100% !important;
            max-width: 660px !important;
            border-radius: 12px !important;
            border: 1px solid #e2e8f0 !important;
            box-shadow: 0 4px 20px -4px rgba(27,54,93,0.08) !important;
            margin: 0 auto !important;
            background-color: #ffffff !important;
            overflow: hidden !important;
        }}
        @media only screen and (max-width: 640px) {{
            .email-wrapper {{
                padding: 12px 6px !important;
            }}
            .email-container {{
                width: 100% !important;
                max-width: 100% !important;
                border-radius: 10px !important;
            }}
            .content-cell {{
                padding: 22px 18px !important;
            }}
            .header-cell {{
                padding: 16px 18px !important;
            }}
            .nav-cell {{
                padding: 9px 14px !important;
                text-align: center !important;
            }}
            .footer-cell {{
                padding: 20px 16px !important;
            }}
            .header-tag-cell {{
                display: none !important;
            }}
            .btn-cta {{
                display: block !important;
                width: 100% !important;
                box-sizing: border-box !important;
                margin: 8px 0 !important;
                text-align: center !important;
                padding: 14px 16px !important;
                font-size: 13px !important;
                border-radius: 8px !important;
            }}
            .btn-cta-secondary {{
                margin-left: 0 !important;
            }}
        }}
    </style>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8f8f4; margin: 0; padding: 0; color: #1e293b; line-height: 1.5; -webkit-text-size-adjust: 100%;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-wrapper" style="background-color: #f8f8f4; width: 100%; margin: 0; padding: 24px 12px;">
        <tr>
            <td align="center" class="email-outer-td" style="padding: 0; margin: 0;">
                <!-- Main Card Container -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-container" style="max-width: 660px; width: 100%; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 4px 20px -4px rgba(27,54,93,0.08); margin: 0 auto; overflow: hidden;">
                    
                    <!-- Top Brand Header -->
                    <tr>
                        <td class="header-cell" style="background-color: #ffffff; padding: 20px 28px; border-bottom: 2px solid #1b365d;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%;">
                                <tr>
                                    <td align="left" valign="middle" style="padding: 0;">
                                        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td valign="middle" style="padding-right: 14px;">
                                                    <a href="https://surplusdocket.com" target="_blank" style="text-decoration: none; display: block;">
                                                        <img src="{LOGO_URL}" alt="Surplus Docket Crest" width="46" height="36" style="display: block; width: 46px; height: auto; max-height: 38px; border: 0;" />
                                                    </a>
                                                </td>
                                                <td valign="middle" style="line-height: 1.15;">
                                                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-weight: 900; font-size: 22px; letter-spacing: -0.02em; margin: 0;">
                                                        <a href="https://surplusdocket.com" target="_blank" style="text-decoration: none;">
                                                            <span style="color: #4c6d48; font-weight: 800;">SURPLUS</span> <span style="color: #1b365d; font-weight: 900;">DOCKET</span>
                                                        </a>
                                                    </div>
                                                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 10px; font-weight: 700; color: #64748b; letter-spacing: 0.06em; text-transform: uppercase; margin-top: 3px;">
                                                        Court Registry Intelligence
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td align="right" valign="middle" class="header-tag-cell" style="padding: 0;">
                                        <a href="{STRIPE_PORTAL_URL}" target="_blank" style="text-decoration: none;">
                                            <span style="display: inline-block; background-color: #edf3ec; border: 1px solid #c2d9c0; color: #365134; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11px; font-weight: 700; padding: 6px 14px; border-radius: 9999px; letter-spacing: 0.02em; white-space: nowrap;">
                                                DAY 6 • COURTESY NOTICE
                                            </span>
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Secondary Quick Navigation Bar -->
                    <tr>
                        <td class="nav-cell" style="background-color: #f8fafc; padding: 9px 28px; border-bottom: 1px solid #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td align="left" style="color: #64748b;">
                                        <a href="{TOOLKIT_URL}" target="_blank" style="color: #1b365d; text-decoration: none; font-weight: 700;">Practitioner Toolkit</a>
                                        <span style="color: #cbd5e1; margin: 0 8px;">•</span>
                                        <a href="{STRIPE_PORTAL_URL}" target="_blank" style="color: #526174; text-decoration: none;">Billing Portal</a>
                                    </td>
                                    <td align="right" style="color: #94a3b8; font-size: 11px; font-weight: 500;">
                                        Evaluation Day 6 of 7
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td class="content-cell" style="padding: 26px 30px; background-color: #ffffff;">
                            <p style="font-size: 15px; margin: 0 0 12px 0; color: #102238;">Dear <b>{name}</b>{firm_suffix},</p>
                            <p style="font-size: 13px; line-height: 1.6; color: #475569; margin: 0 0 20px 0;">
                                This is an institutional courtesy notice regarding your 7-day practice evaluation of Surplus Docket. Your trial introductory period concludes tomorrow.
                            </p>

                            <!-- Transparent Terms Box -->
                            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px 20px; margin: 20px 0;">
                                <div style="font-size: 12px; font-weight: 800; color: #1b365d; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px;">
                                    Seamless Rollover &amp; Evaluation Terms:
                                </div>
                                <p style="font-size: 13px; color: #334155; line-height: 1.6; margin: 0 0 12px 0;">
                                    To ensure your morning court feed and litigation intake remain completely uninterrupted, your subscription will transition seamlessly on Day 8 to the standard Core Plan ($249/month).
                                </p>
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="font-size: 12px; color: #475569; line-height: 1.6;">
                                    <tr>
                                        <td style="padding: 4px 0; vertical-align: top; width: 20px;">•</td>
                                        <td style="padding: 4px 0;"><b>Unbroken Delivery:</b> Continuous 7:00 AM EST daily morning feeds to your primary inbox.</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 4px 0; vertical-align: top;">•</td>
                                        <td style="padding: 4px 0;"><b>Audited Dockets:</b> Full access to verified unencumbered equity filings across all 6 core states.</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 4px 0; vertical-align: top;">•</td>
                                        <td style="padding: 4px 0;"><b>Practitioner Dossiers:</b> Ongoing access to statutory court motion templates and petitions.</td>
                                    </tr>
                                </table>
                            </div>

                            <!-- 1-Click Management Box -->
                            <div style="background-color: #edf3ec; border: 1px solid #c2d9c0; border-radius: 10px; padding: 18px 20px; margin: 20px 0;">
                                <div style="font-size: 12px; font-weight: 800; color: #365134; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">
                                    🛡️ 100% Self-Serve Account Control
                                </div>
                                <p style="font-size: 12px; line-height: 1.6; color: #2e442c; margin: 0 0 14px 0;">
                                    If you wish to keep your feed active, no action is needed. If you ever need to adjust practice seats, update payment methods, or cancel before the rollover, you have 1-click self-service access anytime:
                                </p>
                                <div style="text-align: center;">
                                    <a href="{STRIPE_PORTAL_URL}" target="_blank" class="btn-cta" style="display: inline-block; background-color: #1b365d; color: #ffffff; text-decoration: none; font-weight: 700; font-size: 13px; padding: 13px 26px; border-radius: 8px; letter-spacing: 0.02em; box-shadow: 0 2px 6px rgba(27,54,93,0.18);">
                                        Open Stripe Subscriber Portal &rarr;
                                    </a>
                                </div>
                            </div>

                            <p style="font-size: 12px; line-height: 1.6; color: #64748b; margin: 16px 0 0 0;">
                                Zero cancellation fees. Zero lock-in contracts. If you have questions or require custom CSV columns for your firm's case management software, simply reply directly to this briefing.
                            </p>

                            <!-- Signature Block -->
                            <div style="margin-top: 26px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #475569;">
                                <strong style="color: #1b365d; font-size: 13px;">Surplus Docket Intelligence</strong><br>
                                <span style="font-size: 12px; color: #64748b;">Court Registry Ingestion Desk</span><br>
                                <a href="https://surplusdocket.com" target="_blank" style="color: #4c6d48; text-decoration: none; font-weight: 600;">surplusdocket.com</a> • <a href="mailto:dockets@surplusdocket.com" style="color: #1b365d; text-decoration: none;">dockets@surplusdocket.com</a>
                            </div>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td class="footer-cell" style="background-color: #f8fafc; padding: 22px 28px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; line-height: 1.6;">
                            <div style="margin-bottom: 8px; font-weight: 600;">
                                <a href="{TOOLKIT_URL}" target="_blank" style="color: #526174; text-decoration: none;">Practitioner Toolkit</a> &nbsp;•&nbsp; 
                                <a href="{STRIPE_PORTAL_URL}" target="_blank" style="color: #1b365d; text-decoration: underline; font-weight: 700;">Subscriber Billing Portal</a>
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


def compose_day10_email(subscriber):
    name = subscriber.get("name", "Counsel")
    firm_suffix = format_firm_suffix(subscriber)
    year = datetime.now().year

    text_body = f"""Dear {name},

Following the conclusion of your recent evaluation of Surplus Docket, our court registry ingestion desk has continued indexing verified tax deed surplus filings across your monitored jurisdictions.

Over the past week alone, dozens of unencumbered surplus files representing millions in recoverable equity have been recorded by county clerks across Florida, Texas, Georgia, California, North Carolina, and Tennessee.

SINGLE-CASE ROI:
In asset recovery practice, securing representation on just one $75,000 unencumbered surplus file yields $15,000 to $18,750 in statutory contingency fees (under state fee caps). A full year of Surplus Docket Core ($249/mo) is covered more than 5x over by a single successful claim.

INSTANT 1-CLICK REACTIVATION:
If you would like to restore daily 7:00 AM EST court feed deliveries with unencumbered CSV and Excel attachments, you can reactivate your practice subscription instantly:
Direct Checkout: {STRIPE_CHECKOUT_URL}
Or via Stripe Billing Portal: {STRIPE_PORTAL_URL}

• Zero setup fees
• No long-term lock-in (month-to-month, cancel anytime)
• Full access to Practitioner Toolkit verified petition motions

Best regards,

Surplus Docket Intelligence
Court Registry Ingestion Desk | Surplus Docket
surplusdocket.com • dockets@surplusdocket.com

---
{LEGAL_DISCLAIMER}
Reactivate Subscription: {STRIPE_CHECKOUT_URL}
"""

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Docket Intelligence Update — Priority Reactivation</title>
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
            background-color: #f8f8f4 !important;
        }}
        .email-wrapper {{
            width: 100% !important;
            background-color: #f8f8f4 !important;
            margin: 0 !important;
            padding: 24px 12px !important;
        }}
        .email-outer-td {{
            padding: 0 !important;
            margin: 0 !important;
        }}
        .email-container {{
            width: 100% !important;
            max-width: 660px !important;
            border-radius: 12px !important;
            border: 1px solid #e2e8f0 !important;
            box-shadow: 0 4px 20px -4px rgba(27,54,93,0.08) !important;
            margin: 0 auto !important;
            background-color: #ffffff !important;
            overflow: hidden !important;
        }}
        @media only screen and (max-width: 640px) {{
            .email-wrapper {{
                padding: 12px 6px !important;
            }}
            .email-container {{
                width: 100% !important;
                max-width: 100% !important;
                border-radius: 10px !important;
            }}
            .content-cell {{
                padding: 22px 18px !important;
            }}
            .header-cell {{
                padding: 16px 18px !important;
            }}
            .nav-cell {{
                padding: 9px 14px !important;
                text-align: center !important;
            }}
            .footer-cell {{
                padding: 20px 16px !important;
            }}
            .header-tag-cell {{
                display: none !important;
            }}
            .btn-cta {{
                display: block !important;
                width: 100% !important;
                box-sizing: border-box !important;
                margin: 8px 0 !important;
                text-align: center !important;
                padding: 14px 16px !important;
                font-size: 13px !important;
                border-radius: 8px !important;
            }}
            .btn-cta-secondary {{
                margin-left: 0 !important;
            }}
        }}
    </style>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8f8f4; margin: 0; padding: 0; color: #1e293b; line-height: 1.5; -webkit-text-size-adjust: 100%;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-wrapper" style="background-color: #f8f8f4; width: 100%; margin: 0; padding: 24px 12px;">
        <tr>
            <td align="center" class="email-outer-td" style="padding: 0; margin: 0;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-container" style="max-width: 660px; width: 100%; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 4px 20px -4px rgba(27,54,93,0.08); margin: 0 auto; overflow: hidden;">
                    <tr>
                        <td class="header-cell" style="background-color: #ffffff; padding: 20px 28px; border-bottom: 2px solid #1b365d;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%;">
                                <tr>
                                    <td align="left" valign="middle" style="padding: 0;">
                                        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td valign="middle" style="padding-right: 14px;">
                                                    <a href="https://surplusdocket.com" target="_blank" style="text-decoration: none; display: block;">
                                                        <img src="{LOGO_URL}" alt="Surplus Docket Crest" width="46" height="36" style="display: block; width: 46px; height: auto; max-height: 38px; border: 0;" />
                                                    </a>
                                                </td>
                                                <td valign="middle" style="line-height: 1.15;">
                                                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-weight: 900; font-size: 22px; letter-spacing: -0.02em; margin: 0;">
                                                        <a href="https://surplusdocket.com" target="_blank" style="text-decoration: none;">
                                                            <span style="color: #4c6d48; font-weight: 800;">SURPLUS</span> <span style="color: #1b365d; font-weight: 900;">DOCKET</span>
                                                        </a>
                                                    </div>
                                                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 10px; font-weight: 700; color: #64748b; letter-spacing: 0.06em; text-transform: uppercase; margin-top: 3px;">
                                                        Court Registry Intelligence
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td align="right" valign="middle" class="header-tag-cell" style="padding: 0;">
                                        <a href="{STRIPE_CHECKOUT_URL}" target="_blank" style="text-decoration: none;">
                                            <span style="display: inline-block; background-color: #edf3ec; color: #365134; border: 1px solid #c2d9c0; font-size: 11px; font-weight: 800; padding: 6px 14px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">
                                                Docket Intelligence Update
                                            </span>
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td class="content-cell" style="padding: 26px 30px; background-color: #ffffff;">
                            <p style="font-size: 15px; margin: 0 0 12px 0; color: #102238;">Dear <b>{name}</b>{firm_suffix},</p>
                            <p style="font-size: 13px; line-height: 1.6; color: #475569; margin: 0 0 20px 0;">
                                Following the conclusion of your evaluation of Surplus Docket, county court registries have recorded hundreds of thousands of dollars in newly unencumbered surplus funds across your target jurisdictions.
                            </p>
                            <div style="background-color: #edf3ec; border: 1px solid #c2d9c0; border-radius: 10px; padding: 18px 20px; margin: 20px 0;">
                                <div style="font-size: 12px; font-weight: 800; color: #365134; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">
                                    ⚖️ Practice Acquisition Economics:
                                </div>
                                <p style="font-size: 12px; color: #2e442c; line-height: 1.6; margin: 0;">
                                    A single verified petition on a typical $75,000 surplus recovery generates <b>$15,000 to $18,750</b> in statutory contingency legal fees. That single resolution covers more than 5 years of Surplus Docket Core subscriptions.
                                </p>
                            </div>
                            <div style="text-align: center; margin: 28px 0 22px 0;">
                                <a href="{STRIPE_CHECKOUT_URL}" target="_blank" class="btn-cta" style="display: inline-block; background-color: #1b365d; color: #ffffff; text-decoration: none; font-weight: 700; font-size: 13px; padding: 13px 26px; border-radius: 8px; letter-spacing: 0.02em; box-shadow: 0 2px 6px rgba(27,54,93,0.18);">
                                    Reactivate Daily Feed ($249/mo) &rarr;
                                </a>
                                <a href="{STRIPE_PORTAL_URL}" target="_blank" class="btn-cta btn-cta-secondary" style="display: inline-block; background-color: #ffffff; color: #1b365d; border: 1.5px solid #1b365d; text-decoration: none; font-weight: 700; font-size: 13px; padding: 12px 22px; border-radius: 8px; letter-spacing: 0.02em; margin-left: 8px;">
                                    Stripe Billing Portal
                                </a>
                            </div>
                            <div style="margin-top: 26px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #475569;">
                                <strong style="color: #1b365d; font-size: 13px;">Surplus Docket Intelligence</strong><br>
                                <span style="font-size: 12px; color: #64748b;">Court Registry Ingestion Desk | Surplus Docket</span><br>
                                <a href="https://surplusdocket.com" target="_blank" style="color: #4c6d48; text-decoration: none; font-weight: 600;">surplusdocket.com</a> • <a href="mailto:dockets@surplusdocket.com" style="color: #1b365d; text-decoration: none;">dockets@surplusdocket.com</a>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td class="footer-cell" style="background-color: #f8fafc; padding: 22px 28px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; line-height: 1.6;">
                            <div style="margin-bottom: 8px; font-weight: 600;">
                                <a href="{TOOLKIT_URL}" target="_blank" style="color: #526174; text-decoration: none;">Practitioner Toolkit</a> &nbsp;•&nbsp; 
                                <a href="{STRIPE_PORTAL_URL}" target="_blank" style="color: #1b365d; text-decoration: underline; font-weight: 700;">Subscriber Billing Portal</a>
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


def send_lifecycle_email(dest, subject, text_body, html_body, is_dry_run=False):
    if is_dry_run:
        print(f"  [DRY RUN] Would send email to: {dest}")
        print(f"            Subject: {subject}")
        return True

    if not GMAIL_APP_PASS:
        print(f"  ⚠️ GMAIL_APP_PASS not set. Skipping send to {dest}")
        return False

    server = None
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASS)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg["To"] = dest
        msg["Reply-To"] = REPLY_TO
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = email.utils.make_msgid(domain="surplusdocket.com")

        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        server.sendmail(GMAIL_USER, [dest], msg.as_string())
        print(f"  ✉️ Successfully dispatched: {subject} to {dest}")
        return True
    except Exception as e:
        print(f"  ❌ Error sending to {dest}: {e}")
        return False
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass


def parse_subscription_date(date_str):
    if not date_str:
        return None
    try:
        dt_str = date_str.replace("Z", "+00:00")
        return datetime.fromisoformat(dt_str)
    except Exception:
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            return None


def run_trial_sentinel(is_dry_run=False, test_recipient=None, force_day=None):
    print("=" * 70)
    print(" 🏛️ SURPLUS DOCKET — INSTITUTIONAL TRIAL RETENTION SENTINEL")
    print("=" * 70)
    print(f"Mode        : {'DRY RUN' if is_dry_run else 'LIVE DISPATCH'}")
    print(f"Sender      : {FROM_NAME} <{FROM_EMAIL}>")
    print(f"Reply-To    : {REPLY_TO}")
    print(f"Log File    : {LIFECYCLE_LOG_FILE.name}")
    print("=" * 70)

    subscribers = []
    if SUBSCRIBERS_FILE.exists():
        try:
            with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as sf:
                subscribers = json.load(sf)
        except Exception as e:
            print(f"❌ Error loading subscribers: {e}")
            return 1

    lifecycle_log = load_lifecycle_log()
    now_utc = datetime.now(timezone.utc)
    processed_count = 0

    if test_recipient:
        subscribers = [{
            "id": "SUB-TEST",
            "email": test_recipient,
            "name": "Counsel",
            "firm": "",
            "tier": "Core Plan (7-Day Evaluation)",
            "status": "ACTIVE",
            "subscribed_at": now_utc.isoformat()
        }]

    for sub in subscribers:
        email_addr = sub.get("email", "").strip().lower()
        status = sub.get("status", "").upper()

        allowed_statuses = ("ACTIVE", "TRIAL", "TRIALING", "EXPIRED_TRIAL", "CANCELLED", "EXPIRED")
        if not email_addr or status not in allowed_statuses:
            continue

        is_active_or_trial = status in ("ACTIVE", "TRIAL", "TRIALING")
        is_lapsed = status in ("EXPIRED_TRIAL", "CANCELLED", "EXPIRED")

        sub_record = lifecycle_log.setdefault(email_addr, {})

        sub_date = parse_subscription_date(sub.get("subscribed_at"))
        if not sub_date:
            continue

        if sub_date.tzinfo is None:
            sub_date = sub_date.replace(tzinfo=timezone.utc)

        days_active = (now_utc - sub_date).total_seconds() / 86400.0

        print(f"\nEvaluating subscriber: {email_addr} (Day {days_active:.1f} of trial, status: {status})")

        # Day 1 Quick-Start Onboarding Trigger
        should_send_day1 = False
        if force_day == 1:
            should_send_day1 = True
        elif not sub_record.get("day_1_sent") and 0.5 <= days_active < 2.5 and is_active_or_trial:
            should_send_day1 = True

        if should_send_day1:
            print(f"  Triggering Day 1 Quick-Start Onboarding for {email_addr}...")
            subject = "[Surplus Docket] Welcome Counsel — Practice Quick-Start & Feed Integration"
            t_body, h_body = compose_day1_email(sub)
            if send_lifecycle_email(email_addr, subject, t_body, h_body, is_dry_run=is_dry_run):
                if not is_dry_run:
                    sub_record["day_1_sent"] = now_utc.isoformat()
                    save_lifecycle_log(lifecycle_log)
                    processed_count += 1

        # Day 3 Statutory Advisory Trigger
        should_send_day3 = False
        if force_day == 3:
            should_send_day3 = True
        elif not sub_record.get("day_3_sent") and 2.5 <= days_active < 5.0 and is_active_or_trial:
            should_send_day3 = True

        if should_send_day3:
            print(f"  Triggering Day 3 Statutory Advisory for {email_addr}...")
            subject = "[Surplus Docket] Practice Advisory — Statutory Claim Windows & Petition Dossiers"
            t_body, h_body = compose_day3_email(sub)
            if send_lifecycle_email(email_addr, subject, t_body, h_body, is_dry_run=is_dry_run):
                if not is_dry_run:
                    sub_record["day_3_sent"] = now_utc.isoformat()
                    save_lifecycle_log(lifecycle_log)
                    processed_count += 1

        # Day 6 Evaluation Trigger (Strictly bounded to trial evaluation window 5.5 to 7.5 days)
        tier_lower = str(sub.get("tier", "")).lower()
        is_trial_tier = "trial" in tier_lower or "evaluation" in tier_lower or "core" in tier_lower
        should_send_day6 = False
        if force_day == 6:
            should_send_day6 = True
        elif not sub_record.get("day_6_sent") and 5.5 <= days_active <= 7.5 and is_trial_tier and is_active_or_trial:
            should_send_day6 = True

        if should_send_day6:
            print(f"  Triggering Day 6 Courtesy Rollover Notice for {email_addr}...")
            subject = "[Surplus Docket] Courtesy Notice — Trial Evaluation Ending Soon (Account Summary)"
            t_body, h_body = compose_day6_email(sub)
            if send_lifecycle_email(email_addr, subject, t_body, h_body, is_dry_run=is_dry_run):
                if not is_dry_run:
                    sub_record["day_6_sent"] = now_utc.isoformat()
                    save_lifecycle_log(lifecycle_log)
                    processed_count += 1

        # Day 10 Win-Back Reactivation Trigger (for expired or cancelled trialists)
        should_send_day10 = False
        if force_day == 10:
            should_send_day10 = True
        elif not sub_record.get("day_10_sent") and 9.0 <= days_active <= 15.0 and is_lapsed:
            should_send_day10 = True

        if should_send_day10:
            print(f"  Triggering Day 10 Win-Back Reactivation for {email_addr}...")
            subject = "[Surplus Docket] Docket Updates in Your Jurisdiction — Priority Reactivation"
            t_body, h_body = compose_day10_email(sub)
            if send_lifecycle_email(email_addr, subject, t_body, h_body, is_dry_run=is_dry_run):
                if not is_dry_run:
                    sub_record["day_10_sent"] = now_utc.isoformat()
                    save_lifecycle_log(lifecycle_log)
                    processed_count += 1

    print(f"\n✅ Sentinel run completed. Dispatches triggered: {processed_count}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Surplus Docket 7-Day Trial Lifecycle Sentinel")
    parser.add_argument("--dry-run", action="store_true", help="Simulate email dispatches without sending")
    parser.add_argument("--send", action="store_true", help="Send live lifecycle emails")
    parser.add_argument("--test-email", type=str, help="Recipient email address for test preview")
    parser.add_argument("--force-day", type=int, choices=[1, 3, 6, 10], help="Force Day 1, Day 3, Day 6, or Day 10 email for testing")

    args = parser.parse_args()
    dry_run = args.dry_run if args.dry_run else (not args.send)

    sys.exit(run_trial_sentinel(
        is_dry_run=dry_run,
        test_recipient=args.test_email,
        force_day=args.force_day
    ))
