#!/bin/bash
# ╔══════════════════════════════════════════════════════════╗
# ║  SearXNG Private Instance - One-Click Install Script     ║
# ║  (Non-Docker: systemd + venv + Caddy)                   ║
# ║                                                           ║
# ║  Edit CONFIG section di bawah sebelum menjalankan.       ║
# ║  Usage: sudo bash install.sh                             ║
# ╚══════════════════════════════════════════════════════════╝

set -euo pipefail

# ─── CONFIG ───
# Ganti dengan domain kamu
SEARXNG_DOMAIN="search.example.com"
# Kosongkan = auto-generate
SEARXNG_SECRET=""
# Email untuk Let's Encrypt HTTPS
SEARXNG_ADMIN_EMAIL="admin@example.com"
# Kosongkan = auto-generate
CADDY_API_KEY=""

# ─── COLORS ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[ OK ]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERR ]${NC} $1"; }
fatal() { error "$1"; exit 1; }

# ─── CHECK ROOT ───
if [[ $EUID -ne 0 ]]; then
    fatal "Script harus dijalankan sebagai root (sudo bash install.sh)"
fi

# ─── DETECT DISTRO ───
if [[ ! -f /etc/os-release ]]; then
    fatal "Distro tidak terdeteksi"
fi
source /etc/os-release

info "Installing SearXNG private instance on $ID $VERSION_ID"
info "Domain: $SEARXNG_DOMAIN"

# ─── AUTO-GENERATE SECRETS ───
if [[ -z "$SEARXNG_SECRET" ]]; then
    SEARXNG_SECRET=$(openssl rand -hex 32)
    ok "Generated secret_key: ${SEARXNG_SECRET:0:8}...${SEARXNG_SECRET: -8}"
fi

if [[ -z "$CADDY_API_KEY" ]]; then
    CADDY_API_KEY=$(openssl rand -hex 24)
    ok "Generated API key: $CADDY_API_KEY"
fi

# ─── 1. INSTALL DEPENDENCIES ───
info "Installing system dependencies..."
case "$ID" in
    ubuntu|debian)
        apt-get update -qq
        apt-get install -y -qq git curl python3 python3-venv python3-pip \
            ca-certificates gnupg caddy
        ;;
    centos|rhel|fedora|rocky|almalinux)
        if [[ "$ID" == "fedora" || "$ID" == "centos" || "$ID" == "rocky" || "$ID" == "almalinux" ]]; then
            dnf install -y git curl python3 python3-pip ca-certificates gnupg caddy
        else
            yum install -y git curl python3 python3-pip epel-release
            yum install -y ca-certificates gnupg2 caddy
        fi
        ;;
    arch|manjaro)
        pacman -Sy --noconfirm git curl python python-pip ca-certificates gnupg caddy
        ;;
    *)
        fatal "Unsupported distribution: $ID"
        ;;
esac
ok "Dependencies installed"

# ─── 2. CREATE SYSTEM USER ───
if id searxng &>/dev/null; then
    info "User searxng already exists"
else
    info "Creating system user 'searxng'..."
    useradd --system --user-group --home-dir /opt/searxng --no-create-home searxng
    mkdir -p /opt/searxng
    chown searxng:searxng /opt/searxng
    ok "User 'searxng' created"
fi

# ─── 3. DOWNLOAD SEARXNG SOURCE ───
if [[ -d /opt/searxng/searxng-src/.git ]]; then
    info "SearXNG source already exists, updating..."
    cd /opt/searxng/searxng-src
    git pull origin master
    ok "SearXNG updated"
else
    info "Cloning SearXNG repository..."
    chown searxng:searxng /opt/searxng
    sudo -u searxng bash -c "
        cd /opt/searxng
        git clone https://github.com/searxng/searxng.git searxng-src
    "
    ok "SearXNG cloned"
fi

# ─── 4. SETUP PYTHON VENV ───
info "Setting up Python virtual environment..."
sudo -u searxng bash -c "
    cd /opt/searxng/searxng-src
    python3 -m venv searx-pyenv
    source searx-pyenv/bin/activate
    pip install -q -U pip setuptools wheel
    pip install -q -e .
"
ok "Python venv ready"

# ─── 5. CONFIGURE SEARXNG ───
info "Configuring SearXNG..."
SETTINGS="/opt/searxng/settings.yml"

# Copy default settings if needed
if [[ ! -f "$SETTINGS" ]]; then
    cp /opt/searxng/searxng-src/searx/settings.yml "$SETTINGS"
fi

# Create a minimal settings.yml (reliable, no Python dependency)
cat > "$SETTINGS" << 'SETTINGSEOF'
use_default_settings: true

general:
    debug: false
    instance_name: "Private SearXNG"
    enable_metrics: false

server:
    secret_key: PLACEHOLDER_SECRET
    limiter: false
    method: "GET"
    image_proxy: true

search:
    safe_search: 0
    autocomplete: "google"
    default_lang: "auto"
    formats:
        - html
        - json

engines:
    - name: google
      engine: google
      shortcut: g
      disabled: false

    - name: bing
      engine: bing
      shortcut: b
      disabled: false

    - name: duckduckgo
      engine: duckduckgo
      shortcut: ddg
      disabled: false

    - name: brave
      engine: brave
      shortcut: br
      disabled: false

    - name: startpage
      engine: startpage
      shortcut: sp
      disabled: false

    - name: yahoo
      engine: yahoo
      shortcut: yh
      disabled: false

    - name: mojeek
      engine: mojeek
      shortcut: mk
      disabled: false

    - name: ecosia
      engine: ecosia
      shortcut: ec
      disabled: false

    - name: wikipedia
      engine: wikipedia
      shortcut: wp
      disabled: false

    - name: wikidata
      engine: wikidata
      shortcut: wd
      disabled: false

    - name: github
      engine: github
      shortcut: gh
      disabled: false

    - name: stackoverflow
      engine: stackoverflow
      shortcut: so
      disabled: false

    - name: hackernews
      engine: hackernews
      shortcut: hn
      disabled: false

    - name: arxiv
      engine: arxiv
      shortcut: arx
      disabled: false

outgoing:
    request_timeout: 6.0
    max_request_timeout: 15.0
    pool_connections: 100
    pool_maxsize: 20
    retries: 2

ui:
    static_use_hash: true
    cachebuster: true
    default_theme: simple
SETTINGSEOF

# Replace placeholder with real secret
sed -i "s/PLACEHOLDER_SECRET/$SEARXNG_SECRET/" "$SETTINGS"

# Set permissions
chown searxng:searxng "$SETTINGS"
chmod 640 "$SETTINGS"
ok "SearXNG configured"

# ─── 6. SETUP SYSTEMD SERVICE ───
info "Installing systemd service..."

cat > /etc/systemd/system/searxng.service << SERVICEEOF
[Unit]
Description=SearXNG Private Search Instance
Documentation=https://docs.searxng.org/
After=network-online.target
Wants=network-online.target

[Service]
Type=exec
User=searxng
Group=searxng
WorkingDirectory=/opt/searxng/searxng-src
ExecStart=/opt/searxng/searxng-src/searx-pyenv/bin/python \
    /opt/searxng/searxng-src/searx/webapp.py
Restart=on-failure
RestartSec=10
Environment=SEARXNG_SETTINGS_PATH=$SETTINGS
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/searxng

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload
systemctl enable --now searxng
ok "systemd service installed and started"

# ─── 7. WAIT FOR SEARXNG ───
info "Waiting for SearXNG to start..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8080/ >/dev/null 2>&1; then
        ok "SearXNG is running"
        break
    fi
    sleep 1
done

# ─── 8. SETUP CADDY REVERSE PROXY ───
info "Configuring Caddy reverse proxy..."

if grep -q "$SEARXNG_DOMAIN" /etc/caddy/Caddyfile 2>/dev/null; then
    warn "Caddy already configured for $SEARXNG_DOMAIN, skipping"
else
    # Backup original
    cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak 2>/dev/null || true

    cat > /etc/caddy/Caddyfile << CADDYEOF
$SEARXNG_DOMAIN {
    tls $SEARXNG_ADMIN_EMAIL

    @noapikey {
        not header X-API-Key $CADDY_API_KEY
    }
    respond @noapikey 401

    reverse_proxy 127.0.0.1:8080 {
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }

    header {
        -Server
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "no-referrer"
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
    }

    encode zstd gzip

    log {
        output stdout
        format json
        level INFO
    }
}
CADDYEOF

    systemctl restart caddy
    ok "Caddy configured and restarted"
fi

# ─── 9. FIREWALL ───
info "Checking firewall..."
if command -v ufw &>/dev/null; then
    ufw allow 80/tcp 2>/dev/null || true
    ufw allow 443/tcp 2>/dev/null || true
    ok "UFW rules added (ports 80, 443)"
elif command -v firewall-cmd &>/dev/null; then
    firewall-cmd --permanent --add-service=http 2>/dev/null || true
    firewall-cmd --permanent --add-service=https 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
    ok "firewalld rules added (http, https)"
fi

# ─── DONE ───
echo ""
echo "============================================================"
echo "  SearXNG Installation Complete!"
echo "============================================================"
echo ""
echo "  URL:       https://$SEARXNG_DOMAIN"
echo "  API Key:   $CADDY_API_KEY"
echo ""
echo "  Test (locally):"
echo "    curl http://localhost:8080/healthz"
echo ""
echo "  Test (via domain + API key):"
echo "    curl -H 'X-API-Key: $CADDY_API_KEY' \\"
echo "         'https://$SEARXNG_DOMAIN/search?q=test&format=json'"
echo ""
echo "  Update SearXNG:"
echo "    cd /opt/searxng/searxng-src"
echo "    source searx-pyenv/bin/activate"
echo "    git pull && pip install -U -e ."
echo "    systemctl restart searxng caddy"
echo ""
echo "  Logs:"
echo "    journalctl -u searxng -f"
echo "    journalctl -u caddy -f"
echo ""
