"""News + social context — free sources only, no paid APIs.

Filters cached RSS headlines and Reddit posts by simple keyword match
against the symbol's base asset, so Claude can ground "why is this coin
moving" in something other than the chart. This is intentionally simple
(substring match, not NLP sentiment classification) — it surfaces real
headlines/posts for Claude to read and judge, rather than pretending to
score sentiment with a fake precision this data doesn't support.
"""

from app.data_sources import news as news_source
from app.data_sources import reddit as reddit_source

# Base-asset name variants for the symbols this app commonly tracks/backfills.
# Falls back to the bare ticker for anything not listed.
_COIN_NAMES: dict[str, list[str]] = {
    "BTC": ["bitcoin", "btc"],
    "ETH": ["ethereum", "eth", "ether"],
    "BNB": ["bnb", "binance coin"],
    "SOL": ["solana", "sol"],
    "XRP": ["xrp", "ripple"],
    "ADA": ["cardano", "ada"],
    "DOGE": ["dogecoin", "doge"],
    "AVAX": ["avalanche", "avax"],
    "LINK": ["chainlink", "link"],
    "DOT": ["polkadot", "dot"],
}
_MACRO_KEYWORDS = ["fed", "sec", "regulation", "etf", "interest rate", "cpi", "inflation"]


def _keywords_for(symbol: str) -> list[str]:
    base = symbol.replace("USDT", "").upper()
    return _COIN_NAMES.get(base, [base.lower()])


async def get_news_context(symbol: str, headline_limit: int = 5) -> dict:
    keywords = _keywords_for(symbol)

    headlines = await news_source.get_cached_headlines()
    relevant = [h for h in headlines if any(kw in h["title"].lower() for kw in keywords)]
    macro = [
        h for h in headlines
        if h not in relevant and any(kw in h["title"].lower() for kw in _MACRO_KEYWORDS)
    ]
    combined_headlines = [
        {"source": h["source"], "title": h["title"]} for h in (relevant + macro)[:headline_limit]
    ]

    reddit_posts = await reddit_source.get_cached_posts()
    reddit_mentions = [
        p["title"] for p in reddit_posts if any(kw in p["title"].lower() for kw in keywords)
    ][:5]

    return {
        "headlines": combined_headlines,
        "reddit_mention_count": len(reddit_mentions),
        "reddit_sample_titles": reddit_mentions,
    }
