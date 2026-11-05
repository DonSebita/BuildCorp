from .base import *  # noqa: F401,F403

DEBUG = False

# La EC2 de AWS Academy se publica por HTTP (puerto 80). Si se agrega HTTPS,
# cambiar estas variables a True en el .env.
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
