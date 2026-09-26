# Crypto AI Terminal — Session Status / Handoff

Last updated: 2026-08-13 (48 resolved trades in DB at time of writing).
Purpose of this file: hand a fresh Claude session everything it needs to
continue this project without re-deriving context from scratch.

## What this project is

A standalone AI-powered crypto trading *analysis* platform (not a real
trading bot — no order execution, paper/observation only). FastAPI backend
(`backend/app`), Next.js 15 frontend (`frontend/`), SQLite dev DB via
SQLAlchemy. Runs locally only, no deployment target currently in active use
(render.yaml exists but is not the focus).

Run locally:
```
cd backend
.venv\Scripts\activate       # or Activate.ps1 in PowerShell
uvicorn app.main:app --reload --port 8000
```
Must `cd backend` first — `app.main` only resolves from inside `backend/`,
running uvicorn from the repo root fails with `ModuleNotFoundError: No
module named 'app'`. This has bitten the user once already.

## Core architecture principle — read this before touching anything

**Deterministic-first, Claude explains, never decides** — with one
confirmed, load-bearing exception:

- Direction (long/short/no_trade): 100% deterministic, `decision.py`.
- Confidence, grade, checklist, entry_quality: 100% deterministic.
- Score breakdown (trend/momentum/volume/funding/structure/history/regime/
  ml/sentiment/liquidity/risk): 100% deterministic, `scoring.py`.
- **Entry/stop-loss/TP1/TP2/TP3 PRICE LEVELS are NOT deterministic
  anywhere.** They are free-text JSON fields Claude fills in
  (`reasoning.py`). Confirmed by grep — zero formula anywhere computes
  these. This was the central finding that shaped the most recent major
  piece of work (see "Multi-target / level-reasoning" below).

**Frozen files** — never modify without the user's *explicit, in-the-moment*
authorization, and even then only additively, verified via
`git diff --stat` before every commit:
- `scoring.py`, `confidence.py`, `decision.py`, `lifecycle.py`,
  `market_regime.py`, `background_scanner.py` (core deterministic pipeline)
- `reasoning.py` — was touched this session (adding reasoning-capture
  fields to the JSON schema), but ONLY with explicit authorization, and
  never touching direction/confidence-forcing logic.
- `ml_model.py` — was touched this session (adding calibration metrics),
  additively only, hyperparameters/chronological-split logic untouched.

## Standing behavioral constraints (earned this session, don't relitigate)

1. **Never run process-management commands (kill/Stop-Process) against the
   user's dev server ports** unless the process was started by me, in the
   same turn. A prior process-cleanup command caused the user's real dev
   server to shut down unexpectedly; I disclosed this proactively and
   committed to this constraint. Still active.
2. **Never claim a fix/model is better based on aggregate numbers alone.**
   The user has twice now demanded strict PRE/POST or outlier-controlled
   analysis rather than accepting "win rate went up" at face value — see
   the two forensic reports below. This is a standing expectation for any
   future performance claim.
3. **Git workflow**: local commits only, with
   `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`. The user
   pushes themselves in this session's environment — `git push` has been
   repeatedly blocked by an auto-mode classifier for both this repo and
   others. Ask before pushing; if blocked, hand the user the exact command.
4. **Testing pattern**: no pytest infra in this project. Manual scripts run
   directly (`python test_X.py`) against the REAL dev DB using clearly-fake
   symbols (`ZZZTEST*`, `ZZZV11*`, `ZZZMT*`, `ZZZLR*`), cleaned up via
   try/finally. Existing suites, all currently passing:
   - `test_trade_outcomes.py`
   - `test_entry_quality.py`
   - `test_v11_data_collection.py`
   - `test_multi_target_phase1.py`
   - `test_level_reasoning_and_ml_revalidation.py`
5. **Never modify code during a "read-only forensic analysis" request.**
   The user has asked for this exact framing twice; standalone
   `analysis_*.py` scripts at repo root are the right pattern, not editing
   `forensic_diagnostics.py` under time pressure to add a report route.
6. **Do not optimize/tune anything based on a small resolved-trade sample.**
   Explicit, repeated instruction. Every performance finding must be
   labeled CONFIRMED / POSSIBLE / INSUFFICIENT DATA, and "insufficient" is
   the default until sample sizes clear real thresholds.

## What's been built, roughly chronologically (compressed — full detail in
git log, 89 completed tasks tracked via the session's TaskCreate/TaskUpdate
tool, all marked completed)

**Foundation**: indicators, feature builder, deterministic scorer,
reasoning/Claude integration, Next.js dashboard, SQLAlchemy DB layer
(OHLCV + market snapshots), smart-money structure detection (swings/BOS/
CHOCH/FVG), historical backfill + similarity search, market regime
detection, trade lifecycle state machine, chart API + frontend charts.

**Closed-loop learning**: `TradeOutcome` DB model (append-only, one row per
issued plan, tracked to resolution), `trade_outcomes.py` engine module,
post-mortem/counterfactual computation on close, digest/report aggregation,
score-correlation diagnostics.

**Decision consistency rewrite (v2.0 prompt)**: made direction fully
deterministic (`decision.py`), built composite confidence engine
(`confidence.py` — agreement between independent signals, not the raw
score restated), rewrote `reasoning.py` so Claude explains a fixed
direction/confidence rather than choosing them, added
model/score-formula/prompt versioning recorded on every TradeOutcome row.

**ML probability layer**: `ml_model.py` — XGBoost win/drawdown classifiers
trained on `MarketSnapshot` (25k+ rows, 6 symbols: BTC/ETH/SOL/BNB/ADA/XRP).
Deliberately shallow/regularized hyperparameters after a documented
overfitting incident (66% train acc, 49.6% held-out — worse than base
rate). `ml_retrain.py:retrain_if_better()` — backs up deployed model,
retrains, rolls back if the candidate is worse (tolerance=0.0).

**Entry-quality layer (a69dcb4, 2026-08-10 11:37:37 +0530, epoch ms
`1786342057000`)**: `entry_quality.py` — deterministic
excellent/good/neutral/late/exhausted classification, answering "is now a
good time to enter" separately from "is this a good setup." Wired into
`reasoning.py:_precompute()` (exhausted forces direction to no_trade) and
`background_scanner.py` (late withholds a new/refreshed plan via the
needs_llm gate). **Important structural fact, confirmed from code and
repeatedly verified in the data**: because both gates fire BEFORE a trade
can be opened, `TradeOutcome.entry_quality` can only ever be
excellent/good/neutral/None in practice — late and exhausted trades are
blocked from ever existing as TradeOutcome rows. There is no way to
directly A/B test "what would a late/exhausted trade have done" from this
table; that counterfactual only lives in `ScanSnapshot.rejection_reason`
(not yet analyzed).

**V1.1 pass**: fixed a real safety bug (Avoid-grade "trades" were being
tracked as active — fixed), extended entry-state capture (macd_hist/cmf/
mfi/bb_pct/BTC-state/breadth/risk-reward/diagnostic flags), extended
`ScanSnapshot` with full candidate-pool visibility, built signal funnel /
daily report / why-not / milestones diagnostic reports, frontend surfacing
of entry quality and R:R.

**Multi-target Phase 1** (520a578): extended `PredictionSnapshot` with a
deterministic `stage` (PRE_ENTRY→OPEN→TP1/2/3_REACHED→EXITED) and
`management_decision` (always HOLD while open, with an explicit "Phase 2
not built" reason — no probability is ever fabricated), running MFE/MAE,
at-issuance score/entry-quality carried forward. Built
`target_conditional_probabilities()` in `forensic_diagnostics.py` — real
P(TP1), P(TP2|TP1 reached), P(TP3|TP2 reached) from actual TradeOutcome
data, gated behind min_sample.

**ML revalidation + level-reasoning capture (b208c6f, most recent
substantive commit)** — this was in response to the user explicitly
choosing "option C" from a 3-way architecture proposal:
- Explicitly REJECTED: (A) retroactively calling Claude on 25k historical
  rows to generate TP1/TP2/TP3 labels — too expensive, not reliable ground
  truth; (B) fitting a deterministic TP/SL approximation from the ~18-24
  live trades that existed then — would just be another small-sample model
  built from the data it's meant to diagnose.
- CHOSEN: keep the 25k-row MarketSnapshot dataset for deterministic
  direction/score/ML validation ONLY (never backfill TP1/TP2/TP3 labels
  onto it); for NEW trades going forward, capture Claude's actual
  per-level reasoning and structural evidence so a target-specific model
  can eventually grow ORGANICALLY from real `TradeOutcome` data, never
  backfilled onto old rows.
- Built: `ml_model.py:evaluate_calibration()` (Brier score, log loss,
  hit-rate-by-predicted-bucket) and `ml_retrain.py:retrain_and_compare()`
  (evaluates the previously-deployed model on the CANDIDATE's exact
  held-out chronological test split — true apples-to-apples). Live result:
  old and new model AUC identical (0.544 win / 0.537 drawdown) because no
  new MarketSnapshot data has accumulated since the last train; calibration
  is close to coin-flip (0.4-0.6 predicted bucket hits 45.9% actual).
  **Honest conclusion: the ML win/drawdown models aren't stale, they're
  just weak — more data is what's missing, not a retrain.**
- Built: `TradeOutcome.level_reasoning` (new JSON column) — captures
  Claude's entry/sl/tp1/tp2/tp3_reasoning strings (new TradePlan schema
  fields, new JSON_INSTRUCTIONS in `reasoning.py`), ATR-at-entry,
  structure_level_used (nearest swing high/low oriented to trade
  direction), nearest_support/resistance, fvg_used, and an explicit
  `order_block_note` — investigated and confirmed this codebase has **no
  order-block detection at all** (`smart_money.py` only implements
  swings/BOS/CHOCH/FVG), reported honestly as unavailable rather than
  faked.
- `smart_money.py:compute_structure()` extended to surface the actual
  swing-high/low and FVG price levels it was already computing internally
  (previously discarded after producing only booleans) — purely additive,
  no detection-logic change.
- `entry_flags.py:compute_risk_reward()` extended with ATR-normalized
  distance fields alongside existing %/RR fields.
- **Real bug caught during testing, fixed before commit**: pandas coerces
  `None` to `NaN` in mixed-type DataFrame columns, so `is not None` checks
  in `feature_builder.py` were silently letting NaN through as if it were
  a real value. Fixed with `pd.notna()`. Caught by the new test suite
  `test_level_reasoning_and_ml_revalidation.py`, not by inspection — a
  reminder that this class of bug is easy to introduce when exposing raw
  pandas columns.

**Top-N ranking fix (0472db4, most recent commit)**: `opportunities.py`
now ranks long/short recommendations above no_trade ones in the top-6 feed
— a high-scoring no_trade setup was crowding out an actual tradeable call
in the fixed-size slot. User-reported UI issue (screenshot of ACEUSDT
showing NO TRADE / 0% confidence at rank 1), diagnosed as by-design
(confidence is hardcoded 0 for no_trade, not a bug) but the ranking-priority
issue underneath it was real and got fixed.

## Two forensic analyses performed this session (read-only, standalone
scripts, no code changed) — full findings already delivered to the user
in chat, summarized here for continuity

### `analysis_entry_quality_pre_post.py` (at the 28-resolved-trade mark)
PRE (n=15 entered): win rate 26.7%, avg return -4.475%, PF 0.312.
POST (n=13 entered): win rate 23.1%, avg return +0.121%, PF 1.042 — but PF
collapses to 0.316 (matching PRE almost exactly) once the single best trade
(VELVETUSDT +27.28%) is excluded. Matched-N win rates were IDENTICAL
(23.1% both sides). entry_quality's `late`/`exhausted` categories showed
zero TradeOutcome rows (structural, confirmed from code). Direction mix and
regime differed heavily between groups (confound, not controlled).
**Verdict at the time: INSUFFICIENT DATA, apparent improvement mostly
attributable to one outlier trade + confounds, not entry_quality itself.**

### `analysis_48trade_forensic.py` (at the 48-resolved-trade mark, most
recent, current)
PRE (n=17): win rate 35.3%, PF 0.737. POST (n=31): win rate 41.9%, PF
2.078, and **PF stays above 1 (1.194) even excluding the two biggest POST
winners** — the first genuinely reassuring number across both analyses.
Discovered the aggregate Best (ACEUSDT +39.812%) and Worst (BICOUSDT
-44.418%) trades the user quoted are BOTH pre-entry_quality trades, not
POST — important for not misattributing them.
Loss pattern in POST is now a single clean failure mode: 100% of POST
losses (18/18) stopped before ever reaching TP1; 0% reached TP1 then
reversed (n=12 that reached TP1, all still won). Found and correctly
handled a data anomaly: SOXSUSDT (short) has TP1 farther from entry than
its own TP2 (Claude ordering error), which would have made a naive
P(TP2|TP1) read >100%; fixed to a proper intersection-based conditional
without touching any code.
entry_quality's own internal ordering was found to be INVERTED in POST —
"excellent" (n=6) actually underperformed "good" (n=11) and "neutral"
(n=14) on every metric. Shorts remain materially worse two checks in a row
(POST short win rate 14.3% vs long 50.0%, n=7 — not enough to act on).
Splitting POST into "first 13 (as of the 28-trade check)" vs "new 18 since
then" showed the improvement is concentrated in the newest batch (win rate
23.1%→55.6%) and is NOT explained by regime (unchanged, all "mixed"),
direction mix (still mostly long), or entry_quality category mix
("excellent" went 0/2 in the new batch).
**Final recommendation given: A — freeze and continue collecting data.**
Not B/C/D/E (no code change indicated for entry_quality, weights, ML
retrain, or TP/SL logic) and not yet F (target-specific TP1/TP2/TP3 model
— conditional probabilities are still built on n=5-13, too small to fit
anything to). Target: get POST past 50 entered trades, ideally spanning
more than the single "mixed" regime seen so far, before reconsidering B-F.

## Currently uncommitted / untracked (as of this writing)

- `backend/analysis_entry_quality_pre_post.py` — untracked, read-only.
- `backend/analysis_48trade_forensic.py` — untracked, read-only.
Both were left as-is pending the user's decision on whether to keep them
as reusable tools (commit) or treat as scratch (delete). Not yet resolved
— ask if picking this back up.

## What's NOT done / open threads for a future session

1. **Decide the fate of the two `analysis_*.py` scripts** (commit vs
   delete) — outstanding question to the user, unanswered as of this file.
2. **Keep collecting POST-entry_quality trade data.** Do not act on
   entry_quality, scoring weights, ML retraining, or TP/SL logic until POST
   clears at least 50 entered trades AND ideally sees more than one market
   regime (currently 100% "mixed" throughout all of POST — a real,
   unaddressed confound).
3. **entry_quality's "excellent" bucket underperforming "good"/"neutral"**
   is a genuine open question, currently unexplained and NOT acted on per
   explicit instruction not to tune on this sample size. Worth another
   forensic pass once "excellent" has more than n=6.
4. **Shorts underperforming longs**, two checks in a row (n=7 both times)
   — same treatment: track, don't act, until sample grows.
5. **Target-specific TP1/TP2/TP3 model (Phase 2 of the multi-target
   project)** is explicitly deferred — the organic dataset
   (`TradeOutcome.level_reasoning`, `target_conditional_probabilities()`)
   is being built now specifically so this can eventually be trained on
   real data instead of backfilled/approximated labels. Not ready yet;
   revisit once conditional-probability sample sizes (P(TP2|TP1),
   P(TP3|TP2)) are large enough — currently single digits to low teens.
6. **SOXSUSDT-style TP1/TP2 ordering anomalies** — only one instance found
   so far (1 of 31 POST trades). Worth a quick check if it recurs; not
   currently frequent enough to justify a Claude-prompt or validation
   change on its own.
7. Two open PRs' worth of local commits (`b208c6f`, `0472db4`) — confirmed
   already in sync with `origin/master` as of the last check in this
   session; verify this is still true if resuming after a gap, since the
   user pushes manually and the auto-mode classifier has repeatedly
   blocked `git push` from within the session.
