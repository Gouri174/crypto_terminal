import json
import re
import time

import anthropic

from app.config import ANTHROPIC_MAX_TOKENS, ANTHROPIC_MAX_TOKENS_SHORT, ANTHROPIC_MODEL, LLM_CANDIDATES
from app.engine.confidence import compute_confidence
from app.engine.decision import decide_direction, market_checklist, trade_grade
from app.models.schemas import ConfidenceBreakdown, HistoryMatch, MLPrediction, ScoreBreakdown, TradePlan

# Explicit timeout: found live that the SDK's default let a call hang for
# 20+ minutes with no error and no completion — for a background scanner
# that's supposed to cycle every few minutes, a silent multi-minute hang is
# worse than a fast, visible failure the loop's own except-and-retry
# already handles.
_client = anthropic.Anthropic(timeout=120.0)

# Bump on any change to what Claude is asked to decide vs. explain, or to
# the JSON contract — recorded on every TradeOutcome row. "2.0" marks the
# decision-consistency rewrite: 1.x let Claude choose direction/confidence
# itself, 2.x forces both from the deterministic engine. That's a real
# behavioral discontinuity worth being able to separate results by, not a
# cosmetic prompt tweak.
PROMPT_VERSION = "2.0"

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
this is not financial advice and no outcome is guaranteed.

Adaptive length: `precomputed_grade` tells you which schema to fill in —
you'll be given either the full analyst-report shape or a short one. On
the short schema (low-grade setups), be brief on purpose: 1-2 items per
list, 2-3 sentence summary. A low-conviction setup doesn't need the same
depth of writeup as a high-conviction one — that's not a shortcut, it's
matching effort to how much this particular call actually matters."""

# Full schema: grade B+ and above — a setup worth the reader's full
# attention gets the full analyst report.
JSON_INSTRUCTIONS_FULL = """
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

# Short schema: grade C or below — a low-conviction (often no_trade) setup
# still deserves a real reason, just not the full report. Deliberately
# drops thesis/scenarios/alternative-trade — those are for setups worth
# dwelling on.
JSON_INSTRUCTIONS_SHORT = """
Respond with ONLY a single JSON object — no markdown code fences, no text
before or after it — matching exactly this shape (this is the SHORT form —
see the adaptive length note above). Do NOT include "recommendation",
"confidence", "checklist", or "grade":

{
  "entry_low": number or null,
  "entry_high": number or null,
  "stop_loss": number or null,
  "take_profit_1": number or null,
  "take_profit_2": number or null,
  "take_profit_3": number or null,
  "risk_level": "low" | "medium" | "high",
  "time_horizon": "scalp" | "intraday" | "swing" | "position",
  "reasons_for": [string, ...] (1-2 items, brief),
  "reasons_against": [string, ...] (1-2 items, brief — why NOT to take this),
  "invalidation": string or null,
  "summary": string (2-3 sentences — why this scored low / isn't clean),
  "disclaimer": string
}
"""

# Appended to SYSTEM_PROMPT only for the batched call — everything above
# still applies per-item; this just explains the array wrapper.
BATCH_ADDENDUM = """

BATCH MODE: you will receive `items`, an array where each element has its
own precomputed_direction/confidence/checklist/grade/schema and market
data — analyze each one independently using every rule above; do not let
one symbol's setup influence another's reasoning. Respond with ONLY a
single JSON ARRAY (no markdown fences, no text outside it), one object per
item, in the same order you received them, and include a "symbol" field
in every object matching that item's symbol so responses can be matched
back reliably even if order isn't preserved. Each item's own `schema`
field ("full" or "short") tells you which shape to fill in for that
specific item — see the FULL and SHORT shapes below; add "symbol": string
as an extra first field on whichever shape you use for that item.
`market_regime_context` is given once, outside `items` — it's the same
overall market regime for every item this cycle, not per-symbol."""

_LOW_GRADES = {"C", "Avoid"}
_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


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
    instructions = JSON_INSTRUCTIONS_SHORT if grade in _LOW_GRADES else JSON_INSTRUCTIONS_FULL
    return (
        "Analyze this futures pair and produce a trade plan explaining the "
        "engine's decision. The direction and confidence below are fixed "
        "and final; explain them, don't recompute or override them.\n\n"
        + json.dumps(payload, indent=2, default=str)
        + "\n\n"
        + instructions
    )


def _precompute(symbol, features, breakdown, history_stats, ml_prediction, alternative) -> dict:
    direction = decide_direction(features, breakdown)
    confidence_data = compute_confidence(direction, breakdown, features, history_stats, ml_prediction)
    checklist = market_checklist(breakdown, history_stats)
    grade = trade_grade(confidence_data["confidence"])
    return {
        "symbol": symbol, "features": features, "breakdown": breakdown,
        "history_stats": history_stats, "ml_prediction": ml_prediction, "alternative": alternative,
        "direction": direction, "confidence_data": confidence_data, "checklist": checklist, "grade": grade,
        "schema": "short" if grade in _LOW_GRADES else "full",
    }


def _finalize_plan(data: dict, pre: dict) -> TradePlan:
    """Shared by the single-symbol and batched paths. Direction, confidence,
    checklist, and grade are never taken from the model's own JSON — always
    injected here from the precomputed values it was told to explain."""
    data = dict(data)
    data["symbol"] = pre["symbol"]
    data["recommendation"] = pre["direction"]
    data["confidence"] = pre["confidence_data"]["confidence"]
    data["checklist"] = pre["checklist"]
    data["grade"] = pre["grade"]

    alt_reason = data.pop("alternative_trade_reason", None)
    alternative = pre["alternative"]
    data["alternative_trade"] = (
        {"symbol": alternative["symbol"], "reason": alt_reason} if (alternative and alt_reason) else None
    )

    plan = TradePlan.model_validate(data)
    plan.confidence_breakdown = ConfidenceBreakdown(**pre["confidence_data"])
    plan.score_breakdown = ScoreBreakdown(**pre["breakdown"])
    plan.history_match = HistoryMatch(**pre["history_stats"]) if pre["history_stats"] else None
    plan.ml_prediction = MLPrediction(**pre["ml_prediction"]) if pre["ml_prediction"] else None
    return plan


def analyze_symbol(
    features: dict,
    score_breakdown: dict,
    history_stats: dict | None,
    regime: dict | None = None,
    ml_prediction: dict | None = None,
    alternative: dict | None = None,
) -> TradePlan:
    pre = _precompute(features["symbol"], features, score_breakdown, history_stats, ml_prediction, alternative)

    max_tokens = ANTHROPIC_MAX_TOKENS_SHORT if pre["grade"] in _LOW_GRADES else ANTHROPIC_MAX_TOKENS
    response = _client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        # Disabled so the full max_tokens budget goes to the JSON answer
        # itself rather than being shared with thinking tokens.
        thinking={"type": "disabled"},
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": build_user_prompt(
                    features, score_breakdown, history_stats, regime, ml_prediction,
                    pre["direction"], pre["confidence_data"], pre["checklist"], pre["grade"], alternative,
                ),
            }
        ],
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        raise ValueError(f"No JSON object found in model response: {text[:500]!r}")

    data = json.loads(match.group(0))
    return _finalize_plan(data, pre)


# Batch calls are capped rather than letting the budget grow unbounded with
# more symbols — a genuinely huge batch should split into two calls, not
# one call asking for an enormous single response. Found live, not
# theoretical: the previous cap (8000) was LOWER than a realistic full
# batch's actual need (LLM_CANDIDATES=6 all at full schema = 6*2500=15000),
# so a 6-symbol batch got silently truncated mid-array — invalid JSON,
# "Expecting ',' delimiter" — and the ENTIRE batch was lost, including
# symbols whose own item would have parsed fine. Sized with real headroom
# above LLM_CANDIDATES' worst case instead of a round number.
BATCH_MAX_TOKENS_CAP = max(20000, LLM_CANDIDATES * ANTHROPIC_MAX_TOKENS + 2000)


def build_batch_user_prompt(pre_items: list[dict], regime: dict | None) -> str:
    items_payload = [
        {
            "symbol": pre["symbol"],
            "schema": pre["schema"],
            "market_data": pre["features"],
            "precomputed_score": pre["breakdown"],
            "precomputed_direction": pre["direction"],
            "precomputed_confidence": pre["confidence_data"]["confidence"],
            "confidence_components": pre["confidence_data"]["components"],
            "confidence_penalties": pre["confidence_data"]["penalties"],
            "precomputed_checklist": pre["checklist"],
            "precomputed_grade": pre["grade"],
            "history_match": pre["history_stats"],
            "ml_prediction": pre["ml_prediction"],
            "alternative_candidate": pre["alternative"],
        }
        for pre in pre_items
    ]
    return (
        "Analyze each of these futures pairs and produce a trade plan "
        "explaining the engine's decision for each. Direction and "
        "confidence are fixed per item; explain them, don't recompute or "
        "override them. market_regime_context applies to every item below "
        "— they're all from the same scan cycle.\n\n"
        + json.dumps({"market_regime_context": regime, "items": items_payload}, indent=2, default=str)
        + "\n\nFULL shape:\n" + JSON_INSTRUCTIONS_FULL
        + "\nSHORT shape:\n" + JSON_INSTRUCTIONS_SHORT
    )


def analyze_batch(items: list[dict], regime: dict | None = None) -> dict[str, TradePlan]:
    """items: list of dicts with keys symbol, features, breakdown,
    history_stats, ml_prediction, alternative — regime is shared across the
    whole batch (same scan cycle). One Claude call covers all of them,
    cutting round-trips and repeated system-prompt overhead vs. one call
    per symbol. Returns {symbol: TradePlan} only for symbols that parsed
    successfully — a malformed or missing item in the response is skipped
    and logged, not treated as a whole-batch failure."""
    if not items:
        return {}

    pre_items = [
        _precompute(it["symbol"], it["features"], it["breakdown"], it["history_stats"],
                    it["ml_prediction"], it["alternative"])
        for it in items
    ]
    budget = sum(ANTHROPIC_MAX_TOKENS_SHORT if p["grade"] in _LOW_GRADES else ANTHROPIC_MAX_TOKENS for p in pre_items)
    max_tokens = min(budget, BATCH_MAX_TOKENS_CAP)

    _start = time.time()
    print(f"[reasoning] batch call starting: {len(items)} symbols, max_tokens={max_tokens}")
    response = _client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        thinking={"type": "disabled"},
        system=SYSTEM_PROMPT + BATCH_ADDENDUM,
        messages=[{"role": "user", "content": build_batch_user_prompt(pre_items, regime)}],
    )
    print(
        f"[reasoning] batch call finished in {time.time() - _start:.1f}s, "
        f"stop_reason={response.stop_reason}, output_tokens={response.usage.output_tokens}"
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    match = _JSON_ARRAY_RE.search(text)
    if not match:
        raise ValueError(f"No JSON array found in batch model response: {text[:500]!r}")
    try:
        raw_items = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Malformed JSON array in batch response ({exc}); "
            f"stop_reason={response.stop_reason}, text_length={len(text)}"
        ) from exc

    by_symbol = {p["symbol"]: p for p in pre_items}
    results: dict[str, TradePlan] = {}
    for raw in raw_items:
        symbol = raw.get("symbol")
        pre = by_symbol.get(symbol)
        if pre is None:
            print(f"[reasoning] batch response included unrecognized symbol {symbol!r}, skipping")
            continue
        try:
            results[symbol] = _finalize_plan(raw, pre)
        except Exception as exc:
            print(f"[reasoning] failed to finalize batched plan for {symbol}: {exc}")
            continue

    missing = set(by_symbol) - set(results)
    if missing:
        print(f"[reasoning] batch response missing symbols: {sorted(missing)}")

    return results
