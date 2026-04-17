#!/usr/bin/env bash
# =============================================================================
# db_reload.sh — restore a MySQL database from a dump file
#
# Restores both schema (CREATE TABLE) and data (INSERT) from a dump produced
# by db_dump.sh. The target database is dropped and recreated from scratch,
# so the result is an exact copy of the database at the time of the dump.
#
# Usage:
#   ./db_reload.sh -u <user> -d <database> -f <dump_file> [-h <host>] [-y]
#
# Arguments:
#   -u  MySQL username
#   -d  Target database name (will be dropped and recreated)
#   -f  Path to the dump file (.sql or .sql.gz)
#   -h  MySQL host (default: 127.0.0.1)
#   -y  Skip confirmation prompt (non-interactive / CI use)
#
# Password is prompted securely at runtime — never pass it as an argument.
#
# Example:
#   ./db_reload.sh -u root -d cybercore_auth -f ./dumps/cybercore_auth_2025-01-01_12-00-00.sql.gz
# =============================================================================

set -euo pipefail

# ── Defaults ─────────────────────────────────────────────────────────────────
DB_HOST="127.0.0.1"
DB_USER=""
DB_PASS=""
DB_NAME=""
DUMP_FILE=""
SKIP_CONFIRM=false

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

MYSQL_BIN="$(find_bin mysql)"   || die "mysql client not found.
  Fix: echo 'export PATH=\"\$PATH:/c/Program Files/MySQL/MySQL Server 8.0/bin\"' >> ~/.bashrc && source ~/.bashrc"
GUNZIP_BIN="$(find_bin gunzip)" || die "gunzip not found — is it installed?"

# ── Argument parsing ──────────────────────────────────────────────────────────
while getopts ":u:d:f:h:y" opt; do
    case $opt in
        u) DB_USER="$OPTARG"    ;;
        d) DB_NAME="$OPTARG"    ;;
        f) DUMP_FILE="$OPTARG"  ;;
        h) DB_HOST="$OPTARG"    ;;
        y) SKIP_CONFIRM=true    ;;
        :) die "Option -$OPTARG requires an argument." ;;
        *) die "Unknown option: -$OPTARG" ;;
    esac
done

# ── Validation ────────────────────────────────────────────────────────────────
[[ -z "$DB_USER"   ]] && die "MySQL username is required (-u)"
[[ -z "$DB_NAME"   ]] && die "Target database name is required (-d)"
[[ -z "$DUMP_FILE" ]] && die "Dump file path is required (-f)"
[[ -f "$DUMP_FILE" ]] || die "Dump file not found: $DUMP_FILE"

# ── Integrity check ───────────────────────────────────────────────────────────
# Verify the file is non-empty and, if gzipped, is not corrupt.
DUMP_SIZE_BYTES="$(wc -c < "$DUMP_FILE")"
[[ "$DUMP_SIZE_BYTES" -gt 0 ]] || die "Dump file is empty: $DUMP_FILE"

if [[ "$DUMP_FILE" == *.gz ]]; then
    log "Verifying dump file integrity..."
    "$GUNZIP_BIN" -t "$DUMP_FILE" 2>/dev/null \
        || die "Dump file is corrupt or incomplete: $DUMP_FILE"
    log "File OK"
fi

# ── Password prompt ───────────────────────────────────────────────────────────
[[ -t 0 ]] || die "No TTY detected — run the script in an interactive terminal."
read -r -s -p "Enter MySQL password for '$DB_USER': " DB_PASS </dev/tty
echo
[[ -z "$DB_PASS" ]] && die "Password cannot be empty."

# ── Verify connection ─────────────────────────────────────────────────────────
log "Verifying connection to $DB_HOST..."
"$MYSQL_BIN" \
    --host="$DB_HOST" \
    --user="$DB_USER" \
    --password="$DB_PASS" \
    --silent \
    -e "SELECT 1;" &>/dev/null \
    || die "Could not connect to MySQL — check host, username and password."
log "Connection OK"

# ── Confirmation ──────────────────────────────────────────────────────────────
DUMP_SIZE_HUMAN="$(du -sh "$DUMP_FILE" | cut -f1)"

if [[ "$SKIP_CONFIRM" == false ]]; then
    echo
    echo "  WARNING: This will DROP and recreate '$DB_NAME' on $DB_HOST."
    echo "  All existing data in that database will be permanently lost."
    echo
    echo "  Dump file : $DUMP_FILE"
    echo "  File size : $DUMP_SIZE_HUMAN"
    echo
    read -r -p "  Type the database name to confirm: " CONFIRM </dev/tty
    [[ "$CONFIRM" == "$DB_NAME" ]] || die "Confirmation did not match — aborting."
fi

# ── MySQL connection helper ───────────────────────────────────────────────────
mysql_cmd() {
    "$MYSQL_BIN" \
        --host="$DB_HOST" \
        --user="$DB_USER" \
        --password="$DB_PASS" \
        --silent \
        "$@"
}

# ── Drop and recreate database ────────────────────────────────────────────────
log "Dropping and recreating database '$DB_NAME'..."

mysql_cmd <<SQL
DROP DATABASE IF EXISTS \`${DB_NAME}\`;
CREATE DATABASE \`${DB_NAME}\`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
SQL

# ── Restore ───────────────────────────────────────────────────────────────────
log "Restoring from $DUMP_FILE ($DUMP_SIZE_HUMAN) — this may take a while..."

START_TS="$(date +%s)"

if [[ "$DUMP_FILE" == *.gz ]]; then
    "$GUNZIP_BIN" -c "$DUMP_FILE" | mysql_cmd "$DB_NAME"
else
    mysql_cmd "$DB_NAME" < "$DUMP_FILE"
fi

END_TS="$(date +%s)"
ELAPSED=$(( END_TS - START_TS ))

# ── Post-restore verification ─────────────────────────────────────────────────
# Count tables and estimated rows in the restored database to confirm
# the restore actually loaded something.
read -r TABLE_COUNT TOTAL_ROWS < <(mysql_cmd --skip-column-names "$DB_NAME" -e \
    "SELECT COUNT(*), COALESCE(SUM(TABLE_ROWS), 0)
     FROM information_schema.TABLES
     WHERE TABLE_SCHEMA = '${DB_NAME}' AND TABLE_TYPE = 'BASE TABLE';")

# ── Summary ───────────────────────────────────────────────────────────────────
log "Restore complete"
log "  Database : $DB_NAME on $DB_HOST"
log "  Tables   : $TABLE_COUNT"
log "  Rows     : ~$TOTAL_ROWS (engine estimate)"
log "  Duration : ${ELAPSED}s"