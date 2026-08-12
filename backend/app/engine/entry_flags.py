"""V1.1 data-collection helpers: risk/reward, market-cluster labeling, and
diagnostic flags computed ONCE at trade issuance. All pure Python, no
Claude call, no network call — nothing here changes score, confidence,
entry/SL/TP generation, or whether a trade is taken. Purely observational,
built to make the NEXT 25-50 resolved trades analyzable the way the first
10 could only partially be (see app/engine/forensic_diagnostics.py's
"NOT STORED" gaps this directly closes).
"""

_OVERBOUGHT_RSI = 80.0
_OVERSOLD_RSI = 20.0

# Static, heuristic classification — this app does not compute rolling
# cross-asset correlations, so this is a coarse, editable label for
# observability only, not a scientific clustering. Anything not listed
# falls back to "Altcoin".
_CLUSTER_MAP = {
    "BTCUSDT": "BTC-correlated",
    "XAUUSDT": "Commodity", "XAGUSDT": "Commodity", "PAXGUSDT": "Commodity",
    "QQQUSDT": "Equity", "NVDAUSDT": "Equity",
    "ETHUSDT": "ETH-correlated", "BNBUSDT": "ETH-correlated", "SOLUSDT": "ETH-correlated",
}


def classify_market_cluster(symbol: str) -> str:
    return _CLUSTER_MAP.get(symbol, "Altcoin")


def compute_risk_reward(
    entry: float | None, stop_loss: float | None,
    tp1: float | None, tp2: float | None, tp3: float | None,
    atr14: float | None = None,
) -> dict:
    """Pure arithmetic on already-decided entry/stop/TP levels — does NOT
    change how those levels are generated, only measures them. NULL
    wherever a level is missing, never estimated.

    atr14 (optional, 4h ATR at issuance) additionally expresses each
    level's distance in ATR units, not just raw %: "SL is 1.5 ATR away"
    is comparable across symbols at wildly different volatility, where
    "SL is 3% away" isn't. Observation only — this does not tell Claude
    where to place a level, only measures where it placed one, feeding
    the organic "Claude usually puts TP1 around N ATR away" dataset."""
    if entry is None or stop_loss is None or entry == 0:
        return {
            "risk_to_sl_pct": None, "reward_to_tp1_pct": None, "reward_to_tp2_pct": None,
            "reward_to_tp3_pct": None, "rr_tp1": None, "rr_tp2": None, "rr_tp3": None,
            "entry_to_sl_atr": None, "entry_to_tp1_atr": None,
            "entry_to_tp2_atr": None, "entry_to_tp3_atr": None,
        }
    risk_pct = abs(entry - stop_loss) / entry * 100

    def _reward(tp: float | None) -> float | None:
        return abs(tp - entry) / entry * 100 if tp is not None else None

    def _rr(reward: float | None) -> float | None:
        return round(reward / risk_pct, 3) if reward is not None and risk_pct else None

    def _atr_distance(level: float | None) -> float | None:
        if level is None or not atr14:
            return None
        return round(abs(level - entry) / atr14, 3)

    r1, r2, r3 = _reward(tp1), _reward(tp2), _reward(tp3)
    return {
        "risk_to_sl_pct": round(risk_pct, 3),
        "reward_to_tp1_pct": round(r1, 3) if r1 is not None else None,
        "reward_to_tp2_pct": round(r2, 3) if r2 is not None else None,
        "reward_to_tp3_pct": round(r3, 3) if r3 is not None else None,
        "rr_tp1": _rr(r1), "rr_tp2": _rr(r2), "rr_tp3": _rr(r3),
        "entry_to_sl_atr": _atr_distance(stop_loss),
        "entry_to_tp1_atr": _atr_distance(tp1),
        "entry_to_tp2_atr": _atr_distance(tp2),
        "entry_to_tp3_atr": _atr_distance(tp3),
    }


def compute_diagnostic_flags(
    breakdown: dict,
    entry_indicators: dict | None,
    entry_quality: str | None,
    risk_reward: dict,
    ml_probability: float | None,
    historic_probability: float | None,
    same_window_signal_count: int,
) -> list[str]:
    """Every flag corresponds to a POSSIBLE-or-weaker pattern from the
    forensic report (app/engine/forensic_diagnostics.py) — computed once at
    issuance for future analysis. NOT used to reject, reweight, or change
    a trade in this pass; a measurement variable only, same status as
    entry_quality."""
    ind = entry_indicators or {}
    flags: list[str] = []

    momentum = breakdown.get("momentum", 0.0)
    structure = breakdown.get("structure", 0.0)
    score = breakdown.get("total", 0.0)

    if momentum >= 12 and structure < 8:
        flags.append("HIGH_MOMENTUM_WEAK_STRUCTURE")
    if score >= 60 and structure < 8:
        flags.append("HIGH_SCORE_WEAK_STRUCTURE")

    atr_distance = ind.get("atr_distance_to_ema20")
    if atr_distance is not None and abs(atr_distance) > 2.5:
        flags.append("HIGH_ATR")

    rsi = ind.get("rsi14")
    if rsi is not None and (rsi > _OVERBOUGHT_RSI or rsi < _OVERSOLD_RSI):
        flags.append("OVERBOUGHT")  # single flag covers overbought-long / oversold-short; direction is on the trade itself

    if historic_probability is None:
        flags.append("NO_HISTORY")
    if ml_probability is None:
        flags.append("NO_ML")

    rr_tp1 = risk_reward.get("rr_tp1")
    if rr_tp1 is not None and rr_tp1 < 1.0:
        flags.append("LOW_TP1_RR")

    if same_window_signal_count > 1:
        flags.append("CLUSTERED_MARKET_EXPOSURE")

    if entry_quality == "late":
        flags.append("LATE_ENTRY")
    if entry_quality == "exhausted":
        flags.append("EXHAUSTED_ENTRY")

    return flags
