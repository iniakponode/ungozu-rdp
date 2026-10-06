#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo/root"; exit 1; fi
APP_ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
APP_USER="${2:-$(stat -c '%U' "$APP_ROOT")}"; APP_GROUP="${3:-$(stat -c '%G' "$APP_ROOT")}"; NPM_PATH="$(command -v npm)"
[[ -x "$APP_ROOT/.runtime/venv/bin/uvicorn" ]] || { echo "Run deploy.sh once before installing services."; exit 1; }
for name in ungozu-rdp-api ungozu-rdp-web; do src="$APP_ROOT/deploy/systemd/$name.service.template"; dst="/etc/systemd/system/$name.service"; sed -e "s|__APP_ROOT__|$APP_ROOT|g" -e "s|__APP_USER__|$APP_USER|g" -e "s|__APP_GROUP__|$APP_GROUP|g" -e "s|__NPM_PATH__|$NPM_PATH|g" "$src" > "$dst"; done
systemctl daemon-reload; systemctl enable ungozu-rdp-api ungozu-rdp-web; systemctl restart ungozu-rdp-api ungozu-rdp-web
systemctl --no-pager --full status ungozu-rdp-api ungozu-rdp-web || true
