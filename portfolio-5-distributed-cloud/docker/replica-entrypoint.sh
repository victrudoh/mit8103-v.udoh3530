#!/bin/bash
# Builds the replica from a base backup of the primary on first start, then
# runs it as a hot standby. A restart reuses the existing data directory.
set -euo pipefail

export PGDATA="${PGDATA:-/var/lib/postgresql/data}"

if [ ! -s "$PGDATA/PG_VERSION" ]; then
  mkdir -p "$PGDATA"
  chown postgres:postgres "$PGDATA"
  chmod 700 "$PGDATA"

  until pg_isready -h pg-primary -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do
    sleep 1
  done

  # -R writes standby.signal and primary_conninfo, -X stream copies WAL while
  # the backup runs, and -C -S creates a replication slot so the primary keeps
  # the WAL the replica still needs. application_name identifies this standby
  # in pg_stat_replication and in synchronous_standby_names.
  gosu postgres env PGPASSWORD=replicator_password pg_basebackup \
    --dbname "host=pg-primary port=5432 user=replicator application_name=replica1" \
    --pgdata "$PGDATA" --write-recovery-conf --wal-method=stream \
    --create-slot --slot=replica_slot_1 --checkpoint=fast --progress --verbose
fi

exec docker-entrypoint.sh postgres -c hot_standby=on
