"""Prediction Version Metadata — Karma V3.2 Phase B.

Every new TradeOutcome records exactly which version of each subsystem
produced it. Version constants for modules this session owns
(expected_value.py, trade_manager.py, reliability.py) live in THOSE
modules; entry_quality.py is frozen-adjacent (part of "existing trade
generation logic") and is NOT edited to add a version constant — its
version is tracked here instead, as a manually-maintained string a human
bumps when entry_quality.py itself actually changes. score_formula_version
is NOT duplicated here — it already exists as its own TradeOutcome column
(scoring.py:SCORE_FORMULA_VERSION), reused as-is.

"Never overwrite older metadata" is satisfied by construction: this is
computed ONCE at issuance (trade_outcomes.py:open_trade_outcome()) and
stored on the row; nothing here ever updates an existing row's metadata.
"""

import hashlib
import time

PREDICTION_ENGINE_VERSION = "v3.2"
# Manually maintained — bump this by hand if/when entry_quality.py's
# classification logic actually changes. Not read from that file because
# it doesn't export a version constant and this session doesn't add one
# to a frozen-adjacent file.
ENTRY_QUALITY_VERSION = "v1.1"


def _prompt_hash() -> str:
    """Hashes reasoning.py's own prompt text — a READ of existing string
    constants, not a modification of that file. Lets a future analysis
    detect a prompt content change even on days nobody remembered to bump
    PROMPT_VERSION by hand."""
    from app.engine.reasoning import JSON_INSTRUCTIONS_FULL, PROMPT_VERSION, SYSTEM_PROMPT

    combined = (SYSTEM_PROMPT + JSON_INSTRUCTIONS_FULL + PROMPT_VERSION).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()[:12]


def build_prediction_metadata() -> dict:
    from app.analytics.reliability import RELIABILITY_VERSION
    from app.engine.expected_value import EXPECTED_VALUE_VERSION
    from app.engine.reasoning import PROMPT_VERSION
    from app.engine.scoring import SCORE_FORMULA_VERSION
    from app.engine.trade_manager import TRADE_MANAGER_VERSION

    return {
        "prediction_version": PREDICTION_ENGINE_VERSION,
        "score_formula_version": SCORE_FORMULA_VERSION,
        "entry_quality_version": ENTRY_QUALITY_VERSION,
        "trade_manager_version": TRADE_MANAGER_VERSION,
        "reliability_version": RELIABILITY_VERSION,
        "expected_value_version": EXPECTED_VALUE_VERSION,
        "prompt_version": PROMPT_VERSION,
        "prompt_hash": _prompt_hash(),
        "build_timestamp": int(time.time() * 1000),
    }


def version_comparison_leaderboard(min_sample: int = 3) -> dict:
    """Groups resolved trades by prediction_metadata.prediction_version
    and reports win rate / PF per version — the "did V3 outperform V2"
    question. Only trades issued after this shipped have a
    prediction_metadata value at all; older rows are grouped under
    "unversioned" rather than dropped or guessed at."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models.db_models import TradeOutcome

    session = SessionLocal()
    try:
        rows = (
            session.execute(select(TradeOutcome).where(TradeOutcome.status.in_(("closed_win", "closed_loss"))))
            .scalars()
            .all()
        )
    finally:
        session.close()

    by_version: dict[str, list] = {}
    for r in rows:
        version = (r.prediction_metadata or {}).get("prediction_version", "unversioned")
        by_version.setdefault(version, []).append(r)

    def pf(sub):
        rets = [r.realized_return_pct for r in sub if r.realized_return_pct is not None]
        gains = sum(x for x in rets if x > 0)
        loss = sum(x for x in rets if x < 0)
        return round(gains / abs(loss), 3) if loss else None

    table = []
    for version, sub in sorted(by_version.items(), key=lambda kv: -len(kv[1])):
        wins = sum(1 for r in sub if r.status == "closed_win")
        table.append({
            "prediction_version": version, "n": len(sub),
            "win_rate_pct": round(wins / len(sub) * 100, 1) if sub else None,
            "profit_factor": pf(sub), "reliable": len(sub) >= min_sample,
        })
    return {"versions": table}
