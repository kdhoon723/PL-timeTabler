#!/usr/bin/env sh
set -eu
[ "$#" -eq 1 ] || { echo "usage: $0 backup.dump" >&2; exit 2; }
docker compose exec -T db pg_restore --clean --if-exists -U "${POSTGRES_USER:-timetabler}" -d "${POSTGRES_DB:-timetabler}" < "$1"
