# Crypto AI Terminal

AI-ranked crypto trade setups: scans Binance USDT-perpetual futures, computes
technical indicators, and uses Claude to produce a trade plan (entry, stop
loss, take-profit levels, confidence, reasoning) for the strongest setups.

**This is analysis only.** It does not hold exchange API keys, does not place
trades, and every output is explicitly framed as a probabilistic estimate,
never a guarantee. See [Important disclaimers](#important-disclaimers) below
before using this for real trading decisions.

## What's implemented

- **Data**: Binance Futures public REST API (klines, funding rate, open
  interest, long/short ratio) — no exchange API key needed, read-only public
  endpoints.
- **Indicators**: EMA(20/50/200), RSI, MACD, Bollinger Bands, ATR, ADX,
  Stochastic RSI, OBV, computed across 1h/4h/1d timeframes via the `ta`
  library.
- **Scoring**: a deterministic pre-filter (`app/engine/scorer.py`) ranks the
  ~40 highest-volume USDT pairs before spending any LLM calls, so only the
  top few candidates per request go to Claude.
- **AI reasoning**: Claude (`claude-opus-5`) turns the computed features into
  a structured trade plan — recommendation, confidence, entry/stop/targets,
  risk level, reasons for/against, and a plain-English summary. Requests a
  JSON object directly in the prompt and parses it (rather than the
  Anthropic API's `output_format`/structured-outputs feature, which hit a
  "Grammar compilation timed out" error on this schema during testing).
- **Frontend**: Next.js dashboard showing ranked opportunity cards, plus a
  per-coin detail page.

## What's NOT implemented (out of scope for this first version)

- Other exchanges (Bybit, OKX, Coinbase, Hyperliquid) — only Binance Futures.
- On-chain data (whale wallets, exchange flows), news/social sentiment, and a
  real historical-pattern-matching vector database. The AI is told explicitly
  not to invent numbers for these and to speak qualitatively when asked.
- Trade execution of any kind. There is no exchange API key anywhere in this
  codebase, by design.
- Auth, persistence/database, alerts, portfolio tracking.

These are natural next additions — the `data_sources/` and `engine/` modules
are structured so a new provider is one new file plus a line in
`feature_builder.py`.

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
