# Skill: Cloud Status

## Purpose
Check the health and sync status of the Cloud AI Employee agent.
Reads from `/Updates/sync_status.json` and `/vault/health_status.json`
to report whether the cloud is online, what it last processed, and
whether the vault is in sync.

## Trigger
Run this skill when:
- The user asks "is the cloud running?" or "what did cloud process?"
- Before checking /Pending_Approval/ to understand cloud activity
- After resuming local work after being offline

## Steps

1. **Read `/Updates/sync_status.json`** — last vault sync result:
   - Timestamp of last sync
   - Agent that pushed (cloud or local)
   - Number of files committed

2. **Read `/vault/health_status.json`** — cloud watcher health:
   - Which watchers are running
   - Last heartbeat timestamp
   - Any disabled watchers

3. **Read `/Updates/` folder** — last 5 A2A update files:
   - What events cloud reported (heartbeat, email_draft_created, etc.)
   - Timestamps of activity

4. **Count `/Pending_Approval/email/` and `/Pending_Approval/social/`**:
   - How many drafts cloud has created and are awaiting local approval

5. **Check `/In_Progress/cloud/`**:
   - Any items currently claimed by cloud (may be mid-processing)

6. **Report status** using the template below.

## Output Template

```
Cloud AI Employee Status — 2026-03-09 08:00 UTC

Vault Sync:
  Last sync: 2026-03-09 07:55 UTC (by cloud)
  Files committed: 3
  Sync health: OK

Cloud Watchers:
  Filesystem:          RUNNING
  Gmail IMAP:          RUNNING
  Facebook/Instagram:  RUNNING
  Twitter:             RUNNING
  Cloud Orchestrator:  RUNNING
  Last heartbeat:      2026-03-09 07:50 UTC

Pending Your Approval:
  /Pending_Approval/email/   → 2 draft(s)
  /Pending_Approval/social/  → 1 draft(s)
  Total: 3 items awaiting your review

In Progress (cloud):
  0 items currently being processed

Recent Cloud Activity (last 5 events):
  07:55  heartbeat
  07:42  email_draft_created  (EMAIL_DRAFT_2026-03-09_074200_client.md)
  07:38  social_draft_created (SOCIAL_DRAFT_2026-03-09_twitter.md)
```

## Rules
- If sync_status.json doesn't exist, say "Vault not yet synced. Run: python sync/vault_sync.py --mode pull"
- If health_status.json doesn't exist, say "Health monitor not running. Start: python watchers/health_monitor.py"
- If last heartbeat is > 10 minutes ago, flag as WARNING: cloud may be down
- Always list pending approvals — these need the user's attention
