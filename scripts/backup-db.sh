#!/usr/bin/env sh
set -eu
mkdir -p "${BACKUP_DIR:-backups}"
file="${BACKUP_DIR:-backups}/timetabler-$(date -u +%Y%m%dT%H%M%SZ).dump"
docker compose exec -T db pg_dump -Fc -U "${POSTGRES_USER:-timetabler}" "${POSTGRES_DB:-timetabler}" > "$file"
echo "wrote $file"
