import asyncio
import time

from fastapi import APIRouter, HTTPException

from app.data_sources import binance
from app.db import SessionLocal
from app.engine import ml_model
from app.engine.background_scanner import load_current_regime
from app.engine.decision import decide_direction
from app.engine.feature_builder import build_features
from app.engine.llm_gate import should_reexplain
from app.engine.reasoning import analyze_symbol
from app.engine.scoring import score_opportunity
from app.engine.similarity import build_current_vector, find_similar
from app.models.db_models import LiveOpportunity
from app.models.schemas import Opportunity, TradePlan

router = APIRouter()

SIMILARITY_INTERVAL = "4h"


@router.get("/analyze/{symbol}", response_model=Opportunity)
async def analyze(symbol: str):
    """Reuses the same cached-explanation logic as the background scanner
    (app/engine/llm_gate.py) — opening this page repeatedly does NOT call
    Claude again unless the score, direction, or cache age actually
    warrant it. Before this existed, every hit called Claude live; that was
    the single largest source of avoidable spend in the app."""
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        raise HTTPException(400, "Only USDT-margined futures pairs are supported, e.g. BTCUSDT")

    try:
        features = await build_features(symbol)
        premium = await binance.get_premium_index(symbol)
    except Exception as exc:
        raise HTTPException(404, f"Could not fetch data for {symbol}: {exc}") from exc

    history_stats = None
    ml_prediction = None
    ind_4h = features.get(f"indicators_{SIMILARITY_INTERVAL}")
    if ind_4h:
        current_vec = build_current_vector(ind_4h)
        history_stats = find_similar(symbol, SIMILARITY_INTERVAL, current_vec)
        ml_prediction = ml_model.predict_probabilities(
            symbol, SIMILARITY_INTERVAL, ind_4h.get("last_close"), current_vec
        )

    regime = load_current_regime()
    score_breakdown = score_opportunity(features, history_stats, regime, ml_prediction)
    direction = decide_direction(features, score_breakdown)
    now_ms = int(time.time() * 1000)

    cached_row = _read_cache(symbol)
    if cached_row and not should_reexplain(
        cached_row.trade_plan, cached_row.last_llm_score, cached_row.trade_plan_updated_at,
        score_breakdown["total"], direction, now_ms,
    ):
        plan = TradePlan.model_validate(cached_row.trade_plan)
    else:
        plan = await asyncio.to_thread(
            analyze_symbol, features, score_breakdown, history_stats, regime, ml_prediction
        )
        _write_cache(symbol, plan, score_breakdown["total"], now_ms)

    lifecycle_status, lifecycle_history = _read_lifecycle(symbol)

    return Opportunity(
        symbol=symbol,
        score=score_breakdown["total"],
        last_price=float(premium["markPrice"]),
        change_24h_pct=0.0,
        trade_plan=plan,
        lifecycle_status=lifecycle_status,
        lifecycle_history=lifecycle_history,
        regime=regime,
    )


def _read_cache(symbol: str) -> LiveOpportunity | None:
    session = SessionLocal()
    try:
        return session.get(LiveOpportunity, symbol)
    finally:
        session.close()


def _write_cache(symbol: str, plan: TradePlan, score_total: float, now_ms: int) -> None:
    """Only updates the explanation-cache fields — never touches
    score/features/lifecycle, which are owned exclusively by the
    background scanner (see its module docstring). If this symbol isn't
    tracked by the scanner yet (e.g. outside the top UNIVERSE_SIZE), there's
    no row to attach the cache to; the next scan cycle will create one and
    this explanation just won't be reused until then — an acceptable gap,
    not a correctness issue."""
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


def _read_lifecycle(symbol: str) -> tuple[str, list]:
    """Lifecycle is owned by the background scanner (see
    background_scanner.py) — this just reads whatever it last computed,
    it never advances the state itself, so opening a coin's detail page
    can't create a second, conflicting state machine."""
    session = SessionLocal()
    try:
        row = session.get(LiveOpportunity, symbol)
        if row is None:
            return "WAIT", []
        return row.lifecycle_status, row.lifecycle_history or []
    finally:
        session.close()
