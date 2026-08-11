"""The continuous background engine.

Runs as a single in-process asyncio loop — no Celery/Redis needed for this
phase; a real worker queue is a later scaling step, not a requirement to
satisfy "always analyzed, not on-click." Every cycle:

1. Recompute the deterministic score for the whole universe (indicators,
   structure, historical similarity, and the market regime from the
   PREVIOUS cycle — see note below) — cheap, no LLM involved.
2. Advance each symbol's trade lifecycle from live price vs. its last known
   trade plan — also deterministic, also no LLM.
3. Persist that state for every scanned symbol, so the site is already
   analyzed the moment someone opens it.
4. Only call Claude for symbols that are top-ranked AND (never explained
   yet, OR their score moved enough to matter, OR the last explanation is
   stale) — this is what keeps LLM spend bounded regardless of universe
   size, instead of scaling with (coins x minutes).
5. Recompute the market regime from THIS cycle's data and store it for
   next cycle's scoring pass. Regime therefore lags scoring by one cycle
   (a few minutes) — a deliberate simplification to avoid a circular
   dependency (breadth needs everyone's features, which needs to exist
   before regime can be computed), not an oversight.
"""

import asyncio
import time

from sqlalchemy import select

from app.config import LLM_CANDIDATES, SCAN_INTERVAL_SECONDS, UNIVERSE_SIZE
from app.data_sources import binance
from app.db import SessionLocal
from app.engine import lifecycle, market_regime, ml_model
from app.engine.confidence import compute_confidence
from app.engine.decision import decide_direction, trade_grade
from app.engine.entry_flags import compute_risk_reward
from app.engine.entry_quality import classify_entry_quality
from app.engine.feature_builder import build_features
from app.engine.llm_gate import should_reexplain
from app.engine.reasoning import analyze_batch
from app.engine.scoring import score_opportunity
from app.engine.similarity import build_current_vector, find_similar
from app.engine.trade_outcomes import open_trade_outcome, update_open_trades
from app.models.db_models import LiveOpportunity, MarketRegimeState, ScanSnapshot
from app.ws import broadcast_update

SIMILARITY_INTERVAL = "4h"


def _rejection_reason(
    direction: str,
    rank: int,
    in_top_candidates: bool,
    explained_this_cycle: bool,
    had_active_plan: bool,
    entry_quality: str | None = None,
) -> str | None:
    """Deterministic, template-built — never asks Claude to explain why a
    symbol wasn't published, since that would risk inventing a reason.
    None means the symbol WAS published/active this cycle."""
    if had_active_plan:
        return None
    if direction == "no_trade":
        if entry_quality == "exhausted":
            return "no_trade: entry_quality=exhausted overrode an otherwise-directional setup (see entry_quality.py)"
        return "no_trade: deterministic direction gate not met (score below threshold, or timeframe trend split)"
    if not in_top_candidates:
        return f"rank {rank} outside top {LLM_CANDIDATES} candidates this cycle"
    if entry_quality == "late":
        return "entry_quality=late — setup direction stands, but a new/refreshed plan is withheld until entry improves"
    if not explained_this_cycle:
        return "in top candidates but not (re)explained this cycle (see llm_gate.should_reexplain)"
    return None

# Guards against the periodic loop and a request-triggered bootstrap scan
# (see routes/opportunities.py) running concurrently, which could otherwise
# double up Binance/Claude calls and hit SQLite's single-writer limit.
_scan_lock = asyncio.Lock()


async def scan_once() -> dict:
    async with _scan_lock:
        return await _run_scan()


async def ensure_scanned() -> None:
    """Used by the request-triggered bootstrap fallback. If a scan is
    already in flight (e.g. the periodic loop's first cycle), waits for it
    instead of kicking off a redundant duplicate scan."""
    if _scan_lock.locked():
        async with _scan_lock:
            return
    async with _scan_lock:
        await _run_scan()


def load_current_regime() -> dict | None:
    session = SessionLocal()
    try:
        row = session.get(MarketRegimeState, 1)
        if row is None:
            return None
        return {
            "label": row.label,
            "trend": row.trend,
            "confidence": row.confidence,
            "btc_trend": row.btc_trend,
            "breadth_bullish_pct": row.breadth_bullish_pct,
            "breadth_bearish_pct": row.breadth_bearish_pct,
            "universe_size": row.universe_size,
            "summary": row.summary,
        }
    finally:
        session.close()


def _save_regime(regime: dict, now_ms: int) -> None:
    session = SessionLocal()
    try:
        row = session.get(MarketRegimeState, 1)
        if row is None:
            row = MarketRegimeState(id=1, updated_at=now_ms, **regime)
            session.add(row)
        else:
            row.updated_at = now_ms
            for key, value in regime.items():
                setattr(row, key, value)
        session.commit()
    finally:
        session.close()


def _pick_alternative(scored: list, current_symbol: str, current_total: float) -> dict | None:
    """The next-best-ranked non-no_trade setup this SAME cycle, only if
    within 15 score points of the current symbol — close enough to be a
    genuine alternative, not a consolation prize. `scored` is already
    sorted descending by total, so the first gap over 15 means nothing
    closer exists later either."""
    for total, breakdown, _history_stats, _ml_prediction, ticker, features in scored:
        symbol = ticker["symbol"]
        if symbol == current_symbol:
            continue
        if current_total - total > 15:
            break
        direction = decide_direction(features, breakdown)
        if direction != "no_trade":
            return {"symbol": symbol, "score": total, "direction": direction}
    return None


async def _run_scan() -> dict:
    regime = load_current_regime()  # from the previous cycle — see module docstring

    tickers, ticker_status = await binance.get_24h_tickers()
    if ticker_status["degraded"]:
        print(
            f"[scanner] running on {ticker_status['stale_seconds']:.0f}s-old cached "
            f"tickers after live fetch failed: {ticker_status['error']}"
        )
    usdt_pairs = [t for t in tickers if t["symbol"].endswith("USDT")]
    usdt_pairs.sort(key=lambda t: float(t["quoteVolume"]), reverse=True)
    universe = usdt_pairs[:UNIVERSE_SIZE]

    feature_sets = await asyncio.gather(
        *(build_features(t["symbol"]) for t in universe),
        return_exceptions=True,
    )

    scored = []
    btc_features = None
    for ticker, features in zip(universe, feature_sets):
        if isinstance(features, Exception):
            continue
        symbol = ticker["symbol"]
        if symbol == "BTCUSDT":
            btc_features = features
        history_stats = None
        ml_prediction = None
        ind_4h = features.get(f"indicators_{SIMILARITY_INTERVAL}")
        if ind_4h:
            current_vec = build_current_vector(ind_4h)
            history_stats = find_similar(symbol, SIMILARITY_INTERVAL, current_vec)
            ml_prediction = ml_model.predict_probabilities(
                symbol, SIMILARITY_INTERVAL, ind_4h.get("last_close"), current_vec
            )
        breakdown = score_opportunity(features, history_stats, regime, ml_prediction)
        scored.append((breakdown["total"], breakdown, history_stats, ml_prediction, ticker, features))

    scored.sort(key=lambda x: x[0], reverse=True)
    now_ms = int(time.time() * 1000)
    to_explain = _persist_scan(scored, now_ms, (regime or {}).get("label"))

    # Advance every open TradeOutcome against this cycle's real prices
    # before issuing any new plans — see app/engine/trade_outcomes.py.
    prices = {ticker["symbol"]: float(ticker["lastPrice"]) for ticker in universe}
    update_open_trades(prices, now_ms, regime_label=(regime or {}).get("label"))

    batch_items = [
        {
            "symbol": symbol,
            "features": features,
            "breakdown": breakdown,
            "history_stats": history_stats,
            "ml_prediction": ml_prediction,
            "alternative": _pick_alternative(scored, symbol, breakdown["total"]),
        }
        for symbol, features, breakdown, history_stats, ml_prediction in to_explain
    ]
    by_symbol_input = {item["symbol"]: item for item in batch_items}

    explained = 0
    if batch_items:
        try:
            plans = await asyncio.to_thread(analyze_batch, batch_items, regime)
        except Exception as exc:
            print(f"[scanner] batch Claude explanation failed for {len(batch_items)} symbols: {exc}")
            plans = {}
        for symbol, plan in plans.items():
            item = by_symbol_input[symbol]
            _save_trade_plan(symbol, plan, item["breakdown"]["total"], now_ms, prices.get(symbol))
            open_trade_outcome(
                symbol, plan, item["breakdown"], item["features"],
                item["history_stats"], item["ml_prediction"], regime, now_ms,
                confidence=plan.confidence, grade=plan.grade,
                entry_quality=plan.entry_quality,
                entry_quality_score=plan.entry_quality_score,
                entry_quality_reasons=plan.entry_quality_reasons,
            )
            explained += 1

    new_regime = market_regime.classify_regime(btc_features, scored)
    _save_regime(new_regime, now_ms)

    return {
        "scanned": len(scored),
        "explained": explained,
        "at": now_ms,
        "degraded": ticker_status["degraded"],
    }


def _persist_scan(scored: list, now_ms: int, regime_label: str | None) -> list:
    """Writes score+features+lifecycle for every scanned symbol; returns
    the subset that needs a fresh Claude explanation this cycle. Also
    appends one ScanSnapshot row per symbol — the full-universe history
    LiveOpportunity's overwrite-in-place design doesn't keep."""
    session = SessionLocal()
    to_explain = []
    try:
        existing = {
            row.symbol: row
            for row in session.execute(select(LiveOpportunity)).scalars().all()
        }

        for rank, (total, breakdown, history_stats, ml_prediction, ticker, features) in enumerate(scored):
            symbol = ticker["symbol"]
            row = existing.get(symbol)
            price = float(ticker["lastPrice"])

            # Cheap pure-Python decision — computed for every symbol now
            # (not just the top LLM_CANDIDATES) so ScanSnapshot's direction
            # column is meaningful for the whole universe, not just the
            # published subset.
            direction = decide_direction(features, breakdown)

            # Entry-quality gate (app/engine/entry_quality.py) — a hypothesis
            # layer built from the first 7-trade forensic analysis, kept
            # deliberately separate from scoring.py's weights. "exhausted"
            # forces no_trade for THIS symbol's ScanSnapshot/gating purposes
            # (reasoning.py:_precompute applies the identical override for
            # whatever Claude actually sees, so both paths agree). "late"
            # does NOT change direction — it only withholds a NEW/refreshed
            # plan below, reusing the existing to_explain/needs_llm gate
            # rather than touching lifecycle.py's state machine.
            entry_quality_data = classify_entry_quality(features, direction, breakdown)
            entry_quality = entry_quality_data["entry_quality"]
            if entry_quality == "exhausted" and direction in ("long", "short"):
                direction = "no_trade"

            in_top_candidates = rank < LLM_CANDIDATES
            had_active_plan = row.trade_plan is not None if row else False

            needs_llm = False
            if in_top_candidates:
                needs_llm = should_reexplain(
                    row.trade_plan if row else None,
                    row.last_llm_score if row else None,
                    row.trade_plan_updated_at if row else None,
                    total,
                    direction,
                    now_ms,
                )
                if entry_quality == "late":
                    needs_llm = False

            # V1.1 full-candidate-pool visibility — compute_confidence()/
            # trade_grade() are pure Python (no Claude call), so this costs
            # nothing extra to compute for the WHOLE universe, not just
            # published symbols. Answers "why did the system choose these 5
            # instead of the others" without a second explain step.
            confidence_data = compute_confidence(direction, breakdown, features, history_stats, ml_prediction)
            candidate_confidence = confidence_data["confidence"] if direction in ("long", "short") else None
            candidate_grade = trade_grade(candidate_confidence) if candidate_confidence is not None else None
            candidate_ml_prob = (ml_prediction or {}).get("win_probability")
            candidate_hist_prob = history_stats.get("win_rate") / 100 if history_stats and "win_rate" in history_stats else None
            risk_reward_tp1 = None
            if row and row.trade_plan:
                tp = row.trade_plan
                entry_low, entry_high = tp.get("entry_low"), tp.get("entry_high")
                entry_mid = (entry_low + entry_high) / 2 if entry_low is not None and entry_high is not None else None
                rr = compute_risk_reward(entry_mid, tp.get("stop_loss"), tp.get("take_profit_1"), None, None)
                risk_reward_tp1 = rr["rr_tp1"]

            session.add(
                ScanSnapshot(
                    timestamp=now_ms,
                    symbol=symbol,
                    rank=rank,
                    score_total=total,
                    score_breakdown=breakdown,
                    direction=direction,
                    in_top_candidates=in_top_candidates,
                    explained_this_cycle=needs_llm,
                    had_active_plan=had_active_plan,
                    market_regime=regime_label,
                    rejection_reason=_rejection_reason(
                        direction, rank, in_top_candidates, needs_llm, had_active_plan, entry_quality
                    ),
                    confidence=candidate_confidence,
                    grade=candidate_grade,
                    entry_quality=entry_quality,
                    ml_probability=candidate_ml_prob,
                    historic_probability=candidate_hist_prob,
                    risk_reward_tp1=risk_reward_tp1,
                )
            )

            if row is None:
                row = LiveOpportunity(
                    symbol=symbol,
                    updated_at=now_ms,
                    last_price=0.0,
                    score_total=0.0,
                    score_breakdown={},
                    features={},
                    lifecycle_status="WAIT",
                    lifecycle_history=[],
                )
                session.add(row)

            new_status, reason, new_sig = lifecycle.advance(
                row.lifecycle_status or "WAIT",
                row.lifecycle_plan_signature or "none",
                price,
                row.trade_plan,  # the PREVIOUS cycle's plan — this cycle's may not exist yet
            )
            if reason:
                history = list(row.lifecycle_history or [])
                history.append({"at": now_ms, "status": new_status, "reason": reason, "signature": new_sig})
                row.lifecycle_history = history[-50:]
            row.lifecycle_status = new_status
            row.lifecycle_plan_signature = new_sig

            row.updated_at = now_ms
            row.last_price = price
            row.change_24h_pct = float(ticker["priceChangePercent"])
            row.score_total = total
            row.score_breakdown = breakdown
            row.features = features
            row.history_match = history_stats

            if needs_llm:
                to_explain.append((symbol, features, breakdown, history_stats, ml_prediction))

        session.commit()
    finally:
        session.close()

    return to_explain


def _save_trade_plan(symbol: str, plan, score_total: float, now_ms: int, price: float | None) -> None:
    """Saves the fresh plan AND recomputes lifecycle_status against it in
    the SAME cycle. Found live: _persist_scan() runs BEFORE Claude is
    called, using the PREVIOUS cycle's plan — so when a trade just closed
    (EXIT_STOPPED/EXIT_TARGET) and Claude immediately issues a new one this
    same cycle, lifecycle_status stayed stuck on the just-closed trade's
    terminal state for a full SCAN_INTERVAL_SECONDS until the NEXT cycle's
    _persist_scan() finally noticed the signature changed. On the coin
    detail page that showed a "Stopped Out" badge sitting directly above a
    brand-new, unrelated recommendation — reads as "this new pick already
    failed," which is wrong. Recomputing here closes that gap immediately."""
    session = SessionLocal()
    try:
        row = session.get(LiveOpportunity, symbol)
        if row is None:
            return
        row.trade_plan = plan.model_dump()
        row.trade_plan_updated_at = now_ms
        row.last_llm_score = score_total

        if price is not None:
            new_status, reason, new_sig = lifecycle.advance(
                row.lifecycle_status or "WAIT", row.lifecycle_plan_signature or "none", price, row.trade_plan
            )
            if reason:
                history = list(row.lifecycle_history or [])
                history.append({"at": now_ms, "status": new_status, "reason": reason, "signature": new_sig})
                row.lifecycle_history = history[-50:]
            row.lifecycle_status = new_status
            row.lifecycle_plan_signature = new_sig

        session.commit()
    finally:
        session.close()


async def run_scanner_loop() -> None:
    while True:
        try:
            summary = await scan_once()
            await broadcast_update(summary)
        except Exception as exc:
            print(f"[scanner] cycle failed: {exc}")
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)
