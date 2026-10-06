#!/usr/bin/env bash
set -euo pipefail

# Preferred usage:
#   RDP_DB_NAME=mydb RDP_DB_USER=myuser RDP_DB_HOST=127.0.0.1 ./deploy/scripts/backup_db.sh
# Password is requested interactively by mysqldump so it is not exposed in shell history.
DB_HOST="${RDP_DB_HOST:-127.0.0.1}"
DB_PORT="${RDP_DB_PORT:-3306}"
DB_NAME="${RDP_DB_NAME:-}"
DB_USER="${RDP_DB_USER:-}"
BACKUP_DIR="${RDP_BACKUP_DIR:-$HOME/rdp-db-backups}"

[[ -n "$DB_NAME" ]] || { echo "Set RDP_DB_NAME"; exit 1; }
[[ -n "$DB_USER" ]] || { echo "Set RDP_DB_USER"; exit 1; }
command -v mysqldump >/dev/null 2>&1 || { echo "mysqldump is not installed"; exit 1; }

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/${DB_NAME}-${STAMP}.sql.gz"

echo "Backing up $DB_NAME to $OUT"
mysqldump --single-transaction --routines --triggers --host="$DB_HOST" --port="$DB_PORT" --user="$DB_USER" --password "$DB_NAME" | gzip -9 > "$OUT"
chmod 600 "$OUT"
test -s "$OUT"
echo "Backup complete: $OUT"
