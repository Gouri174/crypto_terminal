"""Position Size Recommendation — Karma V3.0.

Pure arithmetic, no ML, no execution — this NEVER places an order or
touches capital; it only answers "given this stop distance and this risk
tolerance, how large a position keeps the dollar risk fixed." Same
"suggestion only" contract as trade_manager.py's recommendations.
"""


def recommend_position_size(
    capital: float,
    risk_pct: float,
    stop_distance_pct: float,
    max_leverage: float | None = None,
) -> dict:
    """capital: total account size in quote currency (e.g. USD).
    risk_pct: max % of capital willing to lose on this trade if stopped
    out (e.g. 1.0 for 1%).
    stop_distance_pct: % distance from entry to stop (e.g.
    entry_flags.compute_risk_reward()'s risk_to_sl_pct).
    max_leverage: if given, caps the suggested notional at
    capital * max_leverage regardless of what the risk math alone would
    allow — a real stop-distance/risk-tolerance combination can otherwise
    imply a notional far larger than the account, which isn't a position
    size a spot/low-leverage account could actually take."""
    if capital <= 0 or risk_pct <= 0 or stop_distance_pct <= 0:
        return {
            "position_size": None, "max_dollar_loss": None,
            "note": "capital, risk_pct, and stop_distance_pct must all be positive — returned None rather than a division-by-zero guess.",
        }

    max_dollar_loss = round(capital * (risk_pct / 100), 2)
    # position_size * (stop_distance_pct/100) = max_dollar_loss
    position_size = round(max_dollar_loss / (stop_distance_pct / 100), 2)

    implied_leverage = round(position_size / capital, 2)
    capped = False
    if max_leverage is not None and implied_leverage > max_leverage:
        position_size = round(capital * max_leverage, 2)
        capped = True

    return {
        "capital": capital, "risk_pct": risk_pct, "stop_distance_pct": stop_distance_pct,
        "max_dollar_loss": max_dollar_loss,
        "position_size": position_size,
        "implied_leverage": round(position_size / capital, 2),
        "leverage_capped": capped,
        "note": "Suggestion only — this recommends a size, it never places an order or moves capital.",
    }
