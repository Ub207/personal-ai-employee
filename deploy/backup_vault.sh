#!/bin/bash
# =============================================================================
# backup_vault.sh — Daily Vault + Odoo Backup (Platinum Tier)
# =============================================================================
# Creates a timestamped tar.gz of the vault markdown/state files
# and a pg_dump of the Odoo database.
#
# Security: Never backs up .env, sessions, or node_modules.
#
# Setup (cron, runs daily at 3:30 AM):
#   30 3 * * * /opt/ai-employee/deploy/backup_vault.sh >> /var/log/ai-employee/backup.log 2>&1
# =============================================================================

set -euo pipefail

VAULT_PATH="${VAULT_PATH:-/opt/ai-employee}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/ai-employee}"
ODOO_DB="${ODOO_DB:-mycompany}"
ODOO_USER="${ODOO_USER:-odoo}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

DATE=$(date +%Y-%m-%d)
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

mkdir -p "$BACKUP_DIR"

echo "$LOG_PREFIX Starting backup for $DATE"

# ── 1. Vault markdown backup ──────────────────────────────────────────────────
VAULT_BACKUP="$BACKUP_DIR/vault_${DATE}.tar.gz"

tar --exclude="$VAULT_PATH/.venv" \
    --exclude="$VAULT_PATH/node_modules" \
    --exclude="$VAULT_PATH/.env" \
    --exclude="$VAULT_PATH/.whatsapp_session" \
    --exclude="$VAULT_PATH/.linkedin_session" \
    --exclude="$VAULT_PATH/__pycache__" \
    --exclude="*.pyc" \
    --exclude="*.session" \
    -czf "$VAULT_BACKUP" \
    -C "$(dirname "$VAULT_PATH")" \
    "$(basename "$VAULT_PATH")"

VAULT_SIZE=$(du -h "$VAULT_BACKUP" | cut -f1)
echo "$LOG_PREFIX Vault backup: $VAULT_BACKUP ($VAULT_SIZE)"

# ── 2. Odoo database backup (if Odoo is running) ──────────────────────────────
if systemctl is-active --quiet odoo 2>/dev/null; then
    ODOO_BACKUP="$BACKUP_DIR/odoo_${DATE}.sql.gz"
    sudo -u "$ODOO_USER" pg_dump "$ODOO_DB" | gzip > "$ODOO_BACKUP"
    ODOO_SIZE=$(du -h "$ODOO_BACKUP" | cut -f1)
    echo "$LOG_PREFIX Odoo backup: $ODOO_BACKUP ($ODOO_SIZE)"
else
    echo "$LOG_PREFIX Odoo not running — skipping DB backup"
fi

# ── 3. Git push (vault state to remote) ──────────────────────────────────────
if [[ -d "$VAULT_PATH/.git" ]]; then
    cd "$VAULT_PATH"
    # Stage only markdown/json (security rule)
    git add '*.md' '*.json' 2>/dev/null || true
    if git diff --cached --quiet; then
        echo "$LOG_PREFIX Git: nothing to commit"
    else
        git commit -m "[cloud] Nightly backup sync $DATE" --quiet
        git push --quiet 2>/dev/null && \
            echo "$LOG_PREFIX Git: pushed to remote" || \
            echo "$LOG_PREFIX Git: push failed (check remote access)"
    fi
fi

# ── 4. Prune old backups ──────────────────────────────────────────────────────
find "$BACKUP_DIR" -name "vault_*.tar.gz" -mtime +"$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name "odoo_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete
echo "$LOG_PREFIX Pruned backups older than $RETENTION_DAYS days"

echo "$LOG_PREFIX Backup complete"
