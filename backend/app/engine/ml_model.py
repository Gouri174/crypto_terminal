"""ML probability layer.

Trains gradient-boosted classifiers on the ALREADY-BACKFILLED historical
snapshots (real market states with real realized outcomes — see
historical_engine.py) to predict win probability and large-drawdown
probability. Pools data across every backfilled symbol for more training
data, but standardizes each symbol's features against ITS OWN historical
distribution first: raw indicator values aren't comparable across assets at
wildly different prices/volumes (a MACD histogram of 150 means something
completely different for BTC than for a sub-$1 altcoin, and OBV's scale
depends entirely on that asset's typical volume) — pooling raw values would
silently bias the model toward whichever symbols have the largest numbers,
not the most predictive signal. This is the same per-symbol standardization
similarity.py already uses for nearest-neighbor search; here it's pooled
across symbols afterward instead of kept separate.

Claude never predicts. This module predicts; Claude explains the numbers
this module produces — same principle as the deterministic scoring model.

A note on honesty: the first version of this trained with default-ish
hyperparameters (200 trees, depth 4) and looked good on paper — 66% train
accuracy — until checked against held-out future data, where it scored
49.6%, *worse* than just guessing the base rate. That's textbook
overfitting: with ~25k rows drawn from only 6 correlated crypto assets
(autocorrelated within each symbol, cross-correlated with each other), the
effective sample size is much smaller than it looks, and a flexible model
memorizes noise. The hyperparameters below (shallow trees, heavy L2
regularization, few estimators) were chosen after verifying they generalize
to held-out future data — see train_models()'s reported test_auc, which
should be checked after every retrain, not just accuracy. A test AUC near
0.5 means the model isn't adding real information over the deterministic
score alone; do not trust this component's score contribution if that
happens after backfilling more data — retrain and re-check first.
"""

from pathlib import Path

import numpy as np
import xgboost as xgb
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import MarketSnapshot

# Bump whenever the feature set or hyperparameters change materially —
# recorded on every TradeOutcome row and in ml_models/metadata.json (see
# retrain_if_better() in ml_retrain.py) so results can be separated by
# which model version actually produced them.
ML_MODEL_VERSION = "1.0"

RAW_FEATURE_COLUMNS = ["rsi14", "bb_pct", "atr_pct", "adx14", "stoch_rsi", "cmf", "mfi"]
# Scale-dependent on price/volume — normalize by price before standardizing
# rather than using the raw stored value.
PRICE_SCALED_COLUMNS = ["macd_hist", "obv_slope"]

DRAWDOWN_THRESHOLD_PCT = -3.0
MIN_SYMBOL_HISTORY = 30

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "ml_models"
MODEL_DIR.mkdir(exist_ok=True)
WIN_MODEL_PATH = MODEL_DIR / "win_probability.json"
DRAWDOWN_MODEL_PATH = MODEL_DIR / "drawdown_risk.json"

_win_model: xgb.XGBClassifier | None = None
_drawdown_model: xgb.XGBClassifier | None = None


def _raw_row_features(row: MarketSnapshot) -> list[float | None]:
    vals: list[float | None] = [getattr(row, c) for c in RAW_FEATURE_COLUMNS]
    for c in PRICE_SCALED_COLUMNS:
        raw = getattr(row, c)
        vals.append(raw / row.price if (raw is not None and row.price) else None)
    return vals


def _current_raw_features(current_price: float, current_vec: dict) -> list[float | None]:
    vals: list[float | None] = [current_vec.get(c) for c in RAW_FEATURE_COLUMNS]
    for c in PRICE_SCALED_COLUMNS:
        raw = current_vec.get(c)
        vals.append(raw / current_price if (raw is not None and current_price) else None)
    return vals


def train_models(min_samples: int = 200) -> dict:
    session = SessionLocal()
    try:
        rows = (
            session.execute(
                select(MarketSnapshot).where(MarketSnapshot.forward_return_pct.is_not(None))
            )
            .scalars()
            .all()
        )
    finally:
        session.close()

    if len(rows) < min_samples:
        return {"trained": False, "reason": f"only {len(rows)} labeled snapshots, need >= {min_samples}"}

    by_symbol: dict[str, list[MarketSnapshot]] = {}
    for r in rows:
        by_symbol.setdefault(r.symbol, []).append(r)

    X_parts, yw_parts, yd_parts, t_parts, used_symbols = [], [], [], [], []
    for symbol, srows in by_symbol.items():
        srows.sort(key=lambda r: r.timestamp)
        raw = np.array([_raw_row_features(r) for r in srows], dtype=float)
        valid = ~np.isnan(raw).any(axis=1)
        raw = raw[valid]
        srows = [r for r, v in zip(srows, valid) if v]
        if len(raw) < MIN_SYMBOL_HISTORY:
            continue  # not enough of this symbol's own history to standardize meaningfully

        mean, std = raw.mean(axis=0), raw.std(axis=0)
        std[std == 0] = 1.0
        standardized = (raw - mean) / std

        X_parts.append(standardized)
        yw_parts.append(np.array([1 if r.forward_return_pct > 0 else 0 for r in srows]))
        yd_parts.append(
            np.array(
                [
                    1
                    if (r.forward_max_drawdown_pct is not None and r.forward_max_drawdown_pct < DRAWDOWN_THRESHOLD_PCT)
                    else 0
                    for r in srows
                ]
            )
        )
        t_parts.append(np.array([r.timestamp for r in srows]))
        used_symbols.append(symbol)

    if not X_parts:
        return {"trained": False, "reason": "no symbol had enough of its own history to standardize"}

    X = np.concatenate(X_parts)
    y_win = np.concatenate(yw_parts)
    y_drawdown = np.concatenate(yd_parts)
    timestamps = np.concatenate(t_parts)

    # Time-ordered split across the pooled set — train on the past, test on
    # the future, so the reported accuracy isn't inflated by lookahead leakage.
    order = np.argsort(timestamps)
    X, y_win, y_drawdown = X[order], y_win[order], y_drawdown[order]
    split = int(len(X) * 0.8)

    X_train, X_test = X[:split], X[split:]
    yw_train, yw_test = y_win[:split], y_win[split:]
    yd_train, yd_test = y_drawdown[:split], y_drawdown[split:]

    # Deliberately shallow/heavily regularized — see the module docstring.
    # A deeper, less regularized model looked better on training accuracy
    # (66%) but scored WORSE than the base rate on held-out data (49.6%),
    # i.e. it had memorized noise, not signal.
    model_params = dict(
        n_estimators=50, max_depth=2, learning_rate=0.03,
        reg_lambda=5.0, subsample=0.7, colsample_bytree=0.7,
        eval_metric="logloss",
    )

    win_model = xgb.XGBClassifier(**model_params)
    win_model.fit(X_train, yw_train)

    drawdown_model = xgb.XGBClassifier(**model_params)
    drawdown_model.fit(X_train, yd_train)

    win_model.save_model(str(WIN_MODEL_PATH))
    drawdown_model.save_model(str(DRAWDOWN_MODEL_PATH))

    global _win_model, _drawdown_model
    _win_model, _drawdown_model = win_model, drawdown_model

    def acc(model, X_, y_):
        return round(float(model.score(X_, y_)), 3) if len(X_) else None

    def auc(model, X_, y_):
        if len(X_) == 0 or len(set(y_.tolist())) < 2:
            return None
        return round(float(roc_auc_score(y_, model.predict_proba(X_)[:, 1])), 3)

    return {
        "trained": True,
        "symbols_used": used_symbols,
        "total_samples": len(X),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "win_model_train_accuracy": acc(win_model, X_train, yw_train),
        "win_model_test_accuracy": acc(win_model, X_test, yw_test),
        "win_model_test_auc": auc(win_model, X_test, yw_test),
        "win_base_rate": round(float(y_win.mean()), 3),
        "drawdown_model_train_accuracy": acc(drawdown_model, X_train, yd_train),
        "drawdown_model_test_accuracy": acc(drawdown_model, X_test, yd_test),
        "drawdown_model_test_auc": auc(drawdown_model, X_test, yd_test),
        "drawdown_base_rate": round(float(y_drawdown.mean()), 3),
        "win_model_test_calibration": evaluate_calibration(win_model, X_test, yw_test),
        "drawdown_model_test_calibration": evaluate_calibration(drawdown_model, X_test, yd_test),
        "note": (
            "test_auc near 0.5 means this model isn't adding real signal "
            "over the deterministic score — check this after every retrain."
        ),
        # Not saved to metadata.json (see ml_retrain.py) — returned so a
        # caller can evaluate ANOTHER model (e.g. the previously-deployed
        # one, before this call overwrote it) against the EXACT SAME
        # held-out chronological split, for a true apples-to-apples
        # comparison rather than comparing against an old model's own
        # metrics from a different, earlier test period.
        "_X_test": X_test, "_y_win_test": yw_test, "_y_drawdown_test": yd_test,
    }


_CALIBRATION_BUCKETS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]


def evaluate_calibration(model, X_: np.ndarray, y_: np.ndarray, min_bucket_n: int = 5) -> dict | None:
    """Brier score, log loss, and actual-hit-rate-by-predicted-probability
    bucket on a held-out set — the test that actually matters for a
    probability model: if it says 80-90%, does ~80-90% of that actually
    happen out-of-sample? AUC/accuracy alone can't answer that. Buckets
    with fewer than min_bucket_n test rows report null with their n rather
    than a misleading rate."""
    if len(X_) == 0 or len(set(y_.tolist())) < 2:
        return None
    probs = model.predict_proba(X_)[:, 1]
    brier = round(float(brier_score_loss(y_, probs)), 4)
    try:
        logloss = round(float(log_loss(y_, probs, labels=[0, 1])), 4)
    except ValueError:
        logloss = None

    buckets = []
    for lo, hi in _CALIBRATION_BUCKETS:
        mask = (probs >= lo) & (probs < hi)
        n = int(mask.sum())
        entry = {"predicted_range": f"{lo:.1f}-{min(hi, 1.0):.1f}", "n": n}
        if n < min_bucket_n:
            entry["note"] = f"Insufficient — need >= {min_bucket_n}, have {n}."
        else:
            entry["actual_hit_rate"] = round(float(y_[mask].mean()), 3)
        buckets.append(entry)

    return {"brier_score": brier, "log_loss": logloss, "buckets": buckets}


def _load_models() -> bool:
    global _win_model, _drawdown_model
    if _win_model is not None and _drawdown_model is not None:
        return True
    if not WIN_MODEL_PATH.exists() or not DRAWDOWN_MODEL_PATH.exists():
        return False
    win_model = xgb.XGBClassifier()
    win_model.load_model(str(WIN_MODEL_PATH))
    drawdown_model = xgb.XGBClassifier()
    drawdown_model.load_model(str(DRAWDOWN_MODEL_PATH))
    _win_model, _drawdown_model = win_model, drawdown_model
    return True


def predict_probabilities(
    symbol: str, interval: str, current_price: float, current_vec: dict
) -> dict | None:
    """`current_vec` is similarity.build_current_vector()'s output. Standardizes
    it against THIS symbol's own stored historical distribution — matching
    exactly how the model was trained — before predicting. Returns None if
    the models haven't been trained yet, or this symbol doesn't have enough
    stored history to standardize against (never a fabricated guess)."""
    if not _load_models():
        return None

    session = SessionLocal()
    try:
        rows = (
            session.execute(
                select(MarketSnapshot).where(
                    MarketSnapshot.symbol == symbol, MarketSnapshot.interval == interval
                )
            )
            .scalars()
            .all()
        )
    finally:
        session.close()

    if len(rows) < MIN_SYMBOL_HISTORY:
        return None

    raw_hist = np.array([_raw_row_features(r) for r in rows], dtype=float)
    valid = ~np.isnan(raw_hist).any(axis=1)
    raw_hist = raw_hist[valid]
    if len(raw_hist) < MIN_SYMBOL_HISTORY:
        return None

    mean, std = raw_hist.mean(axis=0), raw_hist.std(axis=0)
    std[std == 0] = 1.0

    current_raw = np.array(_current_raw_features(current_price, current_vec), dtype=float)
    if np.isnan(current_raw).any():
        return None

    current_std = ((current_raw - mean) / std).reshape(1, -1)

    win_prob = float(_win_model.predict_proba(current_std)[0][1])
    drawdown_prob = float(_drawdown_model.predict_proba(current_std)[0][1])

    return {
        "win_probability": round(win_prob, 3),
        "large_drawdown_probability": round(drawdown_prob, 3),
        "model_version": ML_MODEL_VERSION,
    }
