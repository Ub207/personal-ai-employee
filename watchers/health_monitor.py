#!/usr/bin/env python3
"""
health_monitor.py — Gold Tier Health Monitor
=============================================
Monitors all AI Employee watcher processes. Auto-restarts dead processes.
Writes health status to vault/health_status.json and updates Dashboard.md.

Usage:
    python health_monitor.py [--vault-path D:/bronze_tier] [--dry-run]

Requirements:
    pip install psutil
"""

import os
import sys
import json
import time
import signal
import logging
import argparse
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict
from typing import Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# ── Constants ─────────────────────────────────────────────────────────────────

CHECK_INTERVAL_SECONDS = 60
MAX_RESTARTS_PER_HOUR = 3
DISABLED_ALERT_PREFIX = "HEALTH_ALERT_"

WATCHED_PROCESSES = [
    {
        "name": "filesystem_watcher",
        "script": "watchers/filesystem_watcher.py",
        "description": "Filesystem change watcher",
    },
    {
        "name": "gmail_imap_watcher",
        "script": "watchers/gmail_imap_watcher.py",
        "description": "Gmail IMAP monitor",
    },
    {
        "name": "whatsapp_watcher",
        "script": "watchers/whatsapp_watcher.py",
        "description": "WhatsApp Web monitor",
    },
    {
        "name": "approval_orchestrator",
        "script": "watchers/approval_orchestrator.py",
        "description": "Approval workflow orchestrator",
    },
    {
        "name": "facebook_instagram_watcher",
        "script": "watchers/facebook_instagram_watcher.py",
        "description": "Facebook & Instagram monitor",
    },
    {
        "name": "twitter_watcher",
        "script": "watchers/twitter_watcher.py",
        "description": "Twitter/X monitor",
    },
]

# ── Argument Parsing ──────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Health monitor for AI Employee watchers")
    parser.add_argument(
        "--vault-path",
        default=os.environ.get("VAULT_PATH", "D:/bronze_tier"),
        help="Path to the vault root directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.environ.get("DRY_RUN", "false").lower() == "true",
        help="Dry run — do not restart processes",
    )
    return parser.parse_args()

# ── Logging Setup ─────────────────────────────────────────────────────────────

def setup_logging(vault_path: Path) -> logging.Logger:
    logs_dir = vault_path / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / "health_monitor.log"
    logger = logging.getLogger("health_monitor")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        fh.setFormatter(fmt)
        ch.setFormatter(fmt)
        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger

# ── PID File Management ───────────────────────────────────────────────────────

def get_pid_file(vault_path: Path, process_name: str) -> Path:
    return vault_path / "vault" / f"{process_name}.pid"

def read_pid(pid_file: Path) -> Optional[int]:
    try:
        return int(pid_file.read_text().strip())
    except (OSError, ValueError):
        return None

def write_pid(pid_file: Path, pid: int) -> None:
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(pid))

def delete_pid(pid_file: Path) -> None:
    try:
        pid_file.unlink()
    except OSError:
        pass

# ── Process Detection ─────────────────────────────────────────────────────────

def is_process_alive(pid: int) -> bool:
    """Check if a process with this PID is running."""
    if not HAS_PSUTIL:
        # Fallback using os.kill signal 0
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False
    try:
        proc = psutil.Process(pid)
        return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False

def find_process_by_script(script_path: str) -> Optional[int]:
    """Find a running Python process by matching its command line."""
    if not HAS_PSUTIL:
        return None
    script_name = Path(script_path).name
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if any(script_name in arg for arg in cmdline):
                return proc.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None

# ── Process Management ────────────────────────────────────────────────────────

def start_process(
    vault_path: Path,
    process_info: dict,
    dry_run: bool,
    logger: logging.Logger,
) -> Optional[int]:
    """Start a watcher process. Returns PID or None on failure."""
    script = vault_path / process_info["script"]
    if not script.exists():
        logger.warning(f"Script not found, cannot start: {script}")
        return None

    cmd = [sys.executable, str(script), "--vault-path", str(vault_path)]

    if dry_run:
        logger.info(f"[DRY RUN] Would start: {' '.join(cmd)}")
        return -1  # Fake PID for dry run

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        pid = proc.pid
        logger.info(f"Started {process_info['name']} (PID {pid})")

        pid_file = get_pid_file(vault_path, process_info["name"])
        write_pid(pid_file, pid)

        return pid
    except Exception as exc:
        logger.error(f"Failed to start {process_info['name']}: {exc}")
        return None

# ── Restart Tracking ──────────────────────────────────────────────────────────

class RestartTracker:
    """Track restart attempts per process per hour."""

    def __init__(self):
        # {process_name: [timestamp, ...]}
        self._restarts: dict[str, list[float]] = defaultdict(list)

    def record_restart(self, name: str) -> None:
        self._restarts[name].append(time.time())

    def restarts_this_hour(self, name: str) -> int:
        cutoff = time.time() - 3600
        recent = [t for t in self._restarts[name] if t > cutoff]
        self._restarts[name] = recent
        return len(recent)

    def can_restart(self, name: str) -> bool:
        return self.restarts_this_hour(name) < MAX_RESTARTS_PER_HOUR

# ── Health Status File ────────────────────────────────────────────────────────

def write_health_status(
    vault_path: Path,
    statuses: list[dict],
    dry_run: bool,
    logger: logging.Logger,
) -> None:
    status_file = vault_path / "vault" / "health_status.json"
    status_file.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "processes": statuses,
        "dry_run": dry_run,
    }

    if dry_run:
        logger.info(f"[DRY RUN] Would write health_status.json")
        return

    try:
        status_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.error(f"Failed to write health_status.json: {exc}")

# ── Dashboard Update ──────────────────────────────────────────────────────────

def update_dashboard_health(
    vault_path: Path,
    statuses: list[dict],
    dry_run: bool,
    logger: logging.Logger,
) -> None:
    dashboard = vault_path / "Dashboard.md"
    if not dashboard.exists():
        return

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Build health table
    table_lines = [
        "",
        "## Watcher Health",
        f"*Last checked: {ts}*",
        "",
        "| Watcher | Status | PID | Restarts (1h) |",
        "|---------|--------|-----|---------------|",
    ]
    for s in statuses:
        icon = "🟢" if s["alive"] else ("🔴" if not s.get("disabled") else "⚫")
        pid_str = str(s.get("pid", "—"))
        restarts = str(s.get("restarts_this_hour", 0))
        table_lines.append(f"| {s['name']} | {icon} {s['status']} | {pid_str} | {restarts} |")

    table_block = "\n".join(table_lines) + "\n"

    try:
        content = dashboard.read_text(encoding="utf-8")

        # Replace existing health block if present
        if "## Watcher Health" in content:
            start = content.find("## Watcher Health")
            # Find the next ## heading after health block
            next_section = content.find("\n## ", start + 1)
            if next_section == -1:
                new_content = content[:start] + table_block
            else:
                new_content = content[:start] + table_block + "\n" + content[next_section:]
        else:
            new_content = content + table_block

        if dry_run:
            logger.info("[DRY RUN] Would update Dashboard.md health table")
            return

        dashboard.write_text(new_content, encoding="utf-8")
    except Exception as exc:
        logger.error(f"Failed to update Dashboard.md: {exc}")

# ── Pending Approval Alert ────────────────────────────────────────────────────

def write_disabled_alert(
    vault_path: Path,
    process_info: dict,
    restarts: int,
    dry_run: bool,
    logger: logging.Logger,
) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{DISABLED_ALERT_PREFIX}{process_info['name']}_{ts}.md"
    pending_dir = vault_path / "Pending_Approval"
    pending_dir.mkdir(parents=True, exist_ok=True)

    content = f"""---
type: health_alert
process: {process_info['name']}
script: {process_info['script']}
restarts_attempted: {restarts}
created: {datetime.now(timezone.utc).isoformat()}
status: pending
priority: critical
---

# Health Alert — Watcher Disabled

**Process:** `{process_info['name']}`
**Description:** {process_info['description']}
**Script:** `{process_info['script']}`

## What Happened

The watcher process `{process_info['name']}` has crashed and been restarted
**{restarts} times** in the past hour, exceeding the maximum of {MAX_RESTARTS_PER_HOUR}.

The health monitor has **disabled automatic restart** for this process to prevent
a crash loop.

## Required Action

1. SSH/RDP into the server
2. Check logs: `Logs/health_monitor.log`
3. Investigate why `{process_info['script']}` is crashing
4. Fix the root cause
5. Restart the watcher manually:
   ```
   python {process_info['script']} --vault-path {vault_path}
   ```
6. Delete this file when resolved

---
*Generated by health_monitor.py at {datetime.now(timezone.utc).isoformat()}*
"""

    alert_file = pending_dir / filename
    if dry_run:
        logger.info(f"[DRY RUN] Would write alert: {alert_file}")
        return

    alert_file.write_text(content, encoding="utf-8")
    logger.warning(f"Disabled alert written: {alert_file}")

# ── Main Monitor Loop ─────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    vault_path = Path(args.vault_path).resolve()
    dry_run = args.dry_run

    logger = setup_logging(vault_path)
    logger.info(f"Health monitor starting. Vault: {vault_path}. Dry run: {dry_run}")
    logger.info(f"Monitoring {len(WATCHED_PROCESSES)} processes every {CHECK_INTERVAL_SECONDS}s")

    if not HAS_PSUTIL:
        logger.warning("psutil not installed. Process detection will be limited. Run: pip install psutil")

    tracker = RestartTracker()
    disabled: set[str] = set()  # names of processes that have been disabled

    # Handle SIGTERM gracefully
    running = True
    def _shutdown(signum, frame):
        nonlocal running
        logger.info("Received shutdown signal. Stopping health monitor.")
        running = False

    signal.signal(signal.SIGTERM, _shutdown)

    while running:
        check_start = time.time()
        statuses = []

        for proc_info in WATCHED_PROCESSES:
            name = proc_info["name"]

            if name in disabled:
                statuses.append({
                    "name": name,
                    "description": proc_info["description"],
                    "alive": False,
                    "status": "disabled",
                    "pid": None,
                    "restarts_this_hour": tracker.restarts_this_hour(name),
                    "disabled": True,
                })
                continue

            # Determine current PID
            pid_file = get_pid_file(vault_path, name)
            pid = read_pid(pid_file)

            alive = False
            if pid is not None and is_process_alive(pid):
                alive = True
            else:
                # PID file missing or stale — try finding by script name
                found_pid = find_process_by_script(proc_info["script"])
                if found_pid:
                    alive = True
                    pid = found_pid
                    if not dry_run:
                        write_pid(pid_file, found_pid)

            if not alive:
                restarts = tracker.restarts_this_hour(name)
                logger.warning(f"{name} is NOT running (restarts this hour: {restarts}/{MAX_RESTARTS_PER_HOUR})")

                if not tracker.can_restart(name):
                    logger.error(f"{name} has exceeded restart limit — DISABLING")
                    disabled.add(name)
                    delete_pid(pid_file)
                    write_disabled_alert(vault_path, proc_info, restarts + 1, dry_run, logger)
                    statuses.append({
                        "name": name,
                        "description": proc_info["description"],
                        "alive": False,
                        "status": "disabled_crash_loop",
                        "pid": None,
                        "restarts_this_hour": restarts,
                        "disabled": True,
                    })
                    continue

                # Attempt restart
                logger.info(f"Attempting to restart {name}…")
                new_pid = start_process(vault_path, proc_info, dry_run, logger)
                tracker.record_restart(name)

                pid = new_pid
                alive = new_pid is not None and new_pid != -1
                status_str = "restarted" if alive else "restart_failed"
                logger.info(f"{name}: {status_str} (PID {new_pid})")
            else:
                status_str = "running"

            statuses.append({
                "name": name,
                "description": proc_info["description"],
                "alive": alive,
                "status": status_str,
                "pid": pid,
                "restarts_this_hour": tracker.restarts_this_hour(name),
                "disabled": False,
            })

        # Write health status file
        write_health_status(vault_path, statuses, dry_run, logger)

        # Update Dashboard.md
        update_dashboard_health(vault_path, statuses, dry_run, logger)

        elapsed = time.time() - check_start
        sleep_time = max(0, CHECK_INTERVAL_SECONDS - elapsed)

        alive_count = sum(1 for s in statuses if s["alive"])
        logger.info(f"Health check complete: {alive_count}/{len(statuses)} alive. Sleeping {sleep_time:.0f}s…")

        time.sleep(sleep_time)

    logger.info("Health monitor stopped.")


if __name__ == "__main__":
    main()
