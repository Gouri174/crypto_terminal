"""Deterministic trade lifecycle state machine.

The status only advances when live price actually crosses a threshold from
the stored trade plan's entry/stop/TP levels — never inferred, never set by
the LLM. Recomputed every scan cycle in background_scanner.py.

WAIT -> PREPARE -> BUY_NOW -> MOVE_STOP_TO_ENTRY -> TAKE_PARTIAL_PROFIT -> HOLD
                                                                              |
                                                        EXIT_TARGET / EXIT_STOPPED
"""

TERMINAL = {"EXIT_TARGET", "EXIT_STOPPED"}
_STAGE_ORDER = {
    "WAIT": 0,
    "PREPARE": 1,
    "BUY_NOW": 2,
    "MOVE_STOP_TO_ENTRY": 3,
    "TAKE_PARTIAL_PROFIT": 4,
    "HOLD": 5,
    "EXIT_TARGET": 6,
    "EXIT_STOPPED": 6,
}


def plan_signature(plan: dict | None) -> str:
    if not plan:
        return "none"
    return f"{plan.get('recommendation')}:{plan.get('entry_low')}:{plan.get('entry_high')}:{plan.get('stop_loss')}"


def advance(
    current_status: str, current_signature: str, price: float, plan: dict | None
) -> tuple[str, str | None, str]:
    """Returns (new_status, reason_if_changed_else_None, new_signature)."""
    new_sig = plan_signature(plan)

    if plan is None or plan.get("recommendation") == "no_trade":
        if current_status != "WAIT":
            return "WAIT", "No active setup this cycle", new_sig
        return "WAIT", None, new_sig

    if new_sig != current_signature and current_status in TERMINAL:
        return "WAIT", "New setup replaces the completed trade", new_sig

    direction = plan.get("recommendation")
    entry_low, entry_high = plan.get("entry_low"), plan.get("entry_high")
    stop, tp1, tp2 = plan.get("stop_loss"), plan.get("take_profit_1"), plan.get("take_profit_2")

    if None in (entry_low, entry_high, stop) or price is None:
        return current_status, None, new_sig  # not enough numeric data to evaluate

    is_long = direction == "long"
    stage = _STAGE_ORDER.get(current_status, 0)

    if current_status in TERMINAL:
        return current_status, None, new_sig

    def in_entry_zone() -> bool:
        return entry_low <= price <= entry_high

    def hit_stop() -> bool:
        return price <= stop if is_long else price >= stop

    def hit_tp(tp: float | None) -> bool:
        if tp is None:
            return False
        return price >= tp if is_long else price <= tp

    # Before an entry has triggered: WAIT / PREPARE / BUY_NOW
    if stage < _STAGE_ORDER["BUY_NOW"]:
        if in_entry_zone():
            return "BUY_NOW", f"Price {price:g} entered the {entry_low:g}-{entry_high:g} entry zone", new_sig
        distance_pct = min(abs(price - entry_low), abs(price - entry_high)) / price * 100
        if distance_pct <= 1.0:
            if current_status != "PREPARE":
                return "PREPARE", f"Price {price:g} is within 1% of the entry zone", new_sig
            return "PREPARE", None, new_sig
        if current_status != "WAIT":
            return "WAIT", "Price moved away from the entry zone", new_sig
        return "WAIT", None, new_sig

    # After entry: manage the open position
    if hit_stop():
        return "EXIT_STOPPED", f"Price {price:g} hit the stop at {stop:g}", new_sig

    if tp2 is not None and hit_tp(tp2):
        return "EXIT_TARGET", f"Price {price:g} reached take-profit 2 at {tp2:g}", new_sig

    if tp1 is not None and hit_tp(tp1):
        if stage < _STAGE_ORDER["TAKE_PARTIAL_PROFIT"]:
            return "TAKE_PARTIAL_PROFIT", f"Price {price:g} reached take-profit 1 at {tp1:g}", new_sig
        return "HOLD", None, new_sig

    if tp1 is not None:
        entry_mid = (entry_low + entry_high) / 2
        halfway = entry_mid + (tp1 - entry_mid) / 2 if is_long else entry_mid - (entry_mid - tp1) / 2
        reached_halfway = price >= halfway if is_long else price <= halfway
        if reached_halfway and stage < _STAGE_ORDER["MOVE_STOP_TO_ENTRY"]:
            return (
                "MOVE_STOP_TO_ENTRY",
                f"Price {price:g} is halfway to TP1 — consider moving stop to breakeven ({entry_mid:g})",
                new_sig,
            )

    if current_status == "BUY_NOW":
        return "HOLD", "Position open, no new trigger this cycle", new_sig

    return current_status, None, new_sig
