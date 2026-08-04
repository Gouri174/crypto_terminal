import pandas as pd
import ta


def klines_to_df(klines: list[list]) -> pd.DataFrame:
    df = pd.DataFrame(
        klines,
        columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades",
            "taker_buy_base", "taker_buy_quote", "ignore",
        ],
    )
    for col in ("open", "high", "low", "close", "volume", "quote_volume"):
        df[col] = df[col].astype(float)
    return df


def compute_indicator_series(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized indicators for every row — used to reconstruct historical
    market states across an entire candle history, not just the latest one."""
    close, high, low, volume = df["close"], df["high"], df["low"], df["volume"]

    ema20 = ta.trend.ema_indicator(close, window=20)
    ema50 = ta.trend.ema_indicator(close, window=50)
    ema200 = ta.trend.ema_indicator(close, window=200)
    rsi = ta.momentum.rsi(close, window=14)
    macd = ta.trend.MACD(close)
    bb = ta.volatility.BollingerBands(close)
    atr = ta.volatility.average_true_range(high, low, close, window=14)
    adx = ta.trend.adx(high, low, close, window=14)
    stoch = ta.momentum.StochRSIIndicator(close)
    obv = ta.volume.on_balance_volume(close, volume)
    cmf = ta.volume.chaikin_money_flow(high, low, close, volume, window=20)
    mfi = ta.volume.money_flow_index(high, low, close, volume, window=14)

    return pd.DataFrame(
        {
            "price": close,
            "ema20": ema20,
            "ema50": ema50,
            "ema200": ema200,
            "rsi14": rsi,
            "macd_hist": macd.macd_diff(),
            "bb_pct": bb.bollinger_pband(),
            "atr_pct": atr / close,
            "adx14": adx,
            "stoch_rsi": stoch.stochrsi(),
            "obv_slope": obv.diff(5),
            "cmf": cmf,
            "mfi": mfi,
        },
        index=df.index,
    )


def compute_indicators(df: pd.DataFrame) -> dict:
    """Latest-value dict for the live single-symbol analysis path."""
    close = df["close"]
    series = compute_indicator_series(df)
    last_close = float(close.iloc[-1])
    macd = ta.trend.MACD(close)
    bb = ta.volatility.BollingerBands(close)

    return {
        "last_close": last_close,
        "ema20": _last(series["ema20"]),
        "ema50": _last(series["ema50"]),
        "ema200": _last(series["ema200"]),
        "rsi14": _last(series["rsi14"]),
        "macd": _last(macd.macd()),
        "macd_signal": _last(macd.macd_signal()),
        "macd_hist": _last(series["macd_hist"]),
        "bb_upper": _last(bb.bollinger_hband()),
        "bb_lower": _last(bb.bollinger_lband()),
        "bb_pct": _last(series["bb_pct"]),
        "atr14": _last(series["atr_pct"]) * last_close if _last(series["atr_pct"]) else None,
        "adx14": _last(series["adx14"]),
        "stoch_rsi": _last(series["stoch_rsi"]),
        "obv_slope": _last(series["obv_slope"]),
        "cmf": _last(series["cmf"]),
        "mfi": _last(series["mfi"]),
        "trend_vs_ema20": "above" if last_close > (_last(series["ema20"]) or last_close) else "below",
        "trend_vs_ema50": "above" if last_close > (_last(series["ema50"]) or last_close) else "below",
    }


def _last(series: pd.Series) -> float | None:
    if series is None or series.empty or pd.isna(series.iloc[-1]):
        return None
    return round(float(series.iloc[-1]), 6)
