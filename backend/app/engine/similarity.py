"""Historical similarity search over real stored market snapshots.

Given the current market state for a symbol, finds the K most similar past
states of that SAME symbol (nearest neighbor over standardized indicator
values) and reports what ACTUALLY happened next, computed directly from
stored OHLCV — mean/median return, win rate, average drawdown. Returns None
when there isn't enough real history yet rather than fabricating a result.
"""

import numpy as np
from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import MarketSnapshot

FEATURE_COLUMNS = [
    "rsi14", "macd_hist", "bb_pct", "atr_pct",
    "adx14", "stoch_rsi", "obv_slope", "cmf", "mfi",
]
MIN_HISTORY_FOR_SIMILARITY = 20


def build_current_vector(indicator_dict: dict) -> dict:
    """Maps a live compute_indicators() dict onto the same feature space
    used for stored snapshots (atr14 -> atr_pct)."""
    last_close = indicator_dict.get("last_close")
    atr14 = indicator_dict.get("atr14")
    atr_pct = (atr14 / last_close) if (atr14 and last_close) else None

    return {
        "rsi14": indicator_dict.get("rsi14"),
        "macd_hist": indicator_dict.get("macd_hist"),
        "bb_pct": indicator_dict.get("bb_pct"),
        "atr_pct": atr_pct,
        "adx14": indicator_dict.get("adx14"),
        "stoch_rsi": indicator_dict.get("stoch_rsi"),
        "obv_slope": indicator_dict.get("obv_slope"),
        "cmf": indicator_dict.get("cmf"),
        "mfi": indicator_dict.get("mfi"),
    }


def find_similar(
    symbol: str, interval: str, current_features: dict, k: int = 20
) -> dict | None:
    session = SessionLocal()
    try:
        rows = (
            session.execute(
                select(MarketSnapshot).where(
                    MarketSnapshot.symbol == symbol,
                    MarketSnapshot.interval == interval,
                    MarketSnapshot.forward_return_pct.is_not(None),
                )
            )
            .scalars()
            .all()
        )
    finally:
        session.close()

    if len(rows) < MIN_HISTORY_FOR_SIMILARITY:
        return None

    current_vec = np.array(
        [current_features.get(c) for c in FEATURE_COLUMNS], dtype=float
    )
    if np.isnan(current_vec).any():
        return None

    matrix = np.array(
        [[getattr(r, c) for c in FEATURE_COLUMNS] for r in rows], dtype=float
    )
    mean = matrix.mean(axis=0)
    std = matrix.std(axis=0)
    std[std == 0] = 1.0

    standardized = (matrix - mean) / std
    current_std = (current_vec - mean) / std

    distances = np.linalg.norm(standardized - current_std, axis=1)
    k = min(k, len(rows))
    nearest_idx = np.argsort(distances)[:k]
    nearest = [rows[i] for i in nearest_idx]

    returns = np.array([r.forward_return_pct for r in nearest])
    drawdowns = np.array(
        [r.forward_max_drawdown_pct for r in nearest if r.forward_max_drawdown_pct is not None]
    )
    win_rate = float((returns > 0).mean() * 100)
    most_similar = nearest[0]

    return {
        "sample_size": len(nearest),
        "total_history_available": len(rows),
        "mean_return_pct": round(float(returns.mean()), 2),
        "median_return_pct": round(float(np.median(returns)), 2),
        "win_rate": round(win_rate, 1),
        "avg_drawdown_pct": round(float(drawdowns.mean()), 2) if len(drawdowns) else None,
        "horizon_candles": most_similar.forward_horizon_candles,
        "most_similar_timestamp_ms": most_similar.timestamp,
        "most_similar_return_pct": round(most_similar.forward_return_pct, 2),
    }
