# Development guide

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Docker Desktop | latest | Required for Docker Compose workflow |
| Python | 3.12+ | Backend only |
| Node.js | 22+ | Frontend only |
| Git | any | |

Python and Node.js are only needed for local development outside Docker. The Docker Compose workflow requires only Docker Desktop.

## Environment configuration

```bash
cp .env.example .env
```

Open `.env` and set:
- `SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- `OPENAI_API_KEY` — only required if `AI_PROVIDER=openai` (the default)
- Leave PostgreSQL variables as-is for local Docker development

Optional integrations (leave blank to disable):
- `SLACK_WEBHOOK_URL` — Slack incoming webhook URL for analysis completion notifications
- `SCHEDULED_REANALYSIS_INTERVAL_HOURS` — positive integer to enable scheduled re-analysis
- `GRAFANA_ADMIN_PASSWORD` — Grafana admin password (default: `admin`)

Never commit `.env`.

## Start with Docker (recommended)

```bash
docker compose up --build
```

This starts PostgreSQL, runs Alembic migrations, starts the FastAPI backend, builds and starts the Next.js frontend, and starts Prometheus and Grafana.

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Prometheus metrics | http://localhost:8000/metrics |
| Prometheus UI | http://localhost:9090 |
| Grafana | http://localhost:3001 |

Stop with `docker compose down`. Use `docker compose down -v` only if you want to wipe the local PostgreSQL data volume.

## Local backend development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head             # run once; DATABASE_URL must point to a running PostgreSQL
uvicorn app.main:app --reload
```

The backend reads `.env` from the `backend/` directory if present, or from environment variables. For local development, copy the relevant variables from the root `.env` to `backend/.env`, or export them in your shell.

## Local frontend development

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

## AI provider configuration

### OpenAI (default)

```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini     # or any chat model
```

### Ollama (local, no API key)

```bash
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

Install [Ollama](https://ollama.com) and pull the model: `ollama pull llama3.2`.

When running via Docker Compose, use `OLLAMA_BASE_URL=http://host.docker.internal:11434` to reach a locally running Ollama instance.

## Running tests

```bash
cd backend
pytest tests/ -v
```

All 90 tests use an in-memory SQLite database and `MockAIProvider`. No OpenAI key, Ollama installation, or running PostgreSQL is needed.

## Linting and formatting

```bash
# Backend
cd backend
ruff check app tests        # lint
ruff format app tests       # auto-format
ruff format --check app tests  # CI-style format check

# Frontend
cd frontend
npm run lint
npm run typecheck
```

## Database migrations

Migrations live in `backend/migrations/versions/`. To create a new migration after changing a model:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Review auto-generated migrations before committing — Alembic does not always detect all changes correctly.

## Project structure

```text
.
├── .github/workflows/ci.yml   — GitHub Actions CI
├── backend/
│   ├── app/                   — FastAPI application
│   │   ├── analyzers/         — Static rule engines (dockerfile, compose, github_actions, kubernetes, terraform)
│   │   ├── services/          — Business logic (pipeline, sarif, notifications, scheduler)
│   │   └── ...
│   ├── migrations/            — Alembic migration scripts
│   ├── tests/                 — pytest test suite (90 tests)
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── app/                   — Next.js App Router pages
│   ├── components/            — Shared React components
│   ├── lib/                   — API client and TypeScript types
│   ├── Dockerfile
│   └── package.json
├── observability/
│   ├── prometheus.yml         — Prometheus scrape config
│   └── grafana/
│       └── provisioning/      — Auto-provisioned datasource and starter dashboard
├── docs/                      — Architecture, API, Security, Contributing
├── docker-compose.yml
├── .env.example
└── README.md
```
