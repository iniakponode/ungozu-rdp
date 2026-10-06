#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${RDP_APP_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
RUNTIME="$APP_ROOT/.runtime"
VENV="$RUNTIME/venv"
cd "$APP_ROOT"

[[ -f backend/.env ]] || { echo "ERROR: Missing backend/.env"; exit 1; }
[[ -f frontend/.env.production ]] || { echo "ERROR: Missing frontend/.env.production"; exit 1; }

mkdir -p "$RUNTIME"
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/pip" install -r backend/requirements.txt

(
  cd backend
  "$VENV/bin/python" -m compileall -q app
  "$VENV/bin/alembic" heads
  "$VENV/bin/alembic" upgrade head
  "$VENV/bin/alembic" current
)

(
  cd frontend
  npm ci
  npm run type-check
  npm run build
)

restart_services() {
  systemctl restart ungozu-rdp-api ungozu-rdp-web
}

if [[ "${RDP_SKIP_RESTART:-0}" != "1" ]] && systemctl list-unit-files 2>/dev/null | grep -q '^ungozu-rdp-api.service'; then
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    restart_services
  elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    sudo systemctl restart ungozu-rdp-api ungozu-rdp-web
  else
    echo "NOTE: Build/migration succeeded, but this user cannot restart systemd services."
    echo "      Run as root: systemctl restart ungozu-rdp-api ungozu-rdp-web"
  fi
fi

# These local checks succeed after services have been installed/started.
if curl -fsS http://127.0.0.1:8010/api/v1/health >/dev/null 2>&1; then
  curl -fsS http://127.0.0.1:8010/api/v1/health; echo
else
  echo "NOTE: API is not running yet. This is expected on the first deployment before systemd installation."
fi
if curl -fsS -I http://127.0.0.1:3010/ >/dev/null 2>&1; then
  curl -fsS -I http://127.0.0.1:3010/ | head -n 1
else
  echo "NOTE: Next.js is not running yet. This is expected on the first deployment before systemd installation."
fi

printf '\nDeployment build and migration checks completed successfully.\n'
