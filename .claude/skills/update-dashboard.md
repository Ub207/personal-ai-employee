# Skill: Update Dashboard

## Purpose
Refresh `Dashboard.md` to reflect the current real state of the vault —
counts, statuses, pending approvals, and health indicators.

## Trigger
Run this skill:
- After processing any batch of inbox items
- After completing any significant action
- When the user asks for a status update

## Steps

1. **Count files** in each folder:
   - `/Inbox` — unprocessed drop files
   - `/Needs_Action` — pending `.md` files (status: pending)
   - `/Pending_Approval` — approval requests
   - `/Done` — completed today (files modified today)

2. **Check watcher status** by looking for a running PID or a health file
   written by `filesystem_watcher.py`. Report ⚪ Not Started / 🟢 Running / 🔴 Stopped.

3. **Read the last 5 entries** from the Recent Activity Log in `Dashboard.md`.

4. **Rewrite the Overview table** with the fresh counts.

5. **Update the "AI Employee Health" table** with current component statuses.

6. **Set `last_updated`** in the frontmatter to today's date.

7. Write the updated content back to `Dashboard.md`.

## Rules
- Never remove historical entries from the Recent Activity Log — only prepend new ones.
- Keep the Dashboard file under 200 lines; summarise older log entries if needed.
- Preserve all headers and table structure.

## Example Output
```
Dashboard updated:
  Inbox:            0 items
  Needs Action:     2 items
  Pending Approval: 1 item
  Done Today:       5 items
  Watcher:          ⚪ Not Started
```
