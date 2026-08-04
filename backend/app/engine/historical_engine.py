"""Historical backfill: fetch real OHLCV, reconstruct every historical
candle into a computed market-state snapshot, and — because for backfilled
data the future is already known — compute each snapshot's REAL realized
forward return and drawdown. This is the raw material for historical
similarity search. Nothing here is estimated or invented.
"""

import math
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import select

from app.data_sources import binance
from app.db import SessionLocal
from app.engine.smart_money import compute_structure
from app.indicators.technical import compute_indicator_series, klines_to_df
from app.models.db_models import MarketSnapshot, OHLCVCandle

WARMUP_CANDLES = 200  # skip until EMA200 etc. have real (non-NaN) values


async def backfill_symbol(
    symbol: str, interval: str, days: int, horizon_candles: int = 18
) -> dict:
    end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = end_ms - days * 24 * 60 * 60 * 1000

    raw_candles = await binance.get_historical_klines(symbol, interval, start_ms, end_ms)
    if not raw_candles:
        return {
            "symbol": symbol, "interval": interval,
            "candles_fetched": 0, "candles_stored": 0, "snapshots_stored": 0,
        }

    df = klines_to_df(raw_candles)

    session = SessionLocal()
    try:
        candles_stored = _upsert_candles(session, symbol, interval, df)
        snapshots_stored = _build_snapshots(session, symbol, interval, df, horizon_candles)
        session.commit()
    finally:
        session.close()

    return {
        "symbol": symbol,
        "interval": interval,
        "candles_fetched": len(df),
        "candles_stored": candles_stored,
        "snapshots_stored": snapshots_stored,
    }


def _upsert_candles(session, symbol: str, interval: str, df: pd.DataFrame) -> int:
    existing = {
        t
        for (t,) in session.execute(
            select(OHLCVCandle.open_time).where(
                OHLCVCandle.symbol == symbol, OHLCVCandle.interval == interval
            )
        )
    }
    stored = 0
    for _, row in df.iterrows():
        open_time = int(row["open_time"])
        if open_time in existing:
            continue
        session.add(
            OHLCVCandle(
                symbol=symbol,
                interval=interval,
                open_time=open_time,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
        )
        stored += 1
    return stored


def _build_snapshots(
    session, symbol: str, interval: str, df: pd.DataFrame, horizon_candles: int
) -> int:
    indicators = compute_indicator_series(df)
    structure = compute_structure(df)
    closes = df["close"].to_numpy()
    lows = df["low"].to_numpy()
    open_times = df["open_time"].to_numpy()
    n = len(df)

    existing = {
        t
        for (t,) in session.execute(
            select(MarketSnapshot.timestamp).where(
                MarketSnapshot.symbol == symbol, MarketSnapshot.interval == interval
            )
        )
    }

    stored = 0
    for i in range(WARMUP_CANDLES, n):
        open_time = int(open_times[i])
        if open_time in existing:
            continue

        row = indicators.iloc[i]
        if row.isna().any():
            continue

        struct_row = structure.iloc[i]

        forward_return_pct = None
        forward_drawdown_pct = None
        if i + horizon_candles < n:
            entry = closes[i]
            future_close = closes[i + horizon_candles]
            future_lows = lows[i + 1 : i + 1 + horizon_candles]
            forward_return_pct = float((future_close - entry) / entry * 100)
            forward_drawdown_pct = float((future_lows.min() - entry) / entry * 100)

        session.add(
            MarketSnapshot(
                symbol=symbol,
                interval=interval,
                timestamp=open_time,
                price=float(closes[i]),
                ema20=_f(row["ema20"]),
                ema50=_f(row["ema50"]),
                ema200=_f(row["ema200"]),
                rsi14=_f(row["rsi14"]),
                macd_hist=_f(row["macd_hist"]),
                bb_pct=_f(row["bb_pct"]),
                atr_pct=_f(row["atr_pct"]),
                adx14=_f(row["adx14"]),
                stoch_rsi=_f(row["stoch_rsi"]),
                obv_slope=_f(row["obv_slope"]),
                cmf=_f(row["cmf"]),
                mfi=_f(row["mfi"]),
                trend=str(struct_row["trend"]),
                bos_up=bool(struct_row["bos_up"]),
                bos_down=bool(struct_row["bos_down"]),
                choch=bool(struct_row["choch"]),
                fvg_up=bool(struct_row["fvg_up"]),
                fvg_down=bool(struct_row["fvg_down"]),
                forward_return_pct=forward_return_pct,
                forward_max_drawdown_pct=forward_drawdown_pct,
                forward_horizon_candles=horizon_candles if forward_return_pct is not None else None,
            )
        )
        stored += 1

    return stored


def _f(x) -> float | None:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    return float(x)
