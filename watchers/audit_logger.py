#!/usr/bin/env python3
"""
audit_logger.py — Gold Tier Audit Module
=========================================
Thread-safe audit logging for all AI Employee components.
Writes daily JSON log files, rotates after 30 days.

Usage as module:
    from audit_logger import AuditLogger
    logger = AuditLogger(vault_path="D:/bronze_tier")
    logger.log_action("email_sent", {"to": "user@example.com"}, "success", "gmail_watcher")

Usage standalone:
    python audit_logger.py [--vault-path D:/bronze_tier]
    Generates audit report to /Briefings/
"""

import os
import sys
import json
import argparse
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

try:
    from filelock import FileLock, Timeout as FileLockTimeout
    HAS_FILELOCK = True
except ImportError:
    HAS_FILELOCK = False
    # Fallback: use threading lock only (same process safety but not cross-process)


# ── AuditLogger Class ─────────────────────────────────────────────────────────

class AuditLogger:
    """
    Thread-safe audit logger. Writes to Logs/audit_{YYYY-MM-DD}.json.
    Automatically rotates logs older than 30 days.
    """

    LOG_RETENTION_DAYS = 30
    _thread_lock = threading.Lock()

    def __init__(self, vault_path: str | Path = "D:/bronze_tier"):
        self.vault_path = Path(vault_path).resolve()
        self.logs_dir = self.vault_path / "Logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    # ── Private Helpers ────────────────────────────────────────────────────────

    def _today_log_file(self) -> Path:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.logs_dir / f"audit_{date_str}.json"

    def _log_file_for_date(self, date: datetime) -> Path:
        return self.logs_dir / f"audit_{date.strftime('%Y-%m-%d')}.json"

    def _read_log(self, log_file: Path) -> list[dict]:
        if not log_file.exists():
            return []
        try:
            content = log_file.read_text(encoding="utf-8").strip()
            if not content:
                return []
            return json.loads(content)
        except (json.JSONDecodeError, OSError):
            return []

    def _write_log(self, log_file: Path, entries: list[dict]) -> None:
        log_file.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")

    def _append_entry(self, entry: dict) -> None:
        """Thread-safe + file-lock-safe append to today's log file."""
        log_file = self._today_log_file()
        lock_file = Path(str(log_file) + ".lock")

        with AuditLogger._thread_lock:
            if HAS_FILELOCK:
                try:
                    with FileLock(str(lock_file), timeout=10):
                        entries = self._read_log(log_file)
                        entries.append(entry)
                        self._write_log(log_file, entries)
                except FileLockTimeout:
                    # Fallback: write without file lock (still has thread lock)
                    entries = self._read_log(log_file)
                    entries.append(entry)
                    self._write_log(log_file, entries)
            else:
                entries = self._read_log(log_file)
                entries.append(entry)
                self._write_log(log_file, entries)

    def _rotate_old_logs(self) -> int:
        """Remove log files older than LOG_RETENTION_DAYS. Returns count removed."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.LOG_RETENTION_DAYS)
        removed = 0
        for log_file in self.logs_dir.glob("audit_*.json"):
            # Parse date from filename: audit_YYYY-MM-DD.json
            try:
                date_part = log_file.stem.replace("audit_", "")
                file_date = datetime.strptime(date_part, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if file_date < cutoff:
                    log_file.unlink()
                    removed += 1
            except ValueError:
                pass  # Skip files that don't match the pattern
        return removed

    # ── Public API ─────────────────────────────────────────────────────────────

    def log_action(
        self,
        action_type: str,
        details: dict[str, Any],
        result: str,
        source: str,
    ) -> None:
        """
        Log a completed action.

        Args:
            action_type: Short identifier like "email_sent", "invoice_created"
            details:     Arbitrary context dict (recipient, amount, etc.)
            result:      "success", "failed", "dry_run", "skipped"
            source:      Component name: "gmail_watcher", "approval_orchestrator", etc.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "action",
            "action_type": action_type,
            "source": source,
            "result": result,
            "details": details,
        }
        self._append_entry(entry)

    def log_error(
        self,
        component: str,
        error: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Log an error event.

        Args:
            component: Which watcher/module failed
            error:     Error message or exception string
            context:   Optional additional context dict
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "error",
            "component": component,
            "error": error,
            "context": context or {},
        }
        self._append_entry(entry)

    def get_recent_actions(self, hours: int = 24) -> list[dict]:
        """
        Return all audit entries from the last N hours, across log files.

        Args:
            hours: Lookback window in hours (default 24)

        Returns:
            List of entry dicts, sorted oldest-first.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        entries = []

        # Determine which log files to check (may span multiple days)
        days_to_check = min((hours // 24) + 2, self.LOG_RETENTION_DAYS)
        for day_offset in range(days_to_check):
            check_date = datetime.now(timezone.utc) - timedelta(days=day_offset)
            log_file = self._log_file_for_date(check_date)
            for entry in self._read_log(log_file):
                try:
                    ts = datetime.fromisoformat(entry["timestamp"])
                    if ts >= cutoff:
                        entries.append(entry)
                except (KeyError, ValueError):
                    pass

        entries.sort(key=lambda e: e.get("timestamp", ""))
        return entries

    def generate_audit_report(self, hours: int = 168) -> str:
        """
        Generate a Markdown audit report for the last N hours (default: 168 = 7 days).

        Returns:
            Markdown string suitable for saving to /Briefings/
        """
        entries = self.get_recent_actions(hours)
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=hours)

        # Aggregate stats
        by_type: dict[str, int] = {}
        by_source: dict[str, int] = {}
        errors: list[dict] = []
        successes = 0
        failures = 0

        for entry in entries:
            if entry.get("event") == "error":
                errors.append(entry)
                failures += 1
            elif entry.get("event") == "action":
                action_type = entry.get("action_type", "unknown")
                source = entry.get("source", "unknown")
                result = entry.get("result", "unknown")
                by_type[action_type] = by_type.get(action_type, 0) + 1
                by_source[source] = by_source.get(source, 0) + 1
                if result == "success":
                    successes += 1
                elif result in ("failed", "error"):
                    failures += 1

        total = len(entries)
        error_rate = f"{(failures / total * 100):.1f}%" if total > 0 else "0%"

        lines = [
            "---",
            f"generated: {now.isoformat()}",
            f"period: {since.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}",
            "type: audit_report",
            "---",
            "",
            f"# AI Employee Audit Report",
            f"**Period:** {since.strftime('%Y-%m-%d %H:%M UTC')} → {now.strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "## Summary",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Events | {total} |",
            f"| Successful Actions | {successes} |",
            f"| Errors / Failures | {failures} |",
            f"| Error Rate | {error_rate} |",
            "",
            "## Actions by Type",
            "| Action Type | Count |",
            "|-------------|-------|",
        ]

        for action_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
            lines.append(f"| {action_type} | {count} |")

        lines += [
            "",
            "## Actions by Component",
            "| Component | Events |",
            "|-----------|--------|",
        ]
        for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
            lines.append(f"| {source} | {count} |")

        lines += ["", "## Recent Errors"]
        if errors:
            lines += [
                "| Timestamp | Component | Error |",
                "|-----------|-----------|-------|",
            ]
            for err in errors[-20:]:  # last 20 errors
                ts = err.get("timestamp", "")[:19].replace("T", " ")
                component = err.get("component", "unknown")
                error_msg = str(err.get("error", ""))[:80]
                lines.append(f"| {ts} | {component} | {error_msg} |")
        else:
            lines.append("No errors recorded in this period. ✅")

        lines += [
            "",
            "---",
            "*Generated by audit_logger.py*",
        ]

        return "\n".join(lines)

    def cleanup_old_logs(self) -> int:
        """Remove audit logs older than LOG_RETENTION_DAYS. Returns count deleted."""
        return self._rotate_old_logs()


# ── Standalone CLI ────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Logger — generate audit report")
    parser.add_argument(
        "--vault-path",
        default=os.environ.get("VAULT_PATH", "D:/bronze_tier"),
        help="Path to the vault root directory",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=168,
        help="Lookback hours for report (default: 168 = 7 days)",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove audit logs older than 30 days",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    vault_path = Path(args.vault_path).resolve()

    audit = AuditLogger(vault_path=vault_path)

    if args.cleanup:
        removed = audit.cleanup_old_logs()
        print(f"Cleaned up {removed} old audit log files.")

    # Generate report
    report = audit.generate_audit_report(hours=args.hours)

    # Save to Briefings/
    briefings_dir = vault_path / "Briefings"
    briefings_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_file = briefings_dir / f"{date_str}_Audit_Report.md"
    report_file.write_text(report, encoding="utf-8")

    print(f"Audit report written to: {report_file}")
    # Print safely on Windows consoles that don't support full Unicode
    safe_report = report.encode("ascii", errors="replace").decode("ascii")
    print(f"\n{safe_report}")


if __name__ == "__main__":
    main()
