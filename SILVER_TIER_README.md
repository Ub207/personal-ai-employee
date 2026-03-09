# AI Employee — Silver Tier 🥈

> **Status:** Complete — Ready for Gold Tier upgrade

This is your Personal AI Employee built with Claude Code + Obsidian. It monitors Gmail, WhatsApp, and filesystem, auto-posts to LinkedIn, processes approvals, and generates daily briefings.

---

## ✅ Silver Tier Deliverables (Complete)

| Requirement | Status | Location |
|-------------|--------|----------|
| **All Bronze Tier requirements** | ✅ | See `README.md` (Bronze) |
| WhatsApp Watcher | ✅ | `watchers/whatsapp_watcher.py` |
| LinkedIn Auto-Poster | ✅ | `watchers/linkedin_poster.py` |
| MCP Email Server | ✅ | `mcp_servers/email-mcp-server.js` |
| Approval Orchestrator (HITL) | ✅ | `watchers/approval_orchestrator.py` |
| Plan.md Generator (Claude Skill) | ✅ | `.claude/skills/create-plan.md` |
| Daily Briefing Scheduler | ✅ | `watchers/daily_briefing_scheduler.py` |
| Windows Task Scheduler Setup | ✅ | `setup_task_scheduler.ps1` |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SOURCES                             │
├─────────────┬─────────────┬──────────────┬─────────────────────┤
│    Gmail    │  WhatsApp   │  LinkedIn    │  File System        │
└──────┬──────┴──────┬──────┴───────┬──────┴─────────┬───────────┘
       │             │              │                │
       ▼             ▼              ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PERCEPTION LAYER (Watchers)                  │
│  ┌────────────┐ ┌──────────────┐ ┌────────────┐ ┌────────────┐ │
│  │Gmail Watcher│ │WhatsApp Watcher│ │LinkedIn   │ │Filesystem │ │
│  │(IMAP)       │ │(Playwright)  │ │Poster     │ │Watcher     │ │
│  └─────┬──────┘ └──────┬───────┘ └─────┬──────┘ └─────┬──────┘ │
└────────┼────────────────┼───────────────┼──────────────┼────────┘
         │                │               │              │
         ▼                ▼               ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OBSIDIAN VAULT (Local)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ /Needs_Action/  │ /Plans/  │ /Done/  │ /Logs/            │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ /Pending_Approval/  │  /Approved/  │  /Rejected/         │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ Dashboard.md  │ Company_Handbook.md  │ /Briefings/       │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REASONING LAYER                              │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                 CLAUDE CODE + Agent Skills                │ │
│  │   process-inbox │ update-dashboard │ create-plan          │ │
│  └───────────────────────────────────────────────────────────┘ │
└────────────────────────────────┬────────────────────────────────┘
                                 │
              ┌──────────────────┴───────────────────┐
              ▼                                      ▼
┌────────────────────────────┐    ┌────────────────────────────────┐
│    HUMAN-IN-THE-LOOP       │    │         ACTION LAYER           │
│  ┌──────────────────────┐  │    │  ┌─────────────────────────┐   │
│  │ Review Approval Files│──┼───▶│  │    MCP SERVERS          │   │
│  │ Move to /Approved    │  │    │  │  ┌──────┐ ┌──────────┐  │   │
│  └──────────────────────┘  │    │  │  │Email │ │ Browser  │  │   │
│                            │    │  │  │ MCP  │ │   MCP    │  │   │
└────────────────────────────┘    │  │  └──┬───┘ └────┬─────┘  │   │
                                  │  └─────┼──────────┼────────┘   │
                                  └────────┼──────────┼────────────┘
                                           │          │
                                           ▼          ▼
                                  ┌────────────────────────────────┐
                                  │     EXTERNAL ACTIONS           │
                                  │  Send Email │ Post to LinkedIn │
                                  │  WhatsApp   │ Payment APIs     │
                                  └────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    SCHEDULED TASKS                              │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Windows Task Scheduler / cron                            │ │
│  │   • Daily Briefing (8:00 AM)                              │ │
│  │   • Weekly Audit (Sunday 10:00 PM)                        │ │
│  │   • Health Check (Every hour)                             │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Install Dependencies

```bash
cd D:\bronze_tier\watchers
pip install -r requirements.txt
playwright install chromium
```

### 2. Install MCP Server Dependencies

```bash
cd D:\bronze_tier\mcp_servers
npm install
```

### 3. Configure Environment Variables

Create a `.env` file in the vault root:

```bash
# Gmail (Bronze Tier)
GMAIL_USERNAME=your.email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password

# Email MCP Server (Silver Tier)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your.email@gmail.com
SMTP_PASS=your-app-password
DRY_RUN=true
```

### 4. Start All Watchers

```bash
# Terminal 1: Filesystem Watcher
python watchers/filesystem_watcher.py

# Terminal 2: Gmail Watcher
python watchers/gmail_imap_watcher.py

# Terminal 3: WhatsApp Watcher (first run: scan QR code)
python watchers/whatsapp_watcher.py

# Terminal 4: Approval Orchestrator
python watchers/approval_orchestrator.py
```

### 5. Set Up Scheduled Tasks

Run as Administrator in PowerShell:

```powershell
cd D:\bronze_tier
.\setup_task_scheduler.ps1
```

### 6. Configure Claude Code MCP

Create `.claude/mcp.json`:

```json
{
  "servers": [
    {
      "name": "email",
      "command": "node",
      "args": ["mcp_servers/email-mcp-server.js"],
      "env": {
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "your.email@gmail.com",
        "SMTP_PASS": "your-app-password"
      }
    }
  ]
}
```

---

## Watchers Reference

| Watcher | Purpose | Command |
|---------|---------|---------|
| Filesystem | Monitor `/Inbox` for new files | `python watchers/filesystem_watcher.py` |
| Gmail | Monitor Gmail for new emails | `python watchers/gmail_imap_watcher.py` |
| WhatsApp | Monitor WhatsApp for priority messages | `python watchers/whatsapp_watcher.py` |
| LinkedIn | Auto-post business updates | `python watchers/linkedin_poster.py --auto` |
| Approval Orchestrator | Execute approved actions | `python watchers/approval_orchestrator.py` |
| Daily Briefing | Generate CEO briefing | `python watchers/daily_briefing_scheduler.py` |

---

## Agent Skills

| Skill | Purpose |
|-------|---------|
| `process-inbox` | Process all files in `/Needs_Action` |
| `update-dashboard` | Refresh `Dashboard.md` with current state |
| `daily-briefing` | Generate daily CEO summary |
| `create-plan` | Create structured `Plan.md` for complex tasks |

---

## Human-in-the-Loop Workflow

1. **Claude detects action needed** → Creates approval request in `/Pending_Approval/`
2. **Human reviews** → Reads file, understands the action
3. **Human approves** → Moves file to `/Approved/`
4. **Orchestrator executes** → Runs the action via MCP or script
5. **Result logged** → File archived to `/Done/Approvals/`

### Approval File Example

```markdown
---
type: email_send
to: client@example.com
subject: Invoice #123 - $1,500
attachment: /Vault/Invoices/2026-03_Client.pdf
created: 2026-03-09T10:30:00Z
status: pending
---

# Payment Details
- Amount: $1,500
- To: Client Name
- Reference: Invoice #123

## To Approve
Move this file to /Approved folder.

## To Reject
Move this file to /Rejected folder.
```

---

## Scheduled Tasks

| Task | Schedule | Purpose |
|------|----------|---------|
| Daily Briefing | 8:00 AM daily | Generate CEO briefing in `/Briefings/` |
| Weekly Audit | Sunday 10:00 PM | Weekly business review |
| Health Check | Every hour | Monitor watcher processes |

### View Scheduled Tasks

1. Open **Task Scheduler** (search in Start menu)
2. Navigate to **Task Scheduler Library**
3. Find tasks starting with "AI Employee"

### Run Task Manually

Right-click task → **Run**

---

## Testing the System

### Test WhatsApp Watcher

1. Start watcher: `python watchers/whatsapp_watcher.py`
2. Send yourself a WhatsApp message with keyword "urgent"
3. Check `/Needs_Action/` for new action file

### Test LinkedIn Poster

```bash
# Dry run (no actual post)
python watchers/linkedin_poster.py --dry-run --auto

# Draft mode (prepares but doesn't publish)
python watchers/linkedin_poster.py --draft
```

### Test Approval Workflow

1. Create approval request manually in `/Pending_Approval/test.md`:
   ```markdown
   ---
   type: email_send
   to: test@example.com
   subject: Test Email
   ---
   Test body
   ```
2. Move file to `/Approved/`
3. Orchestrator will process and log action

### Test Daily Briefing

```bash
python watchers/daily_briefing_scheduler.py
```

Check `/Briefings/` for generated briefing.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| WhatsApp watcher fails | First run: manually scan QR code on WhatsApp Web |
| LinkedIn poster errors | Ensure browser session exists at `~/.linkedin_session/` |
| MCP server not connecting | Check `node` is installed, run `npm install` in `mcp_servers/` |
| Scheduled task not running | Check task history in Task Scheduler, verify user permissions |
| Emails not sending | Verify SMTP credentials, check `DRY_RUN=false` |

---

## Security Notes

- ⚠️ Never commit `.env` files with credentials
- ⚠️ Use App Passwords, not main password for Gmail
- ⚠️ All financial/social actions require human approval (default: draft mode)
- ⚠️ Review `/Logs/` regularly for audit trail

---

## Next Steps (Gold Tier)

To upgrade to Gold Tier, add:

- [ ] Odoo Community ERP integration (local accounting system)
- [ ] Facebook/Instagram integration
- [ ] Twitter (X) integration
- [ ] Multiple MCP servers for different action types
- [ ] Weekly Business Audit with CEO Briefing
- [ ] Error recovery and graceful degradation
- [ ] Comprehensive audit logging
- [ ] Ralph Wiggum loop for autonomous multi-step completion

---

*Built with Claude Code + Obsidian + Playwright · Silver Tier Complete · 2026-03-09*
