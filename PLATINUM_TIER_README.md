# AI Employee — Platinum Tier 🏆

> **Status:** Complete — Production-ish AI Employee

Built with Claude Code + Obsidian + Git Sync + Cloud VM + Systemd + Odoo Cloud.

---

## ✅ Platinum Tier Deliverables

| Requirement | Status | Location |
|-------------|--------|----------|
| All Gold Tier requirements | ✅ | See `GOLD_TIER_README.md` |
| Cloud VM 24/7 (systemd services) | ✅ | `deploy/systemd/` (13 units) |
| Work-Zone Specialization | ✅ | `watchers/cloud_orchestrator.py` |
| Delegation via Synced Vault | ✅ | `sync/vault_sync.py` (Git-based) |
| Claim-by-move rule | ✅ | `CloudOrchestrator.claim_item()` |
| Single-writer Dashboard rule | ✅ | `/Updates/` → Local merges |
| Security: markdown/state only syncs | ✅ | `sync/vault_sync.py` allowlist |
| Odoo on Cloud VM with HTTPS + backups | ✅ | `deploy/setup_odoo_cloud.sh` |
| A2A Upgrade (Phase 2) | ✅ | `watchers/a2a_agent.py` |
| Platinum demo (passing gate) | ✅ | `demo/platinum_demo.py` — verified live |
| Agent Skills (8 total) | ✅ | `.claude/skills/` |

---

## Platinum Demo — Verified Live ✅

```
Email arrives while Local OFFLINE
  → Cloud Gmail watcher detects email
  → Cloud Orchestrator claims item (claim-by-move)
  → Cloud drafts reply → writes to /Pending_Approval/email/
  → Vault syncs (Git push from cloud)

Local comes back ONLINE
  → Vault syncs (Git pull on local)
  → User sees approval file in /Pending_Approval/email/
  → User approves (moves to /Approved/)
  → Local sends via email MCP
  → Logged to /Logs/email_actions.json
  → Archived to /Done/
  → A2A signal written to /Updates/
  → Cloud acknowledges on next sync
```

Run it yourself:
```bash
python demo/platinum_demo.py --vault-path D:/bronze_tier --auto-approve
```

---

## Architecture — Full Stack

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLOUD VM (24/7 — Ubuntu 22.04)                      │
│                         Oracle Free Tier / AWS / Any VPS                    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  SYSTEMD SERVICES (always-on, auto-restart)                          │  │
│  │  ai-employee-gmail          ai-employee-twitter                       │  │
│  │  ai-employee-facebook-ig    ai-employee-filesystem                    │  │
│  │  ai-employee-approval       ai-employee-health                        │  │
│  │  ai-employee-cloud-orchestrator                                       │  │
│  │  ai-employee-briefing.timer (08:00 daily)                             │  │
│  │  ai-employee-weekly-audit.timer (Sunday 22:00)                        │  │
│  │  vault-sync.timer (every 5 minutes)                                   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────┐   ┌───────────────────────────────────────────────┐  │
│  │  CLOUD VAULT     │   │  ODOO COMMUNITY (port 8069 → nginx 443)        │  │
│  │  /opt/ai-employee│   │  PostgreSQL + daily pg_dump backups            │  │
│  │                  │   │  MCP: search_invoices, get_revenue_summary     │  │
│  │  /Needs_Action/  │   │  HTTPS via certbot + Let's Encrypt             │  │
│  │    email/        │   └───────────────────────────────────────────────┘  │
│  │    social/       │                                                       │
│  │  /In_Progress/   │                                                       │
│  │    cloud/        │   Work-Zone Ownership:                               │
│  │  /Pending_       │   Cloud OWNS: email triage, draft replies,          │
│  │   Approval/      │              social post drafts, Odoo queries        │
│  │    email/        │   Cloud NEVER: sends email, posts, pays              │
│  │    social/       │                                                       │
│  │  /Updates/       │   (All send/post/pay goes to Pending_Approval        │
│  │  /Plans/         │    for Local agent to execute after approval)        │
│  └──────────────────┘                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │   GIT SYNC (every 5 minutes)  │
                    │   vault_sync.py               │
                    │                               │
                    │  Security allowlist:          │
                    │    ✅ *.md  ✅ *.json          │
                    │    ❌ .env  ❌ *.session        │
                    │    ❌ node_modules  ❌ .venv    │
                    │                               │
                    │  Claim-by-move rule:          │
                    │    /Needs_Action/email/xxx.md │
                    │    → /In_Progress/cloud/xxx   │
                    │    → /Done/cloud/xxx          │
                    │                               │
                    │  Single-writer Dashboard:     │
                    │    Cloud → /Updates/          │
                    │    Local merges into Dashboard│
                    └───────────────┬───────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                         LOCAL MACHINE (Windows)                              │
│                                                                             │
│  ┌──────────────────┐   ┌──────────────────────────────────────────────┐   │
│  │  LOCAL VAULT     │   │  LOCAL-ONLY (never synced to cloud)          │   │
│  │  D:/bronze_tier  │   │                                              │   │
│  │                  │   │  .env (SMTP, Twitter, FB, Odoo creds)        │   │
│  │  /Approved/      │   │  .whatsapp_session/                          │   │
│  │  /Rejected/      │   │  .linkedin_session/                          │   │
│  │  /Done/          │   │  Banking credentials                         │   │
│  │  Dashboard.md    │   │  Payment tokens                              │   │
│  │  (single writer) │   └──────────────────────────────────────────────┘   │
│  └──────────────────┘                                                       │
│                                                                             │
│  Local OWNS:  Approvals, WhatsApp, payments, final send/post                │
│  Local NEVER: Shares credentials with cloud                                 │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  MCP SERVERS (local execution)                                       │  │
│  │  email-mcp-server.js  →  sends approved emails via SMTP             │  │
│  │  odoo-mcp-server.js   →  queries cloud Odoo via JSON-RPC            │  │
│  │  social-mcp-server.js →  posts to Twitter/FB/IG after approval      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Work-Zone Specialization

| Zone | Owner | What They Do | What They Never Do |
|------|-------|-------------|-------------------|
| **Email** | Cloud | Triage, draft replies | Send emails |
| **Social** | Cloud | Draft posts, schedule | Post publicly |
| **Financial (query)** | Cloud | Search invoices, revenue | Create/approve invoices |
| **Approvals** | Local | Review, approve, reject | — |
| **Email Send** | Local | Execute via email MCP | — |
| **Social Post** | Local | Execute via social MCP | — |
| **Payments** | Local | Manual after MCP + approval | — |
| **WhatsApp** | Local | Browser session (can't be cloud) | — |

---

## Delegation via Synced Vault

### Folder Protocol

```
/Needs_Action/email/    ← Cloud writes action files here
/Needs_Action/social/   ← Cloud writes action files here
/In_Progress/cloud/     ← Cloud claims items here (claim-by-move)
/In_Progress/local/     ← Local claims items here (claim-by-move)
/Pending_Approval/email/ ← Cloud writes drafts, Local approves
/Pending_Approval/social/← Cloud writes drafts, Local posts
/Approved/              ← Local moves here to trigger execution
/Rejected/              ← Human rejection
/Updates/               ← Cloud signals (heartbeat, drafts, events)
/Plans/email/           ← Cloud plans for email workflows
/Plans/social/          ← Cloud plans for social workflows
```

### Claim-by-Move Rule

```python
# Cloud claims an item atomically:
shutil.move(
    "Needs_Action/email/EMAIL_001.md",
    "In_Progress/cloud/EMAIL_001.md"
)
# If move succeeds → cloud owns it
# If FileNotFoundError → another agent already claimed it
```

### Single-Writer Dashboard Rule

- **Cloud** writes to `/Updates/UPDATE_*.json`
- **Local** (only) reads Updates and merges into `Dashboard.md`
- This prevents git conflicts on the most frequently updated file

---

## Cloud VM Setup

### Quick Start (Oracle Free Tier / Ubuntu 22.04)

```bash
# 1. SSH into your cloud VM
ssh ubuntu@your-vm-ip

# 2. Clone this repo (vault)
git clone git@github.com:youruser/ai-employee-vault.git /opt/ai-employee

# 3. Set environment and run setup
export VAULT_GIT_REMOTE="git@github.com:youruser/ai-employee-vault.git"
export VAULT_PATH="/opt/ai-employee"
sudo bash /opt/ai-employee/deploy/setup_cloud_vm.sh

# 4. Configure credentials
sudo nano /opt/ai-employee/.env   # Add Gmail, Twitter, FB tokens

# 5. Deploy Odoo (optional)
export ODOO_DOMAIN="odoo.yourdomain.com"
export ODOO_ADMIN_PASS="your-master-password"
sudo bash /opt/ai-employee/deploy/setup_odoo_cloud.sh

# 6. Set up HTTPS for Odoo
certbot --nginx -d odoo.yourdomain.com

# 7. Verify services
systemctl status ai-employee-gmail
systemctl status ai-employee-cloud-orchestrator
systemctl status vault-sync.timer
```

### Verify All Services

```bash
systemctl list-units "ai-employee-*" --all
journalctl -u ai-employee-cloud-orchestrator -f
journalctl -u vault-sync -f
```

---

## Vault Sync Setup (Git)

### One-Time Local Setup

```bash
cd D:/bronze_tier
git init
# Create a PRIVATE repo on GitHub first, then:
git remote add origin git@github.com:youruser/ai-employee-vault.git
# Copy sync gitignore to keep secrets safe:
copy sync\.gitignore_sync .gitignore
git add *.md *.json .gitignore .env.example
git commit -m "Initial vault"
git push -u origin main
```

### Sync Commands

```bash
# Pull cloud changes (after cloud processed while you were offline)
python sync/vault_sync.py --vault-path D:/bronze_tier --mode pull

# Push local approvals to cloud
python sync/vault_sync.py --vault-path D:/bronze_tier --mode push

# Full bidirectional sync (most common)
python sync/vault_sync.py --vault-path D:/bronze_tier --mode sync

# See what would sync (dry run)
python sync/vault_sync.py --vault-path D:/bronze_tier --mode status
```

---

## A2A Communication (Phase 2)

```bash
# Cloud sends a delegation request to Local:
python watchers/a2a_agent.py send \
    --from cloud --to local \
    --type delegate --action process_approval \
    --payload '{"file": "EMAIL_DRAFT_2026-03-09.md", "priority": "high"}'

# Local listens for messages (runs as a background service):
python watchers/a2a_agent.py listen --agent local --interval 30

# View message history:
python watchers/a2a_agent.py history --limit 10
```

Messages are JSON files in `/Updates/`. Git sync carries them between agents. The vault is always the audit record.

---

## Agent Skills (8 total)

| Skill | Tier | Purpose |
|-------|------|---------|
| `process-inbox` | Bronze | Triage /Needs_Action |
| `update-dashboard` | Bronze | Refresh Dashboard.md |
| `daily-briefing` | Bronze | Daily CEO briefing |
| `create-plan` | Silver | Generate Plan.md files |
| `weekly-audit` | Gold | Weekly business review |
| `social-post` | Gold | Cross-platform posting |
| `cloud-status` | Platinum | Check cloud health + sync status |
| `sync-vault` | Platinum | Trigger Git vault sync |

---

## Security Rules (Platinum)

| Rule | Implementation |
|------|----------------|
| Secrets never sync | `sync/vault_sync.py` extension allowlist (`.md`, `.json` only) |
| Cloud never sends | All email/social goes to `/Pending_Approval/` |
| Cloud never pays | Payments always require local + human approval |
| WhatsApp on local only | Browser session can't run headless on cloud |
| Banking creds local only | Never in `.env` on cloud |
| Single Dashboard writer | Local owns Dashboard.md; Cloud writes to `/Updates/` |
| Claim-by-move | Atomic file move prevents double-processing |

---

## Lessons Learned (Platinum)

1. **Git is the right sync primitive.** It gives you conflict detection, history, and the security rule (`.gitignore`) for free. Syncthing is simpler to set up but provides no conflict resolution or history.

2. **The claim-by-move rule is elegant.** `shutil.move()` is atomic on the same filesystem. Two agents racing for the same file: exactly one wins, the other gets `FileNotFoundError`. No locks needed.

3. **Single-writer Dashboard prevents the hardest conflict.** Dashboard.md is updated constantly. Having only Local write to it and Cloud write to `/Updates/` means zero merge conflicts on the most-edited file.

4. **Cloud should NEVER hold secrets.** WhatsApp requires a browser session. LinkedIn requires a browser session. Both are auth tokens. If the cloud VM is compromised, you want attackers to find only Markdown files. Design your zones with this threat model in mind.

5. **Systemd is the right 24/7 runtime.** Docker adds complexity without benefit here. Systemd handles restarts, logging (`journalctl`), scheduling (timer units), and dependencies out of the box.

6. **Odoo JSON-RPC from MCP is powerful.** The Odoo MCP server gives Claude direct access to your accounting data. Combine with the weekly audit skill for genuine AI-driven business intelligence.

7. **The platinum demo is the north star.** "Email while offline" is the killer feature. Everything else (cloud VM, git sync, claim-by-move, approval workflow) exists to make that one scenario work reliably.

8. **A2A via files is underrated.** File-based messaging is slower than HTTP but gives you a free audit log, works through network partitions, and requires zero additional infrastructure. For a personal AI employee, this tradeoff is almost always correct.

---

## Backup Schedule

| Item | Frequency | Location | Retention |
|------|-----------|----------|-----------|
| Vault (tar.gz) | Daily 3:30 AM | `/var/backups/ai-employee/` | 30 days |
| Odoo DB (pg_dump) | Daily 3:30 AM | `/var/backups/odoo/` | 30 days |
| Vault (git push) | Every 5 min | GitHub remote | Unlimited |
| Local vault | Daily (Windows Task Scheduler) | External drive or cloud | — |

---

## Complete File List (Platinum Tier additions)

```
D:/bronze_tier/
├── deploy/
│   ├── setup_cloud_vm.sh          ← Full Ubuntu VM bootstrap script
│   ├── setup_odoo_cloud.sh        ← Odoo 17 + nginx + certbot + backups
│   ├── backup_vault.sh            ← Daily vault + Odoo backup
│   └── systemd/                   ← 13 systemd unit files
│       ├── ai-employee-filesystem.service
│       ├── ai-employee-gmail.service
│       ├── ai-employee-facebook-instagram.service
│       ├── ai-employee-twitter.service
│       ├── ai-employee-approval.service
│       ├── ai-employee-health.service
│       ├── ai-employee-cloud-orchestrator.service
│       ├── ai-employee-briefing.service + .timer
│       ├── ai-employee-weekly-audit.service + .timer
│       └── vault-sync.service + .timer
├── sync/
│   ├── vault_sync.py              ← Git-based secure vault sync
│   ├── sync_config.json.example   ← Config template
│   └── .gitignore_sync            ← Security exclusions
├── watchers/
│   ├── cloud_orchestrator.py      ← Cloud-side master orchestrator
│   └── a2a_agent.py               ← Agent-to-Agent messaging
├── demo/
│   └── platinum_demo.py           ← End-to-end demo script (verified ✅)
├── In_Progress/
│   ├── cloud/                     ← Cloud claims items here
│   └── local/                     ← Local claims items here
├── Updates/                       ← Cloud signals → Local merges
├── Needs_Action/
│   ├── email/                     ← Cloud email domain
│   ├── social/                    ← Cloud social domain
│   └── financial/                 ← Cloud financial domain
├── Pending_Approval/
│   ├── email/                     ← Cloud email drafts
│   └── social/                    ← Cloud social drafts
└── .claude/skills/
    ├── cloud-status.md            ← Check cloud health
    └── sync-vault.md              ← Trigger vault sync
```

---

*Built with Claude Code + Obsidian + Git + Systemd + Odoo + Twitter/FB/IG*
*Platinum Tier Complete · 2026-03-09* 🏆
