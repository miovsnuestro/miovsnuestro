#!/bin/bash
# Informe diario para la revisión programada de Claude: sube salud, latido y marcador (sin mapa,
# sin claves) a la rama «estado» del repositorio. Solo si hay GITHUB_TOKEN en .env.
set -e
cd "$(dirname "$0")"
source <(grep -E '^(GITHUB_TOKEN|GITHUB_REPO)=' .env)
[ -z "${GITHUB_TOKEN:-}" ] && exit 0
D=datos/informe_repo
if [ ! -d $D/.git ]; then
  git clone -q --single-branch --branch estado "https://x-access-token:${GITHUB_TOKEN}@${GITHUB_REPO}" $D 2>/dev/null || {
    git init -q $D && git -C $D checkout -q -b estado && git -C $D remote add origin "https://x-access-token:${GITHUB_TOKEN}@${GITHUB_REPO}"; }
fi
cp datos/salud.json datos/latido.json $D/ 2>/dev/null || true
.venv/bin/python - <<'PY' > $D/marcador.json
import json; e = json.load(open("web/estado.json")); e.pop("mapa", None); e["agentes"] = len(e["agentes"]); print(json.dumps(e, ensure_ascii=False, indent=1))
PY
tail -n 100 datos/vigilante.log > $D/vigilante.log 2>/dev/null || true
sqlite3 -json datos/$(cat .mundo).db "SELECT dia, titulo, estado FROM propuestas ORDER BY id DESC LIMIT 10" > $D/propuestas.json 2>/dev/null || true
sqlite3 -json datos/$(cat .mundo).db "SELECT dia, campo, motivos FROM moderacion ORDER BY rowid DESC LIMIT 20" > $D/moderacion.json 2>/dev/null || true
tail -n 60 datos/reels.log > $D/reels.log 2>/dev/null || true
sqlite3 -json datos/reels.db "SELECT id, datetime(creado,'unixepoch') AS creado, estado, version FROM reels ORDER BY id DESC LIMIT 10" > $D/reels.json 2>/dev/null || true
git log -1 --format='%h %cs %s' > $D/version.txt 2>/dev/null || true
cd $D && git add -A
git diff --cached --quiet || git -c user.name="miovsnuestro-servidor" -c user.email="servidor@miovsnuestro" commit -qm "Informe $(date +%F)"
git push -q origin estado
