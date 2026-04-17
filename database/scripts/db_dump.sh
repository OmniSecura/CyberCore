#!/usr/bin/env bash
# =============================================================================
# db_dump.sh — dump a MySQL database (schema + data) to a timestamped file
#
# Produces a single compressed .sql.gz file containing:
#   - CREATE TABLE statements for every table (schema)
#   - INSERT statements for every row (data)
#   - Stored routines, triggers, and events
#
# The resulting file can be loaded on any MySQL 8.x instance with db_reload.sh
# to restore the database to the exact state it was in at dump time.
#
# Usage:
#   ./db_dump.sh -u <user> -d <database> [-h <host>] [-o <output_dir>]
#
# Arguments:
#   -u  MySQL username
#   -d  Database name to dump
#   -h  MySQL host (default: 127.0.0.1)
#   -o  Output directory for dump files (default: ./dumps)
#
# Password is prompted securely at runtime — never pass it as an argument.
#
# Output:
#   <output_dir>/<database>_YYYY-MM-DD_HH-MM-SS.sql.gz
#
# Example:
#   ./db_dump.sh -u root -d cybercore_auth -o ./dumps
# =============================================================================

set -euo pipefail

# ── Defaults ─────────────────────────────────────────────────────────────────
DB_HOST="127.0.0.1"
DB_USER=""
DB_PASS=""
DB_NAME=""
OUTPUT_DIR="./dumps"

# ── Helpers ───────────────────────────────────────────────────────────────────
log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
err()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2; }
die()  { err "$*"; exit 1; }

# ── Locate MySQL binaries (handles Windows/Git Bash PATH gaps) ────────────────
find_bin() {
    local name="$1"
    if command -v "$name" &>/dev/null; then
        command -v "$name"; return
    fi
    local win_paths=(
        "/c/Program Files/MySQL/MySQL Server 8.0/bin/$name"
        "/c/Program Files/MySQL/MySQL Server 8.4/bin/$name"
        "/c/Program Files/MySQL/MySQL Server 5.7/bin/$name"
        "/c/xampp/mysql/bin/$name"
        "/c/wamp64/bin/mysql/mysql8.0/bin/$name"
    )
    for p in "${win_paths[@]}"; do
        [[ -x "$p"       ]] && { echo "$p";       return; }
        [[ -x "${p}.exe" ]] && { echo "${p}.exe"; return; }
    done
    return 1
}

MYSQLDUMP_BIN="$(find_bin mysqldump)" || die "mysqldump not found.
  Fix: echo 'export PATH=\"\$PATH:/c/Program Files/MySQL/MySQL Server 8.0/bin\"' >> ~/.bashrc && source ~/.bashrc"
MYSQL_BIN="$(find_bin mysql)" || die "mysql not found."
GZIP_BIN="$(find_bin gzip)"   || die "gzip not found — is it installed?"

# ── Argument parsing ──────────────────────────────────────────────────────────
while getopts ":u:d:h:o:" opt; do
    case $opt in
        u) DB_USER="$OPTARG"    ;;
        d) DB_NAME="$OPTARG"    ;;
        h) DB_HOST="$OPTARG"    ;;
        o) OUTPUT_DIR="$OPTARG" ;;
        :) die "Option -$OPTARG requires an argument." ;;
        *) die "Unknown option: -$OPTARG" ;;
    esac
done

# ── Validation ────────────────────────────────────────────────────────────────
[[ -z "$DB_USER" ]] && die "MySQL username is required (-u)"
[[ -z "$DB_NAME" ]] && die "Database name is required (-d)"

# ── Password prompt ───────────────────────────────────────────────────────────
[[ -t 0 ]] || die "No TTY detected — run the script in an interactive terminal."
read -r -s -p "Enter MySQL password for '$DB_USER': " DB_PASS </dev/tty
echo
[[ -z "$DB_PASS" ]] && die "Password cannot be empty."

# ── Verify connection and database existence ───────────────────────────────────
log "Verifying connection to '$DB_NAME' on $DB_HOST..."

DB_EXISTS="$("$MYSQL_BIN" \
    --host="$DB_HOST" \
    --user="$DB_USER" \
    --password="$DB_PASS" \
    --silent --skip-column-names \
    -e "SELECT COUNT(*) FROM information_schema.SCHEMATA
        WHERE SCHEMA_NAME = '${DB_NAME}';" 2>&1)" \
    || die "Could not connect to MySQL — check host, username and password."

[[ "$DB_EXISTS" -eq 1 ]] || die "Database '$DB_NAME' does not exist on $DB_HOST."

# ── Collect pre-dump stats ────────────────────────────────────────────────────
# Count tables and total rows so we can confirm the dump looks complete.
read -r TABLE_COUNT TOTAL_ROWS < <("$MYSQL_BIN" \
    --host="$DB_HOST" \
    --user="$DB_USER" \
    --password="$DB_PASS" \
    --silent --skip-column-names \
    -e "SELECT COUNT(*), COALESCE(SUM(TABLE_ROWS), 0)
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = '${DB_NAME}' AND TABLE_TYPE = 'BASE TABLE';" 2>/dev/null)

log "Database has $TABLE_COUNT table(s), ~$TOTAL_ROWS row(s) (estimate)"

# ── Check whether this MySQL instance uses GTIDs ──────────────────────────────
# --set-gtid-purged errors on servers where GTID mode is OFF and the option
# is not writable. We detect the mode and set the flag accordingly.
GTID_MODE="$("$MYSQL_BIN" \
    --host="$DB_HOST" \
    --user="$DB_USER" \
    --password="$DB_PASS" \
    --silent --skip-column-names \
    -e "SELECT @@GLOBAL.gtid_mode;" 2>/dev/null || echo "OFF")"

if [[ "$GTID_MODE" == "OFF" ]]; then
    GTID_FLAG="--set-gtid-purged=OFF"
else
    GTID_FLAG="--set-gtid-purged=ON"
fi

# ── Setup output ──────────────────────────────────────────────────────────────
mkdir -p "$OUTPUT_DIR"
TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
DUMP_FILE="${OUTPUT_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"
PARTIAL_FILE="${DUMP_FILE}.partial"

# Clean up partial file if script is interrupted mid-dump
trap '[[ -f "$PARTIAL_FILE" ]] && rm -f "$PARTIAL_FILE"; log "Dump interrupted — partial file removed."' INT TERM

# ── Dump ──────────────────────────────────────────────────────────────────────
log "Dumping schema and data..."

"$MYSQLDUMP_BIN" \
    --host="$DB_HOST" \
    --user="$DB_USER" \
    --password="$DB_PASS" \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --column-statistics=0 \
    --add-drop-table \
    --create-options \
    --extended-insert \
    --complete-insert \
    $GTID_FLAG \
    "$DB_NAME" \
    | "$GZIP_BIN" -9 > "$PARTIAL_FILE"

# Only rename to final name once the dump completed without error
mv "$PARTIAL_FILE" "$DUMP_FILE"

# ── Summary ───────────────────────────────────────────────────────────────────
DUMP_SIZE="$(du -sh "$DUMP_FILE" | cut -f1)"

log "Dump complete"
log "  File   : $DUMP_FILE"
log "  Size   : $DUMP_SIZE"
log "  Tables : $TABLE_COUNT"
log "  Rows   : ~$TOTAL_ROWS (engine estimate — actual count may differ)"
log "  Reload : ./db_reload.sh -u $DB_USER -d $DB_NAME -f $DUMP_FILE"