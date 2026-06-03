#!/bin/bash
# ══════════════════════════════════════════════════════════════════════
# 1S: ERP Free Edition — One-click VPS deploy script
# Usage: bash deploy.sh [domain]
# Example: bash deploy.sh www.1s-compiler.ru
#
# Tested on: Ubuntu 22.04, Debian 12
# Requires:  sudo, git, docker, docker compose
# ══════════════════════════════════════════════════════════════════════
set -euo pipefail

DOMAIN="${1:-www.1s-compiler.ru}"
REPO="https://github.com/vftens/1s-compiler.git"
APP_DIR="/opt/1s-erp"
EMAIL="aico@ya.ru"   # change to your email for Let's Encrypt

echo ""
echo "═══════════════════════════════════════════════════"
echo "  1S: ERP Free Edition — VPS Deploy"
echo "  Domain: $DOMAIN"
echo "═══════════════════════════════════════════════════"
echo ""

# ── 1. System dependencies ────────────────────────────────────────────
echo "[1/6] Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq docker.io docker-compose-v2 git certbot python3-certbot-nginx nginx

# ── 2. Clone / update repo ───────────────────────────────────────────
echo "[2/6] Setting up application..."
if [ -d "$APP_DIR" ]; then
    cd "$APP_DIR" && git pull --ff-only
else
    git clone "$REPO" "$APP_DIR"
    cd "$APP_DIR"
fi
mkdir -p data/config

# ── 3. Build Docker image ─────────────────────────────────────────────
echo "[3/6] Building Docker image..."
docker build -t 1s-erp:latest .

# ── 4. Start application ─────────────────────────────────────────────
echo "[4/6] Starting application..."
docker run -d --name 1s-erp-app --restart unless-stopped \
    -p 127.0.0.1:5000:5000 \
    -v "$APP_DIR/data/config:/app/config" \
    -e PYTHONUTF8=1 \
    1s-erp:latest

sleep 3
curl -sf http://localhost:5000/api/v1/ping | grep -q '"status":"ok"' \
    && echo "  ✓ App is healthy" \
    || echo "  ! App health check failed — check logs: docker logs 1s-erp-app"

# ── 5. Nginx + SSL ────────────────────────────────────────────────────
echo "[5/6] Configuring Nginx..."
sed "s/1s-compiler.ru/$DOMAIN/g" "$APP_DIR/nginx/nginx.conf" \
    > /etc/nginx/sites-available/1s-erp
ln -sf /etc/nginx/sites-available/1s-erp /etc/nginx/sites-enabled/1s-erp
nginx -t && systemctl reload nginx

echo "[5/6] Obtaining SSL certificate..."
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
    -m "$EMAIL" --redirect || echo "  ! SSL skipped (check domain DNS)"

# ── 6. Done ───────────────────────────────────────────────────────────
echo ""
echo "[6/6] Setting up auto-renewal..."
systemctl enable --now certbot.timer 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Deploy complete!"
echo "  URL:    https://$DOMAIN"
echo "  Login:  admin / admin   (CHANGE THIS!)"
echo "  Logs:   docker logs 1s-erp-app -f"
echo "═══════════════════════════════════════════════════"
