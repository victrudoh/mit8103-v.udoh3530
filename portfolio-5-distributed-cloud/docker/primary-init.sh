#!/bin/bash
# Runs once, when the primary's data directory is first initialised.
# It creates the account the replica uses and allows it to stream WAL.
set -euo pipefail

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'SQL'
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'replicator_password';
SQL

# pg_hba.conf has no replication rule for other containers by default;
# 'all' in the database column never matches replication connections.
echo "host replication replicator all scram-sha-256" >> "$PGDATA/pg_hba.conf"
