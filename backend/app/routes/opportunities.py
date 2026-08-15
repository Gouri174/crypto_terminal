from fastapi import APIRouter, Query
from sqlalchemy import select

from app.config import LLM_CANDIDATES
from app.db import SessionLocal
from app.engine.background_scanner import ensure_scanned, load_current_regime
from app.models.db_models import LiveOpportunity
from app.models.schemas import Opportunity

router = APIRouter()


@router.get("/opportunities", response_model=list[Opportunity])
async def get_opportunities(limit: int = Query(default=6, le=LLM_CANDIDATES)):
    """Reads the background scanner's latest cached state — fast, and
    doesn't trigger any Claude calls itself. If the scanner hasn't
    completed a cycle yet (fresh start), runs one bootstrap scan so the
    dashboard isn't empty."""
    rows = _load_top(limit)

    if not rows:
        await ensure_scanned()
        rows = _load_top(limit)

    regime = load_current_regime()

    return [
        Opportunity(
            symbol=row.symbol,
            score=row.score_total,
            last_price=row.last_price,
            change_24h_pct=row.change_24h_pct,
            trade_plan=row.trade_plan,
            lifecycle_status=row.lifecycle_status,
            lifecycle_history=row.lifecycle_history or [],
            regime=regime,
        )
        for row in rows
    ]


def _load_top(limit: int) -> list[LiveOpportunity]:
    """Long/short candidates always rank above no_trade ones, regardless of
    score — a no_trade setup can score highest (strong overall setup, just
    no directional edge right now: mixed timeframes, or exhausted entry
    timing) but there's no trade to actually profit from, so it shouldn't
    crowd out a real long/short call in a fixed-size top-N slot. no_trade
    rows are still included to fill remaining slots (still useful context
    on what the engine is watching), just sorted last. Within each group,
    unchanged: highest score_total first.

    trade_plan.recommendation isn't queryable as a SQL column (JSON blob),
    so this pulls every scored-and-explained row and partitions in Python
    rather than in the query — fine at this app's scanned-universe scale
    (tens to low hundreds of rows), same tradeoff other reports here make."""
    session = SessionLocal()
    try:
        rows = (
            session.execute(
                select(LiveOpportunity)
                .where(LiveOpportunity.trade_plan.is_not(None))
                .order_by(LiveOpportunity.score_total.desc())
            )
            .scalars()
            .all()
        )
    finally:
        session.close()

    def _sort_key(row: LiveOpportunity) -> tuple[int, float]:
        direction = (row.trade_plan or {}).get("recommendation")
        is_no_trade = 1 if direction not in ("long", "short") else 0
        return (is_no_trade, -row.score_total)

    return sorted(rows, key=_sort_key)[:limit]
