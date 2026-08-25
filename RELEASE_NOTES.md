# Release Notes

## v0.90.1

Maintenance release fixing the public-release hygiene test on live installations. Runtime databases and backups remain excluded from distributable archives; the test now inspects the candidate archive rather than treating legitimate installed data as a leak.

# Weight Tracker v0.90.0 — Public Beta

This release turns the stable local-first platform into a public-release candidate while preserving the v0.40.x data schema and established CLI behavior.

## Public-release work

- removed developer-specific filesystem paths and user IDs from shipped prompts/help examples
- rewrote the README around fresh installs, upgrades, AI-agent discovery, and public use
- added generic AI-agent integration and architecture documentation
- added public-release and support guidance
- expanded repository/runtime-data exclusions
- added automated public-release hygiene checks
- release packaging now runs regression and hygiene checks before producing artifacts
- installer uses restrictive permissions and preserves/backups an existing database

## REST hardening

- unauthenticated `/health` no longer exposes database paths or user counts
- bearer-token comparison uses constant-time comparison
- non-loopback binds require a token of at least 32 characters
- generic POST commands use an explicit allowlist
- POST requests require `Content-Type: application/json`
- `X-Content-Type-Options: nosniff` is sent with JSON responses

## Compatibility

- data schema version remains `1`
- command schema version remains `1`
- existing SQLite databases require no migration
- existing v0.40.x CLI commands remain available

This is a public beta, not a medical device or a 1.0 compatibility declaration.
