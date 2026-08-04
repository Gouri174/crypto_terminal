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

# --- Background scanner ---
# Runs continuously in-process (no Celery/Redis needed for this phase — a
# single asyncio loop satisfies "always analyzed, not on-click" without
# extra infra; upgrade to a real worker queue later if scaling past one
# process). Recomputes the deterministic score for the whole universe every
# cycle; only calls Claude for symbols that are ranked highly enough OR
# whose score has moved enough to warrant a fresh explanation.
SCANNER_ENABLED = os.environ.get("SCANNER_ENABLED", "true").lower() == "true"
SCAN_INTERVAL_SECONDS = int(os.environ.get("SCAN_INTERVAL_SECONDS", "300"))
LLM_SCORE_CHANGE_THRESHOLD = float(os.environ.get("LLM_SCORE_CHANGE_THRESHOLD", "8"))
LLM_MAX_AGE_SECONDS = int(os.environ.get("LLM_MAX_AGE_SECONDS", "1800"))
