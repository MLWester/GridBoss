GridBoss - Master App Spec (MVP)

One-line: App-centric SaaS for sim racing league management with Discord announcements and Stripe subscriptions.
Source of truth: The web app. Discord bot is a companion (announcements, linking).
Tech: React (Vite+TS+Tailwind), FastAPI (Python 3.11), PostgreSQL, Redis, Dramatiq (or RQ), Stripe, discord.py.
Principles: Small, composable services; stateless API; background jobs for slow/3rd-party work; explicit RBAC; test-first for scoring/standings & billing webhooks.

Table of Contents

Product Goals & Non-Goals

Roles, Plans & Entitlements

Core User Stories (Acceptance Criteria)

System Architecture

Environment, Secrets & Docker

Data Model (ERD, Tables, Indexes)

Domain Rules (Points, Standings, Seasons)

API Contracts (Routes, Payloads, Errors)

Background Jobs & Queues

Discord Integration (Bot + Linking)

Billing (Stripe)

Frontend UI Spec (Pages, Components, States)

Security, Privacy, Compliance

Performance & Rate Limits

Observability & Ops

Testing Strategy (Unit/Integration/Load)

Seed & Demo Data

Admin Console (Founder-only MVP)

Definition of Done & Coding Standards

Out-of-Scope (MVP)

Branch Plan & File Layout

1) Product Goals & Non-Goals
Goals

Replace spreadsheets and ad-hoc Discord workflows with a simple league OS.

Make event scheduling, results entry, and standings dead-easy.

Keep drivers engaged via Discord announcements.

Monetize with Stripe subscriptions (feature gating, limits).

Non-Goals (MVP)

No automated parsing from sim log files/APIs. (Future)

No mobile app (web responsive only). (Future)

No deep analytics (consistency charts, incidents, etc.). (Future)

2) Roles, Plans & Entitlements
Roles (per league)

OWNER: full control; manages billing/integration.

ADMIN: manage league, events, drivers, results.

STEWARD: enter results, penalties, points overrides.

DRIVER: read-only.

Plans

FREE:

1 league, <= 20 drivers, manual results only, no Discord posts.

PRO ($20/mo):

<= 100 drivers/league, Discord announcements, season history, CSV driver import.

ELITE ($50/mo):

Unlimited drivers/leagues, custom branding, API export (read-only).

Enforcement: route decorator @requires_plan("PRO"), league/driver limits validated server-side.

3) Core User Stories (Acceptance Criteria)

Create league & roster

POST /leagues -> {name, slug} unique; default season auto-created (active).

POST /leagues/{id}/drivers supports bulk paste; unique display_name per league.

Schedule events

POST /leagues/{id}/events stores UTC time; GET returns local when ?tz= provided.

Filter upcoming/completed; cancel/update with audit trail.

Enter results & compute standings

POST /events/{id}/results accepts bulk entries with {driverId, finishPosition, bonusPoints?, penaltyPoints?}.

Server computes total_points = max(0, base+bonus-penalty) from active points scheme.

Triggers async standings recompute and (if PRO w/ Discord linked) results announcement job.

Idempotency via Idempotency-Key header.

Discord companion

Link guild + channel; Test Post button.

Announce new events and results/standings.

Billing

Checkout for PRO/ELITE; Portal for manage/cancel.

Webhooks update plan, enforce gates and limits with grace period.

4) System Architecture
[Browser] -> Cloudflare/CDN -> [Frontend (Vite/React)]
                           -> [API LB] -> [FastAPI pods] -> [PostgreSQL]
                                               |        -> [Redis]
                                               -> [Worker pods] -> [Discord API, Stripe API]
[Discord Bot] <-> [Redis queue] <-> [Worker pods]


API stateless; all long tasks go to worker (Dramatiq recommended).

Redis for: queues, cache (standings), rate-limits, idempotency keys.

Postgres single source of truth; row-level multi-tenancy via league_id.

Bot only posts messages & handles slash commands; no business logic.

5) Environment, Secrets & Docker
.env.example
# General
APP_ENV=dev
APP_URL=http://localhost:5173
API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:5173

# API
API_PORT=8000
JWT_SECRET=change_me
JWT_ACCESS_TTL_MIN=15
JWT_REFRESH_TTL_DAYS=14

# DB/Cache
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/gridboss
REDIS_URL=redis://redis:6379/0

# Discord
DISCORD_CLIENT_ID=xxx
DISCORD_CLIENT_SECRET=xxx
DISCORD_REDIRECT_URI=http://localhost:8000/auth/discord/callback
DISCORD_BOT_TOKEN=xxx

# Stripe
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PRICE_PRO=price_xxx
STRIPE_PRICE_ELITE=price_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

Docker Compose (dev)

Services: frontend, api, worker, bot, db (postgres), redis, optional stripe-cli.

Healthchecks for api/db/redis.

Volumes mounted for hot-reload.

6) Data Model (ERD, Tables, Indexes)
Entities

users: Discord SSO (discord_id, username, avatar), optional email.

leagues: owner_id (user), name, slug unique, plan, driver_limit.

memberships: user<->league, role (enum).

teams: per league, unique name per league.

drivers: per league, unique display_name per league; optional linked user & discord_id.

seasons: per league, name, is_active (exactly one active enforced by app).

events: per league/season, name, track, start_time (UTC), laps?, distance_km?, status.

points_schemes + points_rules: position -> base points (default F1).

results: per event+driver, finish_position, started_position?, status (FINISHED|DNF|DNS|DSQ), bonus/penalty, total_points (denormalized).

integrations_discord: league -> guild_id, channel_id, is_active.

billing_accounts: owner_user_id -> stripe_customer_id, plan, current_period_end.

subscriptions: stripe_subscription_id, plan, status, started_at.

audit_logs: actor, league, entity, action, before/after JSON, timestamp.

Key Indexes

leagues.slug unique

drivers(league_id, display_name) unique

events(league_id, start_time) btree

results(event_id, finish_position) btree

Partial: events(status) WHERE status='SCHEDULED'

DDL (excerpt)
CREATE TYPE league_role AS ENUM ('OWNER','ADMIN','STEWARD','DRIVER');

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT now(),
  email TEXT UNIQUE,
  discord_id TEXT UNIQUE,
  discord_username TEXT,
  avatar_url TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE leagues (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT now(),
  owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  plan TEXT NOT NULL DEFAULT 'FREE',
  driver_limit INT NOT NULL DEFAULT 20
);

CREATE TABLE memberships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id UUID NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role league_role NOT NULL,
  UNIQUE (league_id, user_id)
);

CREATE TABLE teams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id UUID NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  UNIQUE (league_id, name)
);

CREATE TABLE drivers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id UUID NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  display_name TEXT NOT NULL,
  discord_id TEXT,
  team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
  UNIQUE (league_id, display_name)
);

CREATE TABLE seasons (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id UUID NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id UUID NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
  season_id UUID REFERENCES seasons(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  track TEXT NOT NULL,
  start_time TIMESTAMPTZ NOT NULL,
  laps INT,
  distance_km NUMERIC(6,2),
  status TEXT NOT NULL DEFAULT 'SCHEDULED'
);

CREATE TABLE points_schemes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id UUID NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
  season_id UUID REFERENCES seasons(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  is_default BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE points_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scheme_id UUID NOT NULL REFERENCES points_schemes(id) ON DELETE CASCADE,
  position INT NOT NULL,
  points INT NOT NULL
);

CREATE TABLE results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  driver_id UUID NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
  finish_position INT NOT NULL,
  started_position INT,
  status TEXT NOT NULL DEFAULT 'FINISHED',
  bonus_points INT NOT NULL DEFAULT 0,
  penalty_points INT NOT NULL DEFAULT 0,
  total_points INT NOT NULL,
  UNIQUE (event_id, driver_id)
);

CREATE TABLE integrations_discord (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id UUID NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
  guild_id TEXT NOT NULL,
  channel_id TEXT,
  installed_by_user UUID REFERENCES users(id),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (league_id, guild_id)
);

CREATE TABLE billing_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  stripe_customer_id TEXT UNIQUE,
  plan TEXT NOT NULL DEFAULT 'FREE',
  current_period_end TIMESTAMPTZ
);

CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  billing_account_id UUID NOT NULL REFERENCES billing_accounts(id) ON DELETE CASCADE,
  stripe_subscription_id TEXT UNIQUE,
  plan TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

7) Domain Rules (Points, Standings, Seasons)
Points

Default scheme F1: 1->25, 2->18, 3->15, 4->12, 5->10, 6->8, 7->6, 8->4, 9->2, 10->1.

total_points = max(0, base(position) + bonus - penalty).

Missing mapping => base = 0.

Custom scheme editable per league (simple table editor).

Standings

Aggregate by season across that season's events.

Order by SUM(total_points) DESC, tie-break on wins (count of finish_position=1), then best_finish (lowest pos).

Cache per season_id in Redis; invalidate on results write.

Seasons

Exactly one active season per league (app-enforced).

MVP may operate with a single default season.

8) API Contracts
Conventions

Auth: Discord OAuth -> JWT (access 15m), Refresh (rotating, HttpOnly).

Errors:

{ "error": { "code": "string", "message": "string", "field": "optional" } }


Idempotency: For mutating bulk ops & webhooks -> Idempotency-Key.

Auth
GET  /auth/discord/start        -> 302 to Discord
GET  /auth/discord/callback     -> sets refresh cookie, returns 302 to APP_URL
GET  /me                        -> { user, memberships, billingPlan }
POST /logout                    -> clears cookies

Leagues
POST /leagues                   -> {id, name, slug, plan}
GET  /leagues                   -> array of leagues user belongs to
GET  /leagues/{leagueId}
PATCH/DELETE /leagues/{leagueId}


Create League (example)

POST /leagues
{ "name": "Amarillo GT3 Cup", "slug": "amarillo-gt3" }

Drivers & Teams
POST /leagues/{leagueId}/drivers    # supports {items: [{displayName, teamId?}, ...]} bulk
GET  /leagues/{leagueId}/drivers
PATCH /drivers/{driverId}
DELETE /drivers/{driverId}

POST /leagues/{leagueId}/teams
GET  /leagues/{leagueId}/teams
PATCH /teams/{teamId}
DELETE /teams/{teamId}

Events & Results
POST /leagues/{leagueId}/events
GET  /leagues/{leagueId}/events?status=SCHEDULED|COMPLETED
GET  /events/{eventId}
PATCH/DELETE /events/{eventId}

POST /events/{eventId}/results    # { entries: [...] }, Idempotency-Key required
GET  /events/{eventId}/results


Post Results (example)

POST /events/evt-uuid/results
{
  "entries": [
    { "driverId": "d1", "finishPosition": 1, "bonusPoints": 1, "penaltyPoints": 0 },
    { "driverId": "d2", "finishPosition": 2 }
  ]
}

Standings
GET /leagues/{leagueId}/standings?seasonId={uuid}


Response

{
  "seasonId":"...", "items":[
    { "driverId":"...", "displayName":"...", "points": 85, "wins":2, "bestFinish":1 }
  ]
}

Discord
POST /leagues/{leagueId}/discord/link    # {guildId, channelId}
POST /leagues/{leagueId}/discord/test    # Pro-gated; sends a test message

Billing (Stripe)
POST /billing/checkout    # body: {plan: "PRO"|"ELITE"} -> {url}
POST /billing/portal      # -> {url}
POST /webhooks/stripe     # signature verified; idempotent

9) Background Jobs & Queues
Jobs (Dramatiq or RQ)

recompute_standings(season_id)

announce_event(league_id, event_id)

announce_results(league_id, event_id)

sync_plan_from_stripe(customer_id)

SLO: p95 completion < 5s; retries w/ exponential backoff (max 5).

10) Discord Integration
Bot (discord.py)

Slash:

/gridboss link -> DM secure URL back to app to connect guild/channel.

/gridboss test -> posts to configured channel (Pro-gated).

Consumes Redis queue messages to post event and results embeds.

On failure (no perms/bot removed): mark integration inactive; write audit log.

Security

Validate only OWNER/ADMIN can link.

Store guild_id, channel_id per league; write-only scope to that channel.

11) Billing (Stripe)
Plans

Prices: STRIPE_PRICE_PRO, STRIPE_PRICE_ELITE.

Checkout: create or reuse customer; success/cancel URLs.

Portal: Stripe Billing portal link.

Webhooks (required)

checkout.session.completed -> activate plan.

customer.subscription.updated|deleted -> update status/plan, set grace period.

invoice.payment_failed -> warn + potential downgrade after grace.

Idempotency: store processed stripe_event_id. Verify signature STRIPE_WEBHOOK_SECRET.

Plan Enforcement

Middleware checks entitlements on gateable routes and driver limit on create/update.

12) Frontend UI Spec
Global

Router + ProtectedRoute; React Query for data; global toasts; error boundary.

Navbar shows user, plan badge, league switcher.

Pages

/login

Discord login button. After callback, fetch /me then redirect to /dashboard.

/dashboard

List leagues (role badges). "Create League" CTA. Plan card with Upgrade button.

/l/:slug (League Home)

Tabs: Overview | Drivers | Teams | Events | Standings | Settings

Overview: next event (local time), last results, "Link Discord" (if Pro).

Drivers

Table (display name, team, link icon if connected to user/discord).

Bulk paste (textarea) -> preview -> save. Enforce uniqueness; show conflicts.

Teams

Simple CRUD; assign drivers via row editor.

Events

Create form: name, track, datetime picker (shows local; stores UTC), laps/distance.

List: upcoming/completed filter; local time labels.

Detail: event info + Results tab.

Results

Event detail: results editor with rows (drag to sort positions), bonus/penalty inputs.

Submit -> uses Idempotency-Key. On success -> toast + standings refresh.

Standings

Season selector; table with points, wins, best finish; share link.

Empty state with sample data CTA.

Settings

General: name, slug (validate).

Points Scheme: simple table positions 1..10 (editable).

Discord: link guild/channel, Test Post button (Pro-gated).

Danger Zone: delete league (soft delete).

Billing

Shows current plan & limits; Upgrade (Checkout), Manage (Portal).

UI States to Support

Loading, empty, error (with retry).

Disabled/pro-gated actions show a tooltip "Requires Pro -- Upgrade".

13) Security, Privacy, Compliance

Auth: Discord OAuth2 (PKCE + state), JWT Access (15m) + Refresh (rotating, HttpOnly, Secure).

CSRF: double-submit token for mutating routes.

RBAC: enforce per request; never rely on client claims.

Rate-limits: per user (60 req/min), per league (600 req/min).

PII: store minimal Discord profile. Provide delete/export stubs (MVP OK to stub).

Backups: daily PG backups + PITR.

Audit logs: write on: league settings change, points edits, Discord link, plan changes.

14) Performance & Rate Limits

Standings query p95 <50ms for 10k results (with cache warm).

Result posting -> recompute + announce within <5s at p95.

Redis TTL for standings cache 300s, hard invalidate on writes.

Outbound Discord posting rate-limited & retried with backoff.

15) Observability & Ops

Logs: JSON with x-request-id, include user_id, league_id when available.

Tracing: OpenTelemetry optional; at minimum, correlate API <-> job logs.

Errors: Sentry (API, worker, bot).

Health: /healthz (db/redis ping), /readyz (migrations applied).

CI: run tests, linters, type checks, alembic migration dry-run.

16) Testing Strategy

Unit: points calc, standings ordering (wins, best finish), RBAC guards, idempotency.

Integration: results POST -> standings cache invalidated -> recompute job -> Discord job enqueued (mock client).

Stripe: webhook signature verify + state transitions (fixtures via Stripe CLI).

Load: seed 10k results, standings p95 < 50ms; job queue p95 < 5s.

17) Seed & Demo Data

Script scripts/seed_demo.py:

Owner user, league "Demo GP" (slug demo-gp), 10 drivers, default F1 scheme, 3 events (1 completed with results), sample standings.

Idempotent (upsert by slug).

18) Admin Console (Founder-only MVP)

Read-only pages to: search users/leagues, view subscriptions, force plan (dev only), deactivate Discord integration, view audit logs.

Protected behind env flag ADMIN_MODE=true and role check.

19) Definition of Done & Coding Standards

API: OpenAPI up-to-date; 2-3 tests per new route; RBAC enforced; error envelope consistent.

FE: responsive, error states, optimistic updates where safe, a11y basic pass.

Worker/Bot: retries & backoff, structured logs, Sentry capture.

Docs: README updated; .env.example accurate; CHANGELOG entry.

Style: Prettier/ESLint (FE), Ruff/Black (BE). Conventional commits.

20) Out-of-Scope (MVP)

Auto-parsing sim logs / official APIs.

Public profiles & social graph.

Mobile app.

Advanced analytics (consistency charts, incidents, quali vs race pace).

21) Branch Plan & File Layout
Monorepo
gridboss/
  frontend/
    src/
      pages/
      components/
      api/
      hooks/
      styles/
    index.html
    vite.config.ts
    package.json
  api/
    app.py
    core/        # config, deps, security, rate-limit, error handlers
    db/          # models.py, session.py, migrations/
    routes/      # auth.py, leagues.py, drivers.py, teams.py, events.py, results.py, standings.py, billing.py, discord.py
    services/    # points.py, standings.py, notifications.py, billing.py, audit.py
    tests/
  worker/
    main.py      # queue consumers (standings, announce, billing sync)
    jobs/        # recompute.py, discord_jobs.py
  bot/
    main.py      # discord.py client, slash commands, Redis consumer
  infra/
    docker-compose.yml
    Dockerfile.api
    Dockerfile.frontend
    Dockerfile.bot
    Dockerfile.worker
  scripts/
    seed_demo.py
  docs/
    MASTER_SPEC.md
    API.md
    ERD.md
    CURSOR_PROMPTS.md

Suggested Branches

ops/docker-ci

Backend: be/auth-rbac, be/leagues-crud, be/drivers-teams-api, be/events-api, be/results-points, be/standings-cache, be/discord-integration, be/stripe-billing, be/audit-admin

Frontend: fe/app-shell-auth, fe/leagues-wizard, fe/drivers-teams, fe/events, fe/results-standings, fe/settings-discord, fe/billing-ui

Ops/QA: ops/observability, ops/tests-load

Implementation Notes (for Codex)

Timezone: UI displays local; API stores UTC; ?tz= optional for reads.

Idempotency: Use Idempotency-Key header; backend stores recent keys in Redis with short TTL (e.g., 10 min).

Cache: Redis cache for standings keyed by season_id. Invalidate upon any results write/update/delete.

Driver limits: enforce at API create/update, return 402-like business error {code:"PLAN_LIMIT"}.

Discord test button: if Pro + integration exists, attempt post; return detailed error if bot lacks perms.

Grace period: on downgrade, keep Pro features for 7 days; then hard enforce.

Soft delete: leagues deletions are soft for 7 days; allow restore.

OpenAPI: auto-generate and commit docs/API.md on build or with a script.

Golden Data (for tests)

F1 scheme: positions 1..10 = [25,18,15,12,10,8,6,4,2,1]

Tie-breakers: if equal points, higher wins wins; if still equal, lower best_finish wins; else alphabetical by display_name.

Sample standings expectation stored in api/tests/golden/standings_f1.json.
