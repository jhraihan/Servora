#!/usr/bin/env bash
set -euo pipefail

cd /srv/shebalocal/backend
export DJANGO_SETTINGS_MODULE=config.settings.prod
exec venv/bin/python manage.py "$@"
