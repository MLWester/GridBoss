# GridBoss

GridBoss is an app-centric SaaS platform for managing sim racing leagues. The product unifies league administration, event scheduling, result tracking, Discord announcements, and Stripe based subscriptions into a single experience tailored for competitive communities.

## Current Status
- MVP scope captured in `docs/MasterSpec.md`.
- Product backlog items tracked in `docs/AppPBIs.md`.
- Repository scaffolding and services will be implemented incrementally following PBIs.

## Core Objectives
- Replace spreadsheet workflows with structured league management tools.
- Simplify event scheduling, results entry, and standings calculations.
- Keep drivers engaged using automated Discord announcements.
- Monetize through feature-gated plans and automated billing with Stripe.

## Technology Stack
- Frontend: Vite, React, TypeScript, Tailwind CSS, React Query.
- Backend: FastAPI (Python 3.11), SQLAlchemy, Alembic, Dramatiq or RQ workers.
- Data: PostgreSQL, Redis.
- Integrations: Stripe Billing, Discord OAuth2 and Bot (discord.py).
- Tooling: Docker Compose, Prettier, ESLint, Ruff, Black, Pytest, Vitest, Playwright or Cypress.

## Monorepo Layout (planned)
```
gridboss/
  frontend/
  api/
  worker/
  bot/
  infra/
  scripts/
  docs/
```
Each package will carry its own README or docs as functionality is implemented. Refer to the master spec for file-level expectations.

## Getting Started
1. Install prerequisites: Node 18+, pnpm or npm, Python 3.11, Docker Desktop.
2. Clone the repository and review `docs/MasterSpec.md` for domain context.
3. Follow PBIs in `docs/AppPBIs.md`, starting with PBI-001 to establish tooling and scaffolding.

An `.env.example` file and Docker Compose stack will be introduced in PBI-002. Until then, environment variables are documented in the master spec.

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
