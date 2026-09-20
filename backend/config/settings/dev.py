"""Local development settings."""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True

# Console backend prints email to the terminal, so no SMTP server is needed
# locally and nothing can be accidentally sent to a real address (PRD 11.4).
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

# In development the OTP code is logged rather than sent, so the register ->
# verify flow can be exercised without an SMS provider.
OTP_ECHO_TO_LOG = True

CORS_ALLOW_ALL_ORIGINS = True
