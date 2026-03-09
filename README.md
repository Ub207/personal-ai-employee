# AI Employee — Bronze Tier ✅

> **Status:** Complete — Ready for Silver Tier upgrade

This is your Personal AI Employee built with Claude Code + Obsidian. It monitors your inbox and filesystem, processes files autonomously, and keeps you informed via a Markdown dashboard.

---

## ✅ Bronze Tier Deliverables (Complete)

| Requirement | Status | Location |
|-------------|--------|----------|
| Obsidian vault with Dashboard.md | ✅ | `Dashboard.md` |
| Company Handbook with rules | ✅ | `Company_Handbook.md` |
| Working Watcher (Filesystem) | ✅ | `watchers/filesystem_watcher.py` |
| Working Watcher (Gmail) | ✅ | `watchers/gmail_imap_watcher.py` |
| Claude Code Agent Skills | ✅ | `.claude/skills/` |
| Folder structure | ✅ | `/Inbox`, `/Needs_Action`, `/Done`, `/Pending_Approval`, `/Briefings` |

---

## Quick Start

### 1. Install Dependencies

```bash
cd D:\bronze_tier\watchers
pip install -r requirements.txt
```

### 2. Start the Filesystem Watcher

```bash
cd D:\bronze_tier
python watchers/filesystem_watcher.py
```

Keep this running in a terminal window. It monitors `/Inbox` for new files.

### 3. (Optional) Configure Gmail Watcher

1. Enable IMAP in Gmail: **Settings → Forwarding and POP/IMAP → Enable IMAP**
2. Create App Password: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Set environment variables:

```bash
set GMAIL_USERNAME=your.email@gmail.com
set GMAIL_APP_PASSWORD=your-16-char-app-password
```

4. Run Gmail watcher:

```bash
python watchers/gmail_imap_watcher.py
```

### 4. Use Claude Code to Process Items

Drop a file into `/Inbox` → Watcher creates action file in `/Needs_Action` → Ask Claude to process:

```bash
claude -p "Read Company_Handbook.md and process all files in Needs_Action. Update Dashboard.md and move files to Done when complete."
```

**Or use the Agent Skills:**

```bash
claude -p "Use the process-inbox skill to handle all pending items."
```

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Gmail/Files   │ ──▶ │   Watchers       │ ──▶ │  Needs_Action/  │
│   (External)    │     │   (Python)       │     │  (Markdown)     │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Dashboard.md  │ ◀── │   Claude Code    │ ◀── │  Company_       │
│   (Status)      │     │   (Reasoning)    │     │  Handbook.md    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## Folder Structure

| Folder | Purpose |
|--------|---------|
| `/Inbox` | Drop zone for new files to process |
| `/Needs_Action` | Items awaiting Claude's processing |
| `/Done` | Completed & archived items |
| `/Pending_Approval` | Awaiting your sign-off |
| `/Briefings` | Auto-generated CEO briefings |

---

## Agent Skills

Three custom skills are configured in `.claude/skills/`:

| Skill | Purpose |
|-------|---------|
| `process-inbox` | Scan `/Needs_Action`, take action, move to `/Done` |
| `update-dashboard` | Refresh Dashboard.md with current counts |
| `daily-briefing` | Generate CEO summary in `/Briefings` |

---

## Testing the System

1. **Drop a test file:**
   ```bash
   echo "Test invoice" > Inbox/test.txt
   ```

2. **Wait 5 seconds** — Watcher creates action file in `/Needs_Action`

3. **Ask Claude to process:**
   ```bash
   claude -p "Process all files in Needs_Action using the process-inbox skill"
   ```

4. **Check Dashboard.md** — Activity log should show the processed item

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Watcher not creating files | Check `python watchers/filesystem_watcher.py` is running |
| Claude not responding | Run `claude --login` first |
| Gmail watcher fails | Verify IMAP enabled and App Password is correct |
| Dashboard not updating | Ensure Claude has write permissions to vault |

---

## Next Steps (Silver Tier)

To upgrade to Silver Tier, add:

- [ ] WhatsApp watcher integration
- [ ] LinkedIn auto-posting
- [ ] MCP server for sending emails
- [ ] Human-in-the-loop approval workflow
- [ ] Scheduled tasks (cron/Task Scheduler)

---

## Security Notes

- ⚠️ Never commit `.env` files with credentials
- ⚠️ Use App Passwords, not main password for Gmail
- ⚠️ All financial actions require human approval (see `Company_Handbook.md`)

---

*Built with Claude Code + Obsidian · Bronze Tier Complete · 2026-03-09*
