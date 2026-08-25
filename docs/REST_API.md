# REST API v1

The REST server is optional and uses only the Python standard library. CLI and AI-agent integrations do not require it to run.

## Start locally

```bash
weight_tracker serve
```

Default listener: `127.0.0.1:8765`.

Stop a foreground server with `Ctrl+C`.

## Authentication and network binding

Localhost access is allowed without a token. Any non-loopback bind requires `WEIGHT_TRACKER_API_TOKEN` with at least 32 characters:

```bash
export WEIGHT_TRACKER_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
weight_tracker serve 0.0.0.0 8765
```

Authenticated requests use:

```text
Authorization: Bearer <token>
```

Do not expose the built-in server directly to the public internet. If remote access is required, keep the application behind TLS, firewall/network policy, and appropriate host authentication.

## Health endpoint

`GET /health` is intentionally minimal and unauthenticated so local supervisors can check the service without learning database paths, user counts, or wellness data.

Example:

```json
{"integrity":"ok","status":"ok"}
```

## Read endpoints

Authenticated unless otherwise stated:

- `GET /health` — minimal service/database health; unauthenticated
- `GET /v1/version`
- `GET /v1/capabilities`
- `GET /v1/users/{user_id}/status`
- `GET /v1/users/{user_id}/progress`
- `GET /v1/users/{user_id}/next-milestones`
- `GET /v1/users/{user_id}/weights`
- `GET /v1/users/{user_id}/foods`
- `GET /v1/users/{user_id}/exercises`
- `GET /v1/users/{user_id}/notes`
- `GET /v1/users/{user_id}/observations`
- `GET /v1/users/{user_id}/victories`
- `GET /v1/users/{user_id}/milestones`

List endpoints return complete history.

## Command endpoint

`POST /v1/users/{user_id}/command`

Requests must use `Content-Type: application/json`.

Example:

```json
{"command":"weight","args":[194.8]}
```

The endpoint uses an explicit allowlist. Administrative, discovery, import/export, initialization, server-control, and unknown future commands are not executable through the generic POST endpoint by default.

## Body limit

POST bodies are limited to 1 MiB.
