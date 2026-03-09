# Skill: gmail-send

## Purpose
Send real emails via Gmail SMTP on behalf of the AI Employee.

## Inputs
- `to` — recipient email address
- `subject` — email subject line
- `body` — plain text email body

## Workflow
1. Read `to`, `subject`, `body` from the task or approval file
2. Confirm `DRY_RUN=false` in `.env` before sending
3. Run: `python .claude/skills/gmail-send/scripts/send_email.py`
4. Log result to `/Logs/email_actions.json`
5. Move task to `/Done/`

## Rules
- NEVER send without human approval for external recipients
- Always place draft in `/Pending_Approval/email/` first
- Only send after file is moved to `/Approved/`

## Environment Variables Required
- `SMTP_HOST` — smtp.gmail.com
- `SMTP_PORT` — 587
- `SMTP_USER` — Gmail address
- `SMTP_PASS` — App Password (16 chars)

## Example Usage
```
to: client@example.com
subject: Follow-up on Project
body: Hi, just following up on our last conversation...
```
