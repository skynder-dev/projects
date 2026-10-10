#!/bin/bash
# Local, throw-away PostgreSQL 16 dry-run of server/REVA2_G281_SCAN1_IMPORT_DRYRUN.sql. Touches no remote database.
# Schema + the private-metadata guard trigger are reconstructed from the live catalog (read-only) in g281_local_schema/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; BIN=/usr/lib/postgresql/16/bin; W="${G281_PG_WORKDIR:-/home/claude/pg_dryrun_run}"
rm -rf "$W"; mkdir -p "$W"; chown postgres:postgres "$W"; chmod a+rx "$W"
cp "$ROOT"/diagnostics/tools/g281_local_schema/*.sql "$ROOT"/server/REVA2_G281_SCAN1_IMPORT_DRYRUN.sql "$W"/; chmod a+r "$W"/*.sql
runuser -u postgres -- $BIN/initdb -D "$W/data" -A trust >/dev/null
runuser -u postgres -- $BIN/pg_ctl -D "$W/data" -o "-p 5545 -c listen_addresses='' -c unix_socket_directories=$W" -l "$W/pg.log" -w start >/dev/null
trap 'runuser -u postgres -- $BIN/pg_ctl -D "$W/data" -m immediate stop >/dev/null 2>&1 || true' EXIT
P="runuser -u postgres -- psql -h $W -p 5545 -d postgres -v ON_ERROR_STOP=1 -q -At"
$P -f "$W/inbox_tables.sql"; $P -f "$W/inbox_private_metadata_guard.sql"
$P -f "$W/REVA2_G281_SCAN1_IMPORT_DRYRUN.sql"
[ "$($P -c 'select count(*) from reveng.catalog_candidate_inbox')" = 0 ] || { echo "FAIL: rollback left rows"; exit 1; }
sed 's/^ROLLBACK;/COMMIT;/' "$W/REVA2_G281_SCAN1_IMPORT_DRYRUN.sql" > "$W/commit_local.sql"; chmod a+r "$W/commit_local.sql"
$P -f "$W/commit_local.sql"
got="$($P -c "select (select count(*) from reveng.catalog_discovery_runs)||','||(select count(*) from reveng.catalog_candidate_inbox)||','||(select count(*) filter (where status='rejected') from reveng.catalog_candidate_inbox)||','||(select count(*) filter (where status='research_queue') from reveng.catalog_candidate_inbox)||','||(select count(*) from reveng.catalog_discovery_run_candidates)")"
[ "$got" = "1,40,16,24,40" ] || { echo "FAIL: counts $got"; exit 1; }
$P -f "$W/commit_local.sql"; [ "$($P -c 'select count(*) from reveng.catalog_candidate_inbox')" = 40 ] || { echo "FAIL: not idempotent"; exit 1; }
if $P -c "insert into reveng.catalog_candidate_inbox(fingerprint,candidate_key,analysis_level,raw_name,normalized_name,metadata) values('z','z','niche','n','n','{\"owner_independent\":true}')" >/dev/null 2>&1; then echo "FAIL: guard did not fire"; exit 1; fi
echo "reva2_g281_scan_import_dryrun PASS rollback-clean, 1 run/40 candidates/16 rejected/24 research_queue/40 links, idempotent, private-metadata guard enforced"
