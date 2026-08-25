# API Reference

FastAPI generates interactive documentation at `/docs` (Swagger UI) and `/redoc`. This document describes the endpoints, request/response shapes, and authentication requirements.

## Authentication

All endpoints except `/health`, `/ready`, `/metrics`, `POST /api/v1/auth/register`, and `POST /api/v1/auth/login` require a JWT bearer token.

```
Authorization: Bearer <token>
```

Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 30 minutes).

---

## Auth endpoints

### `POST /api/v1/auth/register`

Create a new account. Rate-limited to 20 requests/minute per IP.

**Request**
```json
{ "email": "user@example.com", "password": "secure-password-123" }
```

Password must be at least 12 characters.

**Response** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "created_at": "2026-08-25T12:00:00"
}
```

**Errors**
- `409 Conflict` — email already registered
- `422 Unprocessable Entity` — validation error

---

### `POST /api/v1/auth/login`

Exchange credentials for a JWT. Rate-limited to 30 requests/minute per IP.

**Request**
```json
{ "email": "user@example.com", "password": "secure-password-123" }
```

**Response** `200 OK`
```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

**Errors**
- `401 Unauthorized` — invalid credentials
- `429 Too Many Requests` — rate limit exceeded

---

### `GET /api/v1/auth/me`

Return the current user. Requires authentication.

**Response** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "created_at": "2026-08-25T12:00:00"
}
```

---

## Configuration endpoints

All configuration endpoints require authentication. Users can only access their own configurations.

### `POST /api/v1/configurations`

Store a configuration for later analysis.

**Request**
```json
{
  "name": "production-dockerfile",
  "configuration_type": "dockerfile",
  "original_content": "FROM python:3.12\nRUN apt-get install vim\n"
}
```

`configuration_type` must be one of: `dockerfile`, `docker_compose`, `github_actions`.

**Response** `201 Created`
```json
{
  "id": "...",
  "user_id": "...",
  "name": "production-dockerfile",
  "configuration_type": "dockerfile",
  "original_content": "...",
  "created_at": "...",
  "updated_at": "..."
}
```

---

### `GET /api/v1/configurations`

List all configurations belonging to the current user.

**Response** `200 OK` — array of configuration objects (without `original_content`)

---

### `GET /api/v1/configurations/{id}`

Get a single configuration including its content.

**Errors**
- `404 Not Found` — configuration does not exist or belongs to another user

---

### `DELETE /api/v1/configurations/{id}`

Delete a configuration and all its analyses (cascade).

**Response** `204 No Content`

---

### `POST /api/v1/configurations/{id}/analyze`

Run the full analysis pipeline: static rules → AI analysis → risk scoring → persist.

**Response** `200 OK`
```json
{
  "id": "...",
  "configuration_id": "...",
  "status": "completed",
  "overall_score": 72.0,
  "error_message": null,
  "created_at": "...",
  "completed_at": "...",
  "findings": [
    {
      "id": "...",
      "analysis_id": "...",
      "rule_id": "DF001",
      "category": "security",
      "severity": "high",
      "title": "Container runs as root",
      "description": "No USER instruction found...",
      "recommendation": "Add a USER instruction...",
      "line_number": null,
      "evidence": "USER instruction is absent",
      "source": "deterministic",
      "confidence": null,
      "created_at": "..."
    }
  ]
}
```

`source` is either `"deterministic"` (static analyzer) or `"ai"` (LLM). `confidence` is a float 0–1 only for AI findings. `error_message` is populated when AI analysis failed but static findings are still returned.

**Errors**
- `404 Not Found` — configuration not found
- `422 Unprocessable Entity` — configuration content cannot be parsed (e.g. invalid YAML)

---

## Analysis endpoints

### `GET /api/v1/analyses`

List all analyses for the current user (across all configurations), most recent first.

**Response** `200 OK` — array of analysis objects with `findings: []` (empty — use `GET /analyses/{id}` for findings)

---

### `GET /api/v1/analyses/{id}`

Get a single analysis with all findings.

**Errors**
- `404 Not Found` — analysis not found or belongs to another user

---

## Health endpoints

These endpoints do not require authentication.

### `GET /health`

Liveness check. Returns `200 OK` if the process is running.

```json
{ "status": "ok" }
```

### `GET /ready`

Readiness check. Executes `SELECT 1` against the database. Returns `503 Service Unavailable` if the database is unreachable.

```json
{ "status": "ready" }
```

### `GET /metrics`

Prometheus text format metrics. Not included in the OpenAPI schema.

Tracked metrics:
- `http_requests_total` — counter by method, endpoint, status
- `http_request_duration_seconds` — histogram by method, endpoint
- `analyses_total` — counter of completed analyses
- `ai_provider_failures_total` — counter of AI provider errors

---

## Error format

All errors use FastAPI's standard format:

```json
{ "detail": "human-readable message" }
```

Validation errors return an array:

```json
{
  "detail": [
    { "loc": ["body", "email"], "msg": "value is not a valid email address", "type": "value_error.email" }
  ]
}
```

Stack traces are never exposed to clients. All 5xx errors are logged server-side.

---

## Risk scoring

`overall_score` is calculated as:

```
score = max(0, 100 − Σ weight(severity))
```

| Severity | Weight |
|---|---|
| critical | 10 |
| high | 7 |
| medium | 4 |
| low | 1 |
