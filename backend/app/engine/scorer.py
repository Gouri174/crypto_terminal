def score_features(features: dict) -> float:
    """Deterministic pre-filter score (0-100) used to rank candidates before
    spending LLM calls on them. Rewards multi-timeframe trend alignment,
    momentum in a healthy (non-extreme) zone, and trend strength."""
    score = 0.0

    ind_1h = features.get("indicators_1h") or {}
    ind_4h = features.get("indicators_4h") or {}
    ind_1d = features.get("indicators_1d") or {}

    trend_votes = [
        ind.get("trend_vs_ema50")
        for ind in (ind_1h, ind_4h, ind_1d)
        if ind.get("trend_vs_ema50")
    ]
    if trend_votes:
        above = trend_votes.count("above")
        below = trend_votes.count("below")
        alignment = max(above, below) / len(trend_votes)
        score += alignment * 40

    rsi = ind_4h.get("rsi14")
    if rsi is not None:
        if 45 <= rsi <= 65 or 35 <= rsi <= 55:
            score += 20
        elif rsi < 25 or rsi > 80:
            score += 5  # extreme, likely overextended

    adx = ind_4h.get("adx14")
    if adx is not None:
        score += min(adx, 40) / 40 * 25

    macd_hist = ind_4h.get("macd_hist")
    if macd_hist is not None:
        score += 10 if macd_hist > 0 else 0

    funding = features.get("funding_rate")
    if funding is not None and abs(funding) < 0.0005:
        score += 5  # neutral funding is healthier than crowded leverage

    return round(min(score, 100), 2)


def direction_hint(features: dict) -> str:
    ind_4h = features.get("indicators_4h") or {}
    trend = ind_4h.get("trend_vs_ema50")
    if trend == "above":
        return "long"
    if trend == "below":
        return "short"
    return "no_trade"
