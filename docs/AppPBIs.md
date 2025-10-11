# GridBoss Product Backlog

## PBI-001 - Platform Foundation and Tooling (complete)
Summary: Establish the monorepo scaffold with baseline tooling and shared configuration.
Scope: Backend, Frontend, Ops
Acceptance Criteria:
- Monorepo directory structure created per Master Spec with placeholder README files where needed.
- Frontend package.json (Vite React TS Tailwind) initialized and backend Python project configured with Poetry or pip tools.
- Prettier, ESLint, Ruff, Black, and EditorConfig configured with lint and format commands documented in README.
Dependencies: none
Branch: pbi/001-foundation-tooling

## PBI-002 - Environment Configuration and Docker (complete)
Summary: Provide environment variable templates and Docker Compose for local development parity.
Scope: Backend, Frontend, Ops
Acceptance Criteria:
- .env.example populated with every variable listed in Master Spec with sensible development defaults and inline comments.
- docker-compose.yml defines frontend, api, worker, bot, postgres, redis, and optional stripe-cli services with health checks and shared volumes for hot reload.
- Documentation in README explains how to boot the stack, override env vars, and connect to backing services.
Dependencies: PBI-001
Branch: pbi/002-env-and-docker

## PBI-003 - Database Schema and ORM Baseline (complete)
Summary: Implement the SQLAlchemy models and migration tooling for core domain tables.
Scope: Backend
Acceptance Criteria:
- SQLAlchemy models defined for users, leagues, memberships, teams, drivers, seasons, events, points_schemes, points_rules, results, integrations_discord, billing_accounts, subscriptions, and audit_logs.
- Alembic configured with env.py and script location, plus an initial migration creating all tables, enums, indexes, and constraints described in the spec.
- Database session management module with dependency wiring for FastAPI routes and basic migration smoke test in CI or docs.
Dependencies: PBI-001, PBI-002
Branch: pbi/003-db-schema

## PBI-004 - Authentication and Session Service (complete)
Summary: Deliver Discord OAuth login, JWT issuance, and session management endpoints.
Scope: Backend, Frontend
Acceptance Criteria:
- GET /auth/discord/start redirects to Discord with PKCE and state, and callback exchanges code for tokens using Discord HTTP client.
- Access and refresh JWTs generated with configured TTLs, refresh token stored as HttpOnly Secure cookie, and POST /logout clears session.
- GET /me returns user profile, memberships, and billing plan using authenticated context with unit tests covering success and failure cases.
Dependencies: PBI-003
Branch: pbi/004-auth-sessions

## PBI-005 - RBAC and Membership Management (complete)
Summary: Implement league membership roles and enforcement helpers.
Scope: Backend
Acceptance Criteria:
- Membership CRUD endpoints invite existing users, update roles, and remove members respecting unique per league constraint.
- Route dependency or decorator verifying role entitlements for OWNER, ADMIN, STEWARD, DRIVER according to spec matrix.
- Tests covering unauthorized access, role upgrades, and ensuring OWNER cannot be demoted when they are the billing contact.
Dependencies: PBI-004
Branch: pbi/005-rbac-memberships

## PBI-006 - League Management API (Still needs to be completed)
Summary: Provide CRUD operations for leagues including default season creation and soft delete.
Scope: Backend
Acceptance Criteria:
- POST /leagues creates league with unique slug, associates requesting user as OWNER, and auto-creates default active season.
- GET, PATCH, DELETE endpoints return league data, support updates to name and slug, and implement soft delete with seven day restore window.
- Business validation ensures plan limits are enforced via driver_limit and audit placeholder events recorded for changes.
Dependencies: PBI-005
Branch: pbi/006-league-api

## PBI-007 - Drivers and Teams API (complete)
Summary: Manage league drivers and teams with bulk operations.
Scope: Backend
Acceptance Criteria:
- POST /leagues/{id}/drivers accepts bulk payload with validation for unique display_name per league and optional team assignment.
- Team CRUD endpoints provide create, update, delete with unique name per league and handle reassignment when deleting a team.
- Responses include linked user or discord_id metadata and errors use standard envelope when conflicts occur.
Dependencies: PBI-006
Branch: pbi/007-drivers-teams

## PBI-008 - Seasons and Points Scheme Management (complete)
Summary: Control season lifecycle and customizable points tables per league.
Scope: Backend
Acceptance Criteria:
- Season endpoints allow create, update, and activate ensuring exactly one active season per league at a time.
- Points scheme CRUD supports default F1 seed, editing position to points map, and toggling is_default flag per season.
- Validation prevents deletion of active scheme if referenced by events and updates cascade to future calculations.
Dependencies: PBI-006, PBI-003
Branch: pbi/008-seasons-points

## PBI-009 - Events Scheduling API (complete)
Summary: Enable creation and management of league events with timezone aware responses.
Scope: Backend
Acceptance Criteria:
- POST /leagues/{id}/events records UTC start_time and optional laps or distance, enforcing per-league uniqueness constraints where applicable.
- GET endpoints filter by status (SCHEDULED, COMPLETED, CANCELED) and return local time when tz query param supplied.
- PATCH and DELETE support updating details and canceling with audit trail hooks and validation against past completed events.
Dependencies: PBI-008
Branch: pbi/009-events-api

## PBI-010 - Background Worker Framework (complete)
Summary: Stand up the asynchronous job runner with Redis-backed queues.
Scope: Backend, Ops
Acceptance Criteria:
- Dramatiq or RQ configured with Redis connection, serializer, and retries per spec with exponential backoff up to five attempts.
- Worker service entrypoint created under worker/main.py consuming annotated jobs and packaged for docker-compose execution.
- Health monitoring or logs confirm worker starts successfully and processes a sample job in development.
Dependencies: PBI-002, PBI-003
Branch: pbi/010-worker-framework

## PBI-011 - Results Processing API (complete)
Summary: Accept race results, compute points, and enqueue downstream jobs.
Scope: Backend
Acceptance Criteria:
- POST /events/{id}/results accepts entries array with finish positions, bonus, penalty, and enforces Idempotency-Key stored in Redis with ttl.
- Total points calculation uses active points scheme, applies bonus and penalty, clamps at zero, and persists per driver result.
- Successful submissions enqueue recompute_standings and announce_results jobs; tests cover idempotent replay and invalid data.
Dependencies: PBI-009, PBI-008, PBI-010
Branch: pbi/011-results-processing

## PBI-012 - Standings Service and Cache (complete)
Summary: Provide season standings aggregation with caching and tie breakers.
Scope: Backend
Acceptance Criteria:
- Standings query sums total_points per driver within a season, counts wins, determines best finish, and orders by spec tie break rules.
- Redis cache layer stores standings per season_id with 300 second ttl and invalidates on results create, update, or delete.
- GET /leagues/{id}/standings?seasonId=uuid returns cached structure with tests covering tie scenarios and cache behavior.
Dependencies: PBI-011
Branch: pbi/012-standings-service

## PBI-013 - Discord Integration API (complete)
Summary: Allow leagues to link Discord guilds and configure announcement channels.
Scope: Backend
Acceptance Criteria:
- POST /leagues/{id}/discord/link validates requester role, stores guild_id and channel_id, and marks integration active.
- Test endpoint enqueues announcement job gated to Pro plan and handles missing permissions or inactive bot states gracefully.
- Integration records stored in integrations_discord table with installed_by_user tracking and audit entries created.
Dependencies: PBI-006, PBI-010, PBI-017
Branch: pbi/013-discord-integration-api

## PBI-014 - Discord Bot Service (complete)
Summary: Build the discord.py bot that handles slash commands and queue driven announcements.
Scope: Backend, Ops
Acceptance Criteria:
- Bot registers /gridboss link and /gridboss test slash commands with Discord and validates permissions before responding.
- Worker consumption formats event and results embeds and posts to configured channel with retry handling for rate limits.
- Failure scenarios mark integration inactive and emit audit logs with structured logging to Sentry.
Dependencies: PBI-013, PBI-010
Branch: pbi/014-discord-bot

## PBI-015 - Stripe Checkout and Portal API (complete)
Summary: Implement subscription checkout and customer portal endpoints.
Scope: Backend
Acceptance Criteria:
- POST /billing/checkout creates or reuses Stripe customer, initiates Checkout Session for Pro or Elite using env price ids, and returns url.
- POST /billing/portal creates billing portal session for authenticated OWNER and returns url with error handling for missing Stripe customer id.
- Billing accounts persisted with plan, driver limits updated on plan change, and business errors returned with structured envelope.
Dependencies: PBI-004, PBI-003
Branch: pbi/015-stripe-checkout

## PBI-016 - Stripe Webhooks and Plan Sync (complete)
Summary: Process Stripe webhook events to align subscription state and grace periods.
Scope: Backend
Acceptance Criteria:
- POST /webhooks/stripe verifies signature using STRIPE_WEBHOOK_SECRET and handles checkout.session.completed, customer.subscription.updated, customer.subscription.deleted, and invoice.payment_failed.
- Webhook handler updates billing_accounts and subscriptions tables, sets current_period_end, and schedules sync_plan_from_stripe job when needed.
- Idempotency for Stripe events stored to prevent double processing with tests covering success, replay, and signature failure.
Dependencies: PBI-015, PBI-010
Branch: pbi/016-stripe-webhooks

## PBI-017 - Plan Enforcement Middleware (complete)
Summary: Enforce plan entitlements and driver limits across gated routes.
Scope: Backend
Acceptance Criteria:
- Decorator @requires_plan(plan) enforces minimum plan on routes, returning business error {code:"PLAN_LIMIT"} when unmet.
- Driver limit checks on driver creation or updates compare against league limits and include seven day grace period after downgrade.
- Discord test endpoint and other gated features respect plan middleware with comprehensive unit tests.
Dependencies: PBI-006, PBI-015, PBI-016
Branch: pbi/017-plan-enforcement

## PBI-018 - Audit Logging Service (complete)
Summary: Capture audit events for key domain changes and expose retrieval API.
Scope: Backend
Acceptance Criteria:
- Audit utility records league settings changes, points edits, Discord link events, billing updates, and result overrides with before and after payloads.
- Background jobs and bot interactions emit audit entries on failures such as missing permissions or plan downgrades.
- Admin endpoint provides paginated audit logs filtered by league with tests ensuring sensitive fields are redacted when necessary.
Dependencies: PBI-006, PBI-011, PBI-017
Branch: pbi/018-audit-logging

## PBI-019 - Observability and Health Endpoints (complete)
Summary: Add structured logging, tracing hooks, and service health probes.
Scope: Backend, Ops
Acceptance Criteria:
- JSON logging includes x-request-id, user_id, league_id when available, and integrates with Sentry for exceptions.
- /healthz and /readyz endpoints report database, Redis connectivity, and migration status with optional caching.
- Optional OpenTelemetry instrumentation scaffolding added with environment toggle and documented configuration.
Dependencies: PBI-003, PBI-010
Branch: pbi/019-observability

## PBI-020 - Backend Automated Test Suite (complete)
Summary: Establish pytest-based unit and integration tests for critical services.
Scope: Backend
Acceptance Criteria:
- Pytest configuration with fixtures for database session, Redis, and Stripe or Discord clients using mocks.
- Tests cover points calculation edge cases, standings ordering tie breakers, RBAC guards, idempotency storage, and Stripe webhook flows.
- CI target ensures tests run in docker-compose or CI with coverage thresholds documented.
Dependencies: PBI-011, PBI-012, PBI-017
Branch: pbi/020-backend-tests

## PBI-021 - Seed and Demo Data Script (complete)
Summary: Provide idempotent script to populate demo league data.
Scope: Backend
Acceptance Criteria:
- scripts/seed_demo.py creates demo user, league, drivers, events, results, and standings per spec using upsert semantics.
- Command line interface or Makefile target documented for running seed script locally.
- Verification step ensures rerunning script does not duplicate records and logs summary output.
Dependencies: PBI-011, PBI-012
Branch: pbi/021-seed-data

## FRONTEND --------------------------------------------------------------------
## PBI-022 - Frontend Shell and Auth Flow (complete)
Summary: Build React shell with routing, state, and authentication handling.
Scope: Frontend
Acceptance Criteria:
- Vite React TypeScript project configured with Tailwind, React Query, and base layout components.
- Public routes include /login with Discord OAuth button and post-login fetch to /me storing user context.
- ProtectedRoute wrapper enforces auth for app routes and handles loading, error, and refresh token renewal flows.
Dependencies: PBI-004
Branch: pbi/022-frontend-shell

## PBI-023 - Dashboard Page
Summary: Implement main dashboard listing leagues and plan status.
Scope: Frontend
Acceptance Criteria:
- /dashboard fetches leagues, displays role badges, and renders create league CTA with modal handling slug validation errors.
- Plan summary card shows current plan, limits, and upgrade button linking to billing flow when appropriate.
- Loading, empty, and error states covered with visuals aligned to professional sim racing aesthetic.
Dependencies: PBI-022, PBI-006
Branch: pbi/023-dashboard

## PBI-024 - League Overview Page
Summary: Deliver league home overview with tabs and key widgets.
Scope: Frontend
Acceptance Criteria:
- Layout with tabs for Overview, Drivers, Teams, Events, Standings, Settings using router aware components.
- Overview tab shows next event local time, last results summary, and Discord link prompt if plan allows.
- State management handles skeleton loading, empty league, and error toasts.
Dependencies: PBI-022, PBI-009, PBI-011
Branch: pbi/024-league-overview

## PBI-025 - Drivers Management UI
Summary: Build drivers tab with roster table and bulk import flow.
Scope: Frontend
Acceptance Criteria:
- Drivers table displays display name, team, linked user indicators, and actions respecting role entitlements.
- Bulk paste modal parses textarea input, previews new drivers, highlights conflicts, and submits via bulk API.
- Inline edit forms support updating driver name or team with optimistic updates and rollback on failure.
Dependencies: PBI-024, PBI-007
Branch: pbi/025-drivers-ui

## PBI-026 - Teams Management UI
Summary: Provide CRUD interface for teams and driver assignments.
Scope: Frontend
Acceptance Criteria:
- Teams list displays name, driver count, and edit or delete controls gated to ADMIN or OWNER roles.
- Create and edit dialogs allow assigning drivers with multi-select, updating roster view in sync.
- Deleting a team prompts confirmation and handles driver reassignment to null with success feedback.
Dependencies: PBI-024, PBI-007
Branch: pbi/026-teams-ui

## PBI-027 - Events Management UI
Summary: Manage event creation, list, and editing with timezone support.
Scope: Frontend
Acceptance Criteria:
- Events tab includes list segmented into upcoming and completed with local time display and status pills.
- Create or edit form captures name, track, datetime picker using league default timezone, laps, distance, and handles validation errors.
- Cancel and delete actions gated to proper roles with confirmation and audit toast messaging.
Dependencies: PBI-024, PBI-009
Branch: pbi/027-events-ui

## PBI-028 - Event Results UI
Summary: Allow stewards to enter race results with drag ordering and modifiers.
Scope: Frontend
Acceptance Criteria:
- Results tab provides drag-and-drop ordering for finish positions, inputs for bonus and penalty points, and status dropdown.
- Submission attaches unique Idempotency-Key header per request and shows success toast plus triggers standings refetch.
- Error handling highlights validation issues from API including PLAN_LIMIT and displays fallback when worker queue delays occur.
Dependencies: PBI-027, PBI-011, PBI-012
Branch: pbi/028-results-ui

## PBI-029 - Standings UI
Summary: Present season standings with tie break indicators and sharing.
Scope: Frontend
Acceptance Criteria:
- Standings tab fetches standings API, displays table with points, wins, best finish, and podium highlight styling.
- Season selector allows switching seasons and updates via React Query while preserving scroll position.
- Share standings button copies deep link or opens modal with shareable summary stub.
Dependencies: PBI-024, PBI-012
Branch: pbi/029-standings-ui

## PBI-030 - Settings General and Points UI
Summary: Support league settings updates and points table editing.
Scope: Frontend
Acceptance Criteria:
- Settings General form allows updating name and slug with inline validation and optimistic UI.
- Points Scheme editor renders editable table for positions 1..10 with ability to reset to default F1.
- Save operations surface success and error toasts, handling plan restrictions and audit confirmations.
Dependencies: PBI-024, PBI-008
Branch: pbi/030-settings-general-points

## PBI-031 - Discord Integration UI
Summary: Deliver UI for linking Discord guilds and testing announcements.
Scope: Frontend
Acceptance Criteria:
- Settings Discord section walks OWNER or ADMIN through linking flow including launch of Discord OAuth window.
- Displays current guild and channel with status badges, provides Test Post button gated to Pro plan with descriptive tooltip otherwise.
- Handles error scenarios such as missing bot permissions and updates integration state on success.
Dependencies: PBI-030, PBI-013
Branch: pbi/031-discord-ui

## PBI-032 - Billing UI
Summary: Implement billing page and upgrade actions.
Scope: Frontend
Acceptance Criteria:
- Billing view shows current plan, driver limit usage, and upgrade buttons that call /billing/checkout for selected plan.
- Manage subscription button opens Stripe portal via API response with loading state and error handling.
- Grace period messaging displayed when downgrade pending and plan restricted actions show tooltip referencing upgrade path.
Dependencies: PBI-023, PBI-015, PBI-017
Branch: pbi/032-billing-ui

## PBI-033 - Admin Console MVP
Summary: Build founder-only console to monitor users, leagues, and subscriptions.
Scope: Frontend, Backend
Acceptance Criteria:
- ADMIN_MODE flag hides console unless enabled and user has founder role.
- Console provides search across users and leagues, displays subscription status, and allows toggling Discord integration active flag.
- Dev-only action to override plan documented and guarded, with audit log entries for each change.
Dependencies: PBI-018, PBI-017, PBI-032
Branch: pbi/033-admin-console

## PBI-034 - Frontend Testing and QA
Summary: Establish frontend automated testing and accessibility checks.
Scope: Frontend
Acceptance Criteria:
- Vitest with React Testing Library covers critical components including forms, tables, and hooks.
- Playwright or Cypress end-to-end tests cover login, create league, submit results, and upgrade plan paths using mocked APIs.
- Accessibility tooling integrated with CI and high severity issues resolved.
Dependencies: PBI-028, PBI-032
Branch: pbi/034-frontend-tests

## OPS & CI -----------------------------------------------------------------------------------

## PBI-035 - CI Pipeline and Quality Gates
Summary: Configure continuous integration workflows for linting, testing, and builds.
Scope: Ops
Acceptance Criteria:
- CI pipeline runs backend and frontend lint, unit tests, and builds on pull requests and main branch.
- Pipeline publishes coverage artifacts, enforces formatting, and caches dependencies for performance.
- Status badges added to README and contribution guidelines updated to reference CI requirements.
Dependencies: PBI-020, PBI-034
Branch: pbi/035-ci-pipeline

## PBI-036 - Performance and Load Testing
Summary: Validate performance targets for standings and job queue throughput.
Scope: Backend, Ops
Acceptance Criteria:
- Load script seeds ten thousand results and measures standings query p95 under cache warm and cold scenarios.
- Background job benchmark records recompute and announcement job completion times verifying p95 under five seconds.
- Results documented in docs/Performance.md with remediation plan for regressions.
Dependencies: PBI-012, PBI-010, PBI-020
Branch: pbi/036-performance-tests

## PBI-037 - Documentation and API Specification
Summary: Maintain documentation set and automated API spec publication.
Scope: Backend, Frontend, Ops
Acceptance Criteria:
- README expanded with setup, running tests, and deployment notes; CHANGELOG initiated per coding standards.
- docs/API.md generated from FastAPI OpenAPI schema with script wired to CI to fail on drift.
- AppPBIs.md updated when PBIs close and docs/CURSOR_PROMPTS.md refreshed with relevant prompts.
Dependencies: PBI-001, PBI-020
Branch: pbi/037-documentation

## PBI-038 - Discord Auth Reintegration
Summary: Restore the full Discord OAuth flow after the temporary development bypass.
Scope: Frontend, Backend
Acceptance Criteria:
- Remove the VITE_BYPASS_AUTH fallback and require live Discord authentication for protected routes.
- Update login/refresh/logout flows and automated tests to cover happy-path and error states.
- Document Discord credential setup and local testing steps now that bypass is gone.
Dependencies: PBI-022, PBI-031
Branch: pbi/038-discord-auth
