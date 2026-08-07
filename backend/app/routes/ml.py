from fastapi import APIRouter

from app.engine.ml_retrain import retrain_if_better, retrain_recommendation

router = APIRouter()


@router.post("/train-ml")
async def train_ml():
    """Trains the win-probability / large-drawdown-probability classifiers
    on whatever historical snapshots have been backfilled so far (see
    POST /api/backfill/{symbol}). Re-run this after backfilling more
    symbols or more history. Only actually DEPLOYS the retrained model if
    its test AUC is at least as good as the currently-deployed model's —
    see app/engine/ml_retrain.py. Check the "deployed" field in the
    response; "reason_not_deployed" explains a rejection."""
    return retrain_if_better()


@router.get("/ml/retrain-recommendation")
async def ml_retrain_recommendation():
    """A REMINDER only — does not retrain anything. Tells you whether
    enough real resolved trades have accumulated to make retraining worth
    considering, per the fixed rule in ml_retrain.retrain_recommendation()."""
    return retrain_recommendation()
