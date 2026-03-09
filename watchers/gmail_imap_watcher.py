"""
gmail_imap_watcher.py — Bronze Tier Watcher
============================================
Monitors Gmail inbox for new unread emails and creates structured
.md action files in /Needs_Action for Claude Code to process.

Uses IMAP protocol — no Google API setup required.
Just enable IMAP in Gmail settings and use an App Password.

Usage:
    python gmail_imap_watcher.py [--vault-path PATH] [--dry-run]

Requirements:
    pip install imaplib2  # or use built-in imaplib

Setup:
    1. Enable IMAP in Gmail: Settings → Forwarding and POP/IMAP → Enable IMAP
    2. Create App Password: myaccount.google.com/apppasswords
    3. Set environment variables:
       - GMAIL_USERNAME=your.email@gmail.com
       - GMAIL_APP_PASSWORD=your-16-char-app-password
"""

import os
import sys
import time
import logging
import argparse
import email
import imaplib
from pathlib import Path
from datetime import datetime
from email.header import decode_header

# Load .env file before reading any environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass  # python-dotenv not installed; rely on shell env

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("GmailWatcher")

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_VAULT = Path(__file__).resolve().parent.parent  # D:/bronze_tier

# Credentials from environment (NEVER hardcode!)
GMAIL_USERNAME = os.getenv("GMAIL_USERNAME", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
CHECK_INTERVAL = 120  # Check every 2 minutes

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Keywords to identify priority emails
PRIORITY_KEYWORDS = ["urgent", "asap", "invoice", "payment", "deadline", "emergency"]


# ── Watcher Class ─────────────────────────────────────────────────────────────
class GmailWatcher:
    """Monitors Gmail inbox and creates action files for new emails."""

    def __init__(self, vault_path: Path, dry_run: bool = False):
        self.vault = vault_path
        self.needs_action = vault_path / "Needs_Action"
        self.dry_run = dry_run
        self.processed_ids: set[str] = set()

        # Ensure folders exist
        self.needs_action.mkdir(parents=True, exist_ok=True)

        # Validate credentials
        if not GMAIL_USERNAME or not GMAIL_APP_PASSWORD:
            log.warning(
                "GMAIL_USERNAME or GMAIL_APP_PASSWORD not set. "
                "Watcher will run in demo mode."
            )

    def connect(self) -> imaplib.IMAP4_SSL:
        """Connect to Gmail IMAP server."""
        log.info(f"Connecting to {IMAP_SERVER}...")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(GMAIL_USERNAME, GMAIL_APP_PASSWORD)
        log.info("Connected successfully.")
        return mail

    def check_for_updates(self) -> list[dict]:
        """Fetch unread emails from inbox."""
        if not GMAIL_USERNAME or not GMAIL_APP_PASSWORD:
            log.info("Demo mode: No credentials configured, skipping email check.")
            return []

        try:
            mail = self.connect()
            mail.select("inbox")

            # Search for unread emails
            status, messages = mail.search(None, "UNSEEN")

            if status != "OK":
                log.warning("Failed to search inbox.")
                mail.close()
                mail.logout()
                return []

            email_ids = messages[0].split()
            new_emails = []

            for email_id in email_ids:
                email_id_str = email_id.decode()
                if email_id_str not in self.processed_ids:
                    status, msg_data = mail.fetch(email_id, "(RFC822)")
                    if status == "OK":
                        raw_email = msg_data[0][1]
                        email_data = self._parse_email(raw_email)
                        email_data["id"] = email_id_str
                        new_emails.append(email_data)
                        self.processed_ids.add(email_id_str)

            mail.close()
            mail.logout()
            return new_emails

        except Exception as e:
            log.error(f"Error checking Gmail: {e}")
            return []

    def _parse_email(self, raw_email: bytes) -> dict:
        """Parse raw email bytes into structured data."""
        msg = email.message_from_bytes(raw_email)

        # Decode subject
        subject, encoding = decode_header(msg.get("Subject", "No Subject"))[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8", errors="replace")
        subject = subject[:100]  # Truncate long subjects

        # Decode from
        from_header, encoding = decode_header(msg.get("From", "Unknown"))[0]
        if isinstance(from_header, bytes):
            from_header = from_header.decode(encoding or "utf-8", errors="replace")
        from_header = from_header[:100]

        # Extract body (plain text preferred)
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        break
                    except Exception:
                        continue
        else:
            try:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
            except Exception:
                body = msg.get_payload()

        # Truncate body for action file
        body_preview = body[:500] + "..." if len(body) > 500 else body

        # Determine priority
        subject_lower = subject.lower()
        body_lower = body.lower()
        priority = "normal"
        if any(kw in subject_lower or kw in body_lower for kw in PRIORITY_KEYWORDS):
            priority = "high"

        return {
            "from": from_header,
            "subject": subject,
            "date": msg.get("Date", datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")),
            "body": body_preview,
            "priority": priority,
        }

    def create_action_file(self, email_data: dict) -> Path:
        """Generate a structured .md action file in /Needs_Action."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        email_id = email_data.get("id", "unknown")
        safe_subject = email_data["subject"].replace(" ", "_").replace("/", "_")[:50]
        action_filename = f"EMAIL_{timestamp}_{safe_subject}.md"
        action_path = self.needs_action / action_filename

        content = f"""---
type: email
from: {email_data["from"]}
subject: {email_data["subject"]}
received: {datetime.now().isoformat()}
priority: {email_data["priority"]}
status: pending
email_id: {email_id}
---

## Email Content

**From:** {email_data["from"]}
**Subject:** {email_data["subject"]}
**Date:** {email_data["date"]}

---

{email_data["body"]}

---

## Suggested Actions

- [ ] Read full email content
- [ ] Draft reply (auto-approved for drafting)
- [ ] Send reply (requires approval)
- [ ] Archive after processing

## Notes

*(Claude Code — add your analysis and action plan here)*
"""

        if self.dry_run:
            log.info(f"[DRY RUN] Would create: {action_path}")
            log.info(f"[DRY RUN] Content preview:\n{content[:300]}...")
            return action_path

        action_path.write_text(content, encoding="utf-8")
        log.info(f"Email action file created: {action_path.name}")
        self._append_dashboard_log(email_data["from"], email_data["subject"], action_filename)
        return action_path

    def _append_dashboard_log(self, sender: str, subject: str, action_file: str):
        """Append a line to the Recent Activity Log in Dashboard.md."""
        dashboard = self.vault / "Dashboard.md"
        if not dashboard.exists():
            log.warning("Dashboard.md not found — skipping log update.")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        log_line = f"| {timestamp} | Email received | {sender}: {subject[:30]}... | → {action_file} |\n"

        text = dashboard.read_text(encoding="utf-8")

        # Try to find the activity log section
        if "| 2026-03-04 | System Initialized" in text:
            text = text.replace(
                "| 2026-03-04 | System Initialized",
                log_line + "| 2026-03-04 | System Initialized",
            )
        else:
            # Append to end
            text += f"\n{log_line}"

        if not self.dry_run:
            dashboard.write_text(text, encoding="utf-8")

    def run(self):
        """Main watcher loop."""
        log.info("=" * 60)
        log.info("  AI Employee — Gmail Watcher  (Bronze Tier)")
        log.info("=" * 60)
        log.info(f"  Vault        : {self.vault}")
        log.info(f"  Check interval: {CHECK_INTERVAL}s")
        log.info(f"  Dry run      : {self.dry_run}")
        if GMAIL_USERNAME:
            log.info(f"  Account      : {GMAIL_USERNAME}")
        else:
            log.info("  Account      : (not configured)")
        log.info("=" * 60)
        log.info("Watcher started. Monitoring Gmail for new unread emails.")
        log.info("Press Ctrl+C to stop.\n")

        while True:
            try:
                emails = self.check_for_updates()
                for email_data in emails:
                    self.create_action_file(email_data)
                if emails:
                    log.info(f"Processed {len(emails)} new email(s).")
            except Exception as e:
                log.error(f"Error in watcher loop: {e}")

            time.sleep(CHECK_INTERVAL)


# ── Runner ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Bronze Tier Gmail Watcher — monitors Gmail for new emails."
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

    watcher = GmailWatcher(vault_path=vault, dry_run=args.dry_run)
    watcher.run()


if __name__ == "__main__":
    main()
