import json
import re

import anthropic

from app.config import ANTHROPIC_MODEL
from app.models.schemas import HistoryMatch, ScoreBreakdown, TradePlan

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an institutional-grade cryptocurrency market analyst.

You do NOT decide the confidence score. It has already been calculated
deterministically from the indicator, structure, funding, and historical
data below (see "precomputed_score"). Your job is to EXPLAIN that score —
what evidence supports it, what evidence contradicts it, and under what
condition the thesis would be invalidated — never to invent a different
number or claim certainty about future price movement. Never say a trade is
"guaranteed" or "for sure" to succeed.

You were given: multi-timeframe technical indicators (EMA/RSI/MACD/Bollinger
Bands/ATR/ADX/Stochastic RSI/OBV slope/CMF/MFI), price-structure flags
computed from pure price action (trend, break-of-structure, change-of-
character, fair value gaps — no proprietary data, just OHLCV math), funding
rate, open interest, long/short ratio, and — when available — REAL
historical-similarity statistics computed from this exact symbol's own
stored market history ("history_match": how many similar past states were
found, and what actually happened after them). If history_match is null,
there is not yet enough stored history for this symbol — say so plainly,
do not invent a hit rate or cite specific past dates you were not given.

Recommend "no_trade" when the setup is not clean — that is a valid and often
correct answer, not a failure to produce output.

Always populate the `disclaimer` field with a plain-English reminder that
this is not financial advice and no outcome is guaranteed."""

JSON_INSTRUCTIONS = """
Respond with ONLY a single JSON object — no markdown code fences, no text
before or after it — matching exactly this shape:

{
  "symbol": string,
  "recommendation": "long" | "short" | "no_trade",
  "confidence": integer (MUST equal round(precomputed_score.total) given below),
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
  "invalidation": string or null,
  "historical_comparison": string or null,
  "summary": string,
  "disclaimer": string
}
"""

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def build_user_prompt(
    features: dict, score_breakdown: dict, history_stats: dict | None
) -> str:
    payload = {
        "market_data": features,
        "precomputed_score": score_breakdown,
        "history_match": history_stats,
    }
    return (
        "Analyze this futures pair and produce a trade plan. Use only the "
        "data below — do not assume data you were not given. The "
        "precomputed_score is fixed and final; explain it, don't recompute "
        "or override it.\n\n"
        + json.dumps(payload, indent=2, default=str)
        + "\n\n"
        + JSON_INSTRUCTIONS
    )


def analyze_symbol(
    features: dict, score_breakdown: dict, history_stats: dict | None
) -> TradePlan:
    response = _client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        # Disabled so the full max_tokens budget goes to the JSON answer
        # itself rather than being shared with thinking tokens.
        thinking={"type": "disabled"},
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": build_user_prompt(features, score_breakdown, history_stats),
            }
        ],
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        raise ValueError(f"No JSON object found in model response: {text[:500]!r}")

    plan = TradePlan.model_validate_json(match.group(0))
    plan.symbol = features["symbol"]

    # Never trust the model to correctly echo the calculated score — set it
    # directly from the deterministic source of truth.
    plan.confidence = round(score_breakdown["total"])
    plan.score_breakdown = ScoreBreakdown(**score_breakdown)
    plan.history_match = HistoryMatch(**history_stats) if history_stats else None

    return plan
