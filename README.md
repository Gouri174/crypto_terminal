# Crypto AI Terminal

AI-ranked crypto trade setups: scans Binance USDT-perpetual futures, computes
technical indicators, and uses Claude to produce a trade plan (entry, stop
loss, take-profit levels, confidence, reasoning) for the strongest setups.

**Live frontend:** https://frontend-kappa-six-60.vercel.app — deployed, but
will sit on "Scanning markets…" until the backend is also deployed publicly
(see [Deploying](#deploying)) and `NEXT_PUBLIC_API_BASE_URL` is set on
Vercel to point at it. Right now it only works for whoever has the backend
running on their own `localhost:8000`.

**This is analysis only.** It does not hold exchange API keys, does not place
trades, and every output is explicitly framed as a probabilistic estimate,
never a guarantee. See [Important disclaimers](#important-disclaimers) below
before using this for real trading decisions.

## Architecture principle

**The LLM never invents numbers.** A deterministic pipeline computes
everything measurable — indicators, price structure, and historical
statistics — from real data. Claude's only job is to *explain* that
evidence in plain English: what supports the trade, what contradicts it,
and where the thesis breaks. `confidence` is set in Python from the
computed score, not parsed from what Claude claims it is.

## What's implemented

- **Data**: Binance Futures public REST API (klines, funding rate, open
  interest, long/short ratio) — no exchange API key needed, read-only public
  endpoints.
- **Indicators**: EMA(20/50/200), RSI, MACD, Bollinger Bands, ATR, ADX,
  Stochastic RSI, OBV slope, CMF, MFI — computed across 1h/4h/1d timeframes
  via the `ta` library.
- **Smart-money structure** (`app/engine/smart_money.py`): swing-point
  fractals, break of structure, change of character, and fair value gaps —
  computed from pure OHLCV price action, no paid data or copied source.
- **Historical backfill engine** (`app/engine/historical_engine.py`):
  fetches real Binance OHLCV history and reconstructs every past candle into
  a stored "market snapshot" (indicators + structure), computing each one's
  *actual* realized forward return and drawdown since, for backfilled data,
  the future is already known. Trigger via
  `POST /api/backfill/{symbol}?interval=4h&days=730`.
- **Historical similarity search** (`app/engine/similarity.py`): given the
  current market state, finds the K nearest historical states of that same
  symbol (standardized feature distance) and reports what actually
  happened — win rate, mean/median return, average drawdown, **multi-
  horizon returns (1d/3d/7d, independently computed from stored OHLCV)**,
  largest gain/loss, the **actual dates** of the closest matches, and a
  computed **key-difference** line (the single feature where today
  differs most from the matched group, in standard deviations — e.g. "RSI
  is notably higher than these historical matches"). Real example from
  BTCUSDT's own 4,162 stored candles: 1d +0.26%, 3d +0.80%, **7d −1.80%**
  — the multi-horizon view surfaced a real reversal the single-number
  version would have hidden. Returns `null` rather than a fabricated stat
  when there isn't enough history yet.
- **ML probability layer** (`app/engine/ml_model.py`, `POST /api/train-ml`):
  gradient-boosted classifiers (XGBoost) trained on the already-backfilled
  historical snapshots to predict win probability and large-drawdown
  probability, standardized per-symbol before pooling across symbols (a
  MACD histogram of 150 means something completely different for BTC than
  for a sub-$1 altcoin — pooling raw values would silently bias the model).
  **Honest result, not oversold:** the first version (200 trees, depth 4)
  hit 66% training accuracy but only 49.6% on held-out future data — *worse*
  than the 50.1% base rate, i.e. it had memorized noise. Reduced to a
  shallow, heavily-regularized model (50 trees, depth 2, strong L2) that
  generalizes to a real but modest edge: **52.8% test accuracy vs 46.1%
  baseline, test AUC 0.544** (0.5 = coin flip). Weighted low in the scoring
  formula (±8 points, vs ±25 for trend) to match that weak-but-real signal
  — and in live testing, Claude correctly read a near-coin-flip prediction
  and flagged it as a risk ("a coin-flip with fat left tail; position size
  accordingly") rather than treating it as strong evidence. Returns `null`
  rather than a fabricated probability when models aren't trained yet or a
  symbol lacks enough history.
- **Deterministic scoring model** (`app/engine/scoring.py`): a fixed,
  documented weighted formula (trend, momentum, volume, funding, structure,
  history match, regime fit, ML prediction, sentiment, cross-exchange
  liquidity, risk penalty) — this is the confidence score. Claude explains
  it; it cannot change it.
- **Free market context — sentiment & news** (`app/data_sources/fear_greed.py`,
  `app/data_sources/news.py`, `app/data_sources/reddit.py`,
  `app/engine/news_engine.py`): all free-tier, no paid API keys.
  - **Fear & Greed Index** (alternative.me, 1h cache): scored deliberately
    small and one-directional — only extreme readings (≤20 or ≥80) move the
    score (±3), and only as a mild contrarian flag. Not treated as a
    trend signal.
  - **News headlines** (CoinDesk + Cointelegraph RSS, 5min cache) and
    **Reddit** (r/CryptoCurrency RSS, 10min cache, requires a real
    `User-Agent` header or Reddit 429s the request): keyword-matched
    against the symbol's coin name and macro keywords, passed to Claude as
    raw context (headlines + sample post titles + a mention count) — **not
    scored numerically**. A mention-count spike could mean bullish
    excitement or panic-selling discussion; distinguishing those needs
    actual reading, so the prompt tells Claude to read the sample titles
    itself rather than trusting a fabricated sentiment score.
- **Cross-exchange liquidity check** (`app/data_sources/bybit.py`,
  `app/data_sources/okx.py`, `app/engine/cross_exchange.py`): for each
  scored symbol, fetches the same pair's price/funding/open-interest from
  Bybit and OKX (public REST, no keys) alongside Binance, and computes
  price-spread% and funding-rate divergence across venues. Scored as a
  small, **directionless** penalty (−3/−2) — a real cross-venue spread is a
  liquidity-stress signal ("liquidity often moves before price") but says
  nothing about which way it resolves, so it never pushes the score long
  or short. Deliberately scoped to the same-symbol check, not a full
  second/third universe scan — that would multiply LLM/API cost by
  exchange count for coverage, not signal quality.
- **Decision consistency** (`app/engine/decision.py`): direction
  (long/short/no_trade) is no longer Claude's call. `decide_direction()`
  reads the same multi-timeframe trend votes `scoring.py` already computes
  — majority of 1h/4h/1d trend-vs-EMA50, gated by a minimum total score
  (`MIN_SCORE_FOR_TRADE`, currently 45) — and a tie or sub-threshold score
  is `no_trade`. This is computed BEFORE Claude is ever called and injected
  into `TradePlan.recommendation` after parsing; the model's own JSON is no
  longer even asked for a recommendation field. `market_checklist()`
  (trend/structure/volume/funding/history/regime/risk pass-fail, plain
  thresholds on already-computed values) and `trade_grade()` (A+ through
  Avoid, a deterministic function of confidence) are the same pattern —
  computed, injected, never asked of the model.
- **Composite confidence** (`app/engine/confidence.py`): replaces "confidence
  = the score" with a weighted-agreement formula over independent signals
  (25% trend, 20% historical similarity, 15% ML, 15% structure, 10% volume,
  5% each funding/regime/sentiment — direction-agnostic components are
  normalized against their own max, trend/ML explicitly measure agreement
  *with the chosen direction*, not just "is this signal strong"), then
  applies penalties: historical similarity pointing the opposite direction
  (−15), crowded long/short positioning (−8), wide cross-exchange spread
  (−5), unusually high ATR-based volatility (−5). A high raw score with a
  contradicting historical match now reads as lower-confidence than the
  score alone would suggest — which is the point. `ScoreBreakdown.total`
  still exists unchanged and still ranks symbols against each other;
  confidence is a genuinely separate number now.
- **AI reasoning, as head analyst not predictor**: Claude
  (`claude-sonnet-5` by default — see Cost controls below) is told the
  direction, confidence, checklist, and grade are already decided and must
  explain them, never contradict them. It
  produces: a one-line `thesis`, entry/stop/TP1-3, reasons for and
  explicitly "why NOT to take this trade," an invalidation point,
  bullish/bearish scenarios, the biggest risks, what evidence would change
  confidence, and — when a deterministically-chosen `alternative_candidate`
  from the same scan cycle scored within 15 points — a sentence on whether
  it's genuinely more compelling (the alternative's symbol is fixed by the
  engine, Claude only writes the reason). Requests a JSON object directly
  in the prompt and parses it (rather than the Anthropic API's
  `output_format`/structured-outputs feature, which hit a "Grammar
  compilation timed out" error on this schema during testing).
  **Verified two ways**: first with a mocked Claude response
  (`backend/test_reasoning_mock.py`) covering the full parse/inject/
  validate path, including that a mocked bullish-sounding response still
  gets forced to `no_trade` when the deterministic direction says so; then
  against a REAL live call once API credits were available — a genuine
  BTCUSDT response came back with `grade: "B+"`, a fully-populated
  checklist, a real `thesis`, a real `take_profit_3`, and `reasons_against`
  correctly framed as "why not." That live run also caught a real bug (see
  Cost controls below).
- **Cost controls**: found via the account actually running out of
  credits — `GET /api/analyze/{symbol}` had NO caching at all. Every page
  load, every refresh, called Claude live, completely bypassing the
  background scanner's cost gating. Fixed:
  - **Shared cache gate** (`app/engine/llm_gate.py:should_reexplain`): both
    the scanner and `/api/analyze` now use the identical decision — skip
    Claude if a cached explanation exists, its direction still matches,
    its score hasn't moved ≥`LLM_SCORE_CHANGE_THRESHOLD` (8 points), and
    it's younger than `LLM_MAX_AGE_SECONDS` (30 min). Direction-change is a
    new trigger the scanner didn't have before either. **Verified live
    against a real call**: same symbol, requested twice — first call took
    31s (real Claude latency) and cost real tokens; second call, 1.3s
    later, returned in ~1s with a `trade_plan` byte-identical to the first
    (score/last_price differ, as they should — those are recomputed live
    every request; the explanation itself was reused, not regenerated).
  - **Model**: default switched from Opus to `claude-sonnet-5`
    (`ANTHROPIC_MODEL` env-overridable) — this is a structured-output
    explanation task over data Python already computed, not open-ended
    research, so Opus's premium wasn't buying anything.
  - **Output budget**: `max_tokens`, env-overridable via
    `ANTHROPIC_MAX_TOKENS`. First tried 1200 (down from the original,
    untested 4096) — **live testing caught this immediately**: a real call
    hit `stop_reason: "max_tokens"` and got cut off mid-JSON, which broke
    the parser outright (`ValueError: No JSON object found`). Raised to
    2500, confirmed live afterward to complete with room to spare. Left as
    a documented near-miss rather than silently fixed, since it's the
    exact kind of regression a token-budget cut can cause without anyone
    noticing until a request actually fails.
  - **Batched Claude calls** (`app/engine/reasoning.py:analyze_batch`):
    all of a scan cycle's `to_explain` symbols now go into ONE Claude call
    (a JSON array response) instead of one call per symbol — cuts
    round-trips and repeated system-prompt overhead. Each item still gets
    its own precomputed direction/confidence/checklist/grade injected
    exactly like the single-symbol path (`_finalize_plan()` is shared by
    both, no duplicated logic). A malformed or missing item in the
    response is skipped and logged, not treated as a whole-batch failure.
    **Verified live**: real cycles produced a 2-symbol batch (SOL+QQQ) and
    a 3-symbol batch (ZEC+EWY+SNDK) — the 3-symbol one's own reasoning
    text for SNDK correctly said "the weakest of the three setups here,"
    confirming Claude saw the batch as related items without the
    reasoning cross-contaminating between symbols.
  - **Adaptive explanation length**: grade (computed before Claude runs)
    selects a FULL schema (thesis, scenarios, alternative-trade writeup)
    for B+ and above, or a deliberately short one (1-2 items per list, no
    thesis/scenarios) for C/Avoid — with a correspondingly smaller
    `ANTHROPIC_MAX_TOKENS_SHORT` budget (700 vs 2500). Verified via the
    mocked-response test; not yet observed live simply because no C/Avoid
    setup has landed in the top-ranked explained set during live testing
    — the code path is the same one the mock exercises, just not yet
    seen with a real low-grade Claude response.
  - **Deliberately NOT done in this pass**: further prompt
    summarization/shortening beyond what adaptive length already gives;
    skipping Claude entirely for `no_trade`/low-grade setups (the existing
    explanations are genuinely useful, not just a cost sink); a manual
    "regenerate" button on the frontend (the cache fix above already
    removes the reason one would be needed).
- **Model/formula/prompt versioning**: `score_formula_version`
  (`scoring.py`), `prompt_version` (`reasoning.py`), and `ml_model_version`
  (`ml_model.py`) are recorded on every `TradeOutcome` row — added via a
  generic auto-migration (see below) rather than a one-off manual fix, so
  future version bumps just work. Exists so a future "did version 3.2
  actually perform better than 3.1" analysis can separate results by what
  produced them, instead of silently pooling scores from different eras.
- **Auto-migrating additive schema changes** (`app/db.py:_sync_additive_columns`):
  this project hit the "new nullable column doesn't exist on the old dev
  DB" class of bug twice already (a cached JSON blob missing a key, and a
  scanner tuple-shape mismatch). `init_db()` now walks every model's
  columns after `create_all()` and `ALTER TABLE ADD COLUMN`s anything
  missing — only ever adds, never drops or alters. **Verified live**: ran
  against the existing dev DB with real `TradeOutcome` rows already in it;
  added 3 new columns, all 7 existing rows stayed readable.
- **Retrain-if-better safety wrapper** (`app/engine/ml_retrain.py`):
  `ml_model.train_models()` always overwrote the deployed model files
  immediately — fine for the first deploy, dangerous for every retrain
  after. `retrain_if_better()` backs up the deployed files, retrains,
  compares the candidate's test AUC against the previously-deployed
  model's recorded metrics (`ml_models/metadata.json`), and rolls back to
  the backup if the candidate is worse — never silently deploys a
  regression. **Verified live with real data** (24,972 labeled snapshots):
  tested all three paths — first deploy (no prior metadata), a genuine
  regression correctly rejected and rolled back (confirmed via file hash
  comparison that the model files were byte-identical to before the
  attempt), and a genuine improvement correctly deployed. `POST
  /api/train-ml` now uses this wrapper; the "deployed" field in its
  response tells you whether the retrain actually took effect. No
  automatic nightly scheduling — this app has no cron/scheduler infra, and
  with current data volume a nightly retrain would mostly have nothing new
  to learn from; wiring this to a clock is a separate, later addition.
- **Feature importance / correlation reporting** (`GET /api/outcomes/correlations`,
  `app/engine/trade_reports.py:feature_importance`): extended with
  human-readable labels, sorted by absolute impact, and an optional
  `?limit=N` to ask "what's mattered in the last N resolved trades"
  instead of always all-time — useful as more data accumulates and older
  scoring-formula eras shouldn't dilute a current read. Still gated behind
  a minimum sample size and still explicitly not a significance test.
- **Storage**: SQLAlchemy, SQLite by default (zero extra infra), swap to
  Postgres by setting `DATABASE_URL` — no code changes needed.
- **Exchange resilience** (`app/data_sources/binance.py:get_24h_tickers`,
  `GET /api/health/exchanges`): the universe-ticker fetch — one call at the
  top of every scan cycle that nothing else was isolated from — now
  retries with backoff (1s/2s/4s) and, if all retries fail, falls back to
  the last successful response rather than raising. A scan runs on
  slightly stale universe data instead of not running at all; the scan
  summary and server log both mark this as `degraded` rather than
  masking it silently. Every per-symbol feature fetch was already
  isolated (`return_exceptions=True`), so this closes the one real
  single-point-of-failure that was left. `GET /api/health/exchanges`
  pings Binance/Bybit/OKX directly and reports the scanner's own ticker
  cache staleness, so an outage or IP ban is visible in one request
  instead of only in server logs — built directly in response to hitting
  exactly this class of problem live (see Deploying → Backend → Render
  for the Binance-IP-ban story this came from).
- **Continuous background engine** (`app/engine/background_scanner.py`):
  runs as a single in-process asyncio loop (no Celery/Redis needed for this
  phase — see below), started at app startup. Every `SCAN_INTERVAL_SECONDS`
  (default 300s) it recomputes score + features for the whole universe —
  cheap, no LLM involved — and persists it, so the dashboard is already
  analyzed the moment someone opens it. Claude is only called for symbols
  that are top-ranked **and** (never explained yet, OR score moved by
  `LLM_SCORE_CHANGE_THRESHOLD`, OR the last explanation is older than
  `LLM_MAX_AGE_SECONDS`) — this is what keeps LLM spend bounded regardless
  of universe size, instead of scaling with (coins × minutes). A
  `POST /api/opportunities`-serving `GET` reads this cached state directly;
  it does not trigger a live scan itself.
- **Live push** (`app/ws.py`, `GET /ws/opportunities`): a lightweight
  WebSocket notifies the frontend when a scan cycle finishes, so the
  dashboard refreshes automatically (with auto-reconnect) instead of
  polling. The frontend re-fetches via the normal REST call on that signal
  rather than trusting a pushed payload — simple, hard to get out of sync.
- **Market regime detection** (`app/engine/market_regime.py`,
  `GET /api/regime`): classifies the overall market — risk-on/risk-off/mixed,
  trend, confidence — from BTC's own trend plus breadth across the scanned
  universe (% of coins above their 4h EMA50). Every symbol's score inherits
  this as a `regime` component (bonus for aligning with the regime, penalty
  for fighting it, neutral when the regime itself is genuinely mixed).
  Deliberately lags scoring by one scan cycle to avoid a circular
  dependency (breadth needs everyone's features to exist first) — documented
  in the module, not a bug.
- **Trade lifecycle engine** (`app/engine/lifecycle.py`): a deterministic
  state machine — WAIT → PREPARE → BUY_NOW → MOVE_STOP_TO_ENTRY →
  TAKE_PARTIAL_PROFIT → HOLD → EXIT_TARGET/EXIT_STOPPED — advanced every
  scan cycle purely from live price crossing the stored plan's entry/stop/
  TP levels. No LLM involved in the transitions; each change is logged with
  a plain-English reason into a per-symbol timeline shown on the detail
  page. Verified across real scan cycles: three symbols advanced
  WAIT → BUY_NOW as price entered their entry zones between cycles.
- **Frontend**: Next.js dashboard with ranked opportunity cards, a live
  indicator, a market-regime banner, and per-symbol lifecycle badges; the
  detail page renders the score breakdown as bars (component/max, e.g.
  "14.19/25"), the historical-match stats, and the lifecycle timeline.
- **AI-annotated chart** (`app/engine/chart_data.py`, `GET /api/chart/{symbol}`,
  `frontend/components/ChartPanel.tsx`): a real `lightweight-charts`
  candlestick chart (TradingView's own open-source library — no paid
  Charting Library license) with EMA20/50/200 overlays, price lines for the
  entry zone/stop-loss/TP1/TP2, and markers for BOS/CHoCH/FVGs and detected
  order blocks (the last opposite-colored candle before a structure break —
  a standard heuristic, computed, not fetched). Every overlay is clickable
  and shows a real explanation: trade-level clicks reuse Claude's actual
  `reasons_for`/`reasons_against`/`invalidation` text verbatim; structure
  markers get a deterministic, template-based description of what was
  detected. **Deliberately no per-click LLM call** — that would reintroduce
  uncontrolled cost exactly where the background-scanner design worked hard
  to bound it. Verified end-to-end: real candle/EMA/marker/order-block data
  reaches the frontend, and the click → explanation-panel interaction works
  (tested live). **Known limitation of this dev session, not of the shipped
  code:** the automated browser used to test this session doesn't composite
  frames to a real display (confirmed directly — `requestAnimationFrame`-
  driven canvas painting never executes, while everything synchronous, like
  `chart.options()` and `series.data()`, reports correct values throughout).
  That means the actual pixel rendering of the candlestick chart could not
  be visually confirmed in this environment; every other layer (data
  fetching, chart configuration, click interactivity) was. Open the app in
  a normal browser to see the chart itself.

- **Closed-loop trade outcome tracking** (`app/models/db_models.py:TradeOutcome`,
  `app/engine/trade_outcomes.py`, `app/engine/trade_reports.py`,
  `GET /api/outcomes`, `GET /api/digest/{daily,weekly,monthly}`,
  `GET /api/outcomes/correlations`): this is the piece that used to be
  genuinely missing — nothing tracked whether the AI's own recommendations
  were actually profitable. Every fresh Claude trade plan now becomes one
  append-only `TradeOutcome` row: the full market state at the moment of
  recommendation (every score component, ML probability, historical-match
  stats, fear/greed, news/Reddit context, the reasoning text) plus entry/
  stop/TP1-3. Nothing is fabricated after the fact — every field below is
  read back from real price:
  - **Lifecycle**: `pending` (issued, not yet entered) → `open` (price
    entered the zone) → `closed_win` / `closed_loss` (hit the outermost
    defined target or the stop) / `closed_stale` (never entered within 14
    days) / `invalidated` (a materially different plan replaced it before
    it resolved). Tracked every scan cycle from real price, not inferred.
  - **MFE/MAE**: `max_runup_pct`/`max_drawdown_pct` record the best and
    worst price actually reached while the position was open — so a trade
    that "won" via TP1 but ran to +9% before pulling back shows that, not
    just the +TP1% it closed at.
  - **Post-mortem** (computed once, at close): `key_score_component` (the
    score component with the largest absolute contribution to that trade's
    score) and `explanation_mentioned_key_factor` (a keyword-match check —
    intentionally simple, not NLP — of whether Claude's own reasoning text
    referenced that component).
  - **Counterfactual**: `counterfactual_return_pct` — what the exact
    opposite direction would have returned over the identical entry-to-exit
    price path. This is the honest, cheap version of "what if we'd gone
    short instead," not a full independent simulation of the opposite
    trade's own stop/target (see the docstring in `trade_outcomes.py` for
    the exact limitation).
  - **Reports**: `performance_digest()` (wins/losses, TP1/2/3 hit rate,
    average return, profit factor, a simplified non-annualized Sharpe, and
    equity-curve max drawdown) at daily/weekly/monthly windows, plus
    `monthly_breakdown()` (best/worst coin and strategy, most-accurate
    timeframe, best regime — each gated behind a minimum sample size so one
    lucky/unlucky trade can't dominate the label) and `score_correlations()`
    (mean score-component value among wins minus losses, gated behind 20
    resolved trades — a diagnostic, not a significance test).
  - **Verified live**: real Claude-issued plans (with a real `take_profit_3`
    when the setup supports one — added to the schema/prompt alongside this
    work) flow into this table during actual scan cycles; two positions
    transitioned `pending` → `open` as real price entered their zones
    between cycles during testing. Win/loss/close-path logic was verified
    with simulated price ticks (`backend/test_trade_outcomes.py`) since real
    trades take days to resolve — that script is honest about being a
    manual verification script, not a pytest suite (there's no test infra
    elsewhere in this project either).
  - **Found and fixed while building this**: `market_regime.classify_regime`
    had been silently crashing at the end of every scan cycle since
    `ml_prediction` was added to the scanner's internal tuple earlier in the
    project — a 5-value unpack against what had become a 6-tuple. It was
    swallowed by the scan loop's broad `except Exception`, so it never
    surfaced as a request-facing error, it just meant `MarketRegimeState`
    had been stale for a while. Fixed; regime now updates every cycle again
    (verified live — confirmed a fresh row write after the fix).
- **Prediction validation system** — an evaluation layer, not another
  prediction engine. Extends the closed-loop tracking above; deliberately
  reuses `TradeOutcome`, `update_open_trades()`'s existing cycle, and
  `trade_reports.py` rather than building a parallel system.
  - **`confidence`/`grade` now stored on `TradeOutcome`** — a real gap:
    these were computed per-plan but discarded after building the
    `TradePlan` response, so no calibration analysis was possible. Now
    threaded from `analyze_batch()`'s output through to `open_trade_outcome()`.
  - **`PredictionSnapshot`** (`app/models/db_models.py`, new table): one
    row per open/pending `TradeOutcome` per scan cycle — timestamp, price,
    unrealized pnl%, distance to TP1/TP2/stop, confidence, grade, regime,
    status, a deterministic plain-English reason. Strictly append-only
    (only ever `INSERT`, never `UPDATE`) — a real time series of how a
    live prediction evolved, not another mutable "current state" row.
    Written by `record_snapshot()`, called from the SAME
    `update_open_trades()` cycle that already checks entry/TP/stop — no
    second timer, no extra API calls, zero Claude involvement anywhere in
    this path. **Verified live**: a real open CYSUSDT position recorded a
    real snapshot (0.48% pnl, 7.1% to TP1, stop 10.5% below price,
    regime `risk_on`) during an actual scan cycle.
  - **Calibration** (`GET /api/outcomes/calibration/{confidence,grade}`):
    buckets resolved trades by their stored confidence/grade and reports
    ACTUAL win rate per bucket — "does a 90-confidence trade really win
    more than a 60-confidence one?" Gated behind a minimum sample per
    bucket, and only ever includes trades that have a stored
    confidence/grade — older rows honestly excluded, not backfilled with
    a guess. **Currently 0 eligible trades** in production, since the
    confidence/grade field only started being recorded this session — this
    will fill in as new trades resolve, not something to fake in the
    meantime.
  - **`GET /api/digest/signals/{daily,weekly}`**: a different slice from
    the existing digests — scores signals by when they were ISSUED, not
    when they resolved, and explicitly reports still-open ones alongside
    completed ones ("today's picks, however far they've gotten"), matching
    the "Today's Signals / Completed / Still Open" report shape. The
    existing `/digest/daily` etc. stay as-is (scored by resolution time) —
    both are real, different questions, not a redundant duplicate.
  - **`GET /api/digest/90day`, `GET /api/outcomes/open-count`**: straightforward
    extensions of the existing digest/count pattern.
  - **`GET /api/outcomes/{id}/snapshots`**: the full append-only history for
    one trade — the raw material for a future frontend "prediction
    progress" view.
  - **Deliberately deferred, not silently dropped**: a periodic
    Claude-generated "prediction update" (re-explaining an open trade only
    on real state changes — invalidation, TP/stop hit, material confidence
    shift) has real cost/complexity and needed its own pass, not folding
    into this one; the frontend Live Prediction Page (progress bars per
    open trade) is pure UI work on top of what's now built, not started
    yet; chart annotation decluttering (fading older BOS/CHoCH/FVG
    markers) touches chart-generation code untouched by this pass.
- **Research diagnostics** — built after inspecting the first 3 real
  resolved trades (all losses) and finding a real, honest caveat: they
  were all created during this session's own manual pipeline testing
  (forced re-explanations within a short window), not organic operation,
  so treating "0% win rate" as a system-quality verdict would have been
  wrong. Built the tools to actually investigate instead of guessing:
  - **`momentum_vs_runup()`** (`GET /api/outcomes/momentum-runup`): tests
    a specific hypothesis — does a maxed-out `momentum_score` at entry
    predict WORSE forward movement (late/exhausted entries) rather than
    better (clean confirmation)? Buckets resolved trades by momentum
    score, reports average MFE/MAE and win rate per bucket. Zero schema
    change — pure analysis over `momentum_score`/`max_runup_pct`, both
    already stored.
  - **`evidence_coverage()`** (`GET /api/outcomes/evidence-coverage`): of
    the sources that can genuinely be unavailable for a given symbol (ML
    prediction, historical similarity, sentiment — NOT trend/momentum/
    volume/structure/funding/regime, which are always computed once
    features exist), how often did each actually participate, and does
    coverage correlate with outcome? A trade scored with zero ML/history
    backing carries more uncertainty than the raw score alone shows.
  - **`entry_indicators`** (new JSON column on `TradeOutcome`): RSI/
    stochRSI/ADX and distance to EMA20/EMA50 on the 4h timeframe, captured
    at the moment each plan is issued — the raw material for a future
    "false breakout" investigation (what do losing setups have in common
    right before they fail). Deliberately does NOT include distance to
    the most recent BOS/FVG price level: `compute_structure()`
    (`smart_money.py`) only ever surfaces per-candle booleans through
    `feature_builder.py`, never the swing-high/low level itself, so that
    specific distance isn't computable without a real feature-builder
    change — left out rather than faked. **Verified live**: a real fresh
    XAUUSDT trade captured real RSI 81.4 / stochRSI 0.75 / ADX 45.9 /
    +2.4% from EMA20 at entry.
  - **Found and fixed via this exact live test**: `BATCH_MAX_TOKENS_CAP`
    was 8000 — lower than a realistic full 6-symbol batch's actual need
    (6 × 2500 = 15000). A 6-symbol batch got silently truncated mid-array
    (invalid JSON, "Expecting ',' delimiter"), losing the ENTIRE batch
    including symbols whose own item would have parsed fine. Raised with
    real headroom above `LLM_CANDIDATES`'s worst case. Also found: the
    Anthropic client had no explicit timeout, and one live call hung for
    20+ minutes with no error before this was caught — added
    `timeout=120.0` and call-duration logging so a hang fails fast and
    visibly instead of silently. A real repeat call after both fixes
    completed cleanly in 76.1s (`stop_reason=end_turn`, 7295 output
    tokens, well under the new cap).
  - **Entry timing extension**: `entry_indicators` gained
    `distance_to_ema200_pct` and `atr_distance_to_ema20` (distance from
    the fast EMA expressed in ATR units, not just raw % — "0.2 ATR above
    EMA20" and "2 ATR above EMA20" are very different entries at the same
    raw percentage on a low- vs high-volatility symbol). Distance to the
    most recent BOS/FVG/swing-high/swing-low remains deferred for the same
    reason as before — not surfaced by `compute_structure()`.
  - **`tp1_hit_at`/`tp2_hit_at`/`tp3_hit_at`** (new nullable columns on
    `TradeOutcome`): the first time each target was actually reached, set
    once and never overwritten after. Answers a genuinely different
    question from `tp1_hit` alone — does a maxed momentum score actually
    LOSE more, or does it just reach TP1 FASTER (closing out the position
    before this existed, those two were indistinguishable from the boolean
    flag alone). `momentum_vs_time_to_tp1()`
    (`GET /api/outcomes/momentum-time-to-tp1`) is the report built on top —
    deliberately kept separate from `momentum_vs_runup()` rather than
    merged into one number, since a component can be "good" on one axis
    (speed) and neutral on the other (win rate). **Verified**: synthetic
    test confirms the timestamp is set once on first hit and never mutated
    by later cycles checking the same open trade; real production data
    correctly shows 0 eligible trades (the field just landed, honestly not
    backfilled).

- **AI research assistant** (`app/engine/ask_router.py`, `POST /api/ask`):
  the old `/api/ask` regex-extracted a symbol and dumped its raw live
  indicator features into a free-form Claude prompt — it never touched
  `TradeOutcome`, `PredictionSnapshot`, or any calibration/diagnostic
  report, so Claude was answering from the same data a trade card already
  shows, not reasoning over the system's actual track record. Rewritten so
  Claude explains real data instead of guessing:
  - **Deterministic router, not NLU**: `classify()` keyword-matches the
    question into zero or more fixed categories (best trades today,
    current trades, system accuracy, confidence/grade calibration, feature
    importance, momentum patterns, long-vs-short, regime performance,
    retrain recommendation) and `gather_context()` calls the matching
    report functions BEFORE any Claude call — Claude only ever sees
    already-computed numbers, never live market data it could hallucinate
    around. A "today"/"this week"/"this month"/"90 day" phrase in the
    question sets the report window (defaults to 30 days).
  - **Symbol matching is a whitelist, not a blocklist** — found live while
    testing: an early version flagged any 2-15 char uppercase word as a
    ticker candidate and filtered common English words with a stopword
    list, which broke immediately ("PERFORMING" → "PERFORMINGUSDT",
    "SUIUSDT" typed by the user → doubled to "SUIUSDTUSDT"). Fixed by
    matching only against symbols that actually exist in `TradeOutcome`/
    `LiveOpportunity` (cached 5 min) — a word that isn't a real tracked
    symbol is silently ignored instead of guessed at.
  - **Research system prompt**: explicitly forbids stating any number not
    present in the provided data block, requires repeating a report's own
    "sample size too small" note rather than drawing a conclusion anyway,
    and requires surfacing unflattering results (e.g. an unprofitable
    system) directly rather than softening them.
  - **Verified live** against the real dev DB (4 resolved trades): asked
    "How is the system performing overall — is it profitable?" and got
    back the real 25% win rate, 1.23 profit factor, 0.09 Sharpe, and an
    explicit caveat that a single trade (CYSUSDT +19.67%) is carrying the
    whole result — not a vague "looks okay." Asked "Should I retrain the
    ML model yet?" and got back the real retrain-recommendation refusal
    (4 resolved trades vs the 200 minimum) with no invented numbers.
  - **Deliberately deferred**: a frontend "AI Research Assistant" chat page
    — the backend endpoint (`POST /api/ask`) is what a future page would
    call; no UI built yet.
- **Retrain recommendation** (`app/engine/ml_retrain.py:retrain_recommendation`,
  `GET /api/ml/retrain-recommendation`): a reminder, not an action — never
  retrains anything itself. Fixed rule: never recommend before 200 total
  resolved `TradeOutcome` rows exist at all; after that, only once BOTH 50
  new resolutions have accumulated since the last train AND 30 days have
  passed since it ("whichever comes later" — neither a fast trickle of
  trades nor the calendar alone is enough alone). Reuses
  `ml_retrain.py`'s existing `metadata.json`, extended with a
  `trade_outcomes_resolved_at_train` snapshot written on every train so a
  later call can compute "how many new resolutions since we last checked."
  Honest limitation stated in its own docstring: this counts `TradeOutcome`
  resolutions as the "is there new signal" trigger, but `train_models()`
  itself still trains on backfilled `MarketSnapshot` candle history, not
  `TradeOutcome` rows directly — training ON the system's own live outcomes
  is a separate, larger project this function does not claim to do.
  **Verified live**: real dev DB currently has 4 resolved trades, correctly
  returns `{"recommend": false, "reason": "Only 4 resolved trades; need >=
  200..."}`.

## Roadmap — what's NOT implemented yet, and why

This follows a phased build rather than attempting everything at once:

- **Funding/OI as similarity dimensions** — historical similarity currently
  matches on technical indicators only (RSI/MACD/BB/ATR/ADX/StochRSI/OBV/
  CMF/MFI). Adding funding-rate history is straightforward (Binance's
  funding-rate history endpoint is free); open-interest history is not
  (Binance only retains ~30 days for free), so that dimension would need a
  different source or would stay indicator-only.
- **More chart overlays** — support/resistance (the swing-point data
  already exists in `smart_money.py`, just not surfaced on the chart yet),
  trendlines, liquidity zones, and volume profile are not built. Volume
  profile specifically needs tick/trade-level data to be honest, not just
  OHLCV — approximating it from candle volume would be a real accuracy
  compromise worth flagging if attempted.
- **AI Replay** (reconstruct what the AI would have recommended at a past
  candle, using only data available then) — not built. The pieces exist
  (historical snapshots already store the full indicator/structure state
  per past candle), but replaying it through Claude and presenting it as
  an interactive "click a candle" feature is new work.
- **Portfolio Mode** (multi-coin risk/correlation view, suggested
  rebalancing) — not built.
- **AI Journal UI** — the data side of this is now built (see
  "Closed-loop trade outcome tracking" above): every recommendation is
  logged with its full market state and real outcome, and
  `GET /api/digest/{daily,weekly,monthly}` already compute "trades with
  ADX>35 + neutral funding won 71%"-style aggregates. What's not built is a
  frontend page to view them, and a scheduler to generate/store a digest
  automatically at midnight rather than computing it on request.
- **A real worker queue (Celery/Redis).** The current single-process
  asyncio loop satisfies "always analyzed, not on-click" without extra
  infra, but doesn't horizontally scale past one process and doesn't
  survive a process restart mid-cycle gracefully. Worth adding once running
  more than one backend instance.
- **Full multi-exchange universe scanning** — what's built is a same-symbol
  cross-reference against Bybit + OKX (price/funding divergence, see above),
  not a second/third full universe scan on those exchanges. Hyperliquid,
  Coinbase, Kraken, Bitget are not integrated at all. Deliberately
  deprioritized: more exchanges scanned independently increases coverage,
  not signal quality, at real added LLM/API cost.
- **Multi-target ML, ranking instead of classifying, separate long/short
  models, regime-specific models** — all genuinely higher-value than the
  current single win/loss classifier, but all need volume of *resolved*
  TradeOutcome rows to retrain on meaningfully (the current XGBoost models
  were trained on backfilled candle history, not on this system's own
  calls). Gated on time passing and the closed loop above accumulating
  data, not on more engineering work right now.
- **Order flow** (order book depth, CVD, liquidation clusters) — needs
  websocket order-book state tracking, a distinct engineering effort.
- **On-chain data** (Glassnode/CryptoQuant/CoinMetrics-tier) — these are
  paid products. Not integrated; would need your own subscription and API
  key, same pattern as the Anthropic key.
- **X/Twitter sentiment** — X's API is paid and not planned. Free-tier
  sentiment (Fear & Greed, RSS news, Reddit) is built — see above.
- **RAG knowledge base** — will be built from free/public sources only
  (Binance Academy/Research, CME/Fed publications, arXiv/SSRN, your own
  notes). Will **not** ingest copyrighted trading books — that's a real
  copyright line, not a technical limitation.
- **`lightweight-charts` with AI-drawn overlays** (buy zone, stop, TPs,
  support/resistance, order blocks) and **personalization** (capital,
  risk %, spot-only) — designed for, not yet built.
- Trade execution of any kind. There is no exchange API key anywhere in
  this codebase, by design, and that won't change silently.

## Setup

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env   # then edit .env and set ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
copy .env.local.example .env.local   # defaults to http://localhost:8000, fine for local dev
npm run dev
```

Open http://localhost:3000. The frontend calls the backend directly using
`NEXT_PUBLIC_API_BASE_URL` (see `frontend/lib/api.ts`) — no proxy involved.

## Deploying

The frontend (Next.js) and backend (FastAPI) deploy separately.

### Backend → Render

Vercel is not a good fit for the backend: `/api/opportunities` makes several
parallel Claude calls and can take 30–60+ seconds, which exceeds or strains
Vercel's serverless function time limits. Render runs it as a normal
long-lived process instead.

1. Push this repo to GitHub.
2. In the [Render dashboard](https://dashboard.render.com), **New → Blueprint**,
   point it at the repo — it will pick up `render.yaml` at the repo root and
   create the `crypto-terminal-backend` web service automatically.
3. On the service's **Environment** tab, set:
   - `ANTHROPIC_API_KEY` — your key (never commit this)
   - `ALLOWED_ORIGINS` — leave blank for now; come back and set it to your
     Vercel URL once you have it (step 3 below), e.g.
     `https://crypto-terminal.vercel.app`
4. Deploy. Render gives you a URL like
   `https://crypto-terminal-backend.onrender.com` — copy it.

Note: on Render's free plan the service sleeps after ~15 minutes idle, so the
first request after a gap adds a ~30–50s cold start on top of normal latency.

Note on region — **found live, not theoretical, twice**: Binance's Futures
API (`fapi.binance.com`) returns HTTP 451 ("Unavailable For Legal Reasons")
for US-based IPs specifically (Binance.US is a separate entity that
doesn't offer futures). Render's default regions (Oregon/Virginia) are
both US and hit this on every scan cycle. Moving to `region: frankfurt`
fixed the 451 — but Frankfurt's *shared* outbound IP pool turned out to
already be banned by Binance with an HTTP 418 ("I'm a teapot," Binance's
specific code for an auto-banned IP) from OTHER Render tenants' traffic,
not ours — confirmed by the ban surviving a full service restart.
`render.yaml` now uses `region: singapore` as a different shared pool to
try; check `GET /api/health/exchanges` (see below) after deploying to see
current status without digging through logs. If Singapore is also banned,
a shared free-tier IP may not be viable long-term — Render's static
outbound IP add-on (paid) or a host with dedicated IPs (Fly.io, Railway)
sidesteps the whole class of problem, since the IP isn't shared with
whatever else is hammering Binance from that pool.

Note on storage: the backend defaults to a local SQLite file, which lives on
Render's ephemeral disk — a redeploy wipes backfilled history. Set
`DATABASE_URL` to a Postgres connection string (Render offers a free
Postgres instance) once you want backfilled history to persist.

### Frontend → Vercel

1. In the [Vercel dashboard](https://vercel.com/new), import the same GitHub
   repo, and set **Root Directory** to `frontend`.
2. Add an environment variable: `NEXT_PUBLIC_API_BASE_URL` = your Render
   backend URL from above (no trailing slash), e.g.
   `https://crypto-terminal-backend.onrender.com`.
3. Deploy. Copy the resulting Vercel URL.
4. Go back to Render and set `ALLOWED_ORIGINS` on the backend service to that
   Vercel URL, then redeploy the backend (Render → Manual Deploy) so CORS
   allows the frontend to call it.

## Important disclaimers

- Nothing in this app is financial advice. Trade plans are AI-generated
  estimates based on current market data and technical indicators — not
  predictions, and never guarantees.
- Cryptocurrency futures trading is high-risk and can result in the loss of
  more than your initial investment. Past patterns do not guarantee future
  outcomes.
- Before using this for real trading, get your own legal/compliance review —
  a tool that outputs specific entry/stop-loss/take-profit levels and ranks
  "best trades" can be viewed as investment advice in some jurisdictions
  depending on how it's distributed and marketed, regardless of disclaimer
  text.
- This app never stores or requests exchange API keys or trading credentials.
  Keep it that way unless you've deliberately decided to add execution and
  have thought through the security and liability implications.
