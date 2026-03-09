#!/usr/bin/env python3
"""
vault_sync.py — Platinum Tier Vault Sync
==========================================
Git-based bidirectional vault sync between Local and Cloud.

Security rule: ONLY syncs markdown (.md) and state (.json) files.
Secrets (.env, tokens, WhatsApp sessions) NEVER sync.

Modes:
  push   — commit local changes and push to remote
  pull   — pull remote changes (fast-forward only)
  sync   — pull first, then push (full bidirectional)
  status — show what would be synced

Usage:
  python sync/vault_sync.py --vault-path D:/bronze_tier --mode sync
  python sync/vault_sync.py --mode push --message "Processed inbox"

On Cloud VM (via systemd timer):
  python sync/vault_sync.py --vault-path /opt/ai-employee --mode push

On Local (manual or scheduled):
  python sync/vault_sync.py --vault-path D:/bronze_tier --mode sync
"""

import os
import sys
import json
import argparse
import subprocess
import logging
from datetime import datetime, timezone
from pathlib import Path

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("VaultSync")

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_VAULT = Path(os.environ.get("VAULT_PATH", "D:/bronze_tier")).resolve()
AGENT_ID = os.environ.get("AGENT_ID", "local")

# Files/patterns that are ALLOWED to sync (whitelist approach)
SYNC_ALLOWED_EXTENSIONS = {".md", ".json"}
SYNC_ALLOWED_FILES = {"CLAUDE.md", ".gitignore"}

# Patterns that are NEVER synced (security rule)
SYNC_BLOCKED_PATTERNS = [
    ".env",
    "*.env",
    ".env.*",
    "*.session",
    "*.session.json",
    "*.pkl",
    "node_modules",
    ".venv",
    "__pycache__",
    "*.pyc",
    "*.log",
    ".git",
    "*.lock",
]


# ── Git helpers ───────────────────────────────────────────────────────────────

def run_git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command in the vault directory."""
    cmd = ["git"] + args
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        log.error(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return result


def is_git_repo(vault: Path) -> bool:
    result = run_git(["rev-parse", "--git-dir"], vault, check=False)
    return result.returncode == 0


def has_remote(vault: Path) -> bool:
    result = run_git(["remote"], vault, check=False)
    return bool(result.stdout.strip())


def get_changed_files(vault: Path) -> list[str]:
    """Return list of files modified or added (unstaged + staged)."""
    result = run_git(["status", "--porcelain"], vault)
    files = []
    for line in result.stdout.splitlines():
        if len(line) > 3:
            files.append(line[3:].strip())
    return files


def is_sync_allowed(file_path: str) -> bool:
    """
    Return True if this file is allowed to sync.
    Security rule: only .md and .json files; never secrets.
    """
    path = Path(file_path)

    # Block by pattern
    name = path.name
    for blocked in SYNC_BLOCKED_PATTERNS:
        if blocked.startswith("*"):
            if name.endswith(blocked[1:]):
                return False
        elif name == blocked or str(path).endswith("/" + blocked):
            return False

    # Allow by extension
    if path.suffix.lower() in SYNC_ALLOWED_EXTENSIONS:
        return True

    # Allow specific filenames
    if name in SYNC_ALLOWED_FILES:
        return True

    return False


def stage_allowed_files(vault: Path) -> list[str]:
    """Stage only allowed files for commit. Returns list of staged files."""
    changed = get_changed_files(vault)
    staged = []

    for f in changed:
        if is_sync_allowed(f):
            run_git(["add", f], vault, check=False)
            staged.append(f)
        else:
            log.debug(f"Skipping (not sync-allowed): {f}")

    return staged


def write_sync_status(vault: Path, status: dict) -> None:
    """Write sync status to Updates/sync_status.json."""
    updates_dir = vault / "Updates"
    updates_dir.mkdir(parents=True, exist_ok=True)
    status_file = updates_dir / "sync_status.json"
    status_file.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Sync operations ───────────────────────────────────────────────────────────

def push(vault: Path, message: str | None = None) -> dict:
    """
    Commit allowed changes and push to remote.
    Returns status dict.
    """
    if not is_git_repo(vault):
        return {"success": False, "error": "Not a git repository. Run: git init && git remote add origin <url>"}

    staged = stage_allowed_files(vault)

    if not staged:
        log.info("Nothing to commit (no allowed files changed).")
        return {"success": True, "committed": 0, "pushed": False, "files": []}

    # Commit
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    commit_msg = message or f"[{AGENT_ID}] Auto-sync {timestamp}"
    run_git(["commit", "-m", commit_msg], vault)
    log.info(f"Committed {len(staged)} file(s): {commit_msg}")

    # Push
    if has_remote(vault):
        result = run_git(["push", "--quiet"], vault, check=False)
        if result.returncode == 0:
            log.info("Push successful.")
            pushed = True
        else:
            log.warning(f"Push failed: {result.stderr.strip()}")
            pushed = False
    else:
        log.warning("No remote configured. Commit saved locally only.")
        pushed = False

    return {
        "success": True,
        "committed": len(staged),
        "pushed": pushed,
        "files": staged,
        "message": commit_msg,
    }


def pull(vault: Path) -> dict:
    """
    Pull remote changes (fast-forward only to avoid conflicts).
    Returns status dict.
    """
    if not is_git_repo(vault):
        return {"success": False, "error": "Not a git repository."}

    if not has_remote(vault):
        return {"success": True, "pulled": 0, "note": "No remote configured."}

    # Fetch
    run_git(["fetch", "--quiet"], vault, check=False)

    # Check if behind remote
    result = run_git(["rev-list", "--count", "HEAD..@{u}"], vault, check=False)
    behind = int(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip().isdigit() else 0

    if behind == 0:
        log.info("Already up to date.")
        return {"success": True, "pulled": 0}

    # Fast-forward merge
    result = run_git(["merge", "--ff-only", "@{u}"], vault, check=False)
    if result.returncode == 0:
        log.info(f"Pulled {behind} new commit(s).")
        return {"success": True, "pulled": behind}
    else:
        log.warning(f"Cannot fast-forward. Diverged history. Manual merge needed.\n{result.stderr.strip()}")
        return {"success": False, "error": "Diverged history — manual merge required.", "behind": behind}


def sync(vault: Path, message: str | None = None) -> dict:
    """Pull then push — full bidirectional sync."""
    pull_result = pull(vault)
    push_result = push(vault, message)
    return {"pull": pull_result, "push": push_result}


def status(vault: Path) -> dict:
    """Show what would be synced without making changes."""
    if not is_git_repo(vault):
        return {"error": "Not a git repository."}

    changed = get_changed_files(vault)
    will_sync = [f for f in changed if is_sync_allowed(f)]
    will_skip = [f for f in changed if not is_sync_allowed(f)]

    result = run_git(["rev-list", "--count", "HEAD..@{u}"], vault, check=False)
    behind = int(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip().isdigit() else 0

    return {
        "changed_total": len(changed),
        "will_sync": will_sync,
        "will_skip": will_skip,
        "behind_remote": behind,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Vault Git Sync — secure markdown-only sync between Local and Cloud"
    )
    parser.add_argument(
        "--vault-path",
        default=str(DEFAULT_VAULT),
        help="Path to vault root",
    )
    parser.add_argument(
        "--mode",
        choices=["push", "pull", "sync", "status"],
        default="sync",
        help="Sync mode (default: sync = pull then push)",
    )
    parser.add_argument(
        "--message", "-m",
        default=None,
        help="Custom commit message",
    )
    parser.add_argument(
        "--agent-id",
        default=AGENT_ID,
        help="Agent identifier for commit messages (cloud / local)",
    )
    return parser.parse_args()


def main() -> None:
    global AGENT_ID
    args = parse_args()
    AGENT_ID = args.agent_id
    vault = Path(args.vault_path).resolve()

    if not vault.exists():
        log.error(f"Vault path does not exist: {vault}")
        sys.exit(1)

    log.info(f"Vault Sync — mode={args.mode} agent={AGENT_ID} vault={vault}")

    if args.mode == "push":
        result = push(vault, args.message)
    elif args.mode == "pull":
        result = pull(vault)
    elif args.mode == "sync":
        result = sync(vault, args.message)
    elif args.mode == "status":
        result = status(vault)
        print(json.dumps(result, indent=2))
        return

    # Write status to Updates/ so Dashboard can read it
    write_sync_status(vault, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": AGENT_ID,
        "mode": args.mode,
        "result": result,
    })

    success = result.get("success", result.get("push", {}).get("success", False))
    if not success:
        log.error(f"Sync failed: {result}")
        sys.exit(1)

    log.info(f"Sync complete: {result}")


if __name__ == "__main__":
    main()
