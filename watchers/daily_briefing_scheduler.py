"""
daily_briefing_scheduler.py — Silver Tier Scheduled Task
=========================================================
Generates daily CEO briefing every morning at 8 AM.
Run via Windows Task Scheduler or cron.

Usage:
    python daily_briefing_scheduler.py [--vault-path PATH]

Setup (Windows Task Scheduler):
    1. Open Task Scheduler
    2. Create Basic Task → "AI Employee Daily Briefing"
    3. Trigger: Daily at 8:00 AM
    4. Action: Start a program
       - Program: python.exe
       - Arguments: daily_briefing_scheduler.py --vault-path D:\bronze_tier
    5. Check "Run whether user is logged on or not"

Setup (Linux/Mac cron):
    0 8 * * * cd /path/to/vault && python daily_briefing_scheduler.py
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("DailyBriefing")

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_VAULT = Path(__file__).resolve().parent.parent  # D:/bronze_tier


# ── Briefing Generator ────────────────────────────────────────────────────────
class DailyBriefingGenerator:
    """Generates daily CEO briefing from vault data."""

    def __init__(self, vault_path: Path):
        self.vault = vault_path
        self.done = vault_path / "Done"
        self.pending = vault_path / "Pending_Approval"
        self.needs_action = vault_path / "Needs_Action"
        self.briefings = vault_path / "Briefings"
        self.handbook = vault_path / "Company_Handbook.md"

        # Ensure briefings folder exists
        self.briefings.mkdir(parents=True, exist_ok=True)

    def count_files(self, folder: Path, hours: int = 24) -> int:
        """Count files modified in last N hours."""
        if not folder.exists():
            return 0

        cutoff = datetime.now() - timedelta(hours=hours)
        count = 0
        for f in folder.glob("*.md"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime > cutoff:
                    count += 1
            except:
                continue
        return count

    def get_recent_done(self, days: int = 7) -> list[dict]:
        """Get recently completed items."""
        if not self.done.exists():
            return []

        cutoff = datetime.now() - timedelta(days=days)
        items = []

        for f in self.done.glob("*.md"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime > cutoff:
                    content = f.read_text(encoding="utf-8")
                    # Extract first line as title
                    first_line = content.split("\n")[0].replace("#", "").strip()[:100]
                    items.append({
                        "file": f.name,
                        "title": first_line,
                        "completed": mtime,
                    })
            except:
                continue

        return sorted(items, key=lambda x: x["completed"], reverse=True)

    def get_pending_approvals(self) -> list[dict]:
        """Get pending approval items with age."""
        if not self.pending.exists():
            return []

        items = []
        for f in self.pending.glob("*.md"):
            try:
                content = f.read_text(encoding="utf-8")
                # Extract frontmatter
                created = None
                action_type = "unknown"
                if "---" in content:
                    parts = content.split("---", 2)
                    if len(parts) >= 2:
                        fm = parts[1]
                        for line in fm.split("\n"):
                            if "created:" in line:
                                try:
                                    created = datetime.fromisoformat(
                                        line.split(":", 1)[1].strip()
                                    )
                                except:
                                    pass
                            if "type:" in line:
                                action_type = line.split(":", 1)[1].strip()

                age_days = (datetime.now() - created).days if created else 0

                items.append({
                    "file": f.name,
                    "type": action_type,
                    "age_days": age_days,
                    "created": created,
                })
            except:
                continue

        return items

    def get_backlog(self) -> list[dict]:
        """Get items in Needs_Action older than 24 hours."""
        if not self.needs_action.exists():
            return []

        cutoff = datetime.now() - timedelta(hours=24)
        items = []

        for f in self.needs_action.glob("*.md"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    content = f.read_text(encoding="utf-8")
                    first_line = content.split("\n")[0].replace("#", "").strip()[:100]
                    items.append({
                        "file": f.name,
                        "title": first_line,
                        "age_hours": int((datetime.now() - mtime).total_seconds() / 3600),
                    })
            except:
                continue

        return items

    def get_business_goals(self) -> dict:
        """Load business goals from handbook."""
        goals = {
            "monthly_goal": "$0",
            "mtd_revenue": "$0",
            "key_metrics": [],
        }

        if not self.handbook.exists():
            return goals

        content = self.handbook.read_text(encoding="utf-8")

        # Simple parsing - look for patterns
        for line in content.split("\n"):
            if "Monthly goal:" in line:
                goals["monthly_goal"] = line.split(":", 1)[1].strip()
            if "Current MTD:" in line:
                goals["mtd_revenue"] = line.split(":", 1)[1].strip()

        return goals

    def generate_briefing(self) -> str:
        """Generate the full briefing content."""
        today = datetime.now()
        weekday = today.strftime("%A")
        date_str = today.strftime("%Y-%m-%d")

        # Gather data
        done_items = self.get_recent_done(days=7)
        pending_items = self.get_pending_approvals()
        backlog_items = self.get_backlog()
        goals = self.get_business_goals()

        # Calculate stats
        done_count = len(done_items)
        pending_count = len(pending_items)
        backlog_count = len(backlog_items)

        # Executive summary
        if done_count > 5:
            summary = f"Highly productive week with {done_count} tasks completed."
        elif done_count > 2:
            summary = f"Steady progress with {done_count} tasks completed this week."
        else:
            summary = f"Light week with {done_count} tasks completed. Consider reviewing priorities."

        if pending_count > 3:
            summary += f" {pending_count} items awaiting your approval."
        if backlog_count > 2:
            summary += f" {backlog_count} items in backlog need attention."

        # Build content
        content = f"""---
generated: {today.isoformat()}
period: {(today - timedelta(days=7)).strftime('%Y-%m-%d')} to {date_str}
type: daily_briefing
weekday: {weekday}
---

# {weekday} Morning CEO Briefing — {date_str}

## Executive Summary
{summary}

---

## Completed This Week ({done_count} items)

"""

        if done_items:
            for item in done_items[:10]:  # Show last 10
                completed_date = item["completed"].strftime("%a %m/%d")
                content += f"- [{completed_date}] {item['title']}\n"
            if len(done_items) > 10:
                content += f"- _... and {len(done_items) - 10} more_\n"
        else:
            content += "_No tasks completed this week._\n"

        content += f"""
---

## Pending Approvals ({pending_count} items)

"""

        if pending_items:
            content += "| Item | Type | Age | Action Needed |\n"
            content += "|------|------|-----|---------------|\n"
            for item in pending_items:
                age_str = f"{item['age_days']} days" if item['age_days'] > 0 else "< 1 day"
                content += f"| {item['file'][:30]}... | {item['type']} | {age_str} | Review in /Pending_Approval |\n"
        else:
            content += "_No pending approvals — all clear!_\n"

        content += f"""
---

## Backlog ({backlog_count} items in /Needs_Action)

"""

        if backlog_items:
            for item in backlog_items[:5]:
                content += f"- ⚠️ {item['age_hours']}h: {item['title']}\n"
            if len(backlog_items) > 5:
                content += f"- _... and {len(backlog_items) - 5} more_\n"
        else:
            content += "_No backlog — inbox is clear!_\n"

        content += f"""
---

## Financial Snapshot

| Metric | Value | Status |
|--------|-------|--------|
| MTD Revenue | {goals['mtd_revenue']} | Update Bank_Transactions.md |
| Monthly Goal | {goals['monthly_goal']} | Set in Company_Handbook.md |

---

## Bottlenecks

"""

        # Identify bottlenecks (pending > 3 days)
        bottlenecks = [p for p in pending_items if p['age_days'] > 3]
        if bottlenecks:
            content += "The following items have been pending for over 3 days:\n\n"
            for item in bottlenecks:
                content += f"- ⚠️ **{item['file']}** ({item['age_days']} days) — consider reviewing\n"
        else:
            content += "_No bottlenecks detected._\n"

        content += f"""
---

## Proactive Suggestions

"""

        # Generate suggestions based on state
        suggestions = []

        if backlog_count > 5:
            suggestions.append("📋 **Backlog Alert:** Consider processing /Needs_Action folder to reduce clutter.")

        if pending_count == 0 and backlog_count == 0:
            suggestions.append("✅ **All Clear:** Great time to focus on strategic work or plan next quarter.")

        if done_count < 3:
            suggestions.append("📈 **Productivity:** Low completion count this week. Review priorities in Business_Goals.md?")

        if suggestions:
            for s in suggestions:
                content += f"{s}\n"
        else:
            content += "_No specific suggestions at this time._\n"

        content += f"""
---
*Generated by AI Employee v0.1 · Silver Tier*
"""

        return content

    def save_briefing(self, content: str) -> Path:
        """Save briefing to file."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        weekday = datetime.now().strftime("%A")
        filename = f"{date_str}_{weekday}_Briefing.md"
        filepath = self.briefings / filename

        filepath.write_text(content, encoding="utf-8")
        return filepath


# ── Runner ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Silver Tier Daily Briefing Generator — creates CEO briefing."
    )
    parser.add_argument(
        "--vault-path",
        default=str(DEFAULT_VAULT),
        help=f"Path to Obsidian vault (default: {DEFAULT_VAULT})",
    )
    args = parser.parse_args()

    vault = Path(args.vault_path).resolve()

    if not vault.exists():
        log.error(f"Vault path does not exist: {vault}")
        sys.exit(1)

    log.info("=" * 60)
    log.info("  AI Employee — Daily Briefing Generator  (Silver Tier)")
    log.info("=" * 60)
    log.info(f"  Vault: {vault}")
    log.info("=" * 60)

    generator = DailyBriefingGenerator(vault_path=vault)
    content = generator.generate_briefing()
    filepath = generator.save_briefing(content)

    log.info(f"Briefing generated: {filepath}")
    log.info("Briefing saved to /Briefings/ folder.")


if __name__ == "__main__":
    main()
