# Karma Archive — Quantitative Audit (Sections A–Z)

Generated 2026-09-26 14:33 UTC directly from `crypto_terminal.db` (read-only). Live DB counts: 982 plans, 118 resolved, 26509 PredictionSnapshots, 81540 ScanSnapshots. The DB grows while the scanner runs, so counts are slightly above the round numbers in the brief.

**Evidence labels:** CONFIRMED (p<0.01, n≥30) · LIKELY (p<0.05) · POSSIBLE (p<0.15) · INSUFFICIENT DATA (n<10 or field not stored) · a hypothesis with p≥0.15 at adequate n is stated as **NOT SUPPORTED** (I say 'false' only where the data affirmatively contradicts it). Fisher exact tests on win/loss; p-values are optimistic because trades are clustered. Where the brief names tables that do not exist as tables (PredictionMetadata, PredictionVersion, CoinHistory, HistoricalSimilarity, ExpectedValue, EntryQuality, RedFlags, Reliability, FailurePatterns, DecisionAudit), they are columns of `trade_outcomes` or computed by `app/analytics/*`; nothing was skipped. Tables in the DB: live_opportunities, market_regime_state, market_snapshots (25,080 rows, 6 symbols, ends 2026-08-04, i.e. before the first trade), ohlcv_candles (6 symbols), prediction_snapshots, rejected_opportunity_outcomes (0 rows), scan_snapshots, trade_outcomes.

**Discrepancies with earlier reports (data wins):** the entry-quality 'excellent' effect I previously called validated is NOT significant on the full sample (§E); the short-selling collapse is largely an outage artefact (§K/§U).

## SECTION A — EXECUTIVE SUMMARY

| Metric | Value |
|---|---|
| Total prediction plans | 982 |
| Entered trades (closed + open) | 142 |
| Closed (resolved) trades | 118 |
| Wins / Losses | 46 / 72 |
| TP1 / TP2 / TP3 hits (among closed) | 54 / 47 / 14 |
| Stop-loss exits | 72 |
| Expired (never entered, `closed_stale`) | 7 |
| Invalidated (superseded) | 774 |
| Open | 24 |
| Pending | 11 |
| Avoid-grade (`rejected_avoid`) | 48 |

| Overall (closed trades) | Value |
|---|---|
| Win rate | 39.0% (95% CI 30.7–48.0%) |
| Profit factor | 1.62 |
| Average return | 2.38% |
| Median return | -1.59% |
| Sharpe (per-trade mean/σ, not annualised) | 0.137 |
| Max drawdown (summed-return curve, no sizing/compounding) | -100.5% |
| Average hold | 82.3 h (median 28.7 h) |
| Best trade | NEARUSDT 114.28% |
| Worst trade | BICOUSDT -44.42% |

| Scenario | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | Sum ret% |
|---|---|---|---|---|---|---|---|
| All trades | 118 | 39.0% | 30.7–48.0 | 2.38 | -1.59 | 1.62 | 280.8 |
| Without top winner | 117 | 38.5% | 30.1–47.5 | 1.42 | -1.61 | 1.37 | 166.5 |
| Without top 3 winners | 115 | 37.4% | 29.1–46.5 | 0.60 | -1.64 | 1.15 | 68.9 |
| Without top 5 winners | 113 | 36.3% | 28.0–45.5 | -0.09 | -1.77 | 0.98 | -10.3 |

**Is Karma Archive profitable? MARGINAL / fragile — the point estimate is positive, but the bootstrap CI of mean return includes zero and PF is below 1 once the top 5 winners are removed (POSSIBLE positive expectancy, not CONFIRMED).** PF 1.62 → 1.15 without the top 3 → 0.98 without the top 5; the median trade is -1.59%. Winners are few and large (top-3 = NEARUSDT +114.3%, UNIUSDT +52.2%, ZECUSDT +45.4%). Bootstrap check below.
Bootstrap 95% CI of the mean return: [-0.47%, 5.74%] (n=118) — INCLUDES zero. Evidence: POSSIBLE (cannot rule out zero expectancy). Note the ‘published/active’ forward returns in §T are survivorship-biased (a row only has +72h data if its trade stayed tracked that long).

## SECTION B — COMPLETE CLOSED TRADE LEDGER

All 118 closed trades (newest first); also saved to `karma_AZ_ledger.csv`. Notes: 'EV' exists only for post-2026-09-12 trades; ML probability exists for a small subset; Reliability* is hindsight (all-data Bayesian). **'Why won/lost' is not stored as a post-mortem** — the last column is the entry thesis from `reasoning` (first 130 chars) plus the computed lifecycle/Trade-Truth verdict; it explains what Claude said at entry, not a causal explanation of the outcome.

| Symbol | Dir | Entry | Exit | Entered | Exited | Hold h | Conf | Grade | EQ | Regime | Trend | Mom | Vol | Struct | Hist | ML prob | EV(R) | Rel* | TP reached | Stop? | Ret% | MFE% | MAE% | Failure pattern | Red flags | Entry thesis / verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ADAUSDT | long | 0.25145 | 0.2639 | 2026-09-25 21:22 | 2026-09-26 01:47 | 4.4 | 62 | B | neutral | risk_on | 23.0 | 15.0 | 10.0 | 6.0 | -1.5 | 0.48 | -0.70 | 44.5 | TP2 | no | 4.95 | 4.95 | 0.54 | closed_at_tp2+weak_structure | weak_structure | [perfect_trade] ADA is a B-grade, 62-confidence long with clean multi-timeframe trend alignment and strong momentum, but structure hasn't freshly  |
| SPCXUSDT | long | 150.075 | 148.55 | 2026-09-14 19:07 | 2026-09-25 20:45 | 265.6 | 70 | B+ | excellent | risk_on | 19.3 | 15.0 | 10.0 | 11.0 | 0.0 | — | 0.29 | 35.0 | none | yes | -1.02 | 0.13 | -1.02 | immediate_reversal+no_historical_analogue,scanner_outage_corrupted | no_history | [infrastructure_failure] SPCXUSDT is a B+ graded long with all three timeframes aligned bullish, strong momentum, and fresh 4h FVG structure, rated 'excell |
| BNBUSDT | long | 725.55 | 776.17 | 2026-09-14 19:07 | 2026-09-25 20:45 | 265.6 | 65 | B+ | neutral | risk_on | 18.7 | 15.0 | 10.0 | 6.0 | 1.5 | 0.48 | -0.82 | 37.7 | TP2 | no | 6.98 | 6.98 | 0.07 | closed_at_tp2+weak_structure,scanner_outage_corrupted | weak_structure | [infrastructure_failure] BNBUSDT is a B+ graded long on trend/momentum alignment across 1h and 1d, but 4h structure is actually bearish and unconfirmed, la |
| UNIUSDT | long | 6.36 | 9.679 | 2026-09-14 17:06 | 2026-09-25 20:45 | 267.7 | 64 | B | neutral | mixed | 20.0 | 15.0 | 10.0 | 6.0 | 0.0 | — | 0.15 | 44.5 | TP2 | no | 52.19 | 52.19 | 0.55 | closed_at_tp2+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | [infrastructure_failure] UNIUSDT is a moderate-confidence (64, grade B) long on the back of strong daily trend strength and multi-timeframe alignment, but  |
| ZECUSDT | long | 1130 | 1549.03 | 2026-09-14 16:32 | 2026-09-25 20:45 | 268.2 | 59 | B | neutral | mixed | 18.4 | 15.0 | 7.0 | 6.0 | 0.0 | — | 0.26 | 42.1 | TP3 | no | 37.08 | 37.08 | 0.36 | ran_to_tp3+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,negative_cmf | [infrastructure_failure] ZEC is a B-grade long built on a strong daily uptrend (ADX 53) and confirming lower-timeframe momentum, but structure_confirms fai |
| HYPEUSDT | long | 79.8 | 91.923 | 2026-09-14 15:57 | 2026-09-25 20:45 | 268.8 | 59 | B | neutral | mixed | 15.1 | 15.0 | 10.0 | 6.0 | 0.0 | — | -0.33 | 42.1 | TP2 | no | 15.19 | 15.19 | -0.13 | closed_at_tp2+rsi_chop_zone,weak_structure,no_historical_analogue,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history | [infrastructure_failure] HYPEUSDT is a grade-B long, but the 4h timeframe is bearish while 1h and 1d lean bullish, a real conflict the structure checklist  |
| BZUSDT | long | 102.25 | 97.46 | 2026-09-14 15:57 | 2026-09-25 20:45 | 268.8 | 54 | C | neutral | mixed | 23.7 | 15.0 | 10.0 | 6.0 | 0.0 | — | -0.22 | 32.5 | none | yes | -4.68 | 0.37 | -4.68 | immediate_reversal+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,funding_elevated | [infrastructure_failure] BZUSDT is a lower-conviction grade-C long: daily/4h trend is up, but funding is sharply negative with short-heavy positioning (a p |
| NEARUSDT | long | 2.3875 | 5.116 | 2026-09-14 15:57 | 2026-09-25 20:45 | 268.8 | 57 | B | neutral | mixed | 21.6 | 15.0 | 2.0 | 6.0 | 0.0 | — | -0.27 | 49.2 | TP2 | no | 114.28 | 114.28 | 0.40 | closed_at_tp2+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,negative_cmf | [infrastructure_failure] NEARUSDT is a grade-B long with full EMA alignment and strong daily ADX, but the volume checklist fails outright — OBV is declinin |
| SUIUSDT | short | 0.725 | 0.7319 | 2026-09-14 15:50 | 2026-09-14 16:48 | 1.0 | 61 | B | neutral | mixed | 17.7 | 15.0 | 10.0 | 6.0 | 0.0 | — | -1.00 | 32.5 | none | yes | -0.95 | 0.18 | -0.95 | immediate_reversal+rsi_chop_zone,weak_structure,no_historical_analogue,short_direction | rsi_chop_30_49,weak_structure,no_history,risk_penalty_applied | [bad_structure_call] SUIUSDT short is a B-grade, 61-confidence setup built on bearish 4h/1d trend and maxed momentum, but structure hasn't confirmed (n |
| XRPUSDT | long | 1.392 | 1.4561 | 2026-09-14 14:57 | 2026-09-14 18:32 | 3.6 | 63 | B | neutral | mixed | 18.9 | 15.0 | 10.0 | 6.0 | 1.5 | 0.47 | -0.34 | 44.5 | TP2 | no | 4.61 | 4.61 | 0.37 | closed_at_tp2+weak_structure | weak_structure | [perfect_trade] XRP is a B-grade long: all timeframes trend up and momentum is maxed out, but there's no fresh 4h structural trigger and the ML mo |
| SOLUSDT | long | 101.25 | 122.51 | 2026-09-14 14:57 | 2026-09-25 20:45 | 269.8 | 57 | B | neutral | mixed | 13.9 | 15.0 | 7.0 | 6.0 | 3.0 | 0.57 | -0.25 | 32.7 | TP2 | no | 21.00 | 21.00 | 0.25 | closed_at_tp2+weak_structure,scanner_outage_corrupted | weak_structure,negative_cmf | [infrastructure_failure] SOL is a lower-conviction B-grade long: the daily uptrend and momentum are intact, but 1h/4h structure currently disagrees, so tre |
| 1000PEPEUSDT | long | 0.0033925 | 0.0044924 | 2026-09-13 11:06 | 2026-09-25 20:45 | 297.7 | 56 | B | neutral | mixed | 15.3 | 15.0 | 7.0 | 6.0 | 0.0 | — | -0.21 | 40.8 | TP2 | no | 32.42 | 32.42 | -1.42 | closed_at_tp2+rsi_chop_zone,weak_structure,no_historical_analogue,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history,negative_cmf | [infrastructure_failure] 1000PEPEUSDT long is a moderate-confidence (56, grade B) momentum play with maxed-out momentum scoring but unconfirmed structure a |
| CLUSDT | long | 96.35 | 92.44 | 2026-09-13 11:00 | 2026-09-25 20:45 | 297.8 | 63 | B | neutral | mixed | 21.2 | 8.0 | 8.0 | 6.0 | 0.0 | — | 0.91 | 42.1 | none | yes | -4.06 | 4.24 | -4.06 | some_favorable_move_then_stopped+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | [infrastructure_failure] This is a B-grade long (63% confidence) on CLUSDT, backed by full trend alignment across 1h/4h/1d and strong 1d ADX, though struct |
| FLOCKUSDT | long | 0.07915 | 0.07489 | 2026-09-13 14:00 | 2026-09-13 17:49 | 3.8 | 60 | B | neutral | mixed | 25.0 | 11.0 | 7.0 | 6.0 | 0.0 | — | 0.02 | 35.4 | none | yes | -5.38 | 2.73 | -5.38 | some_favorable_move_then_stopped+weak_structure,no_historical_analogue | weak_structure,no_history,negative_cmf,risk_penalty_applied | [bad_structure_call] FLOCKUSDT is a B-grade long with strong, well-aligned trend and momentum across all three timeframes, but lacks fresh structural c |
| PUMPUSDT | short | 0.003731 | 0.0046 | 2026-09-13 10:19 | 2026-09-26 07:22 | 309.1 | 60 | B | excellent | mixed | 14.9 | 15.0 | 7.0 | 11.0 | 0.0 | — | 0.10 | 37.7 | TP1 | yes | -23.29 | 6.97 | -23.29 | reached_tp1_then_stopped+rsi_chop_zone,no_historical_analogue,short_direction | rsi_chop_30_49,no_history,negative_cmf | [good_entry_bad_exit] PUMPUSDT is a grade-B short at 60% confidence with an 'excellent' entry quality — fresh 4h bearish structure (FVG + BOS-aligned tr |
| DOGEUSDT | short | 0.084945 | 0.09837 | 2026-09-14 09:53 | 2026-09-25 20:45 | 274.9 | 59 | B | neutral | mixed | 14.9 | 15.0 | 10.0 | 6.0 | 0.0 | — | -1.00 | 30.0 | TP1 | yes | -15.80 | 2.10 | -15.80 | reached_tp1_then_stopped+rsi_chop_zone,weak_structure,no_historical_analogue,short_direction,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history | [infrastructure_failure] DOGEUSDT short is graded B at 59% confidence, but two checklist items — trend_confirms and structure_confirms — are both false, me |
| XAUUSDT | short | 4359.75 | 4292.87 | 2026-09-13 04:49 | 2026-09-14 09:25 | 28.6 | 55 | B | good | mixed | 19.5 | 15.0 | 5.0 | 11.0 | 0.0 | — | -0.31 | 40.8 | TP2 | no | 1.53 | 1.53 | -0.03 | closed_at_tp2+rsi_chop_zone,no_historical_analogue,short_direction | rsi_chop_30_49,no_history,negative_cmf,mfi_over_80 | [perfect_trade] XAUUSDT short is grade B at 55% confidence, backed by full bearish trend agreement across 1h/4h/1d but weakened by extremely crowd |
| USELESSUSDT | long | 0.2343 | 0.22327 | 2026-09-13 03:48 | 2026-09-13 07:16 | 3.5 | 58 | B | neutral | mixed | 19.5 | 15.0 | 10.0 | 6.0 | 0.0 | — | 0.20 | 35.4 | none | yes | -4.71 | -0.01 | -4.71 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history,risk_penalty_applied | [bad_structure_call] USELESSUSDT is a trend-following long: all timeframes agree bullish and momentum/volume support it, but the entry lacks fresh 4h s |
| PUMPUSDT | long | 0.003775 | 0.003694 | 2026-09-13 03:18 | 2026-09-13 08:33 | 5.3 | 56 | B | neutral | mixed | 15.3 | 15.0 | 7.0 | 6.0 | 0.0 | — | 0.72 | 37.7 | none | yes | -2.15 | 1.80 | -2.15 | some_favorable_move_then_stopped+rsi_chop_zone,weak_structure,no_historical_analogue | rsi_chop_30_49,weak_structure,no_history,negative_cmf | [bad_structure_call] PUMPUSDT is a grade-B long driven mainly by 1h bullish momentum, but both 4h and 1d structure remain bearish and 4h/1d volume flow |
| ETHUSDT | long | 2518.8 | 2482.04 | 2026-09-13 02:48 | 2026-09-13 09:31 | 6.7 | 55 | B | neutral | mixed | 22.1 | 15.0 | 5.0 | 6.0 | -3.0 | 0.55 | 0.13 | 26.0 | none | yes | -1.46 | 0.15 | -1.46 | immediate_reversal+weak_structure | weak_structure | [bad_structure_call] ETH's long setup rests on solid daily/4h trend and momentum (ADX 51.4, price above key EMAs) but lacks fresh structural confirmati |
| XAGUSDT | short | 64.6 | 62.71 | 2026-09-13 00:30 | 2026-09-14 09:19 | 32.8 | 51 | C | excellent | mixed | 18.2 | 15.0 | 2.0 | 11.0 | 0.0 | — | 1.86 | 37.7 | TP2 | no | 2.93 | 2.93 | -0.01 | closed_at_tp2+rsi_chop_zone,no_historical_analogue,short_direction | rsi_chop_30_49,no_history,negative_cmf | [perfect_trade] Lower-conviction short (grade C, confidence 51) despite an 'excellent' entry-quality read — 4h/1d trend and a fresh 4h FVG support |
| WLDUSDT | short | 0.40625 | 0.4826 | 2026-09-12 16:14 | 2026-09-25 20:45 | 316.5 | 61 | B | good | mixed | 15.2 | 15.0 | 7.0 | 11.0 | 0.0 | — | -0.41 | 40.8 | TP2 | yes | -18.79 | 4.89 | -18.79 | hit_tp2_then_reversed+rsi_chop_zone,no_historical_analogue,short_direction,scanner_outage_corrupted | rsi_chop_30_49,no_history,negative_cmf | [infrastructure_failure] This is a B-grade, 61-confidence short on WLD based on 1h/4h bearish momentum divergence against a still-bullish daily trend, ente |
| LABUSDT | long | 0.073 | 0.06763 | 2026-09-12 15:50 | 2026-09-12 15:56 | 0.1 | 48 | C | neutral | mixed | 20.0 | 15.0 | 7.0 | 6.0 | 0.0 | — | -0.09 | 35.4 | none | yes | -7.36 | 0.62 | -7.36 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history,negative_cmf,risk_penalty_applied | [bad_structure_call] Momentum and volume favor the long on 1h/4h, but the 1d timeframe is bearish (price far below 1d EMA20/50/200) and structure hasn' |
| SKHYUSDT | long | 190.2 | 184.64 | 2026-09-12 15:39 | 2026-09-13 08:28 | 16.8 | 68 | B+ | neutral | mixed | 24.6 | 8.0 | 10.0 | 6.0 | 0.0 | — | 0.11 | 42.1 | none | yes | -2.92 | 0.15 | -2.92 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | [bad_structure_call] This is a B+ graded long on daily/4h EMA trend alignment and positive volume flow, but the 4h structure label itself reads bearish |
| SKHYNIXUSDT | long | 1365.25 | 1334.08 | 2026-09-12 15:27 | 2026-09-12 19:38 | 4.2 | 66 | B+ | neutral | mixed | 22.7 | 8.0 | 10.0 | 6.0 | 0.0 | — | 0.87 | 37.7 | none | yes | -2.28 | 0.25 | -2.28 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | [bad_structure_call] SKHYNIXUSDT gets a B+ grade on strong multi-timeframe trend alignment and healthy volume/funding conditions, but lacks a fresh str |
| CRCLUSDT | short | 91.75 | 92.66 | 2026-09-12 14:29 | 2026-09-14 12:34 | 46.1 | 54 | C | good | mixed | 16.2 | 15.0 | 7.0 | 11.0 | 0.0 | — | -0.30 | 45.4 | TP1 | yes | -0.99 | 1.50 | -0.99 | reached_tp1_then_stopped+rsi_chop_zone,no_historical_analogue,short_direction | rsi_chop_30_49,no_history,negative_cmf | [good_entry_bad_exit] C-grade short on 4h downtrend with 1h price stalling near resistance, but history is unproven and structure isn't freshly confirmi |
| RIVERUSDT | long | 1.27 | 1.509 | 2026-09-12 13:19 | 2026-09-12 18:34 | 5.2 | 50 | C | neutral | mixed | 19.5 | 15.0 | 10.0 | 6.0 | 0.0 | — | 0.28 | 44.5 | TP2 | no | 18.82 | 18.82 | -0.71 | closed_at_tp2+weak_structure,no_historical_analogue | weak_structure,no_history,risk_penalty_applied | [perfect_trade] Confidence is only 50 (grade C) because this long fights a strongly bearish daily trend (1d EMA200 at 5.35 vs. price 1.27) even th |
| SPCXUSDT | long | 150.1 | 148.2 | 2026-09-12 12:09 | 2026-09-14 01:15 | 37.1 | 61 | B | excellent | mixed | 20.5 | 15.0 | 2.0 | 11.0 | 0.0 | — | 0.70 | 35.0 | none | yes | -1.27 | 0.11 | -1.27 | immediate_reversal+no_historical_analogue | no_history,negative_cmf | [bad_structure_call] SPCXUSDT is a 3/3-timeframe aligned long with fresh 4h FVG support and excellent entry timing per the engine, but volume divergenc |
| SOLUSDT | long | 104.8 | 101.68 | 2026-09-06 07:07 | 2026-09-12 06:56 | 143.8 | 73 | B+ | excellent | risk_on | 19.7 | 15.0 | 10.0 | 11.0 | 3.0 | 0.52 | — | 32.7 | none | yes | -2.98 | 0.54 | -2.98 | immediate_reversal+scanner_outage_corrupted | — | [infrastructure_failure] SOL is a B+ graded long with excellent entry quality, backed by aligned trend across all timeframes and a fresh 4h FVG near curren |
| LINKUSDT | long | 12.185 | 11.516 | 2026-09-06 07:07 | 2026-09-12 06:56 | 143.8 | 72 | B+ | excellent | risk_on | 21.3 | 11.0 | 10.0 | 11.0 | 0.0 | — | — | 45.4 | none | yes | -5.49 | 0.69 | -5.49 | immediate_reversal+no_historical_analogue,scanner_outage_corrupted | no_history | [infrastructure_failure] LINK is a B+ graded long with excellent entry quality and strong multi-timeframe trend alignment, including a confirmed daily BOS. |
| FILUSDT | long | 0.8021 | 0.9216 | 2026-09-06 07:06 | 2026-09-13 14:56 | 175.8 | 69 | B+ | excellent | risk_on | 21.1 | 15.0 | 7.0 | 11.0 | 0.0 | — | — | 44.5 | TP2 | no | 14.90 | 14.90 | -0.37 | closed_at_tp2+no_historical_analogue | no_history,negative_cmf | [perfect_trade] FIL presents a clean 'excellent' entry-quality long with full multi-timeframe trend alignment and a fresh 4h FVG as confirmation,  |
| SKHYUSDT | long | 161.6 | 159.06 | 2026-08-29 03:38 | 2026-09-03 05:21 | 121.7 | 62 | B | neutral | mixed | 18.5 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 42.1 | TP1 | yes | -1.57 | 2.28 | -1.57 | reached_tp1_then_stopped+weak_structure,no_historical_analogue | weak_structure,no_history | [good_entry_bad_exit] SKHYUSDT long is a B-grade, 62%-confidence trend trade built on 1h/1d bullish alignment and a fresh 1h FVG, but the 4h timeframe i |
| HEMIUSDT | long | 0.01165 | 0.010646 | 2026-08-29 06:47 | 2026-08-29 07:03 | 0.3 | 64 | B | neutral | mixed | 25.0 | 11.0 | 10.0 | 6.0 | 0.0 | — | — | 35.4 | none | yes | -8.62 | 0.57 | -8.62 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history,risk_penalty_applied | [bad_structure_call] HEMIUSDT long is a B-grade, 64%-confidence trend-following trade riding a genuinely strong multi-timeframe uptrend with solid volu |
| ENAUSDT | long | 0.163 | 0.15631 | 2026-08-29 03:38 | 2026-08-29 08:16 | 4.6 | 59 | B | neutral | mixed | 25.0 | 15.0 | 5.0 | 6.0 | 0.0 | — | — | 35.4 | TP1 | yes | -4.10 | 1.47 | -4.10 | reached_tp1_then_stopped+weak_structure,no_historical_analogue | weak_structure,no_history,risk_penalty_applied | [good_entry_bad_exit] ENAUSDT long is a B-grade, 59%-confidence trend trade supported by a genuine buyback-related news catalyst, but it carries a volat |
| SOXSUSDT | long | 49.3 | 53 | 2026-08-29 03:38 | 2026-09-02 20:20 | 112.7 | 60 | B | neutral | mixed | 16.1 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 49.2 | TP3 | no | 7.50 | 7.50 | 0.12 | ran_to_tp3+weak_structure,no_historical_analogue | weak_structure,no_history | [perfect_trade] SOXSUSDT long is a B-grade, 60%-confidence trend trade with only 2/3 timeframe alignment and an overbought 1h MFI reading right at |
| SNXXUSDT | short | 12.9 | 13.94 | 2026-08-29 03:07 | 2026-09-02 18:59 | 111.9 | 64 | B | neutral | mixed | 20.2 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 32.5 | none | yes | -8.06 | 0.62 | -8.06 | immediate_reversal+rsi_chop_zone,weak_structure,no_historical_analogue,short_direction,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history | [infrastructure_failure] Deterministic engine flags a B-grade short on SNXXUSDT, driven by bearish 4h/1d trend positioning below key EMAs, but structure an |
| SNDKUSDT | short | 1485 | 1548.9 | 2026-08-29 03:07 | 2026-09-02 18:59 | 111.9 | 59 | B | neutral | mixed | 15.0 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 37.7 | none | yes | -4.30 | 0.10 | -4.30 | immediate_reversal+rsi_chop_zone,weak_structure,no_historical_analogue,short_direction,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history | [infrastructure_failure] SNDKUSDT's B-grade short is the weakest of this batch — it fails the trend_confirms checklist due to a conflicting daily trend rea |
| CLUSDT | long | 83.15 | 90.82 | 2026-08-29 03:07 | 2026-09-02 18:59 | 111.9 | 58 | B | neutral | mixed | 14.4 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 42.1 | TP2 | no | 9.22 | 9.22 | -0.20 | closed_at_tp2+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | [infrastructure_failure] CLUSDT is the lowest-scoring setup in this batch, with 1h and 4h structure explicitly reading bearish against the long call and ve |
| ZECUSDT | long | 802 | 1166.44 | 2026-08-29 01:57 | 2026-09-06 06:22 | 196.4 | 65 | B+ | neutral | mixed | 20.9 | 8.0 | 10.0 | 6.0 | 0.0 | — | — | 42.1 | TP2 | no | 45.44 | 45.44 | -1.45 | closed_at_tp2+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | [infrastructure_failure] ZECUSDT carries the highest confidence and grade in this batch (65%, B+) on the back of a confirmed 1h bullish break-of-structure  |
| TRUMPUSDT | long | 2.75 | 2.174 | 2026-08-29 00:34 | 2026-09-02 18:59 | 114.4 | 47 | C | neutral | mixed | 24.8 | 15.0 | 2.0 | 6.0 | 0.0 | — | — | 35.4 | TP1 | yes | -20.95 | 10.98 | -20.95 | reached_tp1_then_stopped+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,negative_cmf,risk_penalty_applied | [infrastructure_failure] TRUMPUSDT is trend-aligned long but scored only a C grade at 47% confidence due to weak volume confirmation and crowded long posit |
| MOVRUSDT | long | 0.9115 | 0.7656 | 2026-08-28 20:11 | 2026-08-28 20:41 | 0.5 | 59 | B | neutral | mixed | 20.0 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 32.5 | none | yes | -16.01 | 0.23 | -16.01 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history,risk_penalty_applied | [bad_structure_call] MOVRUSDT is a B-grade long where the 4h/1d trend is constructive (strong ADX, rising OBV, unfilled daily bullish FVG below) but th |
| BNBUSDT | long | 694.55 | 686.61 | 2026-08-28 18:07 | 2026-08-28 18:40 | 0.6 | 71 | B+ | good | mixed | 20.0 | 8.0 | 5.0 | 11.0 | 10.5 | 0.54 | — | 37.7 | none | yes | -1.14 | -0.17 | -1.14 | immediate_reversal+rsi_chop_zone | rsi_chop_30_49,risk_penalty_applied | [bad_structure_call] BNBUSDT is a B+ grade long riding a strong daily uptrend with a favorable historical base rate (85% win rate on 20 similar setups) |
| MOVRUSDT | long | 0.9085 | 0.8819 | 2026-08-28 16:05 | 2026-08-28 16:29 | 0.4 | 61 | B | neutral | risk_on | 20.0 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 32.5 | none | yes | -2.93 | -0.11 | -2.93 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history,risk_penalty_applied | [bad_structure_call] MOVRUSDT is a moderate-conviction (Grade B, 61% confidence) long, supported by strong 4h/1d trend and momentum but held back by un |
| SPCXUSDT | long | 140.1 | 146.76 | 2026-08-28 15:58 | 2026-09-03 13:47 | 141.8 | 65 | B+ | neutral | risk_on | 18.8 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 35.0 | TP3 | no | 4.75 | 4.75 | -1.12 | ran_to_tp3+weak_structure,no_historical_analogue | weak_structure,no_history | [perfect_trade] SPCXUSDT is a B+ grade long with all three timeframes trending bullish and healthy volume/funding conditions, but entry timing is  |
| MSTRUSDT | long | 129 | 122.62 | 2026-08-28 15:58 | 2026-09-02 18:59 | 123.0 | 65 | B+ | good | risk_on | 19.5 | 15.0 | 5.0 | 11.0 | 0.0 | — | — | 30.0 | none | yes | -4.95 | -0.32 | -4.95 | immediate_reversal+no_historical_analogue,scanner_outage_corrupted | no_history,risk_penalty_applied | [infrastructure_failure] MSTRUSDT is a B+ long supported by strong 4h/1d trend and momentum, but the 1h timeframe is in active pullback with a bearish BOS, |
| MSTRUSDT | long | 133.7 | 129.1 | 2026-08-28 15:28 | 2026-08-28 15:51 | 0.4 | 65 | B+ | good | risk_on | 19.6 | 15.0 | 5.0 | 11.0 | 0.0 | — | — | 30.0 | none | yes | -3.44 | -0.75 | -3.44 | immediate_reversal+no_historical_analogue | no_history | [bad_structure_call] MSTR presents a B+ long setup where daily and 4h trend are strongly bullish, but the 1h timeframe is actively bearish (BOS down, n |
| ETHUSDT | long | 2502 | 2475.25 | 2026-08-28 15:10 | 2026-08-28 15:58 | 0.8 | 76 | A | neutral | risk_on | 24.4 | 8.0 | 10.0 | 6.0 | 9.0 | 0.49 | — | 26.0 | none | yes | -1.07 | 0.20 | -1.07 | immediate_reversal+weak_structure | weak_structure | [bad_structure_call] Grade A long with strong multi-timeframe trend alignment and a favorable risk-on regime, but structure confirmation is missing and |
| SUIUSDT | long | 0.76925 | 0.7233 | 2026-08-28 15:03 | 2026-09-12 06:56 | 351.9 | 63 | B | neutral | risk_on | 19.9 | 15.0 | 7.0 | 6.0 | 0.0 | — | — | 32.5 | none | yes | -5.97 | 3.59 | -5.97 | some_favorable_move_then_stopped+rsi_chop_zone,weak_structure,no_historical_analogue,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history,negative_cmf | [infrastructure_failure] SUIUSDT is a grade-B long where 1h and 1d trends align bullish but the 4h structure is explicitly labeled bearish, creating an int |
| XAGUSDT | long | 69.4 | 66.76 | 2026-08-28 15:15 | 2026-08-28 16:22 | 1.1 | 61 | B | neutral | risk_on | 20.1 | 15.0 | 5.0 | 6.0 | 0.0 | — | — | 37.7 | none | yes | -3.80 | 0.06 | -3.80 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | [bad_structure_call] XAGUSDT is a grade-B long backed by solid daily/4h trend structure, but the 1h just printed a bearish CHoCH and momentum is soft,  |
| SOLUSDT | long | 104.4 | 99.42 | 2026-08-28 14:10 | 2026-09-02 18:59 | 124.8 | 73 | B+ | good | risk_on | 24.9 | 15.0 | 5.0 | 11.0 | -3.0 | 0.52 | — | 32.7 | TP1 | yes | -4.77 | 2.73 | -4.77 | reached_tp1_then_stopped+scanner_outage_corrupted | — | [infrastructure_failure] SOL is a B+ long with daily/4h trend strongly bullish (ADX 40+) but a corrective 1h dip creating the entry opportunity; entry qual |
| MSTRUSDT | long | 134.74 | 132.35 | 2026-08-28 13:40 | 2026-08-28 14:10 | 0.5 | 71 | B+ | good | risk_on | 24.8 | 15.0 | 5.0 | 11.0 | 0.0 | — | — | 30.0 | none | yes | -1.77 | 0.28 | -1.77 | immediate_reversal+no_historical_analogue | no_history | [bad_structure_call] MSTRUSDT is a B+ long with daily/4h trend strongly bullish and risk-on regime support, but the 1h timeframe is in a bearish micro- |
| MUUSDT | long | 977.35 | 921.1 | 2026-08-21 10:34 | 2026-08-28 12:24 | 169.8 | 66 | B+ | neutral | risk_on | 19.8 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 40.8 | none | yes | -5.75 | 0.40 | -5.75 | immediate_reversal+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | [infrastructure_failure] MUUSDT is a B+ graded long with confidence 66, driven by clean multi-timeframe trend alignment and strong momentum in a risk-on re |
| DRAMUSDT | long | 58.425 | 55.92 | 2026-08-21 09:05 | 2026-08-28 12:24 | 171.3 | 63 | B | neutral | risk_on | 19.7 | 15.0 | 7.0 | 6.0 | 0.0 | — | — | 35.0 | none | yes | -4.29 | 0.62 | -4.29 | immediate_reversal+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,negative_cmf | [infrastructure_failure] DRAMUSDT is a grade-B long with confidence 63, supported by full multi-timeframe trend alignment and strong momentum, but the 4h s |
| SAMSUNGUSDT | long | 196.75 | 187.77 | 2026-08-21 08:25 | 2026-08-28 12:24 | 172.0 | 68 | B+ | neutral | risk_on | 22.0 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 45.4 | none | yes | -4.56 | 0.49 | -4.56 | immediate_reversal+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,liquidity_stress | [infrastructure_failure] SAMSUNGUSDT is a B+ graded long with solid multi-timeframe trend agreement and a risk_on regime tailwind, but entry quality is onl |
| LINKUSDT | long | 9.34 | 11.647 | 2026-08-16 12:09 | 2026-08-21 07:40 | 115.5 | 64 | B | neutral | mixed | 25.0 | 15.0 | 5.0 | 6.0 | 0.0 | — | — | 45.4 | TP2 | no | 24.70 | 24.70 | -0.12 | closed_at_tp2+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | [infrastructure_failure] LINK is a B-grade long built on a strong 4h trend (ADX 47.9) but weak short-term structure and volume confirmation, landing at 'ne |
| CLUSDT | long | 81.225 | 86.38 | 2026-08-16 09:51 | 2026-08-21 07:40 | 117.8 | 62 | B | neutral | mixed | 18.6 | 8.0 | 10.0 | 6.0 | 0.0 | — | — | 42.1 | TP3 | no | 6.35 | 6.35 | 0.04 | ran_to_tp3+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | [infrastructure_failure] CLUSDT is a B-grade, 62-confidence long with all three timeframes trading above key EMAs and clean funding/volume conditions, but  |
| ZECUSDT | short | 488.5 | 629.21 | 2026-08-16 09:34 | 2026-08-21 07:40 | 118.1 | 59 | B | neutral | mixed | 18.6 | 15.0 | 7.0 | 6.0 | 0.0 | — | — | 42.1 | none | yes | -28.80 | 0.76 | -28.80 | immediate_reversal+rsi_chop_zone,weak_structure,no_historical_analogue,short_direction,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history,negative_cmf | [infrastructure_failure] ZEC shows full trend alignment across 1h/4h/1d toward the downside with maxed momentum score, earning a B grade and 59 confidence. |
| ALLOUSDT | short | 0.268 | 0.27539 | 2026-08-16 10:31 | 2026-08-16 11:06 | 0.6 | 63 | B | neutral | mixed | 22.7 | 11.0 | 7.0 | 6.0 | 0.0 | — | — | 35.4 | none | yes | -2.76 | 0.55 | -2.76 | immediate_reversal+rsi_chop_zone,weak_structure,no_historical_analogue,short_direction,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history,negative_cmf | [infrastructure_failure] ALLOUSDT short is graded B at 63% confidence, driven by full timeframe trend agreement and negative funding, but structure lacks a |
| HYPEUSDT | long | 57.145 | 73.76 | 2026-08-16 09:45 | 2026-08-21 07:40 | 117.9 | 65 | B+ | excellent | mixed | 19.4 | 15.0 | 7.0 | 11.0 | 0.0 | — | — | 42.1 | TP3 | no | 29.07 | 29.07 | 0.12 | ran_to_tp3+no_historical_analogue,scanner_outage_corrupted | no_history,negative_cmf | [infrastructure_failure] HYPEUSDT is a B+ graded long with confidence 65, built on aligned 1h/4h bullish trend, a fresh 4h FVG, and strong momentum/volume  |
| ETHUSDT | short | 1880.25 | 2381.77 | 2026-08-16 07:55 | 2026-08-21 07:40 | 119.7 | 56 | B | neutral | mixed | 15.0 | 15.0 | 10.0 | 6.0 | 4.5 | 0.64 | — | 26.0 | none | yes | -26.67 | 0.11 | -26.67 | immediate_reversal+rsi_chop_zone,weak_structure,short_direction,scanner_outage_corrupted | rsi_chop_30_49,weak_structure | [infrastructure_failure] ETH's short is driven by 1h bearish momentum and crowded long positioning, but 4h/1d structure remains bullish, so this is a count |
| SPORTFUNUSDT | long | 0.0258 | 0.02422 | 2026-08-16 03:40 | 2026-08-16 06:42 | 3.0 | 59 | B | neutral | mixed | 23.9 | 15.0 | 7.0 | 6.0 | 0.0 | — | — | 35.4 | none | yes | -6.12 | 0.78 | -6.12 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history,negative_cmf,risk_penalty_applied | [bad_structure_call] This is a B-grade, 59-confidence long on a low-cap/illiquid pair with strong trend agreement across timeframes but no historical o |
| WLDUSDT | long | 0.34795 | 0.3768 | 2026-08-15 21:35 | 2026-08-21 07:40 | 130.1 | 67 | B+ | excellent | mixed | 21.9 | 15.0 | 7.0 | 11.0 | 0.0 | — | — | 40.8 | TP3 | no | 8.29 | 8.29 | -1.48 | ran_to_tp3+no_historical_analogue,scanner_outage_corrupted | no_history,negative_cmf | [infrastructure_failure] WLD offers a B+ graded long with excellent entry timing: 1h/4h trend and structure both confirm, momentum is maxed, and a fresh 4h |
| PUMPUSDT | long | 0.002807 | 0.003912 | 2026-08-15 20:20 | 2026-08-21 07:40 | 131.3 | 71 | B+ | excellent | mixed | 22.3 | 8.0 | 10.0 | 11.0 | 0.0 | — | — | 37.7 | TP2 | no | 39.37 | 39.37 | -3.46 | closed_at_tp2+no_historical_analogue,scanner_outage_corrupted | no_history | [infrastructure_failure] PUMPUSDT shows the cleanest technical alignment in this batch — 3/3 timeframes bullish, fresh 4h FVG, strong volume confirmation — |
| SKHYNIXUSDT | long | 1171.17 | 1253.92 | 2026-08-16 13:01 | 2026-08-21 07:40 | 114.6 | 65 | B+ | excellent | mixed | 20.0 | 8.0 | 7.0 | 11.0 | 0.0 | — | — | 37.7 | TP2 | no | 7.07 | 7.07 | 0.17 | closed_at_tp2+no_historical_analogue,scanner_outage_corrupted | no_history,negative_cmf | [infrastructure_failure] SKHYNIXUSDT is a B+ long anchored on a fresh 4h FVG with strong 4h ADX (48.5), but the 1d structure is still labeled bearish, crea |
| DOGEUSDT | short | 0.07015 | 0.0844 | 2026-08-15 17:07 | 2026-08-21 07:40 | 134.5 | 53 | C | neutral | mixed | 20.6 | 15.0 | 7.0 | 6.0 | 0.0 | — | — | 30.0 | none | yes | -20.31 | 0.95 | -20.31 | immediate_reversal+rsi_chop_zone,weak_structure,no_historical_analogue,short_direction,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history,negative_cmf | [infrastructure_failure] Multi-timeframe trend agreement supports a short bias, but structure hasn't freshly confirmed and 1h momentum is weak (ADX ~10), k |
| BNBUSDT | long | 610.5 | 604.36 | 2026-08-14 00:50 | 2026-08-14 11:14 | 10.4 | 69 | B+ | excellent | mixed | 21.2 | 8.0 | 5.0 | 11.0 | 6.0 | 0.55 | — | 37.7 | none | yes | -1.01 | 0.37 | -1.01 | immediate_reversal | — | [bad_structure_call] BNBUSDT long is supported by full multi-timeframe alignment and a fresh 4h FVG right at current price, with a favorable historical |
| SAMSUNGUSDT | long | 191.5 | 203.79 | 2026-08-14 02:12 | 2026-08-21 07:40 | 173.5 | 66 | B+ | neutral | mixed | 25.0 | 11.0 | 8.0 | 6.0 | 0.0 | — | — | 45.4 | TP2 | no | 6.42 | 6.42 | -0.95 | closed_at_tp2+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,mfi_over_80 | [infrastructure_failure] SAMSUNGUSDT long is driven by a very strong multi-timeframe uptrend (ADX 44+) but lacks fresh confirming structure and historical  |
| APRUSDT | long | 0.457 | 0.544 | 2026-08-14 00:44 | 2026-08-14 12:29 | 11.8 | 64 | B | neutral | mixed | 25.0 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 44.5 | TP3 | no | 19.04 | 19.04 | -4.33 | ran_to_tp3+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,risk_penalty_applied | [infrastructure_failure] APRUSDT is a 64-confidence (Grade B) long where the 4h and 1d trends are strongly bullish, but the 1h has just posted a bearish CH |
| SPCXUSDT | long | 143.55 | 139.58 | 2026-08-13 19:33 | 2026-08-15 14:00 | 42.4 | 66 | B+ | good | mixed | 22.6 | 15.0 | 5.0 | 11.0 | 0.0 | — | — | 35.0 | none | yes | -2.77 | 0.81 | -2.77 | immediate_reversal+no_historical_analogue | no_history | [bad_structure_call] SPCXUSDT is a B+ graded long with good entry quality: price is above EMA20/50 on all timeframes and daily momentum is strong, but  |
| LINKUSDT | long | 8.705 | 9.459 | 2026-08-14 08:24 | 2026-08-15 13:13 | 28.8 | 67 | B+ | neutral | mixed | 23.5 | 8.0 | 10.0 | 6.0 | 0.0 | — | — | 45.4 | TP3 | no | 8.66 | 8.66 | 0.31 | ran_to_tp3+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | [infrastructure_failure] LINKUSDT shows a clean 3-timeframe bullish trend alignment with decent volume/funding backing (score 57.5, confidence 67, grade B+ |
| BTWUSDT | long | 0.2615 | 0.31647 | 2026-08-13 15:54 | 2026-08-15 18:35 | 50.7 | 60 | B | excellent | mixed | 19.3 | 15.0 | 10.0 | 11.0 | 0.0 | — | — | 49.2 | TP3 | no | 21.02 | 21.02 | 0.10 | ran_to_tp3+no_historical_analogue,scanner_outage_corrupted | no_history,risk_penalty_applied,funding_elevated | [infrastructure_failure] BTWUSDT shows a genuinely clean, freshly-confirmed long setup with all three timeframes aligned bullish, fresh 4h FVG support, and |
| ETHUSDT | long | 1888 | 1868.99 | 2026-08-13 15:48 | 2026-08-13 16:40 | 0.9 | 65 | B+ | neutral | mixed | 14.1 | 15.0 | 7.0 | 6.0 | 12.0 | 0.65 | — | 26.0 | none | yes | -1.01 | -0.00 | -1.01 | immediate_reversal+rsi_chop_zone,weak_structure | rsi_chop_30_49,weak_structure,negative_cmf | [bad_structure_call] ETH long is grade B+ with 65% confidence, built on solid 1h/1d bullish structure, strong historical win rate (90%) and supportive  |
| MUUSDT | long | 911.25 | 934.3 | 2026-08-13 13:35 | 2026-08-13 13:47 | 0.2 | 64 | B | neutral | mixed | 20.2 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 40.8 | TP2 | no | 2.53 | 2.53 | 0.26 | closed_at_tp2+weak_structure,no_historical_analogue | weak_structure,no_history | [perfect_trade] MUUSDT is a B-grade, confidence-64 long backed by clean multi-timeframe trend alignment and strong momentum/volume, but structure  |
| SAMSUNGUSDT | long | 185.75 | 195.86 | 2026-08-13 13:16 | 2026-08-13 15:24 | 2.1 | 66 | B+ | neutral | mixed | 24.4 | 11.0 | 8.0 | 6.0 | 0.0 | — | — | 45.4 | TP2 | no | 5.44 | 5.44 | 0.20 | closed_at_tp2+weak_structure,no_historical_analogue | weak_structure,no_history,mfi_over_80 | [perfect_trade] This is a B+ grade long at 66 confidence, driven by unusually strong trend alignment and ADX across all timeframes, but it lacks a |
| SOXSUSDT | short | 41.15 | 40.86 | 2026-08-13 12:58 | 2026-08-13 13:04 | 0.1 | 69 | B+ | good | mixed | 21.1 | 8.0 | 10.0 | 11.0 | 0.0 | — | — | 49.2 | TP2 | no | 0.70 | 0.70 | 0.24 | closed_at_tp2+rsi_chop_zone,no_historical_analogue,short_direction | rsi_chop_30_49,no_history | [perfect_trade] SOXSUSDT is a B+-grade short with 3/3 timeframe agreement and confirmed bearish structure, giving it the cleaner setup of the two  |
| EWYUSDT | long | 174.6 | 179.2 | 2026-08-13 12:10 | 2026-08-13 14:36 | 2.4 | 64 | B | neutral | mixed | 22.4 | 15.0 | 8.0 | 6.0 | 0.0 | — | — | 40.8 | TP2 | no | 2.63 | 2.63 | -0.18 | closed_at_tp2+weak_structure,no_historical_analogue | weak_structure,no_history,mfi_over_80 | [perfect_trade] A trend-following long with bullish alignment across timeframes but weak structural confirmation (checklist structure_confirms: fa |
| DRAMUSDT | long | 54.35 | 55.89 | 2026-08-13 11:33 | 2026-08-13 14:24 | 2.9 | 64 | B | good | mixed | 17.5 | 15.0 | 8.0 | 11.0 | 0.0 | — | — | 35.0 | TP2 | no | 2.83 | 2.83 | -0.33 | closed_at_tp2+no_historical_analogue | no_history,mfi_over_80 | [perfect_trade] DRAMUSDT is a grade-B long with good entry quality, built on a bullish 4h trend (ADX ~30, RSI ~65) and a nearby 1h FVG, but the 1h |
| NVDAUSDT | long | 223.85 | 227.39 | 2026-08-13 15:36 | 2026-08-28 12:24 | 356.8 | 62 | B | neutral | mixed | 23.6 | 15.0 | 5.0 | 6.0 | 0.0 | — | — | 49.2 | TP2 | no | 1.58 | 1.58 | 0.15 | closed_at_tp2+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,negative_cmf,mfi_over_80 | [infrastructure_failure] NVDAUSDT is a grade-B long with neutral entry quality: EMA trend alignment is strong across all three timeframes and ADX confirms  |
| SKHYUSDT | long | 150.8 | 163.91 | 2026-08-13 09:27 | 2026-08-13 14:48 | 5.3 | 64 | B | good | mixed | 18.1 | 15.0 | 8.0 | 11.0 | 0.0 | — | — | 42.1 | TP3 | no | 8.69 | 8.69 | 0.38 | ran_to_tp3+no_historical_analogue | no_history,mfi_over_80 | [perfect_trade] SKHYUSDT is a B-grade long with good entry quality, built on a bullish 4h/1d trend and strong momentum, but the 1h timeframe has j |
| CYSUSDT | long | 1.465 | 1.3759 | 2026-08-13 08:07 | 2026-08-13 09:21 | 1.2 | 63 | B | good | mixed | 25.0 | 15.0 | 5.0 | 11.0 | 0.0 | — | — | 40.8 | none | yes | -6.08 | 0.74 | -6.08 | immediate_reversal+no_historical_analogue | no_history,risk_penalty_applied | [bad_structure_call] CYS has strong trend and momentum scores driving the long call, but the lack of historical data, a volatility penalty, and a confl |
| XAUUSDT | long | 4400.5 | 4374.88 | 2026-08-13 05:34 | 2026-08-13 06:37 | 1.1 | 68 | B+ | neutral | mixed | 25.0 | 8.0 | 10.0 | 6.0 | 0.0 | — | — | 40.8 | none | yes | -0.58 | 0.05 | -0.58 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | [bad_structure_call] XAUUSDT is a B+ graded long with solid multi-timeframe trend alignment (68% confidence) but a 'neutral' entry quality — trend is c |
| PAXGUSDT | long | 4390.5 | 4364.53 | 2026-08-13 05:34 | 2026-08-13 06:37 | 1.1 | 68 | B+ | neutral | mixed | 25.0 | 8.0 | 10.0 | 6.0 | 0.0 | — | — | 40.8 | none | yes | -0.59 | 0.06 | -0.59 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | [bad_structure_call] PAXGUSDT mirrors XAUUSDT's setup closely — a B+ graded long at 68% confidence with all timeframes trend-aligned but no fresh struc |
| BTWUSDT | long | 0.23761 | 0.26966 | 2026-08-13 05:13 | 2026-08-13 15:18 | 10.1 | 61 | B | good | mixed | 19.9 | 15.0 | 10.0 | 11.0 | 0.0 | — | — | 49.2 | TP2 | no | 13.49 | 13.49 | -3.51 | closed_at_tp2+no_historical_analogue | no_history,risk_penalty_applied,funding_elevated | [good_trade] BTW is a grade B long at 61% confidence with confirmed structure and strong multi-timeframe trend alignment, but an explicit volat |
| XAGUSDT | long | 65.35 | 64.34 | 2026-08-12 19:23 | 2026-08-13 19:15 | 23.9 | 68 | B+ | good | mixed | 25.0 | 8.0 | 5.0 | 11.0 | 0.0 | — | — | 37.7 | none | yes | -1.55 | 1.42 | -1.55 | some_favorable_move_then_stopped+no_historical_analogue | no_history | [bad_structure_call] XAGUSDT long is the stronger of the two setups here — confirmed 4h structure, a very strong 4h ADX (42), and a 'good' entry-qualit |
| CRCLUSDT | long | 69.8 | 73.78 | 2026-08-12 14:55 | 2026-08-13 19:04 | 28.1 | 54 | C | neutral | mixed | 23.3 | 15.0 | 5.0 | 6.0 | 0.0 | — | — | 45.4 | TP2 | no | 5.70 | 5.70 | -0.43 | closed_at_tp2+weak_structure,no_historical_analogue | weak_structure,no_history | [perfect_trade] Higher timeframes (4h, 1d) lean bullish, but 1h momentum and structure are weak and history isn't usable here (no stored match), w |
| LITEUSDT | long | 892.5 | 846.79 | 2026-08-12 13:29 | 2026-08-12 13:40 | 0.2 | 73 | B+ | excellent | mixed | 24.1 | 15.0 | 10.0 | 11.0 | 0.0 | — | — | 35.4 | none | yes | -5.12 | 0.84 | -5.12 | immediate_reversal+no_historical_analogue,scanner_outage_corrupted | no_history | [infrastructure_failure] LITE shows strong momentum and volume but carries a B+ grade with a failed history checklist item — there's simply no track record |
| CLUSDT | long | 82.55 | 80.92 | 2026-08-12 11:55 | 2026-08-13 08:38 | 20.7 | 62 | B | neutral | mixed | 23.8 | 15.0 | 5.0 | 6.0 | 0.0 | — | — | 42.1 | none | yes | -1.98 | 0.28 | -1.98 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | [bad_structure_call] CL is a B-grade long on solid multi-timeframe EMA alignment and trend strength (4h ADX ~35), but structure confirmation is missing |
| HOLOUSDT | long | 0.07725 | 0.07171 | 2026-08-12 10:21 | 2026-08-12 18:28 | 8.1 | 64 | B | good | mixed | 23.5 | 15.0 | 7.0 | 11.0 | 0.0 | — | — | 35.4 | none | yes | -7.17 | 0.63 | -7.17 | immediate_reversal+no_historical_analogue,scanner_outage_corrupted | no_history,negative_cmf,risk_penalty_applied | [infrastructure_failure] HOLOUSDT is a grade-B long with genuinely trending 4h/1d structure and strong momentum, but the setup has no historical base rate  |
| DOGEUSDT | long | 0.0714 | 0.0696 | 2026-08-12 08:43 | 2026-08-12 21:31 | 12.8 | 56 | B | good | mixed | 15.6 | 15.0 | 10.0 | 11.0 | 0.0 | — | — | 30.0 | none | yes | -2.52 | 1.06 | -2.52 | some_favorable_move_then_stopped+no_historical_analogue | no_history | [bad_structure_call] DOGE is a B-grade, moderate-confidence (56) long riding an established uptrend on 1h/4h with supportive daily structure, but crowd |
| VELVETUSDT | long | 0.5505 | 0.7007 | 2026-08-12 08:08 | 2026-08-12 18:28 | 10.3 | 63 | B | good | mixed | 24.7 | 15.0 | 5.0 | 11.0 | 0.0 | — | — | 44.5 | TP3 | no | 27.28 | 27.28 | -0.45 | ran_to_tp3+no_historical_analogue,scanner_outage_corrupted | no_history,risk_penalty_applied | [infrastructure_failure] VELVETUSDT is a Grade B long with 63% confidence, driven by strong multi-timeframe trend alignment and a trending 4h ADX, but entr |
| NEARUSDT | long | 1.6425 | 1.862 | 2026-08-12 08:02 | 2026-08-21 07:40 | 215.6 | 61 | B | excellent | mixed | 15.3 | 15.0 | 7.0 | 11.0 | 0.0 | — | — | 49.2 | TP3 | no | 13.36 | 13.36 | -1.80 | ran_to_tp3+no_historical_analogue,scanner_outage_corrupted | no_history,negative_cmf | [infrastructure_failure] NEARUSDT long is a B grade, 61% confidence setup driven by strong short-term momentum and fresh 4h structure, but the daily trend  |
| BZUSDT | long | 87.6 | 85.83 | 2026-08-12 07:37 | 2026-08-13 08:38 | 25.0 | 65 | B+ | neutral | mixed | 24.3 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 32.5 | none | yes | -2.02 | 0.60 | -2.02 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history,funding_elevated | [bad_structure_call] BZUSDT long is a multi-timeframe trend-following setup (B+ grade, 65% confidence) with strong trend and volume scores but weak str |
| SKHYUSDT | long | 143.9 | 152 | 2026-08-12 05:44 | 2026-08-12 13:52 | 8.1 | 63 | B | excellent | mixed | 14.7 | 15.0 | 10.0 | 11.0 | 0.0 | — | — | 42.1 | TP2 | no | 5.63 | 5.63 | 0.51 | closed_at_tp2+no_historical_analogue | no_history | [perfect_trade] A grade B long with good short-term structure and fresh 4h confirmation, but the daily trend disagrees with the 1h/4h bullish read |
| HYPEUSDT | short | 54.3 | 55.689 | 2026-08-11 19:24 | 2026-08-12 11:20 | 15.9 | 64 | B | excellent | mixed | 18.6 | 8.0 | 7.0 | 11.0 | 0.0 | — | — | 42.1 | none | yes | -2.56 | 0.34 | -2.56 | immediate_reversal+rsi_chop_zone,no_historical_analogue,short_direction | rsi_chop_30_49,no_history | [bad_structure_call] Deterministic engine flags a B-grade short on HYPEUSDT with 64% confidence, driven by clean 3-timeframe bearish alignment and a fr |
| SOLUSDT | short | 75.15 | 76.68 | 2026-08-11 19:18 | 2026-08-12 09:29 | 14.2 | 65 | B+ | excellent | mixed | 20.1 | 8.0 | 2.0 | 11.0 | 4.5 | 0.56 | — | 32.7 | none | yes | -2.04 | 0.01 | -2.04 | immediate_reversal+rsi_chop_zone,short_direction | rsi_chop_30_49 | [bad_structure_call] This is a B+ graded, 65%-confidence short on a fresh 4h bearish structure break with aligned 1h/4h trend, but volume confirmation  |
| SNDKUSDT | long | 1263 | 1342.1 | 2026-08-11 18:32 | 2026-08-12 12:54 | 18.4 | 62 | B | excellent | mixed | 13.6 | 15.0 | 10.0 | 11.0 | 0.0 | — | — | 37.7 | TP3 | no | 6.26 | 6.26 | 0.19 | ran_to_tp3+no_historical_analogue | no_history | [perfect_trade] This is a B-grade, 62-confidence long on SNDKUSDT built on strong 1h/4h momentum and a fresh 4h bullish FVG, but it's fighting the |
| SNXXUSDT | short | 9.825 | 10.37 | 2026-08-11 17:15 | 2026-08-12 05:26 | 12.2 | 55 | B | good | mixed | 13.5 | 15.0 | 8.0 | 11.0 | 0.0 | — | — | 32.5 | none | yes | -5.55 | 0.46 | -5.55 | immediate_reversal+no_historical_analogue,short_direction,scanner_outage_corrupted | no_history,risk_penalty_applied | [infrastructure_failure] This is a B-grade short built mainly on 4h/1d trend and strong momentum/structure scores, but it's fighting a bullish 1h picture ( |
| RKLBUSDT | short | 78.1 | — | 2026-08-11 17:03 | 2026-08-11 18:49 | 1.8 | 68 | B+ | good | mixed | 22.9 | 8.0 | 7.0 | 11.0 | 0.0 | — | — | 35.4 | none | yes | -2.66 | 0.41 | -2.66 | immediate_reversal+rsi_chop_zone,no_historical_analogue,short_direction | rsi_chop_30_49,no_history | [bad_structure_call] This is a B+ short on 4h/1d bearish structure beneath a still-mixed 1h picture, with decent trend and structure scores but no supp |
| DRAMUSDT | short | 50.875 | 52.58 | 2026-08-11 15:52 | 2026-08-12 05:26 | 13.6 | 59 | B | neutral | mixed | 15.0 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 35.0 | none | yes | -3.35 | 0.85 | -3.35 | immediate_reversal+weak_structure,no_historical_analogue,short_direction,scanner_outage_corrupted | weak_structure,no_history | [infrastructure_failure] This is a B-grade, medium-confidence (59) short on DRAMUSDT built on daily-trend bearishness diverging from a stalling 1h/4h bounc |
| HYPEUSDT | long | 55.05 | — | 2026-08-11 13:17 | 2026-08-11 15:35 | 2.3 | 57 | B | neutral | mixed | 13.2 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 42.1 | none | yes | -1.64 | -0.00 | -1.64 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | [bad_structure_call] HYPEUSDT is a moderate-confidence (57, grade B) long based on 1h/4h price holding above key EMAs and constructive volume flow, but |
| SKHYNIXUSDT | short | 1008.5 | 1058.89 | 2026-08-11 09:55 | 2026-08-12 05:26 | 19.5 | 55 | B | neutral | mixed | 19.4 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 37.7 | none | yes | -5.00 | 0.09 | -5.00 | immediate_reversal+rsi_chop_zone,weak_structure,no_historical_analogue,short_direction,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history | [infrastructure_failure] This is a grade B, 55-confidence short driven by strong daily/4h bearish momentum, but structure hasn't freshly confirmed and posi |
| SOLUSDT | long | 76.5 | — | 2026-08-10 05:50 | 2026-08-11 15:40 | 33.8 | 45 | C | — | risk_on | 22.3 | 15.0 | 10.0 | 6.0 | 1.5 | 0.63 | — | 32.7 | none | yes | -2.21 | 0.51 | -2.21 | immediate_reversal+weak_structure | weak_structure | [bad_structure_call] Confidence is capped at 45 (grade C) because structure doesn't confirm and the historical analogue set actually skews slightly bea |
| 1000PEPEUSDT | long | 0.0029 | 0.0026833 | 2026-08-10 05:50 | 2026-08-13 00:20 | 66.5 | 64 | B | — | risk_on | 20.7 | 15.0 | 7.0 | 6.0 | 0.0 | — | — | 40.8 | none | yes | -7.47 | 0.15 | -7.47 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | [bad_structure_call] This is a B-grade, moderate-confidence (64) multi-timeframe trend long with clean EMA/momentum alignment across 1h/4h/1d, but it c |
| BTCUSDT | long | 65000 | — | 2026-08-10 05:50 | 2026-08-11 07:11 | 25.3 | 69 | B+ | — | risk_on | 19.7 | 8.0 | 7.0 | 6.0 | 7.5 | 0.60 | — | 35.4 | none | yes | -1.61 | 0.24 | -1.61 | immediate_reversal+weak_structure,scanner_outage_corrupted | weak_structure | [infrastructure_failure] This is a B+ grade, 69-confidence trend-following BTC long backed by a genuinely favorable historical win rate (75%) and clean mul |
| ETHUSDT | long | 1918 | — | 2026-08-10 05:50 | 2026-08-11 07:11 | 25.3 | 69 | B+ | — | risk_on | 19.0 | 8.0 | 7.0 | 6.0 | 7.5 | 0.62 | — | 26.0 | none | yes | -2.32 | 0.27 | -2.32 | immediate_reversal+weak_structure,scanner_outage_corrupted | weak_structure | [infrastructure_failure] B+ grade, 69-confidence ETH long supported by a strong historical win rate and full EMA alignment, but undermined by an explicit 1 |
| BICOUSDT | long | 0.07085 | — | 2026-08-09 05:46 | 2026-08-10 05:12 | 23.4 | 71 | B+ | — | risk_on | 25.0 | 9.0 | 10.0 | 11.0 | 0.0 | — | — | 35.4 | none | yes | -44.42 | -0.55 | -44.42 | immediate_reversal+no_historical_analogue,scanner_outage_corrupted | no_history,high_atr_extension,risk_penalty_applied | [infrastructure_failure] BICO is in a strong, broadly confirmed uptrend across 1h/4h/1d with solid volume backing, earning a B+ grade at 71% confidence, bu |
| ACEUSDT | long | 0.128 | 0.17896 | 2026-08-09 05:34 | 2026-08-14 09:57 | 124.4 | 71 | B+ | — | risk_on | 25.0 | 15.0 | 10.0 | 11.0 | 0.0 | — | — | 40.8 | TP3 | no | 39.81 | 39.81 | -0.99 | ran_to_tp3+no_historical_analogue | no_history,risk_penalty_applied | [perfect_trade] ACEUSDT is a B+ trend-continuation long with strong multi-timeframe ADX alignment and favorable negative funding, but the daily ch |
| BEATUSDT | long | 2.875 | — | 2026-08-09 05:16 | 2026-08-10 05:12 | 23.9 | 62 | B | — | risk_on | 20.9 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 35.4 | TP1 | yes | -9.50 | 8.56 | -9.50 | reached_tp1_then_stopped+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,risk_penalty_applied | [infrastructure_failure] BEATUSDT is a moderate-conviction long (B grade, 62% confidence) driven by aligned 1h/4h bullish trend and momentum, but the daily |
| QQQUSDT | long | 721.25 | 733.27 | 2026-08-08 10:30 | 2026-08-13 23:06 | 132.6 | 72 | B+ | — | risk_on | 24.5 | 8.0 | 7.0 | 11.0 | 0.0 | — | — | 44.5 | TP2 | no | 1.67 | 1.67 | 0.07 | closed_at_tp2+no_historical_analogue | no_history | [perfect_trade] QQQUSDT long leans on strong daily/4h trend, but the 1h structure is explicitly bearish right now and there's no historical or ML  |
| PAXGUSDT | long | 4329 | — | 2026-08-08 06:45 | 2026-08-11 11:04 | 76.3 | 71 | B+ | — | risk_on | 25.0 | 11.0 | 10.0 | 6.0 | 0.0 | — | — | 40.8 | TP2 | no | 1.36 | 1.36 | 0.12 | closed_at_tp2+weak_structure,no_historical_analogue | weak_structure,no_history,high_atr_extension | [perfect_trade] PAXG long closely mirrors the XAUUSDT setup — strong trend and momentum but no historical or ML backing, and entering into overbou |
| CRCLUSDT | long | 66.4 | — | 2026-08-08 06:45 | 2026-08-11 13:46 | 79.0 | 54 | C | — | risk_on | 17.5 | 15.0 | 8.0 | 6.0 | 0.0 | — | — | 45.4 | TP2 | no | 5.24 | 5.24 | 0.48 | closed_at_tp2+weak_structure,no_historical_analogue | weak_structure,no_history | [perfect_trade] CRCL only scored a C-grade 54 confidence long — the 1h structure is actually bearish with a confirmed change-of-character, directl |
| ACEUSDT | long | 0.1145 | — | 2026-08-07 19:53 | 2026-08-08 10:30 | 14.6 | 61 | B | — | risk_on | 25.0 | 15.0 | 10.0 | 11.0 | 0.0 | — | — | 40.8 | none | yes | -9.66 | -0.69 | -9.66 | immediate_reversal+no_historical_analogue | no_history,risk_penalty_applied,liquidity_stress,funding_elevated | [bad_structure_call] ACE is a B-grade, 61-confidence long built on strong 4h/1d trend strength (ADX 56.5, price above all major EMAs) despite a bearish |
| ZECUSDT | long | 511.75 | — | 2026-08-07 19:47 | 2026-08-11 07:11 | 83.4 | 67 | B+ | — | risk_on | 21.1 | 8.0 | 10.0 | 6.0 | 0.0 | — | — | 42.1 | none | yes | -4.36 | 0.40 | -4.36 | immediate_reversal+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | [infrastructure_failure] ZEC long rides strong short-term momentum but directly conflicts with its own bearish daily structure and has no historical or ML  |
| CYSUSDT | long | 0.8175 | — | 2026-08-07 14:41 | 2026-08-07 16:37 | 1.9 | None | — | — | risk_on | 25.0 | 8.0 | 5.0 | 11.0 | 0.0 | — | — | 40.8 | TP2 | no | 19.67 | 19.67 | 0.48 | closed_at_tp2+no_historical_analogue | no_history,risk_penalty_applied | [perfect_trade] CYSUSDT's long signal is driven by a powerful 4h/1d uptrend, but the 1h structure is bearish, daily momentum is extremely overboug |
| EWYUSDT | long | 170.25 | — | 2026-08-05 19:42 | 2026-08-07 14:27 | 42.7 | None | — | — | risk_on | 14.8 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 40.8 | none | yes | -3.65 | 0.15 | -3.65 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | [bad_structure_call] EWY is a B-grade long (61 confidence) riding 4h/1d bullish structure and a supportive risk-on regime, but the failed trend_confirm |
| SNDKUSDT | long | 1387.5 | — | 2026-08-05 19:42 | 2026-08-07 11:51 | 40.1 | None | — | — | risk_on | 14.3 | 15.0 | 10.0 | 6.0 | 0.0 | — | — | 37.7 | none | yes | -7.00 | 0.01 | -7.00 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | [bad_structure_call] SNDK is a B-grade long (60 confidence) built on 4h bullish momentum and CMF flow, but it's the weakest of the three setups here —  |
| DRAMUSDT | long | 54.45 | — | 2026-08-05 19:31 | 2026-08-07 11:51 | 40.3 | None | — | — | risk_on | 12.8 | 15.0 | 10.0 | 11.0 | 0.0 | — | — | 35.0 | none | yes | -5.31 | 0.39 | -5.31 | immediate_reversal+no_historical_analogue | no_history | [bad_structure_call] This is a lower-conviction B-grade long (64 confidence, score 63.8) where short-term momentum is bullish but the daily trend is ac |
| NVDAUSDT | long | 214.7 | 223.53 | 2026-08-05 11:25 | 2026-08-12 21:02 | 177.6 | None | — | — | mixed | 22.3 | 11.0 | 8.0 | 6.0 | 0.0 | — | — | 49.2 | TP2 | no | 4.11 | 4.11 | 0.53 | closed_at_tp2+weak_structure,no_historical_analogue | weak_structure,no_history | [perfect_trade] NVDAUSDT is in a clean multi-timeframe uptrend — above EMA20/50 on 1h/4h/1d, 1h ADX 40, fresh daily MACD cross with a daily FVG, a |

**Ranked biggest winners and losers**

*Top 10 winners*
| # | Symbol | Dir | Ret% | Hold h | Conf | EQ | Regime | Exit in monitoring gap? | Stop slippage% |
|---|---|---|---|---|---|---|---|---|---|
| 1 | NEARUSDT | long | 114.28 | 268.8 | 57 | neutral | mixed | yes | — |
| 2 | UNIUSDT | long | 52.19 | 267.7 | 64 | neutral | mixed | yes | — |
| 3 | ZECUSDT | long | 45.44 | 196.4 | 65 | neutral | mixed | yes | — |
| 4 | ACEUSDT | long | 39.81 | 124.4 | 71 | — | risk_on | no | — |
| 5 | PUMPUSDT | long | 39.37 | 131.3 | 71 | excellent | mixed | yes | — |
| 6 | ZECUSDT | long | 37.08 | 268.2 | 59 | neutral | mixed | yes | — |
| 7 | 1000PEPEUSDT | long | 32.42 | 297.7 | 56 | neutral | mixed | yes | — |
| 8 | HYPEUSDT | long | 29.07 | 117.9 | 65 | excellent | mixed | yes | — |
| 9 | VELVETUSDT | long | 27.28 | 10.3 | 63 | good | mixed | yes | — |
| 10 | LINKUSDT | long | 24.70 | 115.5 | 64 | neutral | mixed | yes | — |

*Top 10 losers*
| # | Symbol | Dir | Ret% | Hold h | Conf | EQ | Regime | Exit in monitoring gap? | Stop slippage% |
|---|---|---|---|---|---|---|---|---|---|
| 1 | BICOUSDT | long | -44.42 | 23.4 | 71 | — | risk_on | yes | — |
| 2 | ZECUSDT | short | -28.80 | 118.1 | 59 | neutral | mixed | yes | -27.24 |
| 3 | ETHUSDT | short | -26.67 | 119.7 | 56 | neutral | mixed | yes | -25.98 |
| 4 | PUMPUSDT | short | -23.29 | 309.1 | 60 | excellent | mixed | no | -15.84 |
| 5 | TRUMPUSDT | long | -20.95 | 114.4 | 47 | neutral | mixed | yes | -13.21 |
| 6 | DOGEUSDT | short | -20.31 | 134.5 | 53 | neutral | mixed | yes | -18.71 |
| 7 | WLDUSDT | short | -18.79 | 316.5 | 61 | good | mixed | yes | -15.87 |
| 8 | MOVRUSDT | long | -16.01 | 0.5 | 59 | neutral | mixed | no | -9.40 |
| 9 | DOGEUSDT | short | -15.80 | 274.9 | 59 | neutral | mixed | yes | -15.12 |
| 10 | ACEUSDT | long | -9.66 | 14.6 | 61 | — | risk_on | no | — |


## SECTION C — CONFIDENCE CALIBRATION

| Bucket | n | Mean predicted | Observed win% | Wilson CI | Pred−Obs pp | Avg ret | Median ret | TP1% | TP2% | TP3% | Stop% | PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| <50 | 3 | 46.7% | 0.0% | 0–56.2 | 46.7 | -10.17 | -7.36 | 33.3 | 0.0 | 0.0 | 100.0 | 0.00 |
| 50–54 | 7 | 52.9% | 57.1% | 25.0–84.2 | -4.2 | 0.96 | 2.93 | 71.4 | 57.1 | 0.0 | 42.9 | 1.26 |
| 55–59 | 22 | 57.4% | 31.8% | 16.4–52.7 | 25.6 | 4.66 | -2.94 | 40.9 | 31.8 | 4.5 | 68.2 | 1.80 |
| 60–64 | 39 | 62.4% | 46.2% | 31.6–61.4 | 16.2 | 2.27 | -1.27 | 56.4 | 48.7 | 20.5 | 53.8 | 1.65 |
| 65–69 | 29 | 66.7% | 37.9% | 22.7–56.0 | 28.8 | 3.15 | -1.01 | 34.5 | 37.9 | 13.8 | 62.1 | 2.97 |
| 70–74 | 12 | 71.6% | 33.3% | 13.8–60.9 | 38.3 | 1.29 | -1.46 | 41.7 | 33.3 | 8.3 | 66.7 | 1.23 |
| 75+ | 1 | 76.0% | 0.0% | 0–79.3 | 76.0 | -1.07 | -1.07 | 0.0 | 0.0 | 0.0 | 100.0 | 0.00 |

Calibration curve (■ predicted, ▒ observed):
```
   <50 n=3   pred ■■■■■■■■■■■■■          46.7%
              obs                          0.0%
 50–54 n=7   pred ■■■■■■■■■■■■■■■        52.9%
              obs  ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒       57.1%
 55–59 n=22  pred ■■■■■■■■■■■■■■■■       57.4%
              obs  ▒▒▒▒▒▒▒▒▒              31.8%
 60–64 n=39  pred ■■■■■■■■■■■■■■■■■      62.4%
              obs  ▒▒▒▒▒▒▒▒▒▒▒▒▒          46.2%
 65–69 n=29  pred ■■■■■■■■■■■■■■■■■■■    66.7%
              obs  ▒▒▒▒▒▒▒▒▒▒             37.9%
 70–74 n=12  pred ■■■■■■■■■■■■■■■■■■■■   71.6%
              obs  ▒▒▒▒▒▒▒▒▒              33.3%
   75+ n=1   pred ■■■■■■■■■■■■■■■■■■■■■  76.0%
              obs                          0.0%
```
Overall: mean stated confidence 62.6% vs observed 38.9% (44/113); exact binomial test p=4.35e-07.
| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| conf ≥70 vs 60–64 | 13/39 | 30.8% / 46.2% | 0.52 | [0.14, 1.97] | 0.5181 | 0.0134 | NOT SIGNIFICANT |
| conf ≥65 vs <65 | 42/71 | 35.7% / 40.8% | 0.8 | [0.37, 1.77] | 0.6907 | 0.0019 | NOT SIGNIFICANT |

Brier 0.298 vs constant-base-rate Brier 0.2378 (n=113); Spearman(confidence, return)=0.094 (p=0.322).
**Is confidence calibrated? NO — CONFIRMED overconfident in aggregate (binomial p above; observed win rate is below predicted in every bucket ≥55).** **Does 70 outperform 60? NOT SUPPORTED** (≥70: 30.8% n=13 vs 60–64: 46.2% n=39, p=0.5181); confidence has no detectable rank relation to return. **Should confidence be shifted?** A display-layer calibration (already built) is justified; shifting the underlying formula is INSUFFICIENT DATA (buckets ≥70 have n≤12).

## SECTION D — GRADE CALIBRATION

| Grade | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | TP1% | TP2% | TP3% | Stop% | Avg conf |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | 0.0% | 0–79.3 | -1.07 | -1.07 | 0.00 | 0.0 | 0.0 | 0.0 | 100.0 | 76.0 |
| B | 61 | 41.0% | 29.5–53.5 | 3.13 | -1.98 | 1.72 | 50.8 | 42.6 | 14.8 | 59.0 | 60.6 |
| B+ | 41 | 36.6% | 23.6–51.9 | 2.60 | -1.14 | 1.94 | 36.6 | 36.6 | 12.2 | 63.4 | 68.1 |
| C | 10 | 40.0% | 16.8–68.7 | -2.38 | -1.60 | 0.58 | 60.0 | 40.0 | 0.0 | 60.0 | 51.0 |
| none | 5 | 40.0% | 11.8–76.9 | 1.56 | -3.65 | 1.49 | 40.0 | 40.0 | 0.0 | 60.0 | — |
| Avoid (never traded) | 48 | — | — | — | — | — | — | — | — | — | — |

| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| B+ vs B | 41/61 | 36.6% / 41.0% | 0.83 | [0.37, 1.88] | 0.6844 | 0.0014 | NOT SIGNIFICANT |

Spearman(grade rank, return)=0.101 (p=0.287, n=113). Grade is a deterministic bin of confidence (≥65→B+, 55–64→B, 45–54→C), so it inherits confidence's calibration. **Do grades mean anything statistically? NOT SUPPORTED** — B+ vs B p=0.6844; A has n=1 and 'Avoid' plans are never traded so the bottom of the scale cannot be validated (INSUFFICIENT DATA).

## SECTION E — ENTRY QUALITY AUDIT

| EQ | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | TP1% | TP2% | TP3% | Stop% | Median hold h | MFE | MAE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| excellent | 19 | 52.6% | 31.7–72.7 | 5.43 | 2.93 | 3.30 | 57.9 | 52.6 | 26.3 | 47.4 | 114.6 | 8.31 | -2.67 |
| good | 20 | 30.0% | 14.5–51.9 | -0.48 | -2.15 | 0.85 | 40.0 | 35.0 | 10.0 | 70.0 | 10.2 | 3.41 | -3.39 |
| neutral | 62 | 38.7% | 27.6–51.2 | 3.43 | -1.60 | 1.87 | 45.2 | 38.7 | 9.7 | 61.3 | 26.6 | 8.01 | -4.07 |
| late | 0 |  |  |  |  |  |  |  |  |  |  |  |  |
| exhausted | 0 |  |  |  |  |  |  |  |  |  |  |  |  |

ScanSnapshot entry_quality distribution (all 81540 scans): {None: 6012, 'excellent': 2322, 'exhausted': 11099, 'good': 3326, 'invalid': 23433, 'late': 15921, 'neutral': 19427}. `late`/`exhausted` never appear among trades **by construction** (they block issuance); their effect is measurable only through §T.
| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| excellent vs rest | 19/82 | 52.6% / 36.6% | 1.93 | [0.7, 5.27] | 0.2067 | 0.0116 | NOT SIGNIFICANT |
| good vs neutral | 20/62 | 30.0% / 38.7% | 0.68 | [0.23, 2.01] | 0.5972 | 0.0044 | NOT SIGNIFICANT |

| Era | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF |
|---|---|---|---|---|---|---|
| Pre entry-quality launch | 17 | 35.3% | 17.3–58.7 | -1.51 | -2.32 | 0.74 |
| Post launch (all) | 101 | 39.6% | 30.6–49.4 | 3.03 | -1.46 | 1.87 |
| Post launch, excl. top-1 winner | 100 | 39.0% | 30.0–48.8 | 1.92 | -1.50 | 1.54 |

**Is Entry Quality actually filtering trades?** It is monotonic only at the top: excellent PF 3.3 vs good 0.85 vs neutral 1.87; 'good' does NOT beat 'neutral' (p=0.5972). Excellent vs rest p=0.2067 → NOT SUPPORTED (no detectable effect at this n). Post-launch PF is higher than pre-launch but the eras differ in calendar time and n (pre n=17), and the gap shrinks without the top winner → POSSIBLE at best; causal credit is INSUFFICIENT DATA.

## SECTION F — TREND AUDIT

**trend_score buckets (max 25)**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| 0–15 | 13 | 30.8% | -1.96% | 0.62 | -3.65% |
| 15–20 | 39 | 46.2% | 2.60% | 1.78 | -0.99% |
| 20–23 | 33 | 33.3% | 5.39% | 2.57 | -2.21% |
| 23–26 | 33 | 39.4% | 0.81% | 1.19 | -1.55% |

| Group | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF |
|---|---|---|---|---|---|---|
| Max trend (≥24) | 25 | 36.0% | 20.2–55.5 | 1.03 | -1.55 | 1.22 |
| Medium (18–24) | 67 | 40.3% | 29.4–52.3 | 3.87 | -1.61 | 2.24 |
| Low (<18) | 26 | 38.5% | 22.4–57.5 | -0.17 | -1.32 | 0.96 |

| Regime | Trend group | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF |
|---|---|---|---|---|---|---|---|
| risk_on | trend ≥22 | 12 | 41.7% | 19.3–68.0 | -0.08 | -1.42 | 0.99 |
| risk_on | trend <22 | 22 | 18.2% | 7.3–38.5 | -2.27 | -3.73 | 0.39 |
| mixed | trend ≥22 | 31 | 35.5% | 21.1–53.1 | 1.78 | -1.98 | 1.61 |
| mixed | trend <22 | 53 | 49.1% | 36.1–62.1 | 5.22 | -0.95 | 2.31 |

Max vs medium: 36.0% (n=25) vs 40.3% (n=67), p=0.8121. Spearman(trend, return)=-0.019 (p=0.84). Mantel–Haenszel OR controlling for regime = 0.88. Trend ≥22 appears in 27/72 losses (37.5%) vs 16/46 wins. **Do maximum-trend trades outperform? NOT SUPPORTED** (no monotone relation; NOT SUPPORTED (no detectable effect at this n)). **Does trend create false positives?** Trend is satisfied by nearly every published plan (median 20.15/25) so it acts as a gate, not a discriminator — high trend appears in as many losses as wins. **Does it dominate losing trades?** It is present in a large share of losses only because it is present in most trades.

## SECTION G — STRUCTURE AUDIT

| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| FVG used in levels (post-capture trades) | 26/54 | 42.3% / 42.6% | 0.99 | [0.38, 2.55] | 1.0 | 0.0 | NOT SIGNIFICANT |
| Price beyond EMA20/50/200 in trade direction | 88/23 | 39.8% / 30.4% | 1.51 | [0.56, 4.04] | 0.4758 | 0.0045 | NOT SIGNIFICANT |
| structure_score ≥ 9 | 45/73 | 42.2% / 37.0% | 1.25 | [0.58, 2.66] | 0.6978 | 0.002 | NOT SIGNIFICANT |

**structure_score buckets**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| 0–6 | 0 |  |  |  |  |
| 6–9 | 73 | 37.0% | 2.54% | 1.66 | -1.98% |
| 9–12 | 45 | 42.2% | 2.12% | 1.57 | -1.14% |
| 12–20 | 0 |  |  |  |  |

**BOS, CHoCH, Order Blocks: INSUFFICIENT DATA** — not persisted per trade (`market_snapshots` has bos/choch columns, but only for 6 symbols and ends 2026-08-04, before the first trade); order-block detection does not exist in the code. FVG is testable only for post-capture trades (n=80). **Which structures matter?** None demonstrated: FVG p=1.0, EMA-stack p=0.4758, structure_score≥9 p=0.6978. **Zero predictive value?** Consistent with zero for all three at this n (INSUFFICIENT POWER, not proof of no effect).

## SECTION H — MOMENTUM AUDIT

| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| RSI 50–70 | 85/28 | 44.7% / 21.4% | 2.96 | [1.09, 8.05] | 0.0432 | 0.0325 | MEDIUM |
| RSI < 50 | 24/89 | 20.8% / 43.8% | 0.34 | [0.12, 0.98] | 0.0581 | 0.0287 | LOW (suggestive only) |
| RSI 30–49 (chop) | 24/89 | 20.8% / 43.8% | 0.34 | [0.12, 0.98] | 0.0581 | 0.0287 | LOW (suggestive only) |
| RSI ≥ 70 | 4/109 | 25.0% / 39.4% | 0.51 | [0.05, 5.08] | 1.0 | 0.0023 | INSUFFICIENT DATA |
| MACD hist > 0 | 78/15 | 42.3% / 40.0% | 1.1 | [0.36, 3.39] | 1.0 | 0.0002 | NOT SIGNIFICANT |
| ADX ≥ 25 | 56/57 | 37.5% / 40.4% | 0.89 | [0.42, 1.89] | 0.8476 | 0.0006 | NOT SIGNIFICANT |
| ADX ≥ 35 | 33/80 | 30.3% / 42.5% | 0.59 | [0.25, 1.4] | 0.2901 | 0.0095 | NOT SIGNIFICANT |
| StochRSI > 0.8 | 32/81 | 50.0% / 34.6% | 1.89 | [0.82, 4.34] | 0.1403 | 0.0145 | LOW (suggestive only) |
| BB%B > 0.8 | 15/78 | 40.0% / 42.3% | 0.91 | [0.29, 2.8] | 1.0 | 0.0002 | NOT SIGNIFICANT |
| BB%B > 0.95 | 2/91 | 100.0% / 40.7% | 7.27 | [0.34, 155.72] | 0.1732 | 0.0274 | INSUFFICIENT DATA |

**RSI**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| 0–30 | 0 |  |  |  |  |
| 30–40 | 1 | 0.0% | -2.76% | 0.00 | -2.76% |
| 40–50 | 23 | 21.7% | -5.12% | 0.31 | -2.56% |
| 50–60 | 53 | 39.6% | 7.31% | 4.14 | -1.27% |
| 60–70 | 32 | 53.1% | 1.87% | 1.72 | 1.62% |
| 70–100 | 4 | 25.0% | -13.48% | 0.02 | -5.44% |

**ADX**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| 0–20 | 32 | 43.8% | 1.62% | 1.44 | -1.29% |
| 20–35 | 48 | 41.7% | 4.82% | 2.49 | -1.36% |
| 35–50 | 27 | 25.9% | -0.40% | 0.90 | -2.02% |
| 50–200 | 6 | 50.0% | 0.12% | 1.01 | -2.01% |

**StochRSI**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| 0–0.2 | 12 | 41.7% | 7.16% | 7.41 | -0.59% |
| 0.2–0.5 | 33 | 30.3% | -0.43% | 0.89 | -2.21% |
| 0.5–0.8 | 36 | 36.1% | 0.08% | 1.01 | -1.96% |
| 0.8–1.01 | 32 | 50.0% | 6.20% | 3.45 | 0.29% |

**BB %B**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| -1–0.2 | 1 | 0.0% | -1.14% | 0.00 | -1.14% |
| 0.2–0.5 | 14 | 21.4% | -8.20% | 0.04 | -3.49% |
| 0.5–0.8 | 63 | 47.6% | 6.88% | 3.94 | -0.59% |
| 0.8–1.0 | 15 | 40.0% | 0.38% | 1.09 | -2.98% |
| 1.0–5 | 0 |  |  |  |  |

**Overextension thresholds (scan of candidate cut-points, upper tail — win rate at/above vs below; multiple comparisons, so treat as exploratory):**
| Cut | n above/below | Win% above / below | OR | p | Evidence |
|---|---|---|---|---|---|
| RSI ≥ 60 | 36/77 | 50.0% / 33.8% | 1.96 | 0.1467 | POSSIBLE |
| RSI ≥ 65 | 7/106 | 42.9% / 38.7% | 1.19 | 1.0 | INSUFFICIENT DATA |
| RSI ≥ 70 | 4/109 | 25.0% / 39.4% | 0.51 | 1.0 | INSUFFICIENT DATA |
| RSI ≥ 75 | 2/111 | 50.0% / 38.7% | 1.58 | 1.0 | INSUFFICIENT DATA |
| StochRSI ≥ 0.7 | 47/66 | 48.9% / 31.8% | 2.05 | 0.0796 | POSSIBLE |
| StochRSI ≥ 0.8 | 32/81 | 50.0% / 34.6% | 1.89 | 0.1403 | POSSIBLE |
| StochRSI ≥ 0.9 | 17/96 | 52.9% / 36.5% | 1.96 | 0.2803 | NOT SUPPORTED (no detectable effect at this n) |
| BB%B ≥ 0.8 | 15/78 | 40.0% / 42.3% | 0.91 | 1.0 | NOT SUPPORTED (no detectable effect at this n) |
| BB%B ≥ 0.9 | 5/88 | 60.0% / 40.9% | 2.17 | 0.6463 | INSUFFICIENT DATA |
| MFI ≥ 70 | 24/69 | 50.0% / 39.1% | 1.56 | 0.4718 | NOT SUPPORTED (no detectable effect at this n) |
| MFI ≥ 80 | 7/86 | 100.0% / 37.2% | 25.15 | 0.0016 | INSUFFICIENT DATA |

**Finding:** the only split reaching p<0.05 is RSI 50–70 vs the rest (44.7% n=85 vs 21.4% n=28, OR 2.96, p=0.0432 → LIKELY, not CONFIRMED). StochRSI ≥0.7 is POSSIBLE (better, not worse). ADX≥35 is NOT significant. **Overextension:** no evidence that overbought readings hurt — high-RSI/StochRSI/BB/MFI bins do equal or better, but the extreme bins (RSI≥70 n=4, BB>0.95 n=2, MFI>80 n=7) are INSUFFICIENT DATA; the hypothesis 'overbought entries lose' is NOT SUPPORTED. The weak end is low momentum (RSI<50: win 20.8%, n=24, p≈0.06 → POSSIBLE).

## SECTION I — VOLUME AUDIT

| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| CMF > 0 | 65/28 | 41.5% / 42.9% | 0.95 | [0.39, 2.32] | 1.0 | 0.0001 | NOT SIGNIFICANT |
| CMF > 0.1 | 31/62 | 51.6% / 37.1% | 1.81 | [0.76, 4.33] | 0.191 | 0.0138 | NOT SIGNIFICANT |
| volume_score ≥ 8 | 66/52 | 43.9% / 32.7% | 1.61 | [0.76, 3.44] | 0.2559 | 0.0095 | NOT SIGNIFICANT |
| volume_score = 10 | 57/61 | 38.6% / 39.3% | 0.97 | [0.46, 2.03] | 1.0 | 0.0 | NOT SIGNIFICANT |
| funding_score = 10 (uncrowded) | 113/5 | 38.9% / 40.0% | 0.96 | [0.15, 5.96] | 1.0 | 0.0 | INSUFFICIENT DATA |
| MFI > 60 | 45/48 | 51.1% / 33.3% | 2.09 | [0.9, 4.83] | 0.096 | 0.0235 | LOW (suggestive only) |

**CMF**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| -1–-0.1 | 10 | 20.0% | -8.22% | 0.05 | -2.45% |
| -0.1–0 | 18 | 55.6% | 11.62% | 3.99 | 4.30% |
| 0–0.1 | 34 | 32.4% | 2.98% | 1.89 | -1.50% |
| 0.1–0.2 | 16 | 37.5% | 0.26% | 1.09 | -2.35% |
| 0.2–1 | 15 | 66.7% | 6.04% | 7.38 | 5.44% |

**volume_score**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| 0–5 | 5 | 40.0% | 18.59% | 4.83 | -1.27% |
| 5–8 | 47 | 31.9% | 1.18% | 1.29 | -1.98% |
| 8–10 | 9 | 77.8% | 2.86% | 3.68 | 4.11% |
| 10–11 | 57 | 38.6% | 1.87% | 1.47 | -1.64% |

**OBV: INSUFFICIENT DATA** (not stored per trade; obv_slope exists only in the pre-trade market_snapshots). Volume-ratio: only as the aggregate volume_score. **Does volume confirmation improve win rate? NOT SUPPORTED** (volume_score≥8: 43.9% vs 32.7%, p=0.2559). Funding is near-constant (10 for 113/118 trades) → cannot be evaluated. Negative CMF trades did not lose more (see table) — the opposite direction of what the design assumes.

## SECTION J — REGIME AUDIT

| Regime | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | TP1% | TP2% | TP3% | Stop% |
|---|---|---|---|---|---|---|---|---|---|---|
| mixed | 84 | 44.0% | 33.9–54.7 | 3.95 | -1.01 | 2.10 | 51.2 | 45.2 | 14.3 | 56.0 |
| risk_on | 34 | 26.5% | 14.6–43.1 | -1.50 | -3.21 | 0.66 | 32.4 | 26.5 | 5.9 | 73.5 |
| risk_off | 0 | — | — | — | — | — | — | — | — | — |
| trend expansion | 0 | — | — | — | — | — | — | — | — | — |
| mean reversion | 0 | — | — | — | — | — | — | — | — | — |
| panic volatility | 0 | — | — | — | — | — | — | — | — | — |

| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| mixed vs risk_on | 84/34 | 44.0% / 26.5% | 2.19 | [0.91, 5.25] | 0.0964 | 0.0199 | LOW (suggestive only) |

ScanSnapshot regime labels over all scans: {'mixed': 67169, 'risk_on': 14371}. **Only risk_on and mixed have ever been emitted; risk_off, trend expansion, mean reversion and panic volatility have n=0** — INSUFFICIENT DATA, and the engine cannot be judged on regimes it never outputs. risk_on has been WORSE than mixed for trades (win 26.5% vs 44.0%, p=0.0964), the reverse of the naive expectation, but regime is confounded with calendar period (POSSIBLE).

## SECTION K — LONG VS SHORT AUDIT

| Segment | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | TP1% | TP2% | TP3% | Stop% | Avg stop slip% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Long (all) | 98 | 43.9% | 34.5–53.7 | 4.57 | -1.11 | 2.60 | 49.0 | 43.9 | 14.3 | 56.1 | -1.52 |
| Short (all) | 20 | 15.0% | 5.2–36.0 | -8.34 | -3.83 | 0.03 | 30.0 | 20.0 | 0.0 | 85.0 | -8.08 |
| Long, exit NOT in monitoring gap | 57 | 36.8% | 25.5–49.8 | 0.80 | -1.46 | 1.34 | 40.4 | 36.8 | 8.8 | 63.2 | -0.96 |
| Short, exit NOT in monitoring gap | 9 | 33.3% | 12.1–64.6 | -3.04 | -0.99 | 0.16 | 44.4 | 33.3 | 0.0 | 66.7 | -3.25 |
| Short, exit inside gap | 11 | 0.0% | 0.0–25.9 | -12.67 | -8.06 | 0.00 | 18.2 | 9.1 | 0.0 | 100.0 | -10.28 |

**By confidence bucket**
| confidence bucket | Dir | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF |
|---|---|---|---|---|---|---|---|
| <60 | long | 21 | 42.9% | 24.5–63.5 | 8.81 | -1.64 | 3.50 |
| <60 | short | 11 | 18.2% | 5.1–47.7 | -9.67 | -5.00 | 0.04 |
| 60–64 | long | 33 | 54.5% | 38.0–70.2 | 4.39 | 2.53 | 2.82 |
| 60–64 | short | 6 | 0.0% | 0–39.0 | -9.40 | -5.41 | 0.00 |
| 65+ | long | 39 | 35.9% | 22.7–51.6 | 2.81 | -1.07 | 2.00 |
| 65+ | short | 3 | 33.3% | 6.1–79.2 | -1.33 | -2.04 | 0.15 |

**By regime**
| regime | Dir | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF |
|---|---|---|---|---|---|---|---|
| risk_on | long | 34 | 26.5% | 14.6–43.1 | -1.50 | -3.21 | 0.66 |
| mixed | long | 64 | 53.1% | 41.1–64.8 | 7.79 | 2.58 | 4.87 |
| mixed | short | 20 | 15.0% | 5.2–36.0 | -8.34 | -3.83 | 0.03 |

**By entry quality**
| entry quality | Dir | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF |
|---|---|---|---|---|---|---|---|
| excellent | long | 15 | 60.0% | 35.7–80.2 | 8.54 | 6.26 | 8.59 |
| excellent | short | 4 | 25.0% | 4.6–69.9 | -6.24 | -2.30 | 0.10 |
| good | long | 14 | 28.6% | 11.7–54.6 | 1.15 | -2.15 | 1.45 |
| good | short | 6 | 33.3% | 9.7–70.0 | -4.29 | -1.83 | 0.08 |
| neutral | long | 52 | 46.2% | 33.3–59.5 | 6.33 | -0.80 | 3.56 |
| neutral | short | 10 | 0.0% | 0–27.8 | -11.60 | -6.53 | 0.00 |
| none | long | 17 | 35.3% | 17.3–58.7 | -1.51 | -2.32 | 0.74 |

**By timeframe**
| timeframe | Dir | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF |
|---|---|---|---|---|---|---|---|
| swing | long | 57 | 36.8% | 25.5–49.8 | 5.10 | -1.46 | 3.17 |
| swing | short | 6 | 16.7% | 3.0–56.4 | -7.99 | -4.92 | 0.03 |
| intraday | long | 41 | 53.7% | 38.7–67.9 | 3.82 | 1.67 | 2.08 |
| intraday | short | 14 | 14.3% | 4.0–39.9 | -8.48 | -3.01 | 0.03 |

**Shorts by symbol**
| Symbol | n | Win | Ret list % | Exit in gap? |
|---|---|---|---|---|
| ALLOUSDT | 1 | 0 | -2.8 | Y |
| CRCLUSDT | 1 | 0 | -1.0 | N |
| DOGEUSDT | 2 | 0 | -20.3, -15.8 | Y, Y |
| DRAMUSDT | 1 | 0 | -3.4 | Y |
| ETHUSDT | 1 | 0 | -26.7 | Y |
| HYPEUSDT | 1 | 0 | -2.6 | N |
| PUMPUSDT | 1 | 0 | -23.3 | N |
| RKLBUSDT | 1 | 0 | -2.7 | N |
| SKHYNIXUSDT | 1 | 0 | -5.0 | Y |
| SNDKUSDT | 1 | 0 | -4.3 | Y |
| SNXXUSDT | 2 | 0 | -5.5, -8.1 | Y, Y |
| SOLUSDT | 1 | 0 | -2.0 | N |
| SOXSUSDT | 1 | 1 | 0.7 | N |
| SUIUSDT | 1 | 0 | -1.0 | N |
| WLDUSDT | 1 | 0 | -18.8 | Y |
| XAGUSDT | 1 | 1 | 2.9 | N |
| XAUUSDT | 1 | 1 | 1.5 | N |
| ZECUSDT | 1 | 0 | -28.8 | Y |

| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| short vs long (all) | 20/98 | 15.0% / 43.9% | 0.23 | [0.06, 0.82] | 0.022 | 0.0398 | MEDIUM |
| short vs long (exit not in gap) | 9/57 | 33.3% / 36.8% | 0.86 | [0.19, 3.79] | 1.0 | 0.0005 | INSUFFICIENT DATA |

**Are shorts fundamentally broken?** Headline: 15.0% win, PF 0.03 (n=20; p=0.022 vs longs → LIKELY). But 11/20 shorts exited inside a monitoring gap and 11/11 of those lost (avg -12.67%); with those removed, shorts win 33.3% (n=9) vs longs 36.8% (p=1.0). Shorts exist only in the `mixed` regime and mostly in a narrow time window, so 'broken only in certain regimes' is UNTESTABLE (no short in risk_on). **Should shorts be disabled? Not on this evidence — INSUFFICIENT DATA** (the failure is confounded with downtime; a hard disable cannot be justified until ≥30 shorts are observed with continuous monitoring).

## SECTION L — TIMEFRAME AUDIT

| Timeframe class | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | Median hold h |
|---|---|---|---|---|---|---|---|
| intraday | 55 | 43.6% | 31.4–56.7 | 0.69 | -1.64 | 1.14 | 42.7 |
| swing | 63 | 34.9% | 24.3–47.2 | 3.86 | -1.57 | 2.32 | 23.9 |

| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| BTC trend agrees with trade direction | 50/43 | 32.0% / 53.5% | 0.41 | [0.18, 0.95] | 0.0572 | 0.0342 | LOW (suggestive only) |
| swing vs intraday | 63/55 | 34.9% / 43.6% | 0.69 | [0.33, 1.46] | 0.3507 | 0.0057 | NOT SIGNIFICANT |
| reasoning text asserts timeframe alignment (text proxy) | 87/31 | 39.1% / 38.7% | 1.02 | [0.44, 2.36] | 1.0 | 0.0 | NOT SIGNIFICANT |

**1h / 4h / 1d alignment as structured fields: INSUFFICIENT DATA** — no per-timeframe trend is stored on trades. Available proxies: BTC-trend/direction agreement, swing-vs-intraday label, and a regex over Claude's free-text (a proxy for what was *claimed*, not computed). None separates outcomes at conventional significance (BTC agreement p=0.0572; text-proxy p=1.0) → no combination is shown to outperform.

## SECTION M — SYMBOL RELIABILITY AUDIT

Bayesian shrinkage (Beta prior strength 10 toward pooled win rate 39.0%). Tier rules (report-defined): **Trusted** n≥5 and reliability≥55; **Watch** default and any symbol with n<3 (thin sample, cannot be promoted or demoted); **Caution** n≥3 and reliability 33–45; **Avoid** n≥3 and (0 wins or reliability<33). Reliability uses all data including each trade itself (hindsight).
| Symbol | n | Wins | Win% | Avg ret | PF | Reliability | Tier |
|---|---|---|---|---|---|---|---|
| NVDAUSDT | 2 | 2 | 100.0% | 2.85 | — | 49.2 | Watch (n<3) |
| NEARUSDT | 2 | 2 | 100.0% | 63.82 | — | 49.2 | Watch (n<3) |
| BTWUSDT | 2 | 2 | 100.0% | 17.25 | — | 49.2 | Watch (n<3) |
| SOXSUSDT | 2 | 2 | 100.0% | 4.11 | — | 49.2 | Watch (n<3) |
| CRCLUSDT | 3 | 2 | 66.7% | 3.32 | 11.03 | 45.4 | Watch |
| SAMSUNGUSDT | 3 | 2 | 66.7% | 2.43 | 2.60 | 45.4 | Watch |
| LINKUSDT | 3 | 2 | 66.7% | 9.29 | 6.08 | 45.4 | Watch |
| QQQUSDT | 1 | 1 | 100.0% | 1.67 | — | 44.5 | Watch (n<3) |
| VELVETUSDT | 1 | 1 | 100.0% | 27.28 | — | 44.5 | Watch (n<3) |
| APRUSDT | 1 | 1 | 100.0% | 19.04 | — | 44.5 | Watch (n<3) |
| FILUSDT | 1 | 1 | 100.0% | 14.90 | — | 44.5 | Watch (n<3) |
| RIVERUSDT | 1 | 1 | 100.0% | 18.82 | — | 44.5 | Watch (n<3) |
| XRPUSDT | 1 | 1 | 100.0% | 4.61 | — | 44.5 | Watch (n<3) |
| UNIUSDT | 1 | 1 | 100.0% | 52.19 | — | 44.5 | Watch (n<3) |
| ADAUSDT | 1 | 1 | 100.0% | 4.95 | — | 44.5 | Watch (n<3) |
| ZECUSDT | 4 | 2 | 50.0% | 12.34 | 2.49 | 42.1 | Caution |
| HYPEUSDT | 4 | 2 | 50.0% | 10.02 | 10.56 | 42.1 | Caution |
| SKHYUSDT | 4 | 2 | 50.0% | 2.46 | 3.19 | 42.1 | Caution |
| CLUSDT | 4 | 2 | 50.0% | 2.38 | 2.58 | 42.1 | Caution |
| EWYUSDT | 2 | 1 | 50.0% | -0.51 | 0.72 | 40.8 | Watch (n<3) |
| CYSUSDT | 2 | 1 | 50.0% | 6.79 | 3.23 | 40.8 | Watch (n<3) |
| ACEUSDT | 2 | 1 | 50.0% | 15.08 | 4.12 | 40.8 | Watch (n<3) |
| PAXGUSDT | 2 | 1 | 50.0% | 0.38 | 2.29 | 40.8 | Watch (n<3) |
| 1000PEPEUSDT | 2 | 1 | 50.0% | 12.47 | 4.34 | 40.8 | Watch (n<3) |
| XAUUSDT | 2 | 1 | 50.0% | 0.48 | 2.64 | 40.8 | Watch (n<3) |
| MUUSDT | 2 | 1 | 50.0% | -1.61 | 0.44 | 40.8 | Watch (n<3) |
| WLDUSDT | 2 | 1 | 50.0% | -5.25 | 0.44 | 40.8 | Watch (n<3) |
| SNDKUSDT | 3 | 1 | 33.3% | -1.68 | 0.55 | 37.7 | Caution |
| SKHYNIXUSDT | 3 | 1 | 33.3% | -0.07 | 0.97 | 37.7 | Caution |
| XAGUSDT | 3 | 1 | 33.3% | -0.81 | 0.55 | 37.7 | Caution |
| BNBUSDT | 3 | 1 | 33.3% | 1.61 | 3.25 | 37.7 | Caution |
| PUMPUSDT | 3 | 1 | 33.3% | 4.64 | 1.55 | 37.7 | Caution |
| BEATUSDT | 1 | 0 | 0.0% | -9.50 | 0.00 | 35.4 | Watch (n<3) |
| BICOUSDT | 1 | 0 | 0.0% | -44.42 | 0.00 | 35.4 | Watch (n<3) |
| BTCUSDT | 1 | 0 | 0.0% | -1.61 | 0.00 | 35.4 | Watch (n<3) |
| RKLBUSDT | 1 | 0 | 0.0% | -2.66 | 0.00 | 35.4 | Watch (n<3) |
| HOLOUSDT | 1 | 0 | 0.0% | -7.17 | 0.00 | 35.4 | Watch (n<3) |
| LITEUSDT | 1 | 0 | 0.0% | -5.12 | 0.00 | 35.4 | Watch (n<3) |
| SPORTFUNUSDT | 1 | 0 | 0.0% | -6.12 | 0.00 | 35.4 | Watch (n<3) |
| ALLOUSDT | 1 | 0 | 0.0% | -2.76 | 0.00 | 35.4 | Watch (n<3) |
| TRUMPUSDT | 1 | 0 | 0.0% | -20.95 | 0.00 | 35.4 | Watch (n<3) |
| HEMIUSDT | 1 | 0 | 0.0% | -8.62 | 0.00 | 35.4 | Watch (n<3) |
| ENAUSDT | 1 | 0 | 0.0% | -4.10 | 0.00 | 35.4 | Watch (n<3) |
| LABUSDT | 1 | 0 | 0.0% | -7.36 | 0.00 | 35.4 | Watch (n<3) |
| USELESSUSDT | 1 | 0 | 0.0% | -4.71 | 0.00 | 35.4 | Watch (n<3) |
| FLOCKUSDT | 1 | 0 | 0.0% | -5.38 | 0.00 | 35.4 | Watch (n<3) |
| DRAMUSDT | 4 | 1 | 25.0% | -2.53 | 0.22 | 35.0 | Caution |
| SPCXUSDT | 4 | 1 | 25.0% | -0.07 | 0.94 | 35.0 | Caution |
| SOLUSDT | 5 | 1 | 20.0% | 1.80 | 1.75 | 32.7 | Avoid |
| SNXXUSDT | 2 | 0 | 0.0% | -6.80 | 0.00 | 32.5 | Watch (n<3) |
| BZUSDT | 2 | 0 | 0.0% | -3.35 | 0.00 | 32.5 | Watch (n<3) |
| SUIUSDT | 2 | 0 | 0.0% | -3.46 | 0.00 | 32.5 | Watch (n<3) |
| MOVRUSDT | 2 | 0 | 0.0% | -9.47 | 0.00 | 32.5 | Watch (n<3) |
| DOGEUSDT | 3 | 0 | 0.0% | -12.88 | 0.00 | 30.0 | Avoid |
| MSTRUSDT | 3 | 0 | 0.0% | -3.39 | 0.00 | 30.0 | Avoid |
| ETHUSDT | 5 | 0 | 0.0% | -6.50 | 0.00 | 26.0 | Avoid |

Symbols: 56; tier counts {'Watch (n<3)': 38, 'Caution': 11, 'Watch': 3, 'Avoid': 4}; symbols with n≥5: 2. Spearman(hindsight reliability, return)=0.527 is hindsight-inflated and NOT evidence of predictiveness. **Out-of-sample test:** none possible with this n per symbol → INSUFFICIENT DATA.

## SECTION N — HISTORICAL SIMILARITY AUDIT

| Group | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF |
|---|---|---|---|---|---|---|
| History present | 16 | 25.0% | 10.2–49.5 | -0.67 | -1.30 | 0.78 |
| History missing | 102 | 41.2% | 32.1–50.9 | 2.86 | -1.70 | 1.72 |

| History said | Won | Lost |
|---|---|---|
| ≥50% win | 3 | 10 |
| <50% win | 1 | 2 |

Coverage 16/118; symbols covered 6/56. history_score values: {-3.0: 2, -1.5: 1, 0.0: 102, 1.5: 3, 3.0: 2, 4.5: 2, 6.0: 1, 7.5: 2, 9.0: 1, 10.5: 1, 12.0: 1} (0 when history is absent or sample<20 — i.e. missing history is scored neutral). **Did history improve accuracy?** No: with history 25.0% vs without 41.2% (p=0.2767); history said ≥50% on 13 trades and 10 lost → the analogue win-rate was over-optimistic (NOT SUPPORTED). Confounded with the few majors that have history. **Did neutral scoring hurt when history was missing?** No: trades WITHOUT history did better; no evidence that treating absence as neutral is harmful (NOT SUPPORTED).

## SECTION O — EXPECTED VALUE AUDIT

Stored EV (issued-time) exists for n=28 closed trades; leave-one-out retrospective EV for the full sample (formula identical to the engine's: P(TP1)·reward_TP1/risk − P(stop before TP1)).

**Stored EV**
| EV bucket | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | Avg realized R |
|---|---|---|---|---|---|---|---|
| <0 | 14 | 57.1% | 32.6–78.6 | 10.88 | 3.07 | 4.14 | 0.97 |
| 0–1R | 13 | 23.1% | 8.2–50.3 | 4.58 | -2.15 | 2.23 | 1.63 |
| 1–2R | 1 | 100.0% | 20.7–100 | 2.93 | 2.93 | — | 12.61 |
| 2R+ | 0 |  |  |  |  |  |  |

**Retrospective LOO EV**
| EV bucket | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | Avg realized R |
|---|---|---|---|---|---|---|---|
| <0 | 61 | 47.5% | 35.5–59.8 | 4.61 | -1.01 | 2.20 | 0.41 |
| 0–1R | 29 | 31.0% | 17.3–49.2 | 1.47 | -1.57 | 1.47 | 0.67 |
| 1–2R | 3 | 33.3% | 6.1–79.2 | -0.32 | -0.95 | 0.75 | 3.23 |
| 2R+ | 0 |  |  |  |  |  |  |

Spearman(retro EV, realized R)=-0.103 (p=0.327, n=93); stored EV vs realized R: -0.003 (p=0.989, n=28). **Does EV correlate with profit? NOT SUPPORTED** — the calibration table shows no monotone rise in realized R with predicted EV; negative-EV bucket outcomes are not worse. EV is dominated by the reward/risk ratio because P(TP1) is pooled.

## SECTION P — TRADE MANAGER AUDIT (TP CONTINUATION MATRIX)

| Transition (trades that reached TP1, n=54) | Probability | Wilson CI |
|---|---|---|
| P(TP2 | TP1) | 85.2% (46/54) | 73.4–92.3 |
| P(TP3 | TP2) | 30.4% (14/46) | 19.1–44.8 |
| P(final loss | TP1) | 16.7% | 9.0–28.7 |
| P(returned to entry after TP1) | 17.9% (n=39) |  |
| P(returned to stop after TP1) | 17.0% (n=53) |  |

Average continuation after TP1 (best excursion vs entry): 14.205% ; average pullback: 3.308%.
**By direction**
| direction | n(TP1) | P(TP2|TP1) | P(TP3|TP2) | P(final loss) |
|---|---|---|---|---|
| long | 48 | 89.6% | 32.6% (n=43) | 10.4% |
| short | 6 | 50.0% | 0.0% (n=3) | 66.7% |

**By regime**
| regime | n(TP1) | P(TP2|TP1) | P(TP3|TP2) | P(final loss) |
|---|---|---|---|---|
| mixed | 43 | 86.0% | 32.4% (n=37) | 16.3% |
| risk_on | 11 | 81.8% | 22.2% (n=9) | 18.2% |

**By confidence**
| confidence | n(TP1) | P(TP2|TP1) | P(TP3|TP2) | P(final loss) |
|---|---|---|---|---|
| 60–64 | 22 | 86.4% | 42.1% (n=19) | 18.2% |
| 65+ | 15 | 93.3% | 35.7% (n=14) | 6.7% |
| <60 | 15 | 73.3% | 9.1% (n=11) | 26.7% |

**By entry quality**
| entry quality | n(TP1) | P(TP2|TP1) | P(TP3|TP2) | P(final loss) |
|---|---|---|---|---|
| excellent | 11 | 90.9% | 50.0% (n=10) | 9.1% |
| good | 8 | 75.0% | 33.3% (n=6) | 37.5% |
| neutral | 28 | 85.7% | 25.0% (n=24) | 14.3% |

Counterfactual policies (assumptions: fills at TP price, no fees; breakeven-stop bounded by optimistic/pessimistic path handling): see below.
| Policy | n | Sum ret% | Avg | PF | Median |
|---|---|---|---|---|---|
| Actual | 118 | 280.8 | 2.38 | 1.62 | -1.59 |
| Exit at TP1 | 118 | -203.6 | -1.725 | 0.42 | -1.006 |
| Exit at TP2 (if TP3 defined) | 118 | 159.6 | 1.352 | 1.37 | -1.559 |
| Breakeven stop after TP1 (optimistic) | 118 | 361.5 | 3.064 | 2.03 | -1.006 |
| Breakeven stop after TP1 (pessimistic) | 118 | 131.0 | 1.111 | 1.37 | -1.006 |

Trade-Manager decisions actually logged in PredictionSnapshot (real probability-driven decisions exist only post-2026-09-12):
| Stage | Decision | Snapshots |
|---|---|---|
| OPEN | HOLD | 12439 |
| PRE_ENTRY | HOLD | 7016 |
| TP1_REACHED | HOLD | 1669 |
| TP1_REACHED | HOLD_FOR_TP2 | 1331 |
| TP2_REACHED | HOLD | 357 |
| TP2_REACHED | MOVE_STOP_TO_TP1 | 239 |
| EXITED | STOPPED | 57 |
| EXITED | TAKE_PROFIT | 43 |
| EXITED | INVALIDATED | 7 |

**Conclusion:** exiting early at TP1 or TP2 is clearly worse than holding (CONFIRMED by arithmetic on n=118); a breakeven stop's benefit is INSUFFICIENT DATA (bounds straddle actual).

## SECTION Q — FAILURE PATTERN ENGINE AUDIT

| Lifecycle (all losses, n=72) | n | % of losses | Avg ret | Total cost % | % of total loss |
|---|---|---|---|---|---|
| immediate_reversal | 57 | 79.2% | -5.78 | -329.6 | 73.1% |
| reached_tp1_then_stopped | 8 | 11.1% | -10.12 | -81.0 | 18.0% |
| some_favorable_move_then_stopped | 6 | 8.3% | -3.60 | -21.6 | 4.8% |
| hit_tp2_then_reversed | 1 | 1.4% | -18.79 | -18.8 | 4.2% |

Risk tags on losses (multi-label): {'no_historical_analogue': 60, 'weak_structure': 46, 'scanner_outage_corrupted': 30, 'rsi_chop_zone': 19, 'short_direction': 17}
| Requested pattern | n | Status |
|---|---|---|
| Immediate reversal | 57 | measured |
| TP1 then stop | 8 | measured |
| TP2 then reverse | 1 | measured |
| Slow bleed (loss held >72h, MFE<1%) | 14 | proxy |
| Perfect trend (win with MAE ≥ −2%) | 43 | proxy (wins) |
| Late breakout / liquidity sweep / trend exhaustion / false breakout / distribution reversal | — | INSUFFICIENT DATA (no per-trade labels; not computed) |

**Cost ranking:** immediate reversals dominate both frequency and cost — CONFIRMED (facts). Causes behind them are not identifiable from stored fields.

## SECTION R — RED FLAG AUDIT

| Flag | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | Win% without | p | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| rsi_chop_30_49 | 24 | 20.8% | 9.2–40.5 | -5.02 | -2.61 | 0.30 | 43.6% | 0.0595 | POSSIBLE |
| weak_structure | 73 | 37.0% | 26.8–48.5 | 2.54 | -1.98 | 1.66 | 42.2% | 0.6978 | NOT SUPPORTED (no detectable effect at this n) |
| no_history | 102 | 41.2% | 32.1–50.9 | 2.86 | -1.70 | 1.72 | 25.0% | 0.2767 | NOT SUPPORTED (no detectable effect at this n) |
| negative_cmf | 28 | 42.9% | 26.5–60.9 | 4.53 | -1.14 | 1.81 | 37.8% | 0.6618 | NOT SUPPORTED (no detectable effect at this n) |
| mfi_over_80 | 7 | 100.0% | 64.6–100 | 4.16 | 2.83 | — | 35.1% | 0.001 | INSUFFICIENT DATA |
| high_atr_extension | 2 | 50.0% | 9.5–90.5 | -21.53 | -21.53 | 0.03 | 38.8% | 1.0 | INSUFFICIENT DATA |
| risk_penalty_applied | 25 | 28.0% | 14.3–47.6 | -0.26 | -4.95 | 0.96 | 41.9% | 0.252 | NOT SUPPORTED (no detectable effect at this n) |
| liquidity_stress | 2 | 0.0% | 0–65.8 | -7.11 | -7.11 | 0.00 | 39.7% | 0.5202 | INSUFFICIENT DATA |
| funding_elevated | 5 | 40.0% | 11.8–76.9 | 3.63 | -2.02 | 2.11 | 38.9% | 1.0 | INSUFFICIENT DATA |
| short_direction | 20 | 15.0% | 5.2–36.0 | -8.34 | -3.83 | 0.03 | 43.9% | 0.022 | LIKELY |
| outage_exit | 52 | 42.3% | 29.9–55.8 | 5.05 | -2.87 | 1.93 | 36.4% | 0.5706 | NOT SUPPORTED (no detectable effect at this n) |

Stored `red_flags` (post-2026-09-?? trades only): 28 trades, tally {'no_historical_analogue': 23, 'weak_structure': 21, 'rsi_chop_zone': 10} (too few to evaluate).
**Which matter?** Only `short_direction` (p≈0.04, confounded by downtime) and the RSI 30–49 chop zone (p≈0.09) are even suggestive; `mfi_over_80` looks 'positive' (n=7) but is INSUFFICIENT DATA. **Should become warnings:** RSI-chop (POSSIBLE) and short-direction (POSSIBLE) as soft warnings only; none justify a score change.

## SECTION S — DECISION AUDIT (CHECKLIST REPLAY)

| Checklist item (FAILED) | Failed in losses | Failed in wins | Win% when failed | Win% when passed | Fisher p |
|---|---|---|---|---|---|
| history | 62/72 (86.1%) | 43/46 (93.5%) | 41.0% (n=105) | 23.1% (n=13) | 0.2459 |
| structure | 46/72 (63.9%) | 27/46 (58.7%) | 37.0% (n=73) | 42.2% (n=45) | 0.6978 |
| trend | 9/72 (12.5%) | 4/46 (8.7%) | 30.8% (n=13) | 40.0% (n=105) | 0.7642 |
| volume | 3/72 (4.2%) | 2/46 (4.3%) | 40.0% (n=5) | 38.9% (n=113) | 1.0 |
| funding | 2/72 (2.8%) | 0/46 (0.0%) | 0.0% (n=2) | 39.7% (n=116) | 0.5202 |
| risk | 0/72 (0.0%) | 0/46 (0.0%) | — | 39.0% (n=118) | — |
| regime | 0/72 (0.0%) | 0/46 (0.0%) | — | 39.0% (n=118) | — |

Failure-frequency chart (share of losses failing each check):
```
history    ████████████████████████       86.1%
structure  ██████████████████             63.9%
trend      ███                            12.5%
volume     █                               4.2%
funding                                    2.8%
risk                                       0.0%
regime                                     0.0%
```
Number of failed checks per trade: {0: 3, 1: 41, 2: 65, 3: 9}. **Checklist items that fail most often (history — which fails by construction whenever no analogue exists — then structure) fail equally often in wins — they do not discriminate (NOT SUPPORTED as filters).** Regime/trend/funding/risk checks almost never fail (constant → no information).

## SECTION T — SCAN SNAPSHOT AUDIT (REJECTIONS AND WHAT HAPPENED AFTER)

| Rejection category | Scan rows | % of all |
|---|---|---|
| published/active (no rejection) | 67402 | 82.7% |
| no_trade (direction gate) | 5962 | 7.3% |
| rank cutoff (outside top 6) | 4551 | 5.6% |
| exhausted | 3086 | 3.8% |
| late | 539 | 0.7% |

Raw reason strings (top 8): {'none': 67402, 'no_trade: deterministic direction gate not met (score below threshold,': 5962, 'no_trade: entry_quality=exhausted overrode an otherwise-directional se': 3086, 'entry_quality=late — setup direction stands, but a new/refreshed plan ': 539, 'rank 9 outside top 6 candidates this cycle': 268, 'rank 10 outside top 6 candidates this cycle': 224, 'rank 20 outside top 6 candidates this cycle': 219, 'rank 21 outside top 6 candidates this cycle': 219}. Avoid-grade plans: 48 (`rejected_avoid`).
| Category (directional scans only) | Directional rows | +1h | +4h | +24h | +72h |
|---|---|---|---|---|---|
| published/active (no rejection) | 40021 | n=17325: avg 0.06% / fav 50% | n=13911: avg 0.37% / fav 52% | n=5578: avg 1.69% / fav 62% | n=1584: avg 13.78% / fav 78% |
| no_trade (direction gate) | 0 | n=0 | n=0 | n=0 | n=0 |
| rank cutoff (outside top 6) | 4551 | n=13: avg 0.53% / fav 69% | n=11: avg -0.08% / fav 36% | n=4: avg -15.62% / fav 25% | n=2: avg -26.46% / fav 50% |
| exhausted | 0 | n=0 | n=0 | n=0 | n=0 |
| late | 539 | n=3: avg -0.48% / fav 33% | n=2: avg -0.38% / fav 50% | n=2: avg 0.51% / fav 50% | n=0 |

**Reading the table:** the ‘published/active’ row is survivorship-biased (rows only appear at long horizons if their plan stayed tracked and the price series is contiguous), so its +24h/+72h averages must not be read as a market baseline; cells with n<10 are INSUFFICIENT DATA. **Critical limitation:** ScanSnapshot stores no price and `market_snapshots` ends before the first scan, so forward returns exist only where a tracked TradeOutcome on the same symbol had PredictionSnapshot prices (a small, selection-biased, highly autocorrelated subset; n shown per cell). `exhausted` scans have direction overwritten to no_trade, so directional outcomes are unrecoverable. **Missed-opportunity totals are INSUFFICIENT DATA**; the recorder for this exists but is not wired into the scanner (0 rows in `rejected_opportunity_outcomes`). I do not report a missed-profit estimate because it would be invented.

## SECTION U — MONITORING / INFRASTRUCTURE AUDIT

| Metric | Value |
|---|---|
| Distinct snapshot cycles | 2115 |
| Span (days) | 49.8 |
| Gaps >10 min | 100 |
| Time inside gaps (days) | 41.8 |
| Scanner uptime | 16.1% |

| Largest gaps: start (UTC) | End (UTC) | Hours | Closed trades that exited inside |
|---|---|---|---|
| 2026-09-14 19:47 | 2026-09-25 20:45 | 265.0 | 12 |
| 2026-08-21 10:45 | 2026-08-28 12:24 | 169.6 | 4 |
| 2026-09-06 07:24 | 2026-09-12 06:56 | 143.5 | 3 |
| 2026-08-16 13:24 | 2026-08-21 07:40 | 114.3 | 11 |
| 2026-08-29 14:24 | 2026-09-02 18:59 | 100.6 | 6 |
| 2026-09-03 14:04 | 2026-09-06 06:22 | 64.3 | 1 |
| 2026-08-10 06:03 | 2026-08-11 07:11 | 25.1 | 3 |
| 2026-08-14 12:40 | 2026-08-15 13:13 | 24.5 | 1 |
| 2026-08-09 05:57 | 2026-08-10 05:12 | 23.3 | 2 |
| 2026-08-08 10:36 | 2026-08-09 04:56 | 18.3 | 0 |

| Impact | Value |
|---|---|
| Closed trades open during ≥1 gap | 83/118 (70.3%) |
| Closed trades whose EXIT fell inside a gap | 52 |
| Stop-exit slippage inside gaps: n / avg / worst | 25 / -6.05% / -27.24% |
| Stop-exit slippage in uptime: n / avg / worst | 35 / -1.29% / -15.84% |
| Estimated loss attributable to downtime (sum of slippage in gaps beyond the uptime median slippage of -0.20%) | -146.3 percentage-points across 25 stop exits |

| Loss attribution | n | Sum ret% | Avg ret% | % of total loss |
|---|---|---|---|---|
| Exit inside gap (infrastructure-contaminated) | 30 | -283.4 | -9.45 | 62.8% |
| Exit during uptime (strategy) | 42 | -167.6 | -3.99 | 37.2% |

**Separation of strategy vs infrastructure:** slippage-in-gap explains an estimated -146.3pp of loss (a lower bound on damage, since it excludes losses that gaps allowed to deepen without a stop being recorded); 30/72 losses carry 62.8% of loss magnitude. Downtime also inflates wins (22/46 wins exited in a gap; avg 24.82% vs 7.74% otherwise), so the net effect on PF cannot be isolated. Uptime ex-gap trades: PF 1.11 (n=66). Evidence: CONFIRMED that monitoring is unreliable; net P&L effect INSUFFICIENT DATA.

## SECTION V — PREDICTION VERSION AUDIT

| Version | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | PF ex-best | TP1% | Stop% | Avg stop slip% |
|---|---|---|---|---|---|---|---|---|---|---|
| V0 pre entry-quality (<2026-08-10 06:07) | 17 | 35.3% | 17.3–58.7 | -1.51 | -2.32 | 0.74 | 0.33 | 41.20 | 64.70 | -4.85 |
| V1 entry-quality live, pre-EV | 73 | 38.4% | 28.1–49.8 | 1.25 | -1.64 | 1.36 | 1.18 | 42.50 | 61.60 | -3.10 |
| V2 EV + Trade Manager + metadata live (≥2026-09-12 06:56) | 28 | 42.9% | 26.5–60.9 | 7.67 | -1.00 | 3.21 | 2.04 | 57.10 | 57.10 | -3.62 |

| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| post-EQ vs pre-EQ | 101/17 | 39.6% / 35.3% | 1.2 | [0.41, 3.51] | 0.7946 | 0.0007 | NOT SIGNIFICANT |
| post-EV vs earlier | 28/90 | 42.9% / 37.8% | 1.24 | [0.52, 2.92] | 0.6618 | 0.0014 | NOT SIGNIFICANT |

Entry-quality launch, EV, Trade Manager and metadata: EV/Trade-Manager/metadata shipped together (first stored EV 2026-09-12 06:56), so they cannot be separated. Differences are between calendar windows and market conditions and are NOT attributable to the features. Post-EQ vs pre-EQ win rate p=0.7946, post-EV vs earlier p=0.6618 → NOT SUPPORTED (no detectable effect at this n). The V2 PF is dominated by a single trade (PF ex-best shown). Evidence: INSUFFICIENT DATA to credit any release.

## SECTION W — FEATURE IMPORTANCE (NO RETRAINING, LOGISTIC/ODDS ONLY)

Univariate: per-1-SD logistic odds ratio with bootstrap 95% CI (400×) on win/loss, plus a joint standardised model with look-ahead-safe features (reliability uses only trades already closed before entry; the EV column is a pooled leave-one-out estimate, whose bias is ~1/n and therefore negligible). A first attempt used per-symbol leave-one-out reliability; it is NOT used because LOO is mechanically anti-correlated with a trade's own outcome (removing a win lowers the score) and produced a spurious negative odds ratio. This is *measurement of the historical outcomes*, not model training for production.
| Feature | n | OR per +1 SD | Bootstrap 95% CI | Evidence |
|---|---|---|---|---|
| trend_score | 118 | 0.97 | [0.66, 1.41] | NOT SUPPORTED (Spearman vs ret -0.02, p=0.84) |
| momentum_score | 118 | 1.07 | [0.75, 1.71] | NOT SUPPORTED (Spearman vs ret -0.09, p=0.34) |
| structure_score | 118 | 1.11 | [0.76, 1.66] | NOT SUPPORTED (Spearman vs ret 0.06, p=0.49) |
| volume_score | 118 | 1.09 | [0.76, 1.58] | NOT SUPPORTED (Spearman vs ret -0.01, p=0.92) |
| regime (mixed=1) | 118 | 1.43 | [0.94, 2.18] | NOT SUPPORTED (Spearman vs ret 0.19, p=0.04) |
| entry_quality (0/1/2) | 101 | 1.17 | [0.73, 1.70] | NOT SUPPORTED (Spearman vs ret 0.09, p=0.38) |
| confidence | 113 | 0.98 | [0.66, 1.35] | NOT SUPPORTED (Spearman vs ret 0.09, p=0.32) |
| history present | 118 | 0.78 | [0.44, 1.19] | NOT SUPPORTED (Spearman vs ret 0.02, p=0.81) |
| reliability (prior-trades only) | 118 | 0.84 | [0.56, 1.19] | NOT SUPPORTED (Spearman vs ret -0.13, p=0.17) |
| EV (retro LOO) | 93 | 0.67 | [0.26, 1.04] | NOT SUPPORTED (Spearman vs ret -0.14, p=0.19) |
| direction (short=1) | 118 | 0.57 | [0.04, 0.84] | LIKELY (Spearman vs ret -0.30, p=0.00) |
| RSI 4h | 113 | 1.39 | [0.95, 2.35] | NOT SUPPORTED (Spearman vs ret 0.09, p=0.34) |

Joint model (9 features, n=113): cross-validated AUC 0.635 ± 0.083 (0.5 = no skill). Features with a CI excluding 0 univariately: ['direction (short=1)']. **Conclusion:** no feature is CONFIRMED (a CI excluding 0 here is 'LIKELY' at best, clustered trades make CIs optimistic). Out-of-sample AUC 0.635 is modest (>0.6), driven mainly by direction (which is confounded with downtime, §K/§U); the score components themselves carry no detectable signal (§F,G,H,I).

## SECTION X — WHAT SHOULD CHANGE? (ROI-RANKED)

Ranking = (evidence strength × size of the affected P&L/data-quality lever) ÷ (risk × complexity). Nothing in Phase 2+ alters scoring, decision, regime, prompt or ML weights unless explicitly marked and evidence exists (none currently does).
| Rank | Change | Bucket | Expected improvement | Evidence (§) | n | Risk | Complexity |
|---|---|---|---|---|---|---|---|
| 1 | Run scanner as supervised always-on service (auto-restart, heartbeat alert) | Immediate (ops, no code in engine) | Removes gap exposure on 70.3% of trades; largest single data-quality gain; P&L effect not isolatable | §U CONFIRMED | 118 | Very low | Low |
| 2 | Report n, CI, median and ex-top-3 PF on every KPI | Immediate (analytics only) | Stops over-reading a right-tail-driven PF | §A: PF 1.62→1.15 | 118 | None | Low |
| 3 | Show calibrated confidence ± interval; label raw confidence 'score, not probability' | Immediate (display) | Fixes ~25pp overstatement | §C: Brier 0.298 > base 0.2378 | 113 | None | Low |
| 4 | Persist BOS/CHoCH/sweep/OBV/timeframe-trend booleans per trade at issuance | Phase 2 (additive code, no scoring change) | Makes §G/§L answerable at n=200 | §G/§L INSUFFICIENT DATA | 0 | Low | Medium |
| 5 | Wire missed-opportunity recorder (approval needed: frozen scanner file) | Phase 2 | Enables unbiased rejection analysis (§T) | §T INSUFFICIENT DATA | 0 | Low | Low-Med |
| 6 | Shadow-log breakeven-stop-after-TP1 outcomes | Analytics only | Unknown; bounds straddle actual | §P | 54 | None | Low |
| 7 | Soft warnings: RSI 30–49 chop, short direction (no gating) | Analytics only | Possible reduction of avoidable losses; unproven | §H/§R p≈0.04–0.09 | 23 | Low | Low |
| 8 | Any score-weight / regime / prompt change | NOT NOW | Cannot be estimated | §W CV-AUC 0.635; §F/§G/§I none significant | 113 | High (overfit) | — |
| 9 | Disable shorts | NOT NOW | Unknown | §K: ex-gap shorts 33.3% (n=9) | 20 | High (loses right tail) | — |
| 10 | ML retraining / auto weight optimizer / coin-specific models | Phase 3 — only if evidence | None shown | §W, prior retrain identical AUC | 118 | High | High |

**INSUFFICIENT DATA to recommend any predictive change.** Everything above rank 3 that touches predictions is deferred to the 200-trade re-audit.

## SECTION Y — 30-DAY FROZEN COMPONENTS CHECK

| Component | Remain frozen? | Evidence |
|---|---|---|
| scoring.py | YES | §W: CV-AUC 0.635; no component's odds ratio is CONFIRMED; §F/§G/§I show no significant component effects; a weight change would fit noise at n=118 |
| decision.py | YES | §S: the checklist items that fail most are equally common in wins and losses (no discrimination) — but changing them would be tuning on the same n; revisit at n≥200 |
| market_regime.py | YES | §J: only 2 of 6 regime labels ever emitted; cannot evaluate what is never produced; unfreezing without data is speculative |
| reasoning prompt | YES | §V: no A/B; releases not separable; entry thesis is the only prompt-dependent output and no per-prompt-version comparison has adequate n |
| ML weights / training | YES | §W/§9: CV-AUC 0.635; retraining previously gave identical AUC; ML score components have p>0.3 |

Freezing is justified by *lack of evidence for change*, not by evidence that the components are good.

## SECTION Z — FINAL VERDICT

Scores are my judgement (0–10), anchored on the cited metrics; they are not statistical estimates.
| Area | Score /10 | Anchor evidence |
|---|---|---|
| Prediction quality | 4 | CV-AUC 0.635; win rate 39.0%; PF 1.62 but 1.15 ex-top-3; median trade -1.59% |
| Entry timing | 4 | Immediate reversals = 79.2% of losses; entry_quality not significant (§E) |
| Risk management | 4 | Median loss vs win asymmetry; gap/slippage tails (worst -27.24%); 70.3% gap-exposed |
| Take-profit logic | 7 | Holding to the outermost target beat early exits (§P: sum ret +280.8% vs -203.6% at TP1) |
| Stop logic | 4 | Stops work as levels but execution tail is bad during gaps (avg slip in gaps -6.05%) |
| Confidence calibration | 2 | Brier 0.298 vs base 0.2378; over-predicts in every bucket ≥55 |
| Market regime detection | n/a (3) | Only 2 labels emitted; risk_on trades did worse than mixed; cannot be validated |
| Trade management | 5 | Real decisions only post 09-12; logic sound, effect unproven (§P) |
| Infrastructure reliability | 1 | Uptime 16.1%, 100 gaps |
| ML usefulness | 2 | ml_score p>0.3, ML probability present on few trades; retrain gave identical AUC |

**1. Single biggest reason trades lose:** the trade is wrong from the first candle — 79.2% of losses are immediate reversals (no TP1, MFE<1%) (CONFIRMED). Why the entries fail is NOT identifiable from stored fields (INSUFFICIENT DATA); the biggest *avoidable-cost* factor is infrastructure: 62.8% of loss magnitude exits inside monitoring gaps.
**2. Single code change most likely to help:** none in the predictive code is evidence-supported. The highest-ROI *change* is operational — a supervised, continuously running scanner with heartbeat alerting — followed by additive logging (structure booleans + missed-opportunity recorder) so the next audit can answer §G, §L and §T.
**3. What must NOT be changed yet:** scoring weights, decision checklist thresholds, regime logic, the reasoning prompt, ML weights/training, the hold-to-outermost-target exit rule (§P), and any hard short-disable.

### Roadmap for the next 200 trades
| Phase | Action | Trigger / gate |
|---|---|---|
| Now (0–20 trades) | Fix uptime; add display honesty (n/CI/median/ex-top-3 PF, calibrated confidence); log structure booleans + missed-opportunity recorder (with approval); shadow-log breakeven-after-TP1 | No prediction change |
| 20–100 | Accumulate under frozen engine; re-run this script weekly (it is deterministic); track continuous-uptime subset separately | Report ex-gap and all-trades metrics side-by-side |
| 100 (≈ 220 total closed) | First re-audit of: entry-quality tiers, RSI-chop flag, short performance ex-gap (need ≥30 clean shorts), EV vs confidence ranking | Act only where p<0.05 AND effect holds ex-top-3 and ex-gap |
| 200 (≈ 320 total) | Consider any evidence-backed weight/flag proposal; evaluate breakeven policy and regime labels beyond risk_on/mixed if they appear | Out-of-sample: fit on first half, test on second |
| Never on this n | ML retrain, auto-optimizer, per-coin models, hard short ban | Requires ≥500 trades and a held-out test |
