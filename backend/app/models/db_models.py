from sqlalchemy import JSON, Boolean, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class OHLCVCandle(Base):
    __tablename__ = "ohlcv_candles"
    __table_args__ = (
        UniqueConstraint("symbol", "interval", "open_time", name="uq_candle"),
        Index("ix_candle_symbol_interval_time", "symbol", "interval", "open_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20))
    interval: Mapped[str] = mapped_column(String(5))
    open_time: Mapped[int] = mapped_column(Integer)  # epoch ms
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)


class MarketSnapshot(Base):
    """One computed market state for a symbol/interval/timestamp.

    Populated by backfilling historical candles (historical_engine.py) and,
    going forward, by live scans. This is the raw material for historical
    similarity search — real stored states, not fabricated comparisons.
    """

    __tablename__ = "market_snapshots"
    __table_args__ = (
        UniqueConstraint("symbol", "interval", "timestamp", name="uq_snapshot"),
        Index("ix_snapshot_symbol_interval_time", "symbol", "interval", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20))
    interval: Mapped[str] = mapped_column(String(5))
    timestamp: Mapped[int] = mapped_column(Integer)  # epoch ms, = candle open_time

    price: Mapped[float] = mapped_column(Float)
    ema20: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema50: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema200: Mapped[float | None] = mapped_column(Float, nullable=True)
    rsi14: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_hist: Mapped[float | None] = mapped_column(Float, nullable=True)
    bb_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    atr_pct: Mapped[float | None] = mapped_column(Float, nullable=True)  # ATR / price
    adx14: Mapped[float | None] = mapped_column(Float, nullable=True)
    stoch_rsi: Mapped[float | None] = mapped_column(Float, nullable=True)
    obv_slope: Mapped[float | None] = mapped_column(Float, nullable=True)
    cmf: Mapped[float | None] = mapped_column(Float, nullable=True)
    mfi: Mapped[float | None] = mapped_column(Float, nullable=True)

    trend: Mapped[str] = mapped_column(String(10))  # "bull" | "bear" | "neutral"
    bos_up: Mapped[bool] = mapped_column(Boolean, default=False)
    bos_down: Mapped[bool] = mapped_column(Boolean, default=False)
    choch: Mapped[bool] = mapped_column(Boolean, default=False)
    fvg_up: Mapped[bool] = mapped_column(Boolean, default=False)
    fvg_down: Mapped[bool] = mapped_column(Boolean, default=False)

    # Realized outcome, computed only when the future is already known (i.e.
    # during historical backfill). Null for recent/live snapshots until
    # enough time has actually passed — never fabricated.
    forward_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    forward_max_drawdown_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    forward_horizon_candles: Mapped[int | None] = mapped_column(Integer, nullable=True)


class LiveOpportunity(Base):
    """The background scanner's always-current state for one symbol.

    Deterministic score + raw features are recomputed and overwritten every
    scan cycle for the whole universe (cheap, no LLM call). trade_plan is
    only refreshed when the symbol is highly ranked or its score has moved
    enough to matter — that's the expensive Claude call, rate-limited by
    design so continuous scanning doesn't mean continuous LLM spend.
    """

    __tablename__ = "live_opportunities"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    updated_at: Mapped[int] = mapped_column(Integer)  # epoch ms, last scan cycle
    last_price: Mapped[float] = mapped_column(Float)
    change_24h_pct: Mapped[float] = mapped_column(Float, default=0.0)

    score_total: Mapped[float] = mapped_column(Float)
    score_breakdown: Mapped[dict] = mapped_column(JSON)
    features: Mapped[dict] = mapped_column(JSON)
    history_match: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    trade_plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    trade_plan_updated_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_llm_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Trade lifecycle state — see app/engine/lifecycle.py. Advances
    # deterministically each scan cycle from live price vs. the stored
    # trade_plan's entry/stop/TP levels; never inferred by the LLM.
    lifecycle_status: Mapped[str] = mapped_column(String(30), default="WAIT")
    lifecycle_plan_signature: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lifecycle_history: Mapped[list] = mapped_column(JSON, default=list)


class TradeOutcome(Base):
    """One AI-generated trade recommendation and everything that happened to
    it afterward. This is the closed-loop learning table: every resolved row
    is a labeled training example (direction, full market state at
    recommendation time, realized outcome) without any manual labeling step
    — the label is just "what actually happened," read back from real price
    data once time has passed. See app/engine/trade_outcomes.py.

    Distinct from LiveOpportunity, which is overwritten every scan cycle and
    only reflects the CURRENT state. This table is append-only: a row is
    created once (when Claude issues a fresh trade plan) and only ever
    updated in place until it resolves, never replaced.
    """

    __tablename__ = "trade_outcomes"
    __table_args__ = (
        Index("ix_outcome_symbol_status", "symbol", "status"),
        Index("ix_outcome_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[int] = mapped_column(Integer)  # epoch ms — when the plan was issued
    symbol: Mapped[str] = mapped_column(String(20))
    exchange: Mapped[str] = mapped_column(String(20), default="binance")
    spot_or_futures: Mapped[str] = mapped_column(String(10), default="futures")
    direction: Mapped[str] = mapped_column(String(10))  # "long" | "short"
    timeframe: Mapped[str] = mapped_column(String(20))  # plan.time_horizon

    # Confidence/grade as actually shown to the user for this plan — see
    # app/engine/confidence.py and app/engine/decision.py:trade_grade.
    # Distinct from `score` below (the ranking score): confidence reflects
    # signal AGREEMENT, score is the raw weighted total. Needed for
    # calibration (does a 90-confidence trade actually win more than a
    # 60-confidence one?) — impossible to answer without storing this.
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # The plan as issued — never mutated after creation.
    entry_low: Mapped[float] = mapped_column(Float)
    entry_high: Mapped[float] = mapped_column(Float)
    entry: Mapped[float] = mapped_column(Float)  # midpoint, for convenience
    stop_loss: Mapped[float] = mapped_column(Float)
    tp1: Mapped[float | None] = mapped_column(Float, nullable=True)
    tp2: Mapped[float | None] = mapped_column(Float, nullable=True)
    tp3: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Lifecycle, tracked by app/engine/trade_outcomes.py from live price —
    # never inferred, never set by the LLM.
    entry_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    tp1_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    tp2_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    tp3_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    stop_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    entry_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exit_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    holding_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    # "pending" (not entered yet) -> "open" (entered) -> "closed_win" |
    # "closed_loss" | "closed_stale" (never entered, expired) | "invalidated"
    # (superseded by a new plan before resolving)
    status: Mapped[str] = mapped_column(String(20), default="pending")

    # The full market state at the moment the plan was issued — the
    # "training example" input side. Mirrors ScoreBreakdown exactly so this
    # table can be joined against future scoring-formula changes.
    score: Mapped[float] = mapped_column(Float)
    trend_score: Mapped[float] = mapped_column(Float, default=0.0)
    momentum_score: Mapped[float] = mapped_column(Float, default=0.0)
    volume_score: Mapped[float] = mapped_column(Float, default=0.0)
    funding_score: Mapped[float] = mapped_column(Float, default=0.0)
    structure_score: Mapped[float] = mapped_column(Float, default=0.0)
    history_score: Mapped[float] = mapped_column(Float, default=0.0)
    regime_score: Mapped[float] = mapped_column(Float, default=0.0)
    ml_score: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    liquidity_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)

    ml_probability: Mapped[float | None] = mapped_column(Float, nullable=True)  # win_probability
    historic_probability: Mapped[float | None] = mapped_column(Float, nullable=True)  # history win_rate/100
    fear_greed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    news_sentiment: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # raw news_context blob
    reddit_sentiment: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # raw reddit context

    reasoning: Mapped[str | None] = mapped_column(String(4000), nullable=True)  # plan.summary
    reasons_for: Mapped[list] = mapped_column(JSON, default=list)
    reasons_against: Mapped[list] = mapped_column(JSON, default=list)
    historical_matches: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # full history_stats
    market_regime: Mapped[str | None] = mapped_column(String(20), nullable=True)  # regime label

    # Realized outcome — only ever computed from real observed price,
    # populated incrementally as price moves and finalized at close.
    realized_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_favorable_price: Mapped[float | None] = mapped_column(Float, nullable=True)  # MFE tracking
    max_adverse_price: Mapped[float | None] = mapped_column(Float, nullable=True)  # MAE tracking
    max_runup_pct: Mapped[float | None] = mapped_column(Float, nullable=True)  # MFE, % from entry
    max_drawdown_pct: Mapped[float | None] = mapped_column(Float, nullable=True)  # MAE, % from entry

    # Post-mortem — computed once at close, see trade_outcomes.py.
    tp1_before_stop: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    key_score_component: Mapped[str | None] = mapped_column(String(20), nullable=True)
    explanation_mentioned_key_factor: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Counterfactual — what the mirrored opposite-direction trade would have
    # done over the same realized price path. See trade_outcomes.py for the
    # simulation method and its honest limitations.
    counterfactual_direction: Mapped[str | None] = mapped_column(String(10), nullable=True)
    counterfactual_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    counterfactual_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Which version of each moving part produced this row — lets a future
    # "did version X actually perform better" analysis separate results by
    # what generated them, instead of silently pooling scores/prompts/
    # models from different eras. See scoring.py, reasoning.py, ml_model.py.
    score_formula_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ml_model_version: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Raw indicator readings at the moment the plan was issued — the "entry
    # timing" / "False Breakout Report" raw material. Deliberately does NOT
    # include distance to the most recent BOS/FVG/swing-high/swing-low:
    # compute_structure() (smart_money.py) only ever surfaces per-candle
    # booleans through feature_builder.py, never the price level itself, so
    # that distance genuinely isn't computable without a separate
    # feature-builder change — not included here rather than faked. Shape:
    # {"rsi14", "stoch_rsi", "adx14", "distance_to_ema20_pct",
    # "distance_to_ema50_pct", "distance_to_ema200_pct",
    # "atr_distance_to_ema20"}, all on the 4h timeframe (matching
    # SIMILARITY_INTERVAL elsewhere).
    entry_indicators: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # First time each target was actually reached — not just whether it
    # eventually was. Enables "time to TP1" analysis (does momentum=15
    # actually lose, or does it just reach the target FASTER, closing the
    # question before this existed you literally couldn't tell those apart
    # from tp1_hit alone). Set once, the first cycle the flag flips true —
    # never overwritten after that.
    tp1_hit_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tp2_hit_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tp3_hit_at: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Entry-timing/exhaustion diagnostic — see app/engine/entry_quality.py.
    # A hypothesis layer built after the first 7-trade forensic analysis,
    # NOT fed back into `score` or `confidence` above. Only ever set on
    # NEW trades from the point this shipped; older rows honestly leave
    # these NULL rather than being backfilled with a guess.
    entry_quality: Mapped[str | None] = mapped_column(String(20), nullable=True)
    entry_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_quality_reasons: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # V1.1 data-collection pass (app/engine/trade_outcomes.py:_close_trade) —
    # the actual observed close price, distinct from `stop_loss`/tp levels.
    # Lets a stop-exit's real fill be compared against the intended stop,
    # separating "the market moved fast between 5-min scan cycles" from "the
    # prediction was simply wrong" — see stop_slippage_pct below. NULL for
    # trades that closed before this shipped, and for any trade still open.
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Only meaningful when the close reason was "stop" — how far past the
    # intended stop_loss price the scanner's next 5-min check actually
    # observed. This is SCANNER_OBSERVED_STOP vs intended stop_loss, not a
    # true tick-level STOP_LEVEL_CROSSED timestamp — this app has no tick
    # data source, so that finer distinction is honestly not computable;
    # documented here rather than faked.
    stop_slippage_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # V1.1: deterministic diagnostic tags computed once at issuance from
    # already-available data (see app/engine/entry_flags.py) — observational
    # labels for later analysis, e.g. HIGH_MOMENTUM_WEAK_STRUCTURE,
    # CLUSTERED_MARKET_EXPOSURE. Never used to reject or change a trade in
    # this pass; a measurement variable only, same as entry_quality above.
    diagnostic_flags: Mapped[list | None] = mapped_column(JSON, nullable=True)


class PredictionSnapshot(Base):
    """One deterministic validation check of an OPEN TradeOutcome, recorded
    every scan cycle. Purely additive — never updated or overwritten, only
    ever INSERTed — so it's a real time series of how a live prediction
    evolved, not a single mutable "current state" like TradeOutcome itself.

    Written by app/engine/trade_outcomes.py:record_snapshot(), called from
    the same update_open_trades() cycle that already checks entry/TP/stop
    against real price — no separate timer, no extra API calls, and NO
    Claude involvement: every field here is arithmetic on data the scanner
    already has this cycle.
    """

    __tablename__ = "prediction_snapshots"
    __table_args__ = (
        Index("ix_snapshot_outcome_id", "trade_outcome_id"),
        Index("ix_snapshot_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_outcome_id: Mapped[int] = mapped_column(Integer)  # FK to TradeOutcome.id, no ORM relationship needed
    timestamp: Mapped[int] = mapped_column(Integer)  # epoch ms
    symbol: Mapped[str] = mapped_column(String(20))

    current_price: Mapped[float] = mapped_column(Float)
    current_pnl_pct: Mapped[float] = mapped_column(Float)  # unrealized, sign-adjusted for direction
    distance_to_tp1_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_to_tp2_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_to_stop_pct: Mapped[float] = mapped_column(Float)

    # Carried over from the TradeOutcome row as of THIS check — confidence/
    # grade don't change after a plan is issued (no re-explanation of open
    # trades yet, see README), but stored per-snapshot anyway so this table
    # is self-contained and doesn't require a join to reconstruct history
    # once that changes.
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(10), nullable=True)
    market_regime: Mapped[str | None] = mapped_column(String(20), nullable=True)

    status: Mapped[str] = mapped_column(String(20))  # TradeOutcome.status at check time
    reason: Mapped[str] = mapped_column(String(200))  # plain-English, deterministic — never LLM-authored


class MarketRegimeState(Base):
    """The scanner's latest market-regime read (single row, id=1).

    Computed from BTC's own trend/structure plus breadth across the
    scanned universe — every symbol's score inherits this context. See
    app/engine/market_regime.py.
    """

    __tablename__ = "market_regime_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    updated_at: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(20))  # "risk_on" | "risk_off" | "mixed"
    trend: Mapped[str] = mapped_column(String(10))  # "bullish" | "bearish" | "ranging"
    confidence: Mapped[int] = mapped_column(Integer)
    btc_trend: Mapped[str] = mapped_column(String(10))
    breadth_bullish_pct: Mapped[float] = mapped_column(Float)
    breadth_bearish_pct: Mapped[float] = mapped_column(Float)
    universe_size: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(String(500))


class ScanSnapshot(Base):
    """Append-only record of EVERY scanned symbol's score/decision each
    cycle — not just the top-ranked ones that go on to become a
    TradeOutcome. LiveOpportunity already computes this for the whole
    universe, but overwrites it in place every cycle; nothing kept the
    history, so "was rank #1 actually better than rank #9" and "what
    scored well but was never published, and why" were both genuinely
    unanswerable — not a small sample size, no data existed at all.

    Pure data capture: nothing here feeds back into scoring, ranking, or
    which symbols get explained/published — see the "no scoring changes"
    rule this project is under. Written every cycle from
    background_scanner.py:_persist_scan(), the same loop that already
    computes rank/score/direction for the whole universe, so this is zero
    extra API or compute cost — just persisting numbers already in memory.
    """

    __tablename__ = "scan_snapshots"
    __table_args__ = (
        Index("ix_scan_snapshot_timestamp", "timestamp"),
        Index("ix_scan_snapshot_symbol", "symbol"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[int] = mapped_column(Integer)  # epoch ms
    symbol: Mapped[str] = mapped_column(String(20))
    rank: Mapped[int] = mapped_column(Integer)  # 0 = highest-scored this cycle
    score_total: Mapped[float] = mapped_column(Float)
    score_breakdown: Mapped[dict] = mapped_column(JSON)
    direction: Mapped[str] = mapped_column(String(10))  # "long" | "short" | "no_trade"

    in_top_candidates: Mapped[bool] = mapped_column(Boolean)  # rank < LLM_CANDIDATES this cycle
    explained_this_cycle: Mapped[bool] = mapped_column(Boolean)  # Claude was (re)called this cycle
    had_active_plan: Mapped[bool] = mapped_column(Boolean)  # already had a live trade_plan from an earlier cycle

    market_regime: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Deterministic, template-built — never LLM-authored (this project never
    # fabricates a reason). None means the symbol WAS published/active this
    # cycle; otherwise a plain-English reason it wasn't. See
    # background_scanner.py:_rejection_reason.
    rejection_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # V1.1: full-candidate-pool visibility (not just published trades) —
    # answers "why did the system choose these 5 instead of the others."
    # All computed deterministically for EVERY scanned symbol in
    # background_scanner.py:_persist_scan — compute_confidence()/
    # trade_grade()/classify_entry_quality() are pure Python, no Claude
    # call, so this costs nothing extra to compute for the whole universe.
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(10), nullable=True)
    entry_quality: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ml_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    historic_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Only populated when this symbol already has a live trade_plan this
    # cycle (entry/stop/tp1 exist to compute a ratio from) — null otherwise,
    # never estimated for a candidate that was never given levels.
    risk_reward_tp1: Mapped[float | None] = mapped_column(Float, nullable=True)
