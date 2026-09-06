"""Trade Manager — Karma V2.1 Phase 2 ("TP Continuation Engine").

This is the Phase 2 that trade_outcomes.py's PredictionSnapshot fields
(tp1_probability/tp2_probability/tp3_probability, management_decision,
decision_reason) were explicitly built to eventually receive — see their
docstrings, which say Phase 1 leaves them NULL/boring on purpose and
Phase 2 would populate them "from a walk-forward-validated model ... they
must NEVER be filled by Claude or invented from the win-probability
number." This module honors that constraint: every probability here comes
from app/engine/expected_value.py's frequency tables (with sample size
and Wilson CI), never Claude, never a trained model, never invented.

Still analytics-only in the sense that matters: this computes a
RECOMMENDATION string and reason, it does not move a stop, close a
position, or change what update_open_trades()/_update_one() actually do
to a trade. Nothing here is executed — see trade_outcomes.py's own
lifecycle logic, which is completely unchanged by this module.
"""

from app.engine.expected_value import historical_tp_probabilities
from app.models.db_models import TradeOutcome

# Below this sample size, a stage-specific probability is reported but NOT
# used to drive a recommendation beyond HOLD — this project's own
# standing rule against tuning/deciding on tiny samples applies here too.
MIN_SAMPLE_FOR_RECOMMENDATION = 5

# Thresholds are the measured aggregate/entry_quality-conditioned rates
# from the V2.1 forensic report (P(TP2|TP1) ranges 80-100% across every
# entry_quality stratum with n>=5), not invented round numbers — a
# genuinely low continuation probability in this app's own history would
# be well below this band, so this is a "still clearly favorable" cut,
# not an arbitrarily chosen one.
HIGH_CONTINUATION_THRESHOLD_PCT = 65.0


def stage_probabilities(row: TradeOutcome, stage: str) -> dict:
    """Returns tp1_probability/tp2_probability/tp3_probability appropriate
    to the CURRENT stage — a target already reached reports 100.0 (it's a
    fact, not an estimate); a target not yet reachable from the current
    stage (e.g. tp3_probability before TP2 has hit) stays None rather than
    guessing forward across two conditional steps at once."""
    direction = row.direction
    entry_quality = row.entry_quality
    market_regime = row.market_regime

    if stage in ("PRE_ENTRY", "OPEN"):
        probs = historical_tp_probabilities(direction, entry_quality, market_regime)
        return {
            "tp1_probability": probs["tp1_probability"]["probability_pct"],
            "tp1_probability_n": probs["tp1_probability"]["n"],
            "tp1_probability_ci": probs["tp1_probability"]["ci_95"],
            "tp2_probability": None,
            "tp3_probability": None,
        }
    if stage == "TP1_REACHED":
        probs = historical_tp_probabilities(direction, entry_quality, market_regime)
        return {
            "tp1_probability": 100.0,
            "tp2_probability": probs["tp2_given_tp1_probability"]["probability_pct"],
            "tp2_probability_n": probs["tp2_given_tp1_probability"]["n"],
            "tp2_probability_ci": probs["tp2_given_tp1_probability"]["ci_95"],
            "tp3_probability": None,
        }
    if stage == "TP2_REACHED":
        probs = historical_tp_probabilities(direction, entry_quality, market_regime)
        return {
            "tp1_probability": 100.0,
            "tp2_probability": 100.0,
            "tp3_probability": probs["tp3_given_tp2_probability"]["probability_pct"],
            "tp3_probability_n": probs["tp3_given_tp2_probability"]["n"],
            "tp3_probability_ci": probs["tp3_given_tp2_probability"]["ci_95"],
        }
    if stage == "TP3_REACHED":
        return {"tp1_probability": 100.0, "tp2_probability": 100.0, "tp3_probability": 100.0}
    # EXITED — report the final, factual outcome, not a forward estimate.
    return {
        "tp1_probability": 100.0 if row.tp1_hit else 0.0,
        "tp2_probability": 100.0 if row.tp2_hit else (0.0 if row.tp1_hit else None),
        "tp3_probability": 100.0 if row.tp3_hit else (0.0 if row.tp2_hit else None),
    }


def compute_management_decision(
    row: TradeOutcome, stage: str, probs: dict, mae_pct: float | None
) -> tuple[str, str]:
    """Extends trade_outcomes.py's Phase-1 stage/status mapping with real
    stage-conditioned probabilities. Terminal stages (PRE_ENTRY, EXITED)
    are unchanged from Phase 1 — there's nothing probabilistic to decide
    once a trade has already closed or hasn't entered yet."""
    if stage == "PRE_ENTRY":
        return "HOLD", "Waiting for price to enter the proposed zone."
    if stage == "EXITED":
        if row.status == "closed_win":
            return "TAKE_PROFIT", "Reached the outermost defined target this cycle."
        if row.status == "closed_loss":
            return "STOPPED", "Stop hit this cycle."
        if row.status == "closed_stale":
            return "INVALIDATED", "Never entered within the max holding window."
        return "INVALIDATED", "Superseded by a new plan before resolving."

    if stage == "OPEN":
        p_tp1 = probs.get("tp1_probability")
        n = probs.get("tp1_probability_n", 0)
        if p_tp1 is None or n < MIN_SAMPLE_FOR_RECOMMENDATION:
            return "HOLD", (
                f"Position open, TP1 not yet reached. Insufficient resolved-trade history "
                f"(n={n}) for this direction/entry_quality/regime combination to estimate "
                f"P(TP1) reliably — holding without a probability-driven call."
            )
        return "HOLD", (
            f"Position open, TP1 not yet reached. Historical P(TP1) for this setup is "
            f"{p_tp1}% (n={n}) — not yet acted on (this app never exits BEFORE a target/stop "
            f"is actually reached; this is informational only)."
        )

    if stage == "TP1_REACHED":
        p_tp2 = probs.get("tp2_probability")
        n = probs.get("tp2_probability_n", 0)
        if p_tp2 is None or n < MIN_SAMPLE_FOR_RECOMMENDATION:
            return "HOLD", f"TP1 reached. Insufficient history (n={n}) to estimate P(TP2|TP1) for this setup — holding without a probability-driven call."
        if p_tp2 >= HIGH_CONTINUATION_THRESHOLD_PCT:
            return "HOLD_FOR_TP2", (
                f"TP1 reached. Historical P(TP2|TP1) for this setup is {p_tp2}% (n={n}) — "
                f"favorable enough to suggest holding for TP2 rather than closing here. "
                f"Suggestion only; nothing in this app moves the stop or exits automatically."
            )
        return "MOVE_STOP_TO_ENTRY", (
            f"TP1 reached, but historical P(TP2|TP1) for this setup is only {p_tp2}% (n={n}) — "
            f"below the {HIGH_CONTINUATION_THRESHOLD_PCT}% bar this app uses to suggest holding. "
            f"Suggestion only; nothing in this app moves the stop automatically."
        )

    if stage == "TP2_REACHED":
        p_tp3 = probs.get("tp3_probability")
        n = probs.get("tp3_probability_n", 0)
        if row.tp3 is None:
            return "HOLD", "TP2 reached; no TP3 is defined for this plan, so this cycle's outermost-target close logic (unchanged) will close it on any further target-direction move."
        if p_tp3 is None or n < MIN_SAMPLE_FOR_RECOMMENDATION:
            return "HOLD", f"TP2 reached. Insufficient history (n={n}) to estimate P(TP3|TP2) for this setup — holding without a probability-driven call."
        if p_tp3 >= HIGH_CONTINUATION_THRESHOLD_PCT:
            return "HOLD_FOR_TP3", f"TP2 reached. Historical P(TP3|TP2) for this setup is {p_tp3}% (n={n}) — favorable enough to suggest holding for TP3."
        return "MOVE_STOP_TO_TP1", (
            f"TP2 reached, but historical P(TP3|TP2) for this setup is only {p_tp3}% (n={n}) — "
            f"below the {HIGH_CONTINUATION_THRESHOLD_PCT}% bar. Suggestion only."
        )

    return "HOLD", f"Unhandled stage {stage!r} — defaulting to HOLD rather than guessing."
