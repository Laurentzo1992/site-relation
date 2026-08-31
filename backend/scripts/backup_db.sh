#!/usr/bin/env bash
# Dumps the production Postgres database to a timestamped, gzip-compressed
# file. Run from the project root (where docker-compose.prod.yml and .env live):
#   ./backend/scripts/backup_db.sh
#
# Suggested cron entry (daily at 3am, keeping the last 14 backups):
#   0 3 * * * cd /path/to/site-relation && ./backend/scripts/backup_db.sh >> /var/log/site-relation-backup.log 2>&1
set -euo pipefail

cd "$(dirname "$0")/../.."  # project root

if [ ! -f .env ]; then
  echo "Error: .env not found in project root. Run this script from the deployed project." >&2
  exit 1
fi
set -a
source .env
set +a

BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILE="$BACKUP_DIR/siterelation_${TIMESTAMP}.sql.gz"

docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$FILE"

echo "Backup written to $FILE"

# Keep only the 14 most recent backups
ls -1t "$BACKUP_DIR"/siterelation_*.sql.gz 2>/dev/null | tail -n +15 | xargs -r rm --
