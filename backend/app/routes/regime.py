from fastapi import APIRouter, HTTPException

from app.engine.background_scanner import load_current_regime
from app.models.schemas import RegimeInfo

router = APIRouter()


@router.get("/regime", response_model=RegimeInfo)
async def get_regime():
    regime = load_current_regime()
    if regime is None:
        raise HTTPException(503, "Market regime not computed yet — the scanner hasn't finished its first cycle.")
    return regime
