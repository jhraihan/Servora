#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/shebalocal}"
CHECK_DB="${PGDATABASE:-shebalocal}_restore_check"
TABLES=(accounts_user accounts_providerprofile bookings_booking payments_ledgerentry reviews_review trust_trustsnapshot)

latest="$(ls -1t "$BACKUP_DIR"/db-*.dump 2>/dev/null | head -n 1 || true)"
if [[ -z "$latest" ]]; then
  echo "No backups in $BACKUP_DIR" >&2
  exit 1
fi

dropdb --if-exists "$CHECK_DB"
createdb "$CHECK_DB"
trap 'dropdb --if-exists "$CHECK_DB"' EXIT

pg_restore --no-owner --exit-on-error ${RESTORE_LIST:+--use-list="$RESTORE_LIST"} --dbname="$CHECK_DB" "$latest"

echo "Restored $(basename "$latest") into $CHECK_DB"
for table in "${TABLES[@]}"; do
  rows="$(psql -XAtq --dbname="$CHECK_DB" -c "SELECT count(*) FROM $table")"
  printf '  %-26s %s rows\n' "$table" "$rows"
done

if [[ "$(psql -XAtq --dbname="$CHECK_DB" -c "SELECT count(*) FROM accounts_user")" -eq 0 ]]; then
  echo "Restore produced an empty accounts_user table" >&2
  exit 1
fi
echo "Restore check passed; $CHECK_DB dropped."
