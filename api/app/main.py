from fastapi import FastAPI

app = FastAPI(title="GridBoss API", version="0.1.0")


@app.get("/healthz", tags=["health"])
async def healthcheck() -> dict[str, str]:
    """Lightweight health check endpoint for local development."""
    return {"status": "ok"}
