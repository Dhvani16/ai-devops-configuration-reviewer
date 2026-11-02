# Security

## Implemented controls

### Authentication and authorisation

- Passwords are hashed with **Argon2** (via `pwdlib`). Plain-text passwords are never stored, logged, or compared directly.
- Sessions use **JWT (HS256)**. The `SECRET_KEY` must be at least 32 characters; startup validation rejects shorter keys.
- **Authorization is enforced at the database query layer.** All configuration and analysis queries JOIN on `user_id` so a valid token from user A cannot retrieve user B's data, even if user B's IDs are guessed.
- Tokens expire after a configurable number of minutes (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 30).

### Transport and headers

Every HTTP response includes:

| Header | Value |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `geolocation=(), microphone=()` |

CORS is restricted to the origins listed in `CORS_ORIGINS`. Only `GET`, `POST`, and `DELETE` methods are permitted.

### Rate limiting

Auth endpoints are rate-limited per client IP using `slowapi` (in-memory):

- `POST /api/v1/auth/register` — 20 requests/minute
- `POST /api/v1/auth/login` — 30 requests/minute

Exceeded limits return `429 Too Many Requests`.

### Input validation

- All request bodies are validated by Pydantic before reaching route handlers. Invalid input returns `422` without touching the database.
- Email addresses are validated using `email-validator`. Passwords must be at least 12 characters.
- Configuration content is treated as **untrusted text**. It is passed to static analyzers and the AI prompt; it is never executed.
- AI responses are validated against a Pydantic schema before any findings are persisted. Malformed AI output is logged and skipped rather than silently stored.

### Secrets management

- API keys, `SECRET_KEY`, and database credentials are read from environment variables only. They are never hard-coded.
- `.env` is in `.gitignore`. `.env.example` contains only safe placeholder values.
- Logs are structured JSON. The logging configuration explicitly avoids logging request bodies, tokens, passwords, and API keys.

### Dependency supply chain

- Python dependencies use `>=` / `<` bounds to allow patch updates while preventing major-version drift.
- `bandit` static security analysis runs against the backend on demand. No medium or high severity issues were found at project completion.

## Out of scope for MVP

The following controls are documented as future enhancements:

- HTTPS/TLS termination (handled by the cloud platform or a reverse proxy)
- OAuth / social login
- Multi-factor authentication
- Content Security Policy header (requires per-page nonce integration)
- Secrets scanning in CI (e.g. `trufflehog`, `gitleaks`)
- OWASP ZAP or similar DAST scanning

## Reporting a vulnerability

Do not include secrets, exploit details, or reproduction steps in public GitHub issues. Contact the repository maintainer privately. Include the affected version, a description of the vulnerability, and any supporting evidence.
