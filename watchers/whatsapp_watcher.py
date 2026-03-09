"""
whatsapp_watcher.py — Silver Tier Watcher
==========================================
Monitors WhatsApp Web for new messages containing priority keywords.
Creates structured .md action files in /Needs_Action for Claude Code.

Uses Playwright for browser automation of WhatsApp Web.

Usage:
    python whatsapp_watcher.py [--vault-path PATH] [--dry-run]

Requirements:
    pip install playwright
    playwright install chromium

Setup:
    1. Install: pip install playwright
    2. Install browser: playwright install chromium
    3. First run: Scan QR code on WhatsApp Web manually
    4. Session saved to: ~/.whatsapp_session/

Note: Be aware of WhatsApp's Terms of Service. Use at your own risk.
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("WhatsAppWatcher")

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_VAULT = Path(__file__).resolve().parent.parent  # D:/bronze_tier

SESSION_PATH = Path.home() / ".whatsapp_session"
CHECK_INTERVAL = 30  # Check every 30 seconds

# Keywords to identify important messages
PRIORITY_KEYWORDS = [
    "urgent", "asap", "invoice", "payment", "help", "emergency",
    "deadline", "meeting", "call", "money", "bill"
]

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


# ── Watcher Class ─────────────────────────────────────────────────────────────
class WhatsAppWatcher:
    """Monitors WhatsApp Web and creates action files for priority messages."""

    def __init__(self, vault_path: Path, dry_run: bool = False):
        self.vault = vault_path
        self.needs_action = vault_path / "Needs_Action"
        self.dry_run = dry_run
        self.processed_messages: set[str] = set()
        self.session_path = SESSION_PATH

        # Ensure folders exist
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.session_path.mkdir(parents=True, exist_ok=True)

    def check_for_updates(self) -> list[dict]:
        """Check WhatsApp Web for new messages with priority keywords."""
        messages = []

        try:
            with sync_playwright() as p:
                # Launch browser with persistent session
                browser = p.chromium.launch_persistent_context(
                    str(self.session_path),
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                    ],
                )

                page = browser.pages[0] if browser.pages else browser.new_page()

                try:
                    # Navigate to WhatsApp Web
                    page.goto("https://web.whatsapp.com", timeout=60000)

                    # Wait for chat list to load (indicates successful login)
                    try:
                        page.wait_for_selector('[data-testid="chat-list"]', timeout=30000)
                    except PlaywrightTimeout:
                        log.warning(
                            "WhatsApp Web not loaded. Please scan QR code manually first run."
                        )
                        browser.close()
                        return []

                    # Find unread message chats
                    unread_chats = page.query_selector_all(
                        '[aria-label*="unread"], [data-testid="unread-mark"]'
                    )

                    for chat in unread_chats:
                        try:
                            # Extract chat info
                            chat_name_elem = chat.query_selector(
                                '[data-testid="chat-cell-name"]'
                            )
                            chat_name = (
                                chat_name_elem.inner_text()
                                if chat_name_elem
                                else "Unknown"
                            )

                            # Get last message preview
                            message_elem = chat.query_selector(
                                '[data-testid="chat-cell-message"]'
                            )
                            message_text = (
                                message_elem.inner_text()
                                if message_elem
                                else ""
                            )

                            # Check for priority keywords
                            message_lower = message_text.lower()
                            if any(kw in message_lower for kw in PRIORITY_KEYWORDS):
                                messages.append({
                                    "from": chat_name[:100],
                                    "text": message_text[:500],
                                    "timestamp": datetime.now().isoformat(),
                                    "priority": "high",
                                })
                                log.info(f"Priority message from {chat_name}: {message_text[:50]}")

                        except Exception as e:
                            log.debug(f"Error parsing chat: {e}")
                            continue

                    browser.close()

                except Exception as e:
                    log.error(f"Error accessing WhatsApp Web: {e}")
                    browser.close()
                    return []

        except Exception as e:
            log.error(f"Playwright error: {e}")
            return []

        return messages

    def create_action_file(self, message_data: dict) -> Path:
        """Generate a structured .md action file in /Needs_Action."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        safe_name = message_data["from"].replace(" ", "_")[:30]
        action_filename = f"WHATSAPP_{timestamp}_{safe_name}.md"
        action_path = self.needs_action / action_filename

        content = f"""---
type: whatsapp_message
from: {message_data["from"]}
received: {message_data["timestamp"]}
priority: {message_data["priority"]}
status: pending
platform: whatsapp
---

## WhatsApp Message Received

**From:** {message_data["from"]}
**Time:** {datetime.fromisoformat(message_data["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")}
**Priority:** {message_data["priority"].upper()}

---

### Message Content

{message_data["text"]}

---

## Suggested Actions

- [ ] Read full message context
- [ ] Draft reply (auto-approved for drafting)
- [ ] Send reply via WhatsApp (requires approval)
- [ ] Mark as read in WhatsApp
- [ ] Archive after processing

## Notes

*(Claude Code — add your analysis and action plan here)*

## Response Guidelines (from Company_Handbook.md)

- Be professional and concise
- Respond within 24 hours for normal priority
- Respond within 1 hour for high priority (invoice, payment, urgent)
- Never share sensitive information via WhatsApp
"""

        if self.dry_run:
            log.info(f"[DRY RUN] Would create: {action_path}")
            log.info(f"[DRY RUN] Content preview:\n{content[:300]}...")
            return action_path

        action_path.write_text(content, encoding="utf-8")
        log.info(f"WhatsApp action file created: {action_path.name}")
        self._append_dashboard_log(message_data["from"], message_data["text"], action_filename)
        return action_path

    def _append_dashboard_log(self, sender: str, message: str, action_file: str):
        """Append a line to the Recent Activity Log in Dashboard.md."""
        dashboard = self.vault / "Dashboard.md"
        if not dashboard.exists():
            log.warning("Dashboard.md not found — skipping log update.")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        log_line = f"| {timestamp} | WhatsApp message | {sender}: {message[:30]}... | → {action_file} |\n"

        text = dashboard.read_text(encoding="utf-8")

        # Find activity log section and insert
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("| 2026-03-09") or line.startswith("| 2026-03-04"):
                lines.insert(i, log_line)
                break
        else:
            lines.append(log_line)

        if not self.dry_run:
            dashboard.write_text("\n".join(lines), encoding="utf-8")

    def run(self):
        """Main watcher loop."""
        log.info("=" * 60)
        log.info("  AI Employee — WhatsApp Watcher  (Silver Tier)")
        log.info("=" * 60)
        log.info(f"  Vault        : {self.vault}")
        log.info(f"  Check interval: {CHECK_INTERVAL}s")
        log.info(f"  Dry run      : {self.dry_run}")
        log.info(f"  Session path : {self.session_path}")
        log.info("=" * 60)
        log.info("Watcher started. Monitoring WhatsApp for priority messages.")
        log.info("First run: Scan QR code on WhatsApp Web if not already logged in.")
        log.info("Press Ctrl+C to stop.\n")

        while True:
            try:
                messages = self.check_for_updates()
                for msg in messages:
                    msg_id = f"{msg['from']}:{msg['text'][:50]}"
                    if msg_id not in self.processed_messages:
                        self.create_action_file(msg)
                        self.processed_messages.add(msg_id)
                if messages:
                    log.info(f"Processed {len(messages)} priority message(s).")
            except Exception as e:
                log.error(f"Error in watcher loop: {e}")

            time.sleep(CHECK_INTERVAL)


# ── Runner ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Silver Tier WhatsApp Watcher — monitors WhatsApp Web for priority messages."
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

    if not vault.exists():
        log.error(f"Vault path does not exist: {vault}")
        sys.exit(1)

    watcher = WhatsAppWatcher(vault_path=vault, dry_run=args.dry_run)
    watcher.run()


if __name__ == "__main__":
    main()
