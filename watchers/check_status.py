"""
check_status.py — Bronze Tier Health Check
Run this anytime to see the full status of your AI Employee.
Usage: python d:/bronze_tier/watchers/check_status.py
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

VAULT = Path("D:/bronze_tier")

def count_files(folder):
    p = VAULT / folder
    if not p.exists():
        return 0, "MISSING"
    files = [f for f in p.iterdir() if f.is_file()]
    return len(files), "OK"

def check_watcher_running():
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
        capture_output=True, text=True
    )
    # Simple check — if filesystem_watcher is in any python process
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'cmdline']):
            cmdline = proc.info.get('cmdline') or []
            if any('filesystem_watcher' in c for c in cmdline):
                return True, f"RUNNING (PID {proc.pid})"
    except ImportError:
        pass
    return False, "NOT RUNNING"

def main():
    print("=" * 55)
    print("  AI Employee — Bronze Tier Status Check")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # Folder counts
    inbox_count, inbox_status = count_files("Inbox")
    needs_count, needs_status = count_files("Needs_Action")
    done_count, done_status   = count_files("Done")
    pend_count, pend_status   = count_files("Pending_Approval")

    print(f"\nVAULT FOLDERS")
    print(f"  Inbox          : {inbox_count} files  {inbox_status}")
    print(f"  Needs_Action   : {needs_count} files  {needs_status}")
    print(f"  Done           : {done_count} files  {done_status}")
    print(f"  Pending_Approval: {pend_count} files {pend_status}")

    # Watcher status
    running, watcher_status = check_watcher_running()
    print(f"\nWATCHER")
    print(f"  Filesystem Watcher : {watcher_status}")

    # Key files
    print(f"\nKEY FILES")
    for fname in ["Dashboard.md", "Company_Handbook.md", "CLAUDE.md"]:
        exists = (VAULT / fname).exists()
        print(f"  {fname:<25} {'OK' if exists else 'MISSING'}")

    # Skills
    print(f"\nSKILLS")
    for skill in ["process-inbox.md", "update-dashboard.md", "daily-briefing.md"]:
        exists = (VAULT / ".claude" / "skills" / skill).exists()
        print(f"  {skill:<30} {'OK' if exists else 'MISSING'}")

    # Summary
    print(f"\n{'=' * 55}")
    if needs_count > 0:
        print(f"  !! {needs_count} file(s) in Needs_Action — process karo!")
    elif inbox_count > 0:
        print(f"  !! {inbox_count} file(s) in Inbox — watcher chala ke drop karo.")
    else:
        print(f"  OK All clear — system ready.")

    if not running:
        print(f"\n  >> Watcher start karo:")
        print(f"     python D:\\bronze_tier\\watchers\\filesystem_watcher.py")
    print("=" * 55)

if __name__ == "__main__":
    main()
