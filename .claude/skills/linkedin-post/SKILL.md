# Skill: linkedin-post

## Purpose
Create and publish LinkedIn posts using browser automation (Playwright).

## Inputs
- `content` — the post text (max 3000 chars)
- `mode` — `draft` (save to /Pending_Approval/) or `post` (publish live)

## Workflow
1. Read post content from task or approval file
2. If mode=draft: save to `/Pending_Approval/social/` and stop
3. If mode=post (only after approval): run `python .claude/skills/linkedin-post/scripts/post_linkedin.py`
4. Log result to `/Logs/social_actions.json`
5. Move task to `/Done/`

## Rules
- NEVER post directly — always draft first
- Only publish after file is moved to `/Approved/`
- Keep posts professional and on-brand

## Environment Variables Required
- `LINKEDIN_EMAIL` — LinkedIn login email
- `LINKEDIN_PASSWORD` — LinkedIn password

## Example Usage
```
content: Excited to share our latest project update...
mode: draft
```
