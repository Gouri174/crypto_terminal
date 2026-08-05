"""Historical similarity search over real stored market snapshots.

Given the current market state for a symbol, finds the K most similar past
states of that SAME symbol (nearest neighbor over standardized indicator
values) and reports what ACTUALLY happened next — multi-horizon returns,
win rate, drawdown, largest gain/loss, the actual dates of the closest
matches, and a real feature-based "key difference" — all computed directly
from stored OHLCV/snapshots. Returns None when there isn't enough real
history yet rather than fabricating a result.
"""

from datetime import datetime, timezone

import numpy as np
from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import MarketSnapshot, OHLCVCandle

FEATURE_COLUMNS = [
    "rsi14", "macd_hist", "bb_pct", "atr_pct",
    "adx14", "stoch_rsi", "obv_slope", "cmf", "mfi",
]
FEATURE_LABELS = {
    "rsi14": "RSI", "macd_hist": "MACD histogram", "bb_pct": "Bollinger %B",
    "atr_pct": "volatility (ATR/price)", "adx14": "ADX", "stoch_rsi": "Stochastic RSI",
    "obv_slope": "OBV slope", "cmf": "Chaikin Money Flow", "mfi": "Money Flow Index",
}
MIN_HISTORY_FOR_SIMILARITY = 20

# Horizons expressed in candles, derived from the interval below.
_HORIZON_DAYS = {"1d": 1, "3d": 3, "7d": 7}


def _candles_per_day(interval: str) -> int:
    if interval.endswith("h"):
        return max(1, 24 // int(interval[:-1]))
    if interval.endswith("d"):
        return 1
    return 6  # sane default; this app only ever uses "4h" for similarity


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
    nearest_std = standardized[nearest_idx]  # for the key-difference calc below

    returns = np.array([r.forward_return_pct for r in nearest])
    drawdowns = np.array(
        [r.forward_max_drawdown_pct for r in nearest if r.forward_max_drawdown_pct is not None]
    )
    win_rate = float((returns > 0).mean() * 100)
    most_similar = nearest[0]

    horizon_returns = _multi_horizon_returns(symbol, interval, nearest)
    most_similar_dates = [
        datetime.fromtimestamp(r.timestamp / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        for r in nearest[:3]
    ]
    key_difference = _key_difference(current_std)

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
        "largest_gain_pct": round(float(returns.max()), 2),
        "largest_loss_pct": round(float(returns.min()), 2),
        "most_similar_dates": most_similar_dates,
        "horizon_returns": horizon_returns,
        "key_difference": key_difference,
    }


def _multi_horizon_returns(symbol: str, interval: str, nearest: list) -> list[dict]:
    """For each matched snapshot, looks up the REAL closing price N candles
    later directly from stored OHLCV (not re-derived from the single
    backfill-time horizon) — so 1d/3d/7d are independently accurate."""
    per_day = _candles_per_day(interval)

    session = SessionLocal()
    try:
        candle_rows = (
            session.execute(
                select(OHLCVCandle.open_time, OHLCVCandle.close)
                .where(OHLCVCandle.symbol == symbol, OHLCVCandle.interval == interval)
                .order_by(OHLCVCandle.open_time)
            )
            .all()
        )
    finally:
        session.close()

    if not candle_rows:
        return []

    time_to_idx = {row.open_time: i for i, row in enumerate(candle_rows)}
    closes = [row.close for row in candle_rows]

    results = []
    for label, days in _HORIZON_DAYS.items():
        horizon_candles = days * per_day
        rets = []
        for snap in nearest:
            idx = time_to_idx.get(snap.timestamp)
            if idx is None or idx + horizon_candles >= len(closes):
                continue
            entry = closes[idx]
            rets.append((closes[idx + horizon_candles] - entry) / entry * 100)
        if rets:
            results.append({
                "horizon": label,
                "mean_return_pct": round(float(np.mean(rets)), 2),
                "sample_size": len(rets),
            })
    return results


def _key_difference(current_std: np.ndarray) -> str | None:
    """Finds the single feature where today's value differs most (in
    standard deviations) from the matched group's average, and describes
    it in plain English — a real, computed comparison, not a guess."""
    idx = int(np.argmax(np.abs(current_std)))
    z = current_std[idx]
    if abs(z) < 0.5:
        return None
    feature = FEATURE_LABELS[FEATURE_COLUMNS[idx]]
    direction = "higher" if z > 0 else "lower"
    return f"Today's {feature} is notably {direction} than the average of these historical matches."
