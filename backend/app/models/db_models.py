from sqlalchemy import Boolean, Float, Index, Integer, String, UniqueConstraint
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
