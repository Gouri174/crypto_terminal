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


def compute_indicators(df: pd.DataFrame) -> dict:
    close, high, low, volume = df["close"], df["high"], df["low"], df["volume"]

    ema20 = ta.trend.ema_indicator(close, window=20)
    ema50 = ta.trend.ema_indicator(close, window=50)
    ema200 = ta.trend.ema_indicator(close, window=200) if len(close) >= 200 else None
    rsi = ta.momentum.rsi(close, window=14)
    macd = ta.trend.MACD(close)
    bb = ta.volatility.BollingerBands(close)
    atr = ta.volatility.average_true_range(high, low, close, window=14)
    adx = ta.trend.adx(high, low, close, window=14)
    stoch = ta.momentum.StochRSIIndicator(close)
    obv = ta.volume.on_balance_volume(close, volume)

    last_close = float(close.iloc[-1])

    return {
        "last_close": last_close,
        "ema20": _last(ema20),
        "ema50": _last(ema50),
        "ema200": _last(ema200) if ema200 is not None else None,
        "rsi14": _last(rsi),
        "macd": _last(macd.macd()),
        "macd_signal": _last(macd.macd_signal()),
        "macd_hist": _last(macd.macd_diff()),
        "bb_upper": _last(bb.bollinger_hband()),
        "bb_lower": _last(bb.bollinger_lband()),
        "bb_pct": _last(bb.bollinger_pband()),
        "atr14": _last(atr),
        "adx14": _last(adx),
        "stoch_rsi": _last(stoch.stochrsi()),
        "obv": _last(obv),
        "trend_vs_ema20": "above" if last_close > _last(ema20) else "below",
        "trend_vs_ema50": "above" if last_close > _last(ema50) else "below",
    }


def _last(series: pd.Series) -> float | None:
    if series is None or series.empty or pd.isna(series.iloc[-1]):
        return None
    return round(float(series.iloc[-1]), 6)
