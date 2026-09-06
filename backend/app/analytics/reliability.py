"""Symbol Reliability Engine — Karma V3.0.

Bayesian-shrunk reliability score per symbol: a raw win rate from 2
trades (100% or 0%) is noise, not signal — shrinking it toward the
overall pooled win rate, weighted by how few trades that symbol has, is
the standard fix (empirical Bayes / Beta-Binomial shrinkage), not a
sophisticated model. This is arithmetic on already-resolved TradeOutcome
rows, not a trained model, and it does not feed back into which symbols
get scanned/scored/traded — see reasoning.py/decision.py, both untouched.

PRIOR_STRENGTH=10 means "a symbol with zero trades is treated as if it
had already seen 10 trades at the overall pooled win rate" — a small,
explicit prior, not an invented round number: 10 sits below this
project's own first meaningful-sample milestone (25, per
forensic_diagnostics.py's data_milestones()) precisely so it doesn't
overwhelm a coin's own real data once it has any.
"""

from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import TradeOutcome

_TRADED_STATUSES = ("closed_win", "closed_loss")
RELIABILITY_VERSION = "v1"
PRIOR_STRENGTH = 10  # pseudo-trades at the pooled win rate


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


def _avg(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def _profit_factor(rows: list[TradeOutcome]) -> float | None:
    rets = [r.realized_return_pct for r in rows if r.realized_return_pct is not None]
    gains = sum(r for r in rets if r > 0)
    loss = sum(r for r in rets if r < 0)
    return round(gains / abs(loss), 3) if loss else None


def _shrunk_win_rate(wins: int, n: int, pooled_rate: float, prior_strength: int) -> float:
    """Beta-Binomial posterior mean with a prior of `prior_strength`
    pseudo-trades at `pooled_rate`: (wins + prior_strength*pooled_rate) /
    (n + prior_strength). As n grows, this converges to the symbol's own
    raw win rate; at n=0 it equals the pooled rate exactly."""
    return (wins + prior_strength * pooled_rate) / (n + prior_strength)


def symbol_reliability(symbol: str | None = None, prior_strength: int = PRIOR_STRENGTH) -> dict:
    """Without `symbol`: every symbol with at least 1 resolved trade,
    ranked by reliability score. With `symbol`: just that one (reports
    n=0/reliability=pooled-rate honestly if the symbol has never resolved
    a trade, rather than refusing to answer)."""
    rows = _traded_rows()
    if not rows:
        return {"note": "No resolved trades yet.", "symbols": []}

    pooled_wins = sum(1 for r in rows if r.status == "closed_win")
    pooled_rate = pooled_wins / len(rows)

    by_symbol: dict[str, list[TradeOutcome]] = {}
    for r in rows:
        by_symbol.setdefault(r.symbol, []).append(r)

    def _entry(sym: str, sym_rows: list[TradeOutcome]) -> dict:
        wins = sum(1 for r in sym_rows if r.status == "closed_win")
        n = len(sym_rows)
        reliability = round(_shrunk_win_rate(wins, n, pooled_rate, prior_strength) * 100, 1)
        raw_win_rate = round(wins / n * 100, 1) if n else None
        slippage = [r.stop_slippage_pct for r in sym_rows if r.stop_slippage_pct is not None]
        return {
            "symbol": sym, "n": n,
            "reliability_score": reliability,
            "raw_win_rate_pct": raw_win_rate,
            "profit_factor": _profit_factor(sym_rows),
            "avg_return_pct": _avg([r.realized_return_pct for r in sym_rows]),
            "avg_stop_slippage_pct": _avg(slippage),
            "avg_max_drawdown_pct": _avg([r.max_drawdown_pct for r in sym_rows]),
            "note": (
                f"Shrunk toward the pooled win rate ({round(pooled_rate * 100, 1)}%) using a "
                f"{prior_strength}-pseudo-trade prior — raw_win_rate_pct is the unshrunk figure, "
                "shown for comparison, not what reliability_score reports."
            ),
        }

    if symbol is not None:
        sym_rows = by_symbol.get(symbol, [])
        return _entry(symbol, sym_rows) if sym_rows else {
            "symbol": symbol, "n": 0, "reliability_score": round(pooled_rate * 100, 1),
            "note": "No resolved trades for this symbol yet — reliability_score defaults to the pooled rate.",
        }

    entries = [_entry(sym, sym_rows) for sym, sym_rows in by_symbol.items()]
    entries.sort(key=lambda e: -e["reliability_score"])
    return {
        "pooled_win_rate_pct": round(pooled_rate * 100, 1),
        "prior_strength": prior_strength,
        "symbols": entries,
    }
