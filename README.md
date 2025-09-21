# GridBoss

GridBoss is an app-centric SaaS platform for managing sim racing leagues. The product unifies league administration, event scheduling, result tracking, Discord announcements, and Stripe based subscriptions into a single experience tailored for competitive communities.

## Current Status
- MVP scope captured in `docs/MasterSpec.md`.
- Product backlog items tracked in `docs/AppPBIs.md`.
- Repository scaffolding, tooling, and baseline services established under PBI-001.

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
  worker/     # Background job processors (future PBI)
  bot/        # Discord bot (future PBI)
  infra/      # Docker, deployment, IaC
  scripts/    # Automation scripts
  docs/       # Specs, API docs, prompts
```
Each package will carry its own README or docs as functionality is implemented. Refer to the master spec for file-level expectations.

## Getting Started
1. Install prerequisites: Node 18+, npm 10+, Python 3.11+, Docker Desktop.
2. Clone the repository and review `docs/MasterSpec.md` for domain context.
3. Bootstrap the frontend:
   ```powershell
   cd frontend
   npm install
   npm run lint
   npm run format
   ```
4. Bootstrap the API service:
   ```powershell
   cd ..\api
   python -m venv .venv
   .venv\Scripts\pip install -r requirements-dev.txt
   .venv\Scripts\ruff check
   .venv\Scripts\black --check .
   ```
5. Follow PBIs in `docs/AppPBIs.md`, starting with `pbi/001-foundation-tooling` for scaffolding.

Docker Compose, environment templates, and additional services arrive with future PBIs.

## Tooling Commands
- Frontend lint: `npm run lint`
- Frontend format check: `npm run format`
- Frontend format write: `npm run format:fix`
- API lint: `.venv\Scripts\ruff check`
- API format: `.venv\Scripts\black .`
- API unit tests (placeholder): `.venv\Scripts\pytest`

## Development Workflow
- Work progresses PBI by PBI. Create a feature branch matching the branch name listed in the backlog (for example `pbi/001-foundation-tooling`).
- Complete the acceptance criteria, validate locally, then open a pull request targeting `main`.
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

