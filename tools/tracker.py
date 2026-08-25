#!/usr/bin/env python3
import json
import sys
from pathlib import Path
import os

from data_portability import export_user, import_user

from db import (
    daily_summary,
    list_exercise,
    list_system_milestones,
    list_food,
    list_notes,
    list_observations,
    list_victories,
    list_weights,
    log_exercise,
    log_food,
    log_note,
    log_observation,
    log_victory,
    log_weight,
    replace_weight,
    undo_last,
    period_summary,
    progress_overview,
    trend_report,
    next_milestones_overview,
    database_diagnostics,
    initialize_database,
    resolve_chat_id,
)

DEFAULT_CHAT_ID = os.environ.get("WEIGHT_TRACKER_DEFAULT_CHAT_ID")
DEFAULT_DISPLAY_NAME = os.environ.get("WEIGHT_TRACKER_DEFAULT_NAME")
BASE_DIR = Path(__file__).resolve().parent.parent
VERSION = (BASE_DIR / "VERSION").read_text(encoding="utf-8").strip()
OUTPUT_JSON = False


COMMAND_HELP = {
    "weight": {
        "category": "Logging",
        "purpose": "Log a body weight entry for the current user.",
        "usage": "weight_tracker [--chat-id ID] weight 236.4",
        "example": "weight_tracker --chat-id 123 weight 199.4",
        "shows": ["logged weight", "new weight milestones if earned"],
        "agent_notes": ["Use when the user gives a weigh-in or says what they weigh.", "After logging, run status unless the user only wanted a quick log."],
        "related": ["weights", "progress", "status", "trend"],
    },
    "weights": {
        "category": "Lists",
        "purpose": "List recent weight entries.",
        "usage": "weight_tracker [--chat-id ID] [--json] weights [LIMIT|all]",
        "example": "weight_tracker --chat-id 123 weights",
        "shows": ["stored weight rows"],
        "agent_notes": ["Use when the user asks to see raw weigh-in history."],
        "related": ["weight", "progress", "trend"],
    },
    "food": {
        "category": "Logging",
        "purpose": "Log food or drink with estimated calories and carbs.",
        "usage": 'weight_tracker [--chat-id ID] food MEAL "description" CAL_MIN CAL_MAX CARB_MIN CARB_MAX CONFIDENCE',
        "example": 'weight_tracker --chat-id 123 food dinner "burger and fries" 900 1200 70 100 medium',
        "shows": ["logged food", "new food milestones if earned"],
        "agent_notes": ["Use when the user describes meals, snacks, drinks, calories, or carbs.", "Log every distinct food item that can be reasonably estimated.", "After logging, run status."],
        "related": ["foods", "status", "report", "trend"],
    },
    "foods": {
        "category": "Lists",
        "purpose": "List recent food entries.",
        "usage": "weight_tracker [--chat-id ID] [--json] foods [LIMIT|all]",
        "example": "weight_tracker --chat-id 123 foods",
        "shows": ["stored food rows"],
        "agent_notes": ["Use when the user asks what foods have been logged."],
        "related": ["food", "report", "status"],
    },
    "exercise": {
        "category": "Logging",
        "purpose": "Log exercise with duration, optional distance, and estimated calories burned.",
        "usage": 'weight_tracker [--chat-id ID] exercise "description" TYPE MINUTES DISTANCE CAL_MIN CAL_MAX CONFIDENCE',
        "example": 'weight_tracker --chat-id 123 exercise "walked 2 miles" walking 40 2 180 220 high',
        "shows": ["logged exercise", "new exercise milestones if earned"],
        "agent_notes": ["Use when the user describes physical activity, workouts, chores, walking, shopping, mowing, or other exercise-like activity.", "After logging, run status."],
        "related": ["exercises", "status", "trend", "next-milestones"],
    },
    "exercises": {
        "category": "Lists",
        "purpose": "List recent exercise entries.",
        "usage": "weight_tracker [--chat-id ID] [--json] exercises [LIMIT|all]",
        "example": "weight_tracker --chat-id 123 exercises",
        "shows": ["stored exercise rows"],
        "agent_notes": ["Use when the user asks what exercise has been logged."],
        "related": ["exercise", "trend", "report"],
    },
    "note": {
        "category": "Logging",
        "purpose": "Log a free-form note related to weight management.",
        "usage": 'weight_tracker [--chat-id ID] note "note text" [tags]',
        "example": 'weight_tracker --chat-id 123 note "felt hungry in the evening" cravings',
        "shows": ["logged note", "new note milestones if earned"],
        "agent_notes": ["Use for context, barriers, cravings, sleep, mood, hunger, schedule, or other weight-loss-relevant details."],
        "related": ["notes", "status", "report"],
    },
    "notes": {
        "category": "Lists",
        "purpose": "List recent notes.",
        "usage": "weight_tracker [--chat-id ID] [--json] notes [LIMIT|all]",
        "example": "weight_tracker --chat-id 123 notes",
        "shows": ["stored note rows"],
        "agent_notes": ["Use when the user asks to review notes."],
        "related": ["note", "report"],
    },
    "observation": {
        "category": "Logging",
        "purpose": "Log a pattern, insight, or observation.",
        "usage": 'weight_tracker [--chat-id ID] observation "text" [type] [tags] [importance]',
        "example": 'weight_tracker --chat-id 123 observation "sleep has been poor" sleep recovery 7',
        "shows": ["logged observation", "new observation milestones if earned"],
        "agent_notes": ["Use when the user notices a trend, pattern, trigger, or lesson."],
        "related": ["observations", "report", "status"],
    },
    "observations": {
        "category": "Lists",
        "purpose": "List recent observations.",
        "usage": "weight_tracker [--chat-id ID] [--json] observations [LIMIT|all]",
        "example": "weight_tracker --chat-id 123 observations",
        "shows": ["stored observation rows"],
        "agent_notes": ["Use when the user asks to review observations or patterns."],
        "related": ["observation", "report"],
    },
    "victory": {
        "category": "Logging",
        "purpose": "Log a scale or non-scale victory.",
        "usage": 'weight_tracker [--chat-id ID] victory "text" [type] [tags]',
        "example": 'weight_tracker --chat-id 123 victory "pants fit looser" clothing nsv',
        "shows": ["logged victory", "new victory milestones if earned"],
        "agent_notes": ["Use when the user reports success, progress, consistency, better choices, clothes fitting differently, energy improvements, or other wins."],
        "related": ["victories", "status", "next-milestones"],
    },
    "victories": {
        "category": "Lists",
        "purpose": "List recent victories.",
        "usage": "weight_tracker [--chat-id ID] [--json] victories [LIMIT|all]",
        "example": "weight_tracker --chat-id 123 victories",
        "shows": ["stored victory rows"],
        "agent_notes": ["Use when the user asks what wins have been recorded."],
        "related": ["victory", "report"],
    },
    "status": {
        "category": "Reports",
        "purpose": "Show the main all-in-one dashboard for current progress.",
        "usage": "weight_tracker [--chat-id ID] status",
        "example": "weight_tracker --chat-id 123 status",
        "shows": ["recent milestones", "today's summary", "today's activity", "progress", "next milestones", "coach notes", "latest activity"],
        "agent_notes": ["Preferred command after logging new data.", "Use when the user asks how they are doing, asks for a dashboard, or after journal reconciliation."],
        "related": ["progress", "trend", "report", "next-milestones"],
    },
    "dashboard": {
        "category": "Reports",
        "purpose": "Alias for status.",
        "usage": "weight_tracker [--chat-id ID] dashboard",
        "example": "weight_tracker --chat-id 123 dashboard",
        "shows": ["same output as status"],
        "agent_notes": ["Use status as the preferred spelling."],
        "related": ["status"],
    },
    "progress": {
        "category": "Reports",
        "purpose": "Show a concise progress dashboard.",
        "usage": "weight_tracker [--chat-id ID] progress",
        "example": "weight_tracker --chat-id 123 progress",
        "shows": ["weight", "logging counts", "food totals", "exercise totals", "today's activity", "latest activity"],
        "agent_notes": ["Use when the user specifically asks for progress but not full status."],
        "related": ["status", "trend", "report"],
    },
    "trend": {
        "category": "Reports",
        "purpose": "Compare the current period to the previous period.",
        "usage": "weight_tracker [--chat-id ID] trend [DAYS]",
        "example": "weight_tracker --chat-id 123 trend 7",
        "shows": ["confidence", "weight movement", "food averages", "exercise comparison", "flags", "coach notes"],
        "agent_notes": ["Use when the user asks whether things are improving, asks for trends, or asks to compare this week to last week."],
        "related": ["report", "status", "progress"],
    },
    "report": {
        "category": "Reports",
        "purpose": "Summarize a date range by number of days.",
        "usage": "weight_tracker [--chat-id ID] report DAYS",
        "example": "weight_tracker --chat-id 123 report 14",
        "shows": ["weight", "food totals and averages", "exercise totals", "reflections", "milestones", "highlights", "coach notes"],
        "agent_notes": ["Use when the user asks how they did this week, over two weeks, this month, or over a specific recent range."],
        "related": ["trend", "status", "progress"],
    },
    "milestones": {
        "category": "Milestones",
        "purpose": "List earned milestones.",
        "usage": "weight_tracker [--chat-id ID] [--json] milestones [LIMIT|all]",
        "example": "weight_tracker --chat-id 123 milestones 20",
        "shows": ["earned milestone rows"],
        "agent_notes": ["Use when the user asks what milestones they have earned."],
        "related": ["next-milestones", "status"],
    },
    "next": {
        "category": "Milestones",
        "purpose": "Alias for next-milestones.",
        "usage": "weight_tracker [--chat-id ID] next",
        "example": "weight_tracker --chat-id 123 next",
        "shows": ["closest upcoming milestones"],
        "agent_notes": ["Use next-milestones as the preferred spelling."],
        "related": ["next-milestones"],
    },
    "next-milestones": {
        "category": "Milestones",
        "purpose": "Show progress toward upcoming milestones.",
        "usage": "weight_tracker [--chat-id ID] next-milestones",
        "example": "weight_tracker --chat-id 123 next-milestones",
        "shows": ["weight", "exercise", "food", "reflection milestone progress"],
        "agent_notes": ["Use when the user asks what they are closest to earning next or what to focus on."],
        "related": ["milestones", "status"],
    },
    "summary": {
        "category": "Reports",
        "purpose": "Show the existing daily summary output.",
        "usage": "weight_tracker [--chat-id ID] summary",
        "example": "weight_tracker --chat-id 123 summary",
        "shows": ["today's stored summary data"],
        "agent_notes": ["Prefer status for normal user-facing summaries."],
        "related": ["status", "progress"],
    },
    "undo": {
        "category": "Utilities",
        "purpose": "Undo the user's most recent logged action when supported.",
        "usage": "weight_tracker [--chat-id ID] undo",
        "example": "weight_tracker --chat-id 123 undo",
        "shows": ["undo result"],
        "agent_notes": ["Use only when the user asks to undo or remove the last entry."],
        "related": ["status"],
    },
    "replace-weight": {
        "category": "Utilities",
        "purpose": "Replace an existing weight entry by row ID.",
        "usage": "weight_tracker [--chat-id ID] replace-weight ID NEW_WEIGHT",
        "example": "weight_tracker --chat-id 123 replace-weight 12 199.5",
        "shows": ["replacement result"],
        "agent_notes": ["Use when correcting a specific weight entry after identifying its row ID."],
        "related": ["weights", "weight"],
    },
    "help": {
        "category": "Utilities",
        "purpose": "Show command help or machine-readable command metadata.",
        "usage": "weight_tracker help [COMMAND] | weight_tracker help --json",
        "example": "weight_tracker help status",
        "shows": ["command index", "command-specific help", "JSON command index"],
        "agent_notes": ["Use this command to discover tracker capabilities instead of relying on memory."],
        "related": ["commands"],
    },
    "commands": {
        "category": "Utilities",
        "purpose": "Alias for help.",
        "usage": "weight_tracker commands [COMMAND] | weight_tracker commands --json",
        "example": "weight_tracker commands --json",
        "shows": ["same output as help"],
        "agent_notes": ["Use help as the preferred spelling."],
        "related": ["help"],
    },
    "capabilities": {
        "category": "Utilities",
        "purpose": "Show versioned machine-readable tracker capabilities.",
        "usage": "weight_tracker capabilities",
        "example": "weight_tracker capabilities",
        "shows": ["version", "commands", "features", "preferred agent commands"],
        "agent_notes": ["Use at agent startup, after tracker updates, or after an unknown-command error to discover installed features."],
        "related": ["help", "commands", "status"],
    },
    "version": {
        "category": "Utilities",
        "purpose": "Show the installed application and interface versions.",
        "usage": "weight_tracker version",
        "example": "weight_tracker version",
        "shows": ["application version", "command schema version", "data schema version"],
        "agent_notes": ["Use when confirming an installation or reporting a bug."],
        "related": ["capabilities", "doctor"],
    },
    "doctor": {
        "category": "Utilities",
        "purpose": "Check database availability, schema completeness, and integrity.",
        "usage": "weight_tracker doctor",
        "example": "weight_tracker doctor",
        "shows": ["database path", "integrity result", "missing tables", "local timestamp"],
        "agent_notes": ["Run after an update or when commands fail unexpectedly."],
        "related": ["version", "init"],
    },
    "export": {
        "category": "Utilities",
        "purpose": "Export one user's complete tracker data to JSON.",
        "usage": "weight_tracker --chat-id ID export FILE",
        "example": "weight_tracker --chat-id 123 export backup.json",
        "shows": ["export path", "row count"],
        "agent_notes": ["Use for user-controlled backups and data portability."],
        "related": ["import", "doctor"],
    },
    "import": {
        "category": "Utilities",
        "purpose": "Import a Weight Tracker JSON export.",
        "usage": "weight_tracker --chat-id ID import FILE [merge|replace]",
        "example": "weight_tracker --chat-id 123 import backup.json merge",
        "shows": ["import mode", "row count"],
        "agent_notes": ["Use replace only after explicit approval and a database backup."],
        "related": ["export", "doctor"],
    },
    "serve": {
        "category": "Utilities",
        "purpose": "Run the local REST API server.",
        "usage": "weight_tracker serve [BIND] [PORT]",
        "example": "WEIGHT_TRACKER_API_TOKEN=secret weight_tracker serve 127.0.0.1 8765",
        "shows": ["REST API listener"],
        "agent_notes": ["Keep loopback-only unless authentication and network policy are configured."],
        "related": ["capabilities", "doctor"],
    },
    "init": {
        "category": "Utilities",
        "purpose": "Initialize a new empty tracker database.",
        "usage": "weight_tracker init",
        "example": "WEIGHT_TRACKER_DB=/tmp/tracker.db weight_tracker init",
        "shows": ["created database path"],
        "agent_notes": ["Never run against a live database unless it does not exist."],
        "related": ["doctor"],
    },
}

COMMAND_ORDER = [
    "weight", "weights", "food", "foods", "exercise", "exercises",
    "note", "notes", "observation", "observations", "victory", "victories",
    "status", "dashboard", "progress", "trend", "report", "summary",
    "milestones", "next", "next-milestones",
    "undo", "replace-weight", "help", "commands", "capabilities",
    "version", "doctor", "export", "import", "serve", "init",
]

CATEGORY_ORDER = ["Logging", "Lists", "Reports", "Milestones", "Utilities"]


def command_json_payload():
    commands = []
    for name in COMMAND_ORDER:
        item = COMMAND_HELP[name]
        commands.append({
            "name": name,
            "category": item["category"],
            "purpose": item["purpose"],
            "usage": item["usage"],
            "example": item["example"],
            "shows": item.get("shows", []),
            "agent_notes": item.get("agent_notes", []),
            "related": item.get("related", []),
        })
    return {
        "tool": "weight_tracker",
        "version": VERSION,
        "command_schema_version": "1",
        "data_schema_version": "1",
        "version_note": "public beta release candidate",
        "preferred_after_logging": "status",
        "commands": commands,
    }


def usage():
    print_command_index()


def print_command_index():
    print("WEIGHT TRACKER COMMANDS")
    print("=======================")
    print()
    print("Global options")
    print("--------------")
    print("--chat-id ID     Select user/account")
    print("--name NAME      Display name for new user records")

    for category in CATEGORY_ORDER:
        names = [name for name in COMMAND_ORDER if COMMAND_HELP[name]["category"] == category]
        if not names:
            continue
        print()
        print(category.upper())
        print("-" * len(category))
        for name in names:
            usage_text = COMMAND_HELP[name]["usage"].replace("weight_tracker [--chat-id ID] ", "")
            usage_text = usage_text.replace("weight_tracker ", "")
            print(f"{name:<16} {COMMAND_HELP[name]['purpose']}")
            print(f"{'':<16} usage: {usage_text}")

    print()
    print("Agent discovery")
    print("---------------")
    print("weight_tracker help COMMAND")
    print("weight_tracker help --json")
    print("weight_tracker capabilities")


def print_command_help(command):
    aliases = {"dashboard": "dashboard", "next": "next", "commands": "commands"}
    command = aliases.get(command, command)
    item = COMMAND_HELP.get(command)
    if item is None:
        print({"status": "error", "message": f"unknown command: {command}"})
        print()
        print_command_index()
        return 1

    title = command.upper()
    print(title)
    print("=" * len(title))

    print_section("Purpose")
    print(item["purpose"])

    print_section("Usage")
    print(item["usage"])

    print_section("Example")
    print(item["example"])

    print_section("Shows")
    for row in item.get("shows", []):
        print(f"- {row}")

    print_section("AI Agent Notes")
    for row in item.get("agent_notes", []):
        print(f"- {row}")

    print_section("Related")
    related = item.get("related", [])
    if related:
        print(", ".join(related))
    else:
        print("None")
    return 0


def print_help_json():
    print(json.dumps(command_json_payload(), indent=2, sort_keys=True))


def capabilities_payload():
    command_names = list(COMMAND_ORDER)
    return {
        "tool": "weight_tracker",
        "version": VERSION,
        "release_stage": "public_beta",
        "command_schema_version": "1",
        "data_schema_version": "1",
        "default_user_command_after_logging": "status",
        "discovery_commands": [
            "weight_tracker capabilities",
            "weight_tracker help --json",
            "weight_tracker help COMMAND",
        ],
        "commands": command_names,
        "command_categories": {
            category.lower(): [
                name for name in COMMAND_ORDER
                if COMMAND_HELP[name]["category"] == category
            ]
            for category in CATEGORY_ORDER
        },
        "features": [
            "multi_user",
            "weight_logging",
            "food_logging",
            "exercise_logging",
            "notes",
            "observations",
            "victories",
            "undo",
            "daily_summary",
            "period_report",
            "trend_report",
            "progress_dashboard",
            "status_dashboard",
            "milestones",
            "milestone_announcements",
            "next_milestones",
            "local_time_timestamps",
            "self_documenting_cli",
            "machine_readable_help",
            "versioned_capabilities",
            "rest_api", "authenticated_network_api", "json_export_import",
            "public_release_checks", "generic_agent_prompt",
            "json_output",
            "full_history_lists",
            "portable_launcher",
            "database_diagnostics",
            "new_database_initialization",
        ],
        "preferred_commands": {
            "after_logging": "status",
            "current_dashboard": "status",
            "range_summary": "report DAYS",
            "trend_comparison": "trend DAYS",
            "earned_milestones": "milestones [LIMIT]",
            "upcoming_milestones": "next-milestones",
            "command_discovery": "help --json",
        },
        "interfaces": {
            "human": "text CLI",
            "machine": "JSON CLI via --json",
            "complete_history": "LIST_COMMAND all --json",
        },
        "database_packaging": {
            "release_tarballs_include_database": False,
            "excluded_patterns": ["*.db", "*.db-wal", "*.db-shm"],
        },
    }


def print_capabilities_json():
    print(json.dumps(capabilities_payload(), indent=2, sort_keys=True))

def extract_identity(argv):
    global OUTPUT_JSON
    chat_id = DEFAULT_CHAT_ID
    display_name = DEFAULT_DISPLAY_NAME
    cleaned = []

    i = 0
    while i < len(argv):
        if argv[i] == "--chat-id" and i + 1 < len(argv):
            chat_id = argv[i + 1]
            i += 2
        elif argv[i] == "--name" and i + 1 < len(argv):
            display_name = argv[i + 1]
            i += 2
        elif argv[i] == "--json" and not (i > 0 and argv[i - 1] in ("help", "commands")):
            OUTPUT_JSON = True
            i += 1
        else:
            cleaned.append(argv[i])
            i += 1

    return resolve_chat_id(chat_id), display_name, cleaned


def emit(data):
    if OUTPUT_JSON:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(data)


def parse_list_limit(args, default):
    if len(args) == 1:
        return default
    if len(args) != 2:
        raise ValueError("expected optional LIMIT or all")
    if args[1].lower() in ("all", "--all"):
        return 2147483647
    return as_int(args[1], "limit")


def as_float(value, field):
    try:
        return float(value)
    except ValueError:
        print({"status": "error", "message": f"{field} must be a number"})
        raise SystemExit(2)


def as_int(value, field):
    try:
        return int(value)
    except ValueError:
        print({"status": "error", "message": f"{field} must be an integer"})
        raise SystemExit(2)


def print_rows(rows):
    for row in rows:
        print(row)




def fmt_number(value, decimals=0):
    if value is None:
        return "--"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if decimals == 0:
        return f"{value:,.0f}"
    return f"{value:,.{decimals}f}"


def fmt_weight(value):
    if value is None:
        return "--"
    return f"{float(value):.1f} lb"


def fmt_range(low, high, suffix=""):
    low = 0 if low is None else low
    high = 0 if high is None else high
    low = float(low)
    high = float(high)
    if low == high:
        text = fmt_number(low)
    else:
        text = f"{fmt_number(low)}-{fmt_number(high)}"
    return f"{text}{suffix}"


def print_section(title):
    print()
    print(title)
    print("-" * len(title))


def print_progress_dashboard(data):
    print("PROGRESS DASHBOARD")
    print("==================")

    weight = data.get("weight", {})
    logging = data.get("logging", {})
    food = data.get("food", {})
    exercise = data.get("exercise", {})
    milestones = data.get("recent_milestones", [])
    today = data.get("today_activity", [])
    latest = data.get("latest_activity", [])

    start = weight.get("start")
    current = weight.get("current")
    pounds_lost = weight.get("pounds_lost")
    percent_lost = weight.get("percent_lost")

    print_section("Weight")
    print(f"Start   : {fmt_weight(start)}")
    print(f"Current : {fmt_weight(current)}")
    if pounds_lost is None:
        print("Change  : --")
    elif pounds_lost >= 0:
        print(f"Lost    : {fmt_number(pounds_lost, 1)} lb ({fmt_number(percent_lost, 1)}%)")
    else:
        print(f"Change  : +{fmt_number(abs(pounds_lost), 1)} lb ({fmt_number(percent_lost, 1)}%)")

    print_section("Logging")
    print(f"Weights      : {fmt_number(logging.get('weight_entries'))}")
    print(f"Food entries : {fmt_number(logging.get('food_entries'))}")
    print(f"Exercise     : {fmt_number(logging.get('exercise_sessions'))}")
    print(f"Notes        : {fmt_number(logging.get('notes'))}")
    print(f"Observations : {fmt_number(logging.get('observations'))}")
    print(f"Victories    : {fmt_number(logging.get('victories'))}")

    print_section("Food Totals")
    print(f"Calories : {fmt_range(food.get('calories_min'), food.get('calories_max'))}")
    print(f"Carbs    : {fmt_range(food.get('carbs_min'), food.get('carbs_max'), ' g')}")

    print_section("Exercise Totals")
    print(f"Minutes  : {fmt_number(exercise.get('duration_minutes'))}")
    print(f"Calories : {fmt_range(exercise.get('burned_min'), exercise.get('burned_max'))}")

    print_section("Recent Milestones")
    if milestones:
        for item in milestones:
            print(f"- {item.get('title', item.get('milestone_key', 'Milestone'))}")
    else:
        print("None yet")

    print_section("Today's Activity")
    if today:
        for item in today:
            summary = item.get("summary") or item.get("action_type") or "activity"
            action_time = item.get("action_time")
            if action_time:
                print(f"- {action_time}: {summary}")
            else:
                print(f"- {summary}")
    else:
        print("No activity logged today")

    print_section("Latest Activity")
    if latest:
        first_time = latest[0].get("action_time")
        if first_time:
            print(f"Last activity: {first_time}")
        for item in latest:
            summary = item.get("summary") or item.get("action_type") or "activity"
            action_time = item.get("action_time")
            if action_time:
                print(f"- {action_time}: {summary}")
            else:
                print(f"- {summary}")
    else:
        print("No activity yet")



def today_count_map(data):
    counts = {}
    for row in data.get("today_counts", []):
        counts[row.get("action_type")] = row.get("count", 0)
    return counts


def print_today_summary(data):
    counts = today_count_map(data)
    weight = counts.get("log_weight", 0)
    food = counts.get("log_food", 0)
    exercise = counts.get("log_exercise", 0)
    notes = counts.get("log_note", 0)
    observations = counts.get("log_observation", 0)
    victories = counts.get("log_victory", 0)

    if not any((weight, food, exercise, notes, observations, victories)):
        print("No tracked activity logged today")
        return

    if weight:
        print(f"Weight logs : {fmt_number(weight)}")
    if food:
        print(f"Food logs   : {fmt_number(food)}")
    if exercise:
        print(f"Exercise    : {fmt_number(exercise)}")
    if notes:
        print(f"Notes       : {fmt_number(notes)}")
    if observations:
        print(f"Observations: {fmt_number(observations)}")
    if victories:
        print(f"Victories   : {fmt_number(victories)}")


def coach_lines(data):
    lines = []
    weight = data.get("weight", {})
    logging = data.get("logging", {})
    exercise = data.get("exercise", {})
    today_counts = today_count_map(data)

    if today_counts.get("log_weight", 0):
        lines.append("Weight was logged today.")
    else:
        lines.append("No weight logged today.")

    if today_counts.get("log_food", 0):
        lines.append("Food logging is active today.")
    else:
        lines.append("No food logged today yet.")

    if today_counts.get("log_exercise", 0):
        lines.append("Exercise was logged today.")
    elif logging.get("exercise_sessions", 0):
        lines.append("Exercise history exists, but none is logged today yet.")

    pounds_lost = weight.get("pounds_lost")
    if pounds_lost is not None:
        if pounds_lost > 0:
            lines.append(f"Overall weight change is down {fmt_number(pounds_lost, 1)} lb from start.")
        elif pounds_lost < 0:
            lines.append(f"Overall weight change is up {fmt_number(abs(pounds_lost), 1)} lb from start.")
        else:
            lines.append("Overall weight is unchanged from start.")

    minutes = exercise.get("duration_minutes") or 0
    if minutes:
        lines.append(f"Total exercise time logged: {fmt_number(minutes)} minutes.")

    return lines




def needed(current, target):
    if current is None or target is None:
        return None
    return max(float(target) - float(current), 0)


def print_progress_line(label, current, target, unit=""):
    if target is None:
        print(f"{label}: --")
        return
    remaining = float(target or 0) - float(current or 0)
    suffix = f" {unit}" if unit else ""
    print(f"{label}: {fmt_number(current)} / {fmt_number(target)}{suffix}")
    if remaining > 0:
        print(f"  Needed: {fmt_number(remaining)}{suffix}")


def print_next_milestones_dashboard(data):
    print("NEXT MILESTONES")
    print("===============")

    weight = data.get("weight", {})
    print_section("Weight")
    print(f"Start   : {fmt_weight(weight.get('start'))}")
    print(f"Current : {fmt_weight(weight.get('current'))}")
    pounds_lost = weight.get("pounds_lost")
    percent_lost = weight.get("percent_lost")
    if pounds_lost is None:
        print("Progress: no weight data yet")
    else:
        if pounds_lost >= 0:
            print(f"Lost    : {fmt_number(pounds_lost, 1)} lb ({fmt_number(percent_lost, 1)}%)")
        else:
            print(f"Change  : +{fmt_number(abs(pounds_lost), 1)} lb ({fmt_number(percent_lost, 1)}%)")
        print(f"Next lb milestone      : {fmt_number(weight.get('next_pounds_lost'))} lb lost")
        print(f"Needed for next lb mark: {fmt_number(weight.get('pounds_to_next'), 1)} lb")
        print(f"Next percent milestone : {fmt_number(weight.get('next_percent_lost'))}% lost")

    exercise = data.get("exercise", {})
    print_section("Exercise")
    print_progress_line("Sessions", exercise.get("sessions"), exercise.get("next_sessions"), "sessions")
    print_progress_line("Minutes ", exercise.get("minutes"), exercise.get("next_minutes"), "minutes")
    print_progress_line("Calories", exercise.get("calories"), exercise.get("next_calories"), "calories")

    food = data.get("food", {})
    print_section("Food")
    print_progress_line("Entries ", food.get("entries"), food.get("next_entries"), "entries")
    print_progress_line("Calories", food.get("calories"), food.get("next_calories"), "calories")

    reflection = data.get("reflection", {})
    print_section("Reflection")
    print_progress_line("Notes       ", reflection.get("notes"), reflection.get("next_notes"), "notes")
    print_progress_line("Observations", reflection.get("observations"), reflection.get("next_observations"), "observations")
    print_progress_line("Victories   ", reflection.get("victories"), reflection.get("next_victories"), "victories")

def print_trend_dashboard(data):
    days = data.get("days", 7)
    current = data.get("current", {})
    previous = data.get("previous", {})
    averages = data.get("averages", {})
    flags = set(data.get("flags", []))

    print(f"{days}-DAY TREND REPORT")
    print("=" * (len(str(days)) + 17))

    print_section("Confidence")
    print(f"Level : {data.get('confidence', 'unknown')}")
    for reason in data.get("confidence_reasons", []):
        print(f"- {reason}")

    print_section("Weight")
    print(f"Entries : {fmt_number(current.get('weight_entries'))}")
    print(f"Start   : {fmt_weight(current.get('start_weight'))}")
    print(f"Current : {fmt_weight(current.get('current_weight'))}")
    change = current.get("weight_change")
    if change is None:
        print("Change  : --")
    elif change < 0:
        print(f"Change  : down {fmt_number(abs(change), 1)} lb")
    elif change > 0:
        print(f"Change  : up {fmt_number(change, 1)} lb")
    else:
        print("Change  : stable")

    print_section("Food")
    print(f"Current entries : {fmt_number(current.get('food_count'))}")
    print(f"Current days    : {fmt_number(averages.get('current_food_days'))} of {fmt_number(days)}")
    print(f"Calories total  : {fmt_range(current.get('calories_min'), current.get('calories_max'))}")
    print(f"Calories/day    : {fmt_range(averages.get('current_avg_calories_min'), averages.get('current_avg_calories_max'))}")
    print(f"Carbs/day       : {fmt_range(averages.get('current_avg_carbs_min'), averages.get('current_avg_carbs_max'), ' g')}")

    diff = averages.get("calorie_midpoint_difference")
    if diff is not None:
        if diff < 0:
            print(f"Vs previous     : down {fmt_number(abs(diff))} cal/day")
        elif diff > 0:
            print(f"Vs previous     : up {fmt_number(diff)} cal/day")
        else:
            print("Vs previous     : unchanged")
    else:
        print("Vs previous     : not enough prior food data")

    print_section("Exercise")
    print(f"Current sessions : {fmt_number(current.get('exercise_count'))}")
    print(f"Current days     : {fmt_number(averages.get('current_exercise_days'))} of {fmt_number(days)}")
    print(f"Minutes          : {fmt_number(averages.get('current_exercise_minutes'))}")
    print(f"Calories         : {fmt_range(current.get('burned_min'), current.get('burned_max'))}")
    print(f"Previous sessions: {fmt_number(previous.get('exercise_count'))}")
    print(f"Previous minutes : {fmt_number(previous.get('duration_minutes'))}")

    print_section("Flags")
    if flags:
        for flag in sorted(flags):
            print(f"- {flag}")
    else:
        print("None")

    print_section("Coach")
    if "weight_down" in flags:
        print("- Weight is trending down in this period.")
    elif "weight_up" in flags:
        print("- Weight is trending up in this period; compare this with sodium, food volume, and weigh-in timing before assuming fat gain.")
    elif "weight_stable" in flags:
        print("- Weight is stable in this period.")
    else:
        print("- More weigh-ins are needed for a reliable weight trend.")

    if "calories_down_vs_previous" in flags:
        print("- Average logged calories are lower than the previous comparable period.")
    elif "calories_up_vs_previous" in flags:
        print("- Average logged calories are higher than the previous comparable period.")
    elif "calories_similar_vs_previous" in flags:
        print("- Average logged calories are similar to the previous comparable period.")
    else:
        print("- More prior food data is needed for calorie comparison.")

    if current.get("exercise_count", 0):
        print("- Exercise logging is active during this period.")
    else:
        print("- No exercise is logged during this period.")


def print_period_report(data):
    days = data.get("days", 0)
    print(f"{days}-DAY REPORT")
    print("=" * (len(str(days)) + 11))

    print_section("Weight")
    print(f"Entries : {fmt_number(data.get('weight_entries'))}")
    print(f"Start   : {fmt_weight(data.get('start_weight'))}")
    print(f"Current : {fmt_weight(data.get('current_weight'))}")
    change = data.get("weight_change")
    if change is None:
        print("Change  : --")
    elif change < 0:
        print(f"Change  : down {fmt_number(abs(change), 1)} lb")
    elif change > 0:
        print(f"Change  : up {fmt_number(change, 1)} lb")
    else:
        print("Change  : stable")

    averages = data.get("averages", {})
    print_section("Food")
    print(f"Entries      : {fmt_number(data.get('food_count'))}")
    print(f"Calories     : {fmt_range(data.get('calories_min'), data.get('calories_max'))}")
    print(f"Calories/day : {fmt_range(averages.get('calories_min_per_day'), averages.get('calories_max_per_day'))}")
    print(f"Carbs        : {fmt_range(data.get('carbs_min'), data.get('carbs_max'), ' g')}")
    print(f"Carbs/day    : {fmt_range(averages.get('carbs_min_per_day'), averages.get('carbs_max_per_day'), ' g')}")

    print_section("Exercise")
    print(f"Sessions    : {fmt_number(data.get('exercise_count'))}")
    print(f"Minutes     : {fmt_number(data.get('exercise_minutes'))}")
    print(f"Minutes/day : {fmt_number(averages.get('exercise_minutes_per_day'), 1)}")
    print(f"Calories    : {fmt_range(data.get('burned_min'), data.get('burned_max'))}")

    print_section("Reflections")
    print(f"Notes        : {fmt_number(data.get('note_count'))}")
    print(f"Observations : {fmt_number(len(data.get('observations', [])))}")
    print(f"Victories    : {fmt_number(len(data.get('victories', [])))}")

    print_section("Milestones")
    milestones = data.get("milestones", [])
    if milestones:
        for item in milestones:
            title = item.get("title") or item.get("milestone_key") or "Milestone"
            log_date = item.get("log_date")
            if log_date:
                print(f"- {log_date}: {title}")
            else:
                print(f"- {title}")
    else:
        print("None in this period")

    print_section("Highlights")
    victories = data.get("victories", [])
    observations = data.get("observations", [])
    if victories:
        print("Victories:")
        for item in victories[:5]:
            print(f"- {item.get('log_date')}: {item.get('victory')}")
    if observations:
        print("Observations:")
        for item in observations[:5]:
            print(f"- {item.get('log_date')}: {item.get('observation')}")
    if not victories and not observations:
        print("No victories or observations logged in this period")

    print_section("Coach")
    if data.get("food_count", 0):
        print("- Food logging is active in this period.")
    else:
        print("- No food was logged in this period.")
    if data.get("exercise_count", 0):
        print("- Exercise logging is active in this period.")
    else:
        print("- No exercise was logged in this period.")
    if change is None:
        print("- More weigh-ins are needed to summarize weight movement.")
    elif change < 0:
        print("- Weight moved down during this period.")
    elif change > 0:
        print("- Weight moved up during this period; compare against food volume, sodium, timing, and consistency.")
    else:
        print("- Weight was stable during this period.")

def print_status_next_milestones(next_data):
    weight = next_data.get("weight", {})
    exercise = next_data.get("exercise", {})
    food = next_data.get("food", {})
    reflection = next_data.get("reflection", {})

    print_section("Next Milestones")

    pounds_lost = weight.get("pounds_lost")
    if pounds_lost is None:
        print("Weight     : no weight data yet")
    else:
        pounds_to_next = weight.get("pounds_to_next")
        next_pounds = weight.get("next_pounds_lost")
        if pounds_to_next is None:
            print("Weight     : --")
        elif pounds_to_next <= 0:
            print(f"Weight     : {fmt_number(next_pounds)} lb loss milestone reached")
        else:
            print(f"Weight     : {fmt_number(pounds_to_next, 1)} lb to {fmt_number(next_pounds)} lb lost")

    exercise_sessions_needed = needed(exercise.get("sessions"), exercise.get("next_sessions"))
    exercise_minutes_needed = needed(exercise.get("minutes"), exercise.get("next_minutes"))
    food_entries_needed = needed(food.get("entries"), food.get("next_entries"))
    food_calories_needed = needed(food.get("calories"), food.get("next_calories"))
    victories_needed = needed(reflection.get("victories"), reflection.get("next_victories"))

    print(f"Exercise   : {fmt_number(exercise_sessions_needed)} sessions to {fmt_number(exercise.get('next_sessions'))}")
    print(f"Minutes    : {fmt_number(exercise_minutes_needed)} minutes to {fmt_number(exercise.get('next_minutes'))}")
    print(f"Food       : {fmt_number(food_entries_needed)} entries to {fmt_number(food.get('next_entries'))}")
    print(f"Food cals  : {fmt_number(food_calories_needed)} calories to {fmt_number(food.get('next_calories'))}")
    print(f"Victories  : {fmt_number(victories_needed)} victories to {fmt_number(reflection.get('next_victories'))}")


def print_status_dashboard(data, next_data=None):
    print("WEIGHT TRACKER STATUS")
    print("=====================")

    milestones = data.get("recent_milestones", [])
    print_section("Recent Milestones")
    if milestones:
        for item in milestones[:5]:
            print(f"- {item.get('title', item.get('milestone_key', 'Milestone'))}")
    else:
        print("None yet")

    print_section("Today's Summary")
    print_today_summary(data)

    print_section("Today's Activity")
    today = data.get("today_activity", [])
    if today:
        for item in today:
            summary = item.get("summary") or item.get("action_type") or "activity"
            action_time = item.get("action_time")
            if action_time:
                print(f"- {action_time}: {summary}")
            else:
                print(f"- {summary}")
    else:
        print("No activity logged today")

    print_section("Progress")
    weight = data.get("weight", {})
    logging = data.get("logging", {})
    food = data.get("food", {})
    exercise = data.get("exercise", {})
    print(f"Start weight : {fmt_weight(weight.get('start'))}")
    print(f"Current      : {fmt_weight(weight.get('current'))}")
    pounds_lost = weight.get("pounds_lost")
    percent_lost = weight.get("percent_lost")
    if pounds_lost is None:
        print("Change       : --")
    elif pounds_lost >= 0:
        print(f"Lost         : {fmt_number(pounds_lost, 1)} lb ({fmt_number(percent_lost, 1)}%)")
    else:
        print(f"Change       : +{fmt_number(abs(pounds_lost), 1)} lb ({fmt_number(percent_lost, 1)}%)")
    print(f"Food entries : {fmt_number(logging.get('food_entries'))}")
    print(f"Exercise     : {fmt_number(logging.get('exercise_sessions'))}")
    print(f"Notes        : {fmt_number(logging.get('notes'))}")
    print(f"Calories     : {fmt_range(food.get('calories_min'), food.get('calories_max'))}")
    print(f"Exercise min : {fmt_number(exercise.get('duration_minutes'))}")

    if next_data is not None:
        print_status_next_milestones(next_data)

    print_section("Coach")
    for line in coach_lines(data):
        print(f"- {line}")

    latest = data.get("latest_activity", [])
    print_section("Latest Activity")
    if latest:
        first_time = latest[0].get("action_time")
        if first_time:
            print(f"Last activity: {first_time}")
        for item in latest[:5]:
            summary = item.get("summary") or item.get("action_type") or "activity"
            action_time = item.get("action_time")
            if action_time:
                print(f"- {action_time}: {summary}")
            else:
                print(f"- {summary}")
    else:
        print("No activity yet")

def main():
    chat_id, display_name, args = extract_identity(sys.argv[1:])

    if not args:
        usage()
        return 1

    cmd = args[0]

    if cmd in ("help", "commands"):
        if len(args) == 1:
            print_command_index()
            return 0
        if len(args) == 2 and args[1] == "--json":
            print_help_json()
            return 0
        if len(args) == 2:
            return print_command_help(args[1])
        usage()
        return 1

    if cmd == "capabilities":
        if len(args) != 1:
            usage()
            return 1
        print_capabilities_json()
        return 0

    if cmd == "version":
        emit({"tool": "weight_tracker", "version": VERSION, "command_schema_version": "1", "data_schema_version": "1"})
        return 0

    if cmd == "doctor":
        result = database_diagnostics()
        emit(result)
        return 0 if result.get("status") == "ok" else 2

    if cmd == "init":
        emit(initialize_database())
        return 0

    if cmd == "export":
        if len(args) != 2:
            usage(); return 1
        if not chat_id:
            emit({"status": "error", "message": "--chat-id is required for export"}); return 2
        emit(export_user(chat_id, args[1]))
        return 0

    if cmd == "import":
        if len(args) not in (2, 3):
            usage(); return 1
        if not chat_id:
            emit({"status": "error", "message": "--chat-id is required for import"}); return 2
        mode = args[2] if len(args) == 3 else "merge"
        try:
            emit(import_user(args[1], chat_id, mode))
            return 0
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            emit({"status": "error", "message": str(exc)})
            return 1

    if cmd == "serve":
        if len(args) > 3:
            usage(); return 1
        bind = args[1] if len(args) >= 2 else "127.0.0.1"
        port = args[2] if len(args) >= 3 else "8765"
        api_server = str(BASE_DIR / "tools" / "api_server.py")
        os.execv(sys.executable, [
            sys.executable,
            api_server,
            "--bind", bind,
            "--port", port,
        ])
        return 1  # os.execv only returns if execution fails

    if not chat_id:
        emit({
            "status": "error",
            "message": "--chat-id is required for user data commands; alternatively set WEIGHT_TRACKER_DEFAULT_CHAT_ID",
        })
        return 2

    if cmd == "weight":
        if len(args) != 2:
            usage()
            return 1
        weight = as_float(args[1], "weight")
        emit(log_weight(chat_id, weight, display_name, "cli"))
        return 0

    if cmd == "weights":
        try:
            rows = list_weights(chat_id, parse_list_limit(args, 10))
        except ValueError as exc:
            emit({"status": "error", "message": str(exc)})
            return 1
        emit(rows) if OUTPUT_JSON else print_rows(rows)
        return 0

    if cmd == "food":
        if len(args) != 8:
            usage()
            return 1
        emit(log_food(
            chat_id=chat_id,
            meal=args[1],
            description=args[2],
            calories_min=as_float(args[3], "calories_min"),
            calories_max=as_float(args[4], "calories_max"),
            carbs_min=as_float(args[5], "carbs_min"),
            carbs_max=as_float(args[6], "carbs_max"),
            confidence=args[7],
            display_name=display_name,
            source_text="cli",
        ))
        return 0

    if cmd == "foods":
        try:
            rows = list_food(chat_id, parse_list_limit(args, 20))
        except ValueError as exc:
            emit({"status": "error", "message": str(exc)})
            return 1
        emit(rows) if OUTPUT_JSON else print_rows(rows)
        return 0

    if cmd == "exercise":
        if len(args) != 8:
            usage()
            return 1
        emit(log_exercise(
            chat_id=chat_id,
            description=args[1],
            exercise_type=args[2],
            duration_minutes=as_float(args[3], "duration_minutes"),
            distance=as_float(args[4], "distance"),
            calories_burned_min=as_float(args[5], "calories_burned_min"),
            calories_burned_max=as_float(args[6], "calories_burned_max"),
            confidence=args[7],
            display_name=display_name,
            source_text="cli",
        ))
        return 0

    if cmd == "exercises":
        try:
            rows = list_exercise(chat_id, parse_list_limit(args, 20))
        except ValueError as exc:
            emit({"status": "error", "message": str(exc)})
            return 1
        emit(rows) if OUTPUT_JSON else print_rows(rows)
        return 0

    if cmd == "summary":
        emit(daily_summary(chat_id))
        return 0


    if cmd == "report":
        if len(args) != 2:
            usage()
            return 1

        days = as_int(args[1], "days")
        data = period_summary(chat_id, days)
        emit(data) if OUTPUT_JSON else print_period_report(data)
        return 0

    if cmd == "undo":
        emit(undo_last(chat_id))
        return 0

    if cmd == "note":
        if len(args) < 2:
            usage()
            return 1
        note = args[1]
        tags = args[2] if len(args) >= 3 else None
        emit(log_note(chat_id, note, tags, display_name))
        return 0

    if cmd == "notes":
        try:
            rows = list_notes(chat_id, parse_list_limit(args, 20))
        except ValueError as exc:
            emit({"status": "error", "message": str(exc)})
            return 1
        emit(rows) if OUTPUT_JSON else print_rows(rows)
        return 0

    if cmd == "observation":
        if len(args) < 2:
            usage()
            return 1
        observation = args[1]
        observation_type = args[2] if len(args) >= 3 else "general"
        tags = args[3] if len(args) >= 4 else None
        importance = as_int(args[4], "importance") if len(args) >= 5 else 5
        emit(log_observation(
            chat_id,
            observation,
            observation_type,
            tags,
            importance,
            display_name,
        ))
        return 0

    if cmd == "observations":
        try:
            rows = list_observations(chat_id, parse_list_limit(args, 20))
        except ValueError as exc:
            emit({"status": "error", "message": str(exc)})
            return 1
        emit(rows) if OUTPUT_JSON else print_rows(rows)
        return 0

    if cmd == "victory":
        if len(args) < 2:
            usage()
            return 1
        victory = args[1]
        victory_type = args[2] if len(args) >= 3 else "general"
        tags = args[3] if len(args) >= 4 else None
        emit(log_victory(chat_id, victory, victory_type, tags, display_name))
        return 0

    if cmd == "victories":
        try:
            rows = list_victories(chat_id, parse_list_limit(args, 20))
        except ValueError as exc:
            emit({"status": "error", "message": str(exc)})
            return 1
        emit(rows) if OUTPUT_JSON else print_rows(rows)
        return 0


    if cmd == "progress":
        if len(args) != 1:
            usage()
            return 1
        data = progress_overview(chat_id)
        emit(data) if OUTPUT_JSON else print_progress_dashboard(data)
        return 0

    if cmd == "trend":
        if len(args) > 2:
            usage()
            return 1
        days = as_int(args[1], "days") if len(args) == 2 else 7
        data = trend_report(chat_id, days)
        emit(data) if OUTPUT_JSON else print_trend_dashboard(data)
        return 0

    if cmd in ("status", "dashboard"):
        if len(args) != 1:
            usage()
            return 1
        progress = progress_overview(chat_id)
        next_data = next_milestones_overview(chat_id)
        if OUTPUT_JSON:
            emit({"status": progress, "next_milestones": next_data})
        else:
            print_status_dashboard(progress, next_data)
        return 0

    if cmd in ("next", "next-milestones"):
        if len(args) != 1:
            usage()
            return 1
        data = next_milestones_overview(chat_id)
        emit(data) if OUTPUT_JSON else print_next_milestones_dashboard(data)
        return 0

    if cmd == "milestones":
        if len(args) > 2:
            usage()
            return 1
        try:
            limit = parse_list_limit(args, 20)
        except ValueError as exc:
            emit({"status": "error", "message": str(exc)})
            return 1
        rows = list_system_milestones(chat_id, limit)
        emit(rows) if OUTPUT_JSON else print_rows(rows)
        return 0

    if cmd == "replace-weight":
        if len(args) != 3:
            usage()
            return 1
        emit(replace_weight(
            weight_id=as_int(args[1], "weight_id"),
            new_weight=as_float(args[2], "new_weight"),
        ))
        return 0

    usage()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
