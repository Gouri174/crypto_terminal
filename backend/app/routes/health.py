import asyncio
import time

import httpx
from fastapi import APIRouter

from app.data_sources import binance, bybit, okx

router = APIRouter()

_PROBE_SYMBOL = "BTCUSDT"


async def _check_binance() -> dict:
    start = time.time()
    try:
        resp = await binance._client.get("/fapi/v1/premiumIndex", params={"symbol": _PROBE_SYMBOL})
        resp.raise_for_status()
        return {"status": "online", "latency_ms": round((time.time() - start) * 1000)}
    except httpx.HTTPStatusError as exc:
        return {
            "status": "error",
            "http_status": exc.response.status_code,
            "detail": str(exc),
            "latency_ms": round((time.time() - start) * 1000),
        }
    except httpx.HTTPError as exc:
        return {"status": "unreachable", "detail": str(exc), "latency_ms": round((time.time() - start) * 1000)}


async def _check_bybit() -> dict:
    start = time.time()
    try:
        result = await bybit.get_ticker(_PROBE_SYMBOL)
        status = "online" if result else "error"
        return {"status": status, "latency_ms": round((time.time() - start) * 1000)}
    except httpx.HTTPError as exc:
        return {"status": "unreachable", "detail": str(exc), "latency_ms": round((time.time() - start) * 1000)}


async def _check_okx() -> dict:
    start = time.time()
    try:
        result = await okx.get_ticker(_PROBE_SYMBOL)
        status = "online" if result else "error"
        return {"status": status, "latency_ms": round((time.time() - start) * 1000)}
    except httpx.HTTPError as exc:
        return {"status": "unreachable", "detail": str(exc), "latency_ms": round((time.time() - start) * 1000)}


@router.get("/health/exchanges")
async def exchange_health():
    """Pings each exchange with one cheap call so an outage or IP ban (like
    the Binance 418/451 issues this app has hit on shared-IP hosts) is
    immediately visible here instead of only in server logs. Also reports
    whether the scanner's own last successful ticker fetch has fallen back
    to cached data — see app/data_sources/binance.py:get_24h_tickers."""
    binance_status, bybit_status, okx_status = await _gather_all()
    return {
        "binance": binance_status,
        "bybit": bybit_status,
        "okx": okx_status,
        "scanner_ticker_cache": {
            "has_cached_data": binance._last_good_tickers is not None,
            "last_successful_fetch_seconds_ago": (
                round(time.time() - binance._last_good_at) if binance._last_good_at else None
            ),
        },
    }


async def _gather_all():
    return await asyncio.gather(_check_binance(), _check_bybit(), _check_okx())
