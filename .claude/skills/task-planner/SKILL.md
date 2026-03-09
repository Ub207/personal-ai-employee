# Skill: task-planner

## Purpose
Read tasks from Inbox and generate structured execution plans before acting.
AI reasons first, acts second — never skip planning.

## Trigger
Run when a new file appears in `/Inbox/` or `/Needs_Action/`

## Workflow
1. Read the task file from `/Inbox/` or `/Needs_Action/`
2. Analyze intent — what does the task actually require?
3. Break into numbered steps
4. Assign priority: High / Medium / Low
5. Decide: does this require human approval? (Yes/No)
6. Write `Plan_<timestamp>_<task>.md` to `/Needs_Action/`
7. Update Dashboard.md

## Plan File Format
```markdown
---
created: 2026-03-09 09:00
priority: High
requires_approval: Yes
status: PLANNED
---

# Task Plan: <title>

## Original Task
<paste original task content>

## Objective
<one sentence — what success looks like>

## Step-by-Step Plan
1. ...
2. ...
3. ...

## Priority
High — client-facing, time-sensitive

## Requires Human Approval?
Yes — involves sending external email

## Suggested Output
Draft email saved to /Pending_Approval/email/
```

## Rules
- Do NOT execute the task — only plan
- Flag anything involving external communication as requiring approval
- Keep plans concise (under 300 words)
- One plan file per task
