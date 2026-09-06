"""Expected Value engine — Karma V2.1 Phase 1.

Computes TP1/TP2/TP3/stop probabilities and an expected-R figure from
REAL, ALREADY-RESOLVED TradeOutcome history — frequency tables with
explicit sample sizes, never a trained model. This module does not touch
scoring.py, does not change which trades get taken, and does not replace
`score`/`confidence` anywhere — see trade_outcomes.py:open_trade_outcome()
for where this gets attached to a new trade (as an ADDITIONAL field,
"expected_value" on TradeOutcome) and trade_manager.py for how the same
underlying probabilities get reused, conditioned on live stage, for open
trades.

Why frequency tables, not a trained classifier: the read-only V2.1
forensic audit (karma_v2_1_model_improvement_report.md) explicitly found
that training real ML models on this trade count would overfit badly —
TP3 has only 13 positive examples in the entire 86-trade dataset, and a
chronological split would leave single digits in validation. A simple
conditional frequency table with a stated sample size is honest about its
own uncertainty in a way a trained model's point-estimate isn't; if a
requested conditioning is too thin, this backs off to a coarser one and
says so, rather than returning an overconfident number.
"""

import math

from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import TradeOutcome

MIN_SAMPLE = 5
_TRADED_STATUSES = ("closed_win", "closed_loss")


def _traded_rows() -> list[TradeOutcome]:
    session = SessionLocal()
    try:
        return (
            session.execute(select(TradeOutcome).where(TradeOutcome.status.in_(_TRADED_STATUSES)))
            .scalars()
            .all()
        )
    finally:
        session.close()


def _wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float | None, float | None]:
    if n == 0:
        return (None, None)
    phat = successes / n
    denom = 1 + z**2 / n
    center = phat + z**2 / (2 * n)
    half = z * math.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2))
    return (round(max(0.0, (center - half) / denom) * 100, 1), round(min(1.0, (center + half) / denom) * 100, 1))


def _rate(rows: list[TradeOutcome], predicate) -> dict:
    n = len(rows)
    successes = sum(1 for r in rows if predicate(r))
    lo, hi = _wilson_ci(successes, n)
    return {"probability_pct": round(successes / n * 100, 1) if n else None, "ci_95": (lo, hi), "n": n}


def _filtered(rows: list[TradeOutcome], direction: str | None, entry_quality: str | None, market_regime: str | None) -> list[TradeOutcome]:
    sub = rows
    if direction is not None:
        sub = [r for r in sub if r.direction == direction]
    if entry_quality is not None:
        sub = [r for r in sub if r.entry_quality == entry_quality]
    if market_regime is not None:
        sub = [r for r in sub if r.market_regime == market_regime]
    return sub


def _rate_with_backoff(rows: list[TradeOutcome], predicate, direction, entry_quality, market_regime, min_sample: int = MIN_SAMPLE) -> dict:
    """Tries the fully-conditioned slice first (direction + entry_quality +
    regime), then backs off one condition at a time, then falls back to
    the unconditioned aggregate — never silently reports a number from a
    slice smaller than min_sample when a coarser one is available."""
    attempts = [
        ("direction+entry_quality+regime", direction, entry_quality, market_regime),
        ("direction+entry_quality", direction, entry_quality, None),
        ("entry_quality", None, entry_quality, None),
        ("direction", direction, None, None),
        ("unconditioned", None, None, None),
    ]
    for label, d, eq, mr in attempts:
        sub = _filtered(rows, d, eq, mr)
        if len(sub) >= min_sample:
            result = _rate(sub, predicate)
            result["conditioning_used"] = label
            return result
    # even the unconditioned set is below min_sample (only possible very early)
    sub = rows
    result = _rate(sub, predicate)
    result["conditioning_used"] = "unconditioned"
    result["note"] = f"Even the unconditioned sample (n={len(sub)}) is below min_sample={min_sample} — probability is unreliable."
    return result


def historical_tp_probabilities(
    direction: str | None = None,
    entry_quality: str | None = None,
    market_regime: str | None = None,
    min_sample: int = MIN_SAMPLE,
) -> dict:
    """P(TP1), P(stop before TP1) from ALL entered trades matching the
    requested conditioning (with backoff); P(TP2|TP1) and P(TP3|TP2) from
    the subset that actually reached TP1/TP2 respectively — each with its
    own independent backoff, since "reached TP1" is itself a filter that
    shrinks the conditionable population further."""
    rows = _traded_rows()

    tp1 = _rate_with_backoff(rows, lambda r: bool(r.tp1_hit), direction, entry_quality, market_regime, min_sample)
    stop_before_tp1 = _rate_with_backoff(
        rows, lambda r: bool(r.stop_hit and not r.tp1_hit), direction, entry_quality, market_regime, min_sample
    )

    tp1_rows = [r for r in rows if r.tp1_hit]
    tp2_given_tp1 = _rate_with_backoff(tp1_rows, lambda r: bool(r.tp2_hit), direction, entry_quality, market_regime, min_sample)

    tp2_rows = [r for r in rows if r.tp2_hit]
    tp3_given_tp2 = _rate_with_backoff(tp2_rows, lambda r: bool(r.tp3_hit), direction, entry_quality, market_regime, min_sample)

    return {
        "tp1_probability": tp1,
        "tp2_given_tp1_probability": tp2_given_tp1,
        "tp3_given_tp2_probability": tp3_given_tp2,
        "stop_before_tp1_probability": stop_before_tp1,
    }


def compute_expected_value(
    risk_reward: dict,
    direction: str | None = None,
    entry_quality: str | None = None,
    market_regime: str | None = None,
    min_sample: int = MIN_SAMPLE,
) -> dict:
    """Expected R-multiple at issuance: P(TP1) * reward_to_tp1_in_R -
    P(stop_before_TP1) * 1R. Deliberately conservative — like the V2.1
    report's own EV audit, this does NOT credit TP2/TP3 continuation
    upside, so treat the sign and relative ranking as informative, not the
    absolute number as a precise expected-profit figure. `risk_reward` is
    the dict already produced by entry_flags.compute_risk_reward() — this
    function adds probabilities on top, it does not compute risk/reward
    itself."""
    probs = historical_tp_probabilities(direction, entry_quality, market_regime, min_sample)
    tp1 = probs["tp1_probability"]
    stop = probs["stop_before_tp1_probability"]

    risk_pct = risk_reward.get("risk_to_sl_pct")
    reward_tp1_pct = risk_reward.get("reward_to_tp1_pct")

    expected_r = None
    if risk_pct and reward_tp1_pct is not None and tp1["probability_pct"] is not None and stop["probability_pct"] is not None:
        p_tp1 = tp1["probability_pct"] / 100
        p_stop = stop["probability_pct"] / 100
        expected_r = round((p_tp1 * (reward_tp1_pct / risk_pct)) - (p_stop * 1.0), 3)

    return {
        "expected_r": expected_r,
        "expected_reward_pct": reward_tp1_pct,
        "expected_risk_pct": risk_pct,
        "tp1_probability_pct": tp1["probability_pct"],
        "tp2_given_tp1_probability_pct": probs["tp2_given_tp1_probability"]["probability_pct"],
        "tp3_given_tp2_probability_pct": probs["tp3_given_tp2_probability"]["probability_pct"],
        "stop_before_tp1_probability_pct": stop["probability_pct"],
        "sample_size": tp1["n"],
        "conditioning_used": tp1["conditioning_used"],
        "note": (
            "Frequency-table estimate from resolved TradeOutcome history, not a "
            "trained model — see this module's docstring. Does not credit TP2/TP3 "
            "continuation upside, so treat as directional, not a precise expected-profit figure."
        ),
    }
