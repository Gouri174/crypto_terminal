import json

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


def build_user_prompt(features: dict) -> str:
    return (
        "Analyze this futures pair and produce a trade plan as structured "
        "output. Use only the data below — do not assume data you were not "
        "given.\n\n" + json.dumps(features, indent=2, default=str)
    )


def analyze_symbol(features: dict) -> TradePlan:
    response = _client.messages.parse(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(features)}],
        output_format=TradePlan,
    )
    plan = response.parsed_output
    plan.symbol = features["symbol"]
    return plan
