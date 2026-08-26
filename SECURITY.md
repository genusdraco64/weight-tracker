# Security

Do not publish a live `weight_tracker.db`, JSON export, API token, chat/user ID, or unsanitized wellness history in an issue or bug report.

## Local CLI

The CLI trusts operating-system users who can execute it and access its SQLite file. Use filesystem permissions and account isolation appropriate to the machine.

## REST API

The built-in API is localhost-only by default. A non-loopback bind requires a bearer token of at least 32 characters. The `/health` endpoint is deliberately minimal; user endpoints require authentication whenever a token is configured.

The built-in HTTP server does not provide TLS. Do not expose it directly to the public internet. Use a TLS-capable reverse proxy and network access controls if remote access is needed.

## Vulnerability reports

Include application version, reproduction steps, and sanitized output. Remove names, IDs, meals, weights, notes, file paths that reveal identities, and all other personal data.

## Reporting a security vulnerability

Please do not report security vulnerabilities through public GitHub Issues.

Use GitHub's private vulnerability reporting feature on this repository so security details can be reviewed privately before public disclosure.
