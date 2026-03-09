#!/usr/bin/env python3
"""
request_approval.py — human-approval skill script
Creates approval request files and checks their status.
Usage:
  python request_approval.py --create --action "send_email" --details "To: x@y.com"
  python request_approval.py --check --file APPROVAL_2026-03-09_email.md
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
except ImportError:
    pass

VAULT = Path(os.getenv("VAULT_PATH", str(Path(__file__).resolve().parents[3])))
PENDING_DIR = VAULT / "Pending_Approval"


def create_approval(action: str, details: str) -> str:
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = f"APPROVAL_{timestamp}_{action.replace(' ', '_')}.md"
    filepath = PENDING_DIR / filename

    content = f"""---
action: {action}
status: PENDING
requested: {datetime.now().strftime("%Y-%m-%d %H:%M")}
---

# Approval Required: {action}

{details}

---
**To approve:** Replace PENDING with APPROVED above
**To reject:** Replace PENDING with REJECTED above (add reason below)
"""
    filepath.write_text(content, encoding="utf-8")
    print(f"Approval request created: {filepath}")
    print(f"Waiting for human review...")
    return filename


def check_approval(filename: str) -> str:
    filepath = PENDING_DIR / filename
    if not filepath.exists():
        # Check Approved/Rejected folders
        for folder in [VAULT / "Approved", VAULT / "Rejected"]:
            candidate = folder / filename
            if candidate.exists():
                content = candidate.read_text(encoding="utf-8")
                status = "APPROVED" if folder.name == "Approved" else "REJECTED"
                print(f"Status: {status}")
                return status

        print(f"ERROR: File not found: {filename}")
        return "NOT_FOUND"

    content = filepath.read_text(encoding="utf-8")
    if "APPROVED" in content:
        print("Status: APPROVED")
        return "APPROVED"
    elif "REJECTED" in content:
        print("Status: REJECTED")
        return "REJECTED"
    else:
        print("Status: PENDING — waiting for human review")
        return "PENDING"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--create", action="store_true")
    group.add_argument("--check",  action="store_true")
    parser.add_argument("--action",  help="Action name (for --create)")
    parser.add_argument("--details", help="Action details (for --create)")
    parser.add_argument("--file",    help="Approval filename (for --check)")
    args = parser.parse_args()

    if args.create:
        if not args.action or not args.details:
            print("ERROR: --action and --details required with --create")
            sys.exit(1)
        create_approval(args.action, args.details)

    elif args.check:
        if not args.file:
            print("ERROR: --file required with --check")
            sys.exit(1)
        status = check_approval(args.file)
        sys.exit(0 if status == "APPROVED" else 1)
