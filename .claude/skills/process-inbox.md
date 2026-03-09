# Skill: Process Inbox

## Purpose
Scan all files in `/Needs_Action`, analyse each one, take appropriate action
(or write an approval request), then move each file to `/Done`.

## Trigger
Run this skill when:
- The filesystem watcher has created new files in `/Needs_Action`
- The user asks you to process pending items

## Steps

1. **Read `Company_Handbook.md`** to recall the current rules and thresholds.

2. **List all `.md` files in `/Needs_Action`** that have `status: pending`.

3. **For each file**, read its frontmatter and content, then:
   - Determine the `type` (file_drop, email, task, etc.)
   - Assess priority (critical / high / normal / low) using the handbook rules
   - Decide: **auto-process** or **send to `/Pending_Approval`**

4. **Auto-process** (no approval needed) if:
   - It is a file triage, categorisation, or summary task
   - No external communication or financial action is involved

5. **Create approval file** in `/Pending_Approval` if the action:
   - Involves sending any message or email
   - Involves any financial amount > $50
   - Involves an unknown contact
   - Is otherwise flagged in the handbook

6. **Update the item's frontmatter**: set `status: processed` or `status: awaiting_approval`.

7. **Move processed files** to `/Done/`.

8. **Update `Dashboard.md`**:
   - Decrement "Needs Action" count
   - Increment "Completed Today"
   - Add a row to the Recent Activity Log

9. **Report back** a summary: how many items processed, how many sent to approval.

## Example Output
```
Processed 3 items from /Needs_Action:
  ✅ FILE_2026-03-04_120000_report.md — categorised as document, moved to /Done
  ✅ FILE_2026-03-04_121500_invoice.md — approval request created in /Pending_Approval
  ✅ FILE_2026-03-04_130000_notes.md — categorised as notes, moved to /Done

Dashboard updated. 1 item awaiting your approval.
```
