import time
from xml.etree import ElementTree

import httpx

# Reddit's RSS requires a real User-Agent or it 429s generic/default clients.
_client = httpx.AsyncClient(
    timeout=10.0,
    follow_redirects=True,
    headers={"User-Agent": "crypto-terminal-research/1.0"},
)

FEED_URL = "https://www.reddit.com/r/CryptoCurrency/.rss"
_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

_CACHE_TTL_SECONDS = 600
_cache: list[dict] = []
_cache_at: float = 0.0


async def _fetch() -> list[dict]:
    try:
        resp = await _client.get(FEED_URL)
        resp.raise_for_status()
        root = ElementTree.fromstring(resp.content)  # Reddit's feed is Atom, not RSS 2.0
        items = []
        for entry in root.findall("atom:entry", _ATOM_NS)[:25]:
            title = (entry.findtext("atom:title", default="", namespaces=_ATOM_NS) or "").strip()
            if title:
                items.append({"title": title})
        return items
    except Exception:
        return []


async def get_cached_posts() -> list[dict]:
    """r/CryptoCurrency's front page as a general market-sentiment pulse —
    not per-symbol (most coins don't have a reliable dedicated subreddit to
    guess at). Shared across a scan cycle, not refetched per symbol."""
    global _cache, _cache_at
    if _cache and (time.time() - _cache_at) < _CACHE_TTL_SECONDS:
        return _cache
    posts = await _fetch()
    if posts:
        _cache = posts
        _cache_at = time.time()
    return _cache
