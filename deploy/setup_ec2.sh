#!/usr/bin/env bash
# Instalación de BuildCorp en una EC2 Ubuntu 22.04/24.04 (AWS Academy).
# Uso:  sudo bash deploy/setup_ec2.sh <IP_PUBLICA> [CLAVE_DB]
# Ejecutar desde la carpeta del repositorio ya clonado en /home/ubuntu/BuildCorp.
set -euo pipefail

IP="${1:?Indica la IP pública de la EC2}"
CLAVE_DB="${2:-$(openssl rand -hex 12)}"
APP_DIR="/home/ubuntu/BuildCorp"
USUARIO="ubuntu"

echo "==> Paquetes del sistema"
apt-get update -y
apt-get install -y python3-venv python3-pip postgresql nginx git

echo "==> Base de datos PostgreSQL (solo localhost)"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='buildcorp'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER buildcorp WITH PASSWORD '${CLAVE_DB}';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='buildcorp'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE buildcorp OWNER buildcorp;"

echo "==> Entorno virtual y dependencias"
sudo -u "$USUARIO" python3 -m venv "$APP_DIR/.venv"
sudo -u "$USUARIO" "$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

if [ ! -f "$APP_DIR/.env" ]; then
  echo "==> Creando .env"
  cat > "$APP_DIR/.env" <<EOF
DEBUG=False
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=postgres://buildcorp:${CLAVE_DB}@localhost:5432/buildcorp
ALLOWED_HOSTS=${IP},localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://${IP}
SITE_URL=http://${IP}
EOF
  chown "$USUARIO":"$USUARIO" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
fi

echo "==> Migraciones, estáticos y datos demo"
cd "$APP_DIR"
export DJANGO_SETTINGS_MODULE=buildcorp.settings.prod
sudo -u "$USUARIO" -E .venv/bin/python manage.py migrate --noinput
sudo -u "$USUARIO" -E .venv/bin/python manage.py collectstatic --noinput
sudo -u "$USUARIO" -E .venv/bin/python manage.py cargar_roles
sudo -u "$USUARIO" -E .venv/bin/python manage.py cargar_demo || true
mkdir -p "$APP_DIR/media" && chown -R "$USUARIO":www-data "$APP_DIR/media" && chmod -R 775 "$APP_DIR/media"
chmod 755 /home/ubuntu

echo "==> Gunicorn (systemd)"
cp deploy/gunicorn.service /etc/systemd/system/buildcorp.service
systemctl daemon-reload
systemctl enable --now buildcorp
systemctl restart buildcorp

echo "==> Nginx"
cp deploy/nginx_buildcorp.conf /etc/nginx/sites-available/buildcorp
ln -sf /etc/nginx/sites-available/buildcorp /etc/nginx/sites-enabled/buildcorp
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "==> Cron (morosidad y mantenciones)"
crontab -u "$USUARIO" deploy/crontab.txt

echo "==> Despliegue automático (revisa GitHub cada 2 minutos)"
cp deploy/buildcorp-actualizar.service deploy/buildcorp-actualizar.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now buildcorp-actualizar.timer

echo "Listo:http://${IP}/  (usuarios demo: admin, bodeguero, encargado, ventas · clave buildcorp2026)"
