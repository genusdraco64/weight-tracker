PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    chat_id TEXT PRIMARY KEY,
    display_name TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_profiles (
    chat_id TEXT PRIMARY KEY REFERENCES users(chat_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_preferences (
    chat_id TEXT PRIMARY KEY REFERENCES users(chat_id) ON DELETE CASCADE,
    day_boundary_hour INTEGER NOT NULL DEFAULT 3 CHECK(day_boundary_hour BETWEEN 0 AND 23)
);

CREATE TABLE IF NOT EXISTS weights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL REFERENCES users(chat_id) ON DELETE CASCADE,
    logged_at TEXT NOT NULL,
    log_date TEXT NOT NULL,
    weight REAL NOT NULL CHECK(weight > 0),
    source_text TEXT,
    deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT,
    deleted_reason TEXT
);

CREATE TABLE IF NOT EXISTS food_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL REFERENCES users(chat_id) ON DELETE CASCADE,
    logged_at TEXT NOT NULL,
    log_date TEXT NOT NULL,
    meal TEXT NOT NULL,
    description TEXT NOT NULL,
    calories_min REAL,
    calories_max REAL,
    carbs_min REAL,
    carbs_max REAL,
    confidence TEXT,
    source TEXT,
    source_text TEXT,
    deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT,
    deleted_reason TEXT
);

CREATE TABLE IF NOT EXISTS exercise_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL REFERENCES users(chat_id) ON DELETE CASCADE,
    logged_at TEXT NOT NULL,
    log_date TEXT NOT NULL,
    description TEXT NOT NULL,
    exercise_type TEXT,
    duration_minutes REAL,
    distance REAL,
    calories_burned_min REAL,
    calories_burned_max REAL,
    confidence TEXT,
    source TEXT,
    source_text TEXT,
    deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT,
    deleted_reason TEXT
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL REFERENCES users(chat_id) ON DELETE CASCADE,
    logged_at TEXT NOT NULL,
    log_date TEXT NOT NULL,
    note TEXT NOT NULL,
    tags TEXT,
    deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT,
    deleted_reason TEXT
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL REFERENCES users(chat_id) ON DELETE CASCADE,
    logged_at TEXT NOT NULL,
    log_date TEXT NOT NULL,
    observation TEXT NOT NULL,
    observation_type TEXT,
    tags TEXT,
    importance INTEGER,
    deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT,
    deleted_reason TEXT
);

CREATE TABLE IF NOT EXISTS victories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL REFERENCES users(chat_id) ON DELETE CASCADE,
    logged_at TEXT NOT NULL,
    log_date TEXT NOT NULL,
    victory TEXT NOT NULL,
    victory_type TEXT,
    tags TEXT,
    deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT,
    deleted_reason TEXT
);

CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    action_time TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target_table TEXT,
    target_id INTEGER,
    summary TEXT
);

CREATE TABLE IF NOT EXISTS system_milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    milestone_key TEXT NOT NULL,
    milestone_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    achieved_at TEXT NOT NULL,
    log_date TEXT NOT NULL,
    value REAL,
    unit TEXT,
    source_table TEXT,
    source_id INTEGER,
    announced INTEGER NOT NULL DEFAULT 0,
    announced_at TEXT,
    UNIQUE(chat_id, milestone_key)
);

CREATE TABLE IF NOT EXISTS food_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    calories_min REAL,
    calories_max REAL,
    carbs_min REAL,
    carbs_max REAL,
    source TEXT,
    confidence TEXT
);

CREATE TABLE IF NOT EXISTS exercise_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    calories_per_hour_min REAL,
    calories_per_hour_max REAL,
    source TEXT,
    confidence TEXT
);

CREATE INDEX IF NOT EXISTS idx_weights_user_date ON weights(chat_id, log_date, deleted);
CREATE INDEX IF NOT EXISTS idx_food_user_date ON food_entries(chat_id, log_date, deleted);
CREATE INDEX IF NOT EXISTS idx_exercise_user_date ON exercise_entries(chat_id, log_date, deleted);
CREATE INDEX IF NOT EXISTS idx_notes_user_date ON notes(chat_id, log_date, deleted);
CREATE INDEX IF NOT EXISTS idx_observations_user_date ON observations(chat_id, log_date, deleted);
CREATE INDEX IF NOT EXISTS idx_victories_user_date ON victories(chat_id, log_date, deleted);
CREATE INDEX IF NOT EXISTS idx_actions_user_time ON action_log(chat_id, action_time);
CREATE INDEX IF NOT EXISTS idx_milestones_user_time ON system_milestones(chat_id, achieved_at);
