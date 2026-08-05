"""Closed-loop trade outcome tracking.

Every fresh AI trade plan becomes one append-only TradeOutcome row. Nothing
is overwritten in place except the row's own lifecycle fields as live price
resolves it — a row is created once and only ever updated until it closes.
That makes every closed row a labeled training example (full market state
at recommendation time + real realized outcome) without a manual labeling
step; see app/models/db_models.py:TradeOutcome for the schema and
app/engine/trade_reports.py for the digests built on top of this table.

Two entry points, both called from background_scanner.py:
  - open_trade_outcome(): called once, right after Claude issues a fresh
    trade plan for a symbol.
  - update_open_trades(): called every scan cycle for every symbol with a
    pending/open row, using prices this cycle already fetched (no extra
    API calls).
"""

from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import TradeOutcome

# A trade that never enters, or never resolves, within this window is
# closed out rather than tracked forever. 14 days comfortably covers this
# app's longest time_horizon ("position") without letting dead rows pile up.
MAX_HOLDING_HOURS = 24 * 14

_COMPONENT_FIELDS = {
    "trend": "trend_score", "momentum": "momentum_score", "volume": "volume_score",
    "funding": "funding_score", "structure": "structure_score", "history": "history_score",
    "regime": "regime_score", "ml": "ml_score", "sentiment": "sentiment_score",
    "liquidity": "liquidity_score", "risk": "risk_score",
}
_COMPONENT_KEYWORDS = {
    "trend": ["trend", "ema", "moving average"],
    "momentum": ["momentum", "rsi", "macd"],
    "volume": ["volume", "obv", "cmf", "mfi"],
    "funding": ["funding"],
    "structure": ["structure", "bos", "choch", "fair value gap", "fvg", "order block", "break of structure"],
    "history": ["historical", "history", "similar setup", "similar situation"],
    "regime": ["regime", "market-wide", "broader market", "overall market"],
    "ml": ["ml model", "machine learning", "model predict", "model-predicted"],
    "sentiment": ["fear", "greed", "sentiment"],
    "liquidity": ["liquidity", "cross-exchange", "spread", "divergence"],
    "risk": ["risk", "overextend", "volatility", "extended"],
}


def open_trade_outcome(
    symbol: str,
    plan,
    breakdown: dict,
    features: dict,
    history_stats: dict | None,
    ml_prediction: dict | None,
    regime: dict | None,
    now_ms: int,
) -> None:
    """No-op for no_trade recommendations or plans missing the numeric
    levels needed to track a position — there's nothing to follow."""
    if plan.recommendation not in ("long", "short"):
        return
    if plan.entry_low is None or plan.entry_high is None or plan.stop_loss is None:
        return

    session = SessionLocal()
    try:
        existing_open = (
            session.execute(
                select(TradeOutcome).where(
                    TradeOutcome.symbol == symbol,
                    TradeOutcome.status.in_(["pending", "open"]),
                )
            )
            .scalars()
            .all()
        )
        for old in existing_open:
            if (
                old.direction == plan.recommendation
                and old.entry_low == plan.entry_low
                and old.entry_high == plan.entry_high
                and old.stop_loss == plan.stop_loss
            ):
                return  # identical plan already being tracked — nothing new
            # A materially different plan replaced this one before it
            # resolved. Tagged separately from win/loss since we never
            # found out what it would have done.
            old.status = "invalidated"
            old.exit_time = now_ms

        news_context = features.get("news_context") or {}
        row = TradeOutcome(
            created_at=now_ms,
            symbol=symbol,
            direction=plan.recommendation,
            timeframe=plan.time_horizon,
            entry_low=plan.entry_low,
            entry_high=plan.entry_high,
            entry=(plan.entry_low + plan.entry_high) / 2,
            stop_loss=plan.stop_loss,
            tp1=plan.take_profit_1,
            tp2=plan.take_profit_2,
            tp3=plan.take_profit_3,
            status="pending",
            score=breakdown.get("total", 0.0),
            trend_score=breakdown.get("trend", 0.0),
            momentum_score=breakdown.get("momentum", 0.0),
            volume_score=breakdown.get("volume", 0.0),
            funding_score=breakdown.get("funding", 0.0),
            structure_score=breakdown.get("structure", 0.0),
            history_score=breakdown.get("history", 0.0),
            regime_score=breakdown.get("regime", 0.0),
            ml_score=breakdown.get("ml", 0.0),
            sentiment_score=breakdown.get("sentiment", 0.0),
            liquidity_score=breakdown.get("liquidity", 0.0),
            risk_score=breakdown.get("risk", 0.0),
            ml_probability=(ml_prediction or {}).get("win_probability"),
            historic_probability=(
                (history_stats["win_rate"] / 100) if history_stats and "win_rate" in history_stats else None
            ),
            fear_greed=(features.get("fear_greed") or {}).get("value"),
            news_sentiment={"headlines": news_context.get("headlines", [])},
            reddit_sentiment={
                "reddit_mention_count": news_context.get("reddit_mention_count"),
                "reddit_sample_titles": news_context.get("reddit_sample_titles"),
            },
            reasoning=plan.summary,
            reasons_for=plan.reasons_for,
            reasons_against=plan.reasons_against,
            historical_matches=history_stats,
            market_regime=(regime or {}).get("label"),
        )
        session.add(row)
        session.commit()
    finally:
        session.close()


def update_open_trades(prices: dict[str, float], now_ms: int) -> None:
    """prices: symbol -> last price, from data this scan cycle already
    fetched. A symbol that's temporarily outside the scanned universe just
    doesn't get a price update that cycle — its MFE/MAE tracking has a gap
    until it reappears, rather than costing an extra API call to chase it.
    Documented tradeoff, not a silent bug."""
    session = SessionLocal()
    try:
        open_rows = (
            session.execute(
                select(TradeOutcome).where(TradeOutcome.status.in_(["pending", "open"]))
            )
            .scalars()
            .all()
        )
        for row in open_rows:
            price = prices.get(row.symbol)
            if price is None:
                continue
            _update_one(row, price, now_ms)
        session.commit()
    finally:
        session.close()


def _update_one(row: TradeOutcome, price: float, now_ms: int) -> None:
    is_long = row.direction == "long"

    if row.status == "pending":
        age_hours = (now_ms - row.created_at) / 3_600_000
        if row.entry_low <= price <= row.entry_high:
            row.status = "open"
            row.entry_hit = True
            row.entry_time = now_ms
            row.max_favorable_price = price
            row.max_adverse_price = price
        elif age_hours > MAX_HOLDING_HOURS:
            row.status = "closed_stale"
            row.exit_time = now_ms
        return

    if row.status != "open":
        return

    if row.max_favorable_price is None or (
        (is_long and price > row.max_favorable_price) or (not is_long and price < row.max_favorable_price)
    ):
        row.max_favorable_price = price
    if row.max_adverse_price is None or (
        (is_long and price < row.max_adverse_price) or (not is_long and price > row.max_adverse_price)
    ):
        row.max_adverse_price = price

    hit_stop = price <= row.stop_loss if is_long else price >= row.stop_loss
    hit_tp1 = row.tp1 is not None and (price >= row.tp1 if is_long else price <= row.tp1)
    hit_tp2 = row.tp2 is not None and (price >= row.tp2 if is_long else price <= row.tp2)
    hit_tp3 = row.tp3 is not None and (price >= row.tp3 if is_long else price <= row.tp3)

    row.tp1_hit = row.tp1_hit or hit_tp1
    row.tp2_hit = row.tp2_hit or hit_tp2
    row.tp3_hit = row.tp3_hit or hit_tp3
    row.stop_hit = row.stop_hit or hit_stop

    # The trade closes at whichever is the outermost defined target (TP3 if
    # set, else TP2, else TP1) or the stop — whichever is hit first. This is
    # a simplification: it doesn't model partial position sizing across
    # multiple targets, it treats "reached the final target" as full close.
    final_target_hit = hit_tp3 or (row.tp3 is None and hit_tp2) or (row.tp3 is None and row.tp2 is None and hit_tp1)

    close_reason = None
    if hit_stop:
        close_reason = "stop"
    elif final_target_hit:
        close_reason = "target"
    else:
        age_hours = (now_ms - row.entry_time) / 3_600_000 if row.entry_time else 0
        if age_hours > MAX_HOLDING_HOURS:
            close_reason = "max_holding"

    if close_reason:
        _close_trade(row, price, now_ms, close_reason)


def _close_trade(row: TradeOutcome, exit_price: float, now_ms: int, reason: str) -> None:
    is_long = row.direction == "long"
    sign = 1 if is_long else -1

    row.exit_time = now_ms
    row.holding_minutes = round((now_ms - row.entry_time) / 60_000, 1) if row.entry_time else None
    row.realized_return_pct = round((exit_price - row.entry) / row.entry * 100 * sign, 3)

    if reason == "stop":
        row.status = "closed_loss"
    elif reason == "target":
        row.status = "closed_win"
    else:  # max_holding — classify by sign of realized return, not by which line was crossed
        row.status = "closed_win" if row.realized_return_pct > 0 else "closed_loss"

    if row.max_favorable_price is not None:
        row.max_runup_pct = round((row.max_favorable_price - row.entry) / row.entry * 100 * sign, 3)
    if row.max_adverse_price is not None:
        row.max_drawdown_pct = round((row.max_adverse_price - row.entry) / row.entry * 100 * sign, 3)

    # Meaningful mainly when status is closed_loss: did price reach TP1 at
    # some point before the stop ultimately took the trade out?
    row.tp1_before_stop = row.tp1_hit

    row.key_score_component = _key_score_component(row)
    row.explanation_mentioned_key_factor = _explanation_mentions(row, row.key_score_component)
    _compute_counterfactual(row)


def _key_score_component(row: TradeOutcome) -> str:
    values = {name: getattr(row, field) for name, field in _COMPONENT_FIELDS.items()}
    return max(values, key=lambda k: abs(values[k]))


def _explanation_mentions(row: TradeOutcome, key_component: str) -> bool:
    text_parts = list(row.reasons_for or []) + list(row.reasons_against or [])
    if row.reasoning:
        text_parts.append(row.reasoning)
    text = " ".join(text_parts).lower()
    keywords = _COMPONENT_KEYWORDS.get(key_component, [])
    return any(kw in text for kw in keywords)


def _compute_counterfactual(row: TradeOutcome) -> None:
    """What the exact opposite direction would have realized over the SAME
    entry-to-exit price path. Deliberately simple: return = -realized_return
    (mirroring long<->short on identical entry/exit prices is exact math,
    not an approximation) — but this does NOT independently simulate the
    opposite trade's own stop/target being hit earlier or later than this
    trade's actual exit. A real "what if we'd gone short instead" answer
    would need to walk the opposite trade forward on its own terms; this is
    the honest, cheap version of that question, not the full one."""
    row.counterfactual_direction = "short" if row.direction == "long" else "long"
    if row.realized_return_pct is not None:
        row.counterfactual_return_pct = round(-row.realized_return_pct, 3)
    row.counterfactual_note = (
        "Mirrors the realized entry-to-exit price path with the opposite "
        "direction; does not simulate the opposite trade's own independent "
        "stop-loss/take-profit."
    )
