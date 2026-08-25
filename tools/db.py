#!/usr/bin/env python3
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("WEIGHT_TRACKER_DB", str(BASE_DIR / "weight_tracker.db"))).expanduser().resolve()
SCHEMA_PATH = BASE_DIR / "schema.sql"
REQUIRED_TABLES = {
    "users", "user_profiles", "user_preferences", "weights",
    "food_entries", "exercise_entries", "notes", "observations",
    "victories", "action_log", "system_milestones",
}

LOG_ACTION_TYPES = (
    "log_weight",
    "log_food",
    "log_exercise",
    "log_note",
    "log_observation",
    "log_victory",
)

SOFT_DELETE_TABLES = (
    "weights",
    "food_entries",
    "exercise_entries",
    "notes",
    "observations",
    "victories",
)



def initialize_database(force=False):
    """Create a new database schema without modifying an existing populated DB."""
    if DB_PATH.exists() and DB_PATH.stat().st_size > 0 and not force:
        return {"status": "exists", "database": str(DB_PATH)}
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(schema)
    try:
        DB_PATH.chmod(0o600)
    except OSError:
        pass
    return {"status": "initialized", "database": str(DB_PATH)}


def database_diagnostics():
    result = {
        "database": str(DB_PATH),
        "exists": DB_PATH.exists(),
        "schema_file": str(SCHEMA_PATH),
        "schema_exists": SCHEMA_PATH.exists(),
        "local_timestamp": local_timestamp(),
    }
    if not DB_PATH.exists():
        result.update({"status": "error", "message": "database does not exist; run init"})
        return result
    try:
        with connect() as conn:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
            user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] if "users" in tables else None
        missing = sorted(REQUIRED_TABLES - tables)
        result.update({
            "status": "ok" if integrity == "ok" and not missing else "error",
            "integrity": integrity,
            "missing_tables": missing,
            "user_count": user_count,
        })
    except sqlite3.Error as exc:
        result.update({"status": "error", "message": str(exc)})
    return result


def resolve_chat_id(chat_id):
    """Preserve legacy numeric/Telegram IDs without assuming a platform for new IDs."""
    if chat_id is None:
        return None
    raw = str(chat_id)
    if not raw.isdigit():
        return raw
    prefixed = f"telegram:{raw}"
    if not DB_PATH.exists():
        return raw
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT chat_id FROM users WHERE chat_id IN (?, ?)",
                (raw, prefixed),
            ).fetchall()
        existing = {row["chat_id"] for row in rows}
        if prefixed in existing:
            return prefixed
        if raw in existing:
            return raw
    except sqlite3.Error:
        pass
    return raw

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def local_timestamp():
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def log_date_for_now(day_boundary_hour=3):
    now = datetime.now()
    if now.hour < day_boundary_hour:
        now = now - timedelta(days=1)
    return now.date().isoformat()


def ensure_user(chat_id, display_name=None):
    chat_id = str(chat_id)

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO users (chat_id, display_name, first_seen_at, last_seen_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                display_name = COALESCE(excluded.display_name, users.display_name),
                last_seen_at = excluded.last_seen_at
            """,
            (chat_id, display_name, local_timestamp(), local_timestamp()),
        )

        conn.execute(
            "INSERT OR IGNORE INTO user_profiles (chat_id) VALUES (?)",
            (chat_id,),
        )

        conn.execute(
            "INSERT OR IGNORE INTO user_preferences (chat_id) VALUES (?)",
            (chat_id,),
        )


def get_day_boundary_hour(chat_id):
    chat_id = str(chat_id)

    with connect() as conn:
        row = conn.execute(
            """
            SELECT day_boundary_hour
            FROM user_preferences
            WHERE chat_id = ?
            """,
            (chat_id,),
        ).fetchone()

    return int(row["day_boundary_hour"]) if row else 3

def current_log_date(chat_id):
    boundary = get_day_boundary_hour(chat_id)
    return log_date_for_now(boundary)


def add_action(chat_id, action_type, table, target_id, summary):
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO action_log
                (chat_id, action_time, action_type, target_table, target_id, summary)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                local_timestamp(),
                action_type,
                table,
                target_id,
                summary,
            ),
        )

def add_system_milestone(
    chat_id,
    milestone_key,
    milestone_type,
    title,
    description=None,
    value=None,
    unit=None,
    source_table=None,
    source_id=None,
):
    chat_id = str(chat_id)
    log_date = current_log_date(chat_id)

    with connect() as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO system_milestones
                (
                    chat_id, milestone_key, milestone_type,
                    title, description, achieved_at, log_date,
                    value, unit, source_table, source_id
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                milestone_key,
                milestone_type,
                title,
                description,
                local_timestamp(),
                log_date,
                value,
                unit,
                source_table,
                source_id,
            ),
        )

        if cur.rowcount == 0:
            return {"status": "exists", "milestone_key": milestone_key}

        milestone_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO action_log
                (chat_id, action_time, action_type, target_table, target_id, summary)
            VALUES (?, ?, 'system_milestone', 'system_milestones', ?, ?)
            """,
            (
                chat_id,
                local_timestamp(),
                milestone_id,
                f"System milestone: {title}",
            ),
        )

    return {
        "status": "created",
        "id": milestone_id,
        "milestone_key": milestone_key,
        "title": title,
    }



def consume_unannounced_milestones(chat_id):
    chat_id = str(chat_id)

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id, log_date, milestone_key, milestone_type,
                title, description, value, unit
            FROM system_milestones
            WHERE chat_id = ?
              AND announced = 0
            ORDER BY achieved_at ASC, id ASC
            """,
            (chat_id,),
        ).fetchall()

        milestone_ids = [row["id"] for row in rows]
        if milestone_ids:
            placeholders = ",".join("?" for _ in milestone_ids)
            conn.execute(
                f"""
                UPDATE system_milestones
                SET announced = 1,
                    announced_at = ?
                WHERE chat_id = ?
                  AND id IN ({placeholders})
                """,
                [local_timestamp(), chat_id, *milestone_ids],
            )

    return [dict(row) for row in rows]


def attach_milestone_announcements(result, chat_id):
    milestones = consume_unannounced_milestones(chat_id)
    if milestones:
        result["milestones"] = milestones
    return result

def list_system_milestones(chat_id, limit=20):
    chat_id = str(chat_id)

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id, log_date, milestone_key, milestone_type,
                title, description, value, unit, announced
            FROM system_milestones
            WHERE chat_id = ?
            ORDER BY log_date DESC, achieved_at DESC
            LIMIT ?
            """,
            (chat_id, int(limit)),
        ).fetchall()

    return [dict(row) for row in rows]

def check_first_weight_milestone(chat_id, weight_id, weight):
    chat_id = str(chat_id)

    with connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM weights
            WHERE chat_id = ?
              AND deleted = 0
            """,
            (chat_id,),
        ).fetchone()

    if row["count"] != 1:
        return {"status": "not_first_weight"}

    return add_system_milestone(
        chat_id=chat_id,
        milestone_key="first_weight_logged",
        milestone_type="weight",
        title="First Weight Logged",
        description="You logged your first weight entry.",
        value=weight,
        unit="lb",
        source_table="weights",
        source_id=weight_id,
    )

def check_weight_progress_milestones(chat_id, weight_id, weight):
    chat_id = str(chat_id)
    weight = float(weight)

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, log_date, weight
            FROM weights
            WHERE chat_id = ?
              AND deleted = 0
            ORDER BY log_date ASC, logged_at ASC
            """,
            (chat_id,),
        ).fetchall()

    if len(rows) < 2:
        return []

    starting_weight = float(rows[0]["weight"])

    previous_weights = [
        float(row["weight"])
        for row in rows
        if row["id"] != weight_id
    ]

    if not previous_weights:
        return []


    created = []


    pounds_lost = starting_weight - weight

    # 5 / 10 / 15 / 20 lb etc.
    for milestone in range(5, 301, 5):
        if pounds_lost >= milestone:
            created.append(add_system_milestone(
                chat_id=chat_id,
                milestone_key=f"{milestone}_pounds_lost",
                milestone_type="weight_loss",
                title=f"{milestone} Pounds Lost",
                description=f"You have lost at least {milestone} lb from your starting weight.",
                value=milestone,
                unit="lb",
                source_table="weights",
                source_id=weight_id,
            ))

    percent_lost = (pounds_lost / starting_weight) * 100 if starting_weight > 0 else 0

    # 5% / 10% / 15% / 20% etc.
    for milestone in range(5, 101, 5):
        if percent_lost >= milestone:
            created.append(add_system_milestone(
                chat_id=chat_id,
                milestone_key=f"{milestone}_percent_lost",
                milestone_type="weight_loss_percent",
                title=f"{milestone}% Body Weight Lost",
                description=f"You have lost at least {milestone}% of your starting weight.",
                value=milestone,
                unit="percent",
                source_table="weights",
                source_id=weight_id,
            ))

    return created

def check_first_exercise_milestone(chat_id, exercise_id):
    chat_id = str(chat_id)

    with connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM exercise_entries
            WHERE chat_id = ?
              AND deleted = 0
            """,
            (chat_id,),
        ).fetchone()

    if row["count"] != 1:
        return {"status": "not_first_exercise"}

    return add_system_milestone(
        chat_id=chat_id,
        milestone_key="first_exercise_logged",
        milestone_type="exercise",
        title="First Exercise Logged",
        description="You logged your first exercise session.",
        source_table="exercise_entries",
        source_id=exercise_id,
    )


def check_exercise_progress_milestones(chat_id, exercise_id):
    chat_id = str(chat_id)

    with connect() as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS sessions,
                COALESCE(SUM(duration_minutes), 0) AS minutes,
                COALESCE(SUM(calories_burned_max), 0) AS calories
            FROM exercise_entries
            WHERE chat_id = ?
              AND deleted = 0
            """,
            (chat_id,),
        ).fetchone()

    sessions = int(totals["sessions"] or 0)
    minutes = float(totals["minutes"] or 0)
    calories = float(totals["calories"] or 0)

    created = []

    for milestone in range(5, 1001, 5):
        if sessions >= milestone:
            created.append(add_system_milestone(
                chat_id=chat_id,
                milestone_key=f"{milestone}_exercise_sessions",
                milestone_type="exercise_sessions",
                title=f"{milestone} Exercise Sessions",
                description=f"You have logged at least {milestone} exercise sessions.",
                value=milestone,
                unit="sessions",
                source_table="exercise_entries",
                source_id=exercise_id,
            ))

    for milestone in range(100, 100001, 100):
        if minutes >= milestone:
            created.append(add_system_milestone(
                chat_id=chat_id,
                milestone_key=f"{milestone}_exercise_minutes",
                milestone_type="exercise_minutes",
                title=f"{milestone} Exercise Minutes",
                description=f"You have logged at least {milestone} exercise minutes.",
                value=milestone,
                unit="minutes",
                source_table="exercise_entries",
                source_id=exercise_id,
            ))

    for milestone in range(1000, 1000001, 1000):
        if calories >= milestone:
            created.append(add_system_milestone(
                chat_id=chat_id,
                milestone_key=f"{milestone}_exercise_calories",
                milestone_type="exercise_calories",
                title=f"{milestone} Exercise Calories",
                description=f"You have logged at least {milestone} estimated exercise calories burned.",
                value=milestone,
                unit="calories",
                source_table="exercise_entries",
                source_id=exercise_id,
            ))

    return created



def check_first_food_milestone(chat_id, food_id):
    chat_id = str(chat_id)

    with connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM food_entries
            WHERE chat_id = ?
              AND deleted = 0
            """,
            (chat_id,),
        ).fetchone()

    if row["count"] != 1:
        return {"status": "not_first_food"}

    return add_system_milestone(
        chat_id=chat_id,
        milestone_key="first_food_logged",
        milestone_type="food",
        title="First Food Logged",
        description="You logged your first food entry.",
        source_table="food_entries",
        source_id=food_id,
    )


def check_food_progress_milestones(chat_id, food_id):
    chat_id = str(chat_id)

    with connect() as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS entries,
                COALESCE(SUM(calories_max), 0) AS calories
            FROM food_entries
            WHERE chat_id = ?
              AND deleted = 0
            """,
            (chat_id,),
        ).fetchone()

    entries = int(totals["entries"] or 0)
    calories = float(totals["calories"] or 0)

    created = []

    for milestone in (10, 50, 100):
        if entries >= milestone:
            created.append(add_system_milestone(
                chat_id=chat_id,
                milestone_key=f"{milestone}_food_entries",
                milestone_type="food_entries",
                title=f"{milestone} Food Entries",
                description=f"You have logged at least {milestone} food entries.",
                value=milestone,
                unit="entries",
                source_table="food_entries",
                source_id=food_id,
            ))

    for milestone in (10000, 25000, 50000):
        if calories >= milestone:
            created.append(add_system_milestone(
                chat_id=chat_id,
                milestone_key=f"{milestone}_food_calories",
                milestone_type="food_calories",
                title=f"{milestone} Food Calories Logged",
                description=f"You have logged at least {milestone} estimated food calories.",
                value=milestone,
                unit="calories",
                source_table="food_entries",
                source_id=food_id,
            ))

    return created


def check_reflection_milestones(chat_id, source_table, source_id):
    chat_id = str(chat_id)

    configs = {
        "notes": {
            "first_key": "first_note_logged",
            "first_title": "First Note Logged",
            "first_description": "You logged your first note.",
            "count_type": "note_entries",
            "count_title": "Notes Logged",
            "count_description": "notes",
            "unit": "notes",
            "milestones": (10, 25, 50, 100),
        },
        "observations": {
            "first_key": "first_observation_logged",
            "first_title": "First Observation Logged",
            "first_description": "You logged your first observation.",
            "count_type": "observation_entries",
            "count_title": "Observations Logged",
            "count_description": "observations",
            "unit": "observations",
            "milestones": (10, 25, 50, 100),
        },
        "victories": {
            "first_key": "first_victory_logged",
            "first_title": "First Victory Logged",
            "first_description": "You logged your first victory.",
            "count_type": "victory_entries",
            "count_title": "Victories Logged",
            "count_description": "victories",
            "unit": "victories",
            "milestones": (5, 10, 25, 50, 100),
        },
    }

    if source_table not in configs:
        return []

    config = configs[source_table]

    with connect() as conn:
        row = conn.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM {source_table}
            WHERE chat_id = ?
              AND deleted = 0
            """,
            (chat_id,),
        ).fetchone()

    count = int(row["count"] or 0)
    created = []

    if count == 1:
        created.append(add_system_milestone(
            chat_id=chat_id,
            milestone_key=config["first_key"],
            milestone_type=source_table,
            title=config["first_title"],
            description=config["first_description"],
            source_table=source_table,
            source_id=source_id,
        ))

    for milestone in config["milestones"]:
        if count >= milestone:
            created.append(add_system_milestone(
                chat_id=chat_id,
                milestone_key=f"{milestone}_{config['unit']}",
                milestone_type=config["count_type"],
                title=f"{milestone} {config['count_title']}",
                description=f"You have logged at least {milestone} {config['count_description']}.",
                value=milestone,
                unit=config["unit"],
                source_table=source_table,
                source_id=source_id,
            ))

    return created

def log_weight(chat_id, weight, display_name=None, source_text=None):
    chat_id = str(chat_id)
    ensure_user(chat_id, display_name)

    boundary = get_day_boundary_hour(chat_id)
    log_date = log_date_for_now(boundary)

    with connect() as conn:
        existing = conn.execute(
            """
            SELECT id, weight
            FROM weights
            WHERE chat_id = ?
              AND log_date = ?
              AND deleted = 0
            ORDER BY logged_at DESC
            LIMIT 1
            """,
            (chat_id, log_date),
        ).fetchone()

        if existing:
            return {
                "status": "duplicate",
                "message": (
                    f"Weight already exists for {log_date}: "
                    f"{existing['weight']} lb. Confirm before replacing."
                ),
                "existing_id": existing["id"],
                "existing_weight": existing["weight"],
                "new_weight": weight,
                "log_date": log_date,
            }

        cur = conn.execute(
            """
            INSERT INTO weights
                (chat_id, logged_at, log_date, weight, source_text)
            VALUES (?, ?, ?, ?, ?)
            """,
            (chat_id, local_timestamp(), log_date, float(weight), source_text),
        )

        weight_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO action_log
                (chat_id, action_time, action_type, target_table, target_id, summary)
            VALUES (?, ?, 'log_weight', 'weights', ?, ?)
            """,
            (
                chat_id,
                local_timestamp(),
                weight_id,
                f"Logged weight {weight} lb for {log_date}",
            ),
        )

    check_first_weight_milestone(
        chat_id=chat_id,
        weight_id=weight_id,
        weight=weight,
    )

    check_weight_progress_milestones(
        chat_id=chat_id,
        weight_id=weight_id,
        weight=weight,
    )

    return attach_milestone_announcements({
        "status": "logged",
        "weight": float(weight),
        "log_date": log_date,
    }, chat_id)

def replace_weight(weight_id, new_weight, reason="user approved replacement"):
    with connect() as conn:
        old = conn.execute(
            """
            SELECT id, chat_id, log_date, weight
            FROM weights
            WHERE id = ?
              AND deleted = 0
            """,
            (weight_id,),
        ).fetchone()

        if not old:
            return {"status": "not_found"}

        conn.execute(
            """
            UPDATE weights
            SET weight = ?, source_text = ?
            WHERE id = ?
            """,
            (float(new_weight), reason, weight_id),
        )

        conn.execute(
            """
            INSERT INTO action_log
                (chat_id, action_time, action_type, target_table, target_id, summary)
            VALUES (?, ?, 'replace_weight', 'weights', ?, ?)
            """,
            (
                old["chat_id"],
                local_timestamp(),
                weight_id,
                f"Replaced weight for {old['log_date']} from {old['weight']} to {new_weight}",
            ),
        )

    return {
        "status": "replaced",
        "id": weight_id,
        "old_weight": old["weight"],
        "new_weight": float(new_weight),
        "log_date": old["log_date"],
    }


def list_weights(chat_id, limit=10):
    chat_id = str(chat_id)

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, log_date, weight, logged_at
            FROM weights
            WHERE chat_id = ?
              AND deleted = 0
            ORDER BY log_date DESC, logged_at DESC
            LIMIT ?
            """,
            (chat_id, int(limit)),
        ).fetchall()

    return [dict(row) for row in rows]

def log_food(
    chat_id,
    meal,
    description,
    calories_min=None,
    calories_max=None,
    carbs_min=None,
    carbs_max=None,
    confidence="unknown",
    source=None,
    display_name=None,
    source_text=None,
):
    chat_id = str(chat_id)
    ensure_user(chat_id, display_name)

    boundary = get_day_boundary_hour(chat_id)
    log_date = log_date_for_now(boundary)

    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO food_entries
                (
                    chat_id, logged_at, log_date, meal, description,
                    calories_min, calories_max,
                    carbs_min, carbs_max,
                    confidence, source, source_text
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                local_timestamp(),
                log_date,
                meal,
                description,
                calories_min,
                calories_max,
                carbs_min,
                carbs_max,
                confidence,
                source,
                source_text,
            ),
        )

        food_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO action_log
                (chat_id, action_time, action_type, target_table, target_id, summary)
            VALUES (?, ?, 'log_food', 'food_entries', ?, ?)
            """,
            (
                chat_id,
                local_timestamp(),
                food_id,
                f"Logged food: {meal} - {description}",
            ),
        )

    check_first_food_milestone(
        chat_id=chat_id,
        food_id=food_id,
    )
    check_food_progress_milestones(
        chat_id=chat_id,
        food_id=food_id,
    )

    return attach_milestone_announcements({
        "status": "logged",
        "id": food_id,
        "log_date": log_date,
        "meal": meal,
        "description": description,
        "calories_min": calories_min,
        "calories_max": calories_max,
        "carbs_min": carbs_min,
        "carbs_max": carbs_max,
        "confidence": confidence,
    }, chat_id)


def list_food(chat_id, limit=20):
    chat_id = str(chat_id)

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id, log_date, meal, description,
                calories_min, calories_max,
                carbs_min, carbs_max,
                confidence, logged_at
            FROM food_entries
            WHERE chat_id = ?
              AND deleted = 0
            ORDER BY log_date DESC, logged_at DESC
            LIMIT ?
            """,
            (chat_id, int(limit)),
        ).fetchall()

    return [dict(row) for row in rows]

def log_exercise(
    chat_id,
    description,
    exercise_type=None,
    duration_minutes=None,
    distance=None,
    calories_burned_min=None,
    calories_burned_max=None,
    confidence="unknown",
    source=None,
    display_name=None,
    source_text=None,
):
    chat_id = str(chat_id)
    ensure_user(chat_id, display_name)

    boundary = get_day_boundary_hour(chat_id)
    log_date = log_date_for_now(boundary)

    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO exercise_entries
                (
                    chat_id, logged_at, log_date, description, exercise_type,
                    duration_minutes, distance,
                    calories_burned_min, calories_burned_max,
                    confidence, source, source_text
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                local_timestamp(),
                log_date,
                description,
                exercise_type,
                duration_minutes,
                distance,
                calories_burned_min,
                calories_burned_max,
                confidence,
                source,
                source_text,
            ),
        )

        exercise_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO action_log
                (chat_id, action_time, action_type, target_table, target_id, summary)
            VALUES (?, ?, 'log_exercise', 'exercise_entries', ?, ?)
            """,
            (
                chat_id,
                local_timestamp(),
                exercise_id,
                f"Logged exercise: {description}",
            ),
        )

    check_first_exercise_milestone(
        chat_id=chat_id,
        exercise_id=exercise_id,
    )
    check_exercise_progress_milestones(
        chat_id=chat_id,
        exercise_id=exercise_id,
    )

    return attach_milestone_announcements({
        "status": "logged",
        "id": exercise_id,
        "log_date": log_date,
        "description": description,
        "calories_burned_min": calories_burned_min,
        "calories_burned_max": calories_burned_max,
        "confidence": confidence,
    }, chat_id)

def list_exercise(chat_id, limit=20):
    chat_id = str(chat_id)

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id, log_date, description, exercise_type,
                duration_minutes, distance,
                calories_burned_min, calories_burned_max,
                confidence, logged_at
            FROM exercise_entries
            WHERE chat_id = ?
              AND deleted = 0
            ORDER BY log_date DESC, logged_at DESC
            LIMIT ?
            """,
            (chat_id, int(limit)),
        ).fetchall()

    return [dict(row) for row in rows]

def daily_summary(chat_id, log_date=None):
    chat_id = str(chat_id)

    if log_date is None:
        boundary = get_day_boundary_hour(chat_id)
        log_date = log_date_for_now(boundary)

    with connect() as conn:
        weight = conn.execute(
            """
            SELECT weight
            FROM weights
            WHERE chat_id = ?
              AND log_date = ?
              AND deleted = 0
            ORDER BY logged_at DESC
            LIMIT 1
            """,
            (chat_id, log_date),
        ).fetchone()

        food = conn.execute(
            """
            SELECT
                SUM(calories_min) AS calories_min,
                SUM(calories_max) AS calories_max,
                SUM(carbs_min) AS carbs_min,
                SUM(carbs_max) AS carbs_max,
                COUNT(*) AS food_count
            FROM food_entries
            WHERE chat_id = ?
              AND log_date = ?
              AND deleted = 0
            """,
            (chat_id, log_date),
        ).fetchone()

        exercise = conn.execute(
            """
            SELECT
                SUM(calories_burned_min) AS burned_min,
                SUM(calories_burned_max) AS burned_max,
                COUNT(*) AS exercise_count
            FROM exercise_entries
            WHERE chat_id = ?
              AND log_date = ?
              AND deleted = 0
            """,
            (chat_id, log_date),
        ).fetchone()

    return {
        "log_date": log_date,
        "weight": weight["weight"] if weight else None,
        "food_count": food["food_count"] or 0,
        "calories_min": food["calories_min"] or 0,
        "calories_max": food["calories_max"] or 0,
        "carbs_min": food["carbs_min"] or 0,
        "carbs_max": food["carbs_max"] or 0,
        "exercise_count": exercise["exercise_count"] or 0,
        "burned_min": exercise["burned_min"] or 0,
        "burned_max": exercise["burned_max"] or 0,
    }

def trend_report(chat_id, days=7):
    chat_id = str(chat_id)
    days = int(days)

    current = period_summary(chat_id, days)

    with connect() as conn:
        prev_start = f"-{days * 2} days"
        prev_end = f"-{days} days"

        previous_food = conn.execute(
            """
            SELECT
                COUNT(DISTINCT log_date) AS food_days,
                COUNT(*) AS food_count,
                SUM(calories_min) AS calories_min,
                SUM(calories_max) AS calories_max,
                SUM(carbs_min) AS carbs_min,
                SUM(carbs_max) AS carbs_max
            FROM food_entries
            WHERE chat_id = ?
              AND deleted = 0
              AND log_date >= date('now', 'localtime', ?)
              AND log_date < date('now', 'localtime', ?)
            """,
            (chat_id, prev_start, prev_end),
        ).fetchone()

        current_food_days = conn.execute(
            """
            SELECT COUNT(DISTINCT log_date) AS food_days
            FROM food_entries
            WHERE chat_id = ?
              AND deleted = 0
              AND log_date >= date('now', 'localtime', ?)
            """,
            (chat_id, f"-{days} days"),
        ).fetchone()

        previous_exercise = conn.execute(
            """
            SELECT
                COUNT(DISTINCT log_date) AS exercise_days,
                COUNT(*) AS exercise_count,
                SUM(duration_minutes) AS duration_minutes,
                SUM(calories_burned_min) AS burned_min,
                SUM(calories_burned_max) AS burned_max
            FROM exercise_entries
            WHERE chat_id = ?
              AND deleted = 0
              AND log_date >= date('now', 'localtime', ?)
              AND log_date < date('now', 'localtime', ?)
            """,
            (chat_id, prev_start, prev_end),
        ).fetchone()

        current_exercise = conn.execute(
            """
            SELECT
                COUNT(DISTINCT log_date) AS exercise_days,
                SUM(duration_minutes) AS duration_minutes
            FROM exercise_entries
            WHERE chat_id = ?
              AND deleted = 0
              AND log_date >= date('now', 'localtime', ?)
            """,
            (chat_id, f"-{days} days"),
        ).fetchone()

    def avg(total, count):
        if not total or not count:
            return None
        return round(total / count, 1)

    current_food_day_count = current_food_days["food_days"] or 0
    previous_food_day_count = previous_food["food_days"] or 0

    current_avg_calories_min = avg(current["calories_min"], current_food_day_count)
    current_avg_calories_max = avg(current["calories_max"], current_food_day_count)
    previous_avg_calories_min = avg(previous_food["calories_min"], previous_food_day_count)
    previous_avg_calories_max = avg(previous_food["calories_max"], previous_food_day_count)

    current_avg_carbs_min = avg(current["carbs_min"], current_food_day_count)
    current_avg_carbs_max = avg(current["carbs_max"], current_food_day_count)
    previous_avg_carbs_min = avg(previous_food["carbs_min"], previous_food_day_count)
    previous_avg_carbs_max = avg(previous_food["carbs_max"], previous_food_day_count)

    flags = []

    if current["weight_entries"] < 2:
        flags.append("not_enough_weight_data")

    if current_food_day_count == 0:
        flags.append("no_food_logged")
    elif current_food_day_count < max(2, days // 2):
        flags.append("limited_food_data")

    if current["exercise_count"] == 0:
        flags.append("no_exercise_logged")

    if current["weight_change"] is not None:
        if current["weight_change"] < 0:
            flags.append("weight_down")
        elif current["weight_change"] > 0:
            flags.append("weight_up")
        else:
            flags.append("weight_stable")

    if previous_food_day_count > 0 and current_food_day_count > 0:
        current_mid = (current_avg_calories_min + current_avg_calories_max) / 2
        previous_mid = (previous_avg_calories_min + previous_avg_calories_max) / 2

        diff = round(current_mid - previous_mid, 1)

        if diff <= -100:
            flags.append("calories_down_vs_previous")
        elif diff >= 100:
            flags.append("calories_up_vs_previous")
        else:
            flags.append("calories_similar_vs_previous")
    else:
        diff = None
        flags.append("not_enough_previous_food_data")

    confidence = "high"
    confidence_reasons = []

    if current["weight_entries"] < 2:
        confidence = "low"
        confidence_reasons.append("fewer than 2 weigh-ins")

    if current_food_day_count < max(2, days // 2):
        confidence = "low"
        confidence_reasons.append(f"food logged on only {current_food_day_count} of {days} days")

    if not confidence_reasons:
        confidence_reasons.append("enough logged data for a useful short-term comparison")

    return {
        "days": days,
        "confidence": confidence,
        "confidence_reasons": confidence_reasons,
        "flags": flags,

        "current": current,

        "previous": {
            "food_days": previous_food_day_count,
            "food_count": previous_food["food_count"] or 0,
            "calories_min": previous_food["calories_min"] or 0,
            "calories_max": previous_food["calories_max"] or 0,
            "carbs_min": previous_food["carbs_min"] or 0,
            "carbs_max": previous_food["carbs_max"] or 0,
            "exercise_days": previous_exercise["exercise_days"] or 0,
            "exercise_count": previous_exercise["exercise_count"] or 0,
            "duration_minutes": previous_exercise["duration_minutes"] or 0,
            "burned_min": previous_exercise["burned_min"] or 0,
            "burned_max": previous_exercise["burned_max"] or 0,
        },

        "averages": {
            "current_food_days": current_food_day_count,
            "previous_food_days": previous_food_day_count,
            "current_avg_calories_min": current_avg_calories_min,
            "current_avg_calories_max": current_avg_calories_max,
            "previous_avg_calories_min": previous_avg_calories_min,
            "previous_avg_calories_max": previous_avg_calories_max,
            "current_avg_carbs_min": current_avg_carbs_min,
            "current_avg_carbs_max": current_avg_carbs_max,
            "previous_avg_carbs_min": previous_avg_carbs_min,
            "previous_avg_carbs_max": previous_avg_carbs_max,
            "calorie_midpoint_difference": diff,
            "current_exercise_days": current_exercise["exercise_days"] or 0,
            "current_exercise_minutes": current_exercise["duration_minutes"] or 0,
        },
    }

def period_summary(chat_id, days=7):
    chat_id = str(chat_id)
    days = int(days)

    with connect() as conn:
        weights = conn.execute(
            """
            SELECT log_date, weight
            FROM weights
            WHERE chat_id = ?
              AND deleted = 0
              AND log_date >= date('now', 'localtime', ?)
            ORDER BY log_date ASC, logged_at ASC
            """,
            (chat_id, f"-{days} days"),
        ).fetchall()

        food = conn.execute(
            """
            SELECT
                COUNT(*) AS food_count,
                SUM(calories_min) AS calories_min,
                SUM(calories_max) AS calories_max,
                SUM(carbs_min) AS carbs_min,
                SUM(carbs_max) AS carbs_max
            FROM food_entries
            WHERE chat_id = ?
              AND deleted = 0
              AND log_date >= date('now', 'localtime', ?)
            """,
            (chat_id, f"-{days} days"),
        ).fetchone()

        exercise = conn.execute(
            """
            SELECT
                COUNT(*) AS exercise_count,
                SUM(duration_minutes) AS duration_minutes,
                SUM(calories_burned_min) AS burned_min,
                SUM(calories_burned_max) AS burned_max
            FROM exercise_entries
            WHERE chat_id = ?
              AND deleted = 0
              AND log_date >= date('now', 'localtime', ?)
            """,
            (chat_id, f"-{days} days"),
        ).fetchone()

        notes = conn.execute(
            """
            SELECT COUNT(*) AS note_count
            FROM notes
            WHERE chat_id = ?
              AND deleted = 0
              AND log_date >= date('now', 'localtime', ?)
            """,
            (chat_id, f"-{days} days"),
        ).fetchone()

        milestones = conn.execute(
            """
            SELECT title, milestone_key, log_date, value, unit
            FROM system_milestones
            WHERE chat_id = ?
              AND log_date >= date('now', 'localtime', ?)
            ORDER BY achieved_at DESC, id DESC
            LIMIT 10
            """,
            (chat_id, f"-{days} days"),
        ).fetchall()

        victories = conn.execute(
            """
            SELECT log_date, victory, victory_type
            FROM victories
            WHERE chat_id = ?
              AND deleted = 0
              AND log_date >= date('now', 'localtime', ?)
            ORDER BY log_date ASC, logged_at ASC
            """,
            (chat_id, f"-{days} days"),
        ).fetchall()

        observations = conn.execute(
            """
            SELECT log_date, observation, observation_type, importance
            FROM observations
            WHERE chat_id = ?
              AND deleted = 0
              AND log_date >= date('now', 'localtime', ?)
            ORDER BY importance DESC, log_date ASC, logged_at ASC
            LIMIT 10
            """,
            (chat_id, f"-{days} days"),
        ).fetchall()

    start_weight = weights[0]["weight"] if weights else None
    current_weight = weights[-1]["weight"] if weights else None
    weight_change = (
        round(current_weight - start_weight, 1)
        if start_weight is not None and current_weight is not None
        else None
    )

    return {
        "days": days,
        "weight_entries": len(weights),
        "start_weight": start_weight,
        "current_weight": current_weight,
        "weight_change": weight_change,

        "food_count": food["food_count"] or 0,
        "calories_min": food["calories_min"] or 0,
        "calories_max": food["calories_max"] or 0,
        "carbs_min": food["carbs_min"] or 0,
        "carbs_max": food["carbs_max"] or 0,

        "exercise_count": exercise["exercise_count"] or 0,
        "exercise_minutes": exercise["duration_minutes"] or 0,
        "burned_min": exercise["burned_min"] or 0,
        "burned_max": exercise["burned_max"] or 0,

        "note_count": notes["note_count"] or 0,
        "victories": [dict(row) for row in victories],
        "observations": [dict(row) for row in observations],
        "milestones": [dict(row) for row in milestones],
        "averages": {
            "calories_min_per_day": round((food["calories_min"] or 0) / days, 1) if days else 0,
            "calories_max_per_day": round((food["calories_max"] or 0) / days, 1) if days else 0,
            "carbs_min_per_day": round((food["carbs_min"] or 0) / days, 1) if days else 0,
            "carbs_max_per_day": round((food["carbs_max"] or 0) / days, 1) if days else 0,
            "exercise_minutes_per_day": round((exercise["duration_minutes"] or 0) / days, 1) if days else 0,
        },
    }



def progress_overview(chat_id, recent_milestone_limit=5):
    chat_id = str(chat_id)
    recent_milestone_limit = int(recent_milestone_limit)

    with connect() as conn:
        weights = conn.execute(
            """
            SELECT log_date, weight, logged_at
            FROM weights
            WHERE chat_id = ?
              AND deleted = 0
            ORDER BY log_date ASC, logged_at ASC, id ASC
            """,
            (chat_id,),
        ).fetchall()

        counts = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM weights WHERE chat_id = ? AND deleted = 0) AS weight_entries,
                (SELECT COUNT(*) FROM food_entries WHERE chat_id = ? AND deleted = 0) AS food_entries,
                (SELECT COUNT(*) FROM exercise_entries WHERE chat_id = ? AND deleted = 0) AS exercise_sessions,
                (SELECT COUNT(*) FROM notes WHERE chat_id = ? AND deleted = 0) AS notes,
                (SELECT COUNT(*) FROM observations WHERE chat_id = ? AND deleted = 0) AS observations,
                (SELECT COUNT(*) FROM victories WHERE chat_id = ? AND deleted = 0) AS victories
            """,
            (chat_id, chat_id, chat_id, chat_id, chat_id, chat_id),
        ).fetchone()

        food = conn.execute(
            """
            SELECT
                SUM(calories_min) AS calories_min,
                SUM(calories_max) AS calories_max,
                SUM(carbs_min) AS carbs_min,
                SUM(carbs_max) AS carbs_max
            FROM food_entries
            WHERE chat_id = ?
              AND deleted = 0
            """,
            (chat_id,),
        ).fetchone()

        exercise = conn.execute(
            """
            SELECT
                SUM(duration_minutes) AS duration_minutes,
                SUM(calories_burned_min) AS burned_min,
                SUM(calories_burned_max) AS burned_max
            FROM exercise_entries
            WHERE chat_id = ?
              AND deleted = 0
            """,
            (chat_id,),
        ).fetchone()

        recent_milestones = conn.execute(
            """
            SELECT
                id, log_date, milestone_key, milestone_type,
                title, description, value, unit, announced
            FROM system_milestones
            WHERE chat_id = ?
            ORDER BY achieved_at DESC, id DESC
            LIMIT ?
            """,
            (chat_id, recent_milestone_limit),
        ).fetchall()

        today_activity = conn.execute(
            """
            SELECT action_type, action_time, target_table, target_id, summary
            FROM action_log
            WHERE chat_id = ?
              AND date(action_time) = date('now', 'localtime')
            ORDER BY action_time DESC, id DESC
            LIMIT 10
            """,
            (chat_id,),
        ).fetchall()

        today_counts = conn.execute(
            """
            SELECT action_type, COUNT(*) AS count
            FROM action_log
            WHERE chat_id = ?
              AND date(action_time) = date('now', 'localtime')
            GROUP BY action_type
            ORDER BY action_type
            """,
            (chat_id,),
        ).fetchall()

        latest = conn.execute(
            """
            SELECT action_type, action_time, target_table, target_id, summary
            FROM action_log
            WHERE chat_id = ?
            ORDER BY action_time DESC, id DESC
            LIMIT 5
            """,
            (chat_id,),
        ).fetchall()

    start_weight = weights[0]["weight"] if weights else None
    current_weight = weights[-1]["weight"] if weights else None

    pounds_lost = None
    percent_lost = None
    if start_weight is not None and current_weight is not None:
        pounds_lost = round(start_weight - current_weight, 1)
        if start_weight:
            percent_lost = round((pounds_lost / start_weight) * 100, 1)

    return {
        "weight": {
            "start": start_weight,
            "current": current_weight,
            "pounds_lost": pounds_lost,
            "percent_lost": percent_lost,
        },
        "logging": {
            "weight_entries": counts["weight_entries"] or 0,
            "food_entries": counts["food_entries"] or 0,
            "exercise_sessions": counts["exercise_sessions"] or 0,
            "notes": counts["notes"] or 0,
            "observations": counts["observations"] or 0,
            "victories": counts["victories"] or 0,
        },
        "food": {
            "calories_min": food["calories_min"] or 0,
            "calories_max": food["calories_max"] or 0,
            "carbs_min": food["carbs_min"] or 0,
            "carbs_max": food["carbs_max"] or 0,
        },
        "exercise": {
            "duration_minutes": exercise["duration_minutes"] or 0,
            "burned_min": exercise["burned_min"] or 0,
            "burned_max": exercise["burned_max"] or 0,
        },
        "recent_milestones": [dict(row) for row in recent_milestones],
        "today_activity": [dict(row) for row in today_activity],
        "today_counts": [dict(row) for row in today_counts],
        "latest_activity": [dict(row) for row in latest],
    }


def _next_threshold(value, thresholds, step_after_last=None):
    value = float(value or 0)
    for threshold in thresholds:
        if value < threshold:
            return threshold
    if step_after_last:
        base = thresholds[-1] if thresholds else 0
        steps = int((value - base) // step_after_last) + 1
        return base + (steps * step_after_last)
    return None


def next_milestones_overview(chat_id):
    chat_id = str(chat_id)

    with connect() as conn:
        weights = conn.execute(
            """
            SELECT weight, log_date, logged_at
            FROM weights
            WHERE chat_id = ?
              AND deleted = 0
            ORDER BY log_date ASC, logged_at ASC, id ASC
            """,
            (chat_id,),
        ).fetchall()

        totals = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM food_entries WHERE chat_id = ? AND deleted = 0) AS food_entries,
                (SELECT COALESCE(SUM(calories_max), 0) FROM food_entries WHERE chat_id = ? AND deleted = 0) AS food_calories,
                (SELECT COUNT(*) FROM exercise_entries WHERE chat_id = ? AND deleted = 0) AS exercise_sessions,
                (SELECT COALESCE(SUM(duration_minutes), 0) FROM exercise_entries WHERE chat_id = ? AND deleted = 0) AS exercise_minutes,
                (SELECT COALESCE(SUM(calories_burned_max), 0) FROM exercise_entries WHERE chat_id = ? AND deleted = 0) AS exercise_calories,
                (SELECT COUNT(*) FROM notes WHERE chat_id = ? AND deleted = 0) AS notes,
                (SELECT COUNT(*) FROM observations WHERE chat_id = ? AND deleted = 0) AS observations,
                (SELECT COUNT(*) FROM victories WHERE chat_id = ? AND deleted = 0) AS victories
            """,
            (chat_id, chat_id, chat_id, chat_id, chat_id, chat_id, chat_id, chat_id),
        ).fetchone()

    start_weight = weights[0]["weight"] if weights else None
    current_weight = weights[-1]["weight"] if weights else None
    pounds_lost = None
    percent_lost = None
    if start_weight is not None and current_weight is not None:
        pounds_lost = round(start_weight - current_weight, 1)
        percent_lost = round((pounds_lost / start_weight) * 100, 1) if start_weight else None

    next_pounds = _next_threshold(max(pounds_lost or 0, 0), list(range(5, 305, 5)), 5)
    next_percent = _next_threshold(max(percent_lost or 0, 0), list(range(5, 105, 5)), 5)

    return {
        "weight": {
            "start": start_weight,
            "current": current_weight,
            "pounds_lost": pounds_lost,
            "percent_lost": percent_lost,
            "next_pounds_lost": next_pounds,
            "pounds_to_next": round(next_pounds - (pounds_lost or 0), 1) if next_pounds is not None else None,
            "next_percent_lost": next_percent,
            "percent_to_next": round(next_percent - (percent_lost or 0), 1) if next_percent is not None and percent_lost is not None else None,
        },
        "food": {
            "entries": totals["food_entries"] or 0,
            "next_entries": _next_threshold(totals["food_entries"], (10, 50, 100), 50),
            "calories": totals["food_calories"] or 0,
            "next_calories": _next_threshold(totals["food_calories"], (10000, 25000, 50000), 25000),
        },
        "exercise": {
            "sessions": totals["exercise_sessions"] or 0,
            "next_sessions": _next_threshold(totals["exercise_sessions"], list(range(5, 1005, 5)), 5),
            "minutes": totals["exercise_minutes"] or 0,
            "next_minutes": _next_threshold(totals["exercise_minutes"], list(range(100, 100100, 100)), 100),
            "calories": totals["exercise_calories"] or 0,
            "next_calories": _next_threshold(totals["exercise_calories"], list(range(1000, 1001000, 1000)), 1000),
        },
        "reflection": {
            "notes": totals["notes"] or 0,
            "next_notes": _next_threshold(totals["notes"], (10, 25, 50, 100), 25),
            "observations": totals["observations"] or 0,
            "next_observations": _next_threshold(totals["observations"], (10, 25, 50, 100), 25),
            "victories": totals["victories"] or 0,
            "next_victories": _next_threshold(totals["victories"], (5, 10, 25, 50, 100), 25),
        },
    }

def undo_last(chat_id):
    chat_id = str(chat_id)

    allowed_tables = SOFT_DELETE_TABLES

    with connect() as conn:
        placeholders = ",".join("?" for _ in LOG_ACTION_TYPES)

        actions = conn.execute(
            f"""
            SELECT target_table, target_id, summary
            FROM action_log
            WHERE chat_id = ?
              AND action_type IN ({placeholders})
            ORDER BY action_time DESC, id DESC
            LIMIT 25
            """,
            (chat_id, *LOG_ACTION_TYPES),
        ).fetchall()

        for action in actions:
            table = action["target_table"]
            target_id = action["target_id"]

            if table not in allowed_tables:
                continue

            row = conn.execute(
                f"SELECT deleted FROM {table} WHERE id = ?",
                (target_id,),
            ).fetchone()

            if not row or row["deleted"]:
                continue

            conn.execute(
                f"""
                UPDATE {table}
                SET deleted = 1,
                    deleted_at = ?,
                    deleted_reason = 'undo last entry'
                WHERE id = ?
                  AND deleted = 0
                """,
                (local_timestamp(), target_id),
            )

            conn.execute(
                """
                INSERT INTO action_log
                    (chat_id, action_time, action_type, target_table, target_id, summary)
                VALUES (?, ?, 'undo', ?, ?, ?)
                """,
                (
                    chat_id,
                    local_timestamp(),
                    table,
                    target_id,
                    f"Undid: {action['summary']}",
                ),
            )

            return {
                "status": "undone",
                "table": table,
                "id": target_id,
                "summary": action["summary"],
            }

    return {"status": "not_found"}

def log_note(chat_id, note, tags=None, display_name=None):
    chat_id = str(chat_id)
    ensure_user(chat_id, display_name)

    boundary = get_day_boundary_hour(chat_id)
    log_date = log_date_for_now(boundary)

    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO notes
                (chat_id, logged_at, log_date, note, tags)
            VALUES (?, ?, ?, ?, ?)
            """,
            (chat_id, local_timestamp(), log_date, note, tags),
        )

        note_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO action_log
                (chat_id, action_time, action_type, target_table, target_id, summary)
            VALUES (?, ?, 'log_note', 'notes', ?, ?)
            """,
            (chat_id, local_timestamp(), note_id, f"Logged note: {note[:80]}"),
        )

    check_reflection_milestones(chat_id, "notes", note_id)

    return attach_milestone_announcements({
        "status": "logged",
        "id": note_id,
        "log_date": log_date,
        "note": note,
        "tags": tags,
    }, chat_id)


def list_notes(chat_id, limit=20):
    chat_id = str(chat_id)

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, log_date, note, tags, logged_at
            FROM notes
            WHERE chat_id = ?
              AND deleted = 0
            ORDER BY log_date DESC, logged_at DESC
            LIMIT ?
            """,
            (chat_id, int(limit)),
        ).fetchall()

    return [dict(row) for row in rows]

def log_observation(
    chat_id,
    observation,
    observation_type="general",
    tags=None,
    importance=5,
    display_name=None,
):
    chat_id = str(chat_id)
    ensure_user(chat_id, display_name)

    boundary = get_day_boundary_hour(chat_id)
    log_date = log_date_for_now(boundary)

    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO observations
                (chat_id, logged_at, log_date, observation, observation_type, tags, importance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (chat_id, local_timestamp(), log_date, observation, observation_type, tags, int(importance)),
        )

        observation_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO action_log
                (chat_id, action_time, action_type, target_table, target_id, summary)
            VALUES (?, ?, 'log_observation', 'observations', ?, ?)
            """,
            (chat_id, local_timestamp(), observation_id, f"Logged observation: {observation[:80]}"),
        )

    check_reflection_milestones(chat_id, "observations", observation_id)

    return attach_milestone_announcements({
        "status": "logged",
        "id": observation_id,
        "log_date": log_date,
        "observation": observation,
        "observation_type": observation_type,
        "tags": tags,
        "importance": int(importance),
    }, chat_id)


def list_observations(chat_id, limit=20):
    chat_id = str(chat_id)

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, log_date, observation, observation_type, tags, importance, logged_at
            FROM observations
            WHERE chat_id = ?
              AND deleted = 0
            ORDER BY log_date DESC, logged_at DESC
            LIMIT ?
            """,
            (chat_id, int(limit)),
        ).fetchall()

    return [dict(row) for row in rows]

def log_victory(
    chat_id,
    victory,
    victory_type="general",
    tags=None,
    display_name=None,
):
    chat_id = str(chat_id)
    ensure_user(chat_id, display_name)

    boundary = get_day_boundary_hour(chat_id)
    log_date = log_date_for_now(boundary)

    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO victories
                (chat_id, logged_at, log_date, victory, victory_type, tags)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chat_id, local_timestamp(), log_date, victory, victory_type, tags),
        )

        victory_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO action_log
                (chat_id, action_time, action_type, target_table, target_id, summary)
            VALUES (?, ?, 'log_victory', 'victories', ?, ?)
            """,
            (chat_id, local_timestamp(), victory_id, f"Logged victory: {victory[:80]}"),
        )

    check_reflection_milestones(chat_id, "victories", victory_id)

    return attach_milestone_announcements({
        "status": "logged",
        "id": victory_id,
        "log_date": log_date,
        "victory": victory,
        "victory_type": victory_type,
        "tags": tags,
    }, chat_id)


def list_victories(chat_id, limit=20):
    chat_id = str(chat_id)

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, log_date, victory, victory_type, tags, logged_at
            FROM victories
            WHERE chat_id = ?
              AND deleted = 0
            ORDER BY log_date DESC, logged_at DESC
            LIMIT ?
            """,
            (chat_id, int(limit)),
        ).fetchall()

    return [dict(row) for row in rows]
