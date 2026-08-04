import asyncio

from fastapi import APIRouter, HTTPException

from app.engine.feature_builder import build_features
from app.engine.reasoning import analyze_symbol
from app.engine.scorer import score_features
from app.models.schemas import Opportunity
from app.data_sources import binance

router = APIRouter()


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

    score = score_features(features)
    plan = await asyncio.to_thread(analyze_symbol, features)

    return Opportunity(
        symbol=symbol,
        score=score,
        last_price=float(premium["markPrice"]),
        change_24h_pct=0.0,
        trade_plan=plan,
    )
