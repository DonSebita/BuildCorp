from .base import *  # noqa: F401,F403

DEBUG = False

# Nginx termina el SSL y avisa a Django con X-Forwarded-Proto (deploy/setup_ssl.sh).
# Así request.is_secure() y la validación CSRF reconocen las peticiones HTTPS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# La app se publica por HTTP en la IP pública (requisito de la evaluación) y por
# HTTPS en <ip>.sslip.io. Las cookies "secure" romperían el login por HTTP, por eso
# quedan en False; si se usa solo HTTPS, cambiarlas a True en el .env.
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)  # noqa: F405
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)  # noqa: F405
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
