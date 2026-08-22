# AI DevOps Configuration Reviewer — Master Engineering Prompt

You are acting as a **senior software architect, AI engineer, Python/FastAPI developer, frontend engineer, DevOps engineer, security engineer, testing engineer, and university project mentor**.

I am a Computer Science student building this project for a university course called:

**AI Integrated Full Stack with DevOps**

The project is:

# AI DevOps Configuration Reviewer

Build this as a **real, production-style full-stack application**, not as a toy CRUD application or a simple ChatGPT wrapper.

The application should use AI as a core part of the analysis pipeline.

---

# 1. PROJECT OBJECTIVE

Build a web application where a developer can submit DevOps configuration files and receive an intelligent analysis.

The application should initially support:

- Dockerfiles
- Docker Compose files
- GitHub Actions workflow YAML files

The system should analyze configurations for:

- Security problems
- Reliability problems
- Performance issues
- Maintainability problems
- Bad DevOps practices
- Configuration mistakes
- Potential production issues
- Optimization opportunities

The application should combine:

1. Deterministic/static analysis
2. AI/LLM analysis
3. Rule-based validation
4. Structured findings
5. Risk/severity scoring
6. Human-readable explanations

AI must therefore be a **core reasoning component**, not merely a chatbot.

---

# 2. PRIMARY GOAL

Create a portfolio-quality project that demonstrates:

- Python
- FastAPI
- React/Next.js
- PostgreSQL
- Docker
- Docker Compose
- GitHub Actions
- CI/CD
- LLM integration
- Prompt engineering
- Structured AI outputs
- Static configuration analysis
- Security thinking
- REST API design
- Authentication
- Testing
- Logging
- Monitoring
- Deployment
- Good software architecture

The system must remain realistic for a solo Computer Science student.

Do NOT introduce unnecessary enterprise complexity.

---

# 3. IMPORTANT DEVELOPMENT CONSTRAINT

I have approximately:

**4 hours/week**

for approximately:

**8–12 weeks**

Therefore:

DO NOT over-engineer the application.

The MVP must be achievable by one developer.

Prefer simple, maintainable implementations over complicated infrastructure.

Do not introduce Kubernetes, microservices, Kafka, Redis, Celery, Terraform, service meshes, or other infrastructure unless there is a compelling reason.

These can be documented as future enhancements.

---

# 4. REQUIRED TECHNOLOGY STACK

## Frontend

Use:

- Next.js
- TypeScript
- Tailwind CSS

Prefer the Next.js App Router.

Use a clean component-based architecture.

Frontend responsibilities:

- Authentication UI
- Dashboard
- Configuration submission
- Analysis results
- Finding details
- Analysis history
- Configuration type selection
- Loading/error states
- Responsive design

---

# 5. BACKEND

Use:

- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL

Use asynchronous FastAPI patterns where appropriate.

Structure the backend into clear modules.

Recommended structure:

backend/

    app/

        main.py

        core/
            config.py
            security.py
            logging.py

        api/
            routes/

        models/

        schemas/

        services/

        analyzers/

        ai/

        db/

        utils/

        tests/

Do not put all application logic inside route handlers.

Use service-layer architecture.

---

# 6. DATABASE

Use PostgreSQL.

The database should store at minimum:

## User

- id
- email
- hashed_password
- created_at
- updated_at

## Project/Configuration

- id
- user_id
- name
- configuration_type
- original_content
- created_at
- updated_at

## Analysis

- id
- configuration_id
- status
- overall_score
- created_at
- completed_at

## Finding

- id
- analysis_id
- category
- severity
- title
- description
- recommendation
- line_number
- evidence
- source
- created_at

Where appropriate, use enums.

Use Alembic migrations.

Never require manual SQL database setup for normal development.

---

# 7. AUTHENTICATION

Implement basic authentication.

Use:

- Email/password
- Password hashing
- JWT authentication

Passwords must NEVER be stored in plaintext.

Protect user-specific resources.

A user must only be able to access their own configurations and analyses.

Implement:

- register
- login
- current-user endpoint

Do not implement OAuth/social login for the MVP.

---

# 8. CORE AI PIPELINE

The central workflow should be:

User submits configuration

↓

Backend identifies configuration type

↓

Deterministic parser/validator analyzes configuration

↓

Rule-based analyzer checks known issues

↓

AI analyzer receives:

- configuration
- configuration type
- deterministic findings
- relevant context

↓

LLM returns structured findings

↓

Backend validates AI output using Pydantic

↓

Findings are normalized

↓

Risk score is calculated

↓

Results stored in PostgreSQL

↓

Frontend displays results

This architecture is extremely important.

Do NOT simply send the entire user input to an LLM and display the raw response.

---

# 9. STATIC ANALYSIS

Implement deterministic analysis before AI.

## Dockerfile checks

At minimum detect things such as:

- Running as root
- Missing USER instruction
- Using latest tag
- Installing unnecessary packages
- Secrets appearing in ENV
- Secrets appearing in ARG
- Missing health check where appropriate
- Excessive image layers
- Unsafe package installation patterns
- Use of unpinned dependencies where detectable

## Docker Compose checks

Detect examples such as:

- privileged containers
- host networking
- excessive capabilities
- exposed sensitive ports
- hard-coded secrets
- missing restart policy
- dangerous volume mounts
- mounting Docker socket
- services running as root

## GitHub Actions checks

Detect examples such as:

- unpinned third-party actions
- excessive permissions
- secrets exposed through logs
- pull_request_target risks
- use of dangerous shell expressions
- missing dependency pinning
- overly broad GITHUB_TOKEN permissions
- dangerous use of user-controlled input

The initial rule engine does NOT need hundreds of rules.

Target approximately:

**5–10 meaningful rules per configuration type.**

Quality is more important than quantity.

---

# 10. AI ANALYSIS

Use an LLM through a provider abstraction.

The application should support:

## Primary

OpenAI API

## Optional local provider

Ollama

Design the AI service so the rest of the application does not depend directly on one provider.

For example:

AIProvider

    OpenAIProvider

    OllamaProvider

Use environment variables to choose the provider.

Example:

AI_PROVIDER=openai

Do not hard-code API keys.

---

# 11. STRUCTURED AI OUTPUT

The LLM must return structured JSON.

Example conceptual schema:

{
    "findings": [
        {
            "category": "security",
            "severity": "high",
            "title": "Container runs as root",
            "description": "...",
            "recommendation": "...",
            "line_number": 12,
            "evidence": "USER instruction is missing",
            "confidence": 0.94
        }
    ]
}

Use Pydantic validation.

If the model returns malformed data:

1. Attempt safe recovery if practical.
2. Otherwise mark the AI analysis as failed.
3. Do not silently store malformed results.

Do not trust LLM output blindly.

---

# 12. AI PROMPT ENGINEERING

Create dedicated prompts rather than putting prompts directly inside route handlers.

Store prompts in a maintainable location, for example:

backend/app/ai/prompts/

Use different analysis context where appropriate.

The AI should be instructed to:

- Analyze the provided configuration
- Consider deterministic findings
- Avoid inventing vulnerabilities
- Explain why an issue matters
- Provide actionable remediation
- Identify severity
- Provide confidence
- Reference relevant lines when possible
- Avoid duplicating deterministic findings unnecessarily
- Return only the required structured schema

Do not ask the AI to make unsupported claims.

---

# 13. RISK SCORING

Implement a deterministic scoring system.

For example:

Critical = 10

High = 7

Medium = 4

Low = 1

Calculate an overall score based on findings.

Do not let the LLM arbitrarily decide the final score.

The backend should calculate the final score.

Document the scoring algorithm.

---

# 14. API DESIGN

Create REST APIs.

Minimum endpoints:

## Authentication

POST /api/v1/auth/register

POST /api/v1/auth/login

GET /api/v1/auth/me

## Configurations

POST /api/v1/configurations

GET /api/v1/configurations

GET /api/v1/configurations/{id}

DELETE /api/v1/configurations/{id}

## Analysis

POST /api/v1/configurations/{id}/analyze

GET /api/v1/analyses/{id}

GET /api/v1/analyses

## Health

GET /health

GET /ready

Use proper HTTP status codes.

Use Pydantic request/response schemas.

Generate OpenAPI documentation automatically through FastAPI.

---

# 15. FRONTEND

Build a professional dashboard.

Required pages:

## Landing page

Explain:

- What the product does
- Supported configuration types
- Main benefits
- Example findings

## Login

Email/password.

## Register

Email/password.

## Dashboard

Display:

- Total analyses
- High-risk configurations
- Recent analyses
- Average score

## New Analysis

Allow user to:

- Select configuration type
- Paste configuration
- Optionally upload a file

Then submit it.

## Analysis Results

Display:

- Overall risk score
- Severity summary
- Security findings
- Reliability findings
- Performance findings
- Maintainability findings
- AI findings
- Deterministic findings

Each finding should show:

- Severity
- Category
- Title
- Description
- Evidence
- Line number
- Recommendation
- Confidence where applicable

## Analysis History

Show previous analyses.

Allow opening an analysis.

---

# 16. UI REQUIREMENTS

The UI should look like a modern developer/security tool.

Think:

- GitHub
- Vercel
- Linear
- modern DevOps dashboards

Do not make it look like a generic student CRUD application.

Use:

- clean typography
- cards
- tables
- severity badges
- code blocks
- syntax highlighting where practical
- responsive layout

Do not spend excessive time on visual effects.

Functionality comes first.

---

# 17. FILE UPLOAD SECURITY

If files are uploaded:

- Limit file size
- Validate extension
- Validate content
- Do not execute uploaded files
- Store safely
- Prevent path traversal
- Never treat uploaded configuration as executable code

Only support:

- Dockerfile
- .yml
- .yaml

for the MVP.

---

# 18. SECURITY

Implement basic application security.

Include:

- password hashing
- JWT authentication
- authorization checks
- input validation
- file validation
- request size limits
- secure configuration
- no secrets committed to Git
- safe error messages
- CORS configuration
- security headers where appropriate

Create a SECURITY.md document.

---

# 19. ENVIRONMENT MANAGEMENT

Create:

.env.example

Never commit:

.env

API keys.

Required environment variables should include something similar to:

DATABASE_URL

SECRET_KEY

JWT_ALGORITHM

ACCESS_TOKEN_EXPIRE_MINUTES

AI_PROVIDER

OPENAI_API_KEY

OLLAMA_BASE_URL

CORS_ORIGINS

Do not put real secrets into source code.

---

# 20. DOCKER

Create Dockerfiles for:

Frontend

Backend

Use Docker Compose for local development.

Expected services:

frontend

backend

postgres

Do not containerize unnecessary components.

Make sure:

docker compose up --build

can start the development environment.

Document this in README.md.

---

# 21. CI/CD

Create GitHub Actions.

At minimum:

## CI

On pull request and push:

1. Install backend dependencies
2. Run formatting/linting
3. Run backend tests
4. Build frontend
5. Run frontend linting
6. Run frontend tests if applicable
7. Build Docker images

Use:

- Ruff
- Pytest
- ESLint
- TypeScript checks

Optionally use:

- Bandit
- pip-audit
- npm audit

Do not make CI excessively slow.

---

# 22. DEPLOYMENT

Design for deployment to a simple cloud platform.

Preferred options:

Render or Railway.

The deployment should include:

Frontend

Backend

PostgreSQL

Use environment variables for production configuration.

Document deployment steps.

Do not require AWS for the MVP.

If deployment credentials cannot be configured locally, provide the exact steps needed to deploy manually.

---

# 23. LOGGING

Implement structured application logging.

Log:

- application startup
- requests
- analysis started
- analysis completed
- analysis failures
- AI provider errors

Never log:

- passwords
- JWT tokens
- API keys
- sensitive configuration secrets

Use appropriate log levels.

---

# 24. MONITORING

Implement a lightweight monitoring approach.

Backend should expose:

/health

/ready

If practical, add Prometheus-compatible metrics.

At minimum track:

- request count
- request duration
- analysis count
- analysis failures
- AI failures

Do NOT spend excessive time building a complete observability platform.

The MVP can expose metrics and document how Prometheus/Grafana could consume them.

---

# 25. TESTING

Testing is mandatory.

Backend:

- Unit tests for rule engine
- Unit tests for risk scoring
- API tests
- Authentication tests
- Authorization tests
- AI response validation tests

Frontend:

- Basic component tests where useful
- Critical user-flow tests

Integration:

Test:

configuration submission

↓

static analysis

↓

AI analysis mock

↓

risk scoring

↓

database persistence

Use mocked AI responses in automated tests.

Tests must NOT require an actual OpenAI API call.

---

# 26. AI COST CONTROL

The project must be usable without expensive AI usage.

Implement:

- small prompts
- structured outputs
- limited input size
- configurable model
- optional Ollama support
- mock AI provider for tests

Never make unnecessary LLM calls.

The static analyzer should run first.

AI should add reasoning and context rather than replacing deterministic checks.

---

# 27. DATABASE DESIGN

Use proper relationships.

Example:

User

1 → many

Configuration

1 → many

Analysis

1 → many

Finding

Use foreign keys.

Add indexes where useful.

Use timestamps.

Use migrations.

Do not store unnecessary duplicate data.

---

# 28. ERROR HANDLING

Create consistent API error responses.

Do not expose stack traces to users.

Log detailed errors server-side.

Frontend must show useful messages.

Handle:

- invalid configuration
- unsupported file
- authentication failure
- database failure
- AI failure
- timeout
- malformed AI response

gracefully.

---

# 29. DOCUMENTATION

Create:

README.md

ARCHITECTURE.md

API.md

SECURITY.md

CONTRIBUTING.md

DEVELOPMENT.md

.env.example

The README should contain:

- project overview
- problem statement
- architecture diagram
- technology stack
- setup instructions
- Docker instructions
- environment variables
- API overview
- screenshots placeholder
- testing instructions
- CI/CD explanation
- deployment instructions
- future enhancements

---

# 30. ARCHITECTURE DIAGRAM

Create an architecture diagram using Mermaid.

Example conceptual architecture:

Browser

↓

Next.js

↓

FastAPI

↓

Analysis Service

↙        ↓        ↘

Rule Engine   AI Provider   PostgreSQL

↓

Findings

↓

Dashboard

Also show:

GitHub

↓

GitHub Actions

↓

Docker Build

↓

Deployment

Improve the diagram based on the actual implementation.

---

# 31. PROJECT STRUCTURE

Use a clean monorepo structure similar to:

ai-devops-reviewer/

├── frontend/

├── backend/

├── docker/

├── .github/

│   └── workflows/

├── docs/

├── tests/

├── docker-compose.yml

├── .env.example

├── .gitignore

├── README.md

└── LICENSE

Adapt the structure if there is a strong technical reason.

---

# 32. CODE QUALITY

Follow these principles:

- SOLID where appropriate
- DRY
- separation of concerns
- type safety
- meaningful naming
- small functions
- clear modules
- no unnecessary abstraction
- no duplicated business logic

Do not create abstractions merely for the sake of demonstrating design patterns.

---

# 33. IMPORTANT: DO NOT FAKE FEATURES

Do not create buttons that do nothing.

Do not implement fake AI.

Do not display hard-coded analysis results.

Do not claim functionality that does not work.

If something cannot reasonably be implemented within the MVP, document it as a future enhancement.

---

# 34. DEVELOPMENT STRATEGY

Build the application incrementally.

DO NOT generate the entire application blindly in one step.

Use the following phases.

---

# PHASE 1 — Architecture and Repository

First inspect the existing repository.

Do not overwrite existing work without understanding it.

Create:

- repository structure
- README
- architecture documentation
- environment configuration
- Docker Compose foundation
- backend skeleton
- frontend skeleton

Verify everything starts.

---

# PHASE 2 — Backend Foundation

Implement:

- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- configuration
- logging
- health endpoints
- authentication

Add tests.

Run tests.

Fix failures.

---

# PHASE 3 — Static Analysis Engine

Implement:

Dockerfile analyzer

Docker Compose analyzer

GitHub Actions analyzer

Create a clean interface such as:

ConfigurationAnalyzer

with implementations:

DockerfileAnalyzer

ComposeAnalyzer

GitHubActionsAnalyzer

Add unit tests for every rule.

Do not add too many rules.

Focus on meaningful rules.

---

# PHASE 4 — AI Layer

Implement:

AIProvider interface

OpenAI provider

Optional Ollama provider

Prompt management

Pydantic structured response

AI analysis service

AI error handling

Mock provider for tests

Test AI integration without requiring real API calls.

---

# PHASE 5 — Analysis Pipeline

Connect:

Configuration

↓

Static Analysis

↓

AI Analysis

↓

Finding normalization

↓

Risk scoring

↓

Database persistence

Make the analysis pipeline testable.

---

# PHASE 6 — Frontend

Implement:

- authentication
- dashboard
- configuration submission
- analysis page
- results
- history

Connect frontend to real backend APIs.

Do not use mock data after API integration is complete.

---

# PHASE 7 — DevOps

Implement:

- Docker
- Docker Compose
- GitHub Actions
- linting
- tests
- Docker build
- environment management
- deployment configuration

---

# PHASE 8 — Observability and Security

Add:

- logging
- health checks
- metrics where practical
- security improvements
- rate limiting if practical
- secure headers
- validation

---

# PHASE 9 — Final Testing

Run:

backend tests

frontend tests

linting

type checks

Docker build

Docker Compose startup

API tests

security checks

Fix all obvious issues.

---

# PHASE 10 — Documentation

Finalize:

README

architecture diagram

API documentation

deployment documentation

security documentation

future roadmap

demo instructions

---

# 35. DEVELOPMENT RULES FOR CODEX

This is extremely important.

Before implementing a feature:

1. Inspect the repository.
2. Understand existing architecture.
3. Identify affected files.
4. Explain briefly what you plan to change.
5. Implement the smallest clean solution.
6. Run relevant tests.
7. Fix errors.
8. Update documentation if necessary.

Do not unnecessarily rewrite working code.

Do not introduce dependencies unless they provide clear value.

Before adding a dependency, consider whether the functionality can be implemented cleanly with the existing stack.

---

# 36. WHEN YOU ENCOUNTER ERRORS

Do not stop after encountering an error.

Investigate the root cause.

Fix it.

Run the relevant tests again.

If the problem is caused by an external service such as OpenAI:

- provide a mock implementation
- make the application still testable
- document the external dependency

Never hide failures.

---

# 37. IMPORTANT LEARNING REQUIREMENT

I am a university student.

Therefore, whenever you introduce a major architectural concept, briefly explain:

- what it does
- why we need it
- why we selected it
- what alternatives exist

Do not turn every response into a tutorial.

Keep explanations concise.

The goal is for me to understand the system rather than blindly copy code.

---

# 38. UNIVERSITY EVALUATION

The final project should clearly demonstrate:

## AI

- LLM integration
- prompt engineering
- structured AI output
- AI + deterministic analysis

## Full Stack

- Next.js
- FastAPI
- REST APIs
- PostgreSQL

## DevOps

- Docker
- Docker Compose
- GitHub Actions
- CI/CD
- deployment
- logging
- monitoring

## Software Engineering

- architecture
- testing
- authentication
- security
- documentation

---

# 39. MVP DEFINITION

The MVP is complete when a user can:

1. Register
2. Login
3. Submit a Dockerfile
4. Submit Docker Compose YAML
5. Submit GitHub Actions YAML
6. Run analysis
7. Receive deterministic findings
8. Receive AI findings
9. See severity levels
10. See recommendations
11. See an overall risk score
12. Save the analysis
13. View analysis history
14. Run the complete system through Docker Compose
15. Pass automated tests
16. Pass CI
17. Deploy the application

Everything beyond this is optional.

---

# 40. FEATURES THAT MUST NOT DELAY THE MVP

Do NOT prioritize:

- Kubernetes
- Terraform
- GitHub OAuth
- Slack integration
- GitHub App integration
- browser extensions
- mobile application
- multi-agent AI
- fine-tuning
- custom ML model training
- real-time collaboration
- complex RBAC
- billing
- payments

These are future enhancements.

---

# 41. FINAL DEMO FLOW

The final application should support a compelling demonstration:

1. Open dashboard.
2. Select Dockerfile.
3. Paste an intentionally vulnerable Dockerfile.
4. Click "Analyze".
5. Show deterministic security findings.
6. Show AI reasoning.
7. Show severity.
8. Show recommendations.
9. Show overall risk score.
10. Show analysis history.
11. Show Dockerized application.
12. Show GitHub Actions CI.
13. Show deployment.
14. Show logs/health monitoring.

The demo should take approximately 5–10 minutes.

---

# 42. IMPORTANT ENGINEERING PRINCIPLE

The most important architectural distinction is:

**Static analysis tells us what rules were violated.**

**AI explains context, identifies subtle issues, prioritizes findings, and provides reasoning/remediation.**

The system should demonstrate why combining deterministic analysis with AI is better than using an LLM alone.

---

# 43. FINAL QUALITY BAR

Before considering the project complete, verify:

- No obvious security vulnerabilities
- No hard-coded secrets
- No dead API endpoints
- No fake UI features
- No major TODOs in MVP functionality
- No failing tests
- No obvious TypeScript errors
- No obvious Python lint errors
- Docker Compose works
- Database migrations work
- Authentication works
- Authorization works
- AI failure is handled
- Static analysis works without AI
- AI output is schema validated
- README is complete
- CI works
- Deployment instructions work

---

# 44. HOW I WANT YOU TO WORK WITH ME

Do not attempt to create everything in a single response.

Work through the project phase by phase.

At the beginning of each phase:

- explain the objective
- identify the files that will be created/changed
- implement the phase

At the end:

- run tests/checks
- report what works
- report what remains
- tell me the exact next step

If you discover that a proposed feature is too ambitious for the project's 8–12 week / 4-hours-per-week constraint, explicitly say so and recommend cutting it.

Prefer a smaller working system over a large unfinished system.

---

# 45. FIRST TASK

Start now.

First inspect my current VS Code repository.

Do NOT immediately generate the entire application.

Determine:

1. What files already exist?
2. What technology is already present?
3. Whether the repository is empty or partially implemented.
4. What should be preserved.
5. What project structure you recommend.

Then propose **Phase 1**.

After that, implement Phase 1 only.

Do not proceed to Phase 2 until Phase 1 is working and verified.

At the end of Phase 1, provide:

- files created
- files modified
- commands to run
- tests/checks performed
- current project status
- next phase

Remember:

**Build a real, working, understandable university project—not a giant code dump.**