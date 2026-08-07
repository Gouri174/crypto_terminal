import asyncio
import time

import httpx

from app.config import BINANCE_FUTURES_BASE

_client = httpx.AsyncClient(base_url=BINANCE_FUTURES_BASE, timeout=10.0)

# get_24h_tickers() is the one call at the very top of every scan cycle
# that nothing else is isolated from — every per-symbol feature fetch is
# already wrapped in return_exceptions=True (see feature_builder.py /
# background_scanner.py), so one bad symbol can't sink a cycle, but until
# now a single ticker-list failure (rate limit, transient network blip, a
# real Binance outage) took the WHOLE cycle down. Retries with backoff
# first; if those also fail, falls back to the last successful response
# rather than raising, so the cycle still runs on slightly stale universe
# data instead of not running at all. staleness/degraded status is
# reported back so it's visible, not silently masked.
_last_good_tickers: list[dict] | None = None
_last_good_at: float | None = None
_TICKER_RETRY_DELAYS = (1.0, 2.0, 4.0)


async def get_24h_tickers() -> tuple[list[dict], dict]:
    """Returns (tickers, status). status = {"degraded": bool, "stale_seconds": float|None,
    "error": str|None} — callers that don't care can just unpack tickers and ignore status."""
    global _last_good_tickers, _last_good_at

    last_exc: Exception | None = None
    for attempt, delay in enumerate((0.0, *_TICKER_RETRY_DELAYS)):
        if delay:
            await asyncio.sleep(delay)
        try:
            resp = await _client.get("/fapi/v1/ticker/24hr")
            resp.raise_for_status()
            tickers = resp.json()
            _last_good_tickers = tickers
            _last_good_at = time.time()
            return tickers, {"degraded": False, "stale_seconds": None, "error": None}
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            print(f"[binance] ticker fetch attempt {attempt + 1} failed: {exc}")
        except httpx.HTTPError as exc:
            last_exc = exc
            print(f"[binance] ticker fetch attempt {attempt + 1} failed: {exc}")

    if _last_good_tickers is not None:
        stale_seconds = time.time() - _last_good_at
        print(
            f"[binance] all ticker fetch attempts failed ({last_exc}); "
            f"falling back to cached tickers, {stale_seconds:.0f}s old"
        )
        return _last_good_tickers, {"degraded": True, "stale_seconds": stale_seconds, "error": str(last_exc)}

    # No prior successful fetch to fall back to (e.g. very first call after
    # a fresh deploy) — nothing to do but surface the real error.
    raise last_exc


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
