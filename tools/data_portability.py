#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path
from datetime import datetime

from db import DB_PATH, connect, resolve_chat_id

EXPORT_TABLES = [
    "users", "user_profiles", "user_preferences", "weights", "food_entries",
    "exercise_entries", "notes", "observations", "victories", "action_log",
    "system_milestones",
]
DELETE_ORDER = [
    "action_log", "system_milestones", "victories", "observations", "notes",
    "exercise_entries", "food_entries", "weights", "user_preferences",
    "user_profiles", "users",
]


def _rows(conn, table, chat_id):
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    if "chat_id" not in cols:
        return []
    return [dict(r) for r in conn.execute(f"SELECT * FROM {table} WHERE chat_id = ?", (chat_id,))]


def export_user(chat_id, output_path):
    chat_id = resolve_chat_id(chat_id)
    payload = {
        "format": "weight-tracker-export",
        "format_version": 1,
        "exported_at": datetime.now().replace(microsecond=0).isoformat(sep=" "),
        "chat_id": chat_id,
        "tables": {},
    }
    with connect() as conn:
        for table in EXPORT_TABLES:
            payload["tables"][table] = _rows(conn, table, chat_id)
    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return {"status": "exported", "chat_id": chat_id, "path": str(path),
            "rows": sum(len(v) for v in payload["tables"].values())}


def _insert_row(conn, table, row, mode):
    columns = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    filtered = {k: v for k, v in row.items() if k in columns}
    if not filtered:
        return 0
    names = list(filtered)
    placeholders = ",".join("?" for _ in names)
    verb = "INSERT OR REPLACE" if mode == "replace" else "INSERT OR IGNORE"
    sql = f"{verb} INTO {table} ({','.join(names)}) VALUES ({placeholders})"
    cur = conn.execute(sql, [filtered[n] for n in names])
    return max(cur.rowcount, 0)


def import_user(input_path, target_chat_id=None, mode="merge"):
    if mode not in {"merge", "replace"}:
        raise ValueError("mode must be merge or replace")
    path = Path(input_path).expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != "weight-tracker-export" or payload.get("format_version") != 1:
        raise ValueError("unsupported export format")
    source_id = str(payload.get("chat_id"))
    target_id = resolve_chat_id(target_chat_id or source_id)
    imported = 0
    with connect() as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        if mode == "replace":
            for table in DELETE_ORDER:
                conn.execute(f"DELETE FROM {table} WHERE chat_id = ?", (target_id,))
        for table in EXPORT_TABLES:
            for row in payload.get("tables", {}).get(table, []):
                row = dict(row)
                row["chat_id"] = target_id
                imported += _insert_row(conn, table, row, mode)
        conn.execute("PRAGMA foreign_keys = ON")
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise sqlite3.IntegrityError(integrity)
    return {"status": "imported", "source_chat_id": source_id,
            "chat_id": target_id, "mode": mode, "rows": imported,
            "path": str(path)}
