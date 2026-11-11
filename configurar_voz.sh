#!/bin/bash
# Configura la voz del narrador de los reels. Ejecutar como root:  bash /srv/miovsnuestro/configurar_voz.sh
# La clave se escribe solo aquí, en el servidor (archivo .env protegido). Nunca la pegues en un chat.
set -euo pipefail
DIR=/srv/miovsnuestro
ENV=$DIR/.env
poner() { grep -v "^$1=" $ENV > $ENV.tmp || true; echo "$1=$2" >> $ENV.tmp; mv $ENV.tmp $ENV; }
echo "== Voz del narrador =="
echo "1) Azure (gratis hasta 0,5 M caracteres/mes, recomendado)"
echo "2) ElevenLabs (de pago, la más natural)"
echo "3) Piper (local, gratis, más robótica)"
read -rp "Elige 1, 2 o 3: " OP </dev/tty
case "$OP" in
  1) read -rsp "Clave de Azure Speech (Clave 1): " K </dev/tty; echo
     read -rp "Región (ej. westeurope): " R </dev/tty; R=${R:-westeurope}
     read -rp "Voz [es-ES-AlvaroNeural / es-ES-ElviraNeural] (Enter = Alvaro): " V </dev/tty; V=${V:-es-ES-AlvaroNeural}
     poner VOZ_PROVEEDOR azure; poner AZURE_SPEECH_KEY "$K"; poner AZURE_SPEECH_REGION "$R"; poner VOZ_AZURE "$V";;
  2) read -rsp "Clave de API de ElevenLabs: " K </dev/tty; echo
     read -rp "ID de la voz de ElevenLabs: " V </dev/tty
     poner VOZ_PROVEEDOR elevenlabs; poner ELEVENLABS_API_KEY "$K"; poner ELEVENLABS_VOZ "$V";;
  *) poner VOZ_PROVEEDOR piper;;
esac
chown mvn:mvn $ENV; chmod 600 $ENV
echo "== Probando la voz =="
sudo -u mvn bash -c "cd $DIR && set -a && . ./.env && set +a && .venv/bin/python - <<'PY'
from reels import fabrica
r = fabrica.voz('Año uno del experimento. Dos sociedades de inteligencia artificial. Mismo mundo. Valores opuestos.', '/tmp/prueba_voz.wav')
print('Voz OK con', fabrica.VOZ_PROVEEDOR, '->', r) if r else print('No se pudo generar la voz')
PY"
if [ -f /tmp/prueba_voz.wav ] && grep -q '^TELEGRAM_TOKEN=' $ENV; then
  . <(grep -E '^(TELEGRAM_TOKEN|TELEGRAM_CHAT_ID)=' $ENV)
  curl -fsS -F chat_id=$TELEGRAM_CHAT_ID -F caption="Prueba de la voz del narrador" -F audio=@/tmp/prueba_voz.wav \
    "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendAudio" >/dev/null && echo "Te he mandado la prueba a Telegram."
fi
echo "Listo. Los próximos reels usarán esta voz."
