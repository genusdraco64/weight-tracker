#!/bin/sh
set -eu
umask 077

SRC_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DEST=${1:-"$HOME/.local/share/weight-tracker"}
BIN_DIR=${2:-"$HOME/.local/bin"}

case "$DEST" in
    /) printf 'Refusing to install into /\n' >&2; exit 2 ;;
esac

mkdir -p "$DEST" "$BIN_DIR"

if [ -f "$DEST/weight_tracker.db" ]; then
    BACKUP="$DEST/weight_tracker.db.bak-$(date +%Y%m%d-%H%M%S)"
    cp -p "$DEST/weight_tracker.db" "$BACKUP"
    chmod 600 "$BACKUP" 2>/dev/null || true
    printf 'Database backup: %s\n' "$BACKUP"
fi

# Copy code without touching runtime data.
(
    cd "$SRC_DIR"
    tar \
      --exclude='./weight_tracker.db' \
      --exclude='./*.db' --exclude='./*.db-wal' --exclude='./*.db-shm' \
      --exclude='./*.db.bak*' --exclude='./dist' --exclude='./__pycache__' \
      -cf - .
) | (
    cd "$DEST"
    tar -xf -
)

chmod 755 "$DEST/weight_tracker" "$DEST/tools/"*.py "$DEST/tests/"*.sh "$DEST/scripts/"*.sh
ln -sfn "$DEST/weight_tracker" "$BIN_DIR/weight_tracker"

if [ ! -f "$DEST/weight_tracker.db" ]; then
    "$DEST/weight_tracker" init >/dev/null
fi
chmod 600 "$DEST/weight_tracker.db" 2>/dev/null || true

"$DEST/weight_tracker" doctor
printf '\nInstalled: %s\nCommand:   %s/weight_tracker\n' "$DEST" "$BIN_DIR"
printf 'If that command is not found, add %s to PATH.\n' "$BIN_DIR"
