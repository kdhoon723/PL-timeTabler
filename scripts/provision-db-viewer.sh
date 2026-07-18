#!/bin/sh
set -eu

: "${DB_VIEWER_PASSWORD:?DB_VIEWER_PASSWORD is required}"

psql --no-psqlrc --set=ON_ERROR_STOP=1 \
  --set=viewer_password="$DB_VIEWER_PASSWORD" <<'SQL'
SELECT CASE
  WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'timetabler_viewer')
    THEN format('ALTER ROLE timetabler_viewer LOGIN PASSWORD %L', :'viewer_password')
  ELSE format('CREATE ROLE timetabler_viewer LOGIN PASSWORD %L', :'viewer_password')
END \gexec

ALTER ROLE timetabler_viewer SET default_transaction_read_only = on;
GRANT CONNECT ON DATABASE timetabler TO timetabler_viewer;
GRANT USAGE ON SCHEMA public TO timetabler_viewer;
REVOKE CREATE ON SCHEMA public FROM timetabler_viewer;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO timetabler_viewer;
ALTER DEFAULT PRIVILEGES FOR ROLE timetabler IN SCHEMA public
  GRANT SELECT ON TABLES TO timetabler_viewer;
SQL
