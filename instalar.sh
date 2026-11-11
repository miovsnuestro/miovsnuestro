#!/bin/bash
# Instalador de Mío vs Nuestro para Ubuntu 24.04. Ejecutar como root en el servidor:
#   curl -fsSL https://raw.githubusercontent.com/miovsnuestro/miovsnuestro/main/instalar.sh | bash
# Pide las claves aquí mismo: nunca pasan por ningún chat.
set -euo pipefail
REPO="${REPO:-https://github.com/miovsnuestro/miovsnuestro.git}"
DIR=/srv/miovsnuestro
USUARIO=mvn

echo "== Mío vs Nuestro: instalación =="
read -rp "Dominio (ej. miovsnuestro.com): " DOMINIO </dev/tty
read -rsp "Clave de API de DeepSeek: " DEEPSEEK </dev/tty; echo
read -rsp "Token del bot de Telegram: " TGTOKEN </dev/tty; echo
read -rp "Mundo a arrancar [pruebas/oficial] (pruebas): " MUNDO </dev/tty; MUNDO=${MUNDO:-pruebas}
read -rsp "Token de GitHub para el informe diario (opcional, Enter para saltar): " GHTOKEN </dev/tty; echo

echo "== 1/7 Paquetes del sistema =="
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git ffmpeg sqlite3 fonts-dejavu-core debian-keyring debian-archive-keyring apt-transport-https curl gpg >/dev/null
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -qq && apt-get install -y -qq caddy >/dev/null
fi

echo "== 2/7 Código =="
id -u $USUARIO >/dev/null 2>&1 || useradd -m -s /bin/bash $USUARIO
if [ -d $DIR/.git ]; then git -C $DIR pull -q; else git clone -q "$REPO" $DIR; fi
mkdir -p $DIR/datos $DIR/copias $DIR/voces $DIR/reels/salida $DIR/reels/musica

echo "== 3/7 Entorno de Python, navegador para grabar y voz =="
python3 -m venv $DIR/.venv
$DIR/.venv/bin/pip install -q --upgrade pip playwright piper-tts
export PLAYWRIGHT_BROWSERS_PATH=$DIR/.navegadores
$DIR/.venv/bin/playwright install --with-deps chromium >/dev/null
VOZ=$DIR/voces/es_ES-davefx-medium.onnx
if [ ! -f $VOZ ]; then
  curl -fsSL -o $VOZ "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx" || echo "  (voz no descargada: los reels saldrán sin narración)"
  curl -fsSL -o $VOZ.json "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json" || true
fi

echo "== 4/7 Telegram: escribe «hola» a tu bot ahora mismo =="
CHAT=""
for i in $(seq 1 30); do
  CHAT=$(curl -fsS "https://api.telegram.org/bot${TGTOKEN}/getUpdates" | python3 -c "import sys,json;r=json.load(sys.stdin)['result'];print(r[-1]['message']['chat']['id'] if r else '')" 2>/dev/null || true)
  [ -n "$CHAT" ] && break; sleep 4
done
[ -z "$CHAT" ] && { echo "No he recibido tu «hola». Vuelve a ejecutar el instalador."; exit 1; }
echo "  Chat encontrado."

echo "== 5/7 Claves (solo en este servidor, archivo .env protegido) =="
umask 077
cat > $DIR/.env <<ENV
DEEPSEEK_API_KEY=$DEEPSEEK
TELEGRAM_TOKEN=$TGTOKEN
TELEGRAM_CHAT_ID=$CHAT
MUNDO=$MUNDO
DOMINIO=$DOMINIO
REEL_URL=http://127.0.0.1/
PLAYWRIGHT_BROWSERS_PATH=$DIR/.navegadores
PIPER=$DIR/.venv/bin/piper
GITHUB_TOKEN=$GHTOKEN
GITHUB_REPO=${REPO#https://}
ENV
umask 022
chown -R $USUARIO:$USUARIO $DIR
chmod 600 $DIR/.env

echo "== 6/7 Servicios (se reinician solos si se caen) =="
for s in motor bot entrevistas; do
  sed -e "s#@DIR@#$DIR#g" -e "s#@USUARIO@#$USUARIO#g" $DIR/despliegue/miovsnuestro-$s.service > /etc/systemd/system/miovsnuestro-$s.service
done
echo "$USUARIO ALL=(root) NOPASSWD: /usr/bin/systemctl restart miovsnuestro-motor" > /etc/sudoers.d/miovsnuestro
chmod 440 /etc/sudoers.d/miovsnuestro
sed -e "s#@DOMINIO@#$DOMINIO#g" -e "s#@DIR@#$DIR#g" $DIR/despliegue/Caddyfile > /etc/caddy/Caddyfile
sed -e "s#@DIR@#$DIR#g" $DIR/despliegue/cron > /etc/cron.d/miovsnuestro
systemctl daemon-reload
systemctl enable --now miovsnuestro-motor miovsnuestro-bot miovsnuestro-entrevistas >/dev/null
systemctl reload caddy || systemctl restart caddy

sudo -u $USUARIO $DIR/copia.sh || true
echo "== 7/7 Comprobación =="
sleep 5
systemctl is-active --quiet miovsnuestro-motor && echo "  Motor: en marcha" || echo "  Motor: ERROR (journalctl -u miovsnuestro-motor)"
systemctl is-active --quiet miovsnuestro-bot && echo "  Bot: en marcha" || echo "  Bot: ERROR (journalctl -u miovsnuestro-bot)"
systemctl is-active --quiet miovsnuestro-entrevistas && echo "  Entrevistas: en marcha" || echo "  Entrevistas: ERROR (journalctl -u miovsnuestro-entrevistas)"
curl -fsS "https://api.telegram.org/bot${TGTOKEN}/sendMessage" -d chat_id=$CHAT -d text="✅ Mío vs Nuestro instalado. Mundo «$MUNDO» en marcha. Escribe /estado cuando quieras." >/dev/null
echo "Listo. Web: https://$DOMINIO (puede tardar unos minutos en tener certificado)."
