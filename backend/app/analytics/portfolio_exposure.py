"""Portfolio Exposure Engine — Karma V3.2 Phase D.

Computes exposure across currently OPEN/PENDING TradeOutcome rows only —
read-only, does not gate, block, or change which new trades get taken
(that would require touching background_scanner.py/decision.py, both
frozen this session). A "maximum recommended additional trades" number is
returned as a SUGGESTION for a human to read, same "never executes"
contract as trade_manager.py's recommendations.

Honest limitation, stated once: a true rolling price-correlation matrix
across all traded symbols isn't computable from stored data — only 6
symbols (the legacy-backfilled majors) have any OHLCV history at all
(confirmed repeatedly across this project's forensic reports). This
module reports SYMBOL-FAMILY concentration (crypto-majors/altcoins vs
gold vs equities vs AI-coins vs meme-coins) as the honest, available
substitute for "BTC correlation," not a real correlation coefficient.
"""

from collections import Counter

from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import TradeOutcome

_OPEN_STATUSES = ("pending", "open")

# Same family groupings used in this project's own forensic analysis
# scripts (analysis_karma_v2_forensic.py) — kept here as the one place
# production code needs this mapping, not duplicated.
_FAMILIES = {
    "crypto_majors": {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"},
    "ai_coins": {"NEARUSDT", "WLDUSDT", "HYPEUSDT"},
    "meme_coins": {"DOGEUSDT", "1000PEPEUSDT", "PUMPUSDT"},
    "gold": {"XAUUSDT", "PAXGUSDT", "XAGUSDT"},
    "stocks_etfs": {
        "NVDAUSDT", "MSTRUSDT", "QQQUSDT", "CRCLUSDT", "SPCXUSDT", "SAMSUNGUSDT",
        "SOXLUSDT", "SNDKUSDT", "KORUUSDT", "SOXSUSDT", "SKHYNIXUSDT", "SKHYUSDT", "NBISUSDT",
    },
}
# Families whose members this app has ever observed trading BTC-adjacent
# (i.e. would be expected to move with BTC in a real correlated crypto
# selloff/rally) — the honest proxy for "BTC correlation" (see module docstring).
_CRYPTO_ADJACENT_FAMILIES = {"crypto_majors", "ai_coins", "meme_coins"}

CONCENTRATION_WARNING_THRESHOLD_PCT = 40.0
MAX_RECOMMENDED_OPEN_TRADES = 10  # a stated, adjustable ceiling, not an invented hard limit


def _family_for(symbol: str) -> str:
    for fam, syms in _FAMILIES.items():
        if symbol in syms:
            return fam
    return "other_altcoin"


def _open_rows() -> list[TradeOutcome]:
    session = SessionLocal()
    try:
        return session.execute(select(TradeOutcome).where(TradeOutcome.status.in_(_OPEN_STATUSES))).scalars().all()
    finally:
        session.close()


def _pct(n, d):
    return round(n / d * 100, 1) if d else None


def portfolio_exposure() -> dict:
    rows = _open_rows()
    n = len(rows)
    if n == 0:
        return {"n_open": 0, "note": "No open/pending trades right now.", "max_recommended_additional_trades": MAX_RECOMMENDED_OPEN_TRADES}

    longs = sum(1 for r in rows if r.direction == "long")
    shorts = sum(1 for r in rows if r.direction == "short")

    family_counts = Counter(_family_for(r.symbol) for r in rows)
    family_exposure = {fam: _pct(count, n) for fam, count in family_counts.items()}

    crypto_adjacent_n = sum(count for fam, count in family_counts.items() if fam in _CRYPTO_ADJACENT_FAMILIES)
    btc_correlation_proxy_pct = _pct(crypto_adjacent_n, n)

    warnings = []
    for fam, pct in family_exposure.items():
        if pct is not None and pct > CONCENTRATION_WARNING_THRESHOLD_PCT:
            warnings.append(f"{fam} exposure is {pct}% of open trades — above the {CONCENTRATION_WARNING_THRESHOLD_PCT}% concentration warning threshold.")
    if btc_correlation_proxy_pct is not None and btc_correlation_proxy_pct > 70:
        warnings.append(f"{btc_correlation_proxy_pct}% of open trades are in BTC-correlated families (crypto majors/AI coins/meme coins) — a broad crypto move affects most of this book at once.")

    remaining_capacity = max(0, MAX_RECOMMENDED_OPEN_TRADES - n)

    return {
        "n_open": n,
        "long_count": longs, "short_count": shorts,
        "long_pct": _pct(longs, n), "short_pct": _pct(shorts, n),
        "family_exposure_pct": family_exposure,
        "btc_correlation_proxy_pct": btc_correlation_proxy_pct,
        "btc_correlation_proxy_note": (
            "This is a symbol-family concentration proxy, NOT a computed price-correlation "
            "coefficient — only 6 symbols in this app have any OHLCV history to compute a real "
            "correlation from. See module docstring."
        ),
        "warnings": warnings,
        "max_recommended_additional_trades": remaining_capacity,
    }
