#!/bin/bash
# Actualiza el código en el servidor sin tocar el mundo, las copias ni las claves.
# Ejecutar como root:   bash /srv/miovsnuestro/actualizar.sh
set -euo pipefail
DIR=/srv/miovsnuestro
USUARIO=mvn
cd $DIR
echo "== Descargando la última versión =="
sudo -u $USUARIO git -C $DIR pull -q --ff-only
sudo -u $USUARIO git -C $DIR log -1 --format='  Versión: %h · %cs · %s'

# El dominio se guarda en .env (las instalaciones antiguas lo leen del Caddyfile)
DOMINIO=$(grep -E '^DOMINIO=' .env | cut -d= -f2- || true)
if [ -z "$DOMINIO" ]; then
  DOMINIO=$(grep -m1 -oE '^[a-z0-9.-]+\.[a-z]{2,}' /etc/caddy/Caddyfile || true)
  [ -n "$DOMINIO" ] && echo "DOMINIO=$DOMINIO" >> .env
fi

echo "== Servicios, web y tareas programadas =="
for s in motor bot entrevistas; do
  sed -e "s#@DIR@#$DIR#g" -e "s#@USUARIO@#$USUARIO#g" $DIR/despliegue/miovsnuestro-$s.service > /etc/systemd/system/miovsnuestro-$s.service
done
[ -n "$DOMINIO" ] && sed -e "s#@DOMINIO@#$DOMINIO#g" -e "s#@DIR@#$DIR#g" $DIR/despliegue/Caddyfile > /etc/caddy/Caddyfile
sed -e "s#@DIR@#$DIR#g" $DIR/despliegue/cron > /etc/cron.d/miovsnuestro
chown -R $USUARIO:$USUARIO $DIR
systemctl daemon-reload
systemctl enable miovsnuestro-motor miovsnuestro-bot miovsnuestro-entrevistas >/dev/null 2>&1
systemctl restart miovsnuestro-motor miovsnuestro-bot miovsnuestro-entrevistas
systemctl reload caddy || systemctl restart caddy
sleep 3
systemctl is-active --quiet miovsnuestro-motor && echo "  Motor: en marcha" || echo "  Motor: ERROR (journalctl -u miovsnuestro-motor -n 50)"
systemctl is-active --quiet miovsnuestro-bot && echo "  Bot: en marcha" || echo "  Bot: ERROR (journalctl -u miovsnuestro-bot -n 50)"
systemctl is-active --quiet miovsnuestro-entrevistas && echo "  Entrevistas: en marcha" || echo "  Entrevistas: ERROR (journalctl -u miovsnuestro-entrevistas -n 50)"
[ -f $DIR/datos/PAUSA ] && echo "  El mundo sigue EN PAUSA (escribe /reanudar en Telegram cuando quieras que avance)."
echo "Listo."
