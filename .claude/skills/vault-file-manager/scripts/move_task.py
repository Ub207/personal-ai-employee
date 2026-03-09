#!/usr/bin/env python3
"""
move_task.py — vault-file-manager skill script
Moves task files between vault workflow folders.
Usage: python move_task.py --operation inbox-to-action --filename task.md
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
except ImportError:
    pass

VAULT = Path(os.getenv("VAULT_PATH", str(Path(__file__).resolve().parents[3])))

FOLDERS = {
    "inbox":    VAULT / "Inbox",
    "action":   VAULT / "Needs_Action",
    "approval": VAULT / "Pending_Approval",
    "approved": VAULT / "Approved",
    "rejected": VAULT / "Rejected",
    "done":     VAULT / "Done",
}

OPERATIONS = {
    "inbox-to-action":    ("inbox",    "action"),
    "action-to-approval": ("action",   "approval"),
    "approve":            ("approved", "done"),
    "reject":             ("rejected", "done"),
    "complete":           (None,       "done"),
}


def move_task(operation: str, filename: str) -> bool:
    if operation not in OPERATIONS:
        print(f"ERROR: Unknown operation '{operation}'. Choose from: {list(OPERATIONS.keys())}")
        return False

    src_key, dst_key = OPERATIONS[operation]

    dst_folder = FOLDERS[dst_key]
    dst_folder.mkdir(parents=True, exist_ok=True)

    # Find source file
    if src_key:
        src_file = FOLDERS[src_key] / filename
    else:
        # Search all folders
        src_file = None
        for folder in FOLDERS.values():
            candidate = folder / filename
            if candidate.exists():
                src_file = candidate
                break
        if not src_file:
            print(f"ERROR: File '{filename}' not found in any vault folder.")
            return False

    if not src_file.exists():
        print(f"ERROR: Source file not found: {src_file}")
        return False

    dst_file = dst_folder / filename
    shutil.move(str(src_file), str(dst_file))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {operation}: {src_file.parent.name}/{filename} -> {dst_folder.name}/{filename}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", required=True, choices=list(OPERATIONS.keys()))
    parser.add_argument("--filename",  required=True, help="Filename to move")
    args = parser.parse_args()

    success = move_task(args.operation, args.filename)
    sys.exit(0 if success else 1)
