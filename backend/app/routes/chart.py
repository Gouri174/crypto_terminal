from fastapi import APIRouter, HTTPException, Query

from app.db import SessionLocal
from app.engine.chart_data import build_chart
from app.models.db_models import LiveOpportunity

router = APIRouter()


@router.get("/chart/{symbol}")
async def get_chart(
    symbol: str,
    interval: str = Query(default="4h"),
    limit: int = Query(default=300, le=1000),
):
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        raise HTTPException(400, "Only USDT-margined futures pairs are supported, e.g. BTCUSDT")

    trade_plan = _load_trade_plan(symbol)

    try:
        return await build_chart(symbol, interval, limit, trade_plan)
    except Exception as exc:
        raise HTTPException(404, f"Could not build chart for {symbol}: {exc}") from exc


def _load_trade_plan(symbol: str) -> dict | None:
    """Reuses whatever trade plan the background scanner (or a prior
    analyze call) last computed for this symbol, so the chart's overlays
    match what's shown elsewhere — no separate Claude call just to draw a
    chart."""
    session = SessionLocal()
    try:
        row = session.get(LiveOpportunity, symbol)
        return row.trade_plan if row else None
    finally:
        session.close()
