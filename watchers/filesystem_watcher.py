"""
filesystem_watcher.py — Bronze Tier Watcher
============================================
Monitors the /Inbox folder for new files and creates structured
.md action files in /Needs_Action for Claude Code to process.

Usage:
    python filesystem_watcher.py [--vault-path PATH] [--dry-run]

Requirements:
    pip install watchdog
"""

import os
import sys
import time
import shutil
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("FilesystemWatcher")

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_VAULT = Path(__file__).resolve().parent.parent  # D:/bronze_tier

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


# ── Handler ───────────────────────────────────────────────────────────────────
class InboxHandler(FileSystemEventHandler):
    """Watches /Inbox and creates action files in /Needs_Action."""

    def __init__(self, vault_path: Path, dry_run: bool = False):
        self.vault = vault_path
        self.inbox = vault_path / "Inbox"
        self.needs_action = vault_path / "Needs_Action"
        self.dry_run = dry_run
        self.processed: set[str] = set()

        # Ensure folders exist
        self.needs_action.mkdir(parents=True, exist_ok=True)

    # ── Event handlers ────────────────────────────────────────────────────────

    def on_created(self, event):
        if event.is_directory:
            return
        source = Path(event.src_path)
        if source.suffix.lower() in {".tmp", ".part"}:
            return  # skip system / partial files
        if str(source) in self.processed:
            return

        log.info(f"New file detected: {source.name}")
        self._create_action_file(source)
        self.processed.add(str(source))

    def on_moved(self, event):
        """Handle files moved/renamed into Inbox."""
        dest = Path(event.dest_path)
        if dest.parent == self.inbox and not event.is_directory:
            if str(dest) not in self.processed:
                log.info(f"File moved into Inbox: {dest.name}")
                self._create_action_file(dest)
                self.processed.add(str(dest))

    # ── Core logic ────────────────────────────────────────────────────────────

    def _create_action_file(self, source: Path):
        """Generate a structured .md action file in /Needs_Action."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        safe_name = source.stem.replace(" ", "_")[:50]
        action_filename = f"FILE_{timestamp}_{safe_name}.md"
        action_path = self.needs_action / action_filename

        # Gather file metadata
        try:
            size = source.stat().st_size
            size_str = self._human_size(size)
        except FileNotFoundError:
            size_str = "unknown"

        content = f"""---
type: file_drop
source_file: {source.name}
source_path: {source}
size: {size_str}
detected: {datetime.now().isoformat()}
priority: normal
status: pending
---

## New File Detected in Inbox

**File:** `{source.name}`
**Size:** {size_str}
**Detected:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Suggested Actions

- [ ] Review file contents
- [ ] Categorise (invoice / document / media / other)
- [ ] Move to relevant project folder or archive
- [ ] Update Dashboard.md with activity log entry

## Notes

*(Claude Code — add your analysis and action plan here)*
"""

        if self.dry_run:
            log.info(f"[DRY RUN] Would create: {action_path}")
            log.info(f"[DRY RUN] Content preview:\n{content[:300]}...")
            return

        action_path.write_text(content, encoding="utf-8")
        log.info(f"Action file created: {action_path.name}")
        self._append_dashboard_log(source.name, action_filename)
        self._auto_process(action_path.name)

    def _auto_process(self, action_filename: str):
        """Call Claude CLI to automatically process the new action file."""
        prompt = (
            f"New file detected in Needs_Action: {action_filename}\n"
            f"Please process it according to Company_Handbook.md rules, "
            f"move it to /Done, and update Dashboard.md."
        )
        log.info(f"Calling Claude to auto-process: {action_filename}")
        try:
            subprocess.Popen(
                ["claude", "--print", prompt],
                cwd=str(self.vault),
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
            )
        except Exception as e:
            log.warning(f"Claude auto-process failed: {e}")

    def _append_dashboard_log(self, source_name: str, action_file: str):
        """Append a line to the Recent Activity Log in Dashboard.md."""
        dashboard = self.vault / "Dashboard.md"
        if not dashboard.exists():
            log.warning("Dashboard.md not found — skipping log update.")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        log_line = f"| {timestamp} | File detected in Inbox | {source_name} | → {action_file} |\n"

        text = dashboard.read_text(encoding="utf-8")
        marker = "| 2026-03-04 | System Initialized"

        if marker in text:
            # Insert after the existing log line
            text = text.replace(marker, log_line + marker)
        else:
            # Append to end of activity log section
            text += f"\n{log_line}"

        if not self.dry_run:
            dashboard.write_text(text, encoding="utf-8")

    @staticmethod
    def _human_size(size: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# ── Runner ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Bronze Tier Filesystem Watcher — monitors /Inbox for new files."
    )
    parser.add_argument(
        "--vault-path",
        default=str(DEFAULT_VAULT),
        help=f"Path to Obsidian vault (default: {DEFAULT_VAULT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=DRY_RUN,
        help="Log actions without writing files (safe for testing).",
    )
    args = parser.parse_args()

    vault = Path(args.vault_path).resolve()
    inbox = vault / "Inbox"

    if not vault.exists():
        log.error(f"Vault path does not exist: {vault}")
        sys.exit(1)

    inbox.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("  AI Employee — Filesystem Watcher  (Bronze Tier)")
    log.info("=" * 60)
    log.info(f"  Vault     : {vault}")
    log.info(f"  Watching  : {inbox}")
    log.info(f"  Dry run   : {args.dry_run}")
    log.info("=" * 60)

    handler = InboxHandler(vault_path=vault, dry_run=args.dry_run)
    observer = Observer()
    observer.schedule(handler, str(inbox), recursive=False)
    observer.start()

    log.info("Watcher started. Drop files into /Inbox to trigger actions.")
    log.info("Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Stopping watcher...")
        observer.stop()

    observer.join()
    log.info("Watcher stopped.")


if __name__ == "__main__":
    main()
