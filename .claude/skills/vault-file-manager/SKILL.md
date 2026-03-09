# Skill: vault-file-manager

## Purpose
Move task files between vault workflow folders.

## Workflow Folders
```
Inbox/ → Needs_Action/ → Pending_Approval/ → Approved/ → Done/
                       → Rejected/ → Done/
```

## Usage
Run: `python .claude/skills/vault-file-manager/scripts/move_task.py`

## Operations
- `inbox-to-action`   — Move new task from Inbox to Needs_Action
- `action-to-approval` — Move processed task to Pending_Approval
- `approve`           — Move from Approved to Done (after human approves)
- `reject`            — Move from Rejected to Done (log rejection)
- `complete`          — Move any file directly to Done

## Rules
- NEVER delete files permanently — always move to Done
- Log every move with timestamp in `/Logs/`
- Update Dashboard.md after each move

## Example
```
operation: inbox-to-action
filename: task_2026-03-09_client_email.md
```
