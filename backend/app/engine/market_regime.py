"""Market regime classification.

Every symbol's score should inherit this context — a bullish altcoin setup
means something different in a risk-on market than a risk-off one. Computed
deterministically from BTC's own trend/structure plus breadth across the
scanned universe (fraction of coins currently bullish) — nothing fetched
beyond what the scanner already has, nothing invented.
"""


def classify_regime(btc_features: dict | None, scored: list) -> dict:
    """`scored` is the background scanner's list of
    (total_score, score_breakdown, history_stats, ticker, features) tuples
    for everything scanned this cycle."""
    bullish = 0
    bearish = 0
    counted = 0
    for _, _, _, _, features in scored:
        ind = (features or {}).get("indicators_4h") or {}
        vote = ind.get("trend_vs_ema50")
        if vote == "above":
            bullish += 1
            counted += 1
        elif vote == "below":
            bearish += 1
            counted += 1

    breadth_bullish_pct = round(bullish / counted * 100, 1) if counted else 0.0
    breadth_bearish_pct = round(bearish / counted * 100, 1) if counted else 0.0

    btc_ind_1d = (btc_features or {}).get("indicators_1d") or {}
    btc_ind_4h = (btc_features or {}).get("indicators_4h") or {}
    btc_trend = btc_ind_1d.get("trend_vs_ema50") or btc_ind_4h.get("trend_vs_ema50")
    btc_adx = btc_ind_4h.get("adx14") or 0
    btc_trend_label = (
        "bull" if btc_trend == "above" else "bear" if btc_trend == "below" else "neutral"
    )

    if btc_trend_label == "bull" and breadth_bullish_pct >= 60:
        label, trend = "risk_on", "bullish"
    elif btc_trend_label == "bear" and breadth_bullish_pct <= 40:
        label, trend = "risk_off", "bearish"
    elif btc_adx < 20 and 40 <= breadth_bullish_pct <= 60:
        label, trend = "mixed", "ranging"
    else:
        label, trend = "mixed", "transitional"

    # Confidence: how extreme/aligned the breadth and BTC trend strength are.
    breadth_extremity = abs(breadth_bullish_pct - 50) * 2  # 0-100
    confidence = round(min(100, breadth_extremity * 0.6 + min(btc_adx, 40) / 40 * 100 * 0.4))

    summary = (
        f"BTC is {btc_trend_label} (4h ADX {btc_adx:.1f}); "
        f"{breadth_bullish_pct}% of the scanned universe ({counted} symbols) is "
        f"trading above its 4h EMA50, {breadth_bearish_pct}% below."
    )

    return {
        "label": label,
        "trend": trend,
        "confidence": confidence,
        "btc_trend": btc_trend_label,
        "breadth_bullish_pct": breadth_bullish_pct,
        "breadth_bearish_pct": breadth_bearish_pct,
        "universe_size": counted,
        "summary": summary,
    }
