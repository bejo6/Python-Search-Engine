# ╔══════════════════════════════════════════════════════════╗
# ║  SearXNG Private Instance - Non-Docker Deployment        ║
# ║  (systemd + venv + Caddy)                               ║
# ║                                                           ║
# ║  Files:                                                  ║
# ║  ├── install.sh            - One-click install script    ║
# ║  ├── settings.yml          - SearXNG config              ║
# ║  ├── searxng.service       - systemd service file        ║
# ║  └── Caddyfile             - HTTPS + auth reverse proxy  ║
# ╚══════════════════════════════════════════════════════════╝

## Quick Start

```bash
# Copy files ke VPS
scp -r deploy/systemd/* user@your-vps:/opt/searxng/

# SSH ke VPS
ssh user@your-vps

# Jalankan install
sudo bash /opt/searxng/install.sh
```

## Manual Installation

```bash
# 1. Buat user dedicated
sudo adduser --system --group --home /opt/searxng searxng

# 2. Clone SearXNG
sudo -u searxng -i
cd /opt/searxng
git clone https://github.com/searxng/searxng.git searxng-src
cd searxng-src

# 3. Setup Python virtual env
python3 -m venv searx-pyenv
source searx-pyenv/bin/activate
pip install -U pip setuptools wheel

# 4. Install SearXNG
pip install -e .

# 5. Setup setting
cp settings.yml /opt/searxng/settings.yml
# Edit settings.yml: ganti secret_key, sesuaikan engines

# 6. Setup systemd
sudo cp searxng.service /etc/systemd/system/searxng.service
sudo systemctl daemon-reload
sudo systemctl enable --now searxng

# 7. Setup Caddy untuk HTTPS + Auth
# Edit Caddyfile: ganti domain, API key/username
sudo cp Caddyfile /etc/caddy/Caddyfile
sudo systemctl restart caddy
```

## Struktur Directory

```
/opt/searxng/
├── searxng-src/            # Source code SearXNG
│   └── searx-pyenv/        # Python virtual environment
├── settings.yml            # Config (mounted read-only)
├── searxng.service         # systemd unit
└── Caddyfile              # Caddy config
```

## Testing

```bash
# Test lokal (tanpa auth)
curl http://localhost:8080/healthz

# Test via domain (dengan API key)
curl -H "X-API-Key: YOUR_SECRET_API_KEY" \
     "https://search.example.com/search?q=test&format=JSON"
```

## Update

```bash
sudo -u searxng -i
cd searxng-src
source searx-pyenv/bin/activate
git pull origin master
pip install -U -e .
sudo systemctl restart searxng
```

## Logs

```bash
# SearXNG logs
journalctl -u searxng -f --no-pager

# Caddy logs
journalctl -u caddy -f --no-pager
# atau: journalctl -u caddy -f | jq .
```
