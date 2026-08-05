import json
import re

import anthropic

from app.config import ANTHROPIC_MODEL
from app.models.schemas import HistoryMatch, MLPrediction, ScoreBreakdown, TradePlan

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an institutional crypto analyst.

Below you will be given a structured snapshot containing multi-timeframe
technical indicators, market structure (break-of-structure, change-of-
character, fair value gaps — computed from pure price action), funding
rate, open interest, long/short ratio, the overall market regime, a
deterministic score breakdown, real historical analogues for this exact
symbol, ML-model win/drawdown probabilities when available, and free
market context: the Fear & Greed index (features.fear_greed), and real
headlines/Reddit activity relevant to this symbol from free RSS sources
(features.news_context — CoinDesk, Cointelegraph, r/CryptoCurrency). This
is a small, free-tier news/sentiment feed, not a comprehensive one — if
news_context.headlines is empty, that means no relevant headline was found
in the recent feed, not that nothing is happening; say so plainly rather
than inventing news. The reddit_mention_count is a raw mention count, not a
sentiment score — read reddit_sample_titles yourself to judge whether
mentions look bullish, bearish, or neutral; do not assume more mentions
means more bullish. You are also given features.cross_exchange: this
symbol's price/funding/open-interest on Binance vs Bybit vs OKX where
available. A meaningful price_spread_pct or funding_divergence is a real
liquidity-stress signal ("liquidity often moves before price") but is
directionless on its own — it tells you something is unusual across
venues, not which way it resolves.

Your job is NOT to invent indicators or guess missing data. Evaluate ONLY
the supplied evidence. You do NOT decide the confidence score — it is
already computed (see "precomputed_score"); your job is to explain it, not
recompute or override it. Never claim certainty about future price
movement or say a trade is "guaranteed" or "for sure" to succeed.

On historical data: you MAY cite the real dates and numbers given in
history_match verbatim. Never state a date, hit rate, win rate, or
statistic that isn't literally present in the data you were given. If
history_match or ml_prediction is null, there isn't enough stored history
for this symbol yet — say so plainly rather than inventing one.

On regime: read every symbol's setup in the context of the overall market
regime given below (e.g. a bullish altcoin thesis is weaker evidence during
a risk-off regime).

Recommend "no_trade" when the setup is not clean — that is a valid and
often correct answer, not a failure to produce output.

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
  "stop_loss": number or null (with reasoning captured in "invalidation"),
  "take_profit_1": number or null,
  "take_profit_2": number or null,
  "risk_level": "low" | "medium" | "high",
  "time_horizon": "scalp" | "intraday" | "swing" | "position",
  "risk_reward": string or null,
  "market_regime": string or null (one sentence on how the overall regime given below affects THIS symbol's setup),
  "reasons_for": [string, ...],
  "reasons_against": [string, ...],
  "invalidation": string or null (the specific condition(s) that invalidate this setup),
  "historical_comparison": string or null,
  "bullish_scenario": string or null (what has to happen for this to work out, and roughly where it goes),
  "bearish_scenario": string or null (what happens if the thesis is wrong, and roughly where it goes),
  "biggest_risks": [string, ...] (the 2-4 biggest risks to this specific setup),
  "evidence_that_would_increase_confidence": string or null (what additional evidence — not asked for speculatively, just named — would raise or lower confidence if it were available),
  "summary": string (concise, suitable for an experienced trader),
  "disclaimer": string
}
"""

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def build_user_prompt(
    features: dict,
    score_breakdown: dict,
    history_stats: dict | None,
    regime: dict | None,
    ml_prediction: dict | None,
) -> str:
    payload = {
        "market_data": features,
        "precomputed_score": score_breakdown,
        "history_match": history_stats,
        "market_regime": regime,
        "ml_prediction": ml_prediction,
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
    features: dict,
    score_breakdown: dict,
    history_stats: dict | None,
    regime: dict | None = None,
    ml_prediction: dict | None = None,
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
                "content": build_user_prompt(
                    features, score_breakdown, history_stats, regime, ml_prediction
                ),
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
    plan.ml_prediction = MLPrediction(**ml_prediction) if ml_prediction else None

    return plan
