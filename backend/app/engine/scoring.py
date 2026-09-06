"""Deterministic, transparent opportunity scoring.

This replaces "ask the LLM for a confidence number" with a fixed formula
over data already computed. Claude's job is to EXPLAIN this score using the
component breakdown and historical evidence — never to invent it.
"""

# Bump whenever the weights or component set change materially — recorded
# on every TradeOutcome row so a future "does the formula version predict
# performance" analysis can actually separate results by which formula
# produced them, instead of silently mixing scores from different eras.
#
# 2.1 (Karma V2.1, see backend/karma_v2_1_model_improvement_report.md,
# read-only audit of 86 resolved trades): _momentum_score and
# _volume_score changed, both with evidence that survived a stratified-
# by-entry_quality robustness check (Section 2 of that report) — momentum
# reduced (odds ratio 0.691, negative net lift after controlling for
# entry_quality), volume increased (odds ratio 2.215, POSITIVE lift in
# every testable entry_quality stratum). _structure_score's FVG term
# increased on weaker evidence (odds ratio 1.8, small n=16) — flagged as
# medium-risk in that report, not the same confidence as momentum/volume.
# Trend, History, Funding, and Regime are DELIBERATELY UNCHANGED: the same
# report found Trend's apparent edge does NOT survive the same stratified
# check (sign flips between entry_quality strata) and History is likely
# confounded with a specific underperforming symbol group rather than an
# independent signal — its own Rules 11/12 say "hold, do not act yet."
SCORE_FORMULA_VERSION = "2.1"


def _tf(features: dict, tf: str) -> dict:
    return features.get(f"indicators_{tf}") or {}


def _structure(features: dict, tf: str) -> dict:
    return features.get(f"structure_{tf}") or {}


def score_opportunity(
    features: dict,
    history_stats: dict | None,
    regime: dict | None = None,
    ml_prediction: dict | None = None,
) -> dict:
    trend = _trend_score(features)
    momentum = _momentum_score(features)
    volume = _volume_score(features)
    funding = _funding_score(features)
    structure = _structure_score(features)
    history = _history_score(history_stats)
    regime_score = _regime_score(features, regime)
    ml = _ml_score(ml_prediction)
    sentiment = _sentiment_score(features)
    liquidity = _liquidity_score(features)
    risk = _risk_penalty(features)

    total = (
        trend + momentum + volume + funding + structure + history
        + regime_score + ml + sentiment + liquidity + risk
    )
    total = max(0.0, min(100.0, total))

    return {
        "trend": trend,
        "momentum": momentum,
        "volume": volume,
        "funding": funding,
        "structure": structure,
        "history": history,
        "regime": regime_score,
        "ml": ml,
        "liquidity": liquidity,
        "sentiment": sentiment,
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
    """V2.1: max contribution reduced from 15 to 12 (karma_v2_1 report,
    Rule 3 — odds ratio 0.691, i.e. a maxed-momentum trade in the 86-trade
    audit was LESS likely to win, and the effect held even after
    controlling for entry_quality). The RSI zone was also narrowed and
    re-shaped rather than just uniformly scaled down: 50-70 is where the
    audit found winners concentrate (Rule 4, odds ratio 3.135 — the single
    strongest odds ratio found in that report), while 25-50 ("RSI 30-49"
    in the report's own language) had a 92.3% loss rate on n=13 (Rule 1) —
    previously scored the same as a perfectly healthy reading; now scored
    like the red flag the data shows it to be."""
    rsi = _tf(features, "4h").get("rsi14")
    macd_hist = _tf(features, "4h").get("macd_hist")

    score = 0.0
    if rsi is not None:
        if 50 <= rsi < 70:
            score += 7
        elif 25 <= rsi < 50:
            score += 1  # V2.1: the specific "chop zone" the audit flagged as its strongest single red flag
        elif rsi < 25 or rsi >= 80:
            score += 1  # extreme momentum/exhaustion — reduced from 2
        else:
            score += 3  # 70-80: elevated but not yet the extreme-exhaustion zone
    if macd_hist is not None and macd_hist > 0:
        score += 5  # V2.1: reduced from 7 (part of the overall momentum de-weighting, Rule 3)
    return round(score, 2)


def _volume_score(features: dict) -> float:
    """V2.1: max contribution increased from 10 to 13 (karma_v2_1 report,
    Rule 2 — odds ratio 2.215, and the ONLY feature audited whose win-rate
    lift stayed positive in every entry_quality stratum tested, i.e. it
    wasn't just riding entry_quality's own known edge)."""
    ind = _tf(features, "4h")
    score = 0.0
    if (ind.get("obv_slope") or 0) > 0:
        score += 6  # V2.1: was 5
    if (ind.get("cmf") or 0) > 0:
        score += 5  # V2.1: was 3
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
    """V2.1: FVG term increased from 5 to 7 (karma_v2_1 report, Rule 10 —
    odds ratio 1.8, win rate 50.0% vs 35.7% without, positive in both
    testable entry_quality strata). Flagged as MEDIUM risk in that report
    (n=16 trades had FVG data at all) — a smaller, more cautious bump than
    momentum/volume's changes above, not the same confidence level."""
    struct = _structure(features, "4h")
    score = 0.0
    if struct.get("trend") not in (None, "neutral"):
        score += 6
    if struct.get("fvg_up") or struct.get("fvg_down"):
        score += 7  # V2.1: was 5
    if struct.get("choch"):
        score += 4
    return round(min(score, 17), 2)


def _history_score(history_stats: dict | None) -> float:
    if not history_stats or history_stats.get("sample_size", 0) < 20:
        return 0.0
    win_rate = history_stats["win_rate"]
    scaled = (win_rate - 50) / 50 * 15
    return round(max(-15.0, min(15.0, scaled)), 2)


def _regime_score(features: dict, regime: dict | None) -> float:
    """Rewards a symbol whose own trend agrees with the overall market
    regime, penalizes one fighting it. Neutral when the regime is mixed or
    hasn't been computed yet (e.g. the very first scan cycle)."""
    if not regime or regime.get("trend") not in ("bullish", "bearish"):
        return 0.0

    votes = [
        _tf(features, tf).get("trend_vs_ema50")
        for tf in ("1h", "4h", "1d")
        if _tf(features, tf).get("trend_vs_ema50")
    ]
    if not votes:
        return 0.0
    above, below = votes.count("above"), votes.count("below")
    symbol_bullish, symbol_bearish = above > below, below > above

    regime_bullish = regime["trend"] == "bullish"
    if (regime_bullish and symbol_bullish) or (not regime_bullish and symbol_bearish):
        return 5.0
    if (regime_bullish and symbol_bearish) or (not regime_bullish and symbol_bullish):
        return -5.0
    return 0.0


def _ml_score(ml_prediction: dict | None) -> float:
    """From the trained XGBoost classifiers (see ml_model.py) — Claude
    explains this number, it doesn't set it. Zero when the models haven't
    been trained yet or this symbol lacks enough history to predict on
    (ml_model.py returns None rather than a guess in that case).

    Deliberately low weight: as trained, these models show a real but weak
    edge on held-out data (test AUC ~0.54 — see ml_model.py's docstring).
    A weak-signal model shouldn't move the score as much as well-
    established structural factors; this weight should only increase if a
    retrain shows the models genuinely improving (check test_auc)."""
    if not ml_prediction:
        return 0.0
    win_prob = ml_prediction.get("win_probability")
    if win_prob is None:
        return 0.0

    score = (win_prob - 0.5) * 16  # range [-8, +8]
    drawdown_prob = ml_prediction.get("large_drawdown_probability")
    if drawdown_prob is not None:
        score -= drawdown_prob * 4  # further penalty if a large adverse move looks likely
    return round(max(-10.0, min(8.0, score)), 2)


def _sentiment_score(features: dict) -> float:
    """Deliberately tiny and one-directional: extreme Fear & Greed readings
    only. Reddit mention counts are passed to Claude as raw context (see
    news_engine.py) but NOT scored numerically here — a spike in mentions
    could mean bullish excitement or panic-selling discussion, and
    distinguishing those needs actual reading, not a mention count. Don't
    fabricate a directional signal from ambiguous data."""
    fear_greed = features.get("fear_greed")
    if not fear_greed or fear_greed.get("value") is None:
        return 0.0
    value = fear_greed["value"]
    if value <= 20:
        return 3.0  # extreme fear — mildly contrarian-bullish, weak signal
    if value >= 80:
        return -3.0  # extreme greed — euphoria/overextension risk
    return 0.0


def _liquidity_score(features: dict) -> float:
    """Cross-exchange price/funding divergence (Binance vs Bybit vs OKX —
    see cross_exchange.py) as a liquidity-health signal. Deliberately
    directionless: a wide spread doesn't tell you which way price will
    move, only that something is stressed across venues, which is worth a
    small caution flag either way — not a bullish/bearish call."""
    cross = features.get("cross_exchange")
    if not cross:
        return 0.0

    penalty = 0.0
    spread = cross.get("price_spread_pct")
    if spread is not None and spread > 0.5:
        penalty -= 3.0

    funding_div = cross.get("funding_divergence")
    if funding_div is not None and abs(funding_div) > 0.001:
        penalty -= 2.0

    return round(penalty, 2)


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
