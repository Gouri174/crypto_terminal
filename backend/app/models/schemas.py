from pydantic import BaseModel


class TradePlan(BaseModel):
    symbol: str
    recommendation: str  # "long" | "short" | "no_trade"
    confidence: int  # 0-100
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
    historical_comparison: str | None = None
    summary: str
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
