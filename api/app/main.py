from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.settings import get_settings
from app.routes import auth, drivers, events, leagues, memberships, points, results, seasons, teams

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
app.include_router(drivers.router)
app.include_router(events.router)
app.include_router(results.router)
app.include_router(seasons.router)
app.include_router(points.router)
app.include_router(teams.router)


@app.exception_handler(FastAPIHTTPException)
async def api_http_exception_handler(
    request: Request,
    exc: FastAPIHTTPException,
):
    detail = exc.detail
    if isinstance(detail, dict):
        if "error" in detail and isinstance(detail["error"], dict):
            return JSONResponse(status_code=exc.status_code, content=detail)
        if "code" in detail:
            return JSONResponse(status_code=exc.status_code, content={"error": detail})
    return await http_exception_handler(request, exc)


@app.get("/healthz", tags=["health"])
async def healthcheck() -> dict[str, str]:
    """Lightweight health check endpoint for local development."""
    return {"status": "ok"}


