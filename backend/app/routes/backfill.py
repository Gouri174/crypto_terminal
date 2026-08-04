from fastapi import APIRouter, Query

from app.engine.historical_engine import backfill_symbol

router = APIRouter()


@router.post("/backfill/{symbol}")
async def run_backfill(
    symbol: str,
    interval: str = Query(default="4h"),
    days: int = Query(default=365, le=1500),
    horizon_candles: int = Query(default=18, ge=1, le=200),
):
    """One-off historical backfill for a symbol/interval. Fetches real
    Binance OHLCV, reconstructs indicators + price-structure for every
    candle, and stores each as a MarketSnapshot (with realized forward
    return/drawdown, since backfilled history already knows what happened
    next). This is what powers historical similarity search."""
    symbol = symbol.upper()
    result = await backfill_symbol(symbol, interval, days, horizon_candles)
    return result
