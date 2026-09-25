#!/usr/bin/env bash
set -euo pipefail
umask 077

BACKUP_DIR="${BACKUP_DIR:-/var/backups/shebalocal}"
BACKEND_DIR="${BACKEND_DIR:-/srv/shebalocal/backend}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
export PGDATABASE="${PGDATABASE:-shebalocal}"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
database="$BACKUP_DIR/db-$stamp.dump"
media="$BACKUP_DIR/media-$stamp.tar.gz"
mkdir -p "$BACKUP_DIR"

pg_dump --format=custom --no-owner --file="$database.partial"
pg_restore --list "$database.partial" > /dev/null
mv "$database.partial" "$database"

tar -C "$BACKEND_DIR" -czf "$media.partial" media private_media
mv "$media.partial" "$media"

find "$BACKUP_DIR" -maxdepth 1 \( -name 'db-*.dump' -o -name 'media-*.tar.gz' \) -mtime +"$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -maxdepth 1 -name '*.partial' -mmin +60 -delete

if [[ -n "${BACKUP_REMOTE:-}" ]]; then
  rsync -a --delete "$BACKUP_DIR/" "$BACKUP_REMOTE"
fi

echo "$(date -u +%FT%TZ) backup ok: $(basename "$database") $(du -h "$database" | cut -f1), $(basename "$media") $(du -h "$media" | cut -f1)"
