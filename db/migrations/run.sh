#!/usr/bin/env bash
# Aplicador de migraciones SQL plano, idempotente (RNF-07).
# Itera /migrations/*.sql en orden, omite versiones ya registradas en
# schema_migrations y aplica cada una dentro de una transacción.
set -euo pipefail

MIGRATIONS_DIR="${MIGRATIONS_DIR:-/migrations}"

# DATABASE_URL tiene prioridad; si no, se arma desde las variables PG*.
PSQL_DSN="${DATABASE_URL:-}"
if [ -z "${PSQL_DSN}" ]; then
  PSQL_DSN="postgresql://${PGUSER:-tfg}:${PGPASSWORD:-tfg}@${PGHOST:-db}:${PGPORT:-5432}/${PGDATABASE:-tfg}"
fi

run_psql() {
  psql "${PSQL_DSN}" -v ON_ERROR_STOP=1 --no-psqlrc -q "$@"
}

echo "[migrate] destino: ${PGHOST:-db}"

run_psql -c "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now());"

shopt -s nullglob
files=("${MIGRATIONS_DIR}"/*.sql)

for file in "${files[@]}"; do
  version="$(basename "${file}")"
  already="$(run_psql -t -A -c "SELECT 1 FROM schema_migrations WHERE version = '${version}' LIMIT 1;")"
  if [ "${already}" = "1" ]; then
    echo "[migrate] omitida (ya aplicada): ${version}"
    continue
  fi
  echo "[migrate] aplicando: ${version}"
  run_psql --single-transaction -f "${file}" -c "INSERT INTO schema_migrations (version) VALUES ('${version}');"
done

echo "[migrate] completado."
