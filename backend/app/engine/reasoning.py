import json
import re

import anthropic

from app.config import ANTHROPIC_MODEL
from app.models.schemas import TradePlan

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an institutional-grade cryptocurrency market analyst.

You analyze the market data you are given and produce a trade plan. You are
NOT a fortune teller: you never claim certainty about future price movement,
and you never say a trade is "guaranteed" or "for sure" to succeed. Instead
you estimate probabilities and confidence based on the evidence you were
given, and you clearly acknowledge uncertainty and risk.

You were given technical indicators (multi-timeframe EMA/RSI/MACD/Bollinger
Bands/ATR/ADX/Stochastic RSI/OBV), funding rate, open interest, and long/short
ratio for one futures pair. You do not have a real historical pattern-matching
database, on-chain data, or news/sentiment feeds in this request — do not
invent specific past dates, exact percentages from "similar setups", or
numbers you were not given. If asked to comment on historical similarity,
speak qualitatively and say plainly that this is a qualitative read, not a
database lookup.

Recommend "no_trade" when the setup is not clean — that is a valid and often
correct answer, not a failure to produce output.

Always populate the `disclaimer` field with a plain-English reminder that this
is not financial advice and no outcome is guaranteed."""

JSON_INSTRUCTIONS = """
Respond with ONLY a single JSON object — no markdown code fences, no text
before or after it — matching exactly this shape:

{
  "symbol": string,
  "recommendation": "long" | "short" | "no_trade",
  "confidence": integer 0-100,
  "entry_low": number or null,
  "entry_high": number or null,
  "stop_loss": number or null,
  "take_profit_1": number or null,
  "take_profit_2": number or null,
  "risk_level": "low" | "medium" | "high",
  "time_horizon": "scalp" | "intraday" | "swing" | "position",
  "risk_reward": string or null,
  "market_regime": string or null,
  "reasons_for": [string, ...],
  "reasons_against": [string, ...],
  "historical_comparison": string or null,
  "summary": string,
  "disclaimer": string
}
"""

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def build_user_prompt(features: dict) -> str:
    return (
        "Analyze this futures pair and produce a trade plan. Use only the "
        "data below — do not assume data you were not given.\n\n"
        + json.dumps(features, indent=2, default=str)
        + "\n\n"
        + JSON_INSTRUCTIONS
    )


def analyze_symbol(features: dict) -> TradePlan:
    response = _client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        # Disabled so the full max_tokens budget goes to the JSON answer
        # itself rather than being shared with thinking tokens.
        thinking={"type": "disabled"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(features)}],
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        raise ValueError(f"No JSON object found in model response: {text[:500]!r}")

    plan = TradePlan.model_validate_json(match.group(0))
    plan.symbol = features["symbol"]
    return plan
