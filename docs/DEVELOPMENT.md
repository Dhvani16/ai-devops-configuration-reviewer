# Development guide

## Prerequisites

- Docker Desktop with Docker Compose
- Python 3.12 or newer
- Node.js 20 or newer

## Environment configuration

Copy `.env.example` to `.env`. The example values are safe placeholders only; replace `SECRET_KEY` and local database credentials before any shared deployment. Never commit `.env`.

## Start the stack

Run from the repository root:

```powershell
docker compose up --build
```

Use `docker compose down` to stop services. Add `-v` only when you deliberately want to remove the local PostgreSQL data volume.

## Database migrations

Alembic creates the database schema. Docker applies migrations automatically before the backend starts. For local backend development, run this after configuring `DATABASE_URL`:

```powershell
cd backend
alembic upgrade head
```

## Local commands

```powershell
# backend
cd backend
python -m pip install -e ".[dev]"
ruff check .
pytest

# frontend
cd frontend
npm install
npm run lint
npm run typecheck
npm run build
```

Phase 1 does not yet contain application tests. Tests are added alongside features beginning in Phase 2.

AI provider tests use injected fake clients and `MockAIProvider`; no OpenAI key or Ollama installation is needed to run the test suite. A live OpenAI run requires `AI_PROVIDER=openai`, `OPENAI_API_KEY`, and optionally `OPENAI_MODEL`. A local Ollama run requires `AI_PROVIDER=ollama`, `OLLAMA_BASE_URL`, and `OLLAMA_MODEL`.
