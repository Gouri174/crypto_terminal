import time

import httpx

from app.config import ALTERNATIVE_ME_BASE

_client = httpx.AsyncClient(base_url=ALTERNATIVE_ME_BASE, timeout=10.0)

_CACHE_TTL_SECONDS = 3600  # the index only updates once/day; no need to refetch every scan cycle
_cache: dict | None = None
_cache_at: float = 0.0


async def get_fear_greed_index() -> dict:
    resp = await _client.get("/fng/", params={"limit": 1})
    resp.raise_for_status()
    data = resp.json()["data"][0]
    return {"value": int(data["value"]), "classification": data["value_classification"]}


async def get_cached_fear_greed() -> dict | None:
    """Market-wide, not per-symbol — fetch once per scan cycle, not once
    per symbol. Returns None on failure rather than raising, since this is
    supplementary context, not core data the pipeline depends on."""
    global _cache, _cache_at
    if _cache is not None and (time.time() - _cache_at) < _CACHE_TTL_SECONDS:
        return _cache
    try:
        _cache = await get_fear_greed_index()
        _cache_at = time.time()
    except Exception:
        return _cache  # serve stale cache (if any) rather than nothing
    return _cache
