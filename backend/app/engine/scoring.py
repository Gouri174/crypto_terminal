"""Deterministic, transparent opportunity scoring.

This replaces "ask the LLM for a confidence number" with a fixed formula
over data already computed. Claude's job is to EXPLAIN this score using the
component breakdown and historical evidence — never to invent it.
"""


def _tf(features: dict, tf: str) -> dict:
    return features.get(f"indicators_{tf}") or {}


def _structure(features: dict, tf: str) -> dict:
    return features.get(f"structure_{tf}") or {}


def score_opportunity(features: dict, history_stats: dict | None) -> dict:
    trend = _trend_score(features)
    momentum = _momentum_score(features)
    volume = _volume_score(features)
    funding = _funding_score(features)
    structure = _structure_score(features)
    history = _history_score(history_stats)
    risk = _risk_penalty(features)

    total = trend + momentum + volume + funding + structure + history + risk
    total = max(0.0, min(100.0, total))

    return {
        "trend": trend,
        "momentum": momentum,
        "volume": volume,
        "funding": funding,
        "structure": structure,
        "history": history,
        "risk": risk,
        "total": round(total, 1),
    }


def _trend_score(features: dict) -> float:
    votes = [
        _tf(features, tf).get("trend_vs_ema50")
        for tf in ("1h", "4h", "1d")
        if _tf(features, tf).get("trend_vs_ema50")
    ]
    alignment = 0.0
    if votes:
        above = votes.count("above")
        below = votes.count("below")
        alignment = max(above, below) / len(votes)

    adx = _tf(features, "4h").get("adx14") or 0
    return round(alignment * 15 + min(adx, 40) / 40 * 10, 2)


def _momentum_score(features: dict) -> float:
    rsi = _tf(features, "4h").get("rsi14")
    macd_hist = _tf(features, "4h").get("macd_hist")

    score = 0.0
    if rsi is not None:
        if 40 <= rsi <= 65:
            score += 8
        elif rsi < 25 or rsi > 80:
            score += 2  # extreme momentum, lower quality entry
        else:
            score += 4
    if macd_hist is not None and macd_hist > 0:
        score += 7
    return round(score, 2)


def _volume_score(features: dict) -> float:
    ind = _tf(features, "4h")
    score = 0.0
    if (ind.get("obv_slope") or 0) > 0:
        score += 5
    if (ind.get("cmf") or 0) > 0:
        score += 3
    mfi = ind.get("mfi")
    if mfi is not None and 20 <= mfi <= 80:
        score += 2
    return round(score, 2)


def _funding_score(features: dict) -> float:
    funding = features.get("funding_rate")
    if funding is None:
        return 0.0
    abs_funding = abs(funding)
    if abs_funding < 0.0005:
        return 10.0
    if abs_funding < 0.001:
        return 5.0
    return 0.0


def _structure_score(features: dict) -> float:
    struct = _structure(features, "4h")
    score = 0.0
    if struct.get("trend") not in (None, "neutral"):
        score += 6
    if struct.get("fvg_up") or struct.get("fvg_down"):
        score += 5
    if struct.get("choch"):
        score += 4
    return round(min(score, 15), 2)


def _history_score(history_stats: dict | None) -> float:
    if not history_stats or history_stats.get("sample_size", 0) < 20:
        return 0.0
    win_rate = history_stats["win_rate"]
    scaled = (win_rate - 50) / 50 * 15
    return round(max(-15.0, min(15.0, scaled)), 2)


def _risk_penalty(features: dict) -> float:
    ind = _tf(features, "4h")
    penalty = 0.0

    bb_pct = ind.get("bb_pct")
    if bb_pct is not None and (bb_pct > 1.0 or bb_pct < 0.0):
        penalty -= 6

    rsi = ind.get("rsi14")
    if rsi is not None and (rsi > 80 or rsi < 20):
        penalty -= 5

    stoch_rsi = ind.get("stoch_rsi")
    if stoch_rsi is not None and (stoch_rsi > 0.95 or stoch_rsi < 0.05):
        penalty -= 4

    atr14 = ind.get("atr14")
    last_close = features.get("indicators_4h", {}).get("last_close")
    if atr14 and last_close and (atr14 / last_close) > 0.05:
        penalty -= 3

    return round(max(-20.0, penalty), 2)
