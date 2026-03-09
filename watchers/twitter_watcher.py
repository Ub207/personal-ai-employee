#!/usr/bin/env python3
"""
twitter_watcher.py — Gold Tier Watcher
=======================================
Polls Twitter/X mentions and DMs every 5 minutes using Twitter API v2.
Creates action files in /Needs_Action/ for relevant messages.

Usage:
    python twitter_watcher.py [--vault-path D:/bronze_tier] [--dry-run]

Requirements:
    pip install requests
    Set env vars: TWITTER_BEARER_TOKEN, TWITTER_API_KEY, TWITTER_API_SECRET,
                  TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
"""

import os
import sys
import json
import time
import hmac
import base64
import hashlib
import logging
import argparse
import urllib.parse
import secrets
import requests
from datetime import datetime, timezone
from pathlib import Path

# Load .env file before reading any environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass  # python-dotenv not installed; rely on shell env

# ── Constants ─────────────────────────────────────────────────────────────────

POLL_INTERVAL_SECONDS = 300  # 5 minutes
KEYWORDS = {"urgent", "invoice", "help", "question"}
TWITTER_API_BASE = "https://api.twitter.com/2"
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds — exponential: 2, 4, 8

# ── Argument Parsing ──────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Twitter/X watcher for AI Employee")
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

    log_file = logs_dir / "twitter_errors.log"
    logger = logging.getLogger("twitter_watcher")
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
            logger.warning(f"Timeout (attempt {attempt}/{MAX_RETRIES}). Retrying in {wait}s…")
            time.sleep(wait)
        except requests.exceptions.ConnectionError as exc:
            wait = BACKOFF_BASE ** attempt
            logger.warning(f"Connection error (attempt {attempt}/{MAX_RETRIES}): {exc}. Retrying in {wait}s…")
            time.sleep(wait)
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            if status == 429:
                # Rate limited — back off longer
                retry_after = int(exc.response.headers.get("retry-after", 60))
                logger.warning(f"Rate limited. Waiting {retry_after}s…")
                time.sleep(retry_after)
            elif status in (500, 502, 503, 504):
                wait = BACKOFF_BASE ** attempt * 5
                logger.warning(f"Twitter server error {status} (attempt {attempt}/{MAX_RETRIES}). Retrying in {wait}s…")
                time.sleep(wait)
            else:
                logger.error(f"HTTP {status}: {exc}")
                return None
        except Exception as exc:
            logger.error(f"Unrecoverable error: {exc}")
            return None
    logger.error(f"All {MAX_RETRIES} retries exhausted.")
    return None

# ── OAuth 1.0a for Twitter ────────────────────────────────────────────────────

def _percent_encode(s: str) -> str:
    return urllib.parse.quote(str(s), safe="")

def build_oauth1_header(
    method: str,
    url: str,
    api_key: str,
    api_secret: str,
    access_token: str,
    access_secret: str,
    extra_params: dict | None = None,
) -> str:
    """Build OAuth 1.0a Authorization header for Twitter API."""
    oauth_params = {
        "oauth_consumer_key": api_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }

    all_params = {**oauth_params, **(extra_params or {})}
    sorted_params = sorted(all_params.items())
    param_string = "&".join(f"{_percent_encode(k)}={_percent_encode(v)}" for k, v in sorted_params)

    signature_base = "&".join([
        method.upper(),
        _percent_encode(url),
        _percent_encode(param_string),
    ])

    signing_key = f"{_percent_encode(api_secret)}&{_percent_encode(access_secret)}"
    raw_signature = hmac.new(signing_key.encode("utf-8"), signature_base.encode("utf-8"), hashlib.sha1).digest()
    signature = base64.b64encode(raw_signature).decode("utf-8")

    oauth_params["oauth_signature"] = signature
    header_parts = ", ".join(
        f'{_percent_encode(k)}="{_percent_encode(v)}"'
        for k, v in sorted(oauth_params.items())
    )
    return f"OAuth {header_parts}"

# ── Twitter API Helpers ───────────────────────────────────────────────────────

class TwitterClient:
    """Minimal Twitter API v2 client using requests (no tweepy dependency)."""

    def __init__(
        self,
        bearer_token: str,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_secret: str,
    ):
        self.bearer_token = bearer_token
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_secret = access_secret
        self._authenticated_user_id: str | None = None

    def _bearer_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.bearer_token}"}

    def _oauth1_headers(self, method: str, url: str, params: dict | None = None) -> dict:
        auth = build_oauth1_header(
            method=method,
            url=url,
            api_key=self.api_key,
            api_secret=self.api_secret,
            access_token=self.access_token,
            access_secret=self.access_secret,
            extra_params=params,
        )
        return {"Authorization": auth, "Content-Type": "application/json"}

    def get_me(self) -> dict:
        """Get authenticated user info (requires OAuth 1.0a user context)."""
        url = f"{TWITTER_API_BASE}/users/me"
        resp = requests.get(url, headers=self._oauth1_headers("GET", url), timeout=30)
        resp.raise_for_status()
        return resp.json().get("data", {})

    def get_mentions(self, user_id: str, since_id: str | None = None) -> list[dict]:
        """Get mentions timeline for the authenticated user."""
        url = f"{TWITTER_API_BASE}/users/{user_id}/mentions"
        params = {
            "tweet.fields": "created_at,author_id,text",
            "expansions": "author_id",
            "user.fields": "username,name",
            "max_results": 100,
        }
        if since_id:
            params["since_id"] = since_id

        resp = requests.get(url, headers=self._bearer_headers(), params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        tweets = data.get("data", [])
        users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

        # Annotate tweets with author username
        for tweet in tweets:
            author_id = tweet.get("author_id", "")
            author = users.get(author_id, {})
            tweet["author_username"] = author.get("username", "unknown")
            tweet["author_name"] = author.get("name", "Unknown")

        return tweets

    def get_dms(self) -> list[dict]:
        """Get recent Direct Messages (requires dm.read OAuth 1.0a scope)."""
        url = f"{TWITTER_API_BASE}/dm_conversations/with-participant/events"
        # Note: DM endpoint requires OAuth 1.0a user context
        # Use the simpler /dm_events endpoint if available
        params = {"dm_event.fields": "created_at,text,sender_id", "max_results": 50}

        headers = self._oauth1_headers("GET", url)
        resp = requests.get(url, headers=headers, params=params, timeout=30)

        if resp.status_code == 403:
            # DM access requires elevated permissions; skip gracefully
            return []
        resp.raise_for_status()
        return resp.json().get("data", [])

# ── Keyword Detection ─────────────────────────────────────────────────────────

def contains_keyword(text: str) -> bool:
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
    tweet_url: str,
    dry_run: bool,
    logger: logging.Logger,
) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_sender = "".join(c for c in sender if c.isalnum() or c in "-_@")[:30].lstrip("@")
    filename = f"TWITTER_{ts}_{safe_sender}.md"

    content = f"""---
type: {action_type}
platform: twitter
source_id: {source_id}
sender: {sender}
tweet_url: {tweet_url}
received: {datetime.now(timezone.utc).isoformat()}
status: pending
priority: high
---

# Twitter — Action Required

**Platform:** Twitter/X
**From:** {sender}
**Type:** {action_type.replace("_", " ").title()}
**Tweet URL:** {tweet_url}

## Message

{message}

## Suggested Actions

- Reply to acknowledge within business hours
- If invoice/payment query, check Odoo for related records
- If urgent, respond immediately via social-mcp post_to_twitter tool

---
*Created by twitter_watcher.py*
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
    log_line = f"| {ts} | {event_desc} | twitter_watcher |\n"

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

# ── Main Loop ─────────────────────────────────────────────────────────────────

def load_state(vault_path: Path) -> dict:
    state_file = vault_path / "vault" / "twitter_watcher_state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except Exception:
            pass
    return {"last_mention_id": None}

def save_state(vault_path: Path, state: dict) -> None:
    state_dir = vault_path / "vault"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "twitter_watcher_state.json"
    state_file.write_text(json.dumps(state, indent=2))

def main() -> None:
    args = parse_args()
    vault_path = Path(args.vault_path).resolve()
    dry_run = args.dry_run

    logger = setup_logging(vault_path)
    logger.info(f"Twitter watcher starting. Vault: {vault_path}. Dry run: {dry_run}")

    # Load credentials (env first, then .env file)
    env_file = vault_path / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip().strip('"'))

    bearer_token = os.environ.get("TWITTER_BEARER_TOKEN", "")
    api_key = os.environ.get("TWITTER_API_KEY", "")
    api_secret = os.environ.get("TWITTER_API_SECRET", "")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN", "")
    access_secret = os.environ.get("TWITTER_ACCESS_SECRET", "")

    if not bearer_token:
        logger.error("TWITTER_BEARER_TOKEN not set. Watcher cannot start.")
        sys.exit(1)

    client = TwitterClient(
        bearer_token=bearer_token,
        api_key=api_key,
        api_secret=api_secret,
        access_token=access_token,
        access_secret=access_secret,
    )

    # Get authenticated user ID
    def get_user():
        return client.get_me()

    me = with_retry(get_user, logger)
    if not me:
        logger.error("Failed to authenticate with Twitter. Check credentials.")
        sys.exit(1)

    user_id = me.get("id", "")
    username = me.get("username", "")
    logger.info(f"Authenticated as @{username} (ID: {user_id})")

    state = load_state(vault_path)
    logger.info(f"Polling every {POLL_INTERVAL_SECONDS}s. Keywords: {sorted(KEYWORDS)}")

    while True:
        poll_start = time.time()
        total_new = 0

        # ── Poll Mentions ────────────────────────────────────────────────────
        try:
            def fetch_mentions():
                return client.get_mentions(user_id, since_id=state.get("last_mention_id"))

            mentions = with_retry(fetch_mentions, logger) or []

            if mentions:
                # Update since_id to the newest tweet
                state["last_mention_id"] = mentions[0]["id"]

            for tweet in mentions:
                text = tweet.get("text", "")
                if not contains_keyword(text):
                    continue

                tweet_id = tweet.get("id", "")
                author = f"@{tweet.get('author_username', 'unknown')}"
                tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"

                logger.info(f"Mention keyword match from {author}: {text[:80]}")

                write_action_file(
                    vault_path=vault_path,
                    action_type="twitter_mention",
                    source_id=tweet_id,
                    sender=author,
                    message=text,
                    tweet_url=tweet_url,
                    dry_run=dry_run,
                    logger=logger,
                )

                update_dashboard(
                    vault_path,
                    f"Twitter mention from {author} — keyword match",
                    dry_run,
                    logger,
                )
                total_new += 1

        except Exception as exc:
            logger.error(f"Error polling mentions: {exc}", exc_info=True)

        # ── Poll DMs ─────────────────────────────────────────────────────────
        if api_key and access_token:
            try:
                def fetch_dms():
                    return client.get_dms()

                dms = with_retry(fetch_dms, logger) or []

                for dm in dms:
                    text = dm.get("text", "")
                    if not contains_keyword(text):
                        continue

                    dm_id = dm.get("id", "")
                    sender_id = dm.get("sender_id", "unknown")

                    logger.info(f"DM keyword match from user {sender_id}: {text[:80]}")

                    write_action_file(
                        vault_path=vault_path,
                        action_type="twitter_dm",
                        source_id=dm_id,
                        sender=f"user_{sender_id}",
                        message=text,
                        tweet_url=f"https://twitter.com/messages/{sender_id}",
                        dry_run=dry_run,
                        logger=logger,
                    )

                    update_dashboard(
                        vault_path,
                        f"Twitter DM from user {sender_id} — keyword match",
                        dry_run,
                        logger,
                    )
                    total_new += 1

            except Exception as exc:
                logger.error(f"Error polling DMs: {exc}", exc_info=True)

        # ── Save State and Sleep ─────────────────────────────────────────────
        try:
            if not dry_run:
                save_state(vault_path, state)
        except Exception as exc:
            logger.warning(f"Could not save watcher state: {exc}")

        elapsed = time.time() - poll_start
        sleep_time = max(0, POLL_INTERVAL_SECONDS - elapsed)
        logger.info(f"Poll complete. Found {total_new} new items. Sleeping {sleep_time:.0f}s…")
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
