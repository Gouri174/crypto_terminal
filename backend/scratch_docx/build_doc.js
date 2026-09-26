const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, AlignmentType, LevelFormat, convertInchesToTwip,
} = require("docx");

const PAGE_WIDTH = 12240, PAGE_HEIGHT = 15840; // US Letter
const ACCENT = "9C6E2C";
const DIM = "595959";
const RULE = { top: { style: BorderStyle.SINGLE, size: 4, color: "D9D9D9" } };

function h1(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_1, spacing: { before: 400, after: 200 } });
}
function h2(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 300, after: 120 } });
}
function p(text, opts = {}) {
  return new Paragraph({ children: [new TextRun({ text, ...opts })], spacing: { after: 140 } });
}
function lede(text) {
  return new Paragraph({ children: [new TextRun({ text, color: DIM, italics: true })], spacing: { after: 200 } });
}
function bullet(text, boldPrefix) {
  const children = [];
  if (boldPrefix) children.push(new TextRun({ text: boldPrefix + " — ", bold: true }));
  children.push(new TextRun({ text }));
  return new Paragraph({ children, numbering: { reference: "bullets", level: 0 }, spacing: { after: 100 } });
}
function code(text) {
  return new Paragraph({
    children: [new TextRun({ text, font: "Consolas", size: 19 })],
    spacing: { after: 60 },
  });
}
function mono(text, extra = {}) {
  return new TextRun({ text, font: "Consolas", size: 18, ...extra });
}

function cell(children, opts = {}) {
  return new TableCell({
    children: Array.isArray(children) ? children : [new Paragraph({ children: [children] })],
    width: { size: opts.width || 2000, type: WidthType.DXA },
    shading: opts.shading ? { type: ShadingType.CLEAR, color: "auto", fill: opts.shading } : undefined,
    margins: { top: 80, bottom: 80, left: 100, right: 100 },
  });
}

function endpointTable(rows) {
  const colWidths = [2600, 6740];
  return new Table({
    width: { size: 9340, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: [
          cell([new Paragraph({ children: [new TextRun({ text: "Endpoint", bold: true, size: 18 })] })], { width: colWidths[0], shading: "EFE8D8" }),
          cell([new Paragraph({ children: [new TextRun({ text: "What it returns", bold: true, size: 18 })] })], { width: colWidths[1], shading: "EFE8D8" }),
        ],
      }),
      ...rows.map(([path, desc]) => new TableRow({
        children: [
          cell([new Paragraph({ children: [mono(path, { color: ACCENT })] })], { width: colWidths[0] }),
          cell([new Paragraph({ children: [new TextRun({ text: desc, size: 19 })] })], { width: colWidths[1] }),
        ],
      })),
    ],
  });
}

const doc = new Document({
  numbering: {
    config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 260 } } } }] }],
  },
  sections: [{
    properties: { page: { size: { width: PAGE_WIDTH, height: PAGE_HEIGHT }, margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } } },
    children: [

      new Paragraph({ children: [new TextRun({ text: "KARMA ARCHIVE — BACKEND REFERENCE", bold: true, size: 20, color: ACCENT, characterSpacing: 20 })], spacing: { after: 80 } }),
      new Paragraph({ children: [new TextRun({ text: "Analytics, explainability & trade-management layer", size: 44, bold: true })], spacing: { after: 160 } }),
      new Paragraph({
        children: [new TextRun({
          text: "A crypto trading analysis platform built from 0 → 90+ resolved live trades: a deterministic scoring/decision engine, Claude-generated trade plans, and — this document's focus — the read-only analytics layer built on top of it across four release rounds (V2.1 → V3.2).",
          color: DIM, size: 21,
        })],
        spacing: { after: 240 },
      }),
      new Table({
        width: { size: 9340, type: WidthType.DXA },
        columnWidths: [2335, 2335, 2335, 2335],
        rows: [
          new TableRow({ children: [
            cell([new Paragraph({ children: [new TextRun({ text: "Repo", bold: true, size: 16, color: DIM })] })], { width: 2335, shading: "F5F1E8" }),
            cell([new Paragraph({ children: [mono("crypto-terminal/backend")] })], { width: 2335 }),
            cell([new Paragraph({ children: [new TextRun({ text: "Commits", bold: true, size: 16, color: DIM })] })], { width: 2335, shading: "F5F1E8" }),
            cell([new Paragraph({ children: [mono("10 (c511b3e→ffb009d)")] })], { width: 2335 }),
          ]}),
          new TableRow({ children: [
            cell([new Paragraph({ children: [new TextRun({ text: "Routes", bold: true, size: 16, color: DIM })] })], { width: 2335, shading: "F5F1E8" }),
            cell([new Paragraph({ children: [mono("30 documented below")] })], { width: 2335 }),
            cell([new Paragraph({ children: [new TextRun({ text: "Status", bold: true, size: 16, color: DIM })] })], { width: 2335, shading: "F5F1E8" }),
            cell([new Paragraph({ children: [mono("pushed to origin/master")] })], { width: 2335 }),
          ]}),
        ],
      }),

      new Paragraph({ text: "", spacing: { after: 200 } }),
      h1("1. Architecture & Constraints"),
      lede("Every module in this document is additive: it reads already-stored data and computes statistics, suggestions, or narrative — nothing here changes which trades get taken, how they're scored, or what Claude is asked to decide."),

      h2("The hard freeze"),
      p("These files decide trades and were untouched by everything in this document — verified with git diff --stat before every commit:"),
      new Paragraph({ children: [mono("scoring.py")], spacing: { after: 40 } }),
      new Paragraph({ children: [mono("decision.py")], spacing: { after: 40 } }),
      new Paragraph({ children: [mono("market_regime.py")], spacing: { after: 40 } }),
      new Paragraph({ children: [mono("reasoning.py"), new TextRun({ text: "  (the Claude prompt)" })], spacing: { after: 40 } }),
      new Paragraph({ children: [mono("ml_model.py"), new TextRun({ text: "  (weights / training)" })], spacing: { after: 40 } }),
      new Paragraph({ children: [mono("confidence.py")], spacing: { after: 40 } }),
      new Paragraph({ children: [mono("entry_quality.py")], spacing: { after: 40 } }),
      new Paragraph({ children: [mono("lifecycle.py")], spacing: { after: 40 } }),
      new Paragraph({ children: [mono("background_scanner.py")], spacing: { after: 160 } }),
      p("One exception exists in the record, on the record: a commit briefly changed scoring.py's momentum/volume/structure weights from odds-ratio evidence, then reverted them in the very next commit — measurement and implementation had been folded into one pass without a separate sign-off step in between. Both the change and the revert are in the git history (901580f → d44bd96)."),

      h2("What's new instead"),
      p("A new app/analytics/ package (12 modules) plus extensions to app/engine/performance_center.py — Expected Value, Trade Manager probabilities, Confidence Calibration, Red Flags, Failure Patterns, Symbol Reliability, Trade Quality, Karma Explain, Decision Audit, Strategy Attribution, Trade Truth verdicts, Prediction Version Metadata, Market Health, Portfolio Exposure, Daily Scorecards, a Missed-Opportunity recorder, Trade Journal, and a Calibration Dashboard."),
      p("No ML retraining, no automated weight optimizer, no coin-specific models — deferred until the resolved-trade count clears the thresholds each report states, not tuned on the current sample."),

      h1("2. API Reference"),
      lede("All under /api/performance/* unless noted. Full interactive docs (try each call against live data): /docs on the running server."),

      h2("Core performance analytics"),
      endpointTable([
        ["GET /scanner-health", "Heartbeat timeline, outage detection, uptime %. Surfaced two real multi-day monitoring gaps that explained the worst historical stop-slippage losses."],
        ["GET /stop-execution", "Slippage distribution by direction, symbol, ATR-volatility bucket, and during-outage vs. normal uptime."],
        ["GET /tp-continuation", "P(TP2|TP1), P(TP3|TP2), return-to-entry / return-to-stop probabilities from real snapshot price paths."],
        ["GET /confidence-lab", "Confidence-bucket win rates, Brier score, Expected Calibration Error."],
        ["GET /coin-leaderboard", "Per-symbol profit factor / win rate / return / MFE-MAE, gated behind a minimum sample."],
        ["GET /trade-replay/{id}", "Full per-trade payload: entry indicators, Claude's reasoning, snapshot timeline, TP/SL events, exit reason, plus a plain-English narrative and forensic pattern match."],
        ["GET /trade-manager", "Every open trade's distance-to-target, confidence/structure/regime drift since entry, and a Hold / Move-Stop / Exit suggestion with conditional_triggers."],
      ]),

      h2("Expected value & risk"),
      endpointTable([
        ["GET /calibration-table", "Predicted vs. observed win rate per confidence bucket with a 95% Wilson confidence interval."],
        ["GET /ev-leaderboard", "Ranks resolved trades by stored expected_r against what actually happened; reports corr(score, expected_r)."],
        ["GET /red-flag-leaderboard", "Win rate / return by red-flag count (0–3): RSI chop-zone, weak structure, no historical analogue."],
        ["GET /feature-importance", "Existing per-component win-rate lift report, exposed here alongside the rest."],
        ["GET /position-size", "Pure arithmetic — capital / risk % / stop distance → position size and max dollar loss. Never places an order."],
      ]),

      h2("Pattern & reliability"),
      endpointTable([
        ["GET /failure-patterns", "Every resolved loss classified into a lifecycle pattern plus risk tags — only patterns with real occurrences are ever reported."],
        ["GET /coin-reliability", "Bayesian-shrunk (Beta-Binomial) per-symbol reliability score — a 100%-on-2-trades symbol shrinks toward the pooled rate instead of looking falsely excellent."],
      ]),

      h2("Trade intelligence & explainability"),
      endpointTable([
        ["GET /trade-quality/{id}", "0–100 composite: 30% entry quality + 20% EV + 15% reliability + 15% calibration + 10% structure + 10% (inverted red flags). Fixed formula, not ML-tuned."],
        ["GET /confidence-display", "“71 raw / 58 calibrated ±10%, n=22” — reliability-adjusted confidence with real uncertainty."],
        ["GET /explain/{id}", "Karma Explain — bullish/risk evidence, historical similarity, reliability, EV, and (for open trades) an action plan. Pure synthesis, nothing new computed."],
        ["GET /decision-audit", "accepted_because / rejected_checks / warnings per trade — reruns decision.py's own unmodified checklist against stored score breakdowns."],
        ["GET /strategy-attribution", "Classifies every trade into one strategy family (FVG continuation, breakout chase, mean reversion, EMA pullback, …) from already-stored fields."],
      ]),

      h2("Trading operating system (V3.2)"),
      endpointTable([
        ["GET /trade-truth, /trade-truth/{id}", "Trade Truth Engine — forensic verdicts beyond win/loss: perfect_trade, good_entry_bad_exit, bad_structure_call, infrastructure_failure, near_miss_early_stop, and more."],
        ["GET /prediction-versions", "Win rate / PF grouped by prediction_version — the “did V4 outperform V3” question, ready once a version actually changes."],
        ["GET /market-health", "0–100 “is today worth trading” score from regime, breadth, Fear & Greed, and today's scan breakdown."],
        ["GET /portfolio-exposure", "Long/short balance, symbol-family concentration, and a suggested max additional trades — across currently open positions only."],
        ["GET /daily-scorecard/morning", "Market health + 24h scanner funnel + portfolio health + top EV opportunities, assembled into one morning brief."],
        ["GET /daily-scorecard/evening", "Today's performance digest, truth-verdict breakdown, best/worst strategy."],
        ["GET /missed-opportunity-status, -breakdown", "Recorder progress for rejected candidates' directional outcome — refuses to report a rate below 500 resolved rows."],
        ["GET /trade-journal/{id}", "Strengths / mistakes / repeated pattern / analogue / recommendation — a journal entry synthesized from Karma Explain + Trade Truth."],
        ["GET /calibration-dashboard", "Confidence curve + Brier/ECE + TP-continuation calibration + EV calibration, in one payload."],
      ]),

      h1("3. Known Limitations — Disclosed, Not Hidden"),
      lede("Every proxy below exists because the real data doesn't: this project's own standing rule is to report “unavailable” rather than fabricate a plausible-looking number."),
      bullet("is a symbol-family concentration proxy, not a computed price correlation — only 6 symbols in the database have any OHLCV history at all.", "BTC correlation"),
      bullet("(Market Health components) are proxied via the average risk-penalty score and reported as unavailable, respectively — no aggregate ATR-percentile or pooled news-stress metric exists in this codebase yet.", "Volatility Quality & News Stress"),
      bullet("exists in the Trade Truth taxonomy but structurally can't be assigned — entry_quality=\"late\" blocks a new trade from ever being created in the first place.", "late_entry"),
      bullet("replaces a literal “stopped, then price hit TP1 anyway” verdict, which isn't observable — this app stops tracking price the moment a trade closes. The verdict instead reports how close price got (≥80% of the distance to TP1) before reversing.", "near_miss_early_stop"),
      bullet("doesn't exist anywhere in this codebase — only swing points, BOS, CHoCH, and FVG. Strategy Attribution and Decision Audit report this honestly rather than inferring a false match.", "Order-block detection"),
      bullet("tracks directional price movement only, never a literal TP1/TP2/TP3 outcome — a rejected candidate never received Claude-generated levels to grade against.", "Missed Opportunity"),

      h1("4. Build History"),
      lede("10 commits, each independently tested and verified against the frozen-file list before merging."),
      new Table({
        width: { size: 9340, type: WidthType.DXA },
        columnWidths: [1600, 7740],
        rows: [
          new TableRow({ tableHeader: true, children: [
            cell([new Paragraph({ children: [new TextRun({ text: "Commit", bold: true, size: 18 })] })], { width: 1600, shading: "EFE8D8" }),
            cell([new Paragraph({ children: [new TextRun({ text: "What shipped", bold: true, size: 18 })] })], { width: 7740, shading: "EFE8D8" }),
          ]}),
          ...[
            ["c511b3e", "V2.1-A — Expected Value engine (frequency tables, not a trained model)"],
            ["6bdfc1f", "V2.1-B — TP Continuation Engine / Trade Manager"],
            ["901580f", "V2.1-C — Score weight recalibration + Red Flag engine"],
            ["17b61ff", "V2.1-D — Confidence calibration"],
            ["e833491", "V2.1-E — Analytics dashboard additions"],
            ["d44bd96", "Reverted V2.1-C's scoring.py weights; replaced with a measurement-only report"],
            ["42c948d", "V3.0 — Failure Pattern Engine, Symbol Reliability, Position Sizing"],
            ["fa1d4e2", "V3.1 — Trade Quality Score, Karma Explain, Decision Audit, Strategy Attribution"],
            ["f96e47a", "V3.1 — Missed Opportunity recorder (recording only)"],
            ["ffb009d", "V3.2 — Trade Truth, Prediction Metadata, Market Health, Portfolio Exposure, Daily Scorecard, Journal, Calibration Dashboard"],
          ].map(([sha, msg]) => new TableRow({ children: [
            cell([new Paragraph({ children: [mono(sha, { color: ACCENT })] })], { width: 1600 }),
            cell([new Paragraph({ children: [new TextRun({ text: msg, size: 19 })] })], { width: 7740 }),
          ]})),
        ],
      }),
      new Paragraph({ text: "", spacing: { after: 160 } }),
      p("Test coverage: 15 manual verification scripts (no pytest infra in this project) run against the real dev database using clearly-fake symbols, cleaning up after themselves. All passing as of the last commit."),

      h1("5. Running It Locally"),
      code("Backend:"),
      code("  cd backend"),
      code("  .venv\\Scripts\\Activate.ps1"),
      code("  uvicorn app.main:app --reload --port 8000"),
      new Paragraph({ text: "", spacing: { after: 100 } }),
      code("Frontend:"),
      code("  cd frontend"),
      code("  npm run dev"),
      new Paragraph({ text: "", spacing: { after: 100 } }),
      code("Interactive API docs:  http://localhost:8000/docs"),
      code("App:                   http://localhost:3000"),

      new Paragraph({ text: "", spacing: { before: 400 } }),
      new Paragraph({
        border: { top: { style: BorderStyle.SINGLE, size: 6, color: "D9D9D9", space: 8 } },
        children: [new TextRun({ text: "Karma Archive — backend reference · generated from the live codebase and commit history · crypto-terminal/backend", size: 16, color: DIM })],
      }),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  require("fs").writeFileSync("Karma_Archive_Backend_Reference.docx", buf);
  console.log("wrote Karma_Archive_Backend_Reference.docx");
});
