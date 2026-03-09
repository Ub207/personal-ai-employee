#!/usr/bin/env python3
"""
csv_drop_watcher.py — Silver Tier CSV/Invoice Drop Watcher
===========================================================
Monitors /DropBox folder for new CSV or PDF files.
When detected, copies to /Needs_Action/ and creates a metadata .md file.

Usage:
    python watchers/csv_drop_watcher.py [--vault-path D:/bronze_tier]
"""

import os
import sys
import time
import shutil
import logging
import argparse
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("CSVDropWatcher")

SUPPORTED_EXTENSIONS = {".csv", ".pdf", ".xlsx", ".xls"}
CHECK_INTERVAL = 10  # seconds


def process_file(file_path: Path, needs_action: Path, dry_run: bool):
    """Copy dropped file to Needs_Action and create metadata markdown."""
    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        log.info(f"Ignored (unsupported type): {file_path.name}")
        return

    dest_name = f"DROP_{file_path.name}"
    dest_path = needs_action / dest_name

    if dest_path.exists():
        return  # Already processed

    if dry_run:
        log.info(f"[DRY RUN] Would copy: {file_path.name} -> Needs_Action/{dest_name}")
        return

    try:
        shutil.copy2(file_path, dest_path)
        log.info(f"Copied: {file_path.name} -> Needs_Action/{dest_name}")

        # Create metadata markdown
        meta_path = needs_action / (dest_name + ".md")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        size_kb = round(file_path.stat().st_size / 1024, 1)

        content = f"""---
type: drop_file
original_name: {file_path.name}
size_kb: {size_kb}
created: {now}
priority: medium
status: NEEDS_REVIEW
---

# Drop File: {file_path.name}

New **{file_path.suffix.upper()}** file detected in /DropBox and queued for processing.

## File Info
- **Name:** `{file_path.name}`
- **Size:** {size_kb} KB
- **Type:** {file_path.suffix.upper()}
- **Detected:** {now}

## Suggested Actions
- [ ] Review file content
- [ ] Extract and summarize data
- [ ] Create invoice entry if applicable
- [ ] Move to /Done when complete
"""
        meta_path.write_text(content, encoding="utf-8")
        log.info(f"Metadata created: {meta_path.name}")

    except Exception as e:
        log.error(f"Error processing {file_path.name}: {e}")


def run(vault_path: Path, dry_run: bool):
    dropbox = vault_path / "DropBox"
    needs_action = vault_path / "Needs_Action"

    dropbox.mkdir(parents=True, exist_ok=True)
    needs_action.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("  AI Employee - CSV Drop Watcher  (Silver Tier)")
    log.info("=" * 60)
    log.info(f"  Vault     : {vault_path}")
    log.info(f"  Watching  : {dropbox}")
    log.info(f"  Dry run   : {dry_run}")
    log.info("=" * 60)
    log.info("Watcher started. Drop CSV/PDF files into /DropBox to trigger.")
    log.info("Press Ctrl+C to stop.\n")

    processed = set()

    while True:
        try:
            for item in dropbox.iterdir():
                if item.is_file() and item.name not in processed:
                    process_file(item, needs_action, dry_run)
                    processed.add(item.name)
        except Exception as e:
            log.error(f"Watcher loop error: {e}")

        time.sleep(CHECK_INTERVAL)


def main():
    parser = argparse.ArgumentParser(description="Silver Tier CSV Drop Watcher")
    parser.add_argument("--vault-path", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--dry-run", action="store_true",
                        default=os.getenv("DRY_RUN", "false").lower() == "true")
    args = parser.parse_args()

    vault = Path(args.vault_path).resolve()
    if not vault.exists():
        log.error(f"Vault not found: {vault}")
        sys.exit(1)

    run(vault, args.dry_run)


if __name__ == "__main__":
    main()
