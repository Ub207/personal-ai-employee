@echo off
echo Starting AI Employee Watchers...

start "Gmail Watcher" cmd /k "cd /d D:\bronze_tier && python watchers\gmail_imap_watcher.py --vault-path D:\bronze_tier"
start "Twitter Watcher" cmd /k "cd /d D:\bronze_tier && python watchers\twitter_watcher.py --vault-path D:\bronze_tier"
start "Filesystem Watcher" cmd /k "cd /d D:\bronze_tier && python watchers\filesystem_watcher.py --vault-path D:\bronze_tier"
start "Approval Orchestrator" cmd /k "cd /d D:\bronze_tier && python watchers\approval_orchestrator.py --vault-path D:\bronze_tier"
start "Health Monitor" cmd /k "cd /d D:\bronze_tier && python watchers\health_monitor.py --vault-path D:\bronze_tier"
start "Daily Briefing Scheduler" cmd /k "cd /d D:\bronze_tier && python watchers\daily_briefing_scheduler.py --vault-path D:\bronze_tier"
start "CSV Drop Watcher" cmd /k "cd /d D:\bronze_tier && python watchers\csv_drop_watcher.py --vault-path D:\bronze_tier"

echo All 7 watchers started in separate windows.
