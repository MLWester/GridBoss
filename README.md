# GridBoss

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
1. Install prerequisites: Node 18+, npm 10+, Python 3.11+, Docker Desktop.
2. Clone the repository and review `docs/MasterSpec.md` for domain context.
3. Copy environment defaults and customise as needed:
   ```powershell
   Copy-Item .env.example .env
   ```
4. Bootstrap the frontend:
   ```powershell
   cd frontend
   npm install
   npm run lint
   npm run format
   ```
5. Bootstrap the API service:
   ```powershell
   cd ..\api
   python -m venv .venv
   .venv\Scripts\pip install -r requirements-dev.txt
   .venv\Scripts\ruff check
   .venv\Scripts\black --check .
   ```
6. Follow PBIs in `docs/AppPBIs.md`, starting with `pbi/002-env-and-docker` for environment parity.

## Docker Development Stack
The Docker Compose setup lives in `infra/docker-compose.yml` and mirrors the production topology.

1. Ensure `.env` exists (see step 3 above) so services share configuration.
2. Start the stack from the repository root:
   ```powershell
   docker compose --env-file .env -f infra/docker-compose.yml up --build
   ```
3. Visit the frontend at `http://localhost:5173` and the API health check at `http://localhost:8000/healthz`.
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

## Tooling Commands
- Frontend lint: `npm run lint`
- Frontend format check: `npm run format`
- Frontend format write: `npm run format:fix`
- API lint: `.venv\Scripts\ruff check`
- API format: `.venv\Scripts\black .`
- API unit tests (placeholder): `.venv\Scripts\pytest`

## Development Workflow
- Work progresses PBI by PBI. Create a feature branch matching the branch name listed in the backlog (for example `pbi/002-env-and-docker`).
- Complete the acceptance criteria, validate locally (npm/pytest + docker where relevant), then open a pull request targeting `main`.
- Update `docs/AppPBIs.md` status and changelog entries as PBIs close.

## Testing and Quality Gates
- Unit, integration, and end-to-end tests will be established across backend and frontend PBIs (see PBI-020 and PBI-034).
- CI workflows (PBI-035) will run linting, tests, and builds on every pull request.
- Performance benchmarks (PBI-036) ensure standings and job queue SLOs are met.

## Documentation
- `docs/MasterSpec.md` is the source of truth for product and technical requirements.
- `docs/AppPBIs.md` lists the actionable backlog and branch plan.
- Additional documents such as API references, ERDs, and performance notes will be added as PBIs deliver them.

## Contributing
- Follow coding standards defined in the master spec (formatters, linting, test coverage).
- Use Conventional Commits when preparing commit messages.
- Ensure audit logging, observability, and security considerations are addressed per acceptance criteria where applicable.

For questions or clarifications, update the relevant PBI or expand the documentation so decisions remain transparent to the team.