# Personal AI Employee — Bronze Tier

> **Built with Claude Code + Obsidian** | Local-first, Agent-driven, Human-in-the-loop

![Status](https://img.shields.io/badge/Status-Bronze%20Complete-cd7f32)
![Platform](https://img.shields.io/badge/Platform-Windows%20%2F%20Linux-lightgrey)
![AI](https://img.shields.io/badge/AI-Claude%20Code-orange)

---

## What Is This?

A **Personal AI Employee** that runs locally on your machine. It monitors your filesystem and email — creates plans, drafts responses, and asks for your approval before taking any real action.

**Architecture:** `Watcher (Trigger) → Needs_Action → Claude processes → Done`

---

## Vault Structure

```
D:/bronze_tier/
├── Inbox/                    # Drop zone — new tasks arrive here
├── Needs_Action/             # Queued for processing
├── Pending_Approval/         # Awaiting your sign-off
├── Done/                     # Completed & archived
├── Briefings/                # Auto-generated CEO briefings
├── Dashboard.md              # Live status overview
├── Company_Handbook.md       # AI rules of engagement
│
├── watchers/
│   ├── filesystem_watcher.py # Watches /Inbox for new files
│   └── gmail_imap_watcher.py # Monitors Gmail inbox via IMAP
│
└── .claude/skills/
    ├── process-inbox.md      # Process all Needs_Action items
    ├── update-dashboard.md   # Refresh Dashboard.md
    └── daily-briefing.md     # Generate CEO briefing
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Ub207/personal-ai-employee.git
cd personal-ai-employee

pip install -r watchers/requirements.txt
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
DRY_RUN=true   # Set false for live mode
```

### 3. Start Watchers

```bash
# Filesystem watcher
python watchers/filesystem_watcher.py

# Gmail watcher
python watchers/gmail_imap_watcher.py
```

### 4. Test the System

```bash
# Drop a file into Inbox
echo "Process this invoice" > Inbox/test.txt

# Check Dashboard
cat Dashboard.md
```

---

## Agent Skills

| Skill | Purpose |
|-------|---------|
| `/process-inbox` | Scan Needs_Action and process all pending items |
| `/update-dashboard` | Refresh Dashboard.md with current counts and status |
| `/daily-briefing` | Generate today's briefing in /Briefings/ |

---

## Workflow

```
New file dropped in /Inbox
        ↓
  Filesystem watcher detects
        ↓
  Moved to /Needs_Action
        ↓
  Claude reads & creates plan
        ↓
  Draft placed in /Pending_Approval
        ↓
  YOU review & approve
        ↓
       /Done
```

---

## Security

- `.env` is in `.gitignore` — credentials never committed
- `DRY_RUN=true` by default — nothing sent until you explicitly set `false`
- All external actions require human approval via `/Pending_Approval/`

---

## Tech Stack

- **Claude Code** — AI reasoning engine
- **Python 3.11** — Watchers & scripts
- **Obsidian** — Markdown vault / knowledge base
- **IMAP** — Gmail monitoring (no Google API needed)

---

## License

MIT — Free to use and modify.

---

*Personal AI Employee · Bronze Tier · Built with Claude Code · 2026-03-09*
