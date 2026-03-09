#!/usr/bin/env python3
"""
weekly_audit.py — Gold Tier Weekly Business & Accounting Audit
==============================================================
Generates the Monday Morning CEO Briefing with full business + financial snapshot.

Usage:
    python weekly_audit.py [--vault-path D:/bronze_tier] [--dry-run]

Output:
    /Briefings/YYYY-MM-DD_Weekly_CEO_Briefing.md
"""

import os
import sys
import json
import re
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# ── Configuration ─────────────────────────────────────────────────────────────

SUBSCRIPTION_STALE_DAYS = 30  # Flag subscriptions unused > this many days

# ── Argument Parsing ──────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Weekly Business & Accounting Audit")
    parser.add_argument(
        "--vault-path",
        default=os.environ.get("VAULT_PATH", "D:/bronze_tier"),
        help="Path to the vault root directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.environ.get("DRY_RUN", "false").lower() == "true",
        help="Dry run — print report but do not save",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Audit window in days (default: 7)",
    )
    return parser.parse_args()

# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_read_json(file_path: Path) -> Any:
    """Read JSON file, return None on any error."""
    if not file_path.exists():
        return None
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None

def count_md_files(directory: Path) -> int:
    if not directory.exists():
        return 0
    return len(list(directory.glob("*.md")))

def list_md_files_with_frontmatter(directory: Path) -> list[dict]:
    """Read all .md files in a directory, parse basic frontmatter."""
    items = []
    if not directory.exists():
        return items

    for md_file in sorted(directory.glob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
            item = {"filename": md_file.name, "content": content, "frontmatter": {}}

            # Parse YAML-like frontmatter between --- markers
            if content.startswith("---"):
                end = content.find("\n---", 3)
                if end != -1:
                    fm_text = content[3:end]
                    for line in fm_text.splitlines():
                        if ":" in line:
                            key, _, val = line.partition(":")
                            item["frontmatter"][key.strip()] = val.strip()
            items.append(item)
        except Exception:
            pass
    return items

def parse_iso_date(s: str) -> datetime | None:
    """Try to parse an ISO date/datetime string."""
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(s[:len(fmt)], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None

# ── Data Collectors ───────────────────────────────────────────────────────────

def collect_done_items(vault_path: Path, days: int) -> dict:
    """Count and categorize items completed this week."""
    done_dir = vault_path / "Done"
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    items = list_md_files_with_frontmatter(done_dir)

    this_week = []
    by_type: dict[str, int] = {}

    for item in items:
        # Try to get completion date from frontmatter or file mtime
        date_str = item["frontmatter"].get("completed", "") or item["frontmatter"].get("received", "")
        item_date = parse_iso_date(date_str)

        if item_date is None:
            # Fall back to file modification time
            try:
                mtime = (done_dir / item["filename"]).stat().st_mtime
                item_date = datetime.fromtimestamp(mtime, tz=timezone.utc)
            except Exception:
                item_date = datetime.now(timezone.utc)

        if item_date >= cutoff:
            this_week.append(item)
            item_type = item["frontmatter"].get("type", "unknown")
            by_type[item_type] = by_type.get(item_type, 0) + 1

    return {
        "total": len(this_week),
        "by_type": by_type,
        "items": [i["filename"] for i in this_week[-20:]],  # last 20
    }

def collect_pending_approvals(vault_path: Path) -> dict:
    """List items awaiting approval and their age."""
    pending_dir = vault_path / "Pending_Approval"
    now = datetime.now(timezone.utc)
    items = list_md_files_with_frontmatter(pending_dir)
    result = []

    for item in items:
        date_str = item["frontmatter"].get("created", "")
        item_date = parse_iso_date(date_str)
        if item_date is None:
            try:
                mtime = (pending_dir / item["filename"]).stat().st_mtime
                item_date = datetime.fromtimestamp(mtime, tz=timezone.utc)
            except Exception:
                item_date = now

        age_hours = (now - item_date).total_seconds() / 3600
        result.append({
            "filename": item["filename"],
            "type": item["frontmatter"].get("type", "unknown"),
            "priority": item["frontmatter"].get("priority", "normal"),
            "age_hours": round(age_hours, 1),
            "age_str": f"{int(age_hours)}h" if age_hours < 48 else f"{int(age_hours // 24)}d",
        })

    result.sort(key=lambda x: x["age_hours"], reverse=True)
    return {"count": len(result), "items": result}

def collect_needs_action(vault_path: Path) -> dict:
    """Count items in Needs_Action backlog."""
    needs_action_dir = vault_path / "Needs_Action"
    items = list_md_files_with_frontmatter(needs_action_dir)
    pending = [i for i in items if i["frontmatter"].get("status", "pending") == "pending"]
    return {"total": len(items), "pending": len(pending)}

def collect_odoo_financials(vault_path: Path, days: int) -> dict:
    """Parse Logs/odoo_actions.json for financial transactions this week."""
    log_file = vault_path / "Logs" / "odoo_actions.json"
    log_data = safe_read_json(log_file)

    if not log_data:
        return {"available": False, "note": "No Odoo action log found. Connect Odoo to see financials."}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = []

    for entry in log_data:
        ts_str = entry.get("timestamp", "")
        ts = parse_iso_date(ts_str)
        if ts and ts >= cutoff:
            recent.append(entry)

    # Summarize by tool
    by_tool: dict[str, int] = {}
    success_count = 0
    error_count = 0
    invoices_created = []
    revenue_queries = []

    for entry in recent:
        tool = entry.get("tool", "unknown")
        result = entry.get("result", "unknown")
        by_tool[tool] = by_tool.get(tool, 0) + 1
        if result == "success":
            success_count += 1
        elif result == "error":
            error_count += 1
        if tool == "create_invoice" and result == "success":
            invoices_created.append(entry)
        if tool in ("get_revenue_summary", "get_accounting_summary"):
            revenue_queries.append(entry)

    return {
        "available": True,
        "period_days": days,
        "total_actions": len(recent),
        "successful": success_count,
        "errors": error_count,
        "by_tool": by_tool,
        "invoices_created_count": len(invoices_created),
        "note": f"Data from Logs/odoo_actions.json ({len(recent)} actions this period)",
    }

def collect_social_activity(vault_path: Path, days: int) -> dict:
    """Parse Logs/social_actions.json for social media activity."""
    log_file = vault_path / "Logs" / "social_actions.json"
    log_data = safe_read_json(log_file)

    if not log_data:
        return {"available": False, "note": "No social action log found."}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = [e for e in log_data if parse_iso_date(e.get("timestamp", "")) and
              (parse_iso_date(e.get("timestamp", "")) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff]

    by_platform: dict[str, int] = {}
    errors = 0

    for entry in recent:
        platform = entry.get("platform", "unknown")
        result = entry.get("result", "")
        if result == "error":
            errors += 1
        else:
            by_platform[platform] = by_platform.get(platform, 0) + 1

    return {
        "available": True,
        "period_days": days,
        "total_posts": sum(by_platform.values()),
        "by_platform": by_platform,
        "errors": errors,
    }

def collect_audit_events(vault_path: Path, days: int) -> dict:
    """Read audit logs from Logs/audit_*.json files."""
    logs_dir = vault_path / "Logs"
    if not logs_dir.exists():
        return {"available": False}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    all_entries = []

    for audit_file in sorted(logs_dir.glob("audit_*.json")):
        data = safe_read_json(audit_file)
        if not isinstance(data, list):
            continue
        for entry in data:
            ts = parse_iso_date(entry.get("timestamp", ""))
            if ts and ts >= cutoff:
                all_entries.append(entry)

    if not all_entries:
        return {"available": False, "note": "No audit events found for this period."}

    errors = [e for e in all_entries if e.get("event") == "error"]
    actions = [e for e in all_entries if e.get("event") == "action"]

    by_source: dict[str, int] = {}
    for entry in actions:
        src = entry.get("source", "unknown")
        by_source[src] = by_source.get(src, 0) + 1

    return {
        "available": True,
        "total_events": len(all_entries),
        "actions": len(actions),
        "errors": len(errors),
        "by_source": by_source,
    }

def collect_subscriptions(vault_path: Path) -> list[dict]:
    """Parse Company_Handbook.md for Active Subscriptions section."""
    handbook = vault_path / "Company_Handbook.md"
    if not handbook.exists():
        return []

    content = handbook.read_text(encoding="utf-8")

    # Find Active Subscriptions section
    pattern = re.compile(r"##\s*Active Subscriptions(.*?)(?=\n##|\Z)", re.DOTALL | re.IGNORECASE)
    match = pattern.search(content)
    if not match:
        return []

    section = match.group(1)
    subs = []

    # Look for table rows or list items with subscription info
    # Handles markdown table: | Name | Cost | Last Used |
    table_row = re.compile(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
    for row in table_row.finditer(section):
        name, cost, last_used = row.group(1), row.group(2), row.group(3)
        if name.lower() in ("name", "service", "subscription", "tool"):
            continue  # header row

        last_used_date = parse_iso_date(last_used.strip())
        days_since = None
        stale = False

        if last_used_date:
            days_since = (datetime.now(timezone.utc) - last_used_date).days
            stale = days_since > SUBSCRIPTION_STALE_DAYS

        subs.append({
            "name": name.strip(),
            "cost": cost.strip(),
            "last_used": last_used.strip(),
            "days_since": days_since,
            "stale": stale,
        })

    # Also handle bullet list format: - SubscriptionName: $X/month
    bullet = re.compile(r"-\s+(.+?):\s*(\$[\d.]+(?:/\w+)?)")
    for m in bullet.finditer(section):
        name, cost = m.group(1).strip(), m.group(2).strip()
        if not any(s["name"] == name for s in subs):
            subs.append({"name": name, "cost": cost, "last_used": "unknown", "days_since": None, "stale": False})

    return subs

def collect_health_status(vault_path: Path) -> dict:
    """Read vault/health_status.json."""
    health_file = vault_path / "vault" / "health_status.json"
    data = safe_read_json(health_file)
    if not data:
        return {"available": False}
    return {"available": True, **data}

# ── Report Generator ──────────────────────────────────────────────────────────

def generate_weekly_briefing(vault_path: Path, days: int) -> str:
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=days)
    date_str = now.strftime("%Y-%m-%d")
    weekday = now.strftime("%A")

    print("Collecting data…")
    done = collect_done_items(vault_path, days)
    pending = collect_pending_approvals(vault_path)
    backlog = collect_needs_action(vault_path)
    financials = collect_odoo_financials(vault_path, days)
    social = collect_social_activity(vault_path, days)
    audit = collect_audit_events(vault_path, days)
    subscriptions = collect_subscriptions(vault_path)
    health = collect_health_status(vault_path)
    stale_subs = [s for s in subscriptions if s.get("stale")]

    # ── Build Report ──────────────────────────────────────────────────────────
    lines = [
        "---",
        f"generated: {now.isoformat()}",
        f"period: {week_start.strftime('%Y-%m-%d')} to {date_str}",
        "type: weekly_ceo_briefing",
        f"audit_days: {days}",
        "---",
        "",
        f"# {weekday} Morning CEO Briefing — {date_str}",
        f"**Period:** {week_start.strftime('%B %d')} – {now.strftime('%B %d, %Y')}",
        "",
        "## Executive Summary",
        (
            f"This week, the AI Employee completed **{done['total']} tasks**, "
            f"with **{pending['count']} items** still awaiting your approval. "
            f"{f'There are **{stale_subs}** subscriptions flagged for review. ' if stale_subs else ''}"
            f"System health: "
            + (f"{sum(1 for p in health.get('processes', []) if p.get('alive', False))}/{len(health.get('processes', []))} watchers running." if health.get('available') else "Health data unavailable.")
        ),
        "",
        "---",
        "",
        "## Completed This Week",
        f"**Total Completed:** {done['total']} items",
        "",
        "### By Type",
        "| Type | Count |",
        "|------|-------|",
    ]
    if done["by_type"]:
        for t, c in sorted(done["by_type"].items(), key=lambda x: -x[1]):
            lines.append(f"| {t} | {c} |")
    else:
        lines.append("| — | No items completed this week |")

    if done["items"]:
        lines += ["", "### Recent Completions (last 10)"]
        for item in done["items"][-10:]:
            lines.append(f"- {item}")

    lines += [
        "",
        "---",
        "",
        f"## Pending Approvals ({pending['count']})",
    ]

    if pending["items"]:
        lines += [
            "| Item | Type | Priority | Age |",
            "|------|------|----------|-----|",
        ]
        for item in pending["items"][:15]:
            lines.append(
                f"| {item['filename'][:50]} | {item['type']} | {item['priority']} | {item['age_str']} |"
            )
        if pending["count"] > 15:
            lines.append(f"*…and {pending['count'] - 15} more items*")
    else:
        lines.append("No pending approvals. ✅")

    lines += [
        "",
        "---",
        "",
        f"## Backlog ({backlog['pending']} pending items in /Needs_Action)",
    ]
    if backlog["pending"] > 0:
        lines.append(f"⚠️ {backlog['pending']} unprocessed items need attention.")
    else:
        lines.append("Backlog is clear. ✅")

    lines += [
        "",
        "---",
        "",
        "## Financial Snapshot",
    ]

    if financials.get("available"):
        lines += [
            "| Metric | Value |",
            "|--------|-------|",
            f"| Odoo Actions This Week | {financials['total_actions']} |",
            f"| Successful Actions | {financials['successful']} |",
            f"| Errors | {financials['errors']} |",
            f"| Invoices Created | {financials['invoices_created_count']} |",
            "",
            "### Odoo Actions by Tool",
            "| Tool | Count |",
            "|------|-------|",
        ]
        for tool, count in sorted(financials.get("by_tool", {}).items(), key=lambda x: -x[1]):
            lines.append(f"| {tool} | {count} |")
        lines.append(f"\n*{financials['note']}*")
    else:
        lines += [
            "No Odoo financial data available.",
            "",
            "> **Action Required:** Ensure the Odoo MCP server is running and connected.",
            f"> Note: {financials.get('note', '')}",
        ]

    lines += [
        "",
        "---",
        "",
        "## Social Media Activity",
    ]

    if social.get("available"):
        lines += [
            f"**Total posts this week:** {social['total_posts']}",
            "",
            "| Platform | Posts |",
            "|----------|-------|",
        ]
        for platform, count in sorted(social.get("by_platform", {}).items(), key=lambda x: -x[1]):
            lines.append(f"| {platform.title()} | {count} |")
        if social.get("errors", 0) > 0:
            lines.append(f"\n⚠️ {social['errors']} posting errors — review Logs/social_actions.json")
    else:
        lines.append("No social media data available. Social MCP server may not be running.")

    lines += [
        "",
        "---",
        "",
        "## System Health",
    ]

    if health.get("available"):
        processes = health.get("processes", [])
        alive = [p for p in processes if p.get("alive")]
        down = [p for p in processes if not p.get("alive") and not p.get("disabled")]
        disabled_procs = [p for p in processes if p.get("disabled")]

        lines += [
            f"**Watchers running:** {len(alive)}/{len(processes)}",
            "",
            "| Watcher | Status | Restarts (1h) |",
            "|---------|--------|---------------|",
        ]
        for p in processes:
            icon = "🟢" if p.get("alive") else ("⚫" if p.get("disabled") else "🔴")
            restarts = p.get("restarts_this_hour", 0)
            lines.append(f"| {p['name']} | {icon} {p['status']} | {restarts} |")

        if disabled_procs:
            lines.append(f"\n🚨 **{len(disabled_procs)} watcher(s) DISABLED** due to crash loops — check Pending_Approval/")
        if down:
            lines.append(f"\n⚠️ **{len(down)} watcher(s) currently down** — health monitor may restart them")
        else:
            lines.append("\nAll monitored watchers are healthy. ✅")
    else:
        lines.append("Health status unavailable — health_monitor.py may not be running.")

    lines += [
        "",
        "---",
        "",
        "## Subscription Audit",
    ]

    if subscriptions:
        lines += [
            "| Service | Cost | Last Used | Days Idle | Status |",
            "|---------|------|-----------|-----------|--------|",
        ]
        for sub in subscriptions:
            days_idle = str(sub.get("days_since", "—"))
            status = "⚠️ STALE" if sub.get("stale") else "✅ Active"
            lines.append(f"| {sub['name']} | {sub['cost']} | {sub['last_used']} | {days_idle} | {status} |")

        if stale_subs:
            lines.append(f"\n⚠️ **{len(stale_subs)} subscription(s)** unused for {SUBSCRIPTION_STALE_DAYS}+ days — consider cancelling:")
            for sub in stale_subs:
                lines.append(f"  - **{sub['name']}** ({sub['cost']}) — idle {sub.get('days_since', '?')} days")
        else:
            lines.append("\nAll subscriptions appear active. ✅")
    else:
        lines += [
            "No subscription data found in Company_Handbook.md.",
            "",
            "> Add an 'Active Subscriptions' section with a table to track usage.",
        ]

    lines += [
        "",
        "---",
        "",
        "## Audit Trail Summary",
    ]

    if audit.get("available"):
        lines += [
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Events | {audit['total_events']} |",
            f"| Actions | {audit['actions']} |",
            f"| Errors | {audit['errors']} |",
        ]
        if audit.get("by_source"):
            lines += ["", "| Component | Events |", "|-----------|--------|"]
            for src, count in sorted(audit["by_source"].items(), key=lambda x: -x[1]):
                lines.append(f"| {src} | {count} |")
    else:
        lines.append(f"No audit events found. {audit.get('note', '')}")

    lines += [
        "",
        "---",
        "",
        "## Recommended Actions",
        "",
    ]

    action_num = 1
    if pending["count"] > 0:
        lines.append(f"{action_num}. **Review {pending['count']} pending approval(s)** in /Pending_Approval/")
        action_num += 1
    if backlog["pending"] > 5:
        lines.append(f"{action_num}. **Process backlog** — {backlog['pending']} items in /Needs_Action/")
        action_num += 1
    if stale_subs:
        lines.append(f"{action_num}. **Review stale subscriptions** — {len(stale_subs)} service(s) idle > {SUBSCRIPTION_STALE_DAYS} days")
        action_num += 1
    if health.get("available"):
        disabled_count = sum(1 for p in health.get("processes", []) if p.get("disabled"))
        if disabled_count > 0:
            lines.append(f"{action_num}. **Fix disabled watcher(s)** — {disabled_count} process(es) need manual intervention")
            action_num += 1
    if action_num == 1:
        lines.append("No immediate actions required. 🎉")

    lines += [
        "",
        "---",
        f"*Generated by weekly_audit.py at {now.isoformat()}*",
        f"*AI Employee — Gold Tier*",
    ]

    return "\n".join(lines)

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    vault_path = Path(args.vault_path).resolve()
    dry_run = args.dry_run

    print(f"Weekly Audit — Vault: {vault_path}")
    print(f"Period: last {args.days} days")

    report = generate_weekly_briefing(vault_path, args.days)

    if dry_run:
        print("\n[DRY RUN] Report (not saved):\n")
        print(report)
        return

    briefings_dir = vault_path / "Briefings"
    briefings_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_file = briefings_dir / f"{date_str}_Weekly_CEO_Briefing.md"
    output_file.write_text(report, encoding="utf-8")

    print(f"\nBriefing saved to: {output_file}")

    # Update Dashboard.md
    dashboard = vault_path / "Dashboard.md"
    if dashboard.exists():
        try:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            content = dashboard.read_text(encoding="utf-8")
            log_line = f"| {ts} | Weekly CEO Briefing generated | weekly_audit |\n"
            if "## Recent Activity" in content:
                idx = content.find("\n", content.find("## Recent Activity")) + 1
                content = content[:idx] + log_line + content[idx:]
            else:
                content += f"\n## Recent Activity\n{log_line}"
            dashboard.write_text(content, encoding="utf-8")
            print("Dashboard.md updated.")
        except Exception as exc:
            print(f"Warning: Could not update Dashboard.md: {exc}")


if __name__ == "__main__":
    main()
