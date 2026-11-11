#!/usr/bin/env bash
# Despliegue automático de BuildCorp: revisa si hay commits nuevos en origin/main y,
# si los hay, actualiza el código, dependencias, migraciones y estáticos, y reinicia Gunicorn.
# Lo ejecuta como root el timer buildcorp-actualizar.timer cada 2 minutos.
# También se puede correr a mano:  sudo bash deploy/actualizar.sh
set -euo pipefail

APP_DIR="/home/ubuntu/BuildCorp"
USUARIO="ubuntu"
RAMA="main"
LOG="/home/ubuntu/buildcorp-deploy.log"

# Evita dos despliegues a la vez
exec 9>/run/buildcorp-actualizar.lock
flock -n 9 || exit 0

cd "$APP_DIR"
como_app() { sudo -u "$USUARIO" -H env DJANGO_SETTINGS_MODULE=buildcorp.settings.prod "$@"; }
log() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }

como_app git fetch -q origin "$RAMA"
ACTUAL=$(como_app git rev-parse HEAD)
NUEVO=$(como_app git rev-parse "origin/$RAMA")
[ "$ACTUAL" = "$NUEVO" ] && exit 0

trap 'log "ERROR: el despliegue de ${NUEVO:0:7} falló (revisa journalctl -u buildcorp-actualizar)"' ERR

log "Desplegando ${ACTUAL:0:7} -> ${NUEVO:0:7}: $(como_app git log -1 --format=%s "$NUEVO")"
CAMBIADOS=$(como_app git diff --name-only "$ACTUAL" "$NUEVO")
como_app git merge -q --ff-only "origin/$RAMA"

if grep -qx "requirements.txt" <<<"$CAMBIADOS"; then
  log "requirements.txt cambió: instalando dependencias"
  como_app .venv/bin/pip install -q -r requirements.txt
fi

como_app .venv/bin/python manage.py migrate --noinput
como_app .venv/bin/python manage.py collectstatic --noinput >/dev/null

if grep -qx "deploy/gunicorn.service" <<<"$CAMBIADOS"; then
  cp deploy/gunicorn.service /etc/systemd/system/buildcorp.service
  systemctl daemon-reload
fi
systemctl restart buildcorp

log "OK: ${NUEVO:0:7} desplegado"
