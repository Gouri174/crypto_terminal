"""Trade Journal Engine — Karma V3.2 Phase G.

Per-trade strengths/mistakes/repeated-pattern/historical-analogue/future-
recommendation — pure synthesis of karma_explain.py (bullish/risk evidence,
historical context) and trade_truth.py (verdict + lessons). Nothing new is
computed here.
"""


def journal_entry(trade_outcome_id: int) -> dict | None:
    from app.analytics.karma_explain import explain_trade
    from app.analytics.trade_truth import truth_for_trade

    explanation = explain_trade(trade_outcome_id)
    if explanation is None:
        return None
    truth = truth_for_trade(trade_outcome_id)

    return {
        "trade_outcome_id": trade_outcome_id, "symbol": explanation["symbol"],
        "outcome": truth["verdict"] if truth else "open_or_pending",
        "strengths": explanation["bullish_evidence"],
        "mistakes": explanation["risk_evidence"],
        "repeated_pattern": {
            "matched_tags": explanation["historical_context"].get("matched_tags", []),
            "historical_win_rate_pct": explanation["historical_context"].get("win_rate_pct"),
            "historical_n": explanation["historical_context"].get("n"),
        },
        "historical_analogue": explanation["historical_context"],
        "future_recommendation": truth["lessons"] if truth else [],
    }
