#!/usr/bin/env python3
import argparse
import hmac
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
TRACKER = BASE_DIR / "weight_tracker"
TOKEN = os.environ.get("WEIGHT_TRACKER_API_TOKEN", "")
MAX_BODY = 1024 * 1024
LOOPBACK_NAMES = {"127.0.0.1", "::1", "localhost"}
POST_COMMANDS = {
    "weight", "food", "exercise", "note", "observation", "victory",
    "undo", "replace-weight",
    "status", "dashboard", "progress", "summary", "trend", "report",
    "milestones", "next", "next-milestones",
    "weights", "foods", "exercises", "notes", "observations", "victories",
}


def run_tracker(args):
    proc = subprocess.run(
        [str(TRACKER), "--json", *args],
        text=True,
        capture_output=True,
        timeout=30,
    )
    text = proc.stdout.strip() or proc.stderr.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {"status": "error", "message": text or "tracker returned no output"}
    return proc.returncode, data


class Handler(BaseHTTPRequestHandler):
    server_version = "WeightTrackerAPI/1"

    def _json(self, status, payload):
        body = json.dumps(payload, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        if not TOKEN:
            return self.client_address[0] in {"127.0.0.1", "::1"}
        supplied = self.headers.get("Authorization", "")
        expected = f"Bearer {TOKEN}"
        return hmac.compare_digest(supplied, expected)

    def _auth_or_fail(self):
        if self._authorized():
            return True
        self._json(401, {"status": "error", "message": "unauthorized"})
        return False

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            code, data = run_tracker(["doctor"])
            payload = {
                "status": "ok" if code == 0 and data.get("status") == "ok" else "error",
                "integrity": data.get("integrity"),
            }
            self._json(200 if payload["status"] == "ok" else 503, payload)
            return
        if not self._auth_or_fail():
            return
        if path == "/v1/capabilities":
            code, data = run_tracker(["capabilities"])
        elif path == "/v1/version":
            code, data = run_tracker(["version"])
        else:
            parts = [p for p in path.split("/") if p]
            if len(parts) == 4 and parts[:2] == ["v1", "users"]:
                chat_id, command = parts[2], parts[3]
                allowed = {
                    "status", "progress", "next-milestones", "milestones",
                    "weights", "foods", "exercises", "notes",
                    "observations", "victories",
                }
                if command not in allowed:
                    self._json(404, {"status": "error", "message": "unknown endpoint"})
                    return
                tail = ["all"] if command in {
                    "weights", "foods", "exercises", "notes",
                    "observations", "victories", "milestones",
                } else []
                code, data = run_tracker(["--chat-id", chat_id, command, *tail])
            else:
                self._json(404, {"status": "error", "message": "not found"})
                return
        self._json(200 if code == 0 else 400, data)

    def do_POST(self):
        if not self._auth_or_fail():
            return
        path = urlparse(self.path).path
        parts = [p for p in path.split("/") if p]
        if len(parts) != 4 or parts[:2] != ["v1", "users"] or parts[3] != "command":
            self._json(404, {"status": "error", "message": "not found"})
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._json(415, {"status": "error", "message": "Content-Type must be application/json"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY:
            self._json(413, {"status": "error", "message": "invalid body size"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
            command = payload["command"]
            args = payload.get("args", [])
            if command not in POST_COMMANDS:
                raise PermissionError("command not allowed through API")
            if not isinstance(args, list) or not all(isinstance(x, (str, int, float)) for x in args):
                raise ValueError("invalid command arguments")
        except PermissionError as exc:
            self._json(403, {"status": "error", "message": str(exc)})
            return
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            self._json(400, {"status": "error", "message": str(exc)})
            return
        code, data = run_tracker(["--chat-id", parts[2], command, *[str(x) for x in args]])
        self._json(200 if code == 0 else 400, data)


def main():
    parser = argparse.ArgumentParser(description="Weight Tracker REST API")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    ns = parser.parse_args()
    if ns.bind not in LOOPBACK_NAMES:
        if not TOKEN:
            raise SystemExit("WEIGHT_TRACKER_API_TOKEN is required for non-loopback binding")
        if len(TOKEN) < 32:
            raise SystemExit("WEIGHT_TRACKER_API_TOKEN must be at least 32 characters for non-loopback binding")
    server = ThreadingHTTPServer((ns.bind, ns.port), Handler)
    print(f"Weight Tracker API listening on http://{ns.bind}:{ns.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWeight Tracker API stopped", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
