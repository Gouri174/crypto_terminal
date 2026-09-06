"""Market Health Score — Karma V3.2 Phase C.

A 0-100 "is today a good day to trade at all" score, built entirely from
data this app already computes every scan cycle — MarketRegimeState
(market_regime.py, read-only here, never modified), the cached Fear &
Greed index, and the most recent ScanSnapshot cycle's own per-symbol score
breakdowns (risk/funding components scoring.py already produces). No new
live data source is added; two components are honestly reported as
"proxy" or "unavailable" rather than inventing a new aggregate metric
that doesn't exist anywhere in this codebase yet:

- Volatility Quality: no aggregate ATR-percentile exists anywhere in this
  codebase. Proxied by the average `risk` score-breakdown component
  across the latest scan cycle (scoring.py's _risk_penalty already
  penalizes high-ATR entries per symbol; averaging it is the closest
  already-computed volatility signal, not a new one).
- News Stress: no aggregate news-stress metric exists (news_engine.py is
  per-symbol, not pooled). Reported as unavailable (neutral default),
  not fabricated from an ad-hoc aggregation built just for this score.
"""

from collections import defaultdict

from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import ScanSnapshot

_CATEGORY_BANDS = [
    (85, "Very Healthy", "Full risk allowed."),
    (70, "Healthy", "Trade A/B+ setups only."),
    (55, "Neutral", "Half size."),
    (40, "Weak", "Only exceptional setups."),
    (0, "Danger", "Avoid new trades."),
]


def _category_for(score: float) -> tuple[str, str]:
    for threshold, category, rec in _CATEGORY_BANDS:
        if score >= threshold:
            return category, rec
    return "Danger", "Avoid new trades."


def _latest_scan_rows() -> list[ScanSnapshot]:
    session = SessionLocal()
    try:
        latest_ts = session.execute(select(ScanSnapshot.timestamp).order_by(ScanSnapshot.timestamp.desc()).limit(1)).scalar_one_or_none()
        if latest_ts is None:
            return []
        return session.execute(select(ScanSnapshot).where(ScanSnapshot.timestamp == latest_ts)).scalars().all()
    finally:
        session.close()


def compute_market_health(
    regime: dict | None,
    fear_greed: dict | None,
    scan_rows: list[ScanSnapshot] | None = None,
) -> dict:
    """Pure function — everything is a parameter so this is testable
    without touching the DB or live data sources. `current_market_health`
    below is the thin wrapper that gathers real inputs."""
    components = {}

    # Trend alignment (0-20): regime's own confidence, already 0-100.
    confidence = (regime or {}).get("confidence")
    components["trend_alignment"] = round((confidence or 0) / 100 * 20, 1) if confidence is not None else 10.0

    # Breadth (0-20): how much of the universe agrees with the dominant direction.
    bull = (regime or {}).get("breadth_bullish_pct")
    bear = (regime or {}).get("breadth_bearish_pct")
    if bull is not None and bear is not None:
        components["breadth"] = round(max(bull, bear) / 100 * 20, 1)
    else:
        components["breadth"] = 10.0

    # Volatility quality (0-15): proxy via avg risk-penalty component this cycle.
    risk_scores = [r.score_breakdown.get("risk") for r in (scan_rows or []) if r.score_breakdown and r.score_breakdown.get("risk") is not None]
    if risk_scores:
        avg_risk = sum(risk_scores) / len(risk_scores)  # scoring.py's risk penalty ranges roughly [-20, 0]
        components["volatility_quality"] = round(max(0.0, min(15.0, (avg_risk + 20) / 20 * 15)), 1)
    else:
        components["volatility_quality"] = 7.5  # neutral default — no scan data available

    # Funding risk (0-10): avg funding score component this cycle (scoring.py range [0,10]).
    funding_scores = [r.score_breakdown.get("funding") for r in (scan_rows or []) if r.score_breakdown and r.score_breakdown.get("funding") is not None]
    components["funding_risk"] = round(max(0.0, min(10.0, sum(funding_scores) / len(funding_scores))), 1) if funding_scores else 5.0

    # Correlation risk (0-15): proxy via breadth EXTREMITY — a universe
    # moving overwhelmingly one direction is a highly-correlated,
    # concentrated market (see module docstring — this is a systemic-
    # correlation proxy, distinct from Portfolio Exposure's per-position
    # concentration, which uses actual open trades instead).
    if bull is not None and bear is not None:
        extremity = abs(bull - bear)  # 0 = perfectly balanced, 100 = everything one way
        components["correlation_risk"] = round(max(0.0, 15 - extremity / 100 * 15), 1)
    else:
        components["correlation_risk"] = 7.5

    # Fear & Greed (0-10): moderate is healthiest, extremes are penalized
    # (same "extremes are risk, not opportunity" philosophy as
    # scoring.py:_sentiment_score, applied at the market level here).
    fg_value = (fear_greed or {}).get("value")
    if fg_value is not None:
        distance_from_mid = abs(fg_value - 50)
        components["fear_greed"] = round(max(0.0, 10 - distance_from_mid / 50 * 10), 1)
    else:
        components["fear_greed"] = 5.0

    # News stress (0-10): NOT COMPUTED — see module docstring. Neutral default.
    components["news_stress"] = 5.0
    components["news_stress_note"] = "Not computed — no aggregate news-stress data source exists in this codebase yet."

    total = round(sum(v for k, v in components.items() if isinstance(v, (int, float))), 1)
    category, recommendation = _category_for(total)

    return {
        "score": total, "max_score": 100.0, "category": category, "recommendation": recommendation,
        "components": {
            "trend_alignment": {"score": components["trend_alignment"], "max": 20},
            "breadth": {"score": components["breadth"], "max": 20},
            "volatility_quality": {"score": components["volatility_quality"], "max": 15, "note": "Proxy via avg risk-penalty component, not a stored ATR percentile."},
            "funding_risk": {"score": components["funding_risk"], "max": 10},
            "correlation_risk": {"score": components["correlation_risk"], "max": 15, "note": "Systemic breadth-extremity proxy, distinct from Portfolio Exposure's position-level concentration."},
            "fear_greed": {"score": components["fear_greed"], "max": 10},
            "news_stress": {"score": components["news_stress"], "max": 10, "note": components["news_stress_note"]},
        },
        "inputs": {"regime": regime, "fear_greed": fear_greed, "n_scan_rows": len(scan_rows or [])},
    }


async def current_market_health() -> dict:
    from app.data_sources.fear_greed import get_cached_fear_greed
    from app.engine.background_scanner import load_current_regime

    regime = load_current_regime()
    fear_greed = await get_cached_fear_greed()
    scan_rows = _latest_scan_rows()
    return compute_market_health(regime, fear_greed, scan_rows)
