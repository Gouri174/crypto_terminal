from fastapi import APIRouter

from app.engine.ml_model import train_models

router = APIRouter()


@router.post("/train-ml")
async def train_ml():
    """Trains the win-probability / large-drawdown-probability classifiers
    on whatever historical snapshots have been backfilled so far (see
    POST /api/backfill/{symbol}). Re-run this after backfilling more
    symbols or more history — models are saved to disk and loaded lazily
    on first prediction after that."""
    return train_models()
