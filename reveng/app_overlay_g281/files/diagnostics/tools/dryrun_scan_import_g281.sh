#!/bin/bash
# Local, throw-away PostgreSQL 16 dry-run of server/REVA2_G281_SCAN{1,2}_IMPORT_DRYRUN.sql. Touches no remote database.
# Usage: dryrun_scan_import_g281.sh [1|2|3|all]   (default 1)
# Schema + the private-metadata guard trigger are reconstructed from the live catalog (read-only) in g281_local_schema/.
set -euo pipefail
MODE="${1:-1}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; BIN=/usr/lib/postgresql/16/bin; W="${G281_PG_WORKDIR:-/home/claude/pg_dryrun_run}"
case "$MODE" in 1) SCANS="1"; EXP="1,40,16,24,40";; 2) SCANS="2"; EXP="1,32,32,0,32";; 3) SCANS="3"; EXP="1,30,30,0,30";; all|both) SCANS="1 2 3"; EXP="3,102,78,24,102";; *) echo "usage: $0 [1|2|3|all]"; exit 2;; esac
rm -rf "$W"; mkdir -p "$W"; chown postgres:postgres "$W"; chmod a+rx "$W"
cp "$ROOT"/diagnostics/tools/g281_local_schema/*.sql "$W"/
for n in $SCANS; do cp "$ROOT/server/REVA2_G281_SCAN${n}_IMPORT_DRYRUN.sql" "$W"/; done; chmod a+r "$W"/*.sql
runuser -u postgres -- $BIN/initdb -D "$W/data" -A trust >/dev/null
runuser -u postgres -- $BIN/pg_ctl -D "$W/data" -o "-p 5545 -c listen_addresses='' -c unix_socket_directories=$W" -l "$W/pg.log" -w start >/dev/null
trap 'runuser -u postgres -- $BIN/pg_ctl -D "$W/data" -m immediate stop >/dev/null 2>&1 || true' EXIT
P="runuser -u postgres -- psql -h $W -p 5545 -d postgres -v ON_ERROR_STOP=1 -q -At"
$P -f "$W/inbox_tables.sql"; $P -f "$W/inbox_private_metadata_guard.sql"
for n in $SCANS; do
  $P -f "$W/REVA2_G281_SCAN${n}_IMPORT_DRYRUN.sql"
  [ "$($P -c 'select count(*) from reveng.catalog_candidate_inbox')" = 0 ] || { echo "FAIL: rollback left rows (scan $n)"; exit 1; }
done
for n in $SCANS; do sed 's/^ROLLBACK;/COMMIT;/' "$W/REVA2_G281_SCAN${n}_IMPORT_DRYRUN.sql" > "$W/commit_local_$n.sql"; chmod a+r "$W/commit_local_$n.sql"; $P -f "$W/commit_local_$n.sql"; done
got="$($P -c "select (select count(*) from reveng.catalog_discovery_runs)||','||(select count(*) from reveng.catalog_candidate_inbox)||','||(select count(*) filter (where status='rejected') from reveng.catalog_candidate_inbox)||','||(select count(*) filter (where status='research_queue') from reveng.catalog_candidate_inbox)||','||(select count(*) from reveng.catalog_discovery_run_candidates)")"
[ "$got" = "$EXP" ] || { echo "FAIL: counts $got expected $EXP"; exit 1; }
for n in $SCANS; do $P -f "$W/commit_local_$n.sql"; done; [ "$($P -c 'select count(*) from reveng.catalog_candidate_inbox')" = "$(echo "$EXP" | cut -d, -f2)" ] || { echo "FAIL: not idempotent"; exit 1; }
if $P -c "insert into reveng.catalog_candidate_inbox(fingerprint,candidate_key,analysis_level,raw_name,normalized_name,metadata) values('z','z','niche','n','n','{\"owner_independent\":true}')" >/dev/null 2>&1; then echo "FAIL: guard did not fire"; exit 1; fi
echo "reva2_g281_scan_import_dryrun[$MODE] PASS rollback-clean, counts $EXP (runs,candidates,rejected,research_queue,links), idempotent, private-metadata guard enforced"
