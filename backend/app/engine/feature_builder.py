import asyncio

from app.data_sources import binance
from app.indicators.technical import compute_indicators, klines_to_df


async def build_features(symbol: str) -> dict:
    klines_1h, klines_4h, klines_1d, premium, oi, ls_ratio = await asyncio.gather(
        binance.get_klines(symbol, "1h", 200),
        binance.get_klines(symbol, "4h", 200),
        binance.get_klines(symbol, "1d", 200),
        binance.get_premium_index(symbol),
        binance.get_open_interest(symbol),
        binance.get_long_short_ratio(symbol),
        return_exceptions=True,
    )

    features: dict = {"symbol": symbol}

    for label, klines in (("1h", klines_1h), ("4h", klines_4h), ("1d", klines_1d)):
        if isinstance(klines, Exception):
            features[f"indicators_{label}"] = None
            continue
        df = klines_to_df(klines)
        features[f"indicators_{label}"] = compute_indicators(df)

    if not isinstance(premium, Exception):
        features["funding_rate"] = float(premium["lastFundingRate"])
        features["mark_price"] = float(premium["markPrice"])

    if not isinstance(oi, Exception):
        features["open_interest"] = float(oi["openInterest"])

    if not isinstance(ls_ratio, Exception) and ls_ratio:
        features["long_short_ratio"] = float(ls_ratio[0]["longShortRatio"])

    return features
