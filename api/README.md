# GridBoss API

The API service is built with FastAPI and provides the backend for GridBoss. This directory currently ships a development skeleton together with dependency and tooling configuration so future PBIs can focus on implementing business logic.

## Quick start
1. Create a virtual environment (one is already generated as `.venv` when running automated setup):
   ```powershell
   python -m venv .venv
   ```
2. Install dependencies:
   ```powershell
   .venv\Scripts\pip install -r requirements-dev.txt
   ```
3. Run the development server:
   ```powershell
   .venv\Scripts\uvicorn --app app.main:app --reload
   ```

## Tooling
- `black` and `ruff` are configured via `pyproject.toml` with a 100 character line length.
- `pytest` is available for unit and integration tests.
- Database and messaging dependencies follow versions aligned with the master spec (PostgreSQL via SQLAlchemy, Redis, psycopg, Alembic).

## Next steps
Future PBIs will introduce:
- Database models and session management.
- Auth, RBAC, and API routes.
- Background workers, Stripe integration, and Discord bot communication.