from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import analyze, ask, opportunities

app = FastAPI(
    title="Crypto AI Terminal API",
    description=(
        "Analysis-only. Produces AI-generated trade plans with confidence "
        "scores, not guarantees. Not financial advice. Does not place trades."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(opportunities.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(ask.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
