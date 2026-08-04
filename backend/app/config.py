import os

ANTHROPIC_MODEL = "claude-opus-5"

BINANCE_FUTURES_BASE = "https://fapi.binance.com"
BINANCE_SPOT_BASE = "https://api.binance.com"
ALTERNATIVE_ME_BASE = "https://api.alternative.me"

# How many symbols (by 24h quote volume) to pull from Binance before scoring.
UNIVERSE_SIZE = int(os.environ.get("UNIVERSE_SIZE", "40"))

# How many top-scored symbols get a full LLM reasoning pass per request.
LLM_CANDIDATES = int(os.environ.get("LLM_CANDIDATES", "6"))

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
