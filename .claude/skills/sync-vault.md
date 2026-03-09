# Skill: Sync Vault

## Purpose
Trigger or check a Git-based vault sync between Local and Cloud.
Ensures the local vault has the latest cloud-processed items
(approval files, updates, signals) and pushes local changes to cloud.

## Trigger
Run this skill when:
- The user says "sync the vault" or "pull from cloud"
- After returning from being offline (pull first)
- After approving items locally (push to cloud so cloud sees Done files)
- Before generating a weekly briefing (want latest cloud data)

## Steps

1. **Check git status** — run `python sync/vault_sync.py --mode status`:
   - Show files that will sync vs files that will be skipped (security)
   - Show how many commits behind remote (cloud)

2. **Ask the user** which mode they want:
   - `pull` — get latest cloud changes (after cloud has been running)
   - `push` — send local changes to cloud (after approving items)
   - `sync` — pull then push (full bidirectional, most common)

3. **Execute sync**:
   ```bash
   python sync/vault_sync.py --vault-path D:/bronze_tier --mode <mode>
   ```
   Note: This requires git to be initialised and a remote configured.

4. **Report result**:
   - How many files synced
   - Whether push succeeded
   - Any conflicts that need manual resolution

5. **Merge /Updates/ signals into Dashboard.md** (Local owns Dashboard):
   - Read all `/Updates/UPDATE_*.json` files not yet merged
   - For each: add a row to Dashboard.md Recent Activity Log
   - Note: Cloud writes to /Updates/, Local merges — single-writer rule

6. **Update Dashboard.md** with sync timestamp.

## Git Setup (one-time)

If the vault is not yet a git repo:
```bash
cd D:/bronze_tier
git init
git remote add origin git@github.com:youruser/ai-employee-vault.git
git add .
git commit -m "Initial vault commit"
git push -u origin main
```

On Cloud VM (one-time):
```bash
git clone git@github.com:youruser/ai-employee-vault.git /opt/ai-employee
```

## Security Reminder
The sync script uses a whitelist: only `.md` and `.json` files sync.
Secrets (`.env`, sessions, tokens) **never** leave your local machine.
Run `python sync/vault_sync.py --mode status` to see exactly what would sync.

## Example Output

```
Vault Sync — mode=sync agent=local vault=D:/bronze_tier

Pull: 4 new commits from cloud
  - Briefings/2026-03-09_Monday_Briefing.md
  - Pending_Approval/email/EMAIL_DRAFT_2026-03-09_074200_client.md
  - Updates/UPDATE_2026-03-09_074200_email_draft_created.json
  - Logs/audit_2026-03-09.json

Push: committed 2 files
  - Done/platinum_demo/DONE_EMAIL_DRAFT_2026-03-09.md
  - Logs/email_actions.json
  Message: [local] Auto-sync 2026-03-09T09:00:00Z

Merged 1 Update signal into Dashboard.md.
Sync complete.
```
