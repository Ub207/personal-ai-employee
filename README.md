<p align="center">
  <img src="https://img.shields.io/badge/Status-Production-brightgreen?style=for-the-badge" />
  <img src="https://img.shields.io/badge/System-4_Tier-blueviolet?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Uptime-24%2F7-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Python-3.9+-yellow?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Claude-Opus_4-FF6B35?style=for-the-badge&logo=anthropic&logoColor=white" />
  <img src="https://img.shields.io/badge/MCP_Servers-10-2C5364?style=for-the-badge" />
</p>

<h1 align="center">Personal AI Employee (Digital FTE)</h1>

<p align="center">
  <strong>A 4-tier autonomous AI agent system that replaces 10+ hours/week of manual business operations.</strong>
</p>

<p align="center">
  <em>Not a chatbot. A full-time digital worker that monitors, drafts, routes, and executes — with human approval.</em>
</p>

---

## The Problem

Solo founders and small agencies spend **10-15 hours/week** on repetitive tasks:
- Reading and replying to emails
- Posting on social media
- Creating invoices and chasing payments
- Updating spreadsheets and dashboards
- Coordinating across platforms

## The Solution

An **AI Employee** that handles all of this **24/7**, autonomously — while keeping humans in control of every decision that matters.

---

## 4-Tier Architecture

```
    PLATINUM ──── Cloud VM (24/7) + Local Machine + Git Vault Sync
        |         Oracle Cloud orchestrator runs even when laptop is off
        |
      GOLD ────── Twitter + Facebook + Instagram + Slack + Odoo ERP
        |         Calendar integration + CEO Briefings + Audit logging
        |
     SILVER ───── Gmail OAuth + LinkedIn + WhatsApp + Obsidian Vault
        |         Human-in-the-loop approval workflow
        |
     BRONZE ───── Core agent loop + File processing + Planning engine
                  Foundation for all automation tiers
```

| Tier | What It Adds | MCP Servers |
|------|-------------|-------------|
| **Bronze** | Core agent loop, file watchers, planning engine | filesystem |
| **Silver** | Email, LinkedIn, WhatsApp, Obsidian GUI | +email, +linkedin, +browser |
| **Gold** | Twitter, FB/IG, Slack, Odoo, Calendar, CEO briefings | +twitter, +facebook-instagram, +slack, +odoo, +calendar |
| **Platinum** | Cloud VM 24/7, Git sync, claim-by-move, dual-agent | All 10 servers |

---

## Complete Feature Matrix

### Communication Automation
| Channel | Monitor | Draft Reply | Send | Approval |
|---------|---------|-------------|------|----------|
| **Gmail** | Auto | AI-drafted | Via MCP | Required |
| **WhatsApp** | Auto | AI-drafted | Human clicks | Required |
| **Slack** | Auto | AI-drafted | Via MCP | Required |

### Social Media Management
| Platform | Draft | Post | Rate Limit |
|----------|-------|------|-----------|
| **LinkedIn Personal** | AI-drafted | Via MCP | 2/week |
| **LinkedIn Company** | AI-drafted | Via MCP | 2/week |
| **Twitter/X** | AI-drafted | Via MCP | Unlimited |
| **Facebook** | AI-drafted | Via MCP | Unlimited |
| **Instagram** | AI-drafted | Via MCP | Unlimited |

### Business Operations
| Function | Capability |
|----------|-----------|
| **Invoicing** | Auto-create draft invoices in Odoo ERP |
| **Payment Follow-ups** | Auto-detect overdue, draft follow-up |
| **Vendor Bills** | Process and create in ERP |
| **CEO Briefing** | Weekly auto-generated business report |
| **Calendar** | Create events, find free slots |
| **Accounting** | Revenue summaries, bank reconciliation |

---

## System Architecture

```
                    ┌─────────────────────────────┐
                    │     Oracle Cloud VM          │
                    │     (Always-On 24/7)         │
                    │                              │
                    │  cloud_orchestrator.py       │
                    │   ├─ Email triage            │
                    │   ├─ Social media drafts     │
                    │   ├─ Odoo invoice drafts     │
                    │   └─ Health monitoring       │
                    └──────────┬──────────────────┘
                               │
                         Git Vault Sync
                        (GitHub Private)
                               │
                    ┌──────────┴──────────────────┐
                    │     Local Machine            │
                    │                              │
                    │  platinum_orchestrator.py     │
                    │   ├─ Gmail OAuth watcher     │
                    │   ├─ WhatsApp watcher        │
                    │   ├─ Approval executor       │
                    │   ├─ Workflow runner          │
                    │   └─ Dashboard updater       │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────┴──────────────────┐
                    │     Obsidian Vault (GUI)     │
                    │                              │
                    │  Human reviews & approves    │
                    │  in Markdown files           │
                    └─────────────────────────────┘
```

---

## 10 MCP Server Integrations

```
  linkedin ──────── Personal & Company page posts
  email ─────────── Gmail: send, read, search, draft (OAuth2)
  twitter ────────── Tweet, timeline, search
  facebook-ig ───── Facebook + Instagram posts
  odoo ────────────── 13 ERP tools (invoices, payments, partners, bills)
  filesystem ────── Vault read/write/search/move
  browser ─────────── Web automation (navigate, click, fill, screenshot)
  calendar ────────── Google Calendar: events, free slots
  slack ─────────── Messages, channels, status, file upload
  (vault-sync) ──── Git-based sync between cloud & local
```

---

## Safety & Governance

> **Human-in-the-loop by design.** No message is sent, no payment is made, and no post goes live without explicit human approval.

| Rule | Description |
|------|------------|
| **Plan First** | Every action requires a PLAN_*.md before execution |
| **Human Approves** | All outbound actions need sign-off |
| **Draft Only** | Accounting entries always created as DRAFT |
| **Never Auto-Send** | Human always clicks the final Send/Post |
| **Audit Trail** | Every action logged with timestamp |
| **Rate Limited** | Max 2 LinkedIn posts/week, 10 emails/hour |

---

## Workflow

```
Event detected (email / message / scheduled task)
        │
        ▼
Watcher creates item in Needs_Action/
        │
        ▼
AI creates PLAN_*.md ──► AI drafts response
        │
        ▼
Pending_Approval/ (human reviews in Obsidian)
        │
   ┌────┴────┐
   ▼         ▼
Approved/  Rejected/
   │
   ▼
Executor sends via MCP ──► Audit log ──► Done/
```

---

## Performance

| Metric | Result |
|--------|--------|
| Weekly time saved | **12+ hours** |
| Email draft speed | < 5 minutes |
| Social posts/week | 4 (2 personal + 2 company) |
| System uptime | 24/7 (cloud VM) |
| Platforms integrated | **10** |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Brain | Claude Code (Opus 4) |
| Language | Python 3.9+ |
| Vault/GUI | Obsidian |
| Cloud | Oracle Cloud (Always Free) |
| ERP | Odoo 17 (Docker) |
| Integrations | 10 MCP Servers |
| Sync | Git (private repo) |
| Monitoring | systemd + health signals |

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/Ub207/personal-ai-employee.git
cd personal-ai-employee

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start the system
python platinum_orchestrator.py
```

---

## Repository Structure

| Repo | Tier | Description |
|------|------|------------|
| [personal-ai-employee](https://github.com/Ub207/personal-ai-employee) | Overview | Main system documentation |
| [silver-tier-ai-employee](https://github.com/Ub207/silver-tier-ai-employee) | Silver | Email, LinkedIn, WhatsApp |
| [gold-tier-ai-employee](https://github.com/Ub207/gold-tier-ai-employee) | Gold | Multi-platform + ERP |
| [vault-sync](https://github.com/Ub207/vault-sync) | Platinum | Cloud-Local vault sync |

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Built by <a href="https://github.com/Ub207">Ubaid ur Rahman</a></strong><br/>
  AI Automation Consulting for Solo Founders & Small Agencies<br/><br/>
  <a href="mailto:usmanubaidurrehman@gmail.com"><img src="https://img.shields.io/badge/Hire_Me-Available-brightgreen?style=for-the-badge" /></a>
</p>
