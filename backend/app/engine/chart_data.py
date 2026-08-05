"""Builds the chart payload the frontend renders with lightweight-charts:
candles, EMA overlays, and every AI-drawn annotation (entry/stop/TP levels,
support/resistance from swing points, BOS/CHOCH markers, fair value gaps,
order blocks). Every overlay carries a plain-English `explain` string
generated deterministically from what was actually detected — no per-click
LLM call, so clicking around the chart costs nothing and can't drift from
the data. Claude's own reasoning (reasons_for/against, invalidation) is
reused verbatim for the entry/stop/TP levels since that IS the real
evidence-based explanation for those.
"""

import pandas as pd
import ta

from app.data_sources import binance
from app.engine.smart_money import compute_structure
from app.indicators.technical import klines_to_df


async def build_chart(symbol: str, interval: str, limit: int, trade_plan: dict | None) -> dict:
    klines = await binance.get_klines(symbol, interval, limit)
    df = klines_to_df(klines)
    structure = compute_structure(df)

    ema20 = ta.trend.ema_indicator(df["close"], window=20)
    ema50 = ta.trend.ema_indicator(df["close"], window=50)
    ema200 = ta.trend.ema_indicator(df["close"], window=200)

    times = (df["open_time"] // 1000).astype(int).tolist()  # lightweight-charts wants seconds

    candles = [
        {
            "time": t,
            "open": round(o, 8),
            "high": round(h, 8),
            "low": round(l, 8),
            "close": round(c, 8),
        }
        for t, o, h, l, c in zip(times, df["open"], df["high"], df["low"], df["close"])
    ]

    def line_series(series: pd.Series) -> list[dict]:
        return [
            {"time": t, "value": round(float(v), 8)}
            for t, v in zip(times, series)
            if pd.notna(v)
        ]

    markers = _build_markers(df, structure, times)
    order_blocks = _find_order_blocks(df, structure, times)
    levels = _build_levels(trade_plan)

    return {
        "symbol": symbol,
        "interval": interval,
        "candles": candles,
        "ema20": line_series(ema20),
        "ema50": line_series(ema50),
        "ema200": line_series(ema200),
        "markers": markers,
        "order_blocks": order_blocks,
        "levels": levels,
    }


def _build_markers(df: pd.DataFrame, structure: pd.DataFrame, times: list[int]) -> list[dict]:
    markers = []
    highs, lows = df["high"].to_numpy(), df["low"].to_numpy()

    for i in range(len(df)):
        t = times[i]
        row = structure.iloc[i]

        if row["bos_up"]:
            markers.append({
                "time": t, "type": "bos_up", "position": "belowBar", "price": float(lows[i]),
                "label": "BOS ↑",
                "explain": (
                    f"Break of Structure (bullish continuation): price closed above the "
                    f"prior swing high, confirming the existing uptrend is still in control."
                ),
            })
        if row["bos_down"]:
            markers.append({
                "time": t, "type": "bos_down", "position": "aboveBar", "price": float(highs[i]),
                "label": "BOS ↓",
                "explain": (
                    f"Break of Structure (bearish continuation): price closed below the "
                    f"prior swing low, confirming the existing downtrend is still in control."
                ),
            })
        if row["choch"]:
            markers.append({
                "time": t, "type": "choch", "position": "inBar", "price": float((highs[i] + lows[i]) / 2),
                "label": "CHoCH",
                "explain": (
                    "Change of Character: price broke a structural level AGAINST the prior "
                    "trend — the first evidence the trend may be turning. Not confirmation "
                    "on its own, but the point where the read on direction changed."
                ),
            })
        if row["fvg_up"] and i >= 2:
            gap_from = float(highs[i - 2])
            gap_to = float(lows[i])
            markers.append({
                "time": t, "type": "fvg_up", "position": "belowBar", "price": gap_to,
                "label": "FVG",
                "explain": (
                    f"Bullish fair value gap: a 3-candle imbalance leaving a gap between "
                    f"~{gap_from:.6g} and ~{gap_to:.6g} with no trading in between. Gaps "
                    f"like this often get revisited before the move continues."
                ),
            })
        if row["fvg_down"] and i >= 2:
            markers.append({
                "time": t, "type": "fvg_down", "position": "aboveBar", "price": float(highs[i]),
                "label": "FVG",
                "explain": (
                    "Bearish fair value gap: a 3-candle imbalance left by a fast down-move. "
                    "Price often revisits this zone before continuing lower."
                ),
            })

    return markers


def _find_order_blocks(df: pd.DataFrame, structure: pd.DataFrame, times: list[int], lookback: int = 5) -> list[dict]:
    """The order block for a break of structure is the last opposite-colored
    candle before the impulse move that caused the break — a simple,
    widely-taught heuristic, not a proprietary indicator."""
    opens, closes = df["open"].to_numpy(), df["close"].to_numpy()
    highs, lows = df["high"].to_numpy(), df["low"].to_numpy()
    blocks = []

    for i in range(len(df)):
        row = structure.iloc[i]
        if row["bos_up"] or (row["choch"] and row["trend"] == "bull"):
            for j in range(i - 1, max(i - lookback, -1), -1):
                if closes[j] < opens[j]:  # last bearish candle before the up-move
                    blocks.append({
                        "time_start": int(times[j]),
                        "time_end": int(times[i]),
                        "top": float(highs[j]),
                        "bottom": float(lows[j]),
                        "direction": "bullish",
                        "explain": (
                            "Bullish order block: the last down-candle before price broke "
                            "structure upward. This zone is where the move originated — a "
                            "pullback into it (if it holds) is a common continuation entry."
                        ),
                    })
                    break
        elif row["bos_down"] or (row["choch"] and row["trend"] == "bear"):
            for j in range(i - 1, max(i - lookback, -1), -1):
                if closes[j] > opens[j]:  # last bullish candle before the down-move
                    blocks.append({
                        "time_start": int(times[j]),
                        "time_end": int(times[i]),
                        "top": float(highs[j]),
                        "bottom": float(lows[j]),
                        "direction": "bearish",
                        "explain": (
                            "Bearish order block: the last up-candle before price broke "
                            "structure downward — the origin of the down-move, and a common "
                            "zone for a continuation entry on a pullback."
                        ),
                    })
                    break

    return blocks[-15:]  # cap so the chart doesn't get cluttered on long histories


def _build_levels(trade_plan: dict | None) -> list[dict]:
    if not trade_plan or trade_plan.get("recommendation") == "no_trade":
        return []

    reasons_for = trade_plan.get("reasons_for") or []
    reasons_against = trade_plan.get("reasons_against") or []
    invalidation = trade_plan.get("invalidation")

    def explain_entry():
        text = "AI-selected entry zone."
        if reasons_for:
            text += " Supporting evidence: " + " ".join(reasons_for[:2])
        return text

    levels = []
    if trade_plan.get("entry_low") is not None:
        levels.append({
            "type": "entry_low", "price": trade_plan["entry_low"], "label": "Entry Low",
            "color": "#26a69a", "explain": explain_entry(),
        })
    if trade_plan.get("entry_high") is not None:
        levels.append({
            "type": "entry_high", "price": trade_plan["entry_high"], "label": "Entry High",
            "color": "#26a69a", "explain": explain_entry(),
        })
    if trade_plan.get("stop_loss") is not None:
        text = "AI-calculated stop loss — the price level that invalidates this thesis."
        if invalidation:
            text = invalidation
        levels.append({
            "type": "stop_loss", "price": trade_plan["stop_loss"], "label": "Stop Loss",
            "color": "#ef5350", "explain": text,
        })
    if trade_plan.get("take_profit_1") is not None:
        levels.append({
            "type": "take_profit_1", "price": trade_plan["take_profit_1"], "label": "TP1",
            "color": "#26a69a",
            "explain": "First take-profit target. " + (
                (" ".join(reasons_for[:1])) if reasons_for else ""
            ),
        })
    if trade_plan.get("take_profit_2") is not None:
        levels.append({
            "type": "take_profit_2", "price": trade_plan["take_profit_2"], "label": "TP2",
            "color": "#1b7a6f",
            "explain": "Extended take-profit target if momentum continues past TP1.",
        })

    if reasons_against:
        levels.append({
            "type": "risk_note", "price": None, "label": "Risks",
            "color": "#ef5350", "explain": " ".join(reasons_against[:2]),
        })

    return levels
