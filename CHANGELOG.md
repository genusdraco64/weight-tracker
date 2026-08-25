# Changelog

## 0.90.1

### Fixed
- Public-release hygiene checks now validate the code-only release candidate instead of failing on legitimate live databases and backups in an installed instance.

## 0.90.0 - 2026-08-25 — Public Beta

### Added
- Generic AI-agent integration and architecture documentation.
- Public release checklist, roadmap, support guidance, and release hygiene tests.
- Release manifests and regression/hygiene gates in the packaging script.
- Example REST API environment configuration.

### Changed
- Removed developer-specific paths and user identifiers from public files.
- Updated installer permissions and public-facing documentation.
- Hardened REST authentication, health output, content handling, and POST command allowlisting.

### Compatibility
- Data schema remains version 1.
- Command schema remains version 1.
- No database migration is required.

## 0.40.2 - 2026-08-06

- Fixed regression tests to allocate available local TCP ports dynamically, avoiding false failures when fixed test ports are already in use.

## 0.40.1 - Maintenance Release

### Fixed
- REST API shutdown now handles terminal `Ctrl+C` cleanly.
- The API closes its listening socket and exits without Python tracebacks.
- The CLI `serve` wrapper now coordinates interruption of the child API process.

### Compatibility
- No database migration is required.
- No CLI or REST endpoint behavior changed.

## 0.30.0 - Platform Core Milestone

### Added
- Semantic version metadata and `version` command.
- `doctor` database integrity and schema check.
- `init` command and complete new-install `schema.sql`.
- JSON output for reports, dashboards, lists, and logging responses through `--json`.
- Full-history access through `weights all`, `foods all`, `exercises all`, and other list commands.
- `WEIGHT_TRACKER_DB` override for isolated testing and integrations.
- Portable launcher with no hard-coded home directory.
- Backward-compatible numeric/Telegram identity resolution.
- Regression test suite and public-project documentation.

### Changed
- Capabilities now report semantic, command-schema, and data-schema versions.
- Release packages are code-only and exclude SQLite databases and runtime files.

### Compatibility
- Existing CLI command names and text report formats remain supported.
- No live database migration is required for an existing installation.
