#!/usr/bin/env sh
set -eu
# Safe local deployment helper. It does not mutate Cloudflare DNS or read secrets.
docker compose up -d --build
docker compose ps
printf '%s\n' 'App is available locally at http://127.0.0.1:8080.' 'Configure Cloudflare Tunnel ingress to this origin only after health checks pass:' '  service: http://127.0.0.1:8080'
