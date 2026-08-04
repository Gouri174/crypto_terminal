import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS, SCANNER_ENABLED
from app.db import init_db
from app.engine.background_scanner import run_scanner_loop
from app.routes import analyze, ask, backfill, opportunities, ws

app = FastAPI(
    title="Crypto AI Terminal API",
    description=(
        "Analysis-only. Produces AI-generated trade plans with confidence "
        "scores, not guarantees. Not financial advice. Does not place trades."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(opportunities.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(ask.router, prefix="/api")
app.include_router(backfill.router, prefix="/api")
app.include_router(ws.router)

_scanner_task: asyncio.Task | None = None


@app.on_event("startup")
async def on_startup():
    global _scanner_task
    init_db()
    if SCANNER_ENABLED and _scanner_task is None:
        _scanner_task = asyncio.create_task(run_scanner_loop())


@app.get("/api/health")
async def health():
    return {"status": "ok"}
