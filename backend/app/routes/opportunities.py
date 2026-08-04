import asyncio

from fastapi import APIRouter, Query

from app.config import LLM_CANDIDATES, UNIVERSE_SIZE
from app.data_sources import binance
from app.engine.feature_builder import build_features
from app.engine.reasoning import analyze_symbol
from app.engine.scorer import score_features
from app.models.schemas import Opportunity

router = APIRouter()


@router.get("/opportunities", response_model=list[Opportunity])
async def get_opportunities(limit: int = Query(default=6, le=LLM_CANDIDATES)):
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
        scored.append((score_features(features), ticker, features))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]

    opportunities = []
    for score, ticker, features in top:
        plan = await asyncio.to_thread(analyze_symbol, features)
        opportunities.append(
            Opportunity(
                symbol=ticker["symbol"],
                score=score,
                last_price=float(ticker["lastPrice"]),
                change_24h_pct=float(ticker["priceChangePercent"]),
                trade_plan=plan,
            )
        )

    return opportunities
