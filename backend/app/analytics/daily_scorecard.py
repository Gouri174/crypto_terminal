"""Daily Scorecard — Karma V3.2 Phase E.

Morning report (market health + scanner funnel + portfolio health + top
opportunities) and evening report (closed trades + TP summary + best/
worst + lessons) — pure assembly over already-existing modules. Nothing
computed here is new; every number comes from a function this codebase
already has.
"""

import time

_DAY_MS = 86_400_000


async def morning_report() -> dict:
    from app.analytics.market_health import current_market_health
    from app.analytics.portfolio_exposure import portfolio_exposure
    from app.engine.background_scanner import load_current_regime
    from app.engine.forensic_diagnostics import signal_funnel_report
    from app.engine.performance_center import ev_leaderboard

    now_ms = int(time.time() * 1000)
    health = await current_market_health()
    funnel = signal_funnel_report(now_ms - _DAY_MS, now_ms)
    exposure = portfolio_exposure()
    ev = ev_leaderboard(min_sample=1)
    top_trades = sorted(
        [e for e in ev.get("ranked_by_expected_r", []) if e.get("status") in ("closed_win", "closed_loss")],
        key=lambda e: -(e.get("expected_r") or -999),
    )[:5]

    return {
        "date": now_ms,
        "market_health": health,
        "regime": load_current_regime(),
        "scanner_funnel": funnel,
        "portfolio_health": exposure,
        "top_opportunities_by_ev": top_trades,
    }


def evening_report(day_ms: int = _DAY_MS) -> dict:
    from app.analytics.strategy_attribution import strategy_leaderboard
    from app.analytics.trade_truth import truth_leaderboard
    from app.engine.trade_reports import performance_digest

    now_ms = int(time.time() * 1000)
    digest = performance_digest(now_ms - day_ms, now_ms, label="today")
    truth = truth_leaderboard(min_sample=1)
    strategies = strategy_leaderboard(min_sample=1)

    best_strategy = max(strategies["strategies"], key=lambda s: s["win_rate_pct"] or -1, default=None)
    worst_strategy = min(strategies["strategies"], key=lambda s: s["win_rate_pct"] or 101, default=None)

    return {
        "date": now_ms,
        "performance_digest": digest,
        "truth_breakdown": truth,
        "best_strategy_today": best_strategy,
        "worst_strategy_today": worst_strategy,
    }
