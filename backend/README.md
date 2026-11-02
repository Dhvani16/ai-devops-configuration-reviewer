# Backend

FastAPI application providing the analysis pipeline, REST API, JWT authentication, and PostgreSQL persistence.

## Quick commands

```bash
# Install dependencies (requires Python 3.12+)
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload

# Lint and format
ruff check app tests
ruff format app tests

# Run tests (no database or API key required)
pytest tests/ -v
```

## Key modules

| Module | Responsibility |
|---|---|
| `app/api/routes/` | Thin HTTP handlers — auth, configurations, analyses, health |
| `app/services/` | Business logic — pipeline orchestration, scoring, CRUD |
| `app/analyzers/` | Deterministic rule engines for Dockerfile, Compose, GitHub Actions |
| `app/ai/` | Provider abstraction, prompts, OpenAI/Ollama/Mock providers |
| `app/core/` | Config, security helpers, JSON logging, rate limiter, Prometheus metrics |
| `app/models/` | SQLAlchemy ORM models |
| `app/schemas/` | Pydantic request/response contracts |
| `migrations/` | Alembic migration scripts |

## AI providers

Set `AI_PROVIDER=openai` (default) and `OPENAI_API_KEY` for OpenAI. Set `AI_PROVIDER=ollama` with `OLLAMA_BASE_URL` and `OLLAMA_MODEL` for local Ollama. Tests always use `MockAIProvider` — no external service is needed.

## Endpoints

See [docs/API.md](../docs/API.md) for the full reference. Interactive docs are at `http://localhost:8000/docs`.
