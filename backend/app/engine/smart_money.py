"""Smart-money / price-action structure detection.

Pure price-action math computed from OHLCV — no paid data, no third-party
"smart money" feed. Implements generic, widely-taught concepts (fractal
swing points, break of structure, change of character, fair value gaps) from
first principles, not transcribed from any single copyrighted source.
"""

import pandas as pd


def find_swing_points(df: pd.DataFrame, lookback: int = 2) -> tuple[pd.Series, pd.Series]:
    """A swing high/low is a fractal: the single highest high (or lowest low)
    within a +/- lookback window of candles."""
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    n = len(df)
    swing_high = [False] * n
    swing_low = [False] * n

    for i in range(lookback, n - lookback):
        window_h = highs[i - lookback : i + lookback + 1]
        if highs[i] == window_h.max() and (window_h == highs[i]).sum() == 1:
            swing_high[i] = True
        window_l = lows[i - lookback : i + lookback + 1]
        if lows[i] == window_l.min() and (window_l == lows[i]).sum() == 1:
            swing_low[i] = True

    return pd.Series(swing_high, index=df.index), pd.Series(swing_low, index=df.index)


def find_fair_value_gaps(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """3-candle imbalance: a bullish FVG is a gap between candle[i-2].high and
    candle[i].low left by a strong impulse candle in between (and mirrored
    for bearish)."""
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    n = len(df)
    fvg_up = [False] * n
    fvg_down = [False] * n

    for i in range(2, n):
        if low[i] > high[i - 2]:
            fvg_up[i] = True
        if high[i] < low[i - 2]:
            fvg_down[i] = True

    return pd.Series(fvg_up, index=df.index), pd.Series(fvg_down, index=df.index)


def compute_structure(df: pd.DataFrame, lookback: int = 2) -> pd.DataFrame:
    """Walks candles in order, tracking the most recent confirmed swing
    high/low and the prevailing structural trend. A break of the level in the
    direction of the current trend is a Break of Structure (continuation); a
    break against it is a Change of Character (possible reversal).

    Returns a DataFrame aligned to `df.index` with columns:
    trend, bos_up, bos_down, choch, fvg_up, fvg_down, nearest_swing_high,
    nearest_swing_low, fvg_up_bottom, fvg_up_top, fvg_down_top, fvg_down_bottom

    The nearest_swing_high/low and fvg_*_top/bottom columns are the exact
    price values this function was already computing internally to decide
    bos_up/bos_down/choch/fvg_up/fvg_down — surfaced here as their own
    columns rather than discarded, so a caller can capture the actual
    structure level or FVG range a trade was measured against, not just
    the boolean flag. No detection logic changes: same swings, same BOS/
    CHOCH/FVG rules as before, this only stops throwing away values that
    were already sitting in the loop.
    """
    swing_high, swing_low = find_swing_points(df, lookback)
    fvg_up, fvg_down = find_fair_value_gaps(df)
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    n = len(df)

    trend = ["neutral"] * n
    bos_up = [False] * n
    bos_down = [False] * n
    choch = [False] * n
    nearest_swing_high = [None] * n
    nearest_swing_low = [None] * n
    fvg_up_bottom = [None] * n
    fvg_up_top = [None] * n
    fvg_down_top = [None] * n
    fvg_down_bottom = [None] * n

    last_swing_high = None
    last_swing_low = None
    current_trend = "neutral"

    for i in range(n):
        if swing_high.iloc[i]:
            last_swing_high = closes[i] if last_swing_high is None else max(last_swing_high, df["high"].iloc[i])
            last_swing_high = df["high"].iloc[i]
        if swing_low.iloc[i]:
            last_swing_low = df["low"].iloc[i]

        if last_swing_high is not None and closes[i] > last_swing_high:
            if current_trend == "bull":
                bos_up[i] = True
            else:
                choch[i] = True
                current_trend = "bull"
            last_swing_high = None  # level consumed, wait for the next swing

        elif last_swing_low is not None and closes[i] < last_swing_low:
            if current_trend == "bear":
                bos_down[i] = True
            else:
                choch[i] = True
                current_trend = "bear"
            last_swing_low = None

        trend[i] = current_trend
        nearest_swing_high[i] = last_swing_high
        nearest_swing_low[i] = last_swing_low

        if i >= 2:
            if fvg_up.iloc[i]:
                fvg_up_bottom[i] = highs[i - 2]
                fvg_up_top[i] = lows[i]
            if fvg_down.iloc[i]:
                fvg_down_top[i] = lows[i - 2]
                fvg_down_bottom[i] = highs[i]

    return pd.DataFrame(
        {
            "trend": trend,
            "bos_up": bos_up,
            "bos_down": bos_down,
            "choch": choch,
            "fvg_up": fvg_up,
            "fvg_down": fvg_down,
            "nearest_swing_high": nearest_swing_high,
            "nearest_swing_low": nearest_swing_low,
            "fvg_up_bottom": fvg_up_bottom,
            "fvg_up_top": fvg_up_top,
            "fvg_down_top": fvg_down_top,
            "fvg_down_bottom": fvg_down_bottom,
        },
        index=df.index,
    )
