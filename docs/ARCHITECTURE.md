# Architecture

Weight Tracker separates natural-language interaction from deterministic wellness storage and reporting.

```text
Human / automation / AI agent
            |
            v
       CLI or REST API
            |
            v
       tracker.py
            |
   +--------+--------+
   |        |        |
 logging  reports  discovery
   |        |        |
   +--------+--------+
            |
            v
          db.py
            |
            v
          SQLite
```

## Components

- `weight_tracker` — portable launcher.
- `tools/tracker.py` — command parsing, formatting, help, capabilities, and application orchestration.
- `tools/db.py` — SQLite persistence, identity resolution, milestones, reports, and diagnostics.
- `tools/data_portability.py` — per-user JSON export/import.
- `tools/api_server.py` — optional dependency-free REST adapter.
- `schema.sql` — schema for new databases.
- `prompts/wellness_agent.md` — generic AI-agent operating guidance.

## Contracts

Human-facing text may evolve for readability. JSON clients should rely on `command_schema_version` and `data_schema_version` and consult `capabilities`.

The live database is runtime state and is never part of a release artifact.
