import asyncio

from app.data_sources import binance
from app.data_sources.fear_greed import get_cached_fear_greed
from app.engine.cross_exchange import get_cross_exchange_context
from app.engine.news_engine import get_news_context
from app.engine.smart_money import compute_structure
from app.indicators.technical import compute_indicators, klines_to_df


async def build_features(symbol: str) -> dict:
    klines_1h, klines_4h, klines_1d, premium, oi, ls_ratio, fear_greed, news_context = (
        await asyncio.gather(
            binance.get_klines(symbol, "1h", 200),
            binance.get_klines(symbol, "4h", 200),
            binance.get_klines(symbol, "1d", 200),
            binance.get_premium_index(symbol),
            binance.get_open_interest(symbol),
            binance.get_long_short_ratio(symbol),
            get_cached_fear_greed(),
            get_news_context(symbol),
            return_exceptions=True,
        )
    )

    features: dict = {"symbol": symbol}

    for label, klines in (("1h", klines_1h), ("4h", klines_4h), ("1d", klines_1d)):
        if isinstance(klines, Exception):
            features[f"indicators_{label}"] = None
            features[f"structure_{label}"] = None
            continue
        df = klines_to_df(klines)
        features[f"indicators_{label}"] = compute_indicators(df)

        structure = compute_structure(df)
        last = structure.iloc[-1]
        features[f"structure_{label}"] = {
            "trend": last["trend"],
            "bos_up": bool(last["bos_up"]),
            "bos_down": bool(last["bos_down"]),
            "choch": bool(last["choch"]),
            "fvg_up": bool(last["fvg_up"]),
            "fvg_down": bool(last["fvg_down"]),
        }

    binance_price = None
    binance_funding = None
    if not isinstance(premium, Exception):
        binance_funding = float(premium["lastFundingRate"])
        binance_price = float(premium["markPrice"])
        features["funding_rate"] = binance_funding
        features["mark_price"] = binance_price

    if not isinstance(oi, Exception):
        features["open_interest"] = float(oi["openInterest"])

    if not isinstance(ls_ratio, Exception) and ls_ratio:
        features["long_short_ratio"] = float(ls_ratio[0]["longShortRatio"])

    features["fear_greed"] = fear_greed if not isinstance(fear_greed, Exception) else None
    features["news_context"] = news_context if not isinstance(news_context, Exception) else None

    try:
        features["cross_exchange"] = await get_cross_exchange_context(
            symbol, binance_price, binance_funding
        )
    except Exception:
        features["cross_exchange"] = None

    return features
