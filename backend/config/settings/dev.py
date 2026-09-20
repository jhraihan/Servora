from .base import *
from .base import env

DEBUG = True

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

OTP_ECHO_TO_LOG = True

CORS_ALLOW_ALL_ORIGINS = True
