# Contributing

## Branching

- `main` — stable, always deployable
- `dev` — integration branch; merge feature branches here first
- Feature branches: `feature/<short-description>`

Open a pull request from your feature branch to `dev`. The CI pipeline (lint → tests → Docker build) must pass before merging.

## Before opening a pull request

1. Run the backend checks:
   ```bash
   cd backend
   ruff check app tests
   ruff format --check app tests
   pytest tests/ -v
   ```

2. Run the frontend checks:
   ```bash
   cd frontend
   npm run lint && npm run typecheck
   ```

3. Ensure all tests pass. Do not disable or skip tests without a documented reason.

4. Do not commit `.env`, API keys, passwords, tokens, or database data. Run `git diff --staged` before committing to verify.

## Code standards

- **Route handlers are thin.** Business logic belongs in `services/`, analysis rules in `analyzers/`, AI interaction in `ai/`.
- **New backend logic needs tests.** Add unit tests to `backend/tests/`. Use `MockAIProvider` for anything that would otherwise call a real AI provider.
- **Type everything.** Python functions use type hints; TypeScript code avoids `any`.
- **No comments explaining what the code does.** Well-named identifiers are the documentation. Add a comment only when the *why* is non-obvious (a hidden constraint, a workaround for a specific bug).

## Adding a new analysis rule

1. Open the relevant analyzer (`analyzers/dockerfile.py`, `analyzers/compose.py`, `analyzers/github_actions.py`).
2. Add a method that returns `list[Finding]`. Use the existing rule methods as a template.
3. Call the new method from `analyze()`.
4. Add a unit test in `backend/tests/test_analyzers.py` with a minimal config that triggers the rule and one that does not.

## Adding a new configuration type

1. Add the type to `FindingConfigurationType` in `backend/app/schemas/finding.py`.
2. Implement a new `ConfigurationAnalyzer` subclass in `backend/app/analyzers/`.
3. Register it in `backend/app/analyzers/factory.py`.
4. Update the AI prompt in `backend/app/ai/prompts/configuration_analysis.py`.
5. Add the type to the frontend type selector in `frontend/app/new/page.tsx`.
6. Add tests.

## Dependency policy

- Add a Python dependency only if it solves a problem that cannot be reasonably solved with the existing stack.
- Pin with `>=x.y,<(x+1).0` bounds in `pyproject.toml`.
- Add an npm dependency only when genuinely needed; prefer packages that are already in the Next.js ecosystem.
- Do not introduce Kubernetes, Redis, Celery, Terraform, or microservice infrastructure — these are documented as future enhancements.
