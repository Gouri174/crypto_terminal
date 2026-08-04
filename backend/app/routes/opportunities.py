from fastapi import APIRouter, Query
from sqlalchemy import select

from app.config import LLM_CANDIDATES
from app.db import SessionLocal
from app.engine.background_scanner import ensure_scanned
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

    return [
        Opportunity(
            symbol=row.symbol,
            score=row.score_total,
            last_price=row.last_price,
            change_24h_pct=row.change_24h_pct,
            trade_plan=row.trade_plan,
        )
        for row in rows
    ]


def _load_top(limit: int) -> list[LiveOpportunity]:
    session = SessionLocal()
    try:
        return (
            session.execute(
                select(LiveOpportunity)
                .where(LiveOpportunity.trade_plan.is_not(None))
                .order_by(LiveOpportunity.score_total.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
    finally:
        session.close()
