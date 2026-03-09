# Skill: human-approval

## Purpose
Request human approval before executing sensitive actions.
Creates an approval file and waits for APPROVED or REJECTED response.

## When to Use
- Sending external emails
- Publishing social media posts
- Financial transactions
- Any irreversible action

## Workflow
1. Create approval file in `/Pending_Approval/` with full action details
2. Notify: update Dashboard.md "Pending Approvals" count
3. STOP — do not proceed until human responds
4. Run: `python .claude/skills/human-approval/scripts/request_approval.py --check`
5. If APPROVED → proceed with action skill
6. If REJECTED → log reason and move to Done

## Approval File Format
```markdown
---
action: send_email
status: PENDING
requested: 2026-03-09 09:00
---
# Approval Required: Send Email to client@example.com
**Action:** Send email
**To:** client@example.com
**Subject:** Project Update
**Body:** Hi, following up on...

To approve: add APPROVED to this file
To reject: add REJECTED + reason
```

## Rules
- One approval file per action
- Never auto-approve
- Log all approvals and rejections
