# GridBoss
[![CI](https://github.com/GridBoss/GridBoss/actions/workflows/ci.yml/badge.svg)](https://github.com/GridBoss/GridBoss/actions/workflows/ci.yml)

GridBoss is an app-centric SaaS platform for managing sim racing leagues. The product unifies league administration, event scheduling, result tracking, Discord announcements, and Stripe based subscriptions into a single experience tailored for competitive communities.

## Current Status
- MVP scope captured in `docs/MasterSpec.md`.
- Product backlog items tracked in `docs/AppPBIs.md`.
- Repository scaffolding, tooling, environment templates, and Docker stack established under PBIs 001-002.

## Core Objectives
- Replace spreadsheet workflows with structured league management tools.
- Simplify event scheduling, results entry, and standings calculations.
- Keep drivers engaged using automated Discord announcements.
- Monetize through feature-gated plans and automated billing with Stripe.

## Technology Stack
- Frontend: Vite, React, TypeScript, Tailwind CSS, React Query.
- Backend: FastAPI (Python 3.11+), SQLAlchemy, Alembic, Dramatiq or RQ workers.
- Data: PostgreSQL, Redis.
- Integrations: Stripe Billing, Discord OAuth2 and Bot (discord.py).
- Tooling: Docker Compose, Prettier, ESLint, Ruff, Black, Pytest, Vitest, Playwright or Cypress.

## Monorepo Layout
```
gridboss/
  frontend/   # React app
  api/        # FastAPI service
  worker/     # Background job processors
  bot/        # Discord bot service
  infra/      # Docker, deployment, IaC
  scripts/    # Automation scripts
  docs/       # Specs, API docs, prompts
```
Each package will carry its own README or docs as functionality is implemented. Refer to the master spec for file-level expectations.

## Getting Started
1. Install prerequisites: Node 18+, npm 10+, Python 3.11+, Docker Desktop (enable WSL2 integration on Windows).
2. Clone the repository and review `docs/MasterSpec.md` for domain context.
3. Copy environment defaults and customise as needed:
   ```powershell
   Copy-Item .env.example .env
   ```
   - This file is consumed by the API, worker, bot, and Docker Compose services.
4. Bootstrap the frontend:
   ```powershell
   cd frontend
   npm install
   npm run lint
   npm run format
   ```
5. Bootstrap the API service and worker dependencies:
   ```powershell
   cd ..\api
   python -m venv .venv
   .venv\Scripts\pip install -r requirements-dev.txt
   .venv\Scripts\ruff check
   .venv\Scripts\black --check .
   cd ..\worker
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```
6. Follow PBIs in `docs/AppPBIs.md`, starting with `pbi/002-env-and-docker` for environment parity.
7. Configuration reference lives in `docs/CONFIG.md`; review before deploying to new environments.

## Docker Development Stack
The Docker Compose setup lives in `infra/docker-compose.yml` and mirrors the production topology.

1. Ensure `.env` exists (see step 3 above) so services share configuration.
2. Start the stack from the repository root:
   ```powershell
   docker compose --env-file .env -f infra/docker-compose.yml up --build
   ```
3. Visit the frontend at `http://localhost:5173` and the API health check at `http://localhost:8000/healthz`. Service readiness (database, Redis, migrations) is exposed at `http://localhost:8000/readyz`.
4. Optional Stripe CLI forwarding can be enabled via the `stripe` profile:
   ```powershell
   docker compose --env-file .env -f infra/docker-compose.yml --profile stripe up stripe-cli
   ```

Services provided:
- `frontend`: Vite dev server with hot reload and Tailwind.
- `api`: FastAPI app served by Uvicorn.
- `worker`: Placeholder Python process ready for Dramatiq/RQ wiring.
- `bot`: Placeholder Discord bot process.
- `db`: PostgreSQL 16 with persistent Docker volume.
- `redis`: Redis 7 for cache, queues, and rate limiting.
- `stripe-cli`: Optional webhook forwarding helper.

Stop the stack with `docker compose --env-file .env -f infra/docker-compose.yml down`.

## Running Tests
- **Backend (FastAPI)**:
  ```powershell
  $env:PYTHONPATH = 'api'
  .\api\.venv\Scripts\ruff check api
  .\api\.venv\Scripts\black --check api
  .\api\.venv\Scripts\pytest
  ```
  Pytest emits coverage via `pytest-cov` (see `coverage.xml`) and mirrors the CI job.
- **Frontend (React/Vite)**:
  ```powershell
  cd frontend
  npm run lint
  npm run format
  npm run test
  npm run test:coverage
  npm run build
  ```
 Use `npm run test:watch` for interactive development and `npm run test:e2e` once Playwright fixtures are populated.
- **End-to-end**: Playwright config lives at `frontend/playwright.config.ts`; tests expect the Docker stack to be running locally.

## Pre-commit Hooks & Secret Scanning
- Install the shared hooks once per machine:
  ```powershell
  python -m pip install pre-commit
  pre-commit install
  ```
  Hooks run Ruff (lint), Black (format), ESLint, and Prettier before every commit.
- To run hooks across the whole repo manually, execute `pre-commit run --all-files`.
- Scan for leaked secrets locally with the helper script:
  - Unix/macOS: `./scripts/gitleaks-scan.sh`
  - Windows PowerShell: `./scripts/gitleaks-scan.ps1`
  The script uses a local `gitleaks` binary when available and falls back to Docker.

## Tooling Commands
- Frontend lint: `npm run lint`
- Frontend format check: `npm run format`
- Frontend format write: `npm run format:fix`
- API lint: `.venv\Scripts\ruff check`
- API format: `.venv\Scripts\black .`
- API unit tests (placeholder): `.venv\Scripts\pytest`

## Transactional Email
- Enable transactional email by supplying `EMAIL_ENABLED=true`, `SENDGRID_API_KEY=<key>`, and `EMAIL_FROM_ADDRESS=<verified@domain>` in `.env` (or your deployment secrets). The worker automatically prefers SendGrid when both SMTP and SendGrid credentials are present.
- Verify your sending domain with SendGrid (SPF include, DKIM CNAMEs, optional DMARC record). Deployment checklists should confirm the DNS status is “verified” before flipping `EMAIL_ENABLED` in production.
- Run `pytest gridboss_email` to exercise the provider adapters. To perform an end-to-end smoke test, start the stack (`docker compose ... up`), open a Python shell, and call:
  ```python
  from app.services.email import queue_transactional_email
  queue_transactional_email(
      template_id="welcome",
      recipient="sandbox@example.com",
      context={"display_name": "Driver", "app_url": "https://app.grid-boss.com"},
  )
  ```
  Check SendGrid’s activity log for the delivery and inspect the `audit_logs` table for the `email_sent` entry.

## Deployment Notes
- **Container Builds**: Production images are defined in `infra/`. Inject secrets (Stripe, Discord, database) via your deployment platform instead of committing them to `.env`.
- **Database Migrations**: Use Alembic (`api/alembic.ini`). From `api/`, run `alembic revision --autogenerate -m "<summary>"` then `alembic upgrade head` before promoting a release.
- **Static Assets**: `npm run build` outputs to `frontend/dist/`; serve this folder via CDN or static hosting in production.
- **Observability**: Set `SENTRY_DSN`, `OTEL_ENABLED=true`, and `OTEL_EXPORTER_ENDPOINT` in production manifests to emit telemetry.
- **Rollbacks**: Maintain database backups alongside release tags; if rollout fails, redeploy the previous image and run `alembic downgrade` to the prior revision.

## Development Workflow
- Work progresses PBI by PBI. Create a feature branch matching the branch name listed in the backlog (for example `pbi/002-env-and-docker`).
- Complete the acceptance criteria, validate locally (npm/pytest + docker where relevant), then open a pull request targeting `main`.
- Update `docs/AppPBIs.md` status and changelog entries as PBIs close.

## Testing and Quality Gates
- Unit, integration, and end-to-end tests will be established across backend and frontend PBIs (see PBI-020 and PBI-034).
- CI workflow (`.github/workflows/ci.yml`) runs frontend/backend lint, formatting checks, unit tests with coverage, and builds on pushes to `main` and all pull requests, uploading coverage artifacts for review.
- Performance benchmarks (PBI-036) ensure standings and job queue SLOs are met.

## Documentation
- `docs/MasterSpec.md` is the source of truth for product and technical requirements.
- `docs/AppPBIs.md` lists the actionable backlog and branch plan.
- Additional documents such as API references, ERDs, and performance notes will be added as PBIs deliver them.

## Contributing
- Follow coding standards defined in the master spec (formatters, linting, test coverage).
- Use Conventional Commits when preparing commit messages.
- Ensure audit logging, observability, and security considerations are addressed per acceptance criteria where applicable.
- Run the CI-equivalent checks before opening a PR: `npm run lint`, `npm run format`, `npm run test:coverage`, `npm run build` from `frontend/`, and `ruff check`, `black --check`, `pytest` (coverage enabled) from `api/`.

For questions or clarifications, update the relevant PBI or expand the documentation so decisions remain transparent to the team.
## Observability Configuration
- Logs are emitted as structured JSON and include `X-Request-ID`, `user_id`, and `league_id` context where available.
- Set `SENTRY_DSN` and optional `SENTRY_TRACES_SAMPLE_RATE` to forward API/worker exceptions to Sentry. The worker automatically adopts the same DSN and app environment.
- Frontend telemetry is controlled via Vite env keys: `VITE_SENTRY_DSN` and optional `VITE_SENTRY_TRACES_SAMPLE_RATE`. When unset, the bundle skips Sentry at runtime.
- Enable OpenTelemetry exports with `OTEL_ENABLED=true` and optionally configure `OTEL_EXPORTER_ENDPOINT` and `OTEL_SERVICE_NAME`. The worker reports spans using the same configuration (it suffixes `-worker` to the service name).
- Configure health check caching with `HEALTH_CACHE_SECONDS` to reduce probe load; the default disables caching for immediate feedback.
