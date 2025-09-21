# GridBoss API

The API service is built with FastAPI and provides the backend for GridBoss. The database layer now includes SQLAlchemy models, session helpers, and Alembic migrations for the core league management entities.

## Quick start
1. Create or reuse the virtual environment (one is already generated as `.venv` during setup):
   ```powershell
   python -m venv .venv
   ```
2. Install dependencies:
   ```powershell
   .venv\Scripts\pip install -r requirements-dev.txt
   ```
3. Apply database migrations (requires PostgreSQL available at `DATABASE_URL`):
   ```powershell
   $env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/gridboss"
   .venv\Scripts\alembic upgrade head
   ```
4. Run the development server:
   ```powershell
   .venv\Scripts\uvicorn --app app.main:app --reload
   ```

## Tooling
- `black` and `ruff` are configured via `pyproject.toml` with a 100 character line length.
- `pytest` is available for unit and integration tests.
- Core database models live in `app/db/models.py` and share the base in `app/db/base.py`.
- Alembic configuration resides in `alembic.ini` with scripts under `app/db/migrations/`.

## Database Modules
- `app/db/session.py` exposes `get_session()` for FastAPI dependencies and caches the engine/sessionmaker.
- `app/db/models.py` defines users, leagues, memberships, teams, drivers, seasons, events, points, results, Discord integrations, billing, and audit logs.
- The initial migration (`versions/20250921_0001_initial_schema.py`) provisions all core tables, constraints, and indexes described in the master spec.

## Next steps
Future PBIs will introduce:
- Auth, RBAC, and API routes.
- Background workers, Stripe integration, and Discord bot communication.
- Automated tests and seed data.
