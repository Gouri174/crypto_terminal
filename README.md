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
- **Deterministic scoring model** (`app/engine/scoring.py`): a fixed,
  documented weighted formula (trend, momentum, volume, funding, structure,
  history match, risk penalty) — this is the confidence score. Claude
  explains it; it cannot change it.
- **AI reasoning**: Claude (`claude-opus-5`) receives the computed score
  breakdown and real historical-match stats and explains them — entry/stop/
  targets, reasons for/against, and an explicit invalidation point. Requests
  a JSON object directly in the prompt and parses it (rather than the
  Anthropic API's `output_format`/structured-outputs feature, which hit a
  "Grammar compilation timed out" error on this schema during testing).
- **Storage**: SQLAlchemy, SQLite by default (zero extra infra), swap to
  Postgres by setting `DATABASE_URL` — no code changes needed.
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
- **AI Journal** — the lifecycle engine already logs every WAIT→BUY→EXIT
  transition with a reason, which is the raw material for "trades with
  ADX>35 + neutral funding won 71%" style learning. Aggregating that into a
  journal with outcome statistics per condition is the next step, not yet
  built.
- **A real worker queue (Celery/Redis).** The current single-process
  asyncio loop satisfies "always analyzed, not on-click" without extra
  infra, but doesn't horizontally scale past one process and doesn't
  survive a process restart mid-cycle gracefully. Worth adding once running
  more than one backend instance.
- **More exchanges** (Bybit, OKX, Hyperliquid, Coinbase, Kraken, Bitget) —
  same pattern as Binance, additive, not yet built. Deliberately deprioritized
  below the items above — more exchanges increase coverage, not signal
  quality.
- **Order flow** (order book depth, CVD, liquidation clusters) — needs
  websocket order-book state tracking, a distinct engineering effort.
- **On-chain data** (Glassnode/CryptoQuant/CoinMetrics-tier) — these are
  paid products. Not integrated; would need your own subscription and API
  key, same pattern as the Anthropic key.
- **Macro/news/sentiment** — free sources (RSS, FRED, Fear & Greed, GitHub
  activity) are straightforward next additions; X/Twitter's API is paid and
  not planned.
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
