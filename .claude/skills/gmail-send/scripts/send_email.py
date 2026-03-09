#!/usr/bin/env python3
"""
send_email.py — gmail-send skill script
Sends an email via Gmail SMTP using credentials from .env
Usage: python send_email.py --to EMAIL --subject SUBJECT --body BODY
"""

import os
import sys
import smtplib
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
except ImportError:
    pass

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
DRY_RUN   = os.getenv("DRY_RUN", "true").lower() == "true"


def send_email(to: str, subject: str, body: str) -> bool:
    if not SMTP_USER or not SMTP_PASS:
        print("ERROR: SMTP_USER or SMTP_PASS not set in .env")
        return False

    if DRY_RUN:
        print(f"[DRY RUN] Would send email:")
        print(f"  To:      {to}")
        print(f"  Subject: {subject}")
        print(f"  Body:    {body[:100]}...")
        return True

    msg = MIMEMultipart()
    msg["From"]    = SMTP_USER
    msg["To"]      = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, to, msg.as_string())

    print(f"Email sent to {to} — Subject: {subject}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--to",      required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body",    required=True)
    args = parser.parse_args()

    success = send_email(args.to, args.subject, args.body)
    sys.exit(0 if success else 1)
