# Personal AI Employee — All 4 Tiers Complete 🏆

> **Built with Claude Code + Obsidian** | Local-first, Agent-driven, Human-in-the-loop

![Status](https://img.shields.io/badge/Status-Platinum%20Complete-gold)
![Tiers](https://img.shields.io/badge/Tiers-Bronze%20%7C%20Silver%20%7C%20Gold%20%7C%20Platinum-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%2F%20Linux-lightgrey)
![AI](https://img.shields.io/badge/AI-Claude%20Code-orange)

---

## What Is This?

A fully autonomous **Personal AI Employee** that runs locally on your machine. It monitors your email, social media, and filesystem — creates plans, drafts responses, and asks for your approval before taking any real action.

**Architecture:** `Watcher (Trigger) → Plan.md (Brain) → HITL Approval → Skill (Action) → Done`

---

## Tier Completion

| Tier | Status | Key Deliverables |
|------|--------|-----------------|
| Bronze | ✅ Complete | Vault, Dashboard, Filesystem Watcher, Agent Skills |
| Silver | ✅ Complete | CSV Drop Watcher, 5 Production Skills, HITL, Scheduler |
| Gold | ✅ Complete | CEO Briefing, Audit Logger, Health Monitor, Ralph Wiggum Hook |
| Platinum | ✅ Complete | Cloud VM Deploy, 13 Systemd Units, Vault Sync, A2A Agent |

---

## Vault Structure

```
D:/bronze_tier/
├── Inbox/                    # Drop zone — new tasks arrive here
├── Needs_Action/             # Queued for processing
├── Pending_Approval/         # Awaiting your sign-off
│   ├── email/
│   └── social/
├── Approved/                 # You approved — execute
├── Rejected/                 # You rejected — log and archive
├── Done/                     # Completed & archived
├── DropBox/                  # Drop CSV/PDF invoices here
├── Social_Drafts/            # LinkedIn post drafts
├── Briefings/                # Auto-generated CEO briefings
├── Plans/                    # Task execution plans
├── Logs/                     # Audit trail
├── Dashboard.md              # Live status overview
├── Company_Handbook.md       # AI rules of engagement
├── start_watchers.bat        # Start all 7 watchers at once
│
├── watchers/                 # Python watcher scripts
│   ├── filesystem_watcher.py
│   ├── gmail_imap_watcher.py
│   ├── twitter_watcher.py
│   ├── csv_drop_watcher.py
│   ├── approval_orchestrator.py
│   ├── health_monitor.py
│   ├── daily_briefing_scheduler.py
│   ├── facebook_instagram_watcher.py
│   ├── linkedin_poster.py
│   ├── whatsapp_watcher.py
│   ├── weekly_audit.py
│   ├── audit_logger.py
│   ├── ralph_wiggum_hook.py
│   ├── cloud_orchestrator.py
│   └── a2a_agent.py
│
├── .claude/skills/           # Agent Skills (Claude's brain)
│   ├── gmail-send/           # Send emails via SMTP
│   ├── linkedin-post/        # Post to LinkedIn
│   ├── vault-file-manager/   # Move files through workflow
│   ├── human-approval/       # Request human sign-off
│   ├── task-planner/         # Generate Plan.md before acting
│   ├── process-inbox.md
│   ├── update-dashboard.md
│   ├── daily-briefing.md
│   ├── weekly-audit.md
│   ├── social-post.md
│   ├── cloud-status.md
│   └── sync-vault.md
│
├── mcp_servers/              # MCP servers (Node.js)
│   ├── email-mcp-server.js
│   ├── odoo-mcp-server.js
│   └── social-mcp-server.js
│
├── scripts/
│   └── run_ai_employee.py    # Auto-scheduler (every 5 min)
│
├── sync/
│   └── vault_sync.py         # Git-based vault sync
│
└── deploy/                   # Cloud VM deployment
    ├── setup_cloud_vm.sh
    ├── setup_odoo_cloud.sh
    ├── backup_vault.sh
    └── systemd/              # 13 systemd service units
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Ub207/personal-ai-employee.git
cd personal-ai-employee

# Install Python dependencies
pip install -r watchers/requirements.txt

# Install MCP server dependencies
cd mcp_servers && npm install && cd ..
```

### 2. Configure Credentials

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required credentials:
```env
GMAIL_USERNAME=your@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
SMTP_USER=your@gmail.com
SMTP_PASS=xxxx-xxxx-xxxx-xxxx
TWITTER_BEARER_TOKEN=...
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...
DRY_RUN=true   # Set false for live mode
```

### 3. Start All Watchers (Windows)

Double-click `start_watchers.bat` — opens 7 persistent terminal windows:

| Window | Watcher | Purpose |
|--------|---------|---------|
| 1 | Gmail Watcher | Monitors Gmail inbox via IMAP |
| 2 | Twitter Watcher | Monitors mentions & DMs |
| 3 | Filesystem Watcher | Watches /Inbox for new files |
| 4 | CSV Drop Watcher | Watches /DropBox for CSV/PDF |
| 5 | Approval Orchestrator | Processes /Approved & /Rejected |
| 6 | Health Monitor | Auto-restarts crashed watchers |
| 7 | Daily Briefing | Generates CEO briefing at 8AM |

### 4. Test the System

```bash
# Test filesystem watcher
echo "Process this invoice" > Inbox/test.txt

# Test CSV drop watcher
cp any_file.csv DropBox/

# Check Dashboard
cat Dashboard.md
```

---

## Agent Skills

Each skill has a `SKILL.md` (instructions for Claude) + `scripts/` (executable code):

| Skill | Purpose | Script |
|-------|---------|--------|
| `gmail-send` | Send emails via Gmail SMTP | `scripts/send_email.py` |
| `linkedin-post` | Post to LinkedIn via Playwright | `scripts/post_linkedin.py` |
| `vault-file-manager` | Move files through workflow | `scripts/move_task.py` |
| `human-approval` | Create & check approval files | `scripts/request_approval.py` |
| `task-planner` | Generate Plan.md before acting | *(Claude-native)* |
| `process-inbox` | Process all Needs_Action items | *(Claude-native)* |
| `daily-briefing` | Generate CEO briefing | *(Claude-native)* |
| `weekly-audit` | Full business weekly report | *(Claude-native)* |

---

## Workflow

```
External Input (email/file/CSV)
        ↓
   Watcher detects
        ↓
  Needs_Action/ created
        ↓
  Claude creates Plan.md
        ↓
  Pending_Approval/ (draft)
        ↓
  YOU review & approve
        ↓
  Approved/ → Skill executes
        ↓
       Done/
```

---

## Gold Tier Features

- **Weekly CEO Briefing** — Every Sunday, auto-generates business summary
- **Audit Logger** — Thread-safe JSON logs, 30-day rotation
- **Health Monitor** — Auto-restarts dead watchers using psutil
- **Ralph Wiggum Hook** — Claude Code stop hook, enforces multi-step task completion

## Platinum Tier Features

- **Cloud VM Deploy** — Full Ubuntu 22.04 setup scripts (`deploy/`)
- **13 Systemd Units** — All watchers as Linux services with timers
- **Git Vault Sync** — Secure bidirectional sync (`.md`/`.json` only, never secrets)
- **A2A Agent** — File-based Agent-to-Agent messaging via `/Updates/`
- **Cloud Orchestrator** — Claim-by-move rule prevents double-processing

---

## Security

- `.env` is in `.gitignore` — credentials never committed
- `DRY_RUN=true` by default — nothing sent until you explicitly set `false`
- All external actions require human approval via `/Pending_Approval/`
- Vault sync whitelist: only `.md` and `.json` files sync to cloud

---

## Tech Stack

- **Claude Code** — AI reasoning engine
- **Python 3.11** — Watchers & scripts
- **Node.js** — MCP servers
- **Obsidian** — Markdown vault / knowledge base
- **IMAP** — Gmail monitoring (no Google API needed)
- **Twitter API v2** — OAuth 1.0a
- **Playwright** — Browser automation (LinkedIn, WhatsApp)
- **Systemd** — Linux service management (cloud)
- **Git** — Vault sync between local & cloud

---

## License

MIT — Free to use and modify.

---

*Personal AI Employee · All 4 Tiers Complete 🏆 · Built with Claude Code · 2026-03-09*
