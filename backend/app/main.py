from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS
from app.db import init_db
from app.routes import analyze, ask, backfill, opportunities

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


@app.on_event("startup")
async def on_startup():
    init_db()


@app.get("/api/health")
async def health():
    return {"status": "ok"}
