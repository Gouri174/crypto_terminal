"""Composite confidence — agreement between independent signals, not the
deterministic score restated. app/engine/scoring.py's total is what ranks
symbols against each other; this is a separate number, shown to the user
as "confidence," built specifically to reward signals agreeing with each
other and penalize ones that conflict — a high score with a contradicting
historical match should read as LESS trustworthy than the raw score alone
would suggest.
"""

_WEIGHTS = {
    "trend": 0.25, "history": 0.20, "ml": 0.15, "structure": 0.15,
    "volume": 0.10, "funding": 0.05, "regime": 0.05, "sentiment": 0.05,
}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _history_direction(history_stats: dict | None) -> str | None:
    if not history_stats:
        return None
    mean_return = history_stats.get("mean_return_pct", 0)
    if mean_return > 0:
        return "long"
    if mean_return < 0:
        return "short"
    return None


def compute_confidence(
    direction: str,
    breakdown: dict,
    features: dict,
    history_stats: dict | None,
    ml_prediction: dict | None,
) -> dict:
    """direction: the deterministic call from decision.decide_direction().
    "no_trade" always returns 0 confidence — there's no direction to be
    confident about."""
    if direction not in ("long", "short"):
        return {"confidence": 0, "components": {}, "penalties": []}

    # Direction-agnostic component strengths, normalized to 0-1 against
    # each component's own max (these already measure "how clean is this
    # signal," not "which way does it point" — see scoring.py).
    trend = _clamp01(breakdown.get("trend", 0) / 25)
    structure = _clamp01(breakdown.get("structure", 0) / 15)
    volume = _clamp01(breakdown.get("volume", 0) / 10)
    funding = _clamp01(breakdown.get("funding", 0) / 10)
    regime = _clamp01((breakdown.get("regime", 0) + 5) / 10)
    sentiment = _clamp01((breakdown.get("sentiment", 0) + 3) / 6)

    # History and ML DO need to agree with the chosen direction specifically
    # — a strong historical hit rate in the opposite direction is evidence
    # against this trade, not for it.
    hist_dir = _history_direction(history_stats)
    if hist_dir is None:
        history = 0.5  # no data yet — neutral, not penalized for absence
    elif hist_dir == direction:
        win_rate = history_stats.get("win_rate", 50)
        history = _clamp01(0.5 + abs(win_rate - 50) / 100)
    else:
        history = 0.0  # active disagreement

    # win_probability isn't computed per-direction in this app (ml_model.py
    # predicts P(win) for whatever setup was scored) — used directly as an
    # agreement strength, defaulting to neutral when unavailable.
    ml = ml_prediction.get("win_probability") if ml_prediction else None
    ml = ml if ml is not None else 0.5

    components = {
        "trend": round(trend, 2), "history": round(history, 2), "ml": round(ml, 2),
        "structure": round(structure, 2), "volume": round(volume, 2),
        "funding": round(funding, 2), "regime": round(regime, 2), "sentiment": round(sentiment, 2),
    }
    weighted = sum(_WEIGHTS[k] * v for k, v in components.items()) * 100

    penalties = []
    if hist_dir is not None and hist_dir != direction:
        weighted -= 15
        penalties.append("Historical similarity points the opposite direction")

    ls_ratio = features.get("long_short_ratio")
    if ls_ratio is not None and (ls_ratio > 2.5 or ls_ratio < 0.4):
        weighted -= 8
        penalties.append("Crowded positioning (long/short ratio extreme)")

    cross = features.get("cross_exchange") or {}
    spread = cross.get("price_spread_pct")
    if spread is not None and spread > 0.5:
        weighted -= 5
        penalties.append("Wide cross-exchange spread (liquidity stress)")

    ind_4h = features.get("indicators_4h") or {}
    atr14 = ind_4h.get("atr14")
    last_close = ind_4h.get("last_close")
    if atr14 and last_close and (atr14 / last_close) > 0.05:
        weighted -= 5
        penalties.append("Unusually high volatility (ATR over 5% of price)")

    confidence = round(max(0.0, min(100.0, weighted)))
    return {"confidence": confidence, "components": components, "penalties": penalties}
