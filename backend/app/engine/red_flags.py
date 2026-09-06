"""Red Flag engine — Karma V2.1 Phase 6.

Purely observational, additive diagnostic labels computed once at
issuance from already-available `entry_indicators`/score data — same
contract as `entry_flags.py:compute_diagnostic_flags()`, which this
complements rather than duplicates. NOTHING here changes score,
confidence, entry/SL/TP generation, or which trades get taken; a flagged
trade is still taken exactly as it would have been without this module.

Only flags with real evidence from the V2.1 forensic audit
(karma_v2_1_model_improvement_report.md, Section 6 / Rule 14) are
included — this is deliberately NOT the full example list from the
external roadmap this was based on, because several of those examples
(e.g. "RSI>75 + CMF negative") had ZERO occurrences in the actual 86-trade
dataset and can't be justified as a red flag from data that never showed
the pattern happening at all.
"""

RED_FLAG_DEFINITIONS = {
    "rsi_chop_zone": {
        "description": "RSI 30-49 at entry (\"chop zone\") — the strongest single red flag found in the V2.1 audit: 92.3% loss rate (12/13) vs a 56.2% baseline.",
        "evidence": "karma_v2_1_model_improvement_report.md, Section 6, Rule 1. n=13.",
    },
    "weak_structure": {
        "description": "structure_score < 9 — 66.7% loss rate vs 54.3% baseline.",
        "evidence": "karma_v2_1_model_improvement_report.md, Section 6. n=51.",
    },
    "no_historical_analogue": {
        "description": "No stored historical similarity data for this symbol. Flagged for visibility only — the V2.1 report found this is very likely confounded with a specific underperforming symbol group (Rule 11), not an independently causal signal. Do not weight this flag as strongly as the other two.",
        "evidence": "karma_v2_1_model_improvement_report.md, Section 6 and Rule 11 (explicitly a 'hold, do not act' finding). n=9-10.",
    },
}


def compute_red_flags(entry_indicators: dict | None, structure_score: float | None, historic_probability: float | None) -> dict:
    """entry_indicators: the dict already captured by
    trade_outcomes.py:_capture_entry_indicators() at issuance. Returns a
    red_flags list (only the flags actually triggered) and a
    red_flag_score (simple count, 0-3) — not a weighted composite, since
    the three flags have different evidence strength (see
    RED_FLAG_DEFINITIONS above) and collapsing them into one number would
    hide that."""
    ei = entry_indicators or {}
    flags = []

    rsi = ei.get("rsi14")
    if rsi is not None and 30 <= rsi < 50:
        flags.append("rsi_chop_zone")

    if structure_score is not None and structure_score < 9:
        flags.append("weak_structure")

    if historic_probability is None:
        flags.append("no_historical_analogue")

    return {
        "red_flags": flags,
        "red_flag_score": len(flags),
        "red_flag_max": len(RED_FLAG_DEFINITIONS),
        "risk_explanation": [RED_FLAG_DEFINITIONS[f]["description"] for f in flags],
    }
