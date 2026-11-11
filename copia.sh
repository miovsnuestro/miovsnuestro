#!/bin/bash
# Copia de seguridad diaria (cron, 04:00). Guarda 14 días.
set -e
cd "$(dirname "$0")"
mkdir -p copias
for db in datos/*.db; do sqlite3 "$db" ".backup '${db}.bak'"; done
tar -czf "copias/copia_$(date +%Y%m%d_%H%M).tar.gz" datos/*.bak datos/*.pkl datos/*.json 2>/dev/null || true
rm -f datos/*.bak
ls -1t copias/*.tar.gz | tail -n +15 | xargs -r rm -f
