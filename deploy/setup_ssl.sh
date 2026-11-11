#!/usr/bin/env bash
# HTTPS para BuildCorp con Let's Encrypt + Nginx, usando sslip.io como dominio gratuito
# (<IP con guiones>.sslip.io resuelve a la IP pública de la EC2).
#
# Uso:  sudo bash deploy/setup_ssl.sh <IP_PUBLICA> [correo@ejemplo.cl]
# Requisitos: haber corrido deploy/setup_ec2.sh y abrir el puerto 443 en el Security Group.
#
# Resultado:
#   http://<IP>/                    -> sigue funcionando (acceso por IP pública que pide la pauta)
#   http://<dominio>.sslip.io/      -> redirige a HTTPS
#   https://<dominio>.sslip.io/     -> app con certificado válido (cámara del escáner QR en vivo)
set -euo pipefail

IP="${1:?Indica la IP pública de la EC2}"
CORREO="${2:-}"
DOMINIO="${IP//./-}.sslip.io"
APP_DIR="/home/ubuntu/BuildCorp"
WEBROOT="/var/www/certbot"

echo "==> Dominio: ${DOMINIO}"
if ! getent hosts "$DOMINIO" | grep -q "$IP"; then
  echo "ERROR: ${DOMINIO} no resuelve a ${IP}. Revisa la IP." >&2
  exit 1
fi

echo "==> Instalando certbot"
apt-get update -y
apt-get install -y certbot
mkdir -p "$WEBROOT"

echo "==> Bloque de la app compartido por HTTP y HTTPS"
cat > /etc/nginx/snippets/buildcorp_app.conf <<'EOF'
client_max_body_size 10M;   # fotos de activos y firmas

location /static/ {
    alias /home/ubuntu/BuildCorp/staticfiles/;
    expires 7d;
}

location /media/ {
    alias /home/ubuntu/BuildCorp/media/;
}

location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
EOF

escribir_http() {
  cat > /etc/nginx/sites-available/buildcorp <<EOF
# Acceso por IP pública (HTTP), requerido por la evaluación
server {
    listen 80 default_server;
    server_name _;
    location /.well-known/acme-challenge/ { root ${WEBROOT}; }
    include snippets/buildcorp_app.conf;
}

# Dominio sslip.io por HTTP: solo validación de Let's Encrypt y redirección a HTTPS
server {
    listen 80;
    server_name ${DOMINIO};
    location /.well-known/acme-challenge/ { root ${WEBROOT}; }
    location / { return 301 https://\$host\$request_uri; }
}
EOF
}

echo "==> Nginx en HTTP para validar el dominio"
escribir_http
ln -sf /etc/nginx/sites-available/buildcorp /etc/nginx/sites-enabled/buildcorp
nginx -t && systemctl reload nginx

echo "==> Certificado Let's Encrypt"
if [ -n "$CORREO" ]; then
  REG=(-m "$CORREO")
else
  REG=(--register-unsafely-without-email)
fi
certbot certonly --webroot -w "$WEBROOT" -d "$DOMINIO" --agree-tos -n "${REG[@]}" \
  --deploy-hook "systemctl reload nginx"

echo "==> Nginx con HTTPS"
escribir_http
cat >> /etc/nginx/sites-available/buildcorp <<EOF

# HTTPS con certificado válido
server {
    listen 443 ssl;
    http2 on;
    server_name ${DOMINIO};

    ssl_certificate     /etc/letsencrypt/live/${DOMINIO}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMINIO}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:SSL:10m;
    add_header Strict-Transport-Security "max-age=31536000" always;

    include snippets/buildcorp_app.conf;
}
EOF
# Nginx < 1.25 (Ubuntu 22.04) no conoce "http2 on;": usar la sintaxis antigua
if ! nginx -t 2>/dev/null; then
  sed -i -e 's/^    listen 443 ssl;/    listen 443 ssl http2;/' -e '/^    http2 on;/d' /etc/nginx/sites-available/buildcorp
fi
nginx -t && systemctl reload nginx

echo "==> Actualizando .env (hosts, CSRF y URL de los QR)"
ENV="$APP_DIR/.env"
agregar_a_lista() {  # agregar_a_lista VARIABLE valor
  local var="$1" val="$2"
  if grep -q "^${var}=" "$ENV"; then
    grep -q "^${var}=.*${val}" "$ENV" || sed -i "s|^${var}=\(.*\)|${var}=\1,${val}|" "$ENV"
  else
    echo "${var}=${val}" >> "$ENV"
  fi
}
agregar_a_lista ALLOWED_HOSTS "$DOMINIO"
agregar_a_lista CSRF_TRUSTED_ORIGINS "https://${DOMINIO}"
if grep -q "^SITE_URL=" "$ENV"; then
  sed -i "s|^SITE_URL=.*|SITE_URL=https://${DOMINIO}|" "$ENV"
else
  echo "SITE_URL=https://${DOMINIO}" >> "$ENV"
fi
systemctl restart buildcorp

echo "==> Renovación automática"
systemctl list-timers certbot.timer --no-pager || true
certbot renew --dry-run

echo
echo "Listo:"
echo "  http://${IP}/            (IP pública)"
echo "  https://${DOMINIO}/  (HTTPS, cámara del escáner en vivo)"
