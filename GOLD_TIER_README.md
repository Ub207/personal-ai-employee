# AI Employee — Gold Tier 🥇

> **Status:** Complete — All Gold Tier requirements met.

Built with Claude Code + Obsidian + Playwright + Odoo + Social APIs.

---

## ✅ Gold Tier Deliverables

| Requirement | Status | Location |
|-------------|--------|----------|
| All Silver Tier requirements | ✅ | See `SILVER_TIER_README.md` |
| Full cross-domain integration | ✅ | All watchers feed one vault |
| Odoo accounting MCP server | ✅ | `mcp_servers/odoo-mcp-server.js` |
| Facebook + Instagram integration | ✅ | `watchers/facebook_instagram_watcher.py` |
| Twitter (X) integration | ✅ | `watchers/twitter_watcher.py` |
| Multiple MCP servers | ✅ | Email + Odoo + Social (3 servers) |
| Weekly Business + Accounting Audit | ✅ | `watchers/weekly_audit.py` + `skills/weekly-audit.md` |
| Error recovery & graceful degradation | ✅ | `watchers/health_monitor.py` |
| Comprehensive audit logging | ✅ | `watchers/audit_logger.py` |
| Ralph Wiggum loop | ✅ | `watchers/ralph_wiggum_hook.py` + `.claude/settings.json` |
| Architecture documentation | ✅ | This file |
| All AI functionality as Agent Skills | ✅ | `.claude/skills/` (6 skills) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SOURCES                                │
├──────────┬──────────┬──────────┬──────────┬──────────┬─────────────────┤
│  Gmail   │ WhatsApp │LinkedIn  │ Facebook │ Twitter  │  File System    │
│          │          │          │ Instagram│    X     │                 │
└────┬─────┴─────┬────┴─────┬────┴─────┬────┴─────┬────┴────────┬────────┘
     │           │          │          │          │             │
     ▼           ▼          ▼          ▼          ▼             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     PERCEPTION LAYER (Watchers)                         │
│  gmail_imap  whatsapp  linkedin  facebook_ig  twitter  filesystem       │
│  _watcher    _watcher  _poster   _watcher     _watcher _watcher         │
│                                                                         │
│  ← All watchers write to /Needs_Action/ and log to audit_logger.py →   │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │   OBSIDIAN VAULT (Local MD)   │
                    │                               │
                    │  /Inbox         /Needs_Action │
                    │  /Pending_Approval  /Approved │
                    │  /Done          /Rejected     │
                    │  /Plans         /Posts/       │
                    │  /Briefings     /Logs/        │
                    │                               │
                    │  Dashboard.md                 │
                    │  Company_Handbook.md           │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │     REASONING LAYER           │
                    │   Claude Code + Agent Skills  │
                    │                               │
                    │  process-inbox   (Bronze)     │
                    │  update-dashboard(Bronze)     │
                    │  daily-briefing  (Bronze)     │
                    │  create-plan     (Silver)     │
                    │  weekly-audit    (Gold)       │
                    │  social-post     (Gold)       │
                    │                               │
                    │  Ralph Wiggum Stop Hook       │
                    │  (loops until task complete)  │
                    └──────┬──────────────┬─────────┘
                           │              │
              ┌────────────▼──┐  ┌────────▼────────────────┐
              │ HUMAN-IN-LOOP │  │    ACTION LAYER         │
              │               │  │    MCP SERVERS          │
              │ /Pending_     │  │                         │
              │  Approval/    │  │  ┌──────┐ ┌──────────┐  │
              │       ↓       │  │  │Email │ │  Odoo    │  │
              │ Human reviews │  │  │ MCP  │ │  MCP     │  │
              │       ↓       │  │  └──────┘ └──────────┘  │
              │ /Approved/    │  │  ┌────────────────────┐  │
              └───────┬───────┘  │  │   Social MCP       │  │
                      │          │  │  Twitter/FB/IG     │  │
                      └──────────┼──┴────────────────────┘  │
                                 └─────────────────────────┘
                                    │          │         │
                                    ▼          ▼         ▼
                             Send Email   Odoo ERP   Social Posts

┌─────────────────────────────────────────────────────────────────────────┐
│                     MONITORING LAYER                                    │
│  health_monitor.py   — watches all watcher processes, auto-restarts    │
│  audit_logger.py     — thread-safe JSON audit log, 30-day retention    │
│  weekly_audit.py     — Sunday CEO briefing with full business summary  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## MCP Servers (3 total)

| Server | File | Purpose |
|--------|------|---------|
| `email` | `email-mcp-server.js` | Send emails via SMTP, draft to /Pending_Approval |
| `odoo` | `odoo-mcp-server.js` | Odoo JSON-RPC: invoices, revenue, customers |
| `social` | `social-mcp-server.js` | Twitter v2, Facebook + Instagram Graph API |

All servers default to `DRY_RUN=true`. Configured in `.claude/mcp.json`.

---

## Agent Skills (6 total)

| Skill | Tier | Purpose |
|-------|------|---------|
| `process-inbox` | Bronze | Triage /Needs_Action, move to /Done |
| `update-dashboard` | Bronze | Refresh Dashboard.md |
| `daily-briefing` | Bronze | Daily CEO briefing in /Briefings/ |
| `create-plan` | Silver | Generate Plan.md for complex tasks |
| `weekly-audit` | Gold | Full weekly business + accounting review |
| `social-post` | Gold | Cross-platform social posting via MCP |

---

## Watchers Reference

| Watcher | Tier | Platform | Command |
|---------|------|----------|---------|
| `filesystem_watcher.py` | Bronze | Local files | `python watchers/filesystem_watcher.py` |
| `gmail_imap_watcher.py` | Bronze | Gmail | `python watchers/gmail_imap_watcher.py` |
| `whatsapp_watcher.py` | Silver | WhatsApp Web | `python watchers/whatsapp_watcher.py` |
| `linkedin_poster.py` | Silver | LinkedIn | `python watchers/linkedin_poster.py` |
| `approval_orchestrator.py` | Silver | Vault | `python watchers/approval_orchestrator.py` |
| `daily_briefing_scheduler.py` | Silver | Vault | `python watchers/daily_briefing_scheduler.py` |
| `facebook_instagram_watcher.py` | Gold | FB + IG | `python watchers/facebook_instagram_watcher.py` |
| `twitter_watcher.py` | Gold | Twitter/X | `python watchers/twitter_watcher.py` |
| `weekly_audit.py` | Gold | Vault | `python watchers/weekly_audit.py` |
| `health_monitor.py` | Gold | All watchers | `python watchers/health_monitor.py` |

---

## Quick Start (Gold Tier)

### 1. Install All Dependencies

```bash
# Python
cd D:\bronze_tier\watchers
pip install -r requirements.txt
playwright install chromium

# Node.js
cd D:\bronze_tier\mcp_servers
npm install
```

### 2. Configure Credentials

```bash
# Copy the template
copy .env.example .env
# Edit .env with your actual credentials
notepad .env
```

### 3. Start Watchers

```bash
# Terminal 1: Core watchers
python watchers/filesystem_watcher.py

# Terminal 2: Gmail
python watchers/gmail_imap_watcher.py

# Terminal 3: Social media monitoring
python watchers/facebook_instagram_watcher.py

# Terminal 4: Twitter
python watchers/twitter_watcher.py

# Terminal 5: Approval workflow
python watchers/approval_orchestrator.py

# Terminal 6: Health monitor (watches all others)
python watchers/health_monitor.py
```

### 4. Run Weekly Audit (manually or via scheduler)

```bash
python watchers/weekly_audit.py
```

### 5. Generate Audit Report

```bash
python watchers/audit_logger.py
```

### 6. Manage Multi-Step Tasks (Ralph Wiggum)

```bash
# Create a tracked task
python watchers/ralph_wiggum_hook.py --create-task "Process this week" \
    "Read Company_Handbook" "Process inbox" "Generate briefing" "Update dashboard"

# Mark a step done (by index)
python watchers/ralph_wiggum_hook.py --complete-step 0

# Check status
python watchers/ralph_wiggum_hook.py --status
```

---

## Ralph Wiggum Loop

The stop hook is registered in `.claude/settings.json`. When Claude Code finishes a response, it runs `ralph_wiggum_hook.py`. If `vault/current_task.json` has incomplete steps, the hook exits non-zero and Claude continues iterating until all steps are marked complete.

**Use it for complex multi-step workflows:**

```bash
# Tell Claude to use it:
# "Create a task to process inbox, generate briefing, and update dashboard.
#  Mark each step done as you go. Stop only when all steps are complete."
```

---

## Cross-Domain Integration

All components feed into one unified Obsidian vault:

| Domain | Input | Processing | Output |
|--------|-------|------------|--------|
| **Personal** | Gmail, WhatsApp | Priority triage → Needs_Action | Draft replies → Pending_Approval |
| **Business** | Facebook, Instagram, Twitter | Keyword detection → action files | Posts via Social MCP |
| **Financial** | Odoo invoices | Revenue queries via Odoo MCP | Weekly CEO briefing |
| **Ops** | Filesystem, all watchers | health_monitor auto-restart | health_status.json |

---

## Folder Structure (Gold Tier)

```
D:/bronze_tier/
├── Inbox/                  ← File drop zone
├── Needs_Action/           ← Items awaiting processing
├── Pending_Approval/       ← Awaiting human sign-off
├── Approved/               ← Human approved, orchestrator executes
├── Rejected/               ← Human rejected
├── Done/                   ← Completed + archived
│   └── Approvals/          ← Archived approval files
├── Plans/                  ← Plan.md files (Claude reasoning)
├── Posts/
│   ├── Pending/            ← Social posts awaiting publication
│   ├── Published/          ← LinkedIn posts (Playwright)
│   ├── Done/               ← Cross-platform posts completed
│   └── Failed/             ← Posts that failed all platforms
├── Briefings/              ← Daily + weekly CEO briefings
├── Logs/                   ← All component audit logs
│   ├── audit_YYYY-MM-DD.json
│   ├── odoo_actions.json
│   ├── social_actions.json
│   ├── email_actions.json
│   └── health_monitor.log
├── vault/
│   ├── current_task.json   ← Ralph Wiggum task state
│   └── health_status.json  ← Watcher health from health_monitor
├── watchers/               ← All Python watcher scripts
├── mcp_servers/            ← Node.js MCP servers
├── .claude/
│   ├── mcp.json            ← MCP server registry (3 servers)
│   ├── settings.json       ← Ralph Wiggum stop hook
│   ├── settings.local.json ← User permissions
│   └── skills/             ← 6 agent skills
├── Dashboard.md            ← Live status (auto-updated)
├── Company_Handbook.md     ← Rules of engagement
├── .env                    ← Credentials (never commit)
└── .env.example            ← Credential template
```

---

## Error Recovery & Graceful Degradation

`health_monitor.py` provides:
- **Process monitoring** every 60 seconds via `psutil`
- **Auto-restart** up to 3 times per hour per watcher
- **Automatic disable** after 3 failures — writes alert to `/Pending_Approval/`
- **Health status** written to `vault/health_status.json` for Dashboard
- **Degradation**: if a watcher is disabled, the others continue running

All watchers additionally have:
- **Retry logic** with exponential backoff (max 3 retries)
- **Structured error logging** via `audit_logger.py`
- **DRY_RUN mode** for safe testing without side effects

---

## Audit Logging

`audit_logger.py` provides:
- **Daily JSON files**: `Logs/audit_YYYY-MM-DD.json`
- **30-day rotation**: older logs auto-deleted
- **Thread-safe** with `filelock` (cross-process safe)
- **Importable**: `from audit_logger import AuditLogger`
- **Weekly report**: generates Markdown to `/Briefings/`

All other components (watchers, MCP servers) write to their own log files:
- `Logs/odoo_actions.json` — Odoo MCP activity
- `Logs/social_actions.json` — Twitter/FB/IG posts
- `Logs/email_actions.json` — Email sends
- `Logs/health_monitor.log` — Watcher restarts and health

---

## Lessons Learned

1. **Local-first is the right architecture.** Obsidian Markdown files as the "database" means zero vendor lock-in, instant human readability, and trivial backup (it's just files).

2. **Human-in-the-loop is a feature, not a limitation.** The `/Pending_Approval` → `/Approved` workflow prevents costly mistakes. Keep the AI bold in analysis, cautious in execution.

3. **DRY_RUN=true everywhere by default.** Every component should be safe to run without credentials. This makes onboarding and testing much faster.

4. **Playwright for social media is fragile.** WhatsApp and LinkedIn change their DOM constantly. Expect to update selectors every few months. Consider official APIs when they become accessible.

5. **One vault, many watchers.** The architecture scales by adding watchers — each is independent but writes to the same Markdown vault. Adding a new integration means one new Python file, not a new database.

6. **Stop hooks (Ralph Wiggum) change the interaction model.** Instead of one-shot commands, Claude can now iterate on complex tasks until done. Combine with `create-plan` skill for powerful multi-step automation.

7. **Audit logs are essential.** Without `audit_logger.py`, debugging failures across multiple watchers running in parallel would be nearly impossible. Log everything.

8. **Odoo JSON-RPC is stable.** The API hasn't changed significantly across versions. The MCP server pattern (one tool per business operation) is much cleaner than exposing raw API endpoints to Claude.

---

## Security Notes

- ⚠️ **Never commit `.env`** — credentials stay local only
- ⚠️ **DRY_RUN=true by default** on all MCP servers — set to `false` only when ready
- ⚠️ **Financial actions always require human approval** — the orchestrator never auto-executes payments
- ⚠️ **Social posts default to draft mode** — LinkedIn poster requires `--no-draft` flag to actually post
- ⚠️ **WhatsApp ToS** — browser automation of WhatsApp Web may violate Terms of Service; use at your own risk
- ⚠️ **Twitter/X rate limits** — v2 API free tier: 500k tweets/month read, 1500/month write

---

## Next Steps (Platinum Tier)

- [ ] Run the AI Employee on a cloud VM 24/7 (always-on watchers)
- [ ] Deploy Odoo Community on cloud with HTTPS + daily backups
- [ ] Vault sync between local and cloud (markdown/state only)
- [ ] A2A (Agent-to-Agent) upgrade for delegated workflows
- [ ] Email-arrives-while-offline → cloud drafts reply → local approves → MCP sends

---

*Built with Claude Code + Obsidian + Playwright + Odoo + Twitter/FB/IG APIs*
*Gold Tier Complete · 2026-03-09*
