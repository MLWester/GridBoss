from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import get_settings
from app.routes import auth, leagues, memberships

settings = get_settings()

app = FastAPI(title="GridBoss API", version="0.1.0")

allowed_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth.router)
app.include_router(leagues.router)
app.include_router(memberships.router)


@app.get("/healthz", tags=["health"])
async def healthcheck() -> dict[str, str]:
    """Lightweight health check endpoint for local development."""
    return {"status": "ok"}
