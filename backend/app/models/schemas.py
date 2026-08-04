from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    """Deterministic, computed score components. Never invented by the LLM —
    see app/engine/scoring.py. Claude explains these numbers; it doesn't
    set them."""

    trend: float
    momentum: float
    volume: float
    funding: float
    structure: float
    history: float
    risk: float
    total: float


class HistoryMatch(BaseModel):
    """Real statistics from actual stored historical snapshots for this
    symbol — not a fabricated hit rate. See app/engine/similarity.py."""

    sample_size: int
    total_history_available: int
    mean_return_pct: float
    median_return_pct: float
    win_rate: float
    avg_drawdown_pct: float | None = None
    horizon_candles: int | None = None
    most_similar_return_pct: float | None = None


class TradePlan(BaseModel):
    symbol: str
    recommendation: str  # "long" | "short" | "no_trade"
    confidence: int  # 0-100 — set from ScoreBreakdown.total, not by the LLM
    entry_low: float | None = None
    entry_high: float | None = None
    stop_loss: float | None = None
    take_profit_1: float | None = None
    take_profit_2: float | None = None
    risk_level: str  # "low" | "medium" | "high"
    time_horizon: str  # "scalp" | "intraday" | "swing" | "position"
    risk_reward: str | None = None
    market_regime: str | None = None
    reasons_for: list[str] = []
    reasons_against: list[str] = []
    invalidation: str | None = None
    historical_comparison: str | None = None
    summary: str
    score_breakdown: ScoreBreakdown | None = None
    history_match: HistoryMatch | None = None
    disclaimer: str = (
        "This is an AI-generated analysis based on current market data, not a "
        "guarantee of future price movement. Not financial advice. Markets are "
        "uncertain and every trade carries risk of loss."
    )


class Opportunity(BaseModel):
    symbol: str
    score: float
    last_price: float
    change_24h_pct: float
    trade_plan: TradePlan
