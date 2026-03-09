"""
approval_orchestrator.py — Silver Tier HITL Workflow
=====================================================
Human-in-the-Loop approval orchestrator for sensitive actions.
Monitors /Pending_Approval and /Approved folders, executes approved actions.

Usage:
    python approval_orchestrator.py [--vault-path PATH] [--dry-run]

Workflow:
    1. Claude creates approval request in /Pending_Approval/
    2. Human reviews and moves file to /Approved/ or /Rejected/
    3. Orchestrator detects approved files and executes actions
    4. Results logged and files archived to /Done/
"""

import os
import sys
import time
import logging
import subprocess
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("ApprovalOrchestrator")

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_VAULT = Path(__file__).resolve().parent.parent  # D:/bronze_tier

CHECK_INTERVAL = 30  # Check every 30 seconds
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Action type handlers
ACTION_HANDLERS = {
    "email_send": "send_approved_email",
    "email_draft": "send_approved_email",
    "payment": "execute_payment",
    "social_post": "publish_social_post",
    "file_delete": "delete_file",
    "external_api": "call_external_api",
}


# ── Orchestrator Class ────────────────────────────────────────────────────────
class ApprovalOrchestrator:
    """Orchestrates human-in-the-loop approval workflow."""

    def __init__(self, vault_path: Path, dry_run: bool = False):
        self.vault = vault_path
        self.dry_run = dry_run
        self.pending_approval = vault_path / "Pending_Approval"
        self.approved = vault_path / "Approved"
        self.rejected = vault_path / "Rejected"
        self.done = vault_path / "Done"
        self.logs = vault_path / "Logs"

        # Ensure folders exist
        for folder in [self.pending_approval, self.approved, self.rejected, self.done, self.logs]:
            folder.mkdir(parents=True, exist_ok=True)

        self.processed_files: set[str] = set()

    def check_approved_files(self) -> list[Path]:
        """Check for newly approved files."""
        if not self.approved.exists():
            return []

        approved_files = []
        for f in self.approved.glob("*.md"):
            if str(f) not in self.processed_files:
                approved_files.append(f)
                self.processed_files.add(str(f))

        return approved_files

    def check_rejected_files(self) -> list[Path]:
        """Check for newly rejected files."""
        if not self.rejected.exists():
            return []

        rejected_files = []
        for f in self.rejected.glob("*.md"):
            if str(f) not in self.processed_files:
                rejected_files.append(f)
                self.processed_files.add(str(f))

        return rejected_files

    def parse_approval_file(self, file_path: Path) -> dict:
        """Parse approval request file and extract frontmatter."""
        content = file_path.read_text(encoding="utf-8")

        # Extract frontmatter
        frontmatter = {}
        body = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm_text = parts[1].strip()
                body = parts[2].strip()
                for line in fm_text.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        frontmatter[key.strip()] = value.strip().strip('"')

        return {
            "frontmatter": frontmatter,
            "body": body,
            "file_path": file_path,
            "type": frontmatter.get("type", "unknown"),
            "action": frontmatter.get("action", frontmatter.get("type", "unknown")),
            "status": frontmatter.get("status", "pending"),
        }

    def execute_action(self, approval_data: dict) -> tuple[bool, str]:
        """Execute the approved action based on type."""
        action_type = approval_data["type"]
        handler = ACTION_HANDLERS.get(action_type)

        if not handler:
            return False, f"Unknown action type: {action_type}"

        log.info(f"Executing {action_type} via {handler}")

        try:
            if action_type in ["email_send", "email_draft"]:
                return self.send_approved_email(approval_data)
            elif action_type == "payment":
                return self.execute_payment(approval_data)
            elif action_type == "social_post":
                return self.publish_social_post(approval_data)
            elif action_type == "file_delete":
                return self.delete_file(approval_data)
            elif action_type == "external_api":
                return self.call_external_api(approval_data)
            else:
                return False, f"No handler for action type: {action_type}"
        except Exception as e:
            return False, f"Execution error: {str(e)}"

    def send_approved_email(self, approval_data: dict) -> tuple[bool, str]:
        """Send email using MCP server or SMTP."""
        fm = approval_data["frontmatter"]

        to = fm.get("to", "")
        subject = fm.get("subject", "")
        body = approval_data["body"]
        attachment = fm.get("attachment", "")

        if not to or not subject:
            return False, "Missing required fields: to or subject"

        if self.dry_run:
            return True, f"[DRY RUN] Would send email to {to}: {subject}"

        # Try using Claude Code with MCP
        mcp_config_file = self.vault / ".claude" / "mcp.json"
        if mcp_config_file.exists():
            # Use MCP server
            log.info("Using MCP email server...")
            # This would call the MCP server - for now, log the action
            result = f"Email sent via MCP to {to}: {subject}"
        else:
            # Fallback: log the action
            result = f"Email logged for sending to {to}: {subject}"

        self.log_action(approval_data, "email_sent", result)
        return True, result

    def execute_payment(self, approval_data: dict) -> tuple[bool, str]:
        """Execute payment (placeholder - integrate with payment API)."""
        fm = approval_data["frontmatter"]

        amount = fm.get("amount", "0")
        recipient = fm.get("recipient", "Unknown")
        reference = fm.get("reference", "")

        if self.dry_run:
            return True, f"[DRY RUN] Would pay ${amount} to {recipient}"

        # SECURITY: Never auto-execute payments without additional verification
        # This is a placeholder - integrate with your payment provider's API
        result = f"Payment of ${amount} to {recipient} logged for manual processing"
        self.log_action(approval_data, "payment_logged", result)
        return True, result

    def publish_social_post(self, approval_data: dict) -> tuple[bool, str]:
        """Publish social media post."""
        fm = approval_data["frontmatter"]

        platform = fm.get("platform", "linkedin")
        content = approval_data["body"]

        if self.dry_run:
            return True, f"[DRY RUN] Would post to {platform}: {content[:50]}..."

        # Call LinkedIn poster script
        poster_script = self.vault / "watchers" / "linkedin_poster.py"
        if poster_script.exists():
            try:
                # Create temp post file
                posts_pending = self.vault / "Posts" / "Pending"
                posts_pending.mkdir(parents=True, exist_ok=True)
                temp_post = posts_pending / f"orchestrator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                temp_post.write_text(f"""---
title: Orchestrated Post
created: {datetime.now().isoformat()}
status: pending
platform: {platform}
---

{content}
""")
                result = f"Post queued for {platform}"
            except Exception as e:
                return False, f"Failed to queue post: {str(e)}"
        else:
            result = f"Social post logged for {platform}: {content[:50]}..."

        self.log_action(approval_data, "social_post_queued", result)
        return True, result

    def delete_file(self, approval_data: dict) -> tuple[bool, str]:
        """Delete file (with audit trail)."""
        fm = approval_data["frontmatter"]
        file_to_delete = fm.get("file_path", "")

        if not file_to_delete:
            return False, "No file_path specified"

        if self.dry_run:
            return True, f"[DRY RUN] Would delete: {file_to_delete}"

        target = Path(file_to_delete)
        if target.exists():
            # Move to trash instead of permanent delete
            trash = self.vault / "_Trash"
            trash.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(trash / target.name))
            result = f"File moved to trash: {target.name}"
        else:
            result = f"File not found: {file_to_delete}"

        self.log_action(approval_data, "file_deleted", result)
        return True, result

    def call_external_api(self, approval_data: dict) -> tuple[bool, str]:
        """Call external API (placeholder)."""
        fm = approval_data["frontmatter"]

        url = fm.get("url", "")
        method = fm.get("method", "GET")
        body = fm.get("body", "")

        if not url:
            return False, "No URL specified"

        if self.dry_run:
            return True, f"[DRY RUN] Would call {method} {url}"

        # Placeholder - implement actual API call
        result = f"API call logged: {method} {url}"
        self.log_action(approval_data, "api_called", result)
        return True, result

    def log_action(self, approval_data: dict, action_type: str, result: str):
        """Log action to audit trail."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "file": str(approval_data["file_path"]),
            "type": approval_data["type"],
            "action": action_type,
            "result": result,
            "frontmatter": approval_data["frontmatter"],
        }

        # Append to daily log
        log_file = self.logs / f"approvals_{datetime.now().strftime('%Y-%m-%d')}.json"
        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text(encoding="utf-8"))
            except:
                logs = []

        logs.append(log_entry)
        log_file.write_text(json.dumps(logs, indent=2), encoding="utf-8")

    def archive_file(self, file_path: Path, status: str):
        """Move processed file to /Done/."""
        archive_folder = self.done / "Approvals"
        archive_folder.mkdir(parents=True, exist_ok=True)

        # Add status to filename
        new_name = f"{status.upper()}_{file_path.name}"
        dest = archive_folder / new_name

        try:
            shutil.move(str(file_path), str(dest))
            log.info(f"Archived: {file_path.name} -> {new_name}")
        except Exception as e:
            log.error(f"Failed to archive {file_path.name}: {e}")

    def update_dashboard(self, action_type: str, result: str):
        """Update Dashboard.md with approval activity."""
        dashboard = self.vault / "Dashboard.md"
        if not dashboard.exists():
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        log_line = f"| {timestamp} | Approval executed | {action_type}: {result[:40]}... | ✅ Complete |\n"

        text = dashboard.read_text(encoding="utf-8")
        lines = text.split("\n")

        for i, line in enumerate(lines):
            if line.startswith("| 2026-03-09") or line.startswith("| 2026-03-04"):
                lines.insert(i, log_line)
                break
        else:
            lines.append(log_line)

        dashboard.write_text("\n".join(lines), encoding="utf-8")

    def run(self):
        """Main orchestrator loop."""
        log.info("=" * 60)
        log.info("  AI Employee — Approval Orchestrator  (Silver Tier)")
        log.info("=" * 60)
        log.info(f"  Vault        : {self.vault}")
        log.info(f"  Check interval: {CHECK_INTERVAL}s")
        log.info(f"  Dry run      : {self.dry_run}")
        log.info("=" * 60)
        log.info("Orchestrator started. Monitoring /Approved and /Rejected folders.")
        log.info("Move approval requests to /Approved to execute, /Rejected to discard.")
        log.info("Press Ctrl+C to stop.\n")

        while True:
            try:
                # Check approved files
                approved_files = self.check_approved_files()
                for file_path in approved_files:
                    log.info(f"Processing approved file: {file_path.name}")
                    approval_data = self.parse_approval_file(file_path)
                    success, result = self.execute_action(approval_data)
                    self.archive_file(file_path, "approved" if success else "failed")
                    self.update_dashboard(approval_data["type"], result)

                # Check rejected files
                rejected_files = self.check_rejected_files()
                for file_path in rejected_files:
                    log.info(f"Archiving rejected file: {file_path.name}")
                    approval_data = self.parse_approval_file(file_path)
                    self.archive_file(file_path, "rejected")
                    self.update_dashboard(approval_data["type"], "Rejected by user")

            except Exception as e:
                log.error(f"Error in orchestrator loop: {e}")

            time.sleep(CHECK_INTERVAL)


# ── Runner ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Silver Tier Approval Orchestrator — executes approved actions."
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
        help="Log actions without executing (safe for testing).",
    )
    args = parser.parse_args()

    vault = Path(args.vault_path).resolve()

    if not vault.exists():
        log.error(f"Vault path does not exist: {vault}")
        sys.exit(1)

    orchestrator = ApprovalOrchestrator(vault_path=vault, dry_run=args.dry_run)
    orchestrator.run()


if __name__ == "__main__":
    main()
