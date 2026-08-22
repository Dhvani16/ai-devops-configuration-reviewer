# Security

## Current baseline

- `.env` files and common local artifacts are ignored by Git.
- `.env.example` contains placeholders, not real credentials.
- Docker Compose exposes only the frontend, backend, and local PostgreSQL ports needed for development.
- Uploaded configuration will be treated as untrusted text, never executable code.

## Planned MVP controls

Phase 2 implements Argon2 password hashing, JWT authentication, authorization checks for the current-user route, validated settings, and a CORS allow-list. Subsequent phases add upload size/type validation, AI-output validation, security headers, and authorization checks for user-owned configurations and analyses.

## Reporting a vulnerability

Do not include secrets or exploit details in public issues. Contact the repository maintainer privately with reproduction steps and the affected version.
