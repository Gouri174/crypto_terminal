from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    """Deterministic, computed score components. Never invented by the LLM —
    see app/engine/scoring.py. Claude explains these numbers; it doesn't
    set them.

    Fields added after the original set default to 0.0 rather than being
    required — LiveOpportunity caches a trade_plan JSON blob that can
    outlive a schema change (a symbol not re-explained this cycle keeps its
    previous plan), and a required field with no default breaks reading
    back anything scored before that field existed. Learned this the hard
    way: a live scan crashed on read with a real ValidationError until
    these got defaults."""

    trend: float
    momentum: float
    volume: float
    funding: float
    structure: float
    history: float
    risk: float
    total: float
    regime: float = 0.0
    ml: float = 0.0
    sentiment: float = 0.0
    liquidity: float = 0.0


class MLPrediction(BaseModel):
    """Output of the trained XGBoost classifiers (app/engine/ml_model.py) —
    Claude explains these numbers, it doesn't produce them. Trained on
    real backfilled outcomes, standardized per-symbol before pooling
    across symbols so raw indicator scale differences (BTC vs a sub-$1
    altcoin) don't bias the model."""

    win_probability: float
    large_drawdown_probability: float


class HorizonReturn(BaseModel):
    horizon: str  # "1d" | "3d" | "7d"
    mean_return_pct: float
    sample_size: int


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
    largest_gain_pct: float | None = None
    largest_loss_pct: float | None = None
    most_similar_dates: list[str] = []
    horizon_returns: list[HorizonReturn] = []
    key_difference: str | None = None


class RegimeInfo(BaseModel):
    """The overall market regime at the time this opportunity was scored —
    see app/engine/market_regime.py. Computed from BTC's trend plus breadth
    across the scanned universe, not asserted by the LLM."""

    label: str  # "risk_on" | "risk_off" | "mixed"
    trend: str  # "bullish" | "bearish" | "ranging" | "transitional"
    confidence: int
    btc_trend: str
    breadth_bullish_pct: float
    breadth_bearish_pct: float
    universe_size: int
    summary: str


class ConfidenceBreakdown(BaseModel):
    """See app/engine/confidence.py. Deliberately separate from
    ScoreBreakdown — the score ranks symbols against each other; this
    reflects how much independent signals AGREE, which is what
    `confidence` is actually set from now."""

    components: dict[str, float]
    penalties: list[str]


class AlternativeTrade(BaseModel):
    """`symbol` is chosen deterministically (the next-best-ranked setup
    this scan cycle, see background_scanner.py) — Claude only writes
    `reason`, it never picks the symbol."""

    symbol: str
    reason: str


class TradePlan(BaseModel):
    symbol: str
    # "long" | "short" | "no_trade" — decided by app/engine/decision.py
    # from multi-timeframe trend agreement, BEFORE Claude is called.
    # Claude explains this call; it cannot change it.
    recommendation: str
    # 0-100 — set from ConfidenceBreakdown's weighted signal agreement
    # (app/engine/confidence.py), not asked of or trusted from the LLM.
    confidence: int
    # A+ | A | B+ | B | C | Avoid — a deterministic function of confidence,
    # see app/engine/decision.py:trade_grade.
    grade: str | None = None
    confidence_breakdown: ConfidenceBreakdown | None = None
    # Deterministic pass/fail on each factor (app/engine/decision.py)  —
    # Claude may reference these in its reasoning, it doesn't compute them.
    checklist: dict[str, bool] = {}
    # A short "why does this setup exist" line, distinct from the longer
    # `summary` below — Claude's, but constrained to the fixed direction.
    thesis: str | None = None
    alternative_trade: AlternativeTrade | None = None
    entry_low: float | None = None
    entry_high: float | None = None
    stop_loss: float | None = None
    take_profit_1: float | None = None
    take_profit_2: float | None = None
    take_profit_3: float | None = None
    risk_level: str  # "low" | "medium" | "high"
    time_horizon: str  # "scalp" | "intraday" | "swing" | "position"
    risk_reward: str | None = None
    market_regime: str | None = None
    reasons_for: list[str] = []
    reasons_against: list[str] = []
    invalidation: str | None = None
    historical_comparison: str | None = None
    bullish_scenario: str | None = None
    bearish_scenario: str | None = None
    biggest_risks: list[str] = []
    evidence_that_would_increase_confidence: str | None = None
    summary: str
    score_breakdown: ScoreBreakdown | None = None
    history_match: HistoryMatch | None = None
    ml_prediction: MLPrediction | None = None
    disclaimer: str = (
        "This is an AI-generated analysis based on current market data, not a "
        "guarantee of future price movement. Not financial advice. Markets are "
        "uncertain and every trade carries risk of loss."
    )


class LifecycleEvent(BaseModel):
    at: int  # epoch ms
    status: str
    reason: str


class Opportunity(BaseModel):
    symbol: str
    score: float
    last_price: float
    change_24h_pct: float
    trade_plan: TradePlan
    lifecycle_status: str = "WAIT"
    lifecycle_history: list[LifecycleEvent] = []
    regime: RegimeInfo | None = None
