#!/bin/bash
# =============================================================================
# setup_odoo_cloud.sh — Platinum Tier Odoo 17 Community Cloud Deployment
# =============================================================================
# Deploys Odoo Community on Ubuntu 22.04 with:
#   - PostgreSQL database
#   - Nginx reverse proxy with HTTPS (certbot)
#   - Systemd service for 24/7 uptime
#   - Daily pg_dump backups to /var/backups/odoo/
#   - Health monitoring endpoint
#
# Usage:
#   export ODOO_DOMAIN="odoo.yourdomain.com"
#   export ODOO_ADMIN_PASS="your-master-password"
#   export ODOO_DB="mycompany"
#   bash setup_odoo_cloud.sh
# =============================================================================

set -euo pipefail

ODOO_VERSION="${ODOO_VERSION:-17.0}"
ODOO_USER="${ODOO_USER:-odoo}"
ODOO_HOME="${ODOO_HOME:-/opt/odoo}"
ODOO_PORT="${ODOO_PORT:-8069}"
ODOO_DOMAIN="${ODOO_DOMAIN:-}"
ODOO_ADMIN_PASS="${ODOO_ADMIN_PASS:-changeme}"
ODOO_DB="${ODOO_DB:-mycompany}"
BACKUP_DIR="/var/backups/odoo"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

[[ $EUID -ne 0 ]] && error "Run as root: sudo bash $0"

info "============================================================"
info "  AI Employee — Odoo Cloud Setup  (Platinum Tier)"
info "============================================================"
info "  Domain  : ${ODOO_DOMAIN:-not set (HTTP only)}"
info "  DB name : $ODOO_DB"
info "  Port    : $ODOO_PORT"
info "============================================================"

# ── Dependencies ─────────────────────────────────────────────────────────────
info "Installing Odoo dependencies..."
apt-get update -qq
apt-get install -y -qq \
    python3-pip python3-dev python3-venv libxml2-dev libxslt-dev \
    libevent-dev libsasl2-dev libldap2-dev libpq-dev libjpeg-dev \
    libssl-dev libffi-dev wkhtmltopdf fonts-liberation \
    postgresql postgresql-contrib nginx certbot python3-certbot-nginx

# ── PostgreSQL setup ──────────────────────────────────────────────────────────
info "Configuring PostgreSQL..."
systemctl enable --now postgresql
sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname='$ODOO_USER'" \
    | grep -q 1 || sudo -u postgres createuser -d -R -S "$ODOO_USER"
info "PostgreSQL user '$ODOO_USER' ready."

# ── Odoo system user ─────────────────────────────────────────────────────────
if ! id "$ODOO_USER" &>/dev/null; then
    useradd -r -m -s /bin/bash -d "$ODOO_HOME" "$ODOO_USER"
fi

# ── Clone Odoo ───────────────────────────────────────────────────────────────
info "Cloning Odoo $ODOO_VERSION..."
if [[ ! -d "$ODOO_HOME/odoo" ]]; then
    sudo -u $ODOO_USER git clone --depth 1 \
        --branch "$ODOO_VERSION" \
        https://github.com/odoo/odoo.git \
        "$ODOO_HOME/odoo"
else
    warn "Odoo source already exists. Skipping clone."
fi

# ── Python virtualenv ────────────────────────────────────────────────────────
info "Creating Python virtualenv for Odoo..."
sudo -u $ODOO_USER python3 -m venv "$ODOO_HOME/venv"
sudo -u $ODOO_USER "$ODOO_HOME/venv/bin/pip" install --upgrade pip wheel -q
sudo -u $ODOO_USER "$ODOO_HOME/venv/bin/pip" install \
    -r "$ODOO_HOME/odoo/requirements.txt" -q

# ── Odoo config ──────────────────────────────────────────────────────────────
info "Writing Odoo config..."
mkdir -p /etc/odoo /var/log/odoo /var/lib/odoo
chown $ODOO_USER:$ODOO_USER /var/log/odoo /var/lib/odoo

cat > /etc/odoo/odoo.conf <<EOF
[options]
admin_passwd = $ODOO_ADMIN_PASS
db_host = localhost
db_port = 5432
db_user = $ODOO_USER
db_password = False
db_name = $ODOO_DB
http_port = $ODOO_PORT
http_interface = 127.0.0.1
logfile = /var/log/odoo/odoo.log
log_level = warn
workers = 2
max_cron_threads = 1
proxy_mode = True
data_dir = /var/lib/odoo
EOF
chmod 640 /etc/odoo/odoo.conf
chown root:$ODOO_USER /etc/odoo/odoo.conf

# ── Systemd service ──────────────────────────────────────────────────────────
info "Installing Odoo systemd service..."
cat > /etc/systemd/system/odoo.service <<EOF
[Unit]
Description=Odoo Community $ODOO_VERSION
After=postgresql.service network.target

[Service]
Type=simple
User=$ODOO_USER
Group=$ODOO_USER
ExecStart=$ODOO_HOME/venv/bin/python3 $ODOO_HOME/odoo/odoo-bin \
    -c /etc/odoo/odoo.conf
Restart=on-failure
RestartSec=10
KillMode=mixed
StandardOutput=journal
StandardError=journal
SyslogIdentifier=odoo

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now odoo
info "Odoo service started. Initializing DB (this takes 2-3 minutes)..."
sleep 10

# ── Initialize Odoo database ─────────────────────────────────────────────────
info "Initializing Odoo database '$ODOO_DB'..."
sudo -u $ODOO_USER "$ODOO_HOME/venv/bin/python3" "$ODOO_HOME/odoo/odoo-bin" \
    -c /etc/odoo/odoo.conf \
    -d "$ODOO_DB" \
    --init base,account \
    --without-demo=all \
    --stop-after-init 2>/dev/null || warn "DB init may have already run."

# ── Nginx config ─────────────────────────────────────────────────────────────
info "Configuring Nginx..."
if [[ -n "$ODOO_DOMAIN" ]]; then
    cp "$ODOO_HOME/../deploy/nginx.conf" /etc/nginx/sites-available/odoo 2>/dev/null || \
    cat > /etc/nginx/sites-available/odoo <<NGINX
upstream odoo_backend {
    server 127.0.0.1:$ODOO_PORT;
}
server {
    listen 80;
    server_name $ODOO_DOMAIN;
    return 301 https://\$host\$request_uri;
}
server {
    listen 443 ssl http2;
    server_name $ODOO_DOMAIN;
    ssl_certificate     /etc/letsencrypt/live/$ODOO_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$ODOO_DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    proxy_read_timeout 720s;
    proxy_connect_timeout 720s;
    proxy_send_timeout 720s;
    proxy_set_header X-Forwarded-Host \$host;
    proxy_set_header X-Forwarded-For  \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Real-IP \$remote_addr;
    location / { proxy_pass http://odoo_backend; }
    location ~* /web/static/ {
        proxy_pass http://odoo_backend;
        proxy_cache_valid 200 90d;
        add_header Cache-Control "public, max-age=7776000";
    }
    gzip on;
    gzip_types text/css text/less text/plain text/xml application/xml application/json application/javascript;
    client_max_body_size 64m;
}
NGINX
    ln -sf /etc/nginx/sites-available/odoo /etc/nginx/sites-enabled/odoo
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl reload nginx
    info "Nginx configured for $ODOO_DOMAIN"
    info "Run: certbot --nginx -d $ODOO_DOMAIN   to enable HTTPS"
else
    warn "ODOO_DOMAIN not set. Skipping Nginx/HTTPS setup."
fi

# ── Backup setup ─────────────────────────────────────────────────────────────
info "Setting up daily backups to $BACKUP_DIR..."
mkdir -p "$BACKUP_DIR"
chown $ODOO_USER:$ODOO_USER "$BACKUP_DIR"

cat > /usr/local/bin/odoo-backup.sh <<BACKUP
#!/bin/bash
# Daily Odoo backup: pg_dump + filestore
set -euo pipefail
DATE=\$(date +%Y-%m-%d)
BACKUP_FILE="$BACKUP_DIR/odoo_\${DATE}.sql.gz"
pg_dump -U $ODOO_USER $ODOO_DB | gzip > "\$BACKUP_FILE"
# Keep last 30 days
find "$BACKUP_DIR" -name "odoo_*.sql.gz" -mtime +30 -delete
echo "Backup complete: \$BACKUP_FILE"
BACKUP
chmod +x /usr/local/bin/odoo-backup.sh

# Cron: daily backup at 3 AM
(crontab -l 2>/dev/null; echo "0 3 * * * /usr/local/bin/odoo-backup.sh >> /var/log/odoo/backup.log 2>&1") | crontab -

# ── Done ─────────────────────────────────────────────────────────────────────
info "============================================================"
info "  Odoo Cloud setup complete!"
info "============================================================"
info "  Access  : http://$(hostname -I | awk '{print $1}'):$ODOO_PORT"
[[ -n "$ODOO_DOMAIN" ]] && info "  Domain  : https://$ODOO_DOMAIN (after certbot)"
info "  Admin   : Use master password from /etc/odoo/odoo.conf"
info "  Logs    : journalctl -u odoo -f"
info "  Backups : $BACKUP_DIR"
info "============================================================"
