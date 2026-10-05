#!/usr/bin/env python3
"""
Surplus Docket — Autonomous Link-Building & Tool Promotion Outreach Engine
========================================================================
Automates institutional outreach pitching Surplus Docket's Free Practice Tools Hub
(https://surplusdocket.com/tools.html), embeddable statutory calculator, and Clio/Filevine
CRM schemas to:
1. Law School Legal Clinics & Access-to-Justice Centers (DA 87–93)
2. State & Local Bar Association LPM Advisors & Editors (DA 68–88)
3. LegalTech Bloggers, Columnists & Directory Curators (DA 54–85)
4. Real Estate Investor & Property Rights Communities (DA 48–84)

Zero Local Dependency: Runs headlessly in GitHub Actions or locally in dry-run/live modes.
"""

import argparse
import csv
import email
import email.utils
import json
import os
import re
import smtplib
import sys
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LINK_BUILDING_DIR = BASE_DIR / "marketing" / "link_building"
TARGETS_CSV = LINK_BUILDING_DIR / "tool_outreach_targets.csv"
LOG_CSV = LINK_BUILDING_DIR / "tool_outreach_log.csv"
DRAFTS_DIR = LINK_BUILDING_DIR / "outreach_drafts"
PITCHES_DIR = LINK_BUILDING_DIR / "embed_pitches"
UNSUBSCRIBED_FILE = BASE_DIR / "outreach" / "unsubscribed_urls.json"

# Load optional .env
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

GMAIL_USER = os.getenv("GMAIL_USER", "sandwichfitness@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

DEFAULT_FROM_NAME = os.getenv("TOOL_OUTREACH_FROM_NAME", "Elena Brooks")
DEFAULT_FROM_EMAIL = os.getenv("TOOL_OUTREACH_FROM_EMAIL", "elena.brooks@surplusdocket.com")
DEFAULT_REPLY_TO = os.getenv("TOOL_OUTREACH_REPLY_TO", "elena.brooks@surplusdocket.com")


TOOLS_HUB_URL = "https://surplusdocket.com/tools.html"
CALCULATOR_URL = "https://surplusdocket.com/embed/surplus-calculator.html"
CRM_SCHEMAS_URL = "https://surplusdocket.com/tools.html#crm"
TOOLKIT_URL = "https://surplusdocket.com/practitioner-toolkit.html"


def load_targets(targets_path: Path = TARGETS_CSV) -> List[Dict[str, Any]]:
    """Loads all outreach targets from CSV."""
    if not targets_path.exists():
        return []
    targets = []
    with open(targets_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            targets.append(dict(r))
    return targets


def load_contacted_emails(log_path: Path = LOG_CSV) -> set:
    """Returns set of all email addresses already contacted."""
    if not log_path.exists():
        return set()
    contacted = set()
    with open(log_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            email_addr = r.get("recipient_email", "").strip().lower()
            status = r.get("status", "").strip().upper()
            if email_addr and status in ("SENT", "DELIVERED", "CONFIRMED"):
                contacted.add(email_addr)
    return contacted


def load_unsubscribed_domains() -> set:
    """Loads unsubscribed domains or addresses."""
    if not UNSUBSCRIBED_FILE.exists():
        return set()
    try:
        data = json.loads(UNSUBSCRIBED_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return set(d.lower() for d in data)
        elif isinstance(data, dict):
            return set(data.keys())
    except Exception:
        pass
    return set()


# Known bounced email addresses to suppress from all link-building outreach
BOUNCED_EMAILS = {
    "cpm@ncbar.org",
    "editor@lawyerist.com",
    "contact@legaltechnologyhub.com",
    "editor@lawnext.com",
    "clinics@law.ufl.edu",
    "lawclinics@emory.edu",
    "law_clinics@unc.edu",
}
try:
    from outreach.fix_bounces_and_rebuild import BOUNCED_EMAILS as MASTER_BOUNCED_EMAILS
    BOUNCED_EMAILS.update(e.lower() for e in MASTER_BOUNCED_EMAILS)
except Exception:
    pass


def select_outreach_targets(
    targets: List[Dict[str, Any]],
    limit: int = 5,
    target_type: Optional[str] = None,
    specific_email: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Prioritizes and selects eligible uncontacted targets by DA descending."""
    contacted = load_contacted_emails()
    unsubscribed = load_unsubscribed_domains()

    filtered = []
    for t in targets:
        email_addr = t.get("contact_email", "").strip().lower()
        if not email_addr:
            continue
        status = t.get("status", "").strip().upper()
        if status.startswith("BOUNCED"):
            continue
        if email_addr in BOUNCED_EMAILS:
            continue
        domain = email_addr.split("@")[-1] if "@" in email_addr else ""
        if domain in unsubscribed or email_addr in unsubscribed:
            continue
        if specific_email:
            if email_addr == specific_email.strip().lower():
                filtered.append(t)
                break
            continue

        if email_addr in contacted:
            continue
        if target_type and t.get("target_type", "").strip().lower() != target_type.strip().lower():
            continue

        filtered.append(t)

    # Sort by status (READY_FOR_OUTREACH first) then DA descending
    def sort_key(row: Dict[str, Any]) -> Tuple[int, int]:
        is_ready = 1 if row.get("status", "").strip().upper() == "READY_FOR_OUTREACH" else 0
        da_str = str(row.get("da", "50")).strip()
        da_val = int(da_str) if da_str.isdigit() else 50
        return (is_ready, da_val)

    filtered.sort(key=sort_key, reverse=True)
    return filtered[:limit]


def get_pitch_template_content(target_type: str) -> Tuple[str, str]:
    """Loads markdown pitch template corresponding to target_type."""
    template_map = {
        "law_school_clinic": PITCHES_DIR / "pitch_law_school_clinics.md",
        "bar_association_lpm": PITCHES_DIR / "pitch_bar_association_lpm.md",
        "legaltech_blogger": PITCHES_DIR / "pitch_legaltech_bloggers.md",
        "real_estate_community": PITCHES_DIR / "pitch_real_estate_investors.md",
    }
    path = template_map.get(target_type.strip().lower(), PITCHES_DIR / "pitch_legaltech_bloggers.md")
    if not path.exists():
        subject = "Free Open-Access Statutory Surplus & Court Deadline Calculator"
        body = (
            "Hi {Recipient},\n\nWe recently released a free, zero-tracking statutory surplus deadline calculator "
            "and legal practice tools hub: https://surplusdocket.com/tools.html\n\nBest regards,\nSurplus Docket Editorial Team"
        )
        return subject, body

    raw = path.read_text(encoding="utf-8")
    subject = "Free Open-Access Statutory Surplus & Due Process Tools"
    body = raw

    # Extract subject line if present
    subj_match = re.search(r'\*\*Subject Line:\*\*\s*`([^`]+)`', raw)
    if subj_match:
        subject = subj_match.group(1).strip()

    # Strip header metadata from markdown
    if "---" in raw:
        body = raw.split("---", 1)[-1].strip()

    return subject, body


def build_personalized_email(target: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    Builds personalized subject line, plain text body, and HTML version
    customized to the specific target.
    """
    target_type = target.get("target_type", "legaltech_blogger")
    recipient_name = target.get("name", "Director / Editor").strip()
    org_name = target.get("organization", "your organization").strip()
    jurisdiction = target.get("jurisdiction", "National").strip()

    subject_template, body_template = get_pitch_template_content(target_type)

    # State-specific statutory customization
    statute_citation = "FL § 197.582, TX § 34.04, CA § 4675, GA § 48-4-5, NC § 105-374, and TN § 67-5-2501"
    if jurisdiction == "FL":
        statute_citation = "Fla. Stat. § 197.582 (Tax Deed Surplus) and Fla. Stat. § 45.032 (Judicial Foreclosure Surplus)"
    elif jurisdiction == "TX":
        statute_citation = "Texas Tax Code § 34.04 (District Court Excess Proceeds Claims)"
    elif jurisdiction == "CA":
        statute_citation = "California Revenue & Taxation Code § 4675 (County Board Excess Proceeds Claims)"
    elif jurisdiction == "GA":
        statute_citation = "O.C.G.A. § 48-4-5 (Sheriff & Superior Court Interpleader Distribution)"
    elif jurisdiction == "NC":
        statute_citation = "N.C. Gen. Stat. § 105-374 (Upset Bid & Special Proceedings Distribution)"
    elif jurisdiction == "TN":
        statute_citation = "T.C.A. § 67-5-2501 and § 67-5-2702 (Chancery Court Excess Proceeds Claims)"

    subject = subject_template.replace("{Organization}", org_name).replace("{Jurisdiction}", jurisdiction)
    body = body_template.replace("{Editor / Webmaster}", recipient_name)
    body = body.replace("{Community Lead}", recipient_name)
    body = body.replace("{Editor / Practice Management Advisor}", recipient_name)
    body = body.replace("{Clinical Director & Faculty Advisors}", f"{recipient_name} at {org_name}" if org_name != "your organization" else recipient_name)
    body = body.replace("Dear Clinical Director & Faculty Advisors,", f"Hi {recipient_name},")
    body = body.replace("{Recipient}", recipient_name)
    body = body.replace("{Organization}", org_name)
    body = body.replace("{statute_citation}", statute_citation)

    # Clean, human HTML formatting that mirrors the concise plain text (zero iframes, zero spam walls)
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    html_paragraphs = []
    for p in paragraphs:
        p_html = p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        p_html = re.sub(r'(https?://[^\s<]+)', r'<a href="\1" style="color:#1b365d;">\1</a>', p_html)
        p_html = p_html.replace("\n", "<br>")
        html_paragraphs.append(f"  <p style=\"margin: 0 0 14px 0;\">{p_html}</p>")

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:14px;line-height:1.6;color:#1e293b;max-width:600px;margin:0;padding:16px;">
{chr(10).join(html_paragraphs)}
</body>
</html>"""

    return subject, body, html_body


def send_email_smtp(to_email: str, subject: str, text_body: str, html_body: str) -> Tuple[bool, str]:
    """Sends email via authenticated SMTP server."""
    if not GMAIL_APP_PASS:
        return False, "SMTP credentials (GMAIL_APP_PASS) not configured."

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email.utils.formataddr((DEFAULT_FROM_NAME, DEFAULT_FROM_EMAIL))
    msg["To"] = to_email
    msg["Reply-To"] = DEFAULT_REPLY_TO
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain="surplusdocket.com")

    # Strict Elena Brooks identity & anti-leak sanitization
    text_body = (
        text_body
        .replace("sandwichfitness@gmail.com", "elena.brooks@surplusdocket.com")
        .replace("david@surplusdocket.com", "elena.brooks@surplusdocket.com")
        .replace("Dave Mahler", "Elena Brooks")
        .replace("David Mahler", "Elena Brooks")
    )
    html_body = (
        html_body
        .replace("sandwichfitness@gmail.com", "elena.brooks@surplusdocket.com")
        .replace("david@surplusdocket.com", "elena.brooks@surplusdocket.com")
        .replace("Dave Mahler", "Elena Brooks")
        .replace("David Mahler", "Elena Brooks")
    )

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        envelope_from = GMAIL_USER if ("gmail.com" in SMTP_HOST.lower() and GMAIL_USER) else DEFAULT_FROM_EMAIL
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(GMAIL_USER, GMAIL_APP_PASS)
            server.sendmail(envelope_from, [to_email], msg.as_string())
        return True, msg["Message-ID"]
    except Exception as e:
        return False, str(e)


def save_outreach_draft(target: Dict[str, Any], subject: str, text_body: str, html_body: str) -> Path:
    """Saves formatted .eml and .json draft for review and audit logging."""
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r'[^a-zA-Z0-9_]', '_', target.get("organization", "target").lower())
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    eml_path = DRAFTS_DIR / f"{timestamp}_{slug}.eml"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email.utils.formataddr((DEFAULT_FROM_NAME, DEFAULT_FROM_EMAIL))
    msg["To"] = target.get("contact_email", "")
    msg["Reply-To"] = DEFAULT_REPLY_TO
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain="surplusdocket.com")
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    eml_path.write_bytes(msg.as_bytes())
    return eml_path


def log_outreach_event(
    target: Dict[str, Any],
    subject: str,
    status: str,
    notes: str,
    message_id: str = "",
    log_path: Path = LOG_CSV
):
    """Appends outreach transmission to audit log CSV."""
    file_exists = log_path.exists()
    with open(log_path, "a", encoding="utf-8", newline="") as f:
        fieldnames = [
            "timestamp", "organization", "recipient_name", "recipient_email",
            "target_type", "da", "jurisdiction", "subject", "status", "message_id", "notes"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "organization": target.get("organization", ""),
            "recipient_name": target.get("name", ""),
            "recipient_email": target.get("contact_email", ""),
            "target_type": target.get("target_type", ""),
            "da": target.get("da", ""),
            "jurisdiction": target.get("jurisdiction", ""),
            "subject": subject,
            "status": status,
            "message_id": message_id,
            "notes": notes
        })


def update_target_status(email_addr: str, new_status: str, targets_path: Path = TARGETS_CSV):
    """Updates target status and timestamp in tool_outreach_targets.csv."""
    if not targets_path.exists():
        return
    rows = []
    fieldnames = []
    now_iso = datetime.now(timezone.utc).isoformat()
    with open(targets_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for r in reader:
            if r.get("contact_email", "").strip().lower() == email_addr.strip().lower():
                r["status"] = new_status
                r["last_contacted"] = now_iso
            rows.append(r)
    if fieldnames:
        with open(targets_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def run_tool_outreach_pipeline(
    limit: int = 5,
    live_send: bool = False,
    target_type: Optional[str] = None,
    specific_email: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Executes the autonomous tool outreach pipeline:
    1. Loads target pool and filters out previously contacted entities.
    2. Sorts uncontacted targets by DA descending.
    3. Builds personalized pitch with free tools hub, embed calculator, and CRM schemas.
    4. Dispatches via SMTP (if live_send=True and credentials present) or generates audit drafts.
    5. Logs every action to tool_outreach_log.csv and updates target registry.
    """
    targets = load_targets()
    selected = select_outreach_targets(targets, limit=limit, target_type=target_type, specific_email=specific_email)

    mode_label = "LIVE SMTP DISPATCH" if live_send else "DRY-RUN / DRAFT GENERATION"
    print(f"[*] Starting Autonomous Link-Building Tool Outreach ({len(selected)} targets, mode={mode_label})...")

    results = []
    for t in selected:
        org = t.get("organization", "Unknown")
        email_addr = t.get("contact_email", "")
        da = t.get("da", "?")
        t_type = t.get("target_type", "")
        print(f"  -> Pitching [{t_type}] {org} ({email_addr}, DA {da})...")

        subject, text_body, html_body = build_personalized_email(t)

        if live_send and GMAIL_APP_PASS:
            success, info = send_email_smtp(email_addr, subject, text_body, html_body)
            if success:
                print(f"     ✅ Successfully sent email to {email_addr} (Message-ID: {info})")
                log_outreach_event(t, subject, "SENT", "Live SMTP transmission successful", message_id=info)
                update_target_status(email_addr, "SENT")
                results.append({"organization": org, "email": email_addr, "status": "SENT", "info": info})
            else:
                print(f"     ❌ SMTP send failed ({info}). Saving draft fallback...")
                draft_path = save_outreach_draft(t, subject, text_body, html_body)
                log_outreach_event(t, subject, "SMTP_FAILED_DRAFTED", f"Error: {info}", message_id="")
                update_target_status(email_addr, "DRAFTED")
                results.append({"organization": org, "email": email_addr, "status": "DRAFTED_FALLBACK", "draft": str(draft_path)})
            # Polite pause between SMTP transmissions
            time.sleep(1.5)
        else:
            draft_path = save_outreach_draft(t, subject, text_body, html_body)
            print(f"     📄 Generated audit draft: {draft_path.name}")
            log_outreach_event(t, subject, "DRAFTED_DRY_RUN", "Saved .eml draft in dry-run mode", message_id="")
            update_target_status(email_addr, "DRAFTED")
            results.append({"organization": org, "email": email_addr, "status": "DRAFTED_DRY_RUN", "draft": str(draft_path)})

    print(f"[*] Completed link-building tool outreach. Processed {len(results)} targets.")
    return results


def main():
    parser = argparse.ArgumentParser(description="Surplus Docket Autonomous Tool Outreach Engine")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Generate drafts and logs without live transmission")
    parser.add_argument("--live", dest="dry_run", action="store_false", help="Execute live SMTP transmission")
    parser.add_argument("--limit", type=int, default=5, help="Number of targets to contact in this run")
    parser.add_argument("--target-type", type=str, default=None, choices=["law_school_clinic", "bar_association_lpm", "legaltech_blogger", "real_estate_community"], help="Filter by target vertical")
    parser.add_argument("--email", type=str, default=None, help="Process a specific recipient email")
    args = parser.parse_args()

    run_tool_outreach_pipeline(
        limit=args.limit,
        live_send=not args.dry_run,
        target_type=args.target_type,
        specific_email=args.email
    )


if __name__ == "__main__":
    main()
