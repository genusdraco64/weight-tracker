#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION=$(cat "$ROOT/VERSION")
OUT=${1:-"$ROOT/dist"}
NAME="weight_tracker-v${VERSION}-code-only"
mkdir -p "$OUT"

"$ROOT/tests/regression.sh"
"$ROOT/tests/public_release.sh"

ARCHIVE="$OUT/$NAME.tar.gz"
CHECKSUM="$ARCHIVE.sha256"
MANIFEST="$OUT/$NAME.manifest.txt"

rm -f "$ARCHIVE" "$CHECKSUM" "$MANIFEST"

tar -C "$(dirname "$ROOT")" \
  --exclude='*.db' --exclude='*.db-wal' --exclude='*.db-shm' \
  --exclude='*.db.bak*' --exclude='*-export.json' \
  --exclude='__pycache__' --exclude='*.pyc' --exclude='dist' \
  --exclude='*.log' --exclude='*.pid' --exclude='.env' --exclude='api.env' \
  -czf "$ARCHIVE" "$(basename "$ROOT")"

if command -v sha256sum >/dev/null 2>&1; then
    (cd "$OUT" && sha256sum "$(basename "$ARCHIVE")") > "$CHECKSUM"
elif command -v shasum >/dev/null 2>&1; then
    (cd "$OUT" && shasum -a 256 "$(basename "$ARCHIVE")") > "$CHECKSUM"
else
    echo "Need sha256sum or shasum to create release checksum" >&2
    exit 1
fi

tar -tzf "$ARCHIVE" | sort > "$MANIFEST"

if grep -E '(\.db($|\.)|\.db-wal$|\.db-shm$|\.pyc$|__pycache__|/dist/|\.log$|\.pid$)' "$MANIFEST" >/dev/null; then
    echo "Release archive contains forbidden runtime files" >&2
    exit 1
fi

printf '\nRelease artifacts:\n%s\n%s\n%s\n' "$ARCHIVE" "$CHECKSUM" "$MANIFEST"
