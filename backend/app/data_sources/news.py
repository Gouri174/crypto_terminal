import asyncio
import time
from xml.etree import ElementTree

import httpx

_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)

# Free, public RSS — no API key. Standard RSS 2.0 <item> format.
FEEDS = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
}

_CACHE_TTL_SECONDS = 300
_cache: list[dict] = []
_cache_at: float = 0.0


async def _fetch_feed(name: str, url: str) -> list[dict]:
    try:
        resp = await _client.get(url)
        resp.raise_for_status()
        root = ElementTree.fromstring(resp.content)
        items = []
        for item in root.findall(".//item")[:15]:
            title = (item.findtext("title") or "").strip()
            if not title:
                continue
            items.append({
                "source": name,
                "title": title,
                "published": (item.findtext("pubDate") or "").strip(),
                "link": (item.findtext("link") or "").strip(),
            })
        return items
    except Exception:
        return []  # a down/changed feed shouldn't break the whole scan


async def get_cached_headlines() -> list[dict]:
    """Shared across every symbol in a scan cycle — fetch once, not once
    per symbol."""
    global _cache, _cache_at
    if _cache and (time.time() - _cache_at) < _CACHE_TTL_SECONDS:
        return _cache
    results = await asyncio.gather(*(_fetch_feed(name, url) for name, url in FEEDS.items()))
    headlines = [h for feed in results for h in feed]
    if headlines:
        _cache = headlines
        _cache_at = time.time()
    return _cache
