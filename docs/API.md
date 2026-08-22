# API plan

FastAPI will generate interactive OpenAPI documentation at `/docs`.

Phase 2 implements:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /health`
- `GET /ready`

`POST /api/v1/auth/register` and `POST /api/v1/auth/login` accept JSON containing `email` and a password of at least 12 characters. Login returns a bearer JWT. Pass it as `Authorization: Bearer <token>` to `GET /api/v1/auth/me`.

`GET /health` is a liveness check. `GET /ready` checks PostgreSQL connectivity and returns HTTP 503 if the database is unavailable.

Configuration and analysis endpoints are deferred until their supporting persistence and analysis phases are complete. This prevents publishing endpoints that do not yet perform real work.
