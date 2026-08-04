import asyncio

import httpx

from app.config import BINANCE_FUTURES_BASE

_client = httpx.AsyncClient(base_url=BINANCE_FUTURES_BASE, timeout=10.0)


async def get_24h_tickers() -> list[dict]:
    resp = await _client.get("/fapi/v1/ticker/24hr")
    resp.raise_for_status()
    return resp.json()


async def get_klines(symbol: str, interval: str, limit: int = 200) -> list[list]:
    resp = await _client.get(
        "/fapi/v1/klines",
        params={"symbol": symbol, "interval": interval, "limit": limit},
    )
    resp.raise_for_status()
    return resp.json()


async def get_historical_klines(
    symbol: str, interval: str, start_time_ms: int, end_time_ms: int
) -> list[list]:
    """Walks [start_time_ms, end_time_ms) in Binance's max-1000-candle pages.
    Used for one-off historical backfills, not the live hot path."""
    all_candles: list[list] = []
    cursor = start_time_ms

    while cursor < end_time_ms:
        resp = await _client.get(
            "/fapi/v1/klines",
            params={
                "symbol": symbol,
                "interval": interval,
                "startTime": cursor,
                "endTime": end_time_ms,
                "limit": 1000,
            },
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break

        all_candles.extend(batch)
        last_open_time = batch[-1][0]
        if last_open_time <= cursor:
            break  # safety net against an infinite loop on a malformed page
        cursor = last_open_time + 1

        if len(batch) < 1000:
            break  # reached the end of available history

        await asyncio.sleep(0.25)  # stay well under Binance's public rate limit

    return all_candles


async def get_premium_index(symbol: str) -> dict:
    resp = await _client.get("/fapi/v1/premiumIndex", params={"symbol": symbol})
    resp.raise_for_status()
    return resp.json()


async def get_open_interest(symbol: str) -> dict:
    resp = await _client.get("/fapi/v1/openInterest", params={"symbol": symbol})
    resp.raise_for_status()
    return resp.json()


async def get_long_short_ratio(symbol: str, period: str = "1h") -> list[dict]:
    resp = await _client.get(
        "/futures/data/globalLongShortAccountRatio",
        params={"symbol": symbol, "period": period, "limit": 1},
    )
    resp.raise_for_status()
    return resp.json()
