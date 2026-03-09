#!/usr/bin/env python3
"""
cloud_orchestrator.py — Platinum Tier Cloud Orchestrator
=========================================================
Master orchestrator for the cloud AI Employee agent.

Work-Zone Specialization:
  Cloud owns:  Email triage, draft replies, social post drafts/scheduling
               (draft-only; requires Local approval before send/post)
  Local owns:  Approvals, WhatsApp session, payments/banking, final send/post

Claim-by-move rule:
  First agent to move an item from /Needs_Action/<domain>/
  to /In_Progress/<agent>/ owns it. Other agents must ignore it.

Vault communication:
  Cloud writes signals to /Updates/  (status, discoveries, drafts)
  Local merges /Updates/ into Dashboard.md (single writer rule)

Usage:
  python watchers/cloud_orchestrator.py --vault-path /opt/ai-employee --agent-id cloud

Environment:
  AGENT_ID=cloud   (set in systemd unit)
"""

import os
import sys
import json
import time
import shutil
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("CloudOrchestrator")

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_VAULT = Path(os.environ.get("VAULT_PATH", "/opt/ai-employee")).resolve()
AGENT_ID = os.environ.get("AGENT_ID", "cloud")
CHECK_INTERVAL = 60  # seconds between polls

# Work-zone ownership
CLOUD_DOMAINS = {"email", "social", "financial_draft"}
LOCAL_DOMAINS = {"approval", "payment", "whatsapp", "banking"}

# Needs_Action sub-folders this cloud agent processes
CLOUD_INBOX_DIRS = ["email", "social", "financial"]


class CloudOrchestrator:
    """
    Coordinates all cloud-side processing.
    Implements claim-by-move to prevent double-processing.
    Writes signals to /Updates/ for Local to merge into Dashboard.
    """

    def __init__(self, vault_path: Path, agent_id: str = "cloud"):
        self.vault = vault_path
        self.agent_id = agent_id

        # Folder layout
        self.needs_action   = vault_path / "Needs_Action"
        self.in_progress    = vault_path / "In_Progress" / agent_id
        self.pending_approval = vault_path / "Pending_Approval"
        self.done           = vault_path / "Done"
        self.updates        = vault_path / "Updates"
        self.plans          = vault_path / "Plans"
        self.logs_dir       = vault_path / "Logs"

        # Ensure all folders exist
        for folder in [
            self.in_progress,
            self.updates,
            self.logs_dir,
            self.pending_approval / "email",
            self.pending_approval / "social",
            self.plans / "email",
            self.plans / "social",
        ]:
            folder.mkdir(parents=True, exist_ok=True)

        self.processed: set[str] = set()
        self._log_action("startup", {"agent": agent_id, "vault": str(vault_path)}, "success")

    # ── Audit logging ─────────────────────────────────────────────────────────

    def _log_action(self, action_type: str, details: dict, result: str) -> None:
        """Append to daily audit log."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": self.agent_id,
            "action_type": action_type,
            "result": result,
            "details": details,
        }
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"audit_{date_str}.json"
        entries = []
        if log_file.exists():
            try:
                entries = json.loads(log_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                entries = []
        entries.append(entry)
        log_file.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Claim-by-move rule ────────────────────────────────────────────────────

    def claim_item(self, source_path: Path) -> Path | None:
        """
        Atomically claim an item by moving it to /In_Progress/<agent>/.
        Returns the new path if successful, None if already claimed.
        """
        dest = self.in_progress / source_path.name
        if dest.exists():
            return None  # Already claimed (possibly by us on restart)

        try:
            shutil.move(str(source_path), str(dest))
            log.info(f"Claimed: {source_path.name} -> In_Progress/{self.agent_id}/")
            return dest
        except (FileNotFoundError, PermissionError):
            # Another agent claimed it first
            return None

    def release_item(self, claimed_path: Path, destination: Path) -> None:
        """Move a processed item from In_Progress to its final destination."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(claimed_path), str(destination))
        log.info(f"Released: {claimed_path.name} -> {destination.parent.name}/")

    # ── Item processing ───────────────────────────────────────────────────────

    def parse_frontmatter(self, content: str) -> tuple[dict, str]:
        """Parse YAML-lite frontmatter from a markdown file."""
        fm: dict[str, str] = {}
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        fm[k.strip()] = v.strip().strip('"')
                body = parts[2].strip()
        return fm, body

    def process_email_item(self, file_path: Path) -> str:
        """
        Cloud processes email items: drafts a reply and creates approval request.
        Never sends — always routes to /Pending_Approval/email/ for Local.
        """
        content = file_path.read_text(encoding="utf-8")
        fm, body = self.parse_frontmatter(content)

        sender    = fm.get("from", fm.get("sender", "Unknown"))
        subject   = fm.get("subject", "No subject")
        priority  = fm.get("priority", "normal")
        timestamp = datetime.now(timezone.utc).isoformat()
        ts_file   = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")

        # Draft reply (cloud writes, local sends after approval)
        draft_subject = f"Re: {subject}" if not subject.startswith("Re:") else subject
        draft_body = f"""Hi,

Thank you for your email regarding "{subject}".

[AI Employee draft — please review and personalise before sending]

Best regards,
[Your Name]
"""
        approval_content = f"""---
type: email_draft
from_agent: {self.agent_id}
to: {sender}
subject: {draft_subject}
original_subject: {subject}
priority: {priority}
created: {timestamp}
status: pending_approval
action_required: local_send
---

# Email Draft — Requires Local Approval

**To:** {sender}
**Subject:** {draft_subject}
**Priority:** {priority.upper()}
**Drafted by:** Cloud Agent at {timestamp}

---

### Draft Reply

{draft_body}

---

### Original Message Summary

{body[:500]}{"..." if len(body) > 500 else ""}

---

## To Approve
Move this file to `/Approved/` — Local agent will send via MCP.

## To Reject
Move this file to `/Rejected/`.

## Notes
*(Add any personalisation or corrections here before approving)*
"""
        approval_file = self.pending_approval / "email" / f"EMAIL_DRAFT_{ts_file}_{sender[:20].replace(' ', '_')}.md"
        approval_file.write_text(approval_content, encoding="utf-8")

        # Write signal to /Updates/ for Local to merge into Dashboard
        self.write_update("email_draft_created", {
            "file": approval_file.name,
            "to": sender,
            "subject": draft_subject,
            "priority": priority,
        })

        log.info(f"Email draft created: {approval_file.name}")
        return f"Draft created: {approval_file.name}"

    def process_social_item(self, file_path: Path) -> str:
        """
        Cloud processes social items: schedules posts and creates approval requests.
        Never posts directly — routes to /Pending_Approval/social/ for Local.
        """
        content = file_path.read_text(encoding="utf-8")
        fm, body = self.parse_frontmatter(content)

        platform = fm.get("platform", "twitter")
        msg_type = fm.get("type", "social_message")
        sender   = fm.get("from", "Unknown")
        timestamp = datetime.now(timezone.utc).isoformat()
        ts_file   = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")

        # Prepare a post draft based on the incoming message
        post_content = f"""✨ Thank you for reaching out on {platform}!

[Cloud Agent draft — review before posting]

{body[:200]}

#CustomerService #AI
"""

        approval_content = f"""---
type: social_post_draft
from_agent: {self.agent_id}
platform: {platform}
source_type: {msg_type}
source_sender: {sender}
created: {timestamp}
status: pending_approval
action_required: local_post
---

# Social Post Draft — Requires Local Approval

**Platform:** {platform}
**Source:** {msg_type} from {sender}
**Drafted by:** Cloud Agent at {timestamp}

---

### Draft Post

{post_content}

---

### Source Message Summary

{body[:300]}{"..." if len(body) > 300 else ""}

---

## To Approve
Move this file to `/Approved/` — Local agent will post via Social MCP.

## To Reject
Move this file to `/Rejected/`.
"""
        approval_file = self.pending_approval / "social" / f"SOCIAL_DRAFT_{ts_file}_{platform}.md"
        approval_file.write_text(approval_content, encoding="utf-8")

        self.write_update("social_draft_created", {
            "file": approval_file.name,
            "platform": platform,
            "source": sender,
        })

        log.info(f"Social draft created: {approval_file.name}")
        return f"Draft created: {approval_file.name}"

    def process_item(self, claimed_path: Path) -> str:
        """Route a claimed item to the correct cloud processor."""
        content = claimed_path.read_text(encoding="utf-8")
        fm, _ = self.parse_frontmatter(content)
        item_type = fm.get("type", "unknown")
        domain    = fm.get("domain", self._infer_domain(item_type))

        try:
            if domain in ("email", "gmail", "imap") or item_type in ("email", "gmail_email"):
                result = self.process_email_item(claimed_path)
            elif domain in ("social", "twitter", "facebook", "instagram") or \
                 item_type in ("twitter_mention", "twitter_dm", "facebook_message", "instagram_mention"):
                result = self.process_social_item(claimed_path)
            else:
                # Unknown type — write to generic pending approval
                result = self._forward_to_local(claimed_path, domain)

            self._log_action("item_processed", {
                "file": claimed_path.name,
                "type": item_type,
                "domain": domain,
                "result": result,
            }, "success")

            return result

        except Exception as exc:
            self._log_action("item_error", {
                "file": claimed_path.name,
                "error": str(exc),
            }, "error")
            log.error(f"Error processing {claimed_path.name}: {exc}")
            return f"Error: {exc}"

    def _infer_domain(self, item_type: str) -> str:
        """Infer domain from item type string."""
        if any(k in item_type for k in ("email", "gmail", "imap")):
            return "email"
        if any(k in item_type for k in ("twitter", "facebook", "instagram", "social", "whatsapp")):
            return "social"
        if any(k in item_type for k in ("invoice", "payment", "financial")):
            return "financial"
        return "unknown"

    def _forward_to_local(self, claimed_path: Path, domain: str) -> str:
        """Forward an unrecognised item to /Pending_Approval/ for Local."""
        dest_dir = self.pending_approval / domain
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / claimed_path.name
        claimed_path.write_text(
            claimed_path.read_text(encoding="utf-8") +
            f"\n\n---\n*Forwarded by cloud agent — domain: {domain}*\n",
            encoding="utf-8",
        )
        shutil.copy(str(claimed_path), str(dest))
        return f"Forwarded to Pending_Approval/{domain}/"

    # ── Updates (signals to Local) ────────────────────────────────────────────

    def write_update(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Write a signal file to /Updates/ for Local to merge into Dashboard.
        Local is the single writer for Dashboard.md.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        update_file = self.updates / f"UPDATE_{timestamp}_{event_type}.json"
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": self.agent_id,
            "event_type": event_type,
            "data": data,
        }
        update_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        log.debug(f"Update written: {update_file.name}")

    def write_health_signal(self) -> None:
        """Write a heartbeat to /Updates/ so Local knows cloud is alive."""
        self.write_update("heartbeat", {
            "agent": self.agent_id,
            "watchers": "running",
            "uptime": "see systemd: journalctl -u ai-employee-cloud-orchestrator",
        })

    # ── Scan & process ────────────────────────────────────────────────────────

    def scan_cloud_inbox(self) -> list[Path]:
        """
        Scan /Needs_Action/<domain>/ folders that Cloud owns.
        Returns unclaimed .md files.
        """
        items = []
        for domain in CLOUD_INBOX_DIRS:
            domain_dir = self.needs_action / domain
            if not domain_dir.exists():
                continue
            for f in domain_dir.glob("*.md"):
                if str(f) not in self.processed:
                    items.append(f)
        return items

    def scan_toplevel_inbox(self) -> list[Path]:
        """
        Also scan /Needs_Action/ root for items with email/social types
        (created by watchers that don't use domain sub-folders).
        """
        items = []
        if not self.needs_action.exists():
            return []
        for f in self.needs_action.glob("*.md"):
            if str(f) in self.processed:
                continue
            content = f.read_text(encoding="utf-8")
            fm, _ = self.parse_frontmatter(content)
            item_type = fm.get("type", "")
            domain = self._infer_domain(item_type)
            if domain in CLOUD_DOMAINS or item_type in (
                "email", "gmail_email", "twitter_mention", "twitter_dm",
                "facebook_message", "instagram_mention",
            ):
                items.append(f)
        return items

    def run(self) -> None:
        """Main orchestrator loop."""
        log.info("=" * 60)
        log.info(f"  AI Employee — Cloud Orchestrator  (Platinum Tier)")
        log.info("=" * 60)
        log.info(f"  Vault   : {self.vault}")
        log.info(f"  Agent   : {self.agent_id}")
        log.info(f"  Domains : {CLOUD_DOMAINS}")
        log.info(f"  Interval: {CHECK_INTERVAL}s")
        log.info("=" * 60)
        log.info("Cloud orchestrator started. Monitoring vault for email/social items.")
        log.info("Press Ctrl+C to stop.\n")

        iteration = 0
        while True:
            try:
                items = self.scan_cloud_inbox() + self.scan_toplevel_inbox()
                # De-duplicate by path
                seen: set[str] = set()
                unique_items = []
                for item in items:
                    if str(item) not in seen:
                        seen.add(str(item))
                        unique_items.append(item)

                for item_path in unique_items:
                    claimed = self.claim_item(item_path)
                    if claimed is None:
                        continue  # Another agent claimed it first

                    result = self.process_item(claimed)

                    # Move to Done
                    done_dir = self.done / "cloud"
                    done_dir.mkdir(parents=True, exist_ok=True)
                    self.release_item(claimed, done_dir / claimed.name)
                    self.processed.add(str(item_path))

                # Heartbeat every 10 iterations
                iteration += 1
                if iteration % 10 == 0:
                    self.write_health_signal()

            except KeyboardInterrupt:
                log.info("Cloud orchestrator stopping...")
                break
            except Exception as exc:
                log.error(f"Error in orchestrator loop: {exc}")
                self._log_action("loop_error", {"error": str(exc)}, "error")

            time.sleep(CHECK_INTERVAL)


# ── Runner ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Platinum Tier Cloud Orchestrator — processes email/social items on the cloud"
    )
    parser.add_argument("--vault-path", default=str(DEFAULT_VAULT))
    parser.add_argument("--agent-id", default=AGENT_ID)
    args = parser.parse_args()

    vault = Path(args.vault_path).resolve()
    if not vault.exists():
        log.error(f"Vault not found: {vault}")
        sys.exit(1)

    orchestrator = CloudOrchestrator(vault_path=vault, agent_id=args.agent_id)
    orchestrator.run()


if __name__ == "__main__":
    main()
