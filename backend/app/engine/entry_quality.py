"""Entry-quality / exhaustion diagnostic — a hypothesis layer, not a
replacement for scoring.py.

Built after a forensic read of the first 7 resolved TradeOutcome rows (5 of
6 losses had a maxed momentum_score; the one win had the lowest momentum
score of all 7). That finding does NOT mean "momentum is bad" — see
_momentum_score() in scoring.py: a momentum_score of 15 actually requires
RSI in the MODERATE 40-65 band plus a positive MACD histogram, not an
extreme reading (extreme RSI scores only +2 there, explicitly flagged as
"lower quality entry"). So momentum_score alone cannot be the exhaustion
signal — whatever timing problem those losses shared has to come from
somewhere else. This module answers a genuinely different question from
scoring.py: given a direction has ALREADY been decided (decide_direction),
is RIGHT NOW a good place to enter that direction, or is price already
extended away from where the setup was actually confirmed?

Hard constraints this module respects:
- Pure function of already-computed `features`/`breakdown` — no new API
  calls, no paid data, no LLM call. Same inputs scoring.py already has.
- Does NOT touch scoring.py's weights or `breakdown["total"]`. The
  existing score stays exactly as comparable before/after this module
  exists — verified in test_scoring_unchanged.py.
- Output is a deterministic CLASSIFICATION with concrete reasons, not a
  fabricated probability. "late"/"exhausted" are rule outputs, not
  statistical claims — this module has produced zero labeled outcomes at
  the time it was written, so it cannot honestly claim any predictive
  value yet (see trade_reports.py:entry_quality_performance, which will
  say "insufficient sample size" until real data says otherwise).
"""

_OVERBOUGHT_RSI = 80.0
_OVERSOLD_RSI = 20.0
_OVERBOUGHT_STOCH = 0.95
_OVERSOLD_STOCH = 0.05
_OVERBOUGHT_BB = 1.0
_OVERSOLD_BB = 0.0
_ATR_EXTENSION_MODERATE = 2.5
_ATR_EXTENSION_SEVERE = 3.5

# Mirrors decision.py:market_checklist's own structure_confirms threshold
# (structure_score >= 8) rather than inventing a second one.
_STRUCTURE_WEAK_BELOW = 8.0
_STRUCTURE_STRONG_AT_LEAST = 11.0
_MOMENTUM_STRONG_AT_LEAST = 11.0
_MOMENTUM_WEAK_AT_MOST = 4.0

_ENTRY_QUALITIES = ("excellent", "good", "neutral", "late", "exhausted", "invalid")


def _ind(features: dict, tf: str) -> dict:
    return features.get(f"indicators_{tf}") or {}


def _overbought_oversold(features: dict, direction: str) -> tuple[int, list[str]]:
    """How many independent timeframe/indicator readings show an extreme
    consistent with an overextended move in `direction`. Checked across
    1h/4h/1d deliberately — a single-timeframe overbought reading is
    common and often means nothing; agreement across timeframes is what
    actually flagged the worst loss in the forensic sample (BICOUSDT:
    RSI 72/91/94 across 1h/4h/1d)."""
    points = 0
    reasons: list[str] = []
    for tf in ("1h", "4h", "1d"):
        ind = _ind(features, tf)
        rsi = ind.get("rsi14")
        stoch = ind.get("stoch_rsi")
        bb = ind.get("bb_pct")
        if direction == "long":
            if rsi is not None and rsi > _OVERBOUGHT_RSI:
                points += 1
                reasons.append(f"{tf} RSI {rsi:.1f} overbought (>{_OVERBOUGHT_RSI:g})")
            if stoch is not None and stoch > _OVERBOUGHT_STOCH:
                points += 1
                reasons.append(f"{tf} stochRSI {stoch:.2f} extreme (>{_OVERBOUGHT_STOCH:g})")
            if bb is not None and bb > _OVERBOUGHT_BB:
                points += 1
                reasons.append(f"{tf} price above upper Bollinger Band (bb_pct {bb:.2f})")
        elif direction == "short":
            if rsi is not None and rsi < _OVERSOLD_RSI:
                points += 1
                reasons.append(f"{tf} RSI {rsi:.1f} oversold (<{_OVERSOLD_RSI:g})")
            if stoch is not None and stoch < _OVERSOLD_STOCH:
                points += 1
                reasons.append(f"{tf} stochRSI {stoch:.2f} extreme (<{_OVERSOLD_STOCH:g})")
            if bb is not None and bb < _OVERSOLD_BB:
                points += 1
                reasons.append(f"{tf} price below lower Bollinger Band (bb_pct {bb:.2f})")
    return points, reasons


def _atr_extension(features: dict, direction: str) -> tuple[int, list[str]]:
    """Distance from the 4h EMA20 expressed in ATR units — same formula
    trade_outcomes.py:_capture_entry_indicators already uses for
    atr_distance_to_ema20, reused here rather than recomputed differently."""
    ind = _ind(features, "4h")
    last_close, ema20, atr14 = ind.get("last_close"), ind.get("ema20"), ind.get("atr14")
    if not (last_close and ema20 and atr14):
        return 0, []
    atr_distance = (last_close - ema20) / atr14

    if direction == "long" and atr_distance > _ATR_EXTENSION_MODERATE:
        pts = 2 if atr_distance > _ATR_EXTENSION_SEVERE else 1
        return pts, [f"price {atr_distance:.1f} ATR above 4h EMA20 (extended)"]
    if direction == "short" and atr_distance < -_ATR_EXTENSION_MODERATE:
        pts = 2 if atr_distance < -_ATR_EXTENSION_SEVERE else 1
        return pts, [f"price {abs(atr_distance):.1f} ATR below 4h EMA20 (extended)"]
    return 0, []


def _structure_fresh(features: dict, direction: str) -> bool:
    """Direction-specific — structure_score (scoring.py) only checks
    whether SOME structure signal fired, not which way. A long needs a
    bullish BOS/FVG on the 4h, not just any FVG."""
    s4h = features.get("structure_4h") or {}
    if direction == "long":
        return bool(s4h.get("fvg_up") or s4h.get("bos_up"))
    if direction == "short":
        return bool(s4h.get("fvg_down") or s4h.get("bos_down"))
    return False


def _mtf_alignment(features: dict, direction: str) -> tuple[int, int]:
    """(agree, total) — how many of the available 1h/4h/1d trend_vs_ema50
    votes agree with `direction`. Same vote source decide_direction() and
    scoring.py._trend_score() already use, just re-tallied against a
    specific direction rather than taking the majority."""
    votes = [_ind(features, tf).get("trend_vs_ema50") for tf in ("1h", "4h", "1d")]
    votes = [v for v in votes if v]
    if not votes:
        return 0, 0
    wants = "above" if direction == "long" else "below"
    return sum(1 for v in votes if v == wants), len(votes)


def classify_entry_quality(features: dict, direction: str, breakdown: dict) -> dict:
    """Returns {"entry_quality", "entry_quality_score", "entry_quality_reasons"}.

    entry_quality_score is a separate 0-100 diagnostic number for THIS
    module only — never fed back into scoring.py's total or
    confidence.py's confidence. It measures entry TIMING quality, not
    setup quality (that's what score/confidence already measure)."""
    if direction not in ("long", "short"):
        return {
            "entry_quality": "invalid",
            "entry_quality_score": None,
            "entry_quality_reasons": ["No directional setup (direction=no_trade) — entry quality not applicable"],
        }

    momentum_score = breakdown.get("momentum", 0.0)
    structure_score = breakdown.get("structure", 0.0)

    ob_points, ob_reasons = _overbought_oversold(features, direction)
    atr_points, atr_reasons = _atr_extension(features, direction)
    extension = ob_points + atr_points

    fresh = _structure_fresh(features, direction)
    agree, total_votes = _mtf_alignment(features, direction)

    momentum_strong = momentum_score >= _MOMENTUM_STRONG_AT_LEAST
    momentum_weak = momentum_score <= _MOMENTUM_WEAK_AT_MOST
    structure_strong = structure_score >= _STRUCTURE_STRONG_AT_LEAST
    structure_weak = structure_score < _STRUCTURE_WEAK_BELOW

    # Deterministic rules, first match wins. Severe multi-signal extension
    # (>=4 independent overbought/oversold readings, or a very large
    # ATR-distance) is treated as exhausted REGARDLESS of structure —
    # found necessary against the forensic BICOUSDT case, whose structure
    # looked fine (bullish FVGs present) right before a -44% reversal.
    # Moderate extension only becomes "exhausted" when structure isn't
    # backing it up either; on its own it's "late," not a hard stop.
    if extension >= 4:
        quality = "exhausted"
    elif extension >= 2 and (structure_weak or not fresh):
        quality = "exhausted"
    elif extension >= 1:
        quality = "late"
    elif momentum_weak and structure_weak:
        quality = "invalid"
    elif fresh and (momentum_strong or structure_strong):
        quality = "excellent"
    elif not structure_weak:
        quality = "good"
    else:
        quality = "neutral"

    reasons = [
        f"momentum_score {momentum_score:g}/15, structure_score {structure_score:g}/15",
        (
            f"{agree}/{total_votes} timeframes aligned with {direction}"
            if total_votes
            else "no timeframe trend votes available"
        ),
        (
            f"fresh 4h structure supporting {direction} (BOS/FVG)"
            if fresh
            else f"no fresh 4h structure confirming {direction} right now"
        ),
        *ob_reasons,
        *atr_reasons,
    ]

    eq_score = 50.0
    eq_score -= extension * 8
    eq_score += 15 if fresh else -5
    eq_score += 10 if momentum_strong else (-5 if momentum_weak else 0)
    eq_score += 10 if structure_strong else (-8 if structure_weak else 0)
    if total_votes:
        eq_score += (agree / total_votes - 0.5) * 20
    eq_score = round(max(0.0, min(100.0, eq_score)), 1)

    return {"entry_quality": quality, "entry_quality_score": eq_score, "entry_quality_reasons": reasons}
