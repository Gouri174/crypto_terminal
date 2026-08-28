# Performance Center V1

Read-only analytics layer. Nothing in `app/engine/performance_center.py` or
`app/routes/performance.py` writes to `TradeOutcome`, changes
`scoring.py`'s weights, `confidence.py`'s formula, entry/SL/TP generation,
`ml_model.py`, `entry_quality.py`'s thresholds, or `lifecycle.py`. Every
endpoint recomputes from stored rows on each request — nothing is cached
or persisted to a new table (see the module docstring for why: this app
has no cron/scheduler infra by deliberate choice, same reasoning as
`ml_retrain.py`, and at current data volumes recomputing costs nothing
worth caching for).

All endpoints are mounted under `/api/performance/*` (see `app/main.py`).

## 1. Scanner Health — `GET /api/performance/scanner-health`

**What it measures**: whether the scanner process was actually running and
recording `PredictionSnapshot` rows, and for how long it wasn't.

- **Heartbeat**: every distinct `PredictionSnapshot.timestamp` in the DB —
  one per scan cycle that had at least one open/pending trade to check.
- **Outage**: a gap between two consecutive heartbeats longer than
  `gap_threshold_minutes` (default 10, i.e. 2x the default
  `SCAN_INTERVAL_SECONDS`). Can't distinguish "the process was down" from
  "there were zero open trades that cycle" — either way, nothing was
  monitored during that span, which is what matters for stop-execution
  risk.
- **`uptime_pct`**: `(observed_span - total_outage_time) / observed_span`,
  computed only between the first and last heartbeat ever recorded — says
  nothing about time before/after that window.
- **`affected_open_trades`** per outage: symbols with a `TradeOutcome` in
  `status="open"` whose `entry_time` falls before or during the gap and
  whose `exit_time` is null or after the gap start — i.e., trades that were
  genuinely unmonitored for some or all of that outage.

**Query params**: `gap_threshold_minutes` (default 10).

## 2. Stop Execution Audit — `GET /api/performance/stop-execution`

**What it measures**: how far price actually moved past the intended
`stop_loss` before the scanner recorded the exit (`stop_slippage_pct`,
computed once at close in `trade_outcomes.py:_close_trade`).

- Only trades with `stop_hit=True` AND a non-null `stop_slippage_pct` are
  included — older trades that predate the V1.1 `exit_price` capture are
  reported separately as `no_slippage_data_available`, never backfilled or
  estimated.
- **`by_direction`**: long vs short slippage distributions.
- **`by_symbol`**: per-symbol slippage distribution.
- **`by_volatility_bucket`**: buckets by `entry_to_sl_atr` (ATR-normalized
  stop distance, present on trades issued after the level-reasoning
  capture pass) when available, falling back to raw `risk_to_sl_pct`
  (available on every trade) with a `(pct proxy)` label when it isn't —
  never silently mixing the two without saying so.
- **`during_outage_vs_normal`**: splits slippage by whether `exit_time`
  falls inside a scanner-health outage window (same gap definition,
  `outage_gap_threshold_minutes`). In the live data as of this writing,
  outage-window slippage averages an order of magnitude worse than normal
  uptime — see `SESSION_STATUS.md` for the specific incident this
  surfaced (a ~114-hour and a ~170-hour monitoring gap, both correlating
  exactly with the worst short-side losses on record).

**Query params**: `outage_gap_threshold_minutes` (default 10).

## 3. TP Continuation — `GET /api/performance/tp-continuation`

**What it measures**: what happens to a trade AFTER it reaches TP1, using
real intermediate `PredictionSnapshot` prices, not just the trade's final
status.

- **`tp2_probability_given_tp1`**, **`tp3_probability_given_tp2`**:
  intersection-based conditional probabilities (of the trades that reached
  the first target, how many also reached the next one) — NOT a naive
  `count(tp2)/count(tp1)` ratio, which breaks if a trade's TP1/TP2 were
  ever placed out of order (this has happened at least once live; see
  `analysis_48trade_forensic.py`'s anomaly note).
- **`return_to_entry_probability`** / **`return_to_stop_probability`**:
  did price, at any point after `tp1_hit_at`, come back to entry or to the
  original stop. Two real bugs were found and fixed while building this
  (see the docstring on `_post_tp1_path()`):
  - `PredictionSnapshot.current_pnl_pct` is hardcoded to `0.0` for any
    snapshot where `status != "open"` (the closing snapshot itself) — a
    naive `pnl_pct <= 0` check would misread every trade's final row as
    "back at entry." Fixed by comparing `current_price` to `TradeOutcome.entry`
    directly, restricted to snapshots still tagged `status == "open"`.
  - `distance_to_stop_pct` uses the OPPOSITE sign convention from the
    `distance_to_tp*_pct` fields (negative = healthy, for a long) — a
    `<= 0` check would read true almost immediately regardless of real
    price. Fixed by comparing `current_price` to `TradeOutcome.stop_loss`
    directly.
  - Trades with only a single (closing) snapshot after TP1 have no
    intermediate price to check — reported as "undeterminable," not
    silently counted as false.
- **`average_continuation_after_tp1_pct`** / **`average_pullback_after_tp1_pct`**:
  best/worst price excursion relative to entry, among snapshots after
  `tp1_hit_at`.
- **`per_trade`**: the full per-trade breakdown behind the aggregate
  numbers above.

Complements, does not duplicate,
`forensic_diagnostics.py:target_conditional_probabilities()`, which already
reports the aggregate P(TP1)/P(TP2|TP1)/P(TP3|TP2) figures from a
different angle (all resolved trades, not just the post-TP1 path detail).

## 4. Confidence Lab — `GET /api/performance/confidence-lab`

**What it measures**: whether `TradeOutcome.confidence` (0-100) behaves
like a real predicted win probability.

- **`brier_score`**: mean squared error between `confidence/100` and the
  real outcome (1=win, 0=loss) across every resolved trade with a stored
  confidence. Lower is better; 0.25 is what a constant 50% predictor
  scores against a 50/50 base rate.
- **Buckets** (`50-54, 55-59, 60-64, 65-69, 70-74, 75+`, matching the
  convention already used elsewhere in this project's reports): each
  bucket's `avg_predicted_confidence`, `actual_win_rate_pct`, and their
  difference (`calibration_gap`).
- **`expected_calibration_error`**: the standard bucketed ECE — a
  weighted average of `|avg_predicted_confidence - actual_win_rate_pct|`
  across buckets, weighted by each bucket's trade count. Buckets with
  fewer than `min_bucket_n` trades are reported (so nothing is hidden) but
  excluded from the ECE weighting, since a 1-2 trade bucket's "win rate"
  isn't a rate yet.

**Query params**: `min_bucket_n` (default 5).

The pure bucketing/scoring math lives in `_confidence_lab_from_rows()`,
separated from the DB fetch specifically so it can be unit tested against
a hand-built row list instead of whatever happens to be in the live DB —
see `test_performance_center.py`.

## 5. Coin Leaderboard — `GET /api/performance/coin-leaderboard`

**What it measures**: per-symbol profit factor, win rate, average return,
average confidence, average MFE/MAE — ranked by profit factor,
descending. Symbols with fewer than `min_sample` resolved trades are
excluded from the ranked list but counted in
`symbols_excluded_below_min_sample`.

**Query params**: `min_sample` (default 3).

## 6. Trade Replay — `GET /api/performance/trade-replay/{trade_outcome_id}`

**What it returns**: everything needed to replay one trade — the plan as
issued (entry/stop/TPs, confidence/grade/entry_quality), entry indicators
and per-level reasoning (`level_reasoning`, only populated for trades
issued after that capture pass), Claude's reasoning text, the full
`PredictionSnapshot` timeline in order, every TP/SL hit event and
timestamp, the exit price, and a plain-English `exit_reason` derived from
`status`/`stop_hit` (never LLM-authored). 404s (via the route layer) if
the id doesn't exist.

## 7. Trade Manager Analytics — `GET /api/performance/trade-manager`

**Analytics only — nothing here executes, modifies, or closes a trade.**
For every currently `open`/`pending` `TradeOutcome`:

- **`distances`**: sign-adjusted % distance from the latest known price to
  TP1/TP2/TP3/stop.
- **`confidence_trend`**: reports `at_entry` vs `latest_snapshot`
  confidence, but — honestly, not as a bug — these are expected to be
  identical, because this app does not re-explain or re-score an open
  trade after issuance yet (see `PredictionSnapshot.confidence`'s own
  docstring). This field exists so that changes if/when re-explanation
  ships, not to fabricate movement today.
- **`trend_change_momentum_score_delta`** / **`structure_change_score_delta`**:
  the change in the carried-forward `momentum_score`/`structure_score`
  between the first and latest snapshot. There is no separate raw "trend
  score" stored per snapshot to diff against; `momentum_score` is this
  app's existing per-snapshot proxy.
- **`regime_changed`**: whether the market regime at issuance
  (`TradeOutcome.market_regime`) differs from `MarketRegimeState`'s
  current label.
- **`recommendation`**: one of `Hold`, `Move Stop to Breakeven`,
  `Hold for TP3`, `Exit Full` — a small, deterministic, template-built
  heuristic (same contract as `background_scanner.py`'s
  `_rejection_reason()` and `trade_outcomes.py`'s `management_decision`:
  never Claude-authored, never fed back into anything the scanner or
  lifecycle state machine consumes). This is a suggestion surfaced for a
  human to read, not a signal anything in this app acts on.

## Tests

`test_performance_center.py` — same manual-script pattern as every other
test in this project (no pytest infra), fake `ZZZPC*` symbols, cleans up
on success or failure. Covers: outage-gap detection and affected-trade
attribution, stop-slippage direction/volatility-bucket splitting, the two
sign-convention bugs found and fixed while building TP continuation
(regression-tested directly), confidence-lab arithmetic against a hand-
computed Brier score and ECE, coin-leaderboard min-sample gating, trade
replay shape and 404-equivalent behavior, and the Move-Stop-to-Breakeven
recommendation path.
