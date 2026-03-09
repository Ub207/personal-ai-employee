#!/usr/bin/env python3
"""
run_ai_employee.py — AI Employee Automatic Scheduler
=====================================================
Runs the AI Employee task-planner every 5 minutes.
Checks Inbox for new tasks and processes them automatically.

Usage:
    python scripts/run_ai_employee.py

Windows Task Scheduler (run once at startup):
    Action: python D:\bronze_tier\scripts\run_ai_employee.py
    Trigger: At startup, repeat every 5 minutes

Linux/Mac cron (every 5 minutes):
    */5 * * * * /usr/bin/python3 /path/to/scripts/run_ai_employee.py
"""

import os
import sys
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

VAULT = Path(os.getenv("VAULT_PATH", str(Path(__file__).resolve().parent.parent)))
INBOX = VAULT / "Inbox"
NEEDS_ACTION = VAULT / "Needs_Action"
CHECK_INTERVAL = 300  # 5 minutes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(VAULT / "Logs" / "scheduler.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("AIEmployee")


def check_inbox() -> list[Path]:
    """Return list of unprocessed files in Inbox."""
    if not INBOX.exists():
        return []
    return [f for f in INBOX.iterdir() if f.suffix in (".md", ".txt")]


def process_task(task_file: Path):
    """Move task to Needs_Action and log it."""
    dest = NEEDS_ACTION / task_file.name
    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)
    task_file.rename(dest)
    log.info(f"Task queued: {task_file.name} -> Needs_Action/")


def run_cycle():
    tasks = check_inbox()
    if not tasks:
        log.info("Inbox clear — nothing to process.")
        return

    log.info(f"Found {len(tasks)} new task(s) in Inbox.")
    for task in tasks:
        try:
            process_task(task)
        except Exception as e:
            log.error(f"Failed to process {task.name}: {e}")


def main():
    (VAULT / "Logs").mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("  AI Employee Scheduler — Starting")
    log.info(f"  Vault:    {VAULT}")
    log.info(f"  Interval: {CHECK_INTERVAL}s (every 5 minutes)")
    log.info("=" * 60)

    while True:
        try:
            run_cycle()
        except Exception as e:
            log.error(f"Scheduler error: {e}")

        log.info(f"Sleeping {CHECK_INTERVAL}s until next check...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
