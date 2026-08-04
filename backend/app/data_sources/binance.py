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
