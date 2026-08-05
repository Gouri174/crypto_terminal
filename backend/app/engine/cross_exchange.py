"""Cross-exchange divergence — real signal, bounded cost.

Rather than fully re-scanning Bybit's and OKX's own universes (which would
multiply Claude/API spend without necessarily improving signal quality —
see the README roadmap), this fetches the SAME symbol's price/funding/open
interest from Bybit and OKX and compares it to Binance's own numbers.
"Liquidity often moves before price" — a funding rate or price diverging
across venues is a real, observable signal that doesn't require guessing,
even without a full multi-exchange universe scan.
"""

import asyncio

from app.data_sources import bybit, okx


async def get_cross_exchange_context(
    symbol: str, binance_price: float | None, binance_funding: float | None
) -> dict:
    bybit_ticker, okx_ticker = await asyncio.gather(
        bybit.get_ticker(symbol), okx.get_ticker(symbol), return_exceptions=True
    )
    bybit_ticker = None if isinstance(bybit_ticker, Exception) else bybit_ticker
    okx_ticker = None if isinstance(okx_ticker, Exception) else okx_ticker

    exchanges: dict = {}
    if binance_price is not None:
        exchanges["binance"] = {"last_price": binance_price, "funding_rate": binance_funding}
    if bybit_ticker:
        exchanges["bybit"] = bybit_ticker
    if okx_ticker:
        exchanges["okx"] = okx_ticker

    price_spread_pct = None
    prices = [e["last_price"] for e in exchanges.values() if e.get("last_price")]
    if len(prices) >= 2:
        price_spread_pct = round((max(prices) - min(prices)) / min(prices) * 100, 4)

    funding_divergence = None
    fundings = [e["funding_rate"] for e in exchanges.values() if e.get("funding_rate") is not None]
    if len(fundings) >= 2:
        funding_divergence = round(max(fundings) - min(fundings), 6)

    return {
        "exchanges": exchanges,
        "price_spread_pct": price_spread_pct,
        "funding_divergence": funding_divergence,
    }
