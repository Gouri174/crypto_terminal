import asyncio

from fastapi import APIRouter, HTTPException

from app.data_sources import binance
from app.engine.feature_builder import build_features
from app.engine.reasoning import analyze_symbol
from app.engine.scoring import score_opportunity
from app.engine.similarity import build_current_vector, find_similar
from app.models.schemas import Opportunity

router = APIRouter()

SIMILARITY_INTERVAL = "4h"


@router.get("/analyze/{symbol}", response_model=Opportunity)
async def analyze(symbol: str):
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        raise HTTPException(400, "Only USDT-margined futures pairs are supported, e.g. BTCUSDT")

    try:
        features = await build_features(symbol)
        premium = await binance.get_premium_index(symbol)
    except Exception as exc:
        raise HTTPException(404, f"Could not fetch data for {symbol}: {exc}") from exc

    history_stats = None
    ind_4h = features.get(f"indicators_{SIMILARITY_INTERVAL}")
    if ind_4h:
        current_vec = build_current_vector(ind_4h)
        history_stats = find_similar(symbol, SIMILARITY_INTERVAL, current_vec)

    score_breakdown = score_opportunity(features, history_stats)
    plan = await asyncio.to_thread(analyze_symbol, features, score_breakdown, history_stats)

    return Opportunity(
        symbol=symbol,
        score=score_breakdown["total"],
        last_price=float(premium["markPrice"]),
        change_24h_pct=0.0,
        trade_plan=plan,
    )
