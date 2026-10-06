#!/usr/bin/env bash
set -euo pipefail
PUBLIC_BASE="${RDP_PUBLIC_BASE:-https://rdp.iniakpothompson.com}"

echo "Local API health:"
curl -fsS http://127.0.0.1:8010/api/v1/health; echo

echo "Local public-cohort API:"
curl -fsS http://127.0.0.1:8010/api/v1/rdp/public/cohort >/dev/null
echo "OK"

echo "Local Next.js:"
curl -fsS -I http://127.0.0.1:3010/ | head -n 1

if [[ "${RDP_SKIP_PUBLIC_CHECK:-0}" != "1" ]]; then
  echo "Public frontend:"
  curl -fsS -I "$PUBLIC_BASE/" | head -n 1
  echo "Public API through Plesk/nginx:"
  curl -fsS "$PUBLIC_BASE/api/v1/health"; echo
fi
