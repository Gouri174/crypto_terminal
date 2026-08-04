import asyncio

from fastapi import APIRouter, Query

from app.config import LLM_CANDIDATES, UNIVERSE_SIZE
from app.data_sources import binance
from app.engine.feature_builder import build_features
from app.engine.reasoning import analyze_symbol
from app.engine.scoring import score_opportunity
from app.engine.similarity import build_current_vector, find_similar
from app.models.schemas import Opportunity

router = APIRouter()

SIMILARITY_INTERVAL = "4h"


def _score_candidate(features: dict) -> tuple[float, dict, dict | None]:
    history_stats = None
    ind_4h = features.get(f"indicators_{SIMILARITY_INTERVAL}")
    if ind_4h:
        current_vec = build_current_vector(ind_4h)
        history_stats = find_similar(features["symbol"], SIMILARITY_INTERVAL, current_vec)

    breakdown = score_opportunity(features, history_stats)
    return breakdown["total"], breakdown, history_stats


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
        total, breakdown, history_stats = _score_candidate(features)
        scored.append((total, breakdown, history_stats, ticker, features))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]

    plans = await asyncio.gather(
        *(
            asyncio.to_thread(analyze_symbol, features, breakdown, history_stats)
            for _, breakdown, history_stats, _, features in top
        ),
        return_exceptions=True,
    )

    opportunities = []
    for (total, _, _, ticker, _), plan in zip(top, plans):
        if isinstance(plan, Exception):
            continue
        opportunities.append(
            Opportunity(
                symbol=ticker["symbol"],
                score=total,
                last_price=float(ticker["lastPrice"]),
                change_24h_pct=float(ticker["priceChangePercent"]),
                trade_plan=plan,
            )
        )

    return opportunities
