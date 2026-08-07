"""Retrain-if-better safety wrapper around ml_model.train_models().

train_models() always overwrites the deployed model files immediately —
fine for the very first deploy, dangerous for every retrain after that:
nothing stopped a worse model from silently replacing a better one. This
wraps it: back up the currently-deployed files, run train_models() (which
retrains and saves in place), compare the candidate's test AUC against the
PREVIOUSLY deployed model's recorded metrics, and roll back to the backup
if the candidate is worse. Never silently deploys a regression.

Not built here: automatic nightly scheduling. This app has no cron/task-
scheduler infra (the background scanner is a plain asyncio loop, not a
scheduler), and with the current volume of resolved TradeOutcome data,
a nightly retrain would mostly have nothing new to learn from — scheduling
it now would be complexity without payoff. retrain_if_better() is the real
mechanism; wiring it to a clock is a small, separate addition once there's
enough data flowing to make retraining worth automating.
"""

import json
import time
from pathlib import Path

from sqlalchemy import func, select

from app.db import SessionLocal
from app.engine import ml_model
from app.models.db_models import TradeOutcome

METADATA_PATH: Path = ml_model.MODEL_DIR / "metadata.json"
_RESOLVED_TRADE_STATUSES = ("closed_win", "closed_loss", "closed_stale")


def _load_deployed_metadata() -> dict | None:
    if not METADATA_PATH.exists():
        return None
    return json.loads(METADATA_PATH.read_text())


def _count_resolved_trade_outcomes() -> int:
    session = SessionLocal()
    try:
        return session.execute(
            select(func.count())
            .select_from(TradeOutcome)
            .where(TradeOutcome.status.in_(_RESOLVED_TRADE_STATUSES))
        ).scalar_one()
    finally:
        session.close()


def _save_metadata(result: dict) -> None:
    METADATA_PATH.write_text(
        json.dumps(
            {
                "model_version": ml_model.ML_MODEL_VERSION,
                "trained_at": result.get("trained_at"),
                "win_model_test_auc": result.get("win_model_test_auc"),
                "drawdown_model_test_auc": result.get("drawdown_model_test_auc"),
                "total_samples": result.get("total_samples"),
                # Snapshot of the TradeOutcome resolved-count AT this train
                # — the reference point retrain_recommendation() measures
                # "how much new activity since we last checked" against.
                "trade_outcomes_resolved_at_train": _count_resolved_trade_outcomes(),
            },
            indent=2,
        )
    )


def retrain_if_better(min_samples: int = 200, tolerance: float = 0.0) -> dict:
    """tolerance: how much worse (in AUC) a candidate is allowed to be and
    still get deployed — 0.0 means "must be at least as good," not
    strictly better, since two retrains on similar data can differ by
    noise alone. Returns train_models()'s result dict plus "deployed" and,
    when not deployed, "reason_not_deployed"."""
    deployed_metadata = _load_deployed_metadata()

    have_existing_model = ml_model.WIN_MODEL_PATH.exists() and ml_model.DRAWDOWN_MODEL_PATH.exists()
    win_backup = ml_model.WIN_MODEL_PATH.with_suffix(".backup.json")
    drawdown_backup = ml_model.DRAWDOWN_MODEL_PATH.with_suffix(".backup.json")
    if have_existing_model:
        win_backup.write_bytes(ml_model.WIN_MODEL_PATH.read_bytes())
        drawdown_backup.write_bytes(ml_model.DRAWDOWN_MODEL_PATH.read_bytes())

    result = ml_model.train_models(min_samples=min_samples)
    if not result.get("trained"):
        return {**result, "deployed": False, "reason_not_deployed": result.get("reason")}

    result["trained_at"] = int(time.time() * 1000)
    candidate_auc = result.get("win_model_test_auc")
    deployed_auc = deployed_metadata.get("win_model_test_auc") if deployed_metadata else None

    is_regression = (
        deployed_auc is not None and candidate_auc is not None and candidate_auc < deployed_auc - tolerance
    )
    if is_regression:
        # train_models() already overwrote the deployed files — restore
        # the backup and force the in-memory models to reload from it so
        # predictions immediately reflect the rollback, not the rejected
        # candidate.
        ml_model.WIN_MODEL_PATH.write_bytes(win_backup.read_bytes())
        ml_model.DRAWDOWN_MODEL_PATH.write_bytes(drawdown_backup.read_bytes())
        ml_model._win_model = None
        ml_model._drawdown_model = None
        ml_model._load_models()
        return {
            **result,
            "deployed": False,
            "reason_not_deployed": (
                f"candidate win_model_test_auc={candidate_auc} is worse than deployed "
                f"{deployed_auc} (tolerance {tolerance}) — rolled back to the previous model"
            ),
        }

    _save_metadata(result)
    return {**result, "deployed": True, "previous_win_model_test_auc": deployed_auc}


def retrain_recommendation(
    bootstrap_min: int = 200, new_trades_threshold: int = 50, days_threshold: int = 30
) -> dict:
    """A REMINDER, not an action — never retrains anything itself, never
    touches scoring. Rule: never recommend before `bootstrap_min` total
    resolved TradeOutcome rows exist at all. After that, recommend only
    once BOTH `new_trades_threshold` new resolutions have accumulated
    since the last train AND `days_threshold` days have passed — "whichever
    comes later," i.e. neither a fast trickle of trades nor the calendar
    alone is sufficient on its own to justify retraining on a real
    schedule.

    Honest limitation: this counts TradeOutcome resolutions as the "is
    there enough new signal to check in" trigger, but train_models() itself
    still trains on backfilled MarketSnapshot candle data, not TradeOutcome
    rows directly — training ON the system's own live outcomes is a
    separate, larger project this function does not claim to do."""
    total_resolved = _count_resolved_trade_outcomes()

    if total_resolved < bootstrap_min:
        return {
            "recommend": False,
            "reason": (
                f"Only {total_resolved} resolved trades; need >= {bootstrap_min} "
                "before retraining is worth considering at all."
            ),
            "total_resolved_trades": total_resolved,
        }

    deployed = _load_deployed_metadata()
    if deployed is None or deployed.get("trained_at") is None:
        return {
            "recommend": True,
            "reason": "No model has been trained yet, and enough resolved trades exist to start.",
            "total_resolved_trades": total_resolved,
        }

    resolved_at_train = deployed.get("trade_outcomes_resolved_at_train", 0)
    new_since_train = total_resolved - resolved_at_train
    days_since_train = (time.time() * 1000 - deployed["trained_at"]) / 86_400_000

    meets_count = new_since_train >= new_trades_threshold
    meets_days = days_since_train >= days_threshold
    recommend = meets_count and meets_days

    return {
        "recommend": recommend,
        "reason": (
            "Retraining is now worthwhile."
            if recommend
            else (
                f"Not yet — need both >= {new_trades_threshold} new resolved trades "
                f"(have {new_since_train}) AND >= {days_threshold} days since last "
                f"train (have {days_since_train:.1f})."
            )
        ),
        "total_resolved_trades": total_resolved,
        "new_resolved_since_last_train": new_since_train,
        "days_since_last_train": round(days_since_train, 1),
        "current_model_version": deployed.get("model_version"),
        "current_model_test_auc": deployed.get("win_model_test_auc"),
        "estimated_benefit": "Unknown until validation — retrain_if_better() will refuse to deploy a worse model.",
    }
