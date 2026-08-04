"""The continuous background engine.

Runs as a single in-process asyncio loop — no Celery/Redis needed for this
phase; a real worker queue is a later scaling step, not a requirement to
satisfy "always analyzed, not on-click." Every cycle:

1. Recompute the deterministic score for the whole universe (indicators,
   structure, historical similarity) — cheap, no LLM involved.
2. Persist that state for every scanned symbol, so the site is already
   analyzed the moment someone opens it.
3. Only call Claude for symbols that are top-ranked AND (never explained
   yet, OR their score moved enough to matter, OR the last explanation is
   stale) — this is what keeps LLM spend bounded regardless of universe
   size, instead of scaling with (coins x minutes).
"""

import asyncio
import time

from sqlalchemy import select

from app.config import (
    LLM_CANDIDATES,
    LLM_MAX_AGE_SECONDS,
    LLM_SCORE_CHANGE_THRESHOLD,
    SCAN_INTERVAL_SECONDS,
    UNIVERSE_SIZE,
)
from app.data_sources import binance
from app.db import SessionLocal
from app.engine.feature_builder import build_features
from app.engine.reasoning import analyze_symbol
from app.engine.scoring import score_opportunity
from app.engine.similarity import build_current_vector, find_similar
from app.models.db_models import LiveOpportunity
from app.ws import broadcast_update

SIMILARITY_INTERVAL = "4h"

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


async def _run_scan() -> dict:
    tickers = await binance.get_24h_tickers()
    usdt_pairs = [t for t in tickers if t["symbol"].endswith("USDT")]
    usdt_pairs.sort(key=lambda t: float(t["quoteVolume"]), reverse=True)
    universe = usdt_pairs[:UNIVERSE_SIZE]

    feature_sets = await asyncio.gather(
        *(build_features(t["symbol"]) for t in universe),
        return_exceptions=True,
    )

    scored = []
    for ticker, features in zip(universe, feature_sets):
        if isinstance(features, Exception):
            continue
        history_stats = None
        ind_4h = features.get(f"indicators_{SIMILARITY_INTERVAL}")
        if ind_4h:
            current_vec = build_current_vector(ind_4h)
            history_stats = find_similar(ticker["symbol"], SIMILARITY_INTERVAL, current_vec)
        breakdown = score_opportunity(features, history_stats)
        scored.append((breakdown["total"], breakdown, history_stats, ticker, features))

    scored.sort(key=lambda x: x[0], reverse=True)
    now_ms = int(time.time() * 1000)
    to_explain = _persist_scan(scored, now_ms)

    explained = 0
    for symbol, features, breakdown, history_stats in to_explain:
        try:
            plan = await asyncio.to_thread(analyze_symbol, features, breakdown, history_stats)
        except Exception as exc:
            print(f"[scanner] Claude explanation failed for {symbol}: {exc}")
            continue
        _save_trade_plan(symbol, plan, breakdown["total"], now_ms)
        explained += 1

    return {"scanned": len(scored), "explained": explained, "at": now_ms}


def _persist_scan(scored: list, now_ms: int) -> list:
    """Writes score+features for every scanned symbol; returns the subset
    that needs a fresh Claude explanation this cycle."""
    session = SessionLocal()
    to_explain = []
    try:
        existing = {
            row.symbol: row
            for row in session.execute(select(LiveOpportunity)).scalars().all()
        }

        for rank, (total, breakdown, history_stats, ticker, features) in enumerate(scored):
            symbol = ticker["symbol"]
            row = existing.get(symbol)

            needs_llm = False
            if rank < LLM_CANDIDATES:
                if row is None or row.trade_plan is None:
                    needs_llm = True
                elif row.last_llm_score is None or abs(total - row.last_llm_score) >= LLM_SCORE_CHANGE_THRESHOLD:
                    needs_llm = True
                elif (
                    row.trade_plan_updated_at is None
                    or (now_ms - row.trade_plan_updated_at) > LLM_MAX_AGE_SECONDS * 1000
                ):
                    needs_llm = True

            if row is None:
                row = LiveOpportunity(
                    symbol=symbol,
                    updated_at=now_ms,
                    last_price=0.0,
                    score_total=0.0,
                    score_breakdown={},
                    features={},
                )
                session.add(row)

            row.updated_at = now_ms
            row.last_price = float(ticker["lastPrice"])
            row.change_24h_pct = float(ticker["priceChangePercent"])
            row.score_total = total
            row.score_breakdown = breakdown
            row.features = features
            row.history_match = history_stats

            if needs_llm:
                to_explain.append((symbol, features, breakdown, history_stats))

        session.commit()
    finally:
        session.close()

    return to_explain


def _save_trade_plan(symbol: str, plan, score_total: float, now_ms: int) -> None:
    session = SessionLocal()
    try:
        row = session.get(LiveOpportunity, symbol)
        if row is None:
            return
        row.trade_plan = plan.model_dump()
        row.trade_plan_updated_at = now_ms
        row.last_llm_score = score_total
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
