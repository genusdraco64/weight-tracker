# Weight Tracker

**A local-first wellness tracking platform built for humans, automation, and AI agents.**

Weight Tracker keeps weight, food, exercise, notes, observations, victories, and milestones in a local SQLite database while providing stable CLI and JSON interfaces that AI agents and other software can use.

Your wellness history remains under your control. No cloud account, hosted database, subscription, or third-party Python packages are required.

> **Public Beta — v0.90.1**
>
> Weight Tracker is ready for outside testing. CLI and JSON interfaces are intended to remain stable, but a final 1.0 compatibility guarantee has not yet been declared.

---

## What does it do?

You can use Weight Tracker directly:

```bash
weight_tracker --chat-id demo weight 194.8
weight_tracker --chat-id demo status
```

Or put an AI agent in front of it and interact naturally:

```text
You:
I weighed 194.8 this morning.

Agent:
Logs the weight through Weight Tracker, checks for milestones,
and can return your updated status.
```

Later you can ask:

```text
How have I been doing for the last two weeks?

Show me my 7-day trend.

How close am I to my next milestones?

Graph my weight since I started.
```

The agent can discover Weight Tracker's capabilities rather than relying on a hard-coded list of commands:

```bash
weight_tracker capabilities
weight_tracker help --json
weight_tracker help status
```

Complete history is also available in machine-readable form:

```bash
weight_tracker --chat-id demo --json weights all
```

This makes Weight Tracker usable as both a standalone CLI application and a persistent data engine behind AI assistants, dashboards, scripts, and other integrations.

---

## Why local-first?

Wellness data is personal.

Weight Tracker stores its data in a normal SQLite database on the machine running it. There is no required hosted service and no Weight Tracker account.

That means:

- you control the database;
- the application works without a cloud backend;
- data can be backed up with ordinary filesystem tools;
- individual users can be exported and imported as JSON;
- AI agents can use persistent structured data without making the AI conversation itself the database.

Release archives intentionally contain **no user database, backups, logs, or wellness data**.

See [PRIVACY.md](PRIVACY.md) and [SECURITY.md](SECURITY.md).

---

## Features

- Weight tracking
- Food and carbohydrate/calorie estimates
- Exercise tracking
- Notes and observations
- Scale and non-scale victories
- Automatic milestones
- Upcoming milestone progress
- Daily status dashboard
- Multi-day reports
- Period-over-period trends
- Complete historical data access
- Text and JSON output
- Multi-user identity support
- Per-user JSON export/import
- Self-documenting CLI
- Machine-readable capability discovery
- AI-agent integration prompt
- Optional dependency-free REST API
- Automated regression testing
- Public-release privacy checks
- Local SQLite storage
- No third-party Python packages

---

## Example status

A typical status report looks like:

```text
WEIGHT TRACKER STATUS
=====================

Today's Summary
---------------
Weight logs : 1
Food logs   : 3

Progress
--------
Start weight : 225.0 lb
Current      : 217.5 lb
Lost         : 7.5 lb (3.3%)
Food entries : 84
Exercise     : 18
Exercise min : 720

Next Milestones
---------------
Weight   : 2.5 lb to 10 lb lost
Exercise : 2 sessions to 20
Minutes  : 80 minutes to 800

Coach
-----
- Weight was logged today.
- Food logging is active today.
- Overall weight change is down 7.5 lb from start.
```

Values above are example output. Your database contains only your own users and history.

---

## Requirements

- Python 3.9+
- Python SQLite support
- Linux for the complete bundled toolchain

Weight Tracker is developed and tested primarily on Debian Linux. The Python core is intentionally dependency-free and may also work on other POSIX-like systems.

---

## Installation

Download the latest release from the GitHub Releases page.

Extract it:

```bash
tar -xzf weight_tracker-v0.90.1-code-only.tar.gz
cd weight_tracker
./install.sh
```

Ensure `~/.local/bin` is on your `PATH`.

Verify the installation:

```bash
weight_tracker version
weight_tracker doctor
```

Then create your first entry:

```bash
weight_tracker --chat-id demo weight 199.4
weight_tracker --chat-id demo status
```

### Portable checkout

Installation is not required. Weight Tracker can run directly from the source directory:

```bash
./weight_tracker init
./weight_tracker --chat-id demo weight 199.4
./weight_tracker --chat-id demo status
```

### Existing installations

Keep your existing `weight_tracker.db` when upgrading.

Release archives intentionally exclude databases.

---

## Common commands

```bash
# Discover the interface
weight_tracker capabilities
weight_tracker help
weight_tracker help status
weight_tracker help --json

# Diagnostics
weight_tracker version
weight_tracker doctor

# Logging
weight_tracker --chat-id demo weight 199.4
weight_tracker --chat-id demo food breakfast "2 eggs and toast" 240 300 20 30 high
weight_tracker --chat-id demo exercise "walked 2 miles" walking 40 2 180 220 high

# Reports
weight_tracker --chat-id demo status
weight_tracker --chat-id demo report 14
weight_tracker --chat-id demo trend 7
weight_tracker --chat-id demo next-milestones
```

Run:

```bash
weight_tracker help
```

for the complete command list.

---

## JSON and integrations

Supported commands can return structured JSON:

```bash
weight_tracker --chat-id demo --json status
weight_tracker --chat-id demo --json trend 7
weight_tracker --chat-id demo --json report 30
weight_tracker --chat-id demo --json weights all
```

List commands normally return a concise recent view.

Integrations requiring complete history should explicitly request `all`. A default display limit must not be interpreted as the complete dataset.

The command contract is documented in [docs/CLI_CONTRACT.md](docs/CLI_CONTRACT.md).

---

## AI agent integration

Weight Tracker was designed so an AI agent does not need to memorize its interface.

An agent can ask the application what it supports:

```bash
weight_tracker capabilities
weight_tracker help --json
weight_tracker help COMMAND
```

A generic wellness-agent prompt is provided at:

```text
prompts/wellness_agent.md
```

The prompt instructs an agent to use Weight Tracker as the authoritative structured data store and to verify capabilities before claiming that an operation is unsupported.

It does not require a particular AI platform, username, chat service, or filesystem path.

See [docs/AGENT_INTEGRATION.md](docs/AGENT_INTEGRATION.md) for integration details.

---

## User identity

User-data commands require:

```text
--chat-id ID
```

unless `WEIGHT_TRACKER_DEFAULT_CHAT_ID` is configured.

IDs are opaque strings. Platform prefixes can be used to avoid collisions:

```text
telegram:12345
local:greg
discord:12345
```

Compatibility handling exists for older Telegram numeric identities.

---

## Export and import

Export one user's data:

```bash
weight_tracker --chat-id demo export user-demo.json
```

Import it:

```bash
weight_tracker --chat-id demo import user-demo.json merge
```

See [docs/DATA_PORTABILITY.md](docs/DATA_PORTABILITY.md).

Export files contain wellness information and should be protected like the database itself.

---

## Optional REST API

The REST API is **not required** for normal CLI or AI-agent operation.

Start a local server:

```bash
weight_tracker serve
```

Test it:

```bash
curl http://127.0.0.1:8765/health
```

The server binds to localhost by default.

Network exposure requires authentication safeguards. Read [docs/REST_API.md](docs/REST_API.md) before binding the API to another interface.

---

## Development and testing

Run the complete regression suite:

```bash
./tests/regression.sh
```

Run the public-release hygiene checks:

```bash
./tests/public_release.sh
```

Architecture documentation is available in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Building a release

```bash
./scripts/package_release.sh
```

The packaging process runs regression and public-release checks before producing the release archive, SHA-256 checksum, and manifest.

Databases, WAL/SHM files, backups, logs, Python bytecode, caches, and other runtime/private files are excluded.

---

## Project status

Weight Tracker is currently in public beta.

The goal of the beta is to test installation and AI-agent integration on systems beyond the original development environment before declaring the 1.0 interface contract.

Bug reports and installation reports are welcome through GitHub Issues.

See [ROADMAP.md](ROADMAP.md) for planned work.

---

## Medical disclaimer

Weight Tracker is intended for personal wellness tracking and informational purposes.

It is **not a medical device** and does not provide medical diagnosis or treatment.

See [DISCLAIMER.md](DISCLAIMER.md).

---

## License

Weight Tracker is released under the MIT License.

See [LICENSE](LICENSE).
