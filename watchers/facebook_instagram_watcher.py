#!/usr/bin/env python3
"""
facebook_instagram_watcher.py — Gold Tier Watcher
==================================================
Polls Facebook Page notifications and Instagram Business mentions every 5 minutes.
Creates action files in /Needs_Action/ for relevant messages.

Usage:
    python facebook_instagram_watcher.py [--vault-path D:/bronze_tier] [--dry-run]

Requirements:
    pip install requests
    Set env vars: FB_PAGE_ID, FB_ACCESS_TOKEN, IG_ACCOUNT_ID
"""

import os
import sys
import json
import time
import logging
import argparse
import requests
from datetime import datetime, timezone
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────

POLL_INTERVAL_SECONDS = 300  # 5 minutes
KEYWORDS = {"urgent", "invoice", "payment", "help", "order", "question"}
FB_GRAPH_BASE = "https://graph.facebook.com/v19.0"
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds — exponential: 2, 4, 8

# ── Argument Parsing ──────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Facebook & Instagram watcher for AI Employee")
    parser.add_argument(
        "--vault-path",
        default=os.environ.get("VAULT_PATH", "D:/bronze_tier"),
        help="Path to the vault root directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.environ.get("DRY_RUN", "false").lower() == "true",
        help="Dry run mode — do not write action files",
    )
    return parser.parse_args()

# ── Logging Setup ─────────────────────────────────────────────────────────────

def setup_logging(vault_path: Path) -> logging.Logger:
    logs_dir = vault_path / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / "facebook_instagram_errors.log"
    logger = logging.getLogger("fb_ig_watcher")
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

# ── Retry Helper ──────────────────────────────────────────────────────────────

def with_retry(func, logger: logging.Logger, *args, **kwargs):
    """Call func with exponential backoff retry. Returns result or None on failure."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.Timeout:
            wait = BACKOFF_BASE ** attempt
            logger.warning(f"Timeout on attempt {attempt}/{MAX_RETRIES}. Retrying in {wait}s…")
            time.sleep(wait)
        except requests.exceptions.ConnectionError as exc:
            wait = BACKOFF_BASE ** attempt
            logger.warning(f"Connection error (attempt {attempt}/{MAX_RETRIES}): {exc}. Retrying in {wait}s…")
            time.sleep(wait)
        except Exception as exc:
            logger.error(f"Unrecoverable error: {exc}")
            return None
    logger.error(f"All {MAX_RETRIES} retries exhausted.")
    return None

# ── Graph API Helpers ─────────────────────────────────────────────────────────

def fb_get(endpoint: str, access_token: str, params: dict | None = None) -> dict | None:
    """Perform a GET request to the Facebook Graph API."""
    url = f"{FB_GRAPH_BASE}{endpoint}"
    query = {"access_token": access_token, **(params or {})}
    resp = requests.get(url, params=query, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise ValueError(f"Graph API error: {data['error'].get('message', data['error'])}")
    return data

# ── Keyword Detection ─────────────────────────────────────────────────────────

def contains_keyword(text: str) -> bool:
    """Return True if any tracked keyword appears in text (case-insensitive)."""
    if not text:
        return False
    lower = text.lower()
    return any(kw in lower for kw in KEYWORDS)

# ── Action File Writer ────────────────────────────────────────────────────────

def write_action_file(
    vault_path: Path,
    action_type: str,
    source_id: str,
    sender: str,
    message: str,
    platform: str,
    dry_run: bool,
    logger: logging.Logger,
) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_sender = "".join(c for c in sender if c.isalnum() or c in "-_")[:30]
    filename = f"{platform.upper()}_{ts}_{safe_sender}.md"

    content = f"""---
type: {action_type}
platform: {platform}
source_id: {source_id}
sender: {sender}
received: {datetime.now(timezone.utc).isoformat()}
status: pending
priority: high
---

# {platform.title()} Message — Action Required

**Platform:** {platform.title()}
**From:** {sender}
**Source ID:** {source_id}
**Received:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}

## Message

{message}

## Suggested Actions

- Reply to the message addressing their concern
- If it involves a payment/invoice, cross-reference with Odoo
- If urgent, escalate immediately

---
*Created by facebook_instagram_watcher.py*
"""

    needs_action_dir = vault_path / "Needs_Action"
    needs_action_dir.mkdir(parents=True, exist_ok=True)
    action_file = needs_action_dir / filename

    if dry_run:
        logger.info(f"[DRY RUN] Would write: {action_file}")
        return

    action_file.write_text(content, encoding="utf-8")
    logger.info(f"Created action file: {action_file}")

# ── Dashboard Update ──────────────────────────────────────────────────────────

def update_dashboard(vault_path: Path, event_desc: str, dry_run: bool, logger: logging.Logger) -> None:
    dashboard = vault_path / "Dashboard.md"
    if not dashboard.exists():
        return

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    log_line = f"| {ts} | {event_desc} | facebook_instagram_watcher |\n"

    try:
        content = dashboard.read_text(encoding="utf-8")
        if "## Recent Activity" in content:
            insertion_point = content.find("\n", content.find("## Recent Activity")) + 1
            new_content = content[:insertion_point] + log_line + content[insertion_point:]
        else:
            new_content = content + f"\n## Recent Activity\n{log_line}"

        if dry_run:
            logger.info(f"[DRY RUN] Would update Dashboard.md: {event_desc}")
            return

        dashboard.write_text(new_content, encoding="utf-8")
    except Exception as exc:
        logger.error(f"Failed to update Dashboard.md: {exc}")

# ── Facebook Polling ──────────────────────────────────────────────────────────

def poll_facebook(
    vault_path: Path,
    page_id: str,
    access_token: str,
    since_timestamp: float,
    dry_run: bool,
    logger: logging.Logger,
) -> int:
    """Poll Facebook Page messages/conversations for relevant items. Returns count of new items."""
    new_items = 0

    def fetch_conversations():
        return fb_get(
            f"/{page_id}/conversations",
            access_token,
            params={"fields": "messages{message,from,created_time}", "limit": 25},
        )

    result = with_retry(fetch_conversations, logger)
    if result is None:
        return 0

    conversations = result.get("data", [])

    for convo in conversations:
        messages = convo.get("messages", {}).get("data", [])
        for msg in messages:
            created_str = msg.get("created_time", "")
            if not created_str:
                continue

            try:
                # Facebook returns ISO format with timezone
                msg_time = datetime.fromisoformat(created_str.replace("Z", "+00:00")).timestamp()
            except ValueError:
                continue

            if msg_time <= since_timestamp:
                continue

            text = msg.get("message", "")
            if not contains_keyword(text):
                continue

            sender_info = msg.get("from", {})
            sender = sender_info.get("name", sender_info.get("id", "unknown"))
            source_id = msg.get("id", "")

            logger.info(f"Facebook keyword match from {sender}: {text[:80]}")

            write_action_file(
                vault_path=vault_path,
                action_type="facebook_message",
                source_id=source_id,
                sender=sender,
                message=text,
                platform="facebook",
                dry_run=dry_run,
                logger=logger,
            )

            update_dashboard(
                vault_path,
                f"Facebook message from {sender} — keyword match",
                dry_run,
                logger,
            )
            new_items += 1

    return new_items

# ── Instagram Polling ─────────────────────────────────────────────────────────

def poll_instagram(
    vault_path: Path,
    ig_account_id: str,
    access_token: str,
    since_timestamp: float,
    dry_run: bool,
    logger: logging.Logger,
) -> int:
    """Poll Instagram Business mentions and comments. Returns count of new items."""
    new_items = 0

    def fetch_mentions():
        return fb_get(
            f"/{ig_account_id}/tags",
            access_token,
            params={"fields": "id,text,timestamp,username", "limit": 25},
        )

    result = with_retry(fetch_mentions, logger)
    if result is None:
        return 0

    mentions = result.get("data", [])

    for mention in mentions:
        ts_str = mention.get("timestamp", "")
        if not ts_str:
            continue

        try:
            mention_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
        except ValueError:
            continue

        if mention_time <= since_timestamp:
            continue

        text = mention.get("text", "")
        if not contains_keyword(text):
            continue

        sender = mention.get("username", "unknown")
        source_id = mention.get("id", "")

        logger.info(f"Instagram mention from @{sender}: {text[:80]}")

        write_action_file(
            vault_path=vault_path,
            action_type="instagram_mention",
            source_id=source_id,
            sender=f"@{sender}",
            message=text,
            platform="instagram",
            dry_run=dry_run,
            logger=logger,
        )

        update_dashboard(
            vault_path,
            f"Instagram mention from @{sender} — keyword match",
            dry_run,
            logger,
        )
        new_items += 1

    # Also check Instagram Direct Messages (requires instagram_manage_messages permission)
    def fetch_ig_messages():
        return fb_get(
            f"/{ig_account_id}/conversations",
            access_token,
            params={"fields": "messages{message,from,created_time}", "limit": 25, "platform": "instagram"},
        )

    ig_convos = with_retry(fetch_ig_messages, logger)
    if ig_convos:
        for convo in ig_convos.get("data", []):
            for msg in convo.get("messages", {}).get("data", []):
                ts_str = msg.get("created_time", "")
                if not ts_str:
                    continue
                try:
                    msg_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
                except ValueError:
                    continue

                if msg_time <= since_timestamp:
                    continue

                text = msg.get("message", "")
                if not contains_keyword(text):
                    continue

                sender_info = msg.get("from", {})
                sender = sender_info.get("name", sender_info.get("username", "unknown"))
                source_id = msg.get("id", "")

                logger.info(f"Instagram DM from {sender}: {text[:80]}")
                write_action_file(
                    vault_path=vault_path,
                    action_type="instagram_mention",
                    source_id=source_id,
                    sender=sender,
                    message=text,
                    platform="instagram",
                    dry_run=dry_run,
                    logger=logger,
                )
                new_items += 1

    return new_items

# ── Main Loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    vault_path = Path(args.vault_path).resolve()
    dry_run = args.dry_run

    logger = setup_logging(vault_path)
    logger.info(f"Facebook/Instagram watcher starting. Vault: {vault_path}. Dry run: {dry_run}")

    # Load credentials from environment
    page_id = os.environ.get("FB_PAGE_ID", "")
    access_token = os.environ.get("FB_ACCESS_TOKEN", "")
    ig_account_id = os.environ.get("IG_ACCOUNT_ID", "")

    # Try to load .env from vault root
    env_file = vault_path / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip().strip('"'))
        page_id = os.environ.get("FB_PAGE_ID", page_id)
        access_token = os.environ.get("FB_ACCESS_TOKEN", access_token)
        ig_account_id = os.environ.get("IG_ACCOUNT_ID", ig_account_id)

    if not access_token:
        logger.error("FB_ACCESS_TOKEN not set. Watcher cannot start.")
        sys.exit(1)

    if not page_id:
        logger.warning("FB_PAGE_ID not set. Facebook polling will be skipped.")
    if not ig_account_id:
        logger.warning("IG_ACCOUNT_ID not set. Instagram polling will be skipped.")

    since_timestamp = time.time() - POLL_INTERVAL_SECONDS  # seed: don't replay old messages

    logger.info(f"Polling every {POLL_INTERVAL_SECONDS}s. Keywords: {sorted(KEYWORDS)}")

    while True:
        poll_start = time.time()
        total_new = 0

        try:
            if page_id:
                fb_new = poll_facebook(
                    vault_path=vault_path,
                    page_id=page_id,
                    access_token=access_token,
                    since_timestamp=since_timestamp,
                    dry_run=dry_run,
                    logger=logger,
                )
                total_new += fb_new
                if fb_new:
                    logger.info(f"Facebook: {fb_new} new keyword matches")

            if ig_account_id:
                ig_new = poll_instagram(
                    vault_path=vault_path,
                    ig_account_id=ig_account_id,
                    access_token=access_token,
                    since_timestamp=since_timestamp,
                    dry_run=dry_run,
                    logger=logger,
                )
                total_new += ig_new
                if ig_new:
                    logger.info(f"Instagram: {ig_new} new keyword matches")

        except Exception as exc:
            logger.error(f"Unexpected error in poll loop: {exc}", exc_info=True)

        since_timestamp = poll_start

        elapsed = time.time() - poll_start
        sleep_time = max(0, POLL_INTERVAL_SECONDS - elapsed)
        logger.info(f"Poll complete. Found {total_new} new items. Sleeping {sleep_time:.0f}s…")
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
