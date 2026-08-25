#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

TMP_BASE=${TMPDIR:-/tmp}/weight-tracker-public-scan.$$
TMP_ARCHIVE="$TMP_BASE.tar.gz"
TMP_DIR="$TMP_BASE.dir"
cleanup() { rm -rf "$TMP_ARCHIVE" "$TMP_DIR"; }
trap cleanup EXIT HUP INT TERM
mkdir -p "$TMP_DIR"

# Test the files that would actually ship, rather than live runtime data that may
# legitimately sit beside the code in an installed instance.
tar -C "$(dirname "$ROOT")" \
  --exclude='*.db' --exclude='*.db-wal' --exclude='*.db-shm' \
  --exclude='*.db.bak*' --exclude='*-export.json' \
  --exclude='__pycache__' --exclude='*.pyc' --exclude='dist' \
  --exclude='*.log' --exclude='*.pid' --exclude='.env' --exclude='api.env' \
  -czf "$TMP_ARCHIVE" "$(basename "$ROOT")"

tar -xzf "$TMP_ARCHIVE" -C "$TMP_DIR"
CANDIDATE="$TMP_DIR/$(basename "$ROOT")"

# Machine-specific home-directory references must never ship in public docs,
# prompts, code, tests, or examples.
if grep -RInE '/home/[[:alnum:]_.-]+/|/Users/[[:alnum:]_.-]+/' "$CANDIDATE" \
    --exclude-dir=__pycache__ --exclude='*.sha256' >"$TMP_BASE.matches" 2>/dev/null; then
    cat "$TMP_BASE.matches" >&2
    rm -f "$TMP_BASE.matches"
    fail "machine-specific home-directory references found in release candidate"
fi
rm -f "$TMP_BASE.matches"
pass "no machine-specific home-directory references"

# Runtime/private files must not be present in the release candidate.
if find "$CANDIDATE" -type f \( \
    -name '*.db' -o -name '*.db-wal' -o -name '*.db-shm' -o \
    -name '*.db.bak*' -o -name '*-export.json' -o -name '*.log' -o \
    -name '*.pid' -o -name '*.pyc' -o -name '.env' -o -name 'api.env' \
\) | grep -q .; then
    find "$CANDIDATE" -type f \( \
        -name '*.db' -o -name '*.db-wal' -o -name '*.db-shm' -o \
        -name '*.db.bak*' -o -name '*-export.json' -o -name '*.log' -o \
        -name '*.pid' -o -name '*.pyc' -o -name '.env' -o -name 'api.env' \
    \) >&2
    fail "runtime/private files found in release candidate"
fi
if find "$CANDIDATE" -type d -name '__pycache__' | grep -q .; then
    fail "__pycache__ found in release candidate"
fi
pass "no runtime/private files in release candidate"

for f in README.md LICENSE DISCLAIMER.md PRIVACY.md SECURITY.md CONTRIBUTING.md SUPPORT.md ROADMAP.md VERSION schema.sql; do
    [ -s "$CANDIDATE/$f" ] || fail "missing required public file: $f"
done
pass "required public files present"

case "$(cat "$CANDIDATE/VERSION")" in
    *[!0-9.]*|'') fail "invalid VERSION" ;;
esac
pass "VERSION format"

if grep -qE '^/home/|/Users/' "$CANDIDATE/prompts/wellness_agent.md"; then
    fail "agent prompt contains machine-specific absolute path"
fi
pass "generic agent prompt"

printf '\nALL PUBLIC RELEASE CHECKS PASSED\n'
