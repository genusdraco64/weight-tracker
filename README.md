# Weight Tracker

Weight Tracker is a local-first wellness tracking engine for people, automation, and AI agents. It stores data in SQLite and exposes stable text and JSON interfaces for weight, food, exercise, notes, observations, victories, milestones, reports, trends, export/import, and an optional REST API.

**Public beta:** v0.90.0. The CLI/JSON contracts are stable enough for integrations, but the project has not yet declared a 1.0 compatibility guarantee.

## Why it is different

- Local SQLite database; no hosted account required.
- Natural-language agents can operate it through a self-documenting CLI.
- Machine-readable `capabilities` and `help --json` interfaces.
- Complete history is available for charts and integrations.
- Optional dependency-free REST API.
- Per-user JSON export/import.
- No third-party Python packages.

Weight Tracker is an informational wellness tool, not a medical device. See `DISCLAIMER.md`.

## Requirements

- Python 3.9+
- SQLite support included with Python
- Linux (tested on Debian) for the complete bundled toolchain; the Python core is intentionally dependency-free and may work on other POSIX-like systems

## Quick start

Extract the release and install it into your user account:

```bash
tar -xzf weight_tracker-v0.90.0-code-only.tar.gz
cd weight_tracker
./install.sh
```

Ensure `~/.local/bin` is on `PATH`, then:

```bash
weight_tracker doctor
weight_tracker --chat-id demo weight 199.4
weight_tracker --chat-id demo status
```

For a portable checkout without installing:

```bash
./weight_tracker init
./weight_tracker --chat-id demo weight 199.4
./weight_tracker --chat-id demo status
```

Existing installations must keep their current `weight_tracker.db`. Release archives intentionally exclude databases.

## Common commands

```bash
weight_tracker capabilities
weight_tracker help
weight_tracker help status
weight_tracker help --json
weight_tracker version
weight_tracker doctor

weight_tracker --chat-id 123 weight 199.4
weight_tracker --chat-id 123 food breakfast "2 eggs and toast" 240 300 20 30 high
weight_tracker --chat-id 123 exercise "walked 2 miles" walking 40 2 180 220 high
weight_tracker --chat-id 123 status
weight_tracker --chat-id 123 report 14
weight_tracker --chat-id 123 trend 7
```

## Machine-readable interfaces

Add `--json` to supported commands:

```bash
weight_tracker --chat-id 123 --json status
weight_tracker --chat-id 123 --json trend 7
weight_tracker --chat-id 123 --json report 30
weight_tracker --chat-id 123 --json weights all
```

List commands normally return a concise recent view. Integrations needing complete history must request `all`; they must not treat the default display limit as the complete dataset.

## User identity

User data commands require `--chat-id ID` unless `WEIGHT_TRACKER_DEFAULT_CHAT_ID` is configured. IDs are opaque strings; use a platform prefix when it helps avoid collisions, such as `telegram:12345` or `local:greg`.

For compatibility, an existing `telegram:<numeric-id>` record is still found when an older integration supplies the bare numeric ID. New bare numeric IDs are no longer automatically labeled as Telegram.

## Database and privacy

The default database is `weight_tracker.db` beside the installed application. Override it for testing or integrations:

```bash
WEIGHT_TRACKER_DB=/tmp/test.db weight_tracker init
```

The database contains private wellness information. Keep it out of repositories, bug reports, and release archives. See `PRIVACY.md` and `SECURITY.md`.

## Export and import

```bash
weight_tracker --chat-id 123 export user-123.json
weight_tracker --chat-id 123 import user-123.json merge
```

See `docs/DATA_PORTABILITY.md`.

## AI agent integration

A generic agent prompt is included at `prompts/wellness_agent.md`. It does not assume OpenClaw, Telegram, a username, or a particular filesystem path.

For integration guidance, see `docs/AGENT_INTEGRATION.md`.

## REST API

The REST server is optional and does not need to run for CLI or agent use.

```bash
weight_tracker serve
curl http://127.0.0.1:8765/health
```

The default listener is localhost only. Read `docs/REST_API.md` before binding it to a network interface.

## Development

```bash
./tests/regression.sh
./tests/public_release.sh
```

Stable interfaces are documented in `docs/CLI_CONTRACT.md`. Architecture is described in `docs/ARCHITECTURE.md`.

## Release packaging

```bash
./scripts/package_release.sh
```

Packaging runs the regression and public-release checks before creating an archive, checksum, and manifest. Databases, WAL/SHM files, bytecode, caches, backups, and runtime logs are excluded.

## License

MIT. See `LICENSE`.
