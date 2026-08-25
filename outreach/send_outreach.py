#!/usr/bin/env python3
"""
Surplus Docket - Automated Cold Email Outreach System
=====================================================
Reads target attorney profiles from CSV, populates personalized email templates,
and outputs individual plain-text email files (dry-run mode by default).
Includes an SMTP sending function and logging tracker.
"""

import os
import sys
import csv
import re
import smtplib
import argparse
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Base directory setup
BASE_DIR = Path(__file__).resolve().parent
TARGETS_CSV = BASE_DIR / "attorney_targets.csv"
TEMPLATES_MD = BASE_DIR / "email_templates.md"
GENERATED_DIR = BASE_DIR / "generated_emails"
SENT_LOG_CSV = BASE_DIR / "sent_log.csv"

# State mapping for natural email phrasing
STATE_NAMES = {
    "FL": "Florida",
    "TX": "Texas",
    "GA": "Georgia",
    "NC": "North Carolina",
    "TN": "Tennessee",
    "CA": "California",
}

# Stripe checkout links by state / tier
STRIPE_LINKS = {
    "FL": "https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X",
    "TX": "https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X",
    "DEFAULT": "https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X",
}


def load_template(templates_path: Path, template_number: int = 1) -> tuple[str, str]:
    """
    Parses email_templates.md and extracts the subject line and body text
    for the specified template number (default: Template 1).
    """
    if not templates_path.exists():
        raise FileNotFoundError(f"Template file not found: {templates_path}")

    content = templates_path.read_text(encoding="utf-8")

    # Split by markdown template headers
    template_pattern = re.compile(
        rf"##\s*Template\s*{template_number}:[^\n]*\n+"
        r"(?:\*\*Subject:\*\*\s*(?P<subject>[^\n]+)\n+)?"
        r"(?P<body>.*?)"
        r"(?=\n---|\n##\s*Template|\Z)",
        re.DOTALL | re.IGNORECASE,
    )

    match = template_pattern.search(content)
    if not match:
        raise ValueError(f"Could not find Template {template_number} in {templates_path}")

    subject = match.group("subject").strip() if match.group("subject") else "Surplus Docket Data Feed"
    body = match.group("body").strip()

    return subject, body


def read_targets(csv_path: Path) -> list[dict]:
    """Reads recipient attorney records from the CSV file."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Target CSV file not found: {csv_path}")

    targets = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean_row = {}
            for k, v in row.items():
                if k:
                    clean_row[k.strip()] = v.strip() if v else ""
            if clean_row.get("Email"):
                targets.append(clean_row)
    return targets


def personalize_text(text: str, target: dict) -> str:
    """
    Substitutes merge fields in email subject or body text:
    {{name}}, {{firm}}, {{state}}, {{stripe_link}}
    """
    raw_state = target.get("State", "").upper()
    state_display = STATE_NAMES.get(raw_state, raw_state)
    stripe_link = STRIPE_LINKS.get(raw_state, STRIPE_LINKS["DEFAULT"])

    replacements = {
        "{{name}}": target.get("Name", "Counsel"),
        "{{firm}}": target.get("Firm", "your firm"),
        "{{state}}": state_display,
        "{{stripe_link}}": stripe_link,
    }

    result = text
    for tag, value in replacements.items():
        result = result.replace(tag, value)

    return result


def send_email_smtp(to_email: str, subject: str, body_text: str) -> bool:
    """
    Placeholder SMTP email dispatcher.

    ========================================================================
    HOW TO CONFIGURE LIVE SMTP SENDING:
    ========================================================================
    1. Gmail App Password:
       - Enable 2-Step Verification on your Google Account.
       - Go to: https://myaccount.google.com/apppasswords
       - Create an App Password for 'Mail'.
       - Set environment variables:
           export SMTP_HOST="smtp.gmail.com"
           export SMTP_PORT="587"
           export SMTP_USER="your-email@gmail.com"
           export SMTP_PASS="your-16-character-app-password"
           export FROM_EMAIL="your-email@gmail.com"

    2. SendGrid / Mailgun / AWS SES:
       - Set SMTP_HOST="smtp.sendgrid.net", SMTP_PORT="587"
       - Set SMTP_USER="apikey", SMTP_PASS="your_api_key"
       - Set FROM_EMAIL="verified-sender@yourdomain.com"
    ========================================================================
    """
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    from_email = os.getenv("FROM_EMAIL", smtp_user)

    if not smtp_user or not smtp_pass:
        print(f"  [!] SMTP credentials not set. Set SMTP_USER and SMTP_PASS env vars to send live email to {to_email}")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body_text, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        print(f"  [✓] Live email dispatched via SMTP to: {to_email}")
        return True
    except Exception as e:
        print(f"  [✗] Failed to send email to {to_email}: {e}")
        return False


def log_sent_status(log_path: Path, entry: dict):
    """Logs generation/send status to CSV log tracker."""
    fieldnames = ["Timestamp", "Email", "Name", "Firm", "State", "Subject", "Status", "Mode", "Output_File"]
    file_exists = log_path.exists()

    with open(log_path, mode="a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(entry)


def run_outreach(dry_run: bool = True, template_idx: int = 1, limit: int = None):
    """
    Main orchestration routine for generating and dispatching outreach emails.
    """
    print("=" * 70)
    print(f" 📨 SURPLUS INTEL - OUTREACH AUTOMATION SYSTEM (Template #{template_idx})")
    print(f"    Mode: {'🔍 DRY-RUN (File Generation Only)' if dry_run else '🚀 LIVE SENDING (SMTP)'}")
    print("=" * 70)

    # 1. Load template
    subject_tpl, body_tpl = load_template(TEMPLATES_MD, template_number=template_idx)
    print(f"Loaded Template #{template_idx}:")
    print(f"  Subject Pattern: {subject_tpl}\n")

    # 2. Read targets
    targets = read_targets(TARGETS_CSV)
    if limit:
        targets = targets[:limit]
    print(f"Found {len(targets)} recipient targets in: {TARGETS_CSV.name}\n")

    # 3. Prepare output directory
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    generated_count = 0
    sent_count = 0

    # 4. Process each target
    for i, target in enumerate(targets, 1):
        email = target["Email"]
        name = target["Name"]
        firm = target["Firm"]
        state = target["State"]

        # Personalize subject and body
        personalized_subject = personalize_text(subject_tpl, target)
        personalized_body = personalize_text(body_tpl, target)

        # Build clean plain-text output file
        safe_filename = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", email) + ".txt"
        output_file = GENERATED_DIR / safe_filename

        file_content = (
            f"To: {email}\n"
            f"Recipient Name: {name}\n"
            f"Firm: {firm}\n"
            f"State: {state} ({STATE_NAMES.get(state, state)})\n"
            f"Subject: {personalized_subject}\n"
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            + "=" * 70 + "\n\n"
            f"{personalized_body}\n"
        )

        output_file.write_text(file_content, encoding="utf-8")
        generated_count += 1

        if dry_run:
            status = "GENERATED (DRY_RUN)"
            print(f"[{i:02d}/{len(targets):02d}] Generated: {output_file.name} -> {firm} ({email})")
            log_sent_status(SENT_LOG_CSV, {
                "Timestamp": datetime.now().isoformat(),
                "Email": email,
                "Name": name,
                "Firm": firm,
                "State": state,
                "Subject": personalized_subject,
                "Status": status,
                "Mode": "dry-run",
                "Output_File": str(output_file.name),
            })
        else:
            # Live SMTP send mode
            success = send_email_smtp(email, personalized_subject, personalized_body)
            status = "SENT" if success else "FAILED"
            if success:
                sent_count += 1
            log_sent_status(SENT_LOG_CSV, {
                "Timestamp": datetime.now().isoformat(),
                "Email": email,
                "Name": name,
                "Firm": firm,
                "State": state,
                "Subject": personalized_subject,
                "Status": status,
                "Mode": "live",
                "Output_File": str(output_file.name),
            })

    print("\n" + "=" * 70)
    print(" 📊 OUTREACH EXECUTION SUMMARY")
    print("=" * 70)
    print(f"  • Total Targets Processed : {len(targets)}")
    print(f"  • Email Files Generated  : {generated_count} in {GENERATED_DIR}")
    if not dry_run:
        print(f"  • Emails Dispatched Live : {sent_count}")
    print(f"  • Activity Log Updated   : {SENT_LOG_CSV}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Surplus Docket Outreach Automation")
    parser.add_argument(
        "--send", "--live",
        action="store_true",
        help="Perform live SMTP sending (default is dry-run mode)."
    )
    parser.add_argument(
        "--template",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="Email template number to use (1, 2, or 3. Default: 1)."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of emails to generate/send."
    )

    args = parser.parse_args()
    is_dry_run = not args.send

    run_outreach(dry_run=is_dry_run, template_idx=args.template, limit=args.limit)


if __name__ == "__main__":
    main()
