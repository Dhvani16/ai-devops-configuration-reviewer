# AI DevOps Configuration Reviewer

A full-stack application that reviews Dockerfiles, Docker Compose files, and GitHub Actions workflows. It combines deterministic rules with schema-validated LLM findings so developers get actionable, explainable DevOps feedback.

## Project status

Phases 1–4 are complete. The project has a documented FastAPI/Next.js/PostgreSQL foundation, JWT email/password authentication, async SQLAlchemy, deterministic static analysis, and provider-neutral structured AI analysis. Configuration submission, result persistence, and frontend workflows remain intentionally deferred to their specified phases.

## Stack

- Frontend: Next.js App Router, TypeScript, Tailwind CSS
- Backend: Python 3.12+, FastAPI, Pydantic
- Database: PostgreSQL (SQLAlchemy and Alembic are introduced in Phase 2)
- Local environment: Docker and Docker Compose

## Repository layout

```text
.
├── backend/                 # FastAPI application skeleton
├── frontend/                # Next.js App Router skeleton
├── docs/                    # Architecture and development notes
├── docker-compose.yml        # Frontend, backend, and PostgreSQL services
├── .env.example             # Safe environment-variable template
└── context.md               # Project specification (source of truth)
```

## Quick start with Docker

1. Copy `.env.example` to `.env` and replace the local placeholder secrets.
2. Run `docker compose up --build`.
3. Open `http://localhost:3000` for the frontend and `http://localhost:8000/docs` for FastAPI's generated API documentation.

Run the backend migration with `cd backend; alembic upgrade head` when developing outside Docker. Docker runs this migration before starting the backend service.

## Local development

Backend (Python 3.12+):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Frontend (Node.js 20+):

```powershell
cd frontend
npm install
npm run dev
```

On Windows systems where PowerShell blocks `npm.ps1`, use `npm.cmd` instead.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Development guide](docs/DEVELOPMENT.md)
- [Security plan](docs/SECURITY.md)
- [Contribution guide](docs/CONTRIBUTING.md)
- [API plan](docs/API.md)

## Roadmap

The implementation follows the ten phases in `context.md`. The next phase connects configuration storage, deterministic analysis, AI analysis, normalization, risk scoring, and database persistence into a testable analysis pipeline.
