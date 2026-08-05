import httpx

BYBIT_BASE = "https://api.bybit.com"

_client = httpx.AsyncClient(base_url=BYBIT_BASE, timeout=10.0)


async def get_ticker(symbol: str) -> dict | None:
    """Bybit's linear-perpetual ticker conveniently returns price, funding,
    and open interest in one call — same symbol format as Binance
    (e.g. "BTCUSDT"), no conversion needed."""
    resp = await _client.get(
        "/v5/market/tickers", params={"category": "linear", "symbol": symbol}
    )
    resp.raise_for_status()
    data = resp.json()
    result_list = data.get("result", {}).get("list", [])
    if not result_list:
        return None
    row = result_list[0]
    return {
        "last_price": float(row["lastPrice"]),
        "funding_rate": float(row["fundingRate"]) if row.get("fundingRate") else None,
        "open_interest": float(row["openInterest"]) if row.get("openInterest") else None,
    }
