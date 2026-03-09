#!/usr/bin/env python3
"""
ralph_wiggum_hook.py — Gold Tier Stop Hook
==========================================
Claude Code stop hook that checks whether the current vault task is complete.
Named after Ralph Wiggum: "I'm helping! Are we done yet?"

This script is invoked by Claude Code as a stop hook.
Exit code 0 = allow Claude to stop.
Non-zero exit code = Claude should continue (task incomplete).

Task state file: vault/current_task.json
Format:
    {
        "task": "Task description",
        "created": "2026-03-09T10:00:00Z",
        "steps": [
            {"action": "Read Company_Handbook.md", "status": "complete"},
            {"action": "Process inbox items", "status": "pending"},
            {"action": "Update Dashboard.md", "status": "pending"}
        ]
    }

Usage:
    # As a hook (Claude Code calls this automatically):
    python ralph_wiggum_hook.py

    # Create a task:
    python ralph_wiggum_hook.py --create-task "Process this week's emails" \
        "Read inbox" "Categorize emails" "Update dashboard"

    # Complete a step (by index):
    python ralph_wiggum_hook.py --complete-step 0

    # Show current task:
    python ralph_wiggum_hook.py --status

    # Clear current task:
    python ralph_wiggum_hook.py --clear
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path


# ── Constants ─────────────────────────────────────────────────────────────────

VAULT_PATH = Path(os.environ.get("VAULT_PATH", "D:/bronze_tier")).resolve()
TASK_FILE = VAULT_PATH / "vault" / "current_task.json"

# ── Task State Management ─────────────────────────────────────────────────────

def load_task() -> dict | None:
    """Load current task state. Returns None if no task file exists."""
    if not TASK_FILE.exists():
        return None
    try:
        data = json.loads(TASK_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "steps" not in data:
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def save_task(task: dict) -> None:
    """Persist task state to disk."""
    TASK_FILE.parent.mkdir(parents=True, exist_ok=True)
    TASK_FILE.write_text(json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8")


def create_task(task_name: str, steps: list[str]) -> dict:
    """
    Create a new task with the given steps and save it to vault/current_task.json.

    Args:
        task_name: Human-readable task description
        steps:     List of step action descriptions

    Returns:
        The created task dict
    """
    task = {
        "task": task_name,
        "created": datetime.now(timezone.utc).isoformat(),
        "steps": [{"action": step, "status": "pending"} for step in steps],
    }
    save_task(task)
    return task


def complete_step(step_index: int) -> dict | None:
    """
    Mark a step as complete by index.

    Returns:
        Updated task dict, or None if task/step not found.
    """
    task = load_task()
    if task is None:
        return None

    steps = task.get("steps", [])
    if step_index < 0 or step_index >= len(steps):
        return None

    steps[step_index]["status"] = "complete"
    steps[step_index]["completed_at"] = datetime.now(timezone.utc).isoformat()
    task["steps"] = steps
    save_task(task)
    return task


def get_incomplete_steps(task: dict) -> list[dict]:
    """Return list of steps that are not yet complete."""
    return [s for s in task.get("steps", []) if s.get("status") != "complete"]


def is_task_complete(task: dict) -> bool:
    """Return True if all steps are marked complete."""
    steps = task.get("steps", [])
    if not steps:
        return True
    return all(s.get("status") == "complete" for s in steps)


def clear_task() -> None:
    """Remove the current task file."""
    if TASK_FILE.exists():
        TASK_FILE.unlink()


# ── Hook Logic (default mode) ─────────────────────────────────────────────────

def run_hook() -> int:
    """
    Main hook logic.

    Returns:
        0 if Claude may stop (task complete or no task).
        1 if Claude should continue (task has incomplete steps).
    """
    task = load_task()

    # No task file — allow Claude to stop
    if task is None:
        return 0

    # Task complete — allow Claude to stop and clean up
    if is_task_complete(task):
        return 0

    # Task has incomplete steps — instruct Claude to continue
    incomplete = get_incomplete_steps(task)
    task_name = task.get("task", "current task")

    print(f"TASK INCOMPLETE: '{task_name}'")
    print(f"Remaining steps ({len(incomplete)}/{len(task['steps'])}):")
    for i, step in enumerate(incomplete, 1):
        print(f"  {i}. {step['action']}")
    print()
    print("Claude, please continue and complete the remaining steps before stopping.")
    print(f"Task file: {TASK_FILE}")
    print()
    print("To mark a step complete, call: python ralph_wiggum_hook.py --complete-step <index>")

    return 1  # Non-zero = Claude should continue


# ── CLI Interface ─────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ralph Wiggum Hook — task completeness checker for Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--create-task",
        nargs="+",
        metavar=("TASK_NAME", "STEP"),
        help="Create a new task. First arg is task name, rest are steps.",
    )
    group.add_argument(
        "--complete-step",
        type=int,
        metavar="INDEX",
        help="Mark step at INDEX (0-based) as complete",
    )
    group.add_argument(
        "--status",
        action="store_true",
        help="Show current task status and exit 0",
    )
    group.add_argument(
        "--clear",
        action="store_true",
        help="Clear the current task file",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.create_task:
        if len(args.create_task) < 1:
            print("Error: provide at least a task name.", file=sys.stderr)
            sys.exit(2)
        task_name = args.create_task[0]
        steps = args.create_task[1:] if len(args.create_task) > 1 else []
        task = create_task(task_name, steps)
        print(f"Created task: '{task_name}' with {len(steps)} step(s)")
        print(f"Saved to: {TASK_FILE}")
        for i, s in enumerate(task["steps"]):
            print(f"  [{i}] {s['action']} — {s['status']}")
        sys.exit(0)

    elif args.complete_step is not None:
        task = complete_step(args.complete_step)
        if task is None:
            print(f"Error: step {args.complete_step} not found or no active task.", file=sys.stderr)
            sys.exit(2)
        step = task["steps"][args.complete_step]
        print(f"Step {args.complete_step} marked complete: '{step['action']}'")
        incomplete = get_incomplete_steps(task)
        if incomplete:
            print(f"{len(incomplete)} step(s) remaining:")
            for s in incomplete:
                print(f"  - {s['action']}")
        else:
            print("All steps complete! Task done.")
        sys.exit(0)

    elif args.status:
        task = load_task()
        if task is None:
            print("No active task.")
            sys.exit(0)
        print(f"Task: {task['task']}")
        print(f"Created: {task.get('created', 'unknown')}")
        print(f"Steps ({len(task['steps'])} total):")
        for i, s in enumerate(task["steps"]):
            icon = "[DONE]" if s["status"] == "complete" else "[TODO]"
            completed_at = f" [{s.get('completed_at', '')}]" if s["status"] == "complete" else ""
            print(f"  [{i}] {icon} {s['action']}{completed_at}")
        incomplete = get_incomplete_steps(task)
        print(f"\nStatus: {'COMPLETE' if not incomplete else f'{len(incomplete)} step(s) remaining'}")
        sys.exit(0)

    elif args.clear:
        clear_task()
        print("Task cleared.")
        sys.exit(0)

    else:
        # Default: run as a hook
        exit_code = run_hook()
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
