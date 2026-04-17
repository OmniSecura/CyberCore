#!/usr/bin/env bash
# =============================================================================
# db_rebuild_indexes.sh — rebuild all indexes in a MySQL database
#
# Runs OPTIMIZE TABLE on every table in the target database.
# OPTIMIZE TABLE in MySQL rebuilds the table and its indexes, reclaims
# fragmented space, and updates index statistics used by the query planner.
# It is equivalent to running ALTER TABLE ... FORCE on InnoDB tables.
#
# Usage:
#   ./db_rebuild_indexes.sh -u <user> -d <database> [-h <host>] [-t <table>]
#
# Arguments:
#   -u  MySQL username
#   -d  Database name
#   -h  MySQL host (default: 127.0.0.1)
#   -t  Specific table to rebuild (default: all tables in the database)
#
# Password is prompted securely at runtime — never pass it as an argument.
#
# Example — all tables:
#   ./db_rebuild_indexes.sh -u root -d cybercore_auth
#
# Example — single table:
#   ./db_rebuild_indexes.sh -u root -d cybercore_auth -t users
# =============================================================================

set -euo pipefail

# ── Defaults ─────────────────────────────────────────────────────────────────
DB_HOST="127.0.0.1"
DB_USER=""
DB_PASS=""
DB_NAME=""
TARGET_TABLE=""

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

MYSQL_BIN="$(find_bin mysql)" || die "mysql client not found.
  Fix: echo 'export PATH=\"\$PATH:/c/Program Files/MySQL/MySQL Server 8.0/bin\"' >> ~/.bashrc && source ~/.bashrc"

# ── Argument parsing ──────────────────────────────────────────────────────────
while getopts ":u:d:h:t:" opt; do
    case $opt in
        u) DB_USER="$OPTARG"       ;;
        d) DB_NAME="$OPTARG"       ;;
        h) DB_HOST="$OPTARG"       ;;
        t) TARGET_TABLE="$OPTARG"  ;;
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

# ── MySQL connection helper ───────────────────────────────────────────────────
mysql_cmd() {
    "$MYSQL_BIN" \
        --host="$DB_HOST" \
        --user="$DB_USER" \
        --password="$DB_PASS" \
        --silent \
        --skip-column-names \
        "$@"
}

# ── Resolve table list ────────────────────────────────────────────────────────
if [[ -n "$TARGET_TABLE" ]]; then
    EXISTS="$(mysql_cmd "$DB_NAME" -e \
        "SELECT COUNT(*) FROM information_schema.TABLES
         WHERE TABLE_SCHEMA = '${DB_NAME}' AND TABLE_NAME = '${TARGET_TABLE}';")"
    [[ "$EXISTS" -eq 1 ]] || die "Table '$TARGET_TABLE' does not exist in database '$DB_NAME'"
    TABLES=("$TARGET_TABLE")
else
    mapfile -t TABLES < <(mysql_cmd "$DB_NAME" -e \
        "SELECT TABLE_NAME FROM information_schema.TABLES
         WHERE TABLE_SCHEMA = '${DB_NAME}' AND TABLE_TYPE = 'BASE TABLE'
         ORDER BY TABLE_NAME;")
fi

[[ ${#TABLES[@]} -eq 0 ]] && die "No tables found in database '$DB_NAME'"

# ── Rebuild ───────────────────────────────────────────────────────────────────
TOTAL=${#TABLES[@]}
DONE=0
FAILED=0

log "Rebuilding indexes in '$DB_NAME' — $TOTAL table(s) to process"
echo

for TABLE in "${TABLES[@]}"; do
    DONE=$(( DONE + 1 ))
    printf "[%s] [%d/%d] Optimizing %s ... " \
        "$(date '+%Y-%m-%d %H:%M:%S')" "$DONE" "$TOTAL" "$TABLE"

    RESULT="$(mysql_cmd "$DB_NAME" -e "OPTIMIZE TABLE \`${TABLE}\`;" 2>&1)"

    if echo "$RESULT" | grep -qi "error"; then
        echo "FAILED"
        err "  $RESULT"
        FAILED=$(( FAILED + 1 ))
    else
        echo "OK"
    fi
done

# ── Update optimizer statistics ───────────────────────────────────────────────
echo
log "Updating optimizer statistics (ANALYZE TABLE)..."

for TABLE in "${TABLES[@]}"; do
    printf "[%s] Analyzing %s ... " "$(date '+%Y-%m-%d %H:%M:%S')" "$TABLE"
    mysql_cmd "$DB_NAME" -e "ANALYZE TABLE \`${TABLE}\`;" > /dev/null
    echo "OK"
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo
log "Done — $TOTAL table(s) processed, $FAILED failed."
[[ $FAILED -gt 0 ]] && exit 1 || exit 0