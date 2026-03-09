#!/bin/bash
# =============================================================================
# setup_cloud_vm.sh — Platinum Tier Cloud VM Bootstrap
# =============================================================================
# Tested on Ubuntu 22.04 LTS (Oracle Cloud Free Tier / AWS / any Ubuntu VM)
# Run as root or with sudo: bash setup_cloud_vm.sh
#
# What this script does:
#   1. Updates system and installs base dependencies
#   2. Installs Python 3.11+, Node.js 20 LTS
#   3. Clones the vault from Git remote (VAULT_GIT_REMOTE)
#   4. Installs Python + Node dependencies
#   5. Creates the ai-employee system user
#   6. Installs all systemd services from deploy/systemd/
#   7. Enables and starts all services
#
# Usage:
#   export VAULT_GIT_REMOTE="git@github.com:youruser/ai-employee-vault.git"
#   export VAULT_PATH="/opt/ai-employee"
#   bash setup_cloud_vm.sh
# =============================================================================

set -euo pipefail

VAULT_GIT_REMOTE="${VAULT_GIT_REMOTE:-}"
VAULT_PATH="${VAULT_PATH:-/opt/ai-employee}"
AI_USER="${AI_USER:-ai-employee}"
PYTHON_MIN="3.11"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Pre-flight checks ─────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && error "Run as root: sudo bash $0"
[[ -z "$VAULT_GIT_REMOTE" ]] && error "Set VAULT_GIT_REMOTE before running."

info "============================================================"
info "  AI Employee — Cloud VM Setup  (Platinum Tier)"
info "============================================================"
info "  Vault path : $VAULT_PATH"
info "  Git remote : $VAULT_GIT_REMOTE"
info "  System user: $AI_USER"
info "============================================================"

# ── 1. System update ─────────────────────────────────────────────────────────
info "Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
    git curl wget unzip build-essential \
    python3 python3-pip python3-venv \
    software-properties-common apt-transport-https \
    ca-certificates gnupg lsb-release \
    nginx certbot python3-certbot-nginx \
    postgresql postgresql-contrib \
    ufw fail2ban

# ── 2. Node.js 20 LTS ────────────────────────────────────────────────────────
info "Installing Node.js 20 LTS..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
node --version | grep -q "^v20" || warn "Node version unexpected: $(node --version)"

# ── 3. Python 3.11 (if not already) ─────────────────────────────────────────
info "Checking Python version..."
if ! python3 --version 2>&1 | grep -qE "3\.(11|12|13)"; then
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -qq
    apt-get install -y python3.11 python3.11-venv python3.11-dev
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
fi
info "Python: $(python3 --version)"

# ── 4. Create system user ────────────────────────────────────────────────────
info "Creating system user: $AI_USER..."
if ! id "$AI_USER" &>/dev/null; then
    useradd -r -m -s /bin/bash -d /home/$AI_USER "$AI_USER"
fi

# ── 5. Clone vault ───────────────────────────────────────────────────────────
info "Cloning vault from $VAULT_GIT_REMOTE..."
if [[ -d "$VAULT_PATH/.git" ]]; then
    warn "Vault already cloned. Pulling latest..."
    sudo -u $AI_USER git -C "$VAULT_PATH" pull --rebase
else
    sudo -u $AI_USER git clone "$VAULT_GIT_REMOTE" "$VAULT_PATH"
fi

# ── 6. Python virtualenv + dependencies ──────────────────────────────────────
info "Setting up Python virtualenv..."
sudo -u $AI_USER python3 -m venv "$VAULT_PATH/.venv"
sudo -u $AI_USER "$VAULT_PATH/.venv/bin/pip" install --upgrade pip -q
sudo -u $AI_USER "$VAULT_PATH/.venv/bin/pip" install \
    -r "$VAULT_PATH/watchers/requirements.txt" -q
# Install playwright browsers
sudo -u $AI_USER "$VAULT_PATH/.venv/bin/playwright" install chromium --with-deps 2>/dev/null || \
    warn "Playwright browser install skipped (headless LinkedIn/WhatsApp may not work on cloud)"

# ── 7. Node.js dependencies ──────────────────────────────────────────────────
info "Installing Node.js dependencies..."
sudo -u $AI_USER npm --prefix "$VAULT_PATH/mcp_servers" install -q

# ── 8. Ensure .env exists ────────────────────────────────────────────────────
if [[ ! -f "$VAULT_PATH/.env" ]]; then
    cp "$VAULT_PATH/.env.example" "$VAULT_PATH/.env"
    warn ".env created from template. Edit $VAULT_PATH/.env before starting services."
fi
chown $AI_USER:$AI_USER "$VAULT_PATH/.env"
chmod 600 "$VAULT_PATH/.env"

# ── 9. Install systemd services ──────────────────────────────────────────────
info "Installing systemd services..."
SYSTEMD_DIR="$VAULT_PATH/deploy/systemd"

for unit in "$SYSTEMD_DIR"/*.service "$SYSTEMD_DIR"/*.timer; do
    [[ -f "$unit" ]] || continue
    dest="/etc/systemd/system/$(basename "$unit")"
    # Replace placeholder paths in unit files
    sed "s|__VAULT_PATH__|$VAULT_PATH|g; s|__AI_USER__|$AI_USER|g" \
        "$unit" > "$dest"
    info "  Installed: $(basename "$unit")"
done

systemctl daemon-reload

# Enable and start services
SERVICES=(
    ai-employee-filesystem
    ai-employee-gmail
    ai-employee-facebook-instagram
    ai-employee-twitter
    ai-employee-approval
    ai-employee-health
    ai-employee-cloud-orchestrator
    vault-sync
)
TIMERS=(
    ai-employee-briefing
    ai-employee-weekly-audit
    vault-sync
)

for svc in "${SERVICES[@]}"; do
    if systemctl list-unit-files "${svc}.service" &>/dev/null; then
        systemctl enable --now "${svc}.service" 2>/dev/null || warn "Could not start $svc"
        info "  Started: $svc"
    fi
done
for tmr in "${TIMERS[@]}"; do
    if systemctl list-unit-files "${tmr}.timer" &>/dev/null; then
        systemctl enable --now "${tmr}.timer" 2>/dev/null || warn "Could not start $tmr timer"
        info "  Timer started: $tmr"
    fi
done

# ── 10. Firewall ─────────────────────────────────────────────────────────────
info "Configuring firewall (ufw)..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp   # HTTP  (redirect to HTTPS)
ufw allow 443/tcp  # HTTPS (Odoo via nginx)
ufw --force enable

# ── 11. Fail2ban ─────────────────────────────────────────────────────────────
systemctl enable --now fail2ban

# ── Done ─────────────────────────────────────────────────────────────────────
info "============================================================"
info "  Cloud VM setup complete!"
info "============================================================"
info "  Next steps:"
info "  1. Edit $VAULT_PATH/.env with your credentials"
info "  2. Set up Git sync: cd $VAULT_PATH && git remote -v"
info "  3. Run Odoo setup: bash deploy/setup_odoo_cloud.sh"
info "  4. Set up HTTPS: certbot --nginx -d yourdomain.com"
info "  5. Restart services: systemctl restart ai-employee-*"
info "============================================================"
