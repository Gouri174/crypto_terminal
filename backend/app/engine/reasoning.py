import json
import re

import anthropic

from app.config import ANTHROPIC_MODEL
from app.engine.confidence import compute_confidence
from app.engine.decision import decide_direction, market_checklist, trade_grade
from app.models.schemas import ConfidenceBreakdown, HistoryMatch, MLPrediction, ScoreBreakdown, TradePlan

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an institutional crypto analyst — specifically,
the head analyst reviewing output from a deterministic trading engine, not
the one deciding what to trade. You explain decisions; you don't make them.

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

CRITICAL — decision consistency: `precomputed_direction` (long / short /
no_trade) and `precomputed_confidence` (0-100) are already decided by the
deterministic engine, from multi-timeframe trend agreement and a weighted-
agreement formula over independent signals, respectively. You do not
choose a direction and you do not decide confidence. Your entry/stop/
targets, reasoning, and every narrative field must be CONSISTENT with
precomputed_direction — never write a long-biased thesis while
precomputed_direction is "short," and never hedge toward a different
number than precomputed_confidence in your prose. If precomputed_direction
is "no_trade," do not invent a directional call — explain plainly why the
setup isn't clean (e.g. mixed higher-timeframe trend, or a score below the
trading threshold) and leave entry/stop/target fields null.

You are also given `precomputed_checklist` (a dict of pass/fail on trend,
structure, volume, funding, history, regime, and risk confirmation) and
`precomputed_grade` (a letter grade derived from confidence). Reference
any checklist item that failed in your reasoning — don't just restate a
number, explain what a "false" means for this specific setup.

If `alternative_candidate` is present, it's the next-best-ranked setup
from this SAME scan cycle (symbol, its own score, and its own
deterministic direction) — not a suggestion you're generating, a fact
about what else scored well right now. If it's genuinely more compelling
than this trade (better risk/reward, cleaner structure, stronger
momentum), write 1-2 sentences in `alternative_trade_reason` saying why.
If it isn't meaningfully better, or there's no alternative_candidate, set
`alternative_trade_reason` to null. You never choose the alternative's
symbol — it's fixed by the engine.

Your job is NOT to invent indicators or guess missing data. Evaluate ONLY
the supplied evidence. Never claim certainty about future price movement
or say a trade is "guaranteed" or "for sure" to succeed.

On historical data: you MAY cite the real dates and numbers given in
history_match verbatim. Never state a date, hit rate, win rate, or
statistic that isn't literally present in the data you were given. If
history_match or ml_prediction is null, there isn't enough stored history
for this symbol yet — say so plainly rather than inventing one.

On regime: read every symbol's setup in the context of the overall market
regime given below (e.g. a bullish altcoin thesis is weaker evidence during
a risk-off regime).

`reasons_against` should read as direct answers to "why should I NOT take
this trade" — specific and actionable, not generic hedging.

Always populate the `disclaimer` field with a plain-English reminder that
this is not financial advice and no outcome is guaranteed."""

JSON_INSTRUCTIONS = """
Respond with ONLY a single JSON object — no markdown code fences, no text
before or after it — matching exactly this shape. Do NOT include
"recommendation", "confidence", "checklist", or "grade" — those are fixed
by the engine and added by the caller, not written by you:

{
  "entry_low": number or null,
  "entry_high": number or null,
  "stop_loss": number or null (with reasoning captured in "invalidation"),
  "take_profit_1": number or null,
  "take_profit_2": number or null,
  "take_profit_3": number or null (a stretch target beyond TP2, only if the setup clearly supports one — null is fine and common),
  "risk_level": "low" | "medium" | "high",
  "time_horizon": "scalp" | "intraday" | "swing" | "position",
  "risk_reward": string or null,
  "market_regime": string or null (one sentence on how the overall regime given below affects THIS symbol's setup),
  "thesis": string or null (one crisp sentence: why does this setup exist right now — distinct from the longer summary below),
  "reasons_for": [string, ...],
  "reasons_against": [string, ...] (direct answers to "why should I NOT take this trade"),
  "invalidation": string or null (the specific condition(s) that invalidate this setup),
  "historical_comparison": string or null,
  "bullish_scenario": string or null (what has to happen for this to work out, and roughly where it goes),
  "bearish_scenario": string or null (what happens if the thesis is wrong, and roughly where it goes),
  "biggest_risks": [string, ...] (the 2-4 biggest risks to this specific setup),
  "evidence_that_would_increase_confidence": string or null,
  "alternative_trade_reason": string or null (see the alternative_candidate instructions above),
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
    direction: str,
    confidence_data: dict,
    checklist: dict,
    grade: str,
    alternative: dict | None,
) -> str:
    payload = {
        "market_data": features,
        "precomputed_score": score_breakdown,
        "precomputed_direction": direction,
        "precomputed_confidence": confidence_data["confidence"],
        "confidence_components": confidence_data["components"],
        "confidence_penalties": confidence_data["penalties"],
        "precomputed_checklist": checklist,
        "precomputed_grade": grade,
        "history_match": history_stats,
        "market_regime": regime,
        "ml_prediction": ml_prediction,
        "alternative_candidate": alternative,
    }
    return (
        "Analyze this futures pair and produce a trade plan explaining the "
        "engine's decision. The direction and confidence below are fixed "
        "and final; explain them, don't recompute or override them.\n\n"
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
    alternative: dict | None = None,
) -> TradePlan:
    direction = decide_direction(features, score_breakdown)
    confidence_data = compute_confidence(direction, score_breakdown, features, history_stats, ml_prediction)
    checklist = market_checklist(score_breakdown, history_stats)
    grade = trade_grade(confidence_data["confidence"])

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
                    features, score_breakdown, history_stats, regime, ml_prediction,
                    direction, confidence_data, checklist, grade, alternative,
                ),
            }
        ],
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        raise ValueError(f"No JSON object found in model response: {text[:500]!r}")

    data = json.loads(match.group(0))
    # Direction, confidence, checklist, and grade are never taken from the
    # model's own JSON — they're injected here from the precomputed values
    # it was told to explain, exactly like score_breakdown/history_match
    # below.
    data["symbol"] = features["symbol"]
    data["recommendation"] = direction
    data["confidence"] = confidence_data["confidence"]
    data["checklist"] = checklist
    data["grade"] = grade

    alt_reason = data.pop("alternative_trade_reason", None)
    data["alternative_trade"] = (
        {"symbol": alternative["symbol"], "reason": alt_reason} if (alternative and alt_reason) else None
    )

    plan = TradePlan.model_validate(data)
    plan.confidence_breakdown = ConfidenceBreakdown(**confidence_data)
    plan.score_breakdown = ScoreBreakdown(**score_breakdown)
    plan.history_match = HistoryMatch(**history_stats) if history_stats else None
    plan.ml_prediction = MLPrediction(**ml_prediction) if ml_prediction else None

    return plan
