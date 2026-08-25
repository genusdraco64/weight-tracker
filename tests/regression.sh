#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT INT TERM
export WEIGHT_TRACKER_DB="$TMPDIR/regression.db"
WT="$ROOT/weight_tracker"

pass() { printf 'PASS: %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
json_ok() { python3 -m json.tool >/dev/null 2>&1 || fail "$1"; pass "$1"; }

python3 -m py_compile "$ROOT"/tools/*.py
pass "Python compile"

"$WT" init >/dev/null
"$WT" --json doctor | json_ok "database init and doctor"
"$WT" --json version | json_ok "version JSON"
"$WT" capabilities | json_ok "capabilities JSON"
"$WT" help --json | json_ok "help JSON"

ID=424242
"$WT" --chat-id "$ID" --name Regression --json weight 200 | json_ok "weight logging"
"$WT" --chat-id "$ID" --json food breakfast "eggs and toast" 250 300 20 30 high | json_ok "food logging"
"$WT" --chat-id "$ID" --json exercise "walked 2 miles" walking 40 2 180 220 high | json_ok "exercise logging"
"$WT" --chat-id "$ID" --json note "felt good" mood | json_ok "note logging"
"$WT" --chat-id "$ID" --json observation "sleep helps" sleep recovery 7 | json_ok "observation logging"
"$WT" --chat-id "$ID" --json victory "pants fit better" nsv clothing | json_ok "victory logging"

for cmd in \
    "weights all" "foods all" "exercises all" "notes all" \
    "observations all" "victories all" "milestones all" \
    "summary" "progress" "status" "trend 7" "report 14" \
    "next-milestones"
do
    # shellcheck disable=SC2086
    "$WT" --chat-id "$ID" --json $cmd | json_ok "$cmd JSON"
done

"$WT" --chat-id "$ID" status >/dev/null
pass "status text"
"$WT" --chat-id "$ID" report 14 >/dev/null
pass "report text"
"$WT" --chat-id "$ID" trend 7 >/dev/null
pass "trend text"

# A bare numeric ID must keep resolving to the existing canonical account.
COUNT=$("$WT" --chat-id "$ID" --json weights all | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')
[ "$COUNT" -eq 1 ] || fail "numeric identity compatibility"
pass "numeric identity compatibility"

# User-data commands must not silently fall into a shared test/default account.
if "$WT" --json weight 199 >"$TMPDIR/no-id.json" 2>/dev/null; then
    fail "missing chat-id rejection"
fi
python3 - "$TMPDIR/no-id.json" <<'PYNOID'
import json, sys
data=json.load(open(sys.argv[1]))
assert data.get("status") == "error"
assert "--chat-id" in data.get("message", "")
PYNOID
pass "missing chat-id rejection"

# Older telegram:<numeric> identities must remain reachable via bare numeric input.
LEGACY=515151
"$WT" --chat-id "telegram:$LEGACY" --json weight 180 | json_ok "legacy Telegram identity seed"
LEGACY_COUNT=$("$WT" --chat-id "$LEGACY" --json weights all | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')
[ "$LEGACY_COUNT" -eq 1 ] || fail "legacy Telegram identity compatibility"
pass "legacy Telegram identity compatibility"

EXPORT_FILE="$TMPDIR/user-export.json"
"$WT" --chat-id "$ID" --json export "$EXPORT_FILE" | json_ok "user export"
python3 -m json.tool "$EXPORT_FILE" >/dev/null
pass "export file JSON"

IMPORT_DB="$TMPDIR/import.db"
WEIGHT_TRACKER_DB="$IMPORT_DB" "$WT" init >/dev/null
WEIGHT_TRACKER_DB="$IMPORT_DB" "$WT" --chat-id 777 --json import "$EXPORT_FILE" merge | json_ok "user import merge"
IMPORTED=$(WEIGHT_TRACKER_DB="$IMPORT_DB" "$WT" --chat-id 777 --json weights all | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')
[ "$IMPORTED" -eq 1 ] || fail "imported weight history"
pass "imported weight history"

free_port() {
    python3 - <<'PYPORT'
import socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PYPORT
}

PORT=$(free_port)
WEIGHT_TRACKER_API_TOKEN=regression-token "$WT" serve 127.0.0.1 "$PORT" >"$TMPDIR/api.log" 2>&1 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true; rm -rf "$TMPDIR"' EXIT INT TERM
python3 - "$PORT" <<'PYAPI'
import json, sys, time, urllib.request
port=sys.argv[1]
for _ in range(30):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as r:
            json.load(r)
        break
    except Exception:
        time.sleep(.1)
else:
    raise SystemExit("API failed to start")
# Health must be minimal and must not expose local database metadata.
with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
    health=json.load(r)
assert health.get("status") == "ok"
assert "database" not in health and "user_count" not in health and "schema_file" not in health

req=urllib.request.Request(f"http://127.0.0.1:{port}/v1/capabilities", headers={"Authorization":"Bearer regression-token"})
with urllib.request.urlopen(req, timeout=2) as r:
    data=json.load(r)
assert "commands" in data

# POST requires JSON and an allowed command.
body=json.dumps({"command":"status","args":[]}).encode()
post=urllib.request.Request(
    f"http://127.0.0.1:{port}/v1/users/{424242}/command",
    data=body,
    headers={"Authorization":"Bearer regression-token", "Content-Type":"application/json"},
    method="POST",
)
with urllib.request.urlopen(post, timeout=2) as r:
    result=json.load(r)
assert isinstance(result, dict)
PYAPI
kill "$API_PID"
wait "$API_PID" 2>/dev/null || true
pass "REST API health and authentication"

WEIGHT_TRACKER_DB="$TMPDIR/shutdown.db" "$WT" init >/dev/null
SHUTDOWN_PORT=$(free_port)
python3 - "$WT" "$TMPDIR/shutdown.db" "$SHUTDOWN_PORT" <<'PYSHUTDOWN'
import os, signal, subprocess, sys, time
wt, db, port = sys.argv[1:]
env = os.environ.copy()
env["WEIGHT_TRACKER_DB"] = db
p = subprocess.Popen(
    [wt, "serve", "127.0.0.1", port],
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
startup = p.stdout.readline()
if "Weight Tracker API listening" not in startup:
    raise SystemExit("API did not announce startup")
time.sleep(0.1)
p.send_signal(signal.SIGINT)
out, _ = p.communicate(timeout=5)
if "Weight Tracker API stopped" not in out or "Traceback" in out or p.returncode != 0:
    raise SystemExit(f"unclean API shutdown: rc={p.returncode} output={out!r}")
PYSHUTDOWN
pass "REST API graceful Ctrl+C shutdown"

# Non-loopback listeners require a strong token before attempting to bind.
NETWORK_PORT=$(free_port)
if WEIGHT_TRACKER_API_TOKEN=short "$WT" serve 0.0.0.0 "$NETWORK_PORT" >"$TMPDIR/short-token.log" 2>&1; then
    fail "weak network API token rejection"
fi
grep -q 'at least 32 characters' "$TMPDIR/short-token.log" || fail "weak network API token message"
pass "weak network API token rejection"

# Fresh user-level installer test.
INSTALL_HOME="$TMPDIR/install-home"
mkdir -p "$INSTALL_HOME"
env -u WEIGHT_TRACKER_DB HOME="$INSTALL_HOME" "$ROOT/install.sh" >"$TMPDIR/install.log"
INSTALLED="$INSTALL_HOME/.local/bin/weight_tracker"
[ -x "$INSTALLED" ] || fail "installer launcher"
env -u WEIGHT_TRACKER_DB HOME="$INSTALL_HOME" "$INSTALLED" --json version | json_ok "installed version JSON"
env -u WEIGHT_TRACKER_DB HOME="$INSTALL_HOME" "$INSTALLED" --json doctor | json_ok "installed doctor JSON"
MODE=$(python3 - "$INSTALL_HOME/.local/share/weight-tracker/weight_tracker.db" <<'PYMODE'
import os, stat, sys
print(oct(stat.S_IMODE(os.stat(sys.argv[1]).st_mode))[2:])
PYMODE
)
[ "$MODE" = "600" ] || fail "installed database permissions"
pass "installed database permissions"

printf '\nALL REGRESSION TESTS PASSED\n' 
