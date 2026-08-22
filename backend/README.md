# Backend

Phases 2 and 3 provide validated environment settings, structured logging, async SQLAlchemy, Alembic migrations, health checks, JWT email/password authentication, and deterministic configuration analysis.

Run migrations with `alembic upgrade head`. In Docker, migrations run before Uvicorn starts.

The static analyzer has no external-service dependency. It supports Dockerfiles, Docker Compose YAML, and GitHub Actions workflows through `app.analyzers.get_analyzer`.

AI analysis is provider-neutral. Set `AI_PROVIDER=openai` with `OPENAI_API_KEY` and `OPENAI_MODEL`, or set `AI_PROVIDER=ollama` with `OLLAMA_BASE_URL` and `OLLAMA_MODEL`. Automated tests always use `MockAIProvider`; they never call an external AI service.
