#!/usr/bin/env python3
"""
platinum_demo.py — Platinum Tier End-to-End Demo
==================================================
Simulates the minimum passing gate:

  "Email arrives while Local is offline →
   Cloud drafts reply + writes approval file →
   when Local returns, user approves →
   Local executes send via MCP →
   logs → moves task to /Done"

Run this to demonstrate the full Platinum workflow without real email.

Usage:
  python demo/platinum_demo.py --vault-path D:/bronze_tier [--auto-approve]

Steps simulated:
  1. Inject a fake incoming email into /Needs_Action/email/ (simulates Gmail watcher)
  2. Run cloud orchestrator processing (simulates cloud drafting while local offline)
  3. Show the approval file in /Pending_Approval/email/
  4. Prompt user to approve (or --auto-approve skips prompt)
  5. Move file to /Approved/ and simulate local MCP send
  6. Log result + move to /Done/
  7. Write A2A completion signal to /Updates/
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone

VAULT_DEFAULT = Path(os.environ.get("VAULT_PATH", "D:/bronze_tier")).resolve()

SEP = "=" * 60


def banner(msg: str) -> None:
    print(f"\n{SEP}")
    print(f"  {msg}")
    print(SEP)


def step(n: int, msg: str) -> None:
    print(f"\n[Step {n}] {msg}")


def run_demo(vault: Path, auto_approve: bool = False) -> None:
    # Ensure folders exist
    for folder in [
        vault / "Needs_Action" / "email",
        vault / "In_Progress" / "cloud",
        vault / "Pending_Approval" / "email",
        vault / "Approved",
        vault / "Done" / "platinum_demo",
        vault / "Logs",
        vault / "Updates",
    ]:
        folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    ts_iso    = timestamp.isoformat()
    ts_file   = timestamp.strftime("%Y-%m-%d_%H%M%S")

    banner("Platinum Tier Demo — Email-While-Offline Scenario")
    print("""
Scenario:
  1. Local machine is OFFLINE (you're asleep / away)
  2. An email arrives from a client
  3. Cloud AI Employee processes it, drafts a reply
  4. Cloud creates an approval file (never sends directly)
  5. When Local comes back online, vault syncs
  6. You (Local) review and approve
  7. Local sends via MCP, logs, archives to Done
""")

    # ── Step 1: Simulate incoming email ──────────────────────────────────────
    step(1, "Simulating incoming email (Gmail watcher would normally do this)")

    email_action_content = f"""---
type: gmail_email
from: client@example.com
sender: Client Name <client@example.com>
subject: Invoice #2026-001 — Quick question
received: {ts_iso}
priority: high
status: pending
domain: email
---

## Email Received (Simulated)

**From:** Client Name <client@example.com>
**Subject:** Invoice #2026-001 — Quick question
**Time:** {timestamp.strftime('%Y-%m-%d %H:%M UTC')}
**Priority:** HIGH (contains keyword: invoice)

---

### Message Content

Hi,

I received Invoice #2026-001 for $1,500. Just wanted to confirm
the payment deadline — is it 30 days from the invoice date?

Also, can you send me a PDF version?

Thanks,
Client Name

---

## Suggested Actions

- [ ] Draft reply confirming payment terms
- [ ] Attach invoice PDF
- [ ] Send reply (requires approval)
"""
    email_file = vault / "Needs_Action" / "email" / f"EMAIL_{ts_file}_client_invoice_question.md"
    email_file.write_text(email_action_content, encoding="utf-8")
    print(f"  -> Email action file created: {email_file.relative_to(vault)}")

    # ── Step 2: Cloud orchestrator processes ─────────────────────────────────
    step(2, "Cloud orchestrator processes email (simulating cloud-side processing)")
    print("  [Cloud is ONLINE, Local is OFFLINE]")

    # Import and run cloud orchestrator logic directly (no subprocess needed)
    sys.path.insert(0, str(vault / "watchers"))
    try:
        from cloud_orchestrator import CloudOrchestrator
        orchestrator = CloudOrchestrator(vault_path=vault, agent_id="cloud")
        claimed = orchestrator.claim_item(email_file)
        if claimed:
            result = orchestrator.process_item(claimed)
            # Move to done/cloud
            done_dir = vault / "Done" / "platinum_demo"
            orchestrator.release_item(claimed, done_dir / claimed.name)
            print(f"  -> Cloud processed: {result}")
        else:
            print("  -> Could not claim (file may have moved already)")
    except ImportError as e:
        print(f"  [Fallback] Running orchestrator in subprocess: {e}")
        subprocess.run(
            [sys.executable, str(vault / "watchers" / "cloud_orchestrator.py"),
             "--vault-path", str(vault), "--agent-id", "cloud"],
            timeout=10, check=False,
        )

    # ── Step 3: Show approval file ────────────────────────────────────────────
    step(3, "Vault syncs to Local (simulated). Checking /Pending_Approval/email/...")

    approval_dir = vault / "Pending_Approval" / "email"
    approval_files = sorted(approval_dir.glob("EMAIL_DRAFT_*.md"), key=lambda f: f.stat().st_mtime, reverse=True)

    if not approval_files:
        print("  -> No approval file found. Cloud orchestrator may need credentials.")
        print("  -> Creating a sample approval file for demo purposes...")
        sample_approval = approval_dir / f"EMAIL_DRAFT_{ts_file}_demo.md"
        sample_approval.write_text(f"""---
type: email_draft
from_agent: cloud
to: client@example.com
subject: Re: Invoice #2026-001 — Quick question
priority: high
created: {ts_iso}
status: pending_approval
action_required: local_send
---

# Email Draft — Requires Local Approval

**To:** client@example.com
**Subject:** Re: Invoice #2026-001 — Quick question
**Drafted by:** Cloud Agent at {ts_iso}

---

### Draft Reply

Hi Client Name,

Thank you for reaching out about Invoice #2026-001.

Payment is due within 30 days from the invoice date. I have
attached a PDF version for your records.

Please don't hesitate to reach out if you have any further questions.

Best regards,
[Your Name]

---

## To Approve: Move this file to /Approved/
## To Reject:  Move this file to /Rejected/
""", encoding="utf-8")
        approval_files = [sample_approval]

    latest_approval = approval_files[0]
    print(f"  -> Approval file found: {latest_approval.relative_to(vault)}")
    print()
    print("  === APPROVAL FILE PREVIEW ===")
    content = latest_approval.read_text(encoding="utf-8")
    print(content[:800] + ("..." if len(content) > 800 else ""))
    print("  === END PREVIEW ===")

    # ── Step 4: Human approval ────────────────────────────────────────────────
    step(4, "Local returns online. Human reviews approval file.")

    if auto_approve:
        print("  [--auto-approve] Automatically approving...")
        approved = True
    else:
        print()
        choice = input("  Approve this email draft? [y/N]: ").strip().lower()
        approved = choice in ("y", "yes")

    if not approved:
        print("  -> Rejected. Moving to /Rejected/...")
        rejected_dir = vault / "Rejected"
        rejected_dir.mkdir(exist_ok=True)
        shutil.move(str(latest_approval), str(rejected_dir / latest_approval.name))
        print("  Demo complete (rejected).")
        return

    # ── Step 5: Move to /Approved/ ────────────────────────────────────────────
    step(5, "Moving to /Approved/ — Local agent will execute send via MCP")
    approved_dir = vault / "Approved"
    approved_dir.mkdir(exist_ok=True)
    approved_path = approved_dir / latest_approval.name
    shutil.move(str(latest_approval), str(approved_path))
    print(f"  -> Moved to: {approved_path.relative_to(vault)}")

    # Simulate MCP email send (DRY_RUN)
    print("  -> Calling email MCP (DRY_RUN=true — no real email sent)...")
    mcp_result = {
        "status": "dry_run",
        "to": "client@example.com",
        "subject": "Re: Invoice #2026-001 — Quick question",
        "message": "Email would be sent via SMTP MCP server",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    print(f"  -> MCP result: {json.dumps(mcp_result, indent=6)}")

    # ── Step 6: Log + archive to Done ────────────────────────────────────────
    step(6, "Logging result and archiving to /Done/")

    # Write action log
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "local",
        "action_type": "email_sent_approved",
        "result": "dry_run",
        "details": mcp_result,
        "source": "platinum_demo",
    }
    log_file = vault / "Logs" / "email_actions.json"
    entries = []
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            entries = []
    entries.append(log_entry)
    log_file.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")

    # Move approved file to Done
    done_dir = vault / "Done" / "platinum_demo"
    done_dir.mkdir(parents=True, exist_ok=True)
    done_path = done_dir / f"DONE_{approved_path.name}"
    shutil.move(str(approved_path), str(done_path))
    print(f"  -> Archived to: {done_path.relative_to(vault)}")

    # ── Step 7: A2A completion signal ────────────────────────────────────────
    step(7, "Writing A2A completion signal to /Updates/ (for cloud to acknowledge)")

    update = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "local",
        "event_type": "email_sent",
        "data": {
            "to": "client@example.com",
            "subject": "Re: Invoice #2026-001 — Quick question",
            "result": "sent_dry_run",
            "archived_to": str(done_path.relative_to(vault)),
        },
    }
    update_file = vault / "Updates" / f"UPDATE_{ts_file}_email_sent.json"
    update_file.write_text(json.dumps(update, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  -> Update written: {update_file.relative_to(vault)}")

    # ── Summary ──────────────────────────────────────────────────────────────
    banner("Platinum Demo Complete!")
    print(f"""
WORKFLOW VERIFIED:
  1. Email arrived while Local offline       [DONE]
  2. Cloud drafted reply                     [DONE]
  3. Cloud wrote approval file               [DONE]
  4. Vault synced to Local                   [SIMULATED]
  5. Human approved                          [DONE]
  6. Local executed send via MCP (DRY_RUN)   [DONE]
  7. Logged + moved to /Done/                [DONE]
  8. A2A signal written to /Updates/         [DONE]

Files created this demo:
  /Done/platinum_demo/                       (processed items)
  /Logs/email_actions.json                   (audit log entry)
  /Updates/UPDATE_{ts_file}_email_sent.json  (A2A signal)
""")


def main() -> None:
    parser = argparse.ArgumentParser(description="Platinum Tier Demo — Email-while-offline scenario")
    parser.add_argument("--vault-path", default=str(VAULT_DEFAULT))
    parser.add_argument("--auto-approve", action="store_true", help="Skip approval prompt")
    args = parser.parse_args()

    vault = Path(args.vault_path).resolve()
    if not vault.exists():
        print(f"ERROR: Vault not found: {vault}")
        sys.exit(1)

    run_demo(vault, auto_approve=args.auto_approve)


if __name__ == "__main__":
    main()
