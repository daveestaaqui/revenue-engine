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
import html
import urllib.parse
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
DISPATCH_LOG_FILE = BASE_DIR / "portal" / "daily_dispatch_log.json"

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


STATE_NAMES = {"FL": "Florida", "TX": "Texas", "GA": "Georgia", "NC": "North Carolina", "TN": "Tennessee", "CA": "California"}


def get_feed_statistics():
    """Summarize the real master feed. Links come straight from the feed (official source or tested deep link)."""
    stats = {"total_records": 0, "total_surplus": 0.0, "top_dockets": [], "jurisdiction_counts": {}}
    if not MASTER_CSV.exists():
        return stats
    with open(MASTER_CSV, "r", encoding="utf-8", errors="ignore") as f:
        rows = list(csv.DictReader(f))

    def num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    rows.sort(key=lambda r: num(r.get("Surplus_Balance_USD")), reverse=True)
    stats["total_records"] = len(rows)
    stats["total_surplus"] = sum(num(r.get("Surplus_Balance_USD")) for r in rows)
    for r in rows:
        st = (r.get("State") or "").strip().upper()
        if st:
            stats["jurisdiction_counts"][st] = stats["jurisdiction_counts"].get(st, 0) + 1

    # Select top 6 dockets with diversity across active states/counties first,
    # prioritizing records with named owners and direct #search= or case deep links
    def _is_named_deep_docket(r):
        ow = (r.get("Owner_Name") or "").strip()
        vurl = (r.get("Clerk_Verification_URL") or "").strip()
        surl = (r.get("Source_URL") or "").strip()
        days_rem = str(r.get("Days_Remaining_To_Claim") or "").strip()
        urgency = str(r.get("Claim_Urgency_Tier") or "").lower()
        is_expired = days_rem.startswith("-") or "passed" in urgency
        has_named_owner = bool(ow) and "Titleholder of Record" not in ow
        has_deep = ("#search=" in vurl) or (bool(vurl) and vurl != surl)
        return has_named_owner and has_deep and not is_expired

    selected_rows = []
    seen_states = set()
    seen_counties = set()
    # Pass 1: one named deep-linked docket per State (guarantees every active state is represented)
    for r in rows:
        if not _is_named_deep_docket(r):
            continue
        st = (r.get("State") or "").strip()
        ckey = (st, (r.get("County") or "").strip())
        if st not in seen_states:
            seen_states.add(st)
            seen_counties.add(ckey)
            selected_rows.append(r)
        if len(selected_rows) >= 6:
            break
    # Pass 2: one named deep-linked docket per remaining County
    if len(selected_rows) < 6:
        for r in rows:
            if not _is_named_deep_docket(r):
                continue
            ckey = ((r.get("State") or "").strip(), (r.get("County") or "").strip())
            if ckey not in seen_counties and r not in selected_rows:
                seen_counties.add(ckey)
                selected_rows.append(r)
            if len(selected_rows) >= 6:
                break
    # Pass 3: fill any remaining slots
    if len(selected_rows) < 6:
        for r in rows:
            if r not in selected_rows:
                selected_rows.append(r)
            if len(selected_rows) >= 6:
                break
    selected_rows.sort(key=lambda r: num(r.get("Surplus_Balance_USD")), reverse=True)

    for r in selected_rows:
        verify_url = (r.get("Clerk_Verification_URL") or "").strip()
        source_url = (r.get("Source_URL") or "").strip()
        case_no = (r.get("Case_or_TaxDeed_No") or "").strip()
        parcel = (r.get("Parcel_ID") or "").strip()
        stats["top_dockets"].append({
            "docket": case_no or (f"Parcel {parcel}" if parcel else "Listed matter"),
            "raw_identifier": case_no or parcel,
            "owner": (r.get("Owner_Name") or "").strip() or "Owner not published by county",
            "address": (r.get("Property_Address") or "").strip(),
            "amount": num(r.get("Surplus_Balance_USD")),
            "state": (r.get("State") or "").strip(),
            "county": (r.get("County") or "").strip(),
            "statute": (r.get("Governing_Statute") or "").strip(),
            "deadline": (r.get("Claim_Deadline_Date") or "").strip(),
            "clerk_url": verify_url,
            "is_deep_link": ("#search=" in verify_url) or (bool(verify_url) and verify_url != source_url),
            "verify_note": (r.get("Verify_Note") or "").strip(),
            "urgency": (r.get("Claim_Urgency_Tier") or "").strip(),
        })
    return stats


def format_firm_suffix(subscriber):
    raw_firm = (subscriber.get("firm") or "").strip()
    if raw_firm and raw_firm not in ("Surplus Docket Compliance & Research Desk", "Practice", "Legal Practice", "Firm"):
        return f" ({raw_firm})"
    return ""


def compose_email_content(subscriber, stats, date_str):
    from enrichment.processor import build_direct_clerk_url
    name = subscriber.get("name", "Counsel")
    firm_suffix = format_firm_suffix(subscriber)
    total_bal_fmt = f"${stats['total_surplus']:,.2f}"
    rec_count = stats["total_records"]
    year = datetime.now().year
    jurisdiction_counts = stats.get("jurisdiction_counts") or {}
    jurisdictions_line = ", ".join(
        f"{STATE_NAMES.get(st, st)} ({n})" for st, n in sorted(jurisdiction_counts.items(), key=lambda kv: -kv[1])
    ) or "Active Court Registries"

    dockets_text = ""
    dockets_html = ""
    sub_email = (subscriber.get("email") or "").strip().lower()
    for d in stats["top_dockets"]:
        clerk_url = d.get("clerk_url") or build_direct_clerk_url(d.get("county", ""), d.get("state", ""), d.get("docket", ""))
        docket_id_raw = str(d.get("raw_identifier") or d.get("docket", "")).strip()
        import re
        clean_docket_id = re.sub(r"^(parcel|case|apn|docket)\s+", "", docket_id_raw, flags=re.I).strip()
        if clean_docket_id and sub_email:
            from portal.vault_security import build_subscriber_deep_url
            portal_deep_url = build_subscriber_deep_url(
                clean_docket_id, d.get("county", ""), d.get("state", ""), sub_email, date_str
            )
        elif clean_docket_id:
            from portal.vault_security import get_current_vault_key
            vk = get_current_vault_key(date_str)
            portal_deep_url = (
                f"https://surplusdocket.com/docket.html?docket={urllib.parse.quote(clean_docket_id)}&county={urllib.parse.quote(str(d.get('county', '')))}&state={urllib.parse.quote(str(d.get('state', '')))}&k={vk}"
            )
        else:
            portal_deep_url = "https://surplusdocket.com/#live-docket"
        urgency_label = f" [{d['urgency']}]" if d.get("urgency") else ""
        statute_label = f"\n    Statute: {d['statute']}" if d.get("statute") else ""
        link_word = "Registry Verification"
        note = f" ({d['verify_note']})" if d.get("verify_note") else ""
        clerk_label = f"\n    {link_word}: {clerk_url}{note}" if clerk_url else ""
        portal_label = f"\n    Docket Dossier: {portal_deep_url}"
        addr_label = f"\n    Property: {d['address']}" if d.get("address") else ""
        dockets_text += (
            f"• Docket {d['docket']} ({d['county']}, {d['state']}){urgency_label} — ${d['amount']:,.2f}\n"
            f"    Owner: {d['owner']}{addr_label}{statute_label}{portal_label}{clerk_label}\n\n"
        )

        esc_docket = html.escape(str(d.get("docket", "")))
        esc_owner = html.escape(str(d.get("owner", "")))
        esc_address = html.escape(str(d.get("address", "")))
        esc_statute = html.escape(str(d.get("statute", "")))
        esc_state = html.escape(str(d.get("state", "")))
        esc_county = html.escape(str(d.get("county", "")))
        esc_note = html.escape(str(d.get("verify_note", "")))
        esc_clerk_url = html.escape(str(clerk_url or ""), quote=True)
        esc_portal_url = html.escape(str(portal_deep_url), quote=True)

        urgency_val = d.get("urgency", "")
        if "Tier 1" in urgency_val:
            urgency_badge = '<span style="display: inline-block; background-color: #fef2f2; color: #991b1b; border: 1px solid #fecaca; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 6px; font-family: -apple-system, sans-serif;">Tier 1: &lt; 45d Window</span>'
        elif "Tier 2" in urgency_val:
            urgency_badge = '<span style="display: inline-block; background-color: #fffbeb; color: #92400e; border: 1px solid #fde68a; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 6px; font-family: -apple-system, sans-serif;">Tier 2: Priority Window</span>'
        elif "Tier 3" in urgency_val:
            urgency_badge = '<span style="display: inline-block; background-color: #edf3ec; color: #365134; border: 1px solid #c2d9c0; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 6px; font-family: -apple-system, sans-serif;">Tier 3: Active Window</span>'
        else:
            urgency_badge = '<span style="display: inline-block; background-color: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 6px; font-family: -apple-system, sans-serif;">Confirm Window With Clerk</span>'

        statute_markup = f'''
            <span style="display: inline-block; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 11px; font-weight: 600; color: #1b365d; background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 3px 8px; border-radius: 6px; margin-right: 6px;">{esc_statute}</span>
        ''' if esc_statute else ''

        address_markup = f'''
            <div style="color: #64748b; font-size: 12px; margin-top: 3px; line-height: 1.4;">
                <span style="font-size: 10px; text-transform: uppercase; font-weight: 700; color: #94a3b8; letter-spacing: 0.04em;">Property:</span> {esc_address}
            </div>
        ''' if esc_address else ''

        actions_markup = f'''
            <div style="margin-top: 14px;">
                <a href="{esc_portal_url}" target="_blank" class="mobile-btn" style="display: inline-block; background-color: #1b365d; color: #ffffff; font-size: 12px; font-weight: 700; padding: 9px 18px; border-radius: 6px; text-decoration: none; margin-right: 8px; margin-bottom: 6px;">
                    Open Direct Docket Listing &rarr;
                </a>
                {f'<div style="font-size: 11px; color: #64748b; margin-top: 4px;">Verified County Dossier: <a href="{esc_portal_url}" target="_blank" style="color: #365134; font-weight: 600; text-decoration: underline;">Inspect Full Dossier &rarr;</a> &bull; <a href="{esc_clerk_url}" target="_blank" style="color: #64748b; text-decoration: underline;">Clerk Source Reference &nearr;</a>{f" &bull; <span>{esc_note}</span>" if esc_note else ""}</div>' if esc_clerk_url else ""}
            </div>
        '''

        dockets_html += f"""
        <div class="docket-card" style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px 20px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%;">
                <tr>
                    <td align="left" valign="middle" class="mobile-stack" style="padding-bottom: 4px;">
                        <span style="display: inline-block; background-color: #edf3ec; color: #365134; font-size: 11px; font-weight: 800; padding: 3px 8px; border-radius: 6px; border: 1px solid #c2d9c0; margin-right: 8px;">{esc_state} &bull; {esc_county} County</span>
                        <a href="{esc_portal_url}" target="_blank" style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 14px; font-weight: 700; color: #1b365d; text-decoration: none;">{esc_docket}</a>
                    </td>
                    <td align="right" valign="middle" class="mobile-stack mobile-amount" style="padding-bottom: 4px; text-align: right; white-space: nowrap;">
                        <span style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 18px; font-weight: 900; color: #365134;">${d['amount']:,.2f}</span>
                    </td>
                </tr>
                <tr>
                    <td colspan="2" style="font-size: 13px; color: #334155; line-height: 1.5; padding-top: 6px;">
                        <div style="font-size: 14px; font-weight: 700; color: #0f172a;">
                            {esc_owner}
                        </div>
                        {address_markup}
                        <div style="margin-top: 8px;">
                            {statute_markup}
                            {urgency_badge}
                        </div>
                        {actions_markup}
                    </td>
                </tr>
            </table>
        </div>
        """

    text_body = f"""BENCHMARK SUMMARY ({date_str}):
• Active Verified Records: {rec_count} files
• Total Listed Surplus: {total_bal_fmt}
• Jurisdictions in Today's Feed: {jurisdictions_line}

FEATURED COURT DOCKETS:
{dockets_text}ATTACHED COURT INTELLIGENCE FILES:
• Master_Surplus_Lead_Feed.csv ({rec_count} files formatted for case management intake)
• Master_Surplus_Lead_Feed.xlsx (Structured spreadsheet with claim deadlines and fee calculations)

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
    <title>Surplus Docket — Daily Court Intelligence Feed</title>
    <style type="text/css">
        body, table, td, p, a, li {{
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
        }}
        table, td {{
            mso-table-lspace: 0pt;
            mso-table-rspace: 0pt;
        }}
        body {{
            margin: 0 !important;
            padding: 0 !important;
            background-color: #ffffff !important;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            color: #1e293b;
            line-height: 1.5;
        }}
        .email-outer {{
            width: 100% !important;
            min-width: 100% !important;
            background-color: #ffffff !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        .content-cell {{
            padding: 32px 24px !important;
            max-width: 600px !important;
            margin: 0 auto !important;
            display: block !important;
            background-color: #ffffff !important;
        }}
        @media only screen and (max-width: 600px) {{
            .content-cell {{
                padding: 20px 14px !important;
                max-width: 100% !important;
            }}
            .docket-card {{
                padding: 16px 14px !important;
            }}
            .mobile-stack {{
                display: block !important;
                width: 100% !important;
                text-align: left !important;
            }}
            .mobile-amount {{
                margin-top: 6px !important;
            }}
            .mobile-btn {{
                display: block !important;
                width: 100% !important;
                text-align: center !important;
                box-sizing: border-box !important;
                padding: 10px 14px !important;
            }}
            .stat-box {{
                display: block !important;
                width: 100% !important;
                margin-bottom: 10px !important;
            }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; color: #1e293b; line-height: 1.5;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-outer" style="width: 100%; min-width: 100%; background-color: #ffffff; margin: 0; padding: 0;">
        <tr>
            <td align="center" class="content-cell" style="padding: 32px 24px; max-width: 600px; margin: 0 auto; display: block; background-color: #ffffff;">

                <!-- Website-Matched Brand Header (Clean, Pure White, Zero Clutter) -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%; margin-bottom: 20px;">
                    <tr>
                        <td align="left" valign="middle">
                            <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td valign="middle" style="padding-right: 12px;">
                                        <a href="https://surplusdocket.com" target="_blank" style="text-decoration: none; display: block;">
                                            <img src="https://surplusdocket.com/assets/logo_surplus_docket.png" alt="Surplus Docket" width="40" height="30" style="display: block; width: 40px; height: auto; border: 0;" />
                                        </a>
                                    </td>
                                    <td valign="middle">
                                        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-weight: 900; font-size: 22px; letter-spacing: -0.02em; line-height: 1.1;">
                                            <a href="https://surplusdocket.com" target="_blank" style="text-decoration: none;">
                                                <span style="color: #4c6d48; font-weight: 800;">SURPLUS</span> <span style="color: #1b365d; font-weight: 900;">DOCKET</span>
                                            </a>
                                        </div>
                                        <div style="font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.04em; text-transform: uppercase; margin-top: 3px;">
                                            Court Registry Intelligence &bull; {date_str}
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>

                <!-- Crisp 2-Stat Dynamic Pulse (Matching Website Header Cards) -->
                <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 18px; margin-bottom: 22px;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%;">
                        <tr>
                            <td width="50%" align="left" valign="top" class="stat-box" style="padding-right: 12px;">
                                <div style="font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Audited Surplus Pool</div>
                                <div style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 20px; font-weight: 900; color: #365134; margin-top: 2px;">{total_bal_fmt}</div>
                            </td>
                            <td width="50%" align="left" valign="top" class="stat-box" style="padding-left: 12px; border-left: 1px solid #e2e8f0;">
                                <div style="font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Actionable Dockets</div>
                                <div style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 20px; font-weight: 900; color: #1b365d; margin-top: 2px;">{rec_count} Files Active</div>
                            </td>
                        </tr>
                    </table>
                </div>

                <!-- Priority Matters Section Heading -->
                <div style="text-align: left; margin-bottom: 12px;">
                    <div style="font-size: 12px; font-weight: 800; color: #1b365d; text-transform: uppercase; letter-spacing: 0.06em;">
                        Top Matters From Official County Lists
                    </div>
                </div>

                <!-- Card List -->
                {dockets_html}

                <!-- Direct Web Portal & Attachments Access Bar -->
                <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px 20px; margin-top: 20px; text-align: left;">
                    <div style="font-size: 13px; font-weight: 700; color: #0f172a; margin-bottom: 4px;">
                        Complete Intake Datasets Attached
                    </div>
                    <div style="font-size: 12px; color: #64748b; line-height: 1.5; margin-bottom: 14px;">
                        Full unencumbered court dockets ({rec_count} records) are attached in CSV and Excel workbooks with calculated claim deadlines.
                    </div>
                    <div>
                        <a href="https://surplusdocket.com/#live-docket" target="_blank" class="mobile-btn" style="display: inline-block; background-color: #4c6d48; color: #ffffff; font-size: 13px; font-weight: 700; padding: 10px 20px; border-radius: 8px; text-decoration: none;">
                            Open Live Web Docket &rarr;
                        </a>
                    </div>
                </div>

                <!-- Clean Minimal Footer -->
                <div style="margin-top: 28px; padding-top: 18px; border-top: 1px solid #f1f5f9; text-align: center; font-size: 11px; color: #94a3b8; line-height: 1.5;">
                    <div style="color: #64748b; font-weight: 600; margin-bottom: 4px;">
                        Surplus Docket Intelligence &bull; Court Registry Ingestion Desk
                    </div>
                    <div>
                        <a href="https://surplusdocket.com" target="_blank" style="color: #1b365d; text-decoration: none;">surplusdocket.com</a> &bull; <a href="mailto:dockets@surplusdocket.com" style="color: #1b365d; text-decoration: none;">dockets@surplusdocket.com</a>
                    </div>
                    <div style="margin-top: 8px; font-size: 10px; color: #cbd5e1;">
                        {LEGAL_DISCLAIMER} &bull; &copy; {year} Surplus Docket
                    </div>
                </div>

            </td>
        </tr>
    </table>
</body>
</html>
"""
    return text_body, html_body


def dispatch_feed(is_dry_run=False, recipient_override=None, force=False):
    print("=" * 70)
    print(" 🚀 SURPLUS DOCKET — 7:00 AM EST MORNING SUBSCRIBER DISPATCH")
    print("=" * 70)
    print(f"Mode           : {'DRY RUN (Preview Only)' if is_dry_run else 'LIVE SMTP DISPATCH'}")
    print(f"From Sender    : {FROM_NAME} <{FROM_EMAIL}>")
    # Ensure any recent Stripe checkout subscribers are ingested before loading
    if not is_dry_run and not recipient_override:
        try:
            from portal.sync_stripe_subscribers import run_sync
            run_sync()
        except Exception as sync_err:
            print(f"Notice during Stripe subscriber sync: {sync_err}")

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

    try:
        from zoneinfo import ZoneInfo
        now_et = datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        now_et = datetime.now()

    date_key = now_et.strftime("%Y-%m-%d")
    date_str = now_et.strftime("%B %d, %Y")
    subject = f"[Surplus Docket] Daily Morning Court Intelligence Feed — {date_str}"

    # 1. Delivery Window Guard: Morning feed is delivered Mon-Fri in the 7:00 AM - 9:59 AM Eastern Time window.
    # Tolerates GitHub Actions schedule queue delays while strictly blocking early morning (< 7:00 AM), afternoon (>= 10:00 AM), and weekend sends.
    is_weekday = now_et.weekday() < 5
    in_morning_window = is_weekday and (7 <= now_et.hour < 10)
    if not is_dry_run and not recipient_override and not force and not in_morning_window:
        print(f"ℹ️ Delivery Window Guard: Current time is {now_et.strftime('%A %I:%M %p %Z')}.")
        print("   Morning court intelligence feeds are strictly dispatched Mon–Fri between 7:00 AM and 10:00 AM ET.")
        print("   Aborting live dispatch to prevent premature or off-hours delivery. Use --force to override.")
        return 0

    # 2. Idempotency check: if not forcing and not overriding recipient, avoid duplicate same-day dispatches
    if not is_dry_run and not recipient_override and not force and DISPATCH_LOG_FILE.exists():
        try:
            with open(DISPATCH_LOG_FILE, "r", encoding="utf-8") as f:
                log_data = json.load(f)
            if log_data.get("last_dispatched_date") == date_key and log_data.get("status") == "SUCCESS":
                print(f"ℹ️ Morning feed for {date_str} ({date_key}) has ALREADY been dispatched (at {log_data.get('timestamp')}).")
                print("   Skipping duplicate dispatch to prevent inbox spam. Use --force to override.")
                return 0
        except Exception as log_err:
            print(f"Notice reading dispatch log: {log_err}")

    stats = get_feed_statistics()

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
        if not is_dry_run and not recipient_override and sent_count > 0:
            try:
                log_entry = {
                    "last_dispatched_date": date_key,
                    "timestamp": now_et.isoformat(),
                    "sent_count": sent_count,
                    "recipients": [s.get("email") for s in subscribers],
                    "status": "SUCCESS"
                }
                with open(DISPATCH_LOG_FILE, "w", encoding="utf-8") as f:
                    json.dump(log_entry, f, indent=2)
                print(f"✓ Recorded successful morning dispatch in {DISPATCH_LOG_FILE.name}")
            except Exception as we:
                print(f"Notice saving dispatch log: {we}")
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
    esc_name = html.escape(str(name))
    esc_firm_suffix = html.escape(str(firm_suffix))
    total_bal_fmt = f"${stats['total_surplus']:,.2f}"
    rec_count = stats["total_records"]
    year = datetime.now().year

    text_body = f"""Welcome {name},

Your 7-day institutional practice evaluation with Surplus Docket is active for {date_str} under $0 due today.

For the next 7 days, your practice has full access to daily 7:00 AM EST court record feeds indexing verified tax deed surplus and excess proceeds from covered county registries in Florida, Texas, Georgia, Tennessee, and California.

STARTER DATA WORKBOOKS (ATTACHED):
• Master_Surplus_Lead_Feed.csv ({rec_count} files, {total_bal_fmt} total listed surplus)
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
        @media only screen and (max-width: 680px) {{
            .email-wrapper {{ padding: 12px 6px !important; }}
            .email-container {{ width: 100% !important; max-width: 100% !important; border-radius: 10px !important; }}
            .content-cell {{ padding: 22px 18px !important; }}
            .header-cell {{ padding: 16px 18px !important; }}
            .nav-cell {{ padding: 9px 14px !important; }}
            .header-tag-cell {{ display: none !important; }}
            .deliverables-table td {{ display: block !important; width: 100% !important; box-sizing: border-box !important; margin-bottom: 8px !important; }}
            .deliverables-spacer {{ display: none !important; }}
            .btn-cta {{ display: block !important; width: 100% !important; box-sizing: border-box !important; margin: 8px 0 !important; text-align: center !important; padding: 14px 16px !important; font-size: 13px !important; border-radius: 8px !important; }}
        }}
    </style>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8f8f4; margin: 0; padding: 0; color: #1e293b; line-height: 1.5; -webkit-text-size-adjust: 100%;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-wrapper" style="background-color: #f8f8f4; width: 100%; margin: 0; padding: 24px 12px;">
        <tr>
            <td align="center" class="email-outer-td" style="padding: 0; margin: 0;">
                <!-- Main Card Container -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-container" style="max-width: 660px; width: 100%; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 4px 20px -4px rgba(27,54,93,0.08); margin: 0 auto; overflow: hidden;">
                    
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
                            <p style="font-size: 15px; margin: 0 0 12px 0; color: #102238;">Welcome <b>{esc_name}</b>{esc_firm_suffix},</p>
                            <p style="font-size: 13px; line-height: 1.6; color: #475569; margin: 0 0 20px 0;">
                                Your 7-day institutional practice evaluation is active. For the next 7 days, your firm has full access to verified court registry intelligence from covered counties across Florida, Texas, Georgia, Tennessee, and California, complete with direct source document links, statutory claim windows, and preliminary encumbrance review flags.
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
                                                Today's complete indexed files ({rec_count} verified dockets, {total_bal_fmt} total listed surplus) are attached to this transmission:
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
                        <td style="background-color: #f8fafc; padding: 22px 28px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; line-height: 1.6;">
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
    parser.add_argument("--force", action="store_true", help="Force dispatch even if already sent today")
    args = parser.parse_args()

    if args.welcome:
        target = {"email": args.recipient or "david@surplusdocket.com", "name": "Counsel", "firm": ""}
        sys.exit(0 if dispatch_activation_starter_kit(target, is_dry_run=args.dry_run) else 1)

    if not args.send and not args.dry_run:
        args.dry_run = True

    sys.exit(dispatch_feed(is_dry_run=args.dry_run, recipient_override=args.recipient, force=args.force))

