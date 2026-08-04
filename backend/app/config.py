import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_MODEL = "claude-opus-5"

BINANCE_FUTURES_BASE = "https://fapi.binance.com"
BINANCE_SPOT_BASE = "https://api.binance.com"
ALTERNATIVE_ME_BASE = "https://api.alternative.me"

# How many symbols (by 24h quote volume) to pull from Binance before scoring.
UNIVERSE_SIZE = int(os.environ.get("UNIVERSE_SIZE", "40"))

# How many top-scored symbols get a full LLM reasoning pass per request.
LLM_CANDIDATES = int(os.environ.get("LLM_CANDIDATES", "6"))

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Comma-separated list of allowed frontend origins for CORS, e.g.
# "https://crypto-terminal.vercel.app,https://your-preview-url.vercel.app"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
