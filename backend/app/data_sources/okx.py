import asyncio

import httpx

OKX_BASE = "https://www.okx.com"

_client = httpx.AsyncClient(base_url=OKX_BASE, timeout=10.0)


def _to_okx_inst_id(symbol: str) -> str:
    """"BTCUSDT" -> "BTC-USDT-SWAP" (OKX's perpetual-swap instrument ID)."""
    base = symbol.removesuffix("USDT")
    return f"{base}-USDT-SWAP"


async def get_ticker(symbol: str) -> dict | None:
    inst_id = _to_okx_inst_id(symbol)

    async def _price():
        resp = await _client.get("/api/v5/market/ticker", params={"instId": inst_id})
        resp.raise_for_status()
        rows = resp.json().get("data", [])
        return float(rows[0]["last"]) if rows else None

    async def _funding():
        resp = await _client.get("/api/v5/public/funding-rate", params={"instId": inst_id})
        resp.raise_for_status()
        rows = resp.json().get("data", [])
        return float(rows[0]["fundingRate"]) if rows else None

    async def _open_interest():
        resp = await _client.get("/api/v5/public/open-interest", params={"instId": inst_id})
        resp.raise_for_status()
        rows = resp.json().get("data", [])
        return float(rows[0]["oi"]) if rows else None

    last_price, funding_rate, open_interest = await asyncio.gather(
        _price(), _funding(), _open_interest(), return_exceptions=True
    )

    if isinstance(last_price, Exception):
        return None  # instrument likely doesn't exist on OKX under this name

    return {
        "last_price": last_price,
        "funding_rate": None if isinstance(funding_rate, Exception) else funding_rate,
        "open_interest": None if isinstance(open_interest, Exception) else open_interest,
    }
