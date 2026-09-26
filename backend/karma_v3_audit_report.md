# Karma Archive — V3.0 Definitive Forensic Audit

Generated 2026-09-25 21:36 UTC from the live SQLite DB. **Read-only** — no code, prompt, weight, model or DB row was changed. Every figure is computed at run time by `analysis_karma_v3_audit.py`. `n=` is shown throughout; anything the DB cannot support is marked **INSUFFICIENT DATA**.

**Global caveats**: (1) Sharpe is per-trade (mean/σ of realized %), not annualized. (2) 'Drawdown' is a naive summed-return curve (no compounding/sizing). (3) Reliability is computed on all data (hindsight) — it is descriptive here, not what the system knew at entry. (4) Fisher's exact test on 2×2 win/loss tables; with n≈116, only large effects can reach significance. (5) Overlapping/clustered trades are not independent, so p-values are optimistic.

## SECTION 1 — EXECUTIVE SUMMARY

| Metric | Value | n |
|---|---|---|
| Total trade plans ever generated | 924 | 924 |
| Closed (resolved) trades | 116 | 116 |
| Open trades | 16 | 16 |
| Pending (not yet entered) | 12 | 12 |
| Never entered (expired, `closed_stale`) | 6 | 6 |
| Invalidated (superseded by a newer plan) | 727 | 727 (81 never entered) |
| Avoid-grade (`rejected_avoid`) | 47 | 47 |
| Wins / Losses | 45 / 71 | 116 |
| Overall win rate | 38.8% (95% CI 30.4–47.9%) | 116 |
| TP1 / TP2 / TP3 rate | 44.8% / 39.7% / 12.1% | 116 |
| Stop rate | 61.2% | 116 |
| Average return | 2.579% | 116 |
| Median return | -1.59% | 116 |
| Profit factor | 1.7 | 116 |
| Sharpe (per-trade) | 0.149 | 116 |
| Max drawdown (naive summed curve) | -100.5% | 116 |
| Worst single trade | -44.42% | 116 |
| Best single trade | 114.28% | 116 |
| Median hold (hours) | 28.713 | 116 |

| Segment | n | Win rate | PF | Avg ret | Median ret | TP1/TP2/TP3 % | Stop % | Median hold h |
|---|---|---|---|---|---|---|---|---|
| Long | 97 | 43.3% | 2.59 | 4.563% | -1.143% | 48.5/43.3/14.4 | 56.7% | 28.823 |
| Short | 19 | 15.8% | 0.03 | -7.55% | -3.351% | 26.3/21.1/0.0 | 84.2% | 28.603 |
| Timeframe=intraday | 54 | 44.4% | 1.25 | 1.133% | -1.325% | 50.0/46.3/9.3 | 55.6% | 41.535 |
| Timeframe=swing | 62 | 33.9% | 2.3 | 3.838% | -1.59% | 40.3/33.9/14.5 | 66.1% | 24.468 |

| Concentration test | n | PF | Avg ret | Median ret |
|---|---|---|---|---|
| All closed | 116 | 1.7 | 2.579 | -1.59 |
| Excl. best trade (NEARUSDT 114.3%) | 115 | 1.43 | 1.607 | -1.608 |
| Excl. top 3 | 113 | 1.2 | 0.772 | -1.635 |

**Is Karma profitable? → Marginal.** Aggregate PF is 1.7 and average return is 2.579% (n=116), but the median trade is -1.59% and PF falls to 1.2 without the top 3 winners: profit comes from a small number of large longs, while shorts (n=19, PF 0.03) lose. Most trades lose; the edge is right-tail winners.
**Confidence:** MEDIUM for 'positive expectancy so far' (n=116); LOW that it is robust. **Engineering recommendation:** treat headline PF as fragile; report ex-top-3 PF on every dashboard.

## SECTION 2 — COMPLETE CLOSED TRADE LEDGER

All 116 closed trades, newest first (created time). Reliability* = Bayesian per-symbol score on all data (hindsight). EV shown only where stored at issuance (post-V2.1); '—' = not computed for that era. Strategy = `strategy_attribution.classify_strategy` (BOS/CHoCH are proxies). Pattern = lifecycle + risk tags. Outcome = Trade-Truth verdict.

| Symbol | Created | Entered | Closed | Dir | Strategy | Entry | Exit | Stop | TP1 | TP2 | TP3 | Grade | Conf | Score | EQ | Regime | EV(R) | Rel* | Ret% | MFE% | MAE% | Hold h | Pattern | Red flags | Outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPCXUSDT | 2026-09-14 19:01 | 2026-09-14 19:07 | 2026-09-25 20:45 | long | fvg_continuation | 150.075 | 148.55 | 148.6 | 151.57 | 152.52 | 154.77 | B+ | 70 | 70.3 | excellent | risk_on | 0.29 | 34.9 | -1.02 | 0.13 | -1.02 | 265.6 | immediate_reversal+no_historical_analogue,scanner_outage_corrupted | no_history | infrastructure_failure |
| BNBUSDT | 2026-09-14 19:01 | 2026-09-14 19:07 | 2026-09-25 20:45 | long | ema_pullback | 725.55 | 776.17 | 717 | 729.13 | 737.4 | — | B+ | 65 | 64.0 | neutral | risk_on | -0.82 | 37.5 | 6.98 | 6.98 | 0.07 | 265.6 | closed_at_tp2+weak_structure,scanner_outage_corrupted | weak_structure | infrastructure_failure |
| UNIUSDT | 2026-09-14 17:00 | 2026-09-14 17:06 | 2026-09-25 20:45 | long | ema_pullback | 6.36 | 9.679 | 6.19 | 6.57 | 6.8 | — | B | 64 | 61.0 | neutral | mixed | 0.15 | 44.4 | 52.19 | 52.19 | 0.55 | 267.7 | closed_at_tp2+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | infrastructure_failure |
| ZECUSDT | 2026-09-14 16:14 | 2026-09-14 16:32 | 2026-09-25 20:45 | long | ema_pullback | 1130 | 1549.03 | 1108 | 1161.98 | 1184 | 1297.5 | B | 59 | 56.4 | neutral | mixed | 0.26 | 42.0 | 37.08 | 37.08 | 0.36 | 268.2 | ran_to_tp3+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,negative_cmf | infrastructure_failure |
| HYPEUSDT | 2026-09-14 15:50 | 2026-09-14 15:57 | 2026-09-25 20:45 | long | ema_pullback | 79.8 | 91.923 | 76.5 | 80.77 | 89.67 | — | B | 59 | 56.0 | neutral | mixed | -0.33 | 42.0 | 15.19 | 15.19 | -0.13 | 268.8 | closed_at_tp2+rsi_chop_zone,weak_structure,no_historical_analogue,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history | infrastructure_failure |
| BZUSDT | 2026-09-14 15:50 | 2026-09-14 15:57 | 2026-09-25 20:45 | long | ema_pullback | 102.25 | 97.46 | 99 | 103.91 | 112.75 | — | C | 54 | 54.7 | neutral | mixed | -0.22 | 32.3 | -4.68 | 0.37 | -4.68 | 268.8 | immediate_reversal+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,funding_elevated | infrastructure_failure |
| NEARUSDT | 2026-09-14 15:50 | 2026-09-14 15:57 | 2026-09-25 20:45 | long | ema_pullback | 2.3875 | 5.116 | 2.276 | 2.435 | 2.727 | — | B | 57 | 54.6 | neutral | mixed | -0.27 | 49.0 | 114.28 | 114.28 | 0.40 | 268.8 | closed_at_tp2+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,negative_cmf | infrastructure_failure |
| SUIUSDT | 2026-09-14 15:38 | 2026-09-14 15:50 | 2026-09-14 16:48 | short | ema_pullback | 0.725 | 0.7319 | 0.731 | 0.705 | 0.692 | — | B | 61 | 54.7 | neutral | mixed | -1.00 | 32.3 | -0.95 | 0.18 | -0.95 | 1.0 | immediate_reversal+rsi_chop_zone,weak_structure,no_historical_analogue,short_direction | rsi_chop_30_49,weak_structure,no_history,risk_penalty_applied | bad_structure_call |
| XRPUSDT | 2026-09-14 14:44 | 2026-09-14 14:57 | 2026-09-14 18:32 | long | breakout_chase | 1.392 | 1.4561 | 1.3312 | 1.4094 | 1.4502 | — | B | 63 | 58.8 | neutral | mixed | -0.34 | 44.4 | 4.61 | 4.61 | 0.37 | 3.6 | closed_at_tp2+weak_structure | weak_structure | perfect_trade |
| SOLUSDT | 2026-09-14 14:44 | 2026-09-14 14:57 | 2026-09-25 20:45 | long | ema_pullback | 101.25 | 122.51 | 98.92 | 102.31 | 105.77 | — | B | 57 | 54.4 | neutral | mixed | -0.25 | 32.5 | 21.00 | 21.00 | 0.25 | 269.8 | closed_at_tp2+weak_structure,scanner_outage_corrupted | weak_structure,negative_cmf | infrastructure_failure |
| 1000PEPEUSDT | 2026-09-13 11:00 | 2026-09-13 11:06 | 2026-09-25 20:45 | long | ema_pullback | 0.0033925 | 0.0044924 | 0.0032 | 0.003485 | 0.0037666 | — | B | 56 | 53.3 | neutral | mixed | -0.21 | 40.7 | 32.42 | 32.42 | -1.42 | 297.7 | closed_at_tp2+rsi_chop_zone,weak_structure,no_historical_analogue,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history,negative_cmf | infrastructure_failure |
| CLUSDT | 2026-09-13 10:54 | 2026-09-13 11:00 | 2026-09-25 20:45 | long | ema_pullback | 96.35 | 92.44 | 94.6 | 100.9 | 106.98 | — | B | 63 | 53.2 | neutral | mixed | 0.91 | 42.0 | -4.06 | 4.24 | -4.06 | 297.8 | some_favorable_move_then_stopped+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | infrastructure_failure |
| FLOCKUSDT | 2026-09-13 10:47 | 2026-09-13 14:00 | 2026-09-13 17:49 | long | breakout_chase | 0.07915 | 0.07489 | 0.07602 | 0.08205 | 0.08619 | — | B | 60 | 56.0 | neutral | mixed | 0.02 | 35.3 | -5.38 | 2.73 | -5.38 | 3.8 | some_favorable_move_then_stopped+weak_structure,no_historical_analogue | weak_structure,no_history,negative_cmf,risk_penalty_applied | bad_structure_call |
| DOGEUSDT | 2026-09-13 06:29 | 2026-09-14 09:53 | 2026-09-25 20:45 | short | ema_pullback | 0.084945 | 0.09837 | 0.08545 | 0.08454 | 0.08216 | — | B | 59 | 55.9 | neutral | mixed | -1.00 | 29.8 | -15.80 | 2.10 | -15.80 | 274.9 | reached_tp1_then_stopped+rsi_chop_zone,weak_structure,no_historical_analogue,short_direction,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history | infrastructure_failure |
| XAUUSDT | 2026-09-13 04:24 | 2026-09-13 04:49 | 2026-09-14 09:25 | short | fvg_continuation | 4359.75 | 4292.87 | 4390 | 4325 | 4295 | — | B | 55 | 60.5 | good | mixed | -0.31 | 40.7 | 1.53 | 1.53 | -0.03 | 28.6 | closed_at_tp2+rsi_chop_zone,no_historical_analogue,short_direction | rsi_chop_30_49,no_history,negative_cmf,mfi_over_80 | perfect_trade |
| USELESSUSDT | 2026-09-13 03:42 | 2026-09-13 03:48 | 2026-09-13 07:16 | long | ema_pullback | 0.2343 | 0.22327 | 0.2235 | 0.2448 | 0.2559 | 0.274 | B | 58 | 57.5 | neutral | mixed | 0.20 | 35.3 | -4.71 | -0.01 | -4.71 | 3.5 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history,risk_penalty_applied | bad_structure_call |
| PUMPUSDT | 2026-09-13 03:12 | 2026-09-13 03:18 | 2026-09-13 08:33 | long | ema_pullback | 0.003775 | 0.003694 | 0.0037 | 0.003913 | 0.003967 | — | B | 56 | 53.3 | neutral | mixed | 0.72 | 40.7 | -2.15 | 1.80 | -2.15 | 5.3 | some_favorable_move_then_stopped+rsi_chop_zone,weak_structure,no_historical_analogue | rsi_chop_30_49,weak_structure,no_history,negative_cmf | bad_structure_call |
| ETHUSDT | 2026-09-13 02:42 | 2026-09-13 02:48 | 2026-09-13 09:31 | long | ema_pullback | 2518.8 | 2482.04 | 2487 | 2546.11 | 2567.24 | 2666 | B | 55 | 54.2 | neutral | mixed | 0.13 | 25.9 | -1.46 | 0.15 | -1.46 | 6.7 | immediate_reversal+weak_structure | weak_structure | bad_structure_call |
| XAGUSDT | 2026-09-13 00:24 | 2026-09-13 00:30 | 2026-09-14 09:19 | short | fvg_continuation | 64.6 | 62.71 | 64.75 | 64 | 63.03 | — | C | 51 | 56.2 | excellent | mixed | 1.86 | 37.5 | 2.93 | 2.93 | -0.01 | 32.8 | closed_at_tp2+rsi_chop_zone,no_historical_analogue,short_direction | rsi_chop_30_49,no_history,negative_cmf | perfect_trade |
| WLDUSDT | 2026-09-12 16:08 | 2026-09-12 16:14 | 2026-09-25 20:45 | short | fvg_continuation | 0.40625 | 0.4826 | 0.4165 | 0.398 | 0.387 | 0.378 | B | 61 | 58.2 | good | mixed | -0.41 | 40.7 | -18.79 | 4.89 | -18.79 | 316.5 | hit_tp2_then_reversed+rsi_chop_zone,no_historical_analogue,short_direction,scanner_outage_corrupted | rsi_chop_30_49,no_history,negative_cmf | infrastructure_failure |
| LABUSDT | 2026-09-12 15:39 | 2026-09-12 15:50 | 2026-09-12 15:56 | long | trend_continuation_other | 0.073 | 0.06763 | 0.0695 | 0.0745 | 0.078 | — | C | 48 | 55.0 | neutral | mixed | -0.09 | 35.3 | -7.36 | 0.62 | -7.36 | 0.1 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history,negative_cmf,risk_penalty_applied | bad_structure_call |
| SKHYUSDT | 2026-09-12 15:33 | 2026-09-12 15:39 | 2026-09-13 08:28 | long | ema_pullback | 190.2 | 184.64 | 185 | 194 | 197 | 199.6 | B+ | 68 | 58.6 | neutral | mixed | 0.11 | 42.0 | -2.92 | 0.15 | -2.92 | 16.8 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | bad_structure_call |
| SKHYNIXUSDT | 2026-09-12 15:21 | 2026-09-12 15:27 | 2026-09-12 19:38 | long | ema_pullback | 1365.25 | 1334.08 | 1360.5 | 1374.4 | 1396 | 1418 | B+ | 66 | 56.7 | neutral | mixed | 0.87 | 37.5 | -2.28 | 0.25 | -2.28 | 4.2 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | bad_structure_call |
| CRCLUSDT | 2026-09-12 14:23 | 2026-09-12 14:29 | 2026-09-14 12:34 | short | fvg_continuation | 91.75 | 92.66 | 92.6 | 90.76 | 89.24 | — | C | 54 | 59.2 | good | mixed | -0.30 | 45.2 | -0.99 | 1.50 | -0.99 | 46.1 | reached_tp1_then_stopped+rsi_chop_zone,no_historical_analogue,short_direction | rsi_chop_30_49,no_history,negative_cmf | good_entry_bad_exit |
| RIVERUSDT | 2026-09-12 13:13 | 2026-09-12 13:19 | 2026-09-12 18:34 | long | trend_continuation_other | 1.27 | 1.509 | 1.19 | 1.35 | 1.457 | — | C | 50 | 57.5 | neutral | mixed | 0.28 | 44.4 | 18.82 | 18.82 | -0.71 | 5.2 | closed_at_tp2+weak_structure,no_historical_analogue | weak_structure,no_history,risk_penalty_applied | perfect_trade |
| SPCXUSDT | 2026-09-12 12:03 | 2026-09-12 12:09 | 2026-09-14 01:15 | long | fvg_continuation | 150.1 | 148.2 | 148.6 | 151.78 | 154.77 | — | B | 61 | 58.5 | excellent | mixed | 0.70 | 34.9 | -1.27 | 0.11 | -1.27 | 37.1 | immediate_reversal+no_historical_analogue | no_history,negative_cmf | bad_structure_call |
| SOLUSDT | 2026-09-06 07:06 | 2026-09-06 07:07 | 2026-09-12 06:56 | long | fvg_continuation | 104.8 | 101.68 | 102.6 | 107 | 109.5 | 113.6 | B+ | 73 | 72.2 | excellent | risk_on | — | 32.5 | -2.98 | 0.54 | -2.98 | 143.8 | immediate_reversal+scanner_outage_corrupted | — | infrastructure_failure |
| LINKUSDT | 2026-09-06 07:06 | 2026-09-06 07:07 | 2026-09-12 06:56 | long | fvg_continuation | 12.185 | 11.516 | 11.85 | 12.58 | 13 | — | B+ | 72 | 68.3 | excellent | risk_on | — | 45.2 | -5.49 | 0.69 | -5.49 | 143.8 | immediate_reversal+no_historical_analogue,scanner_outage_corrupted | no_history | infrastructure_failure |
| FILUSDT | 2026-09-06 06:53 | 2026-09-06 07:06 | 2026-09-13 14:56 | long | fvg_continuation | 0.8021 | 0.9216 | 0.7852 | 0.8399 | 0.8672 | — | B+ | 69 | 69.2 | excellent | risk_on | — | 44.4 | 14.90 | 14.90 | -0.37 | 175.8 | closed_at_tp2+no_historical_analogue | no_history,negative_cmf | perfect_trade |
| SKHYUSDT | 2026-08-29 03:31 | 2026-08-29 03:38 | 2026-09-03 05:21 | long | ema_pullback | 161.6 | 159.06 | 160.3 | 163.5 | 166.71 | — | B | 62 | 59.5 | neutral | mixed | — | 42.0 | -1.57 | 2.28 | -1.57 | 121.7 | reached_tp1_then_stopped+weak_structure,no_historical_analogue | weak_structure,no_history | good_entry_bad_exit |
| HEMIUSDT | 2026-08-29 03:31 | 2026-08-29 06:47 | 2026-08-29 07:03 | long | trend_continuation_other | 0.01165 | 0.010646 | 0.0109 | 0.01312 | 0.013949 | 0.016 | B | 64 | 59.0 | neutral | mixed | — | 35.3 | -8.62 | 0.57 | -8.62 | 0.3 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history,risk_penalty_applied | bad_structure_call |
| ENAUSDT | 2026-08-29 03:31 | 2026-08-29 03:38 | 2026-08-29 08:16 | long | trend_continuation_other | 0.163 | 0.15631 | 0.157 | 0.16471 | 0.17444 | 0.18375 | B | 59 | 58.0 | neutral | mixed | — | 35.3 | -4.10 | 1.47 | -4.10 | 4.6 | reached_tp1_then_stopped+weak_structure,no_historical_analogue | weak_structure,no_history,risk_penalty_applied | good_entry_bad_exit |
| SOXSUSDT | 2026-08-29 03:31 | 2026-08-29 03:38 | 2026-09-02 20:20 | long | trend_continuation_other | 49.3 | 53 | 47.8 | 49.81 | 50.23 | 52.85 | B | 60 | 57.0 | neutral | mixed | — | 49.0 | 7.50 | 7.50 | 0.12 | 112.7 | ran_to_tp3+weak_structure,no_historical_analogue | weak_structure,no_history | perfect_trade |
| SNXXUSDT | 2026-08-29 03:00 | 2026-08-29 03:07 | 2026-09-02 18:59 | short | ema_pullback | 12.9 | 13.94 | 13.45 | 12.2 | 12.02 | 11.65 | B | 64 | 61.2 | neutral | mixed | — | 32.3 | -8.06 | 0.62 | -8.06 | 111.9 | immediate_reversal+rsi_chop_zone,weak_structure,no_historical_analogue,short_direction,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history | infrastructure_failure |
| SNDKUSDT | 2026-08-29 03:00 | 2026-08-29 03:07 | 2026-09-02 18:59 | short | ema_pullback | 1485 | 1548.9 | 1517 | 1477 | 1436 | 1419.66 | B | 59 | 56.0 | neutral | mixed | — | 37.5 | -4.30 | 0.10 | -4.30 | 111.9 | immediate_reversal+rsi_chop_zone,weak_structure,no_historical_analogue,short_direction,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history | infrastructure_failure |
| CLUSDT | 2026-08-29 03:00 | 2026-08-29 03:07 | 2026-09-02 18:59 | long | ema_pullback | 83.15 | 90.82 | 82.2 | 83.63 | 84.41 | — | B | 58 | 55.4 | neutral | mixed | — | 42.0 | 9.22 | 9.22 | -0.20 | 111.9 | closed_at_tp2+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | infrastructure_failure |
| ZECUSDT | 2026-08-29 01:50 | 2026-08-29 01:57 | 2026-09-06 06:22 | long | ema_pullback | 802 | 1166.44 | 775 | 817.22 | 889.99 | — | B+ | 65 | 54.9 | neutral | mixed | — | 42.0 | 45.44 | 45.44 | -1.45 | 196.4 | closed_at_tp2+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | infrastructure_failure |
| TRUMPUSDT | 2026-08-29 00:06 | 2026-08-29 00:34 | 2026-09-02 18:59 | long | trend_continuation_other | 2.75 | 2.174 | 2.505 | 2.892 | 3.1 | — | C | 47 | 54.8 | neutral | mixed | — | 35.3 | -20.95 | 10.98 | -20.95 | 114.4 | reached_tp1_then_stopped+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,negative_cmf,risk_penalty_applied | infrastructure_failure |
| MOVRUSDT | 2026-08-28 19:42 | 2026-08-28 20:11 | 2026-08-28 20:41 | long | trend_continuation_other | 0.9115 | 0.7656 | 0.845 | 0.975 | 1.038 | 1.138 | B | 59 | 58.0 | neutral | mixed | — | 32.3 | -16.01 | 0.23 | -16.01 | 0.5 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history,risk_penalty_applied | bad_structure_call |
| BNBUSDT | 2026-08-28 18:03 | 2026-08-28 18:07 | 2026-08-28 18:40 | long | fvg_continuation | 694.55 | 686.61 | 686.9 | 707.78 | 719.14 | — | B+ | 71 | 59.0 | good | mixed | — | 37.5 | -1.14 | -0.17 | -1.14 | 0.6 | immediate_reversal+rsi_chop_zone | rsi_chop_30_49,risk_penalty_applied | bad_structure_call |
| MOVRUSDT | 2026-08-28 15:58 | 2026-08-28 16:05 | 2026-08-28 16:29 | long | trend_continuation_other | 0.9085 | 0.8819 | 0.8935 | 0.975 | 1.023 | 1.138 | B | 61 | 63.0 | neutral | risk_on | — | 32.3 | -2.93 | -0.11 | -2.93 | 0.4 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history,risk_penalty_applied | bad_structure_call |
| SPCXUSDT | 2026-08-28 15:51 | 2026-08-28 15:58 | 2026-09-03 13:47 | long | ema_pullback | 140.1 | 146.76 | 138.4 | 141.96 | 143.5 | 146.1 | B+ | 65 | 64.8 | neutral | risk_on | — | 34.9 | 4.75 | 4.75 | -1.12 | 141.8 | ran_to_tp3+weak_structure,no_historical_analogue | weak_structure,no_history | perfect_trade |
| MSTRUSDT | 2026-08-28 15:51 | 2026-08-28 15:58 | 2026-09-02 18:59 | long | fvg_continuation | 129 | 122.62 | 126.5 | 136.17 | 140.85 | 143.19 | B+ | 65 | 61.5 | good | risk_on | — | 29.8 | -4.95 | -0.32 | -4.95 | 123.0 | immediate_reversal+no_historical_analogue,scanner_outage_corrupted | no_history,risk_penalty_applied | infrastructure_failure |
| MSTRUSDT | 2026-08-28 15:21 | 2026-08-28 15:28 | 2026-08-28 15:51 | long | fvg_continuation | 133.7 | 129.1 | 129.5 | 137.17 | 141.1 | 143.19 | B+ | 65 | 65.6 | good | risk_on | — | 29.8 | -3.44 | -0.75 | -3.44 | 0.4 | immediate_reversal+no_historical_analogue | no_history | bad_structure_call |
| ETHUSDT | 2026-08-28 15:03 | 2026-08-28 15:10 | 2026-08-28 15:58 | long | ema_pullback | 2502 | 2475.25 | 2478 | 2535 | 2570 | 2620 | A | 76 | 70.1 | neutral | risk_on | — | 25.9 | -1.07 | 0.20 | -1.07 | 0.8 | immediate_reversal+weak_structure | weak_structure | bad_structure_call |
| SUIUSDT | 2026-08-28 14:57 | 2026-08-28 15:03 | 2026-09-12 06:56 | long | ema_pullback | 0.76925 | 0.7233 | 0.7241 | 0.8013 | 0.9555 | — | B | 63 | 62.9 | neutral | risk_on | — | 32.3 | -5.97 | 3.59 | -5.97 | 351.9 | some_favorable_move_then_stopped+rsi_chop_zone,weak_structure,no_historical_analogue,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history,negative_cmf | infrastructure_failure |
| XAGUSDT | 2026-08-28 14:51 | 2026-08-28 15:15 | 2026-08-28 16:22 | long | ema_pullback | 69.4 | 66.76 | 67.4 | 71.01 | 71.23 | — | B | 61 | 61.1 | neutral | risk_on | — | 37.5 | -3.80 | 0.06 | -3.80 | 1.1 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | bad_structure_call |
| SOLUSDT | 2026-08-28 14:04 | 2026-08-28 14:10 | 2026-09-02 18:59 | long | fvg_continuation | 104.4 | 99.42 | 100.9 | 106.8 | 110 | 113 | B+ | 73 | 65.8 | good | risk_on | — | 32.5 | -4.77 | 2.73 | -4.77 | 124.8 | reached_tp1_then_stopped+scanner_outage_corrupted | — | infrastructure_failure |
| MSTRUSDT | 2026-08-28 13:34 | 2026-08-28 13:40 | 2026-08-28 14:10 | long | fvg_continuation | 134.74 | 132.35 | 132.4 | 136.55 | 137.17 | 141.1 | B+ | 71 | 70.8 | good | risk_on | — | 29.8 | -1.77 | 0.28 | -1.77 | 0.5 | immediate_reversal+no_historical_analogue | no_history | bad_structure_call |
| MUUSDT | 2026-08-21 10:23 | 2026-08-21 10:34 | 2026-08-28 12:24 | long | trend_continuation_other | 977.35 | 921.1 | 963.73 | 987.97 | 1021.79 | 1036 | B+ | 66 | 65.8 | neutral | risk_on | — | 40.7 | -5.75 | 0.40 | -5.75 | 169.8 | immediate_reversal+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | infrastructure_failure |
| DRAMUSDT | 2026-08-21 08:59 | 2026-08-21 09:05 | 2026-08-28 12:24 | long | trend_continuation_other | 58.425 | 55.92 | 57.35 | 59.37 | 60.81 | 62.09 | B | 63 | 62.7 | neutral | risk_on | — | 34.9 | -4.29 | 0.62 | -4.29 | 171.3 | immediate_reversal+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,negative_cmf | infrastructure_failure |
| SAMSUNGUSDT | 2026-08-21 08:13 | 2026-08-21 08:25 | 2026-08-28 12:24 | long | trend_continuation_other | 196.75 | 187.77 | 191 | 203.4 | 206 | 211.5 | B+ | 68 | 66.0 | neutral | risk_on | — | 45.2 | -4.56 | 0.49 | -4.56 | 172.0 | immediate_reversal+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,liquidity_stress | infrastructure_failure |
| LINKUSDT | 2026-08-16 12:03 | 2026-08-16 12:09 | 2026-08-21 07:40 | long | trend_continuation_other | 9.34 | 11.647 | 9.18 | 9.507 | 9.63 | — | B | 64 | 61.0 | neutral | mixed | — | 45.2 | 24.70 | 24.70 | -0.12 | 115.5 | closed_at_tp2+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | infrastructure_failure |
| CLUSDT | 2026-08-16 09:45 | 2026-08-16 09:51 | 2026-08-21 07:40 | long | ema_pullback | 81.225 | 86.38 | 80.8 | 81.56 | 82 | 84.04 | B | 62 | 52.6 | neutral | mixed | — | 42.0 | 6.35 | 6.35 | 0.04 | 117.8 | ran_to_tp3+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | infrastructure_failure |
| ZECUSDT | 2026-08-16 09:27 | 2026-08-16 09:34 | 2026-08-21 07:40 | short | ema_pullback | 488.5 | 629.21 | 494.5 | 483.45 | 480.27 | 466.28 | B | 59 | 56.5 | neutral | mixed | — | 42.0 | -28.80 | 0.76 | -28.80 | 118.1 | immediate_reversal+rsi_chop_zone,weak_structure,no_historical_analogue,short_direction,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history,negative_cmf | infrastructure_failure |
| ALLOUSDT | 2026-08-16 08:42 | 2026-08-16 10:31 | 2026-08-16 11:06 | short | trend_continuation_other | 0.268 | 0.27539 | 0.274 | 0.2616 | 0.2535 | 0.244 | B | 63 | 56.7 | neutral | mixed | — | 35.3 | -2.76 | 0.55 | -2.76 | 0.6 | immediate_reversal+rsi_chop_zone,weak_structure,no_historical_analogue,short_direction,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history,negative_cmf | infrastructure_failure |
| HYPEUSDT | 2026-08-16 08:07 | 2026-08-16 09:45 | 2026-08-21 07:40 | long | fvg_continuation | 57.145 | 73.76 | 56.55 | 57.85 | 58.45 | 59.1 | B+ | 65 | 62.4 | excellent | mixed | — | 42.0 | 29.07 | 29.07 | 0.12 | 117.9 | ran_to_tp3+no_historical_analogue,scanner_outage_corrupted | no_history,negative_cmf | infrastructure_failure |
| ETHUSDT | 2026-08-16 07:44 | 2026-08-16 07:55 | 2026-08-21 07:40 | short | ema_pullback | 1880.25 | 2381.77 | 1890.6 | 1876 | 1852.22 | — | B | 56 | 61.2 | neutral | mixed | — | 25.9 | -26.67 | 0.11 | -26.67 | 119.7 | immediate_reversal+rsi_chop_zone,weak_structure,short_direction,scanner_outage_corrupted | rsi_chop_30_49,weak_structure | infrastructure_failure |
| SPORTFUNUSDT | 2026-08-16 03:29 | 2026-08-16 03:40 | 2026-08-16 06:42 | long | trend_continuation_other | 0.0258 | 0.02422 | 0.02422 | 0.02975 | 0.03598 | — | B | 59 | 58.9 | neutral | mixed | — | 35.3 | -6.12 | 0.78 | -6.12 | 3.0 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history,negative_cmf,risk_penalty_applied | bad_structure_call |
| WLDUSDT | 2026-08-15 21:29 | 2026-08-15 21:35 | 2026-08-21 07:40 | long | fvg_continuation | 0.34795 | 0.3768 | 0.339 | 0.3547 | 0.3629 | 0.372 | B+ | 67 | 64.9 | excellent | mixed | — | 40.7 | 8.29 | 8.29 | -1.48 | 130.1 | ran_to_tp3+no_historical_analogue,scanner_outage_corrupted | no_history,negative_cmf | infrastructure_failure |
| PUMPUSDT | 2026-08-15 17:42 | 2026-08-15 20:20 | 2026-08-21 07:40 | long | fvg_continuation | 0.002807 | 0.003912 | 0.002681 | 0.002946 | 0.002987 | — | B+ | 71 | 61.3 | excellent | mixed | — | 40.7 | 39.37 | 39.37 | -3.46 | 131.3 | closed_at_tp2+no_historical_analogue,scanner_outage_corrupted | no_history | infrastructure_failure |
| SKHYNIXUSDT | 2026-08-15 17:07 | 2026-08-16 13:01 | 2026-08-21 07:40 | long | fvg_continuation | 1171.17 | 1253.92 | 1157.05 | 1209 | 1221.99 | — | B+ | 65 | 56.0 | excellent | mixed | — | 37.5 | 7.07 | 7.07 | 0.17 | 114.6 | closed_at_tp2+no_historical_analogue,scanner_outage_corrupted | no_history,negative_cmf | infrastructure_failure |
| DOGEUSDT | 2026-08-15 16:26 | 2026-08-15 17:07 | 2026-08-21 07:40 | short | ema_pullback | 0.07015 | 0.0844 | 0.0711 | 0.0688 | 0.0677 | — | C | 53 | 58.6 | neutral | mixed | — | 29.8 | -20.31 | 0.95 | -20.31 | 134.5 | immediate_reversal+rsi_chop_zone,weak_structure,no_historical_analogue,short_direction,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history,negative_cmf | infrastructure_failure |
| BNBUSDT | 2026-08-14 00:44 | 2026-08-14 00:50 | 2026-08-14 11:14 | long | fvg_continuation | 610.5 | 604.36 | 604.7 | 615.2 | 620.9 | — | B+ | 69 | 60.4 | excellent | mixed | — | 37.5 | -1.01 | 0.37 | -1.01 | 10.4 | immediate_reversal | — | bad_structure_call |
| SAMSUNGUSDT | 2026-08-14 00:44 | 2026-08-14 02:12 | 2026-08-21 07:40 | long | trend_continuation_other | 191.5 | 203.79 | 182.5 | 195.25 | 199.6 | — | B+ | 66 | 60.0 | neutral | mixed | — | 45.2 | 6.42 | 6.42 | -0.95 | 173.5 | closed_at_tp2+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,mfi_over_80 | infrastructure_failure |
| APRUSDT | 2026-08-14 00:33 | 2026-08-14 00:44 | 2026-08-14 12:29 | long | trend_continuation_other | 0.457 | 0.544 | 0.401 | 0.4877 | 0.5278 | 0.5393 | B | 64 | 63.0 | neutral | mixed | — | 44.4 | 19.04 | 19.04 | -4.33 | 11.8 | ran_to_tp3+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,risk_penalty_applied | infrastructure_failure |
| SPCXUSDT | 2026-08-13 19:27 | 2026-08-13 19:33 | 2026-08-15 14:00 | long | fvg_continuation | 143.55 | 139.58 | 139.6 | 148.6 | 152 | — | B+ | 66 | 63.6 | good | mixed | — | 34.9 | -2.77 | 0.81 | -2.77 | 42.4 | immediate_reversal+no_historical_analogue | no_history | bad_structure_call |
| LINKUSDT | 2026-08-13 17:20 | 2026-08-14 08:24 | 2026-08-15 13:13 | long | ema_pullback | 8.705 | 9.459 | 8.58 | 8.865 | 8.982 | 9.038 | B+ | 67 | 57.5 | neutral | mixed | — | 45.2 | 8.66 | 8.66 | 0.31 | 28.8 | ran_to_tp3+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | infrastructure_failure |
| BTWUSDT | 2026-08-13 15:48 | 2026-08-13 15:54 | 2026-08-15 18:35 | long | fvg_continuation | 0.2615 | 0.31647 | 0.235 | 0.2692 | 0.285 | 0.31 | B | 60 | 57.3 | excellent | mixed | — | 49.0 | 21.02 | 21.02 | 0.10 | 50.7 | ran_to_tp3+no_historical_analogue,scanner_outage_corrupted | no_history,risk_penalty_applied,funding_elevated | infrastructure_failure |
| ETHUSDT | 2026-08-13 15:42 | 2026-08-13 15:48 | 2026-08-13 16:40 | long | ema_pullback | 1888 | 1868.99 | 1873 | 1899.6 | 1911.5 | 1943 | B+ | 65 | 65.0 | neutral | mixed | — | 25.9 | -1.01 | -0.00 | -1.01 | 0.9 | immediate_reversal+rsi_chop_zone,weak_structure | rsi_chop_30_49,weak_structure,negative_cmf | bad_structure_call |
| MUUSDT | 2026-08-13 13:29 | 2026-08-13 13:35 | 2026-08-13 13:47 | long | trend_continuation_other | 911.25 | 934.3 | 901.5 | 916.1 | 929 | — | B | 64 | 61.2 | neutral | mixed | — | 40.7 | 2.53 | 2.53 | 0.26 | 0.2 | closed_at_tp2+weak_structure,no_historical_analogue | weak_structure,no_history | perfect_trade |
| SAMSUNGUSDT | 2026-08-13 13:10 | 2026-08-13 13:16 | 2026-08-13 15:24 | long | trend_continuation_other | 185.75 | 195.86 | 183.3 | 191.23 | 195.7 | — | B+ | 66 | 59.4 | neutral | mixed | — | 45.2 | 5.44 | 5.44 | 0.20 | 2.1 | closed_at_tp2+weak_structure,no_historical_analogue | weak_structure,no_history,mfi_over_80 | perfect_trade |
| SOXSUSDT | 2026-08-13 12:52 | 2026-08-13 12:58 | 2026-08-13 13:04 | short | fvg_continuation | 41.15 | 40.86 | 41.95 | 39.88 | 41.82 | — | B+ | 69 | 60.1 | good | mixed | — | 49.0 | 0.70 | 0.70 | 0.24 | 0.1 | closed_at_tp2+rsi_chop_zone,no_historical_analogue,short_direction | rsi_chop_30_49,no_history | perfect_trade |
| EWYUSDT | 2026-08-13 12:03 | 2026-08-13 12:10 | 2026-08-13 14:36 | long | trend_continuation_other | 174.6 | 179.2 | 172.5 | 177.9 | 178.7 | — | B | 64 | 61.4 | neutral | mixed | — | 40.7 | 2.63 | 2.63 | -0.18 | 2.4 | closed_at_tp2+weak_structure,no_historical_analogue | weak_structure,no_history,mfi_over_80 | perfect_trade |
| DRAMUSDT | 2026-08-13 11:27 | 2026-08-13 11:33 | 2026-08-13 14:24 | long | fvg_continuation | 54.35 | 55.89 | 53.6 | 55.05 | 55.86 | — | B | 64 | 61.5 | good | mixed | — | 34.9 | 2.83 | 2.83 | -0.33 | 2.9 | closed_at_tp2+no_historical_analogue | no_history,mfi_over_80 | perfect_trade |
| NVDAUSDT | 2026-08-13 11:27 | 2026-08-13 15:36 | 2026-08-28 12:24 | long | ema_pullback | 223.85 | 227.39 | 221.2 | 225.24 | 226.48 | — | B | 62 | 59.6 | neutral | mixed | — | 49.0 | 1.58 | 1.58 | 0.15 | 356.8 | closed_at_tp2+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,negative_cmf,mfi_over_80 | infrastructure_failure |
| SKHYUSDT | 2026-08-13 09:21 | 2026-08-13 09:27 | 2026-08-13 14:48 | long | fvg_continuation | 150.8 | 163.91 | 144.3 | 154.06 | 157.06 | 163.87 | B | 64 | 62.0 | good | mixed | — | 42.0 | 8.69 | 8.69 | 0.38 | 5.3 | ran_to_tp3+no_historical_analogue | no_history,mfi_over_80 | perfect_trade |
| CYSUSDT | 2026-08-13 08:01 | 2026-08-13 08:07 | 2026-08-13 09:21 | long | fvg_continuation | 1.465 | 1.3759 | 1.38 | 1.5923 | 1.6995 | 1.7787 | B | 63 | 63.0 | good | mixed | — | 40.7 | -6.08 | 0.74 | -6.08 | 1.2 | immediate_reversal+no_historical_analogue | no_history,risk_penalty_applied | bad_structure_call |
| XAUUSDT | 2026-08-13 05:13 | 2026-08-13 05:34 | 2026-08-13 06:37 | long | ema_pullback | 4400.5 | 4374.88 | 4380 | 4436 | 4456.65 | 4490 | B+ | 68 | 59.0 | neutral | mixed | — | 40.7 | -0.58 | 0.05 | -0.58 | 1.1 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | bad_structure_call |
| PAXGUSDT | 2026-08-13 05:13 | 2026-08-13 05:34 | 2026-08-13 06:37 | long | ema_pullback | 4390.5 | 4364.53 | 4368 | 4425 | 4440.7 | 4479 | B+ | 68 | 59.0 | neutral | mixed | — | 40.7 | -0.59 | 0.06 | -0.59 | 1.1 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | bad_structure_call |
| BTWUSDT | 2026-08-13 04:55 | 2026-08-13 05:13 | 2026-08-13 15:18 | long | bos_pullback | 0.23761 | 0.26966 | 0.214 | 0.25517 | 0.26918 | — | B | 61 | 57.9 | good | mixed | — | 49.0 | 13.49 | 13.49 | -3.51 | 10.1 | closed_at_tp2+no_historical_analogue | no_history,risk_penalty_applied,funding_elevated | good_trade |
| XAGUSDT | 2026-08-12 19:17 | 2026-08-12 19:23 | 2026-08-13 19:15 | long | ema_pullback | 65.35 | 64.34 | 64.35 | 66.59 | 67.04 | 68.5 | B+ | 68 | 59.0 | good | mixed | — | 37.5 | -1.55 | 1.42 | -1.55 | 23.9 | some_favorable_move_then_stopped+no_historical_analogue | no_history | bad_structure_call |
| CRCLUSDT | 2026-08-12 14:50 | 2026-08-12 14:55 | 2026-08-13 19:04 | long | ema_pullback | 69.8 | 73.78 | 68.4 | 71.5 | 72.4 | — | C | 54 | 59.3 | neutral | mixed | — | 45.2 | 5.70 | 5.70 | -0.43 | 28.1 | closed_at_tp2+weak_structure,no_historical_analogue | weak_structure,no_history | perfect_trade |
| LITEUSDT | 2026-08-12 13:17 | 2026-08-12 13:29 | 2026-08-12 13:40 | long | bos_pullback | 892.5 | 846.79 | 855 | 930 | 955 | — | B+ | 73 | 70.1 | excellent | mixed | — | 35.3 | -5.12 | 0.84 | -5.12 | 0.2 | immediate_reversal+no_historical_analogue,scanner_outage_corrupted | no_history | infrastructure_failure |
| CLUSDT | 2026-08-12 11:49 | 2026-08-12 11:55 | 2026-08-13 08:38 | long | trend_continuation_other | 82.55 | 80.92 | 81 | 84 | 85 | 86.5 | B | 62 | 59.8 | neutral | mixed | — | 42.0 | -1.98 | 0.28 | -1.98 | 20.7 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | bad_structure_call |
| HOLOUSDT | 2026-08-12 10:15 | 2026-08-12 10:21 | 2026-08-12 18:28 | long | bos_pullback | 0.07725 | 0.07171 | 0.074 | 0.0825 | 0.0865 | 0.09 | B | 64 | 63.5 | good | mixed | — | 35.3 | -7.17 | 0.63 | -7.17 | 8.1 | immediate_reversal+no_historical_analogue,scanner_outage_corrupted | no_history,negative_cmf,risk_penalty_applied | infrastructure_failure |
| DOGEUSDT | 2026-08-12 08:37 | 2026-08-12 08:43 | 2026-08-12 21:31 | long | ema_pullback | 0.0714 | 0.0696 | 0.06975 | 0.0735 | 0.07485 | 0.0762 | B | 56 | 61.6 | good | mixed | — | 29.8 | -2.52 | 1.06 | -2.52 | 12.8 | some_favorable_move_then_stopped+no_historical_analogue | no_history | bad_structure_call |
| VELVETUSDT | 2026-08-12 08:02 | 2026-08-12 08:08 | 2026-08-12 18:28 | long | bos_pullback | 0.5505 | 0.7007 | 0.505 | 0.595 | 0.628 | 0.679 | B | 63 | 62.7 | good | mixed | — | 44.4 | 27.28 | 27.28 | -0.45 | 10.3 | ran_to_tp3+no_historical_analogue,scanner_outage_corrupted | no_history,risk_penalty_applied | infrastructure_failure |
| NEARUSDT | 2026-08-12 07:56 | 2026-08-12 08:02 | 2026-08-21 07:40 | long | bos_pullback | 1.6425 | 1.862 | 1.595 | 1.69 | 1.72 | 1.76 | B | 61 | 58.3 | excellent | mixed | — | 49.0 | 13.36 | 13.36 | -1.80 | 215.6 | ran_to_tp3+no_historical_analogue,scanner_outage_corrupted | no_history,negative_cmf | infrastructure_failure |
| BZUSDT | 2026-08-12 07:31 | 2026-08-12 07:37 | 2026-08-13 08:38 | long | trend_continuation_other | 87.6 | 85.83 | 85.9 | 89.5 | 91 | 92.9 | B+ | 65 | 60.3 | neutral | mixed | — | 32.3 | -2.02 | 0.60 | -2.02 | 25.0 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history,funding_elevated | bad_structure_call |
| SKHYUSDT | 2026-08-12 05:26 | 2026-08-12 05:44 | 2026-08-12 13:52 | long | breakout_chase | 143.9 | 152 | 139.5 | 148.5 | 152 | — | B | 63 | 60.7 | excellent | mixed | — | 42.0 | 5.63 | 5.63 | 0.51 | 8.1 | closed_at_tp2+no_historical_analogue | no_history | perfect_trade |
| HYPEUSDT | 2026-08-11 19:18 | 2026-08-11 19:24 | 2026-08-12 11:20 | short | ema_pullback | 54.3 | 55.689 | 55.65 | 52.6 | 51.4 | 49.4 | B | 64 | 54.6 | excellent | mixed | — | 42.0 | -2.56 | 0.34 | -2.56 | 15.9 | immediate_reversal+rsi_chop_zone,no_historical_analogue,short_direction | rsi_chop_30_49,no_history | bad_structure_call |
| SOLUSDT | 2026-08-11 19:11 | 2026-08-11 19:18 | 2026-08-12 09:29 | short | ema_pullback | 75.15 | 76.68 | 76.55 | 73.9 | 72.6 | 71 | B+ | 65 | 54.9 | excellent | mixed | — | 32.5 | -2.04 | 0.01 | -2.04 | 14.2 | immediate_reversal+rsi_chop_zone,short_direction | rsi_chop_30_49 | bad_structure_call |
| SNDKUSDT | 2026-08-11 18:14 | 2026-08-11 18:32 | 2026-08-12 12:54 | long | bos_pullback | 1263 | 1342.1 | 1233.5 | 1290 | 1315 | 1340 | B | 62 | 59.6 | excellent | mixed | — | 37.5 | 6.26 | 6.26 | 0.19 | 18.4 | ran_to_tp3+no_historical_analogue | no_history | perfect_trade |
| SNXXUSDT | 2026-08-11 17:09 | 2026-08-11 17:15 | 2026-08-12 05:26 | short | bos_pullback | 9.825 | 10.37 | 10.35 | 9.35 | 8.85 | 8.35 | B | 55 | 54.5 | good | mixed | — | 32.3 | -5.55 | 0.46 | -5.55 | 12.2 | immediate_reversal+no_historical_analogue,short_direction,scanner_outage_corrupted | no_history,risk_penalty_applied | infrastructure_failure |
| RKLBUSDT | 2026-08-11 16:57 | 2026-08-11 17:03 | 2026-08-11 18:49 | short | bos_pullback | 78.1 | — | 80.15 | 75.8 | 73.5 | 71.5 | B+ | 68 | 58.9 | good | mixed | — | 35.3 | -2.66 | 0.41 | -2.66 | 1.8 | immediate_reversal+rsi_chop_zone,no_historical_analogue,short_direction | rsi_chop_30_49,no_history | bad_structure_call |
| DRAMUSDT | 2026-08-11 15:46 | 2026-08-11 15:52 | 2026-08-12 05:26 | short | ema_pullback | 50.875 | 52.58 | 51.75 | 49.8 | 48.6 | — | B | 59 | 56.0 | neutral | mixed | — | 34.9 | -3.35 | 0.85 | -3.35 | 13.6 | immediate_reversal+weak_structure,no_historical_analogue,short_direction,scanner_outage_corrupted | weak_structure,no_history | infrastructure_failure |
| HYPEUSDT | 2026-08-11 13:11 | 2026-08-11 13:17 | 2026-08-11 15:35 | long | ema_pullback | 55.05 | — | 54.25 | 55.75 | 56.4 | 57.1 | B | 57 | 54.2 | neutral | mixed | — | 42.0 | -1.64 | -0.00 | -1.64 | 2.3 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | bad_structure_call |
| SKHYNIXUSDT | 2026-08-11 09:49 | 2026-08-11 09:55 | 2026-08-12 05:26 | short | ema_pullback | 1008.5 | 1058.89 | 1037.5 | 991.7 | 964 | — | B | 55 | 60.4 | neutral | mixed | — | 37.5 | -5.00 | 0.09 | -5.00 | 19.5 | immediate_reversal+rsi_chop_zone,weak_structure,no_historical_analogue,short_direction,scanner_outage_corrupted | rsi_chop_30_49,weak_structure,no_history | infrastructure_failure |
| SOLUSDT | 2026-08-10 05:47 | 2026-08-10 05:50 | 2026-08-11 15:40 | long | ema_pullback | 76.5 | — | 74.9 | 78.2 | 79.5 | — | C | 45 | 70.4 | — | risk_on | — | 32.5 | -2.21 | 0.51 | -2.21 | 33.8 | immediate_reversal+weak_structure | weak_structure | bad_structure_call |
| 1000PEPEUSDT | 2026-08-10 05:47 | 2026-08-10 05:50 | 2026-08-13 00:20 | long | ema_pullback | 0.0029 | 0.0026833 | 0.00282 | 0.00297 | 0.00305 | 0.00315 | B | 64 | 63.7 | — | risk_on | — | 40.7 | -7.47 | 0.15 | -7.47 | 66.5 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | bad_structure_call |
| BTCUSDT | 2026-08-10 05:47 | 2026-08-10 05:50 | 2026-08-11 07:11 | long | ema_pullback | 65000 | — | 64350 | 65650 | 66300 | 67200 | B+ | 69 | 63.4 | — | risk_on | — | 35.3 | -1.61 | 0.24 | -1.61 | 25.3 | immediate_reversal+weak_structure,scanner_outage_corrupted | weak_structure | infrastructure_failure |
| ETHUSDT | 2026-08-10 05:47 | 2026-08-10 05:50 | 2026-08-11 07:11 | long | ema_pullback | 1918 | — | 1888 | 1945 | 1965 | 1990 | B+ | 69 | 63.0 | — | risk_on | — | 25.9 | -2.32 | 0.27 | -2.32 | 25.3 | immediate_reversal+weak_structure,scanner_outage_corrupted | weak_structure | infrastructure_failure |
| BICOUSDT | 2026-08-09 05:40 | 2026-08-09 05:46 | 2026-08-10 05:12 | long | bos_pullback | 0.07085 | — | 0.0615 | 0.0785 | 0.085 | 0.095 | B+ | 71 | 62.0 | — | risk_on | — | 35.3 | -44.42 | -0.55 | -44.42 | 23.4 | immediate_reversal+no_historical_analogue,scanner_outage_corrupted | no_history,high_atr_extension,risk_penalty_applied | infrastructure_failure |
| ACEUSDT | 2026-08-09 05:28 | 2026-08-09 05:34 | 2026-08-14 09:57 | long | bos_pullback | 0.128 | 0.17896 | 0.1155 | 0.1425 | 0.155 | 0.1645 | B+ | 71 | 73.0 | — | risk_on | — | 40.7 | 39.81 | 39.81 | -0.99 | 124.4 | ran_to_tp3+no_historical_analogue | no_history,risk_penalty_applied | perfect_trade |
| BEATUSDT | 2026-08-09 05:08 | 2026-08-09 05:16 | 2026-08-10 05:12 | long | trend_continuation_other | 2.875 | — | 2.63 | 3.02 | 3.18 | 3.4 | B | 62 | 63.9 | — | risk_on | — | 35.3 | -9.50 | 8.56 | -9.50 | 23.9 | reached_tp1_then_stopped+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history,risk_penalty_applied | infrastructure_failure |
| QQQUSDT | 2026-08-08 10:23 | 2026-08-08 10:30 | 2026-08-13 23:06 | long | ema_pullback | 721.25 | 733.27 | 712.5 | 727 | 730 | — | B+ | 72 | 65.5 | — | risk_on | — | 44.4 | 1.67 | 1.67 | 0.07 | 132.6 | closed_at_tp2+no_historical_analogue | no_history | perfect_trade |
| PAXGUSDT | 2026-08-08 06:38 | 2026-08-08 06:45 | 2026-08-11 11:04 | long | trend_continuation_other | 4329 | — | 4280 | 4350 | 4382 | — | B+ | 71 | 67.0 | — | risk_on | — | 40.7 | 1.36 | 1.36 | 0.12 | 76.3 | closed_at_tp2+weak_structure,no_historical_analogue | weak_structure,no_history,high_atr_extension | perfect_trade |
| CRCLUSDT | 2026-08-08 06:38 | 2026-08-08 06:45 | 2026-08-11 13:46 | long | trend_continuation_other | 66.4 | — | 64.5 | 68 | 69.5 | — | C | 54 | 61.5 | — | risk_on | — | 45.2 | 5.24 | 5.24 | 0.48 | 79.0 | closed_at_tp2+weak_structure,no_historical_analogue | weak_structure,no_history | perfect_trade |
| ACEUSDT | 2026-08-07 19:47 | 2026-08-07 19:53 | 2026-08-08 10:30 | long | bos_pullback | 0.1145 | — | 0.1035 | 0.125 | 0.136 | 0.144 | B | 61 | 58.0 | — | risk_on | — | 40.7 | -9.66 | -0.69 | -9.66 | 14.6 | immediate_reversal+no_historical_analogue | no_history,risk_penalty_applied,liquidity_stress,funding_elevated | bad_structure_call |
| ZECUSDT | 2026-08-07 19:40 | 2026-08-07 19:47 | 2026-08-11 07:11 | long | trend_continuation_other | 511.75 | — | 498 | 524 | 535 | — | B+ | 67 | 60.1 | — | risk_on | — | 42.0 | -4.36 | 0.40 | -4.36 | 83.4 | immediate_reversal+weak_structure,no_historical_analogue,scanner_outage_corrupted | weak_structure,no_history | infrastructure_failure |
| CYSUSDT | 2026-08-07 14:34 | 2026-08-07 14:41 | 2026-08-07 16:37 | long | bos_pullback | 0.8175 | — | 0.735 | 0.88 | 0.93 | — | — | — | 61.0 | — | risk_on | — | 40.7 | 19.67 | 19.67 | 0.48 | 1.9 | closed_at_tp2+no_historical_analogue | no_history,risk_penalty_applied | perfect_trade |
| EWYUSDT | 2026-08-05 19:36 | 2026-08-05 19:42 | 2026-08-07 14:27 | long | trend_continuation_other | 170.25 | — | 165.5 | 175 | 178.5 | — | — | — | 60.8 | — | risk_on | — | 40.7 | -3.65 | 0.15 | -3.65 | 42.7 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | bad_structure_call |
| SNDKUSDT | 2026-08-05 19:36 | 2026-08-05 19:42 | 2026-08-07 11:51 | long | trend_continuation_other | 1387.5 | — | 1340 | 1430 | 1460 | — | — | — | 60.3 | — | risk_on | — | 37.5 | -7.00 | 0.01 | -7.00 | 40.1 | immediate_reversal+weak_structure,no_historical_analogue | weak_structure,no_history | bad_structure_call |
| DRAMUSDT | 2026-08-05 19:25 | 2026-08-05 19:31 | 2026-08-07 11:51 | long | bos_pullback | 54.45 | — | 52.1 | 56.5 | 58 | — | — | — | 63.8 | — | risk_on | — | 34.9 | -5.31 | 0.39 | -5.31 | 40.3 | immediate_reversal+no_historical_analogue | no_history | bad_structure_call |
| NVDAUSDT | 2026-08-05 11:21 | 2026-08-05 11:25 | 2026-08-12 21:02 | long | trend_continuation_other | 214.7 | 223.53 | 209.9 | 219.3 | 223.5 | — | — | — | 57.3 | — | mixed | — | 49.0 | 4.11 | 4.11 | 0.53 | 177.6 | closed_at_tp2+weak_structure,no_historical_analogue | weak_structure,no_history | perfect_trade |


## SECTION 3 — EVERY WIN

n(wins)=45, n(losses)=71. Frequency = how many winners (losers) had the property; 'known' denominators differ because some indicators were not captured on the oldest trades. Ranked by (winner freq − loser freq).

| Characteristic | Winners with it | Losers with it | Δ pp | Odds ratio | Fisher p |
|---|---|---|---|---|---|
| MFI > 80 | 7/38 (18.4%) | 0/53 (0.0%) | 18.4 | 25.48 | 0.0016 |
| regime = mixed | 37/45 (82.2%) | 46/71 (64.8%) | 17.4 | 2.51 | 0.0571 |
| RSI 50–70 | 37/43 (86.0%) | 47/68 (69.1%) | 16.9 | 2.76 | 0.068 |
| direction = long | 42/45 (93.3%) | 55/71 (77.5%) | 15.8 | 4.07 | 0.0374 |
| entry_quality = excellent | 10/39 (25.6%) | 8/60 (13.3%) | 12.3 | 2.24 | 0.1814 |
| volume_score ≥ 8 | 28/45 (62.2%) | 37/71 (52.1%) | 10.1 | 1.51 | 0.339 |
| structure_score ≥ 9 | 19/45 (42.2%) | 25/71 (35.2%) | 7.0 | 1.34 | 0.5562 |
| Price beyond all 3 EMAs in trade direction | 34/41 (82.9%) | 52/68 (76.5%) | 6.4 | 1.49 | 0.4763 |
| Bollinger %B > 0.95 | 2/38 (5.3%) | 0/53 (0.0%) | 5.3 | 7.33 | 0.1717 |
| FVG active at entry (post-capture trades only) | 11/33 (33.3%) | 14/45 (31.1%) | 2.2 | 1.11 | 1.0 |
| momentum_score ≥ 14 | 33/45 (73.3%) | 51/71 (71.8%) | 1.5 | 1.08 | 1.0 |
| MACD hist > 0 | 32/38 (84.2%) | 44/53 (83.0%) | 1.2 | 1.09 | 1.0 |
| |ATR-dist. from EMA20| > 2.5 | 1/43 (2.3%) | 1/68 (1.5%) | 0.8 | 1.6 | 1.0 |
| funding_score ≥ 8 (non-crowded) | 43/45 (95.6%) | 68/71 (95.8%) | -0.2 | 0.95 | 1.0 |
| RSI ≥ 70 | 1/43 (2.3%) | 3/68 (4.4%) | -2.1 | 0.52 | 1.0 |
| CMF > 0 | 26/38 (68.4%) | 38/53 (71.7%) | -3.3 | 0.86 | 0.8175 |
| trend_score ≥ 22 | 15/45 (33.3%) | 27/71 (38.0%) | -4.7 | 0.81 | 0.6933 |
| confidence ≥ 65 | 15/43 (34.9%) | 27/68 (39.7%) | -4.8 | 0.81 | 0.6897 |
| history present | 3/45 (6.7%) | 10/71 (14.1%) | -7.4 | 0.44 | 0.3652 |
| entry_quality = good | 6/39 (15.4%) | 14/60 (23.3%) | -7.9 | 0.6 | 0.4445 |
| score ≥ 65 | 4/45 (8.9%) | 12/71 (16.9%) | -8.0 | 0.48 | 0.2771 |
| risk penalty applied (risk_score ≤ -3) | 7/45 (15.6%) | 18/71 (25.4%) | -9.8 | 0.54 | 0.252 |
| ADX 20–50 | 26/43 (60.5%) | 48/68 (70.6%) | -10.1 | 0.64 | 0.3053 |
| ADX ≥ 35 | 10/43 (23.3%) | 23/68 (33.8%) | -10.5 | 0.59 | 0.2891 |
| RSI < 50 | 5/43 (11.6%) | 18/68 (26.5%) | -14.9 | 0.37 | 0.0912 |

**Not measurable per trade (not stored):** bullish/bearish BOS, CHoCH, order blocks, liquidity sweeps, OBV, EMA-stack order (only sign of distance to EMA20/50/200), swing-level breaks → **INSUFFICIENT DATA**.
**Confidence:** HIGH for the strongest single characteristic; most rows are not significant at this n. **Recommendation:** do not derive a 'winner recipe' from frequencies; only entry_quality/RSI-zone survive testing (see §7, §13).

## SECTION 4 — EVERY LOSS

n(losses)=71. Categories overlap (multi-label), ranked by frequency.

| Loss category | n | % of losses | Avg return | Avg MFE | Avg MAE | Avg conf |
|---|---|---|---|---|---|---|
| Never reached TP1 (all no-TP1 losses) | 63 | 88.7% | -5.58% | 0.49% | -5.58% | 63.1 |
| Immediate reversal (no TP1, MFE<1%) | 57 | 80.3% | -5.78% | 0.28% | -5.78% | 63.4 |
| Weak structure (structure_score<9) | 46 | 64.8% | -6.15% | 1.07% | -6.15% | 61.0 |
| Low-volume setup (volume_score<8) | 34 | 47.9% | -5.61% | 1.15% | -5.61% | 62.4 |
| Exit inside a monitoring outage | 30 | 42.3% | -9.45% | 1.54% | -9.45% | 63.2 |
| trend_score ≥ 22 | 27 | 38.0% | -5.86% | 0.99% | -5.86% | 63.9 |
| RSI chop zone 30–49 | 18 | 25.4% | -8.33% | 0.99% | -8.33% | 60.9 |
| Short direction | 16 | 22.5% | -9.29% | 0.87% | -9.29% | 59.7 |
| Negative CMF | 15 | 21.1% | -8.89% | 2.03% | -8.89% | 58.4 |
| Hit TP1 then stopped | 7 | 9.9% | -8.24% | 4.23% | -8.24% | 59.4 |
| Gap/slippage through stop (≥5%) | 7 | 9.9% | -21.05% | 2.86% | -21.05% | 56.3 |
| Overbought entry (RSI≥70 or MFI>80) | 3 | 4.2% | -18.43% | 0.96% | -18.43% | 67.7 |
| Hit TP2 then reversed | 1 | 1.4% | -18.79% | 4.89% | -18.79% | 61.0 |
| High ATR extension (>2.5 ATR from EMA20) | 1 | 1.4% | -44.42% | -0.55% | -44.42% | 71.0 |
| Late entry (entry_quality=late) | 0 | 0.0% | —% | —% | —% | — |

**Not measurable (no stored label):** countertrend entry (no per-trade HTF-disagreement flag), liquidity sweep, bad direction vs. reversal cause → **INSUFFICIENT DATA**. Late entry is n=0 by construction (entry_quality='late' blocks plan issuance).
**Confidence:** HIGH for the lifecycle counts (they are facts); LOW for causal readings. **Recommendation:** the dominant failure is 'wrong from the first candle' — attack entry selection/quality evidence, not exit management.

## SECTION 5 — FAILURE PATTERN ENGINE AUDIT

| Lifecycle category (mutually exclusive) | n | % of losses | Avg return |
|---|---|---|---|
| immediate_reversal | 57 | 80.3% | -5.78 |
| reached_tp1_then_stopped | 7 | 9.9% | -8.24 |
| some_favorable_move_then_stopped | 6 | 8.5% | -3.60 |
| hit_tp2_then_reversed | 1 | 1.4% | -18.79 |

| Overlay (multi-label) | n | % of losses | Avg return |
|---|---|---|---|
| Gap through stop (slippage ≥5%) | 7 | 9.9% | -21.05 |
| Infrastructure failure / scanner missed stop (exit inside outage) | 30 | 42.3% | -9.45 |
| Late invalidation | 0 | 0.0% | — |

**INSUFFICIENT DATA** (no labels in DB): false breakout, mean-reversion failure, trend exhaustion, distribution. 'Late invalidation' is not a loss category here — invalidated plans carry no realized return (see §23).
**Confidence:** HIGH (counts). **Recommendation:** none beyond §4; keep failure-pattern leaderboard as analytics.

## SECTION 6 — WIN PATTERN ENGINE

| Strategy family (all entered) | n | Wins | Success rate | 95% CI | Avg ret | PF |
|---|---|---|---|---|---|---|
| breakout_chase | 3 | 2 | 66.7% | 20.8–93.9% | 1.62 | 1.90 |
| bos_pullback | 13 | 6 | 46.2% | 23.2–70.9% | 3.08 | 1.50 |
| fvg_continuation | 25 | 11 | 44.0% | 26.7–62.9% | 3.20 | 2.42 |
| trend_continuation_other | 28 | 11 | 39.3% | 23.6–57.6% | -0.51 | 0.87 |
| ema_pullback | 47 | 15 | 31.9% | 20.4–46.2% | 4.01 | 2.08 |

| Winner lifecycle | n | % of wins |
|---|---|---|
| closed_at_tp2 | 31 | 68.9% |
| ran_to_tp3 | 14 | 31.1% |

Short winners (possible 'short squeeze' analogue): n=3 of 19 shorts. **INSUFFICIENT DATA** for: liquidity reclaim, news momentum, range breakout, true breakout vs. pullback (no per-trade BOS/range labels; strategy classes are indicator proxies).
**Confidence:** LOW-MEDIUM (small per-family n). **Recommendation:** analytics only; do not rank strategies for trading until each family has n≥30.

## SECTION 7 — ENTRY QUALITY AUDIT

| EQ | n | W | L | Win% (Wilson) | TP1% | TP2% | TP3% | Avg ret | Median ret | PF | MFE | MAE | Median hold h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| excellent | 18 | 10 | 8 | 55.6% (33.7–75.4) | 55.6 | 55.6 | 27.8 | 7.024 | 4.277 | 6.89 | 8.385 | -1.528 | 82.663 |
| good | 20 | 6 | 14 | 30.0% (14.5–51.9) | 40.0 | 35.0 | 10.0 | -0.481 | -2.147 | 0.85 | 3.412 | -3.393 | 10.206 |
| neutral | 61 | 23 | 38 | 37.7% (26.6–50.3) | 44.3 | 37.7 | 9.8 | 3.409 | -1.635 | 1.85 | 8.061 | -4.14 | 28.143 |
| late | 0 |  |  |  |  |  |  |  |  |  |  |  |  |
| exhausted | 0 |  |  |  |  |  |  |  |  |  |  |  |  |

Trades with no entry_quality (pre-launch, n=17) excluded above. `late`/`exhausted` n=0 **by construction** (the scanner blocks issuing a plan in those states) — they can never appear in TradeOutcome.
| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| excellent vs all others | 18/81 | 55.6% / 35.8% | 2.24 | [0.8, 6.31] | 0.1814 | 0.0172 | NOT SIGNIFICANT |
| excellent vs good | 18/20 | 55.6% / 30.0% | 2.92 | [0.77, 11.07] | 0.1881 | 0.0486 | NOT SIGNIFICANT |
| good vs neutral | 20/61 | 30.0% / 37.7% | 0.71 | [0.24, 2.1] | 0.6002 | 0.0035 | NOT SIGNIFICANT |

**Is entry quality predictive?** Excellent vs rest: OR=2.24 (CI 0.8–6.31), p=0.1814; excellent vs good: p=0.1881; good vs neutral: OR=0.71, p=0.6002 — the ordering is NOT monotonic (good does not beat neutral). **Confidence:** NOT SIGNIFICANT for 'excellent is special'. **Recommendation:** keep classifier unchanged. 'Excellent' is directionally favorable (n=18, PF 6.89) but NOT statistically distinguishable at this n — do not call it validated.

## SECTION 8 — CONFIDENCE CALIBRATION

| Bucket | n | Predicted | Observed win% (Wilson) | Cal. err (pp) | TP1% | TP2% | TP3% | Avg ret | Median | PF | Avg R (EV realized) | Brier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| <50 | 3 | 46.7% | 0.0% (0–56.2) | 46.7 | 33.3 | 0.0 | 0.0 | -10.17 | -7.356 | 0.00 | -1.94 | 0.218 |
| 50–54 | 7 | 52.9% | 57.1% (25.0–84.2) | -4.2 | 71.4 | 57.1 | 0.0 | 0.957 | 2.926 | 1.26 | 0.15 | 0.254 |
| 55–59 | 22 | 57.4% | 31.8% (16.4–52.7) | 25.6 | 40.9 | 31.8 | 4.5 | 4.661 | -2.936 | 1.80 | -2.05 | 0.283 |
| 60–64 | 37 | 62.5% | 45.9% (31.0–61.6) | 16.6 | 54.1 | 48.6 | 21.6 | 2.887 | -1.266 | 1.95 | 1.38 | 0.274 |
| 65–69 | 29 | 66.7% | 37.9% (22.7–56.0) | 28.8 | 34.5 | 37.9 | 13.8 | 3.149 | -1.007 | 2.97 | 2.27 | 0.322 |
| 70–74 | 12 | 71.6% | 33.3% (13.8–60.9) | 38.3 | 41.7 | 33.3 | 8.3 | 1.291 | -1.458 | 1.23 | -0.05 | 0.371 |
| 75+ | 1 | 76.0% | 0.0% (0–79.3) | 76.0 | 0.0 | 0.0 | 0.0 | -1.069 | -1.069 | 0.00 | -1.11 | 0.578 |

Overall Brier=0.299 vs constant-base-rate Brier=0.2373 (n=111); ECE≈24.5pp. Reliability diagram (■ predicted, ▒ observed):
```
   <50 n=3   pred ■■■■■■■■■■■■■          46.7%
              obs                          0.0%
 50–54 n=7   pred ■■■■■■■■■■■■■■■        52.9%
              obs  ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒       57.1%
 55–59 n=22  pred ■■■■■■■■■■■■■■■■       57.4%
              obs  ▒▒▒▒▒▒▒▒▒              31.8%
 60–64 n=37  pred ■■■■■■■■■■■■■■■■■      62.5%
              obs  ▒▒▒▒▒▒▒▒▒▒▒▒▒          45.9%
 65–69 n=29  pred ■■■■■■■■■■■■■■■■■■■    66.7%
              obs  ▒▒▒▒▒▒▒▒▒▒             37.9%
 70–74 n=12  pred ■■■■■■■■■■■■■■■■■■■■   71.6%
              obs  ▒▒▒▒▒▒▒▒▒              33.3%
   75+ n=1   pred ■■■■■■■■■■■■■■■■■■■■■  76.0%
              obs                          0.0%
```
Spearman(confidence, return)=0.088, p=0.357 (n=111). **Overconfident** wherever predicted > observed (most buckets ≥55). Confidence is not monotonic in outcome, so it should be treated as a ranking-ish heuristic, not a probability. Model Brier 0.299 is WORSE than the constant base-rate Brier 0.2373: as a probability, confidence has no demonstrated skill (Spearman with return not significant). **Confidence:** MEDIUM (n=111). **Recommendation:** display calibrated confidence + interval (already built); do not rescale the underlying formula until n≥100 per used bucket.

## SECTION 9 — SCORE BREAKDOWN AUDIT

| Component | n | min/Q1/med/Q3/max | win% high vs low (median split) | loss% high-half | Spearman vs ret | p | OR (high vs low) | MI (bits) | Confidence |
|---|---|---|---|---|---|---|---|---|---|
| trend | 116 | 12.8/18.5/20.1/23.5/25.0 | 36.8% vs 40.7% | 63.2% | -0.044 | 0.637 | 0.85 | 0.0011 | NOT SIGNIFICANT |
| momentum | 116 | 8.0/11.0/15.0/15.0/15.0 | — | — | -0.088 | 0.348 | — | — | n/a |
| volume | 116 | 2.0/7.0/8.0/10.0/10.0 | 37.5% vs 40.0% | 62.5% | -0.025 | 0.787 | 0.9 | 0.0005 | NOT SIGNIFICANT |
| funding | 116 | 0.0/10.0/10.0/10.0/10.0 | — | — | -0.003 | 0.978 | — | — | n/a |
| structure | 116 | 6.0/6.0/6.0/11.0/11.0 | 43.2% vs 36.1% | 56.8% | 0.089 | 0.344 | 1.34 | 0.0036 | NOT SIGNIFICANT |
| history | 116 | -3.0/0.0/0.0/0.0/12.0 | 23.1% vs 40.8% | 76.9% | 0.041 | 0.665 | 0.44 | 0.0101 | NOT SIGNIFICANT |
| regime | 116 | 0.0/0.0/0.0/5.0/5.0 | 24.2% vs 44.6% | 75.8% | -0.217 | 0.019 | 0.4 | 0.0267 | LOW (suggestive only) |
| risk penalty | 116 | -8.0/0.0/0.0/0.0/0.0 | — | — | 0.199 | 0.032 | — | — | n/a |
| sentiment | 116 | constant=0.0 | — | — | — | — | — | — | INSUFFICIENT VARIATION |
| ML score | 116 | -2.6/0.0/0.0/0.0/0.9 | 0.0% vs 40.5% | 100.0% | -0.097 | 0.302 | 0.13 | 0.0314 | INSUFFICIENT DATA |
| liquidity | 116 | -5.0/0.0/0.0/0.0/0.0 | — | — | 0.153 | 0.102 | — | — | n/a |
| expected value (stored) | 26 | post-V2.1 only |  |  | -0.027 | 0.894 | — | — | NOT SIGNIFICANT |
| reliability (hindsight) | 116 | all-data |  |  | 0.531 | 0.0 | — | — | hindsight-biased |

Does increasing a component improve returns? Only where Spearman p<0.05 AND the median-split Fisher p<0.05 agree. **SHAP: not available** (no fitted production model on TradeOutcome features — the XGBoost models use MarketSnapshot features). Permutation importance from a cross-validated linear model is in §10.
**Recommendation:** none supported by this table alone; see §10.

## SECTION 10 — SCORE WEIGHT RECOMMENDATION (NO EDITS TO scoring.py)

| Component | Current point range | Std. logit coef | Bootstrap 95% CI (300×) | CI excludes 0? | CV permutation importance (ΔAUC) | Proposed |
|---|---|---|---|---|---|---|
| trend | 0–25 | 0.076 | [-0.294, 0.542] | no | -0.0245 | NO CHANGE SUPPORTED |
| momentum | 0–15 | 0.088 | [-0.404, 0.620] | no | -0.0164 | NO CHANGE SUPPORTED |
| volume | 0–10 | 0.19 | [-0.249, 0.716] | no | -0.0064 | NO CHANGE SUPPORTED |
| funding | 0–10 | 0.083 | [-0.677, 0.545] | no | -0.0156 | NO CHANGE SUPPORTED |
| structure | 0–15 | 0.244 | [-0.167, 0.650] | no | 0.0103 | NO CHANGE SUPPORTED |
| history | −15..+15 | -0.385 | [-0.901, 0.008] | no | 0.0371 | NO CHANGE SUPPORTED |
| regime | −5..+5 | -0.4 | [-0.799, 0.018] | no | 0.0391 | NO CHANGE SUPPORTED |
| risk penalty | −20..0 | 0.318 | [-0.017, 0.794] | no | 0.0248 | NO CHANGE SUPPORTED |
| ML score | −10..+8 | -0.123 | [-0.561, 0.544] | no | -0.0027 | NO CHANGE SUPPORTED |
| liquidity | −5..0 | 0.294 | [-0.002, 0.576] | no | 0.0106 | NO CHANGE SUPPORTED |

L2-logistic on standardized components, n=116, features=10. **Cross-validated AUC = 0.553 ± 0.101** (5-fold×10; 0.5 = no skill). Constant components were excluded (INSUFFICIENT VARIATION).
**Expected improvement:** cannot be estimated — the linear model over the deterministic components has CV-AUC 0.553, i.e. the current score components (as a set) carry little out-of-sample discrimination on win/loss. **Confidence:** INSUFFICIENT DATA — 0 of 10 coefficients have CIs excluding zero. **Recommendation:** propose NO weight change; re-run at n≥200.

## SECTION 11 — TREND ANALYSIS

| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| trend_score ≥ 22 | 42/74 | 35.7% / 40.5% | 0.81 | [0.37, 1.78] | 0.6933 | 0.0016 | NOT SIGNIFICANT |
| ADX 20–50 | 74/37 | 35.1% / 45.9% | 0.64 | [0.29, 1.42] | 0.3053 | 0.0078 | NOT SIGNIFICANT |
| ADX ≥ 35 | 33/78 | 30.3% / 42.3% | 0.59 | [0.25, 1.41] | 0.2891 | 0.0093 | NOT SIGNIFICANT |
| Price beyond all 3 EMAs in trade direction | 86/23 | 39.5% / 30.4% | 1.49 | [0.56, 4.01] | 0.4763 | 0.0043 | NOT SIGNIFICANT |

**trend_score buckets**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| 0–15 | 12 | 33.3% | -0.18% | 0.95 | -2.64% |
| 15–20 | 39 | 46.2% | 2.60% | 1.78 | -0.99% |
| 20–23 | 33 | 33.3% | 5.39% | 2.57 | -2.21% |
| 23–26 | 32 | 37.5% | 0.68% | 1.16 | -1.66% |

**ADX buckets**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| 0–20 | 31 | 45.2% | 2.42% | 1.79 | -1.02% |
| 20–35 | 47 | 40.4% | 4.81% | 2.46 | -1.46% |
| 35–50 | 27 | 25.9% | -0.40% | 0.90 | -2.02% |
| 50–200 | 6 | 50.0% | 0.12% | 1.01 | -2.01% |

Spearman(trend_score, return)=-0.044, p=0.637 (n=116). Trend is a near-universal gate (median trend_score ≈ 20.15), so it cannot discriminate winners from losers; stratified by entry_quality its sign flips (see feature audit). Bullish/bearish BOS, exhaustion vs continuation labels: **INSUFFICIENT DATA**. **Confidence:** NOT SIGNIFICANT. **Recommendation:** treat trend as a gate; do not change its weight (no evidence either way).

## SECTION 12 — STRUCTURE ANALYSIS

| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| structure_score ≥ 9 | 44/72 | 43.2% / 36.1% | 1.34 | [0.62, 2.89] | 0.5562 | 0.0036 | NOT SIGNIFICANT |
| FVG active at entry (post-capture trades only) | 25/53 | 44.0% / 41.5% | 1.11 | [0.42, 2.89] | 1.0 | 0.0004 | NOT SIGNIFICANT |

**structure_score buckets**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| 0–6 | 0 |  |  |  |  |
| 6–9 | 72 | 36.1% | 2.51% | 1.64 | -2.00% |
| 9–12 | 44 | 43.2% | 2.69% | 1.82 | -1.08% |
| 12–20 | 0 |  |  |  |  |

**Distance from entry to nearest opposing swing level (%; post-capture trades only)**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| 0–2 | 26 | 46.2% | 2.35% | 1.54 | -1.01% |
| 2–5 | 21 | 61.9% | 9.66% | 6.12 | 2.83% |
| 5–10 | 11 | 18.2% | 1.67% | 1.34 | -3.44% |
| 10–1000 | 9 | 22.2% | -1.35% | 0.76 | -4.95% |

BOS, CHoCH, order blocks, liquidity sweeps as per-trade booleans: **INSUFFICIENT DATA** — never persisted (order-block detection does not exist in the codebase). Only `structure_score` (aggregate) and FVG-at-entry (post-capture subset) are testable. **Recommendation:** capture BOS/CHoCH/sweep booleans at issuance (analytics only) so this section can be answered at n≥200.

## SECTION 13 — MOMENTUM ANALYSIS

| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| RSI 50–70 | 84/27 | 44.0% / 22.2% | 2.76 | [1.01, 7.52] | 0.068 | 0.0282 | LOW (suggestive only) |
| RSI < 50 | 23/88 | 21.7% / 43.2% | 0.37 | [0.12, 1.07] | 0.0912 | 0.0244 | LOW (suggestive only) |
| RSI ≥ 70 | 4/107 | 25.0% / 39.3% | 0.52 | [0.05, 5.13] | 1.0 | 0.0023 | INSUFFICIENT DATA |
| CMF > 0 | 64/27 | 40.6% / 44.4% | 0.86 | [0.34, 2.12] | 0.8175 | 0.0009 | NOT SIGNIFICANT |
| MFI > 80 | 7/84 | 100.0% / 36.9% | 25.48 | [1.41, 461.35] | 0.0016 | 0.1034 | INSUFFICIENT DATA |
| Bollinger %B > 0.95 | 2/89 | 100.0% / 40.4% | 7.33 | [0.34, 157.16] | 0.1717 | 0.0282 | INSUFFICIENT DATA |
| MACD hist > 0 | 76/15 | 42.1% / 40.0% | 1.09 | [0.35, 3.37] | 1.0 | 0.0002 | NOT SIGNIFICANT |

**RSI(14, 4h)**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| 0–30 | 0 |  |  |  |  |
| 30–40 | 1 | 0.0% | -2.76% | 0.00 | -2.76% |
| 40–50 | 22 | 22.7% | -4.29% | 0.36 | -2.35% |
| 50–60 | 53 | 39.6% | 7.31% | 4.14 | -1.27% |
| 60–70 | 31 | 51.6% | 1.77% | 1.66 | 1.58% |
| 70–100 | 4 | 25.0% | -13.48% | 0.02 | -5.44% |

**MFI**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| 0–40 | 7 | 28.6% | -5.19% | 0.17 | -2.92% |
| 40–60 | 40 | 35.0% | 5.09% | 2.57 | -1.20% |
| 60–80 | 37 | 40.5% | 3.92% | 2.09 | -1.46% |
| 80–90 | 7 | 100.0% | 4.16% | — | 2.83% |
| 90–101 | 0 |  |  |  |  |

**CMF**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| -1–-0.1 | 9 | 22.2% | -6.55% | 0.07 | -2.15% |
| -0.1–0 | 18 | 55.6% | 11.62% | 3.99 | 4.30% |
| 0–0.1 | 33 | 30.3% | 2.92% | 1.85 | -1.55% |
| 0.1–0.2 | 16 | 37.5% | 0.26% | 1.09 | -2.35% |
| 0.2–1 | 15 | 66.7% | 6.04% | 7.38 | 5.44% |

**Bollinger %B**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| -1–0.2 | 1 | 0.0% | -1.14% | 0.00 | -1.14% |
| 0.2–0.5 | 14 | 21.4% | -8.20% | 0.04 | -3.49% |
| 0.5–0.8 | 61 | 47.5% | 7.40% | 4.64 | -0.59% |
| 0.8–1.0 | 15 | 40.0% | 0.38% | 1.09 | -2.98% |
| 1.0–5 | 0 |  |  |  |  |

**Stoch RSI**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| 0–0.2 | 12 | 41.7% | 7.16% | 7.41 | -0.59% |
| 0.2–0.5 | 33 | 30.3% | -0.43% | 0.89 | -2.21% |
| 0.5–0.8 | 35 | 37.1% | 0.75% | 1.13 | -1.64% |
| 0.8–1.01 | 31 | 48.4% | 6.24% | 3.39 | -0.95% |

**|ATR-distance from EMA20|**
| Range | n | Win rate | Avg ret | PF | Median ret |
|---|---|---|---|---|---|
| 0–0.5 | 46 | 32.6% | 5.04% | 2.17 | -1.52% |
| 0.5–1 | 31 | 38.7% | 2.07% | 1.92 | -1.55% |
| 1–2 | 32 | 46.9% | 1.20% | 1.39 | -1.88% |
| 2–10 | 2 | 50.0% | -21.53% | 0.03 | -21.53% |

OBV and momentum-divergence: **INSUFFICIENT DATA** (not stored). **Profitable ranges:** read directly from the bucket tables — only RSI 50–70 vs <50 and the chop-zone finding carry significance in this sample. **Recommendation:** shadow-mode a 'RSI 30–49' flag (already exists in red_flags); no score change.

## SECTION 14 — MARKET REGIME ANALYSIS

| Regime | n | Win rate (Wilson) | PF | Avg ret | Median | TP1% | Stop% | MAE |
|---|---|---|---|---|---|---|---|---|
| mixed | 83 | 44.6% (34.4–55.3) | 2.28 | 4.278 | -1.006 | 50.6 | 55.4 | -3.532 |
| risk_on | 33 | 24.2% (12.8–41.0) | 0.63 | -1.695 | -3.441 | 30.3 | 75.8 | -4.593 |

Confusion matrix (regime × outcome):

| Regime | Win | Loss | P(win|regime) |
|---|---|---|---|
| mixed | 37 | 46 | 44.6% |
| risk_on | 8 | 25 | 24.2% |

| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| regime=mixed vs risk_on | 83/33 | 44.6% / 24.2% | 2.51 | [1.02, 6.22] | 0.0571 | 0.0267 | LOW (suggestive only) |

**Unavailable regimes** (not produced by the engine, n=0): risk_off, trending, range, expansion, compression, mean_reversion, panic → **INSUFFICIENT DATA**. Regime is also confounded with time period (risk_on trades are early-sample). **Confidence:** LOW (suggestive only). **Recommendation:** do not gate on regime yet; track regime×direction as analytics.

## SECTION 15 — LONG VS SHORT

| Segment | n | Win% | PF | Avg ret | Median | TP1% | Stop% | MFE | MAE | Avg conf | Avg trend | Avg struct | Avg stop slip% | Med hold h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Long (all) | 97 | 43.3% | 2.59 | 4.563 | -1.143 | 48.5 | 56.7 | 7.97 | -3.055 | 63.293 | 20.767 | 7.804 | -1.52 | 28.823 |
| Short (all) | 19 | 15.8% | 0.03 | -7.55 | -3.351 | 26.3 | 84.2 | 1.005 | -7.811 | 59.474 | 18.134 | 8.368 | -7.56 | 28.603 |
| Long (ex-outage) | 56 | 35.7% | 1.3 | 0.723 | -1.502 | 39.3 | 64.3 | 3.432 | -2.484 | 62.627 | 20.771 | 7.786 | -0.96 | 6.024 |
| Short (ex-outage) | 8 | 37.5% | 0.56 | -0.504 | -0.972 | 37.5 | 62.5 | 0.952 | -1.125 | 60.875 | 19.304 | 10.375 | -0.11 | 15.061 |

long: entry_quality mix {'none': 17, 'neutral': 51, 'excellent': 15, 'good': 14}; failure lifecycle {'immediate_reversal': 44, 'reached_tp1_then_stopped': 5, 'some_favorable_move_then_stopped': 6}
short: entry_quality mix {'neutral': 10, 'good': 6, 'excellent': 3}; failure lifecycle {'immediate_reversal': 13, 'reached_tp1_then_stopped': 2, 'hit_tp2_then_reversed': 1}

| Regime × direction | n | Win% | Avg ret |
|---|---|---|---|
| risk_on/long | 33 | 24.2% | -1.695 |
| mixed/long | 64 | 53.1% | 7.789 |
| mixed/short | 19 | 15.8% | -7.55 |

| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| short vs long (all) | 19/97 | 15.8% / 43.3% | 0.25 | [0.07, 0.9] | 0.0374 | 0.035 | MEDIUM |
| short vs long (ex-outage) | 8/56 | 37.5% / 35.7% | 1.08 | [0.23, 5.0] | 1.0 | 0.0001 | INSUFFICIENT DATA |

Removing outage-corrupted exits leaves 8 of 19 shorts: win rate 37.5%, PF 0.56, avg -0.504% — versus longs ex-outage 35.7% (n=56). **Diagnosis:** the headline short collapse (15.8% win, avg -7.55%) is concentrated in outage-exit trades: 11 of 19 shorts exited inside a monitoring gap and ALL of them lost. Ex-outage, shorts are statistically indistinguishable from longs (p=1.0, n=8). So the evidence points to an EXECUTION/INFRASTRUCTURE explanation (gap exposure + slippage) at least as much as a SIGNAL one; a signal problem is NOT demonstrated. Regime cannot be separated (shorts exist only in 'mixed'). Caveat: the ex-outage short sample is n=8 — INSUFFICIENT DATA either way. **Confidence:** INSUFFICIENT DATA. **Recommendation:** keep the soft short flag; do NOT hard-disable shorts; re-test after the scanner runs continuously.

## SECTION 16 — SYMBOL RELIABILITY

n(symbols)=55, pooled win rate 38.8%. Tier rule (report-defined, not tuned): Trusted = n≥3 & Bayesian reliability≥50; Avoid = (n≥3 & 0 wins) or reliability<33; else Watchlist. Reliability = Beta-Binomial shrinkage (prior strength 10) — a single trade can never make a symbol 'Trusted'.

| Symbol | n | Wins | Win% | Avg ret | PF | Reliability | Avg conf | Avg EV(R) | % trades w/ risk flags | History avail. | Tier |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NVDAUSDT | 2 | 2 | 100.0% | 2.847 | — | 49.0 | 62.0 | — | 100% | no | Watchlist |
| NEARUSDT | 2 | 2 | 100.0% | 63.824 | — | 49.0 | 59.0 | -0.27 | 100% | no | Watchlist |
| BTWUSDT | 2 | 2 | 100.0% | 17.255 | — | 49.0 | 60.5 | — | 0% | no | Watchlist |
| SOXSUSDT | 2 | 2 | 100.0% | 4.105 | — | 49.0 | 64.5 | — | 100% | no | Watchlist |
| CRCLUSDT | 3 | 2 | 66.7% | 3.317 | 11.03 | 45.2 | 54.0 | -0.30 | 100% | no | Watchlist |
| SAMSUNGUSDT | 3 | 2 | 66.7% | 2.432 | 2.60 | 45.2 | 66.7 | — | 100% | no | Watchlist |
| LINKUSDT | 3 | 2 | 66.7% | 9.291 | 6.08 | 45.2 | 67.7 | — | 67% | no | Watchlist |
| QQQUSDT | 1 | 1 | 100.0% | 1.667 | — | 44.4 | 72.0 | — | 0% | no | Watchlist |
| VELVETUSDT | 1 | 1 | 100.0% | 27.284 | — | 44.4 | 63.0 | — | 0% | no | Watchlist |
| APRUSDT | 1 | 1 | 100.0% | 19.037 | — | 44.4 | 64.0 | — | 100% | no | Watchlist |
| FILUSDT | 1 | 1 | 100.0% | 14.898 | — | 44.4 | 69.0 | — | 100% | no | Watchlist |
| RIVERUSDT | 1 | 1 | 100.0% | 18.819 | — | 44.4 | 50.0 | 0.28 | 100% | no | Watchlist |
| XRPUSDT | 1 | 1 | 100.0% | 4.605 | — | 44.4 | 63.0 | -0.34 | 100% | yes | Watchlist |
| UNIUSDT | 1 | 1 | 100.0% | 52.186 | — | 44.4 | 64.0 | 0.15 | 100% | no | Watchlist |
| ZECUSDT | 4 | 2 | 50.0% | 12.341 | 2.49 | 42.0 | 62.5 | 0.26 | 100% | no | Watchlist |
| HYPEUSDT | 4 | 2 | 50.0% | 10.018 | 10.56 | 42.0 | 61.2 | -0.33 | 100% | no | Watchlist |
| SKHYUSDT | 4 | 2 | 50.0% | 2.457 | 3.19 | 42.0 | 64.2 | 0.11 | 50% | no | Watchlist |
| CLUSDT | 4 | 2 | 50.0% | 2.385 | 2.58 | 42.0 | 61.2 | 0.91 | 100% | no | Watchlist |
| EWYUSDT | 2 | 1 | 50.0% | -0.509 | 0.72 | 40.7 | 64.0 | — | 100% | no | Watchlist |
| CYSUSDT | 2 | 1 | 50.0% | 6.794 | 3.23 | 40.7 | 63.0 | — | 0% | no | Watchlist |
| ACEUSDT | 2 | 1 | 50.0% | 15.076 | 4.12 | 40.7 | 66.0 | — | 0% | no | Watchlist |
| PAXGUSDT | 2 | 1 | 50.0% | 0.382 | 2.29 | 40.7 | 69.5 | — | 100% | no | Watchlist |
| 1000PEPEUSDT | 2 | 1 | 50.0% | 12.475 | 4.34 | 40.7 | 60.0 | -0.21 | 100% | no | Watchlist |
| XAUUSDT | 2 | 1 | 50.0% | 0.476 | 2.64 | 40.7 | 61.5 | -0.31 | 100% | no | Watchlist |
| MUUSDT | 2 | 1 | 50.0% | -1.613 | 0.44 | 40.7 | 65.0 | — | 100% | no | Watchlist |
| PUMPUSDT | 2 | 1 | 50.0% | 18.61 | 18.34 | 40.7 | 63.5 | 0.72 | 50% | no | Watchlist |
| WLDUSDT | 2 | 1 | 50.0% | -5.252 | 0.44 | 40.7 | 64.0 | -0.41 | 100% | no | Watchlist |
| SNDKUSDT | 3 | 1 | 33.3% | -1.681 | 0.55 | 37.5 | 60.5 | — | 67% | no | Watchlist |
| SKHYNIXUSDT | 3 | 1 | 33.3% | -0.072 | 0.97 | 37.5 | 62.0 | 0.87 | 100% | no | Watchlist |
| XAGUSDT | 3 | 1 | 33.3% | -0.808 | 0.55 | 37.5 | 60.0 | 1.86 | 67% | no | Watchlist |
| BNBUSDT | 3 | 1 | 33.3% | 1.609 | 3.25 | 37.5 | 68.3 | -0.82 | 67% | yes | Watchlist |
| BEATUSDT | 1 | 0 | 0.0% | -9.496 | 0.00 | 35.3 | 62.0 | — | 100% | no | Watchlist |
| BICOUSDT | 1 | 0 | 0.0% | -44.418 | 0.00 | 35.3 | 71.0 | — | 100% | no | Watchlist |
| BTCUSDT | 1 | 0 | 0.0% | -1.608 | 0.00 | 35.3 | 69.0 | — | 100% | yes | Watchlist |
| RKLBUSDT | 1 | 0 | 0.0% | -2.663 | 0.00 | 35.3 | 68.0 | — | 100% | no | Watchlist |
| HOLOUSDT | 1 | 0 | 0.0% | -7.172 | 0.00 | 35.3 | 64.0 | — | 100% | no | Watchlist |
| LITEUSDT | 1 | 0 | 0.0% | -5.122 | 0.00 | 35.3 | 73.0 | — | 0% | no | Watchlist |
| SPORTFUNUSDT | 1 | 0 | 0.0% | -6.124 | 0.00 | 35.3 | 59.0 | — | 100% | no | Watchlist |
| ALLOUSDT | 1 | 0 | 0.0% | -2.757 | 0.00 | 35.3 | 63.0 | — | 100% | no | Watchlist |
| TRUMPUSDT | 1 | 0 | 0.0% | -20.945 | 0.00 | 35.3 | 47.0 | — | 100% | no | Watchlist |
| HEMIUSDT | 1 | 0 | 0.0% | -8.618 | 0.00 | 35.3 | 64.0 | — | 100% | no | Watchlist |
| ENAUSDT | 1 | 0 | 0.0% | -4.104 | 0.00 | 35.3 | 59.0 | — | 100% | no | Watchlist |
| LABUSDT | 1 | 0 | 0.0% | -7.356 | 0.00 | 35.3 | 48.0 | -0.09 | 100% | no | Watchlist |
| USELESSUSDT | 1 | 0 | 0.0% | -4.708 | 0.00 | 35.3 | 58.0 | 0.20 | 100% | no | Watchlist |
| FLOCKUSDT | 1 | 0 | 0.0% | -5.382 | 0.00 | 35.3 | 60.0 | 0.02 | 100% | no | Watchlist |
| DRAMUSDT | 4 | 1 | 25.0% | -2.528 | 0.22 | 34.9 | 62.0 | — | 50% | no | Watchlist |
| SPCXUSDT | 4 | 1 | 25.0% | -0.074 | 0.94 | 34.9 | 65.5 | 0.49 | 50% | no | Watchlist |
| SOLUSDT | 5 | 1 | 20.0% | 1.801 | 1.75 | 32.5 | 62.6 | -0.25 | 60% | yes | Avoid |
| SNXXUSDT | 2 | 0 | 0.0% | -6.804 | 0.00 | 32.3 | 59.5 | — | 50% | no | Avoid |
| BZUSDT | 2 | 0 | 0.0% | -3.353 | 0.00 | 32.3 | 59.5 | -0.22 | 100% | no | Avoid |
| SUIUSDT | 2 | 0 | 0.0% | -3.462 | 0.00 | 32.3 | 62.0 | -1.00 | 100% | no | Avoid |
| MOVRUSDT | 2 | 0 | 0.0% | -9.468 | 0.00 | 32.3 | 60.0 | — | 100% | no | Avoid |
| DOGEUSDT | 3 | 0 | 0.0% | -12.88 | 0.00 | 29.8 | 56.0 | -1.00 | 67% | no | Avoid |
| MSTRUSDT | 3 | 0 | 0.0% | -3.387 | 0.00 | 29.8 | 67.0 | — | 0% | no | Avoid |
| ETHUSDT | 5 | 0 | 0.0% | -6.505 | 0.00 | 25.9 | 64.2 | 0.13 | 100% | yes | Avoid |

Tier counts: {'Watchlist': 47, 'Avoid': 8}. **Confidence:** LOW for any symbol with n<5 (most). **Recommendation:** display reliability with sample size; do not auto-exclude symbols.

## SECTION 17 — HISTORY MATCH AUDIT

Coverage: 15/116 closed trades (12.9%) had a historical analogue; symbols with any coverage: 5/55.

| Group | n | Win rate (Wilson) | Avg ret | PF |
|---|---|---|---|---|
| History present | 15 | 20.0% (7.0–45.2) | -1.046 | 0.67 |
| History missing | 101 | 41.6% (32.5–51.3) | 3.117 | 1.83 |

| History says ≥50% win | Won | Lost |
|---|---|---|
| Predicted win (ge 0.5) | 3 | 10 |
| Predicted loss (<0.5) | 0 | 2 |

| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| history present vs missing | 15/101 | 20.0% / 41.6% | 0.35 | [0.09, 1.32] | 0.1566 | 0.0173 | NOT SIGNIFICANT |

False positives (predicted win, lost)=10; false negatives (predicted loss, won)=0. Coverage is confined to the few legacy-backfilled majors, and it is confounded with them. **Is history useful?** Not demonstrably: when present it coincides with worse outcomes (20.0% vs 41.6%, p=0.1566), but that is the majors' underperformance, not a causal effect. **Confidence:** NOT SIGNIFICANT (confounded). **Recommendation:** do not penalize missing history; do not increase its weight; extend coverage before evaluating it.

## SECTION 18 — EXPECTED VALUE AUDIT

Stored EV (computed at issuance from then-available frequency tables) exists for only n=26 closed trades (post-V2.1). To evaluate over the full sample, a **retrospective leave-one-out EV** was also computed: EV_i = P(TP1|others)·(reward_TP1/risk) − P(stop-before-TP1|others)·1 (n=91).
**Stored EV buckets (post-V2.1 only):**
| EV bucket | n | Win% | Avg ret | PF | Avg realized R |
|---|---|---|---|---|---|
| Negative EV | 13 | 53.8% | 11.341 | 4.03 | 0.99 |
| 0–1R | 12 | 25.0% | 6.904 | 4.28 | 2.06 |
| 1–2R | 1 | 100.0% | 2.926 | — | 12.61 |
| 2–3R | 0 |  |  |  |  |
| 3R+ | 0 |  |  |  |  |

**Retrospective leave-one-out EV buckets (full sample):**
| EV bucket | n | Win% | Avg ret | PF | Avg realized R |
|---|---|---|---|---|---|
| Negative EV | 62 | 46.8% | 4.761 | 2.33 | 0.44 |
| 0–1R | 27 | 29.6% | 1.708 | 1.56 | 0.70 |
| 1–2R | 2 | 50.0% | -0.001 | 1.00 | 5.42 |
| 2–3R | 0 |  |  |  |  |
| 3R+ | 0 |  |  |  |  |

| Ranking metric | Spearman vs realized R | p | n |
|---|---|---|---|
| retrospective EV | -0.104 | 0.325 | 91 |
| confidence | 0.034 | 0.746 | 91 |
| total score | -0.073 | 0.493 | 91 |

Stored-EV vs realized: Spearman=0.016, p=0.937 (n=26).
**Does higher EV mean better trades?** No demonstrated relationship: retrospective EV vs realized R Spearman -0.104 (p=0.325), and among stored-EV trades the 'Negative EV' bucket had the best average return (small n). EV is no better a ranker than confidence or score in this sample. EV can 'lie' when the reward/risk term dominates (tight stops inflate EV) and because P(TP1) is pooled and does not vary much by setup. **Confidence:** NOT SIGNIFICANT. **Recommendation:** keep EV as a displayed, shadow-mode number; do not rank trades by it until it beats confidence out-of-sample at n≥200.

## SECTION 19 — TRADE MANAGER AUDIT

| Stage | Decision | Snapshots |
|---|---|---|
| OPEN | HOLD | 11782 |
| PRE_ENTRY | HOLD | 6641 |
| TP1_REACHED | HOLD | 1669 |
| TP1_REACHED | HOLD_FOR_TP2 | 1300 |
| TP2_REACHED | HOLD | 357 |
| TP2_REACHED | MOVE_STOP_TO_TP1 | 239 |
| EXITED | STOPPED | 56 |
| EXITED | TAKE_PROFIT | 42 |
| EXITED | INVALIDATED | 6 |

Snapshot decisions before 2026-09-12 are the Phase-1 placeholder (always HOLD); real probability-driven decisions exist only for post-V2.1 trades.
| Counterfactual policy (all closed trades; non-TP1 trades unchanged) | n | Sum ret % | Avg ret | PF | Median |
|---|---|---|---|---|---|
| Actual (hold to outermost target/stop) | 116 | 299.1 | 2.579 | 1.70 | -1.59 |
| Exit 100% at TP1 | 116 | -212.4 | -1.831 | 0.40 | -1.011 |
| Exit at TP2 when TP3 defined | 116 | 177.9 | 1.534 | 1.44 | -1.559 |
| Move stop to entry after TP1 (optimistic) | 116 | 356.6 | 3.074 | 2.02 | -1.011 |
| Move stop to entry after TP1 (pessimistic) | 116 | 126.1 | 1.087 | 1.36 | -1.011 |

TP1-reaching trades: n=52. Assumptions (disclosed): TP exits fill at the TP price (no slippage/fees); break-even-stop uses snapshot-cadence price path — 'returned to entry' is undeterminable for trades with a single closing snapshot (bounded by the optimistic/pessimistic rows). **Would return improve?** compare the Sum column: exiting at TP1 forfeits the right-tail (avg continuation after TP1 in §20), while a breakeven stop converts TP1-then-stopped losses (8 trades) into ~0. **Confidence:** MEDIUM (arithmetic on real paths, but n=52 and fill assumptions). **Recommendation:** exiting at TP1 (Sum -212.4%) and at TP2 (Sum 177.9%) are both clearly WORSE than holding (Sum 299.1%) — the right tail pays. A breakeven stop after TP1 ranges from 126.1% (pessimistic) to 356.6% (optimistic) around the actual 299.1%: the bounds straddle actual, so its benefit is INSUFFICIENT DATA/inconclusive. Do not change trade handling; at most shadow-log it.

## SECTION 20 — TP CONTINUATION MODEL

**By overall**
| overall | n (TP1) | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(stop) | P(return→entry) | P(return→stop) |
|---|---|---|---|---|---|---|
| all TP1 trades | 52 | 86.5% (74.7–93.3) | 31.1% (n=45) | 15.4% | 18.9% (n=37) | 15.7% (n=51) |

**By confidence bucket**
| confidence bucket | n (TP1) | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(stop) | P(return→entry) | P(return→stop) |
|---|---|---|---|---|---|---|
| 60–64 | 20 | 90.0% (69.9–97.2) | 44.4% (n=18) | 15.0% | 11.8% (n=17) | 15.0% (n=20) |
| 65+ | 15 | 93.3% (70.2–98.8) | 35.7% (n=14) | 6.7% | 20.0% (n=5) | 6.7% (n=15) |
| <60 | 17 | 76.5% (52.7–90.4) | 7.7% (n=13) | 23.5% | 26.7% (n=15) | 25.0% (n=16) |

**By regime**
| regime | n (TP1) | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(stop) | P(return→entry) | P(return→stop) |
|---|---|---|---|---|---|---|
| mixed | 42 | 88.1% (75.0–94.8) | 32.4% (n=37) | 14.3% | 18.2% (n=33) | 14.3% (n=42) |
| risk_on | 10 | 80.0% (49.0–94.3) | 25.0% (n=8) | 20.0% | 25.0% (n=4) | 22.2% (n=9) |

**By trend_score**
| trend_score | n (TP1) | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(stop) | P(return→entry) | P(return→stop) |
|---|---|---|---|---|---|---|
| trend <22 | 34 | 88.2% (73.4–95.3) | 33.3% (n=30) | 14.7% | 11.5% (n=26) | 14.7% (n=34) |
| trend ≥22 | 18 | 83.3% (60.8–94.2) | 26.7% (n=15) | 16.7% | 36.4% (n=11) | 17.6% (n=17) |

**By entry quality**
| entry quality | n (TP1) | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(stop) | P(return→entry) | P(return→stop) |
|---|---|---|---|---|---|---|
| excellent | 10 | 100.0% (72.2–100) | 50.0% (n=10) | 0.0% | 0.0% (n=4) | 0.0% (n=10) |
| good | 8 | 75.0% (40.9–92.9) | 33.3% (n=6) | 37.5% | 25.0% (n=8) | 37.5% (n=8) |
| neutral | 27 | 85.2% (67.5–94.1) | 26.1% (n=23) | 14.8% | 22.7% (n=22) | 14.8% (n=27) |

**By direction**
| direction | n (TP1) | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(stop) | P(return→entry) | P(return→stop) |
|---|---|---|---|---|---|---|
| long | 47 | 89.4% (77.4–95.4) | 33.3% (n=42) | 10.6% | 15.6% (n=32) | 10.9% (n=46) |
| short | 5 | 60.0% (23.1–88.2) | 0.0% (n=3) | 60.0% | 40.0% (n=5) | 60.0% (n=5) |

**By ATR-normalized stop distance**
| ATR-normalized stop distance | n (TP1) | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(stop) | P(return→entry) | P(return→stop) |
|---|---|---|---|---|---|---|
| <1 ATR | 24 | 83.3% (64.1–93.3) | 35.0% (n=20) | 20.8% | 22.2% (n=18) | 20.8% (n=24) |
| ≥1 ATR | 16 | 87.5% (64.0–96.5) | 21.4% (n=14) | 12.5% | 25.0% (n=12) | 12.5% (n=16) |

**By symbol (n≥2 TP1 trades)**
| symbol (n≥2 TP1 trades) | n (TP1) | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(stop) | P(return→entry) | P(return→stop) |
|---|---|---|---|---|---|---|
| BTWUSDT | 2 | 100.0% (34.2–100) | 50.0% (n=2) | 0.0% | 0.0% (n=2) | 0.0% (n=2) |
| CLUSDT | 2 | 100.0% (34.2–100) | 50.0% (n=2) | 0.0% | —% (n=0) | 0.0% (n=2) |
| CRCLUSDT | 3 | 66.7% (20.8–93.9) | 0.0% (n=2) | 33.3% | 33.3% (n=3) | 33.3% (n=3) |
| HYPEUSDT | 2 | 100.0% (34.2–100) | 50.0% (n=2) | 0.0% | 0.0% (n=1) | 0.0% (n=2) |
| LINKUSDT | 2 | 100.0% (34.2–100) | 50.0% (n=2) | 0.0% | —% (n=0) | 0.0% (n=2) |
| NEARUSDT | 2 | 100.0% (34.2–100) | 50.0% (n=2) | 0.0% | 0.0% (n=1) | 0.0% (n=2) |
| NVDAUSDT | 2 | 100.0% (34.2–100) | 0.0% (n=2) | 0.0% | 0.0% (n=2) | 0.0% (n=2) |
| SAMSUNGUSDT | 2 | 100.0% (34.2–100) | 0.0% (n=2) | 0.0% | 0.0% (n=2) | 0.0% (n=2) |
| SKHYUSDT | 3 | 66.7% (20.8–93.9) | 50.0% (n=2) | 33.3% | 33.3% (n=3) | 33.3% (n=3) |
| SOLUSDT | 2 | 50.0% (9.5–90.5) | 0.0% (n=1) | 50.0% | 50.0% (n=2) | 50.0% (n=2) |
| WLDUSDT | 2 | 100.0% (34.2–100) | 50.0% (n=2) | 50.0% | 0.0% (n=1) | 50.0% (n=2) |
| ZECUSDT | 2 | 100.0% (34.2–100) | 50.0% (n=2) | 0.0% | 0.0% (n=2) | 0.0% (n=2) |

Average continuation after TP1 (best excursion vs entry)=14.529%, average pullback=3.853% (n=51). **Recommendation:** none beyond §19 (shadow-mode breakeven). Sub-slices with n<10 are **INSUFFICIENT DATA** for conclusions.

## SECTION 21 — RED FLAG AUDIT

| Flag | n with flag | Win% with | Win% without | Avg ret with | OR | Fisher p | Confidence |
|---|---|---|---|---|---|---|---|
| liquidity_stress | 2 | 0.0% | 39.5% | -7.11 | 0.31 | 0.521 | INSUFFICIENT DATA |
| short_direction | 19 | 15.8% | 43.3% | -7.55 | 0.25 | 0.0374 | MEDIUM |
| rsi_chop_30_49 | 23 | 21.7% | 43.0% | -4.23 | 0.37 | 0.093 | LOW (suggestive only) |
| risk_penalty_applied | 25 | 28.0% | 41.8% | -0.26 | 0.54 | 0.252 | NOT SIGNIFICANT |
| weak_structure | 72 | 36.1% | 43.2% | 2.51 | 0.74 | 0.5562 | NOT SIGNIFICANT |
| funding_elevated | 5 | 40.0% | 38.7% | 3.63 | 1.05 | 1.0 | INSUFFICIENT DATA |
| no_history | 101 | 41.6% | 20.0% | 3.12 | 2.85 | 0.1566 | NOT SIGNIFICANT |
| outage_exit | 52 | 42.3% | 35.9% | 5.05 | 1.31 | 0.5665 | NOT SIGNIFICANT |
| negative_cmf | 27 | 44.4% | 37.1% | 5.56 | 1.36 | 0.5069 | NOT SIGNIFICANT |
| high_atr_extension | 2 | 50.0% | 38.6% | -21.53 | 1.59 | 1.0 | INSUFFICIENT DATA |
| mfi_over_80 | 7 | 100.0% | 34.9% | 4.16 | 27.86 | 0.001 | INSUFFICIENT DATA |

Not measurable: late-entry flag (n=0 by construction), true low-liquidity (liquidity_stress is a cross-exchange-spread proxy), funding extreme (funding_elevated is funding_score≤5 proxy; n tiny) → treat as INSUFFICIENT DATA where n<10.
**Flag combinations (n≥5), worst first:**
| Combination | n | Win% | Avg ret | PF |
|---|---|---|---|---|
| weak_structure + short_direction | 10 | 0.0% | -11.602 | 0.00 |
| negative_cmf + risk_penalty_applied | 5 | 0.0% | -9.396 | 0.00 |
| short_direction + outage_exit | 11 | 0.0% | -12.673 | 0.00 |
| rsi_chop_30_49 + weak_structure | 14 | 14.3% | -5.298 | 0.39 |
| weak_structure + risk_penalty_applied | 13 | 15.4% | -3.751 | 0.44 |
| rsi_chop_30_49 + outage_exit | 12 | 16.7% | -7.406 | 0.35 |
| rsi_chop_30_49 + short_direction | 17 | 17.6% | -7.914 | 0.04 |
| no_history + short_direction | 17 | 17.6% | -6.749 | 0.04 |
| rsi_chop_30_49 + no_history | 19 | 26.3% | -3.492 | 0.44 |
| rsi_chop_30_49 + negative_cmf | 11 | 27.3% | -3.991 | 0.46 |
| negative_cmf + short_direction | 7 | 28.6% | -9.6 | 0.06 |
| no_history + risk_penalty_applied | 24 | 29.2% | -0.221 | 0.97 |
| weak_structure + negative_cmf | 16 | 31.2% | 6.329 | 1.96 |
| risk_penalty_applied + outage_exit | 9 | 33.3% | -2.798 | 0.73 |
| weak_structure + no_history | 62 | 37.1% | 2.973 | 1.75 |

**Confidence:** MEDIUM for the RSI chop zone and short-direction flags; the rest are LOW/NOT SIGNIFICANT. **Recommendation:** keep flags observational; RSI-chop is the only one with a large, consistent effect.

## SECTION 22 — MISSED OPPORTUNITY ANALYSIS

ScanSnapshot rows: 77060; RejectedOpportunityOutcome recorder rows: 0 (the recorder is not wired into the scanner, so it holds no live data).

| Rejection category | Scan rows | Rows with forward price coverage (24h) | Avg 24h dir. return | % favorable at 24h | Avg MFE | Avg MAE | % with MFE ≥5% (TP1-like) |
|---|---|---|---|---|---|---|---|
| published/active (no rejection) | 63416 | 18135 | 0.30% | 48.8% | 2.79% | -1.97% | 15.5% |
| no_trade (direction gate) | 5916 | 1 | |move| 3.70% | n/a (no direction) | max|move| 3.70% |  |  |
| rank cutoff (outside top 6) | 4293 | 16 | -1.42% | 25.0% | 4.05% | -3.62% | 31.2% |
| exhausted | 2896 | 0 |  |  |  |  |  |
| late | 539 | 3 | -1.41% | 33.3% | 0.76% | -2.62% | 0.0% |

**Critical limitation:** ScanSnapshot stores no price. Forward prices exist only where a *TradeOutcome was open on the same symbol* (PredictionSnapshot coverage) — a selection-biased subset (n shown above), and consecutive 5-minute scans of one symbol are highly autocorrelated. Exhausted scans have their direction overwritten to 'no_trade' by the engine, so directional outcomes are unrecoverable (magnitude only). Literal TP1/TP2/TP3/stop replay for rejected candidates is **INSUFFICIENT DATA** (they never received Claude-generated levels). **Confidence:** INSUFFICIENT DATA for 'were rejections wrong'. **Recommendation:** wire the missed-opportunity recorder (needs a scanner edit — requires explicit approval) to collect unbiased forward prices; re-audit at ≥500 resolved rows.

## SECTION 23 — INVALIDATED TRADES

Invalidated plans: n=727 — entered before replacement: 646; never entered: 81.
| Invalidated & entered (n=646) | Value |
|---|---|
| TP1 hit before replacement | 34 |
| TP2 hit | 5 |
| Stop touched | 0 |
| Unrealized P&L at last snapshot: n / avg / % positive | 638 / 0.29% / 72.6% |
| Avg MFE / MAE (tracked while open) | —% / —% |

| Replacement analysis (same symbol, next resolved plan) | n |
|---|---|
| replaced-by-later-resolved-plan | 603 |
| ...that plan lost | 398 |
| ...that plan won | 205 |

Invalidation is a paper status: no realized return is recorded and price is not tracked after the replacement, so **'how many would have won / whether invalidation avoided losses' is INSUFFICIENT DATA** beyond the in-flight metrics above. Most invalidated plans were pending plans re-issued as the entry zone shifted (churn), not closed positions. **Confidence:** LOW. **Recommendation:** record post-invalidation outcome for a sample (analytics) before judging.

## SECTION 24 — NEVER ENTERED TRADES

| Group | n | with price coverage | reached TP1 level w/o entering (missed winner) | reached stop level w/o entering (avoided loser) | neither | both |
|---|---|---|---|---|---|---|
| closed_stale (expired) | 6 | 6 | 4 | 0 | 0 | 2 |
| invalidated, never entered | 81 | 78 | 9 | 1 | 67 | 1 |
| pending now | 12 | 11 | 3 | 2 | 4 | 2 |

Total never-entered plans: n=99. Measured only while pending (snapshots stop at expiry/replacement). Entry-zone effectiveness = share of plans whose zone was reached at all: 84.2% of all 924 plans entered (mostly because plans get replaced while pending). **Confidence:** LOW (coverage-limited). **Recommendation:** none; keep as analytics.

## SECTION 25 — SNAPSHOT TIMELINE AUDIT

| Metric | Value |
|---|---|
| Distinct snapshot timestamps (cycles) | 2003 |
| Snapshots total | 25443 |
| Span (days) | 49.3 |
| Median normal cycle interval (min) | 5.6 |
| Monitoring gaps > 10 min | 97 |
| Total time in gaps (days) | 41.7 |
| Scanner uptime over span | 15.3% |
| Longest gap (hours) | 265.0 |
| Median gap (hours) | 0.21 |

| Impact | n trades | Detail |
|---|---|---|
| Closed trades whose EXIT fell inside a gap | 52 | 30 losses; avg return 5.05% |
| Closed trades open at any point during a gap | 82 | 70.7% of all closed trades |
| Stop slippage during gaps | 25 | avg -6.05%, worst -27.24% |
| Stop slippage in normal uptime | 34 | avg -0.86%, worst -9.40% |

| Latency / slippage metric | n | Median | P90 | Max |
|---|---|---|---|---|
| Stop detection latency = gap between last two snapshots of a losing trade (min) | 68 | 6.7 | 10179.0 | 17205.0 |
| TP overshoot (exit vs outermost target, % in trade direction; + = better than target) | 42 | 2.197 | 24.419 | 87.605 |

| Loss attribution | n | Sum of returns % | % of total loss magnitude |
|---|---|---|---|
| Losses with exit inside a monitoring gap (infrastructure-contaminated) | 30 | -283.4 | 66.3% |
| Losses in normal uptime (strategy) | 41 | -144.3 | 33.7% |

**Outages distort wins as well as losses:** 22 of 45 wins also exited inside a gap (avg return 24.82% vs 7.86% in uptime; TP overshoot median +2.2%, P90 +24%). Late detection inflates both tails, so gap exposure adds noise in both directions — the net effect on PF is not separable from this data.
Open/pending trades with no snapshot for >1h (stale): n=23. **Confidence:** HIGH (timestamps are facts). **Recommendation:** run the scanner as a supervised always-on process; until then annotate every metric with the fraction of trades gap-exposed (70.7%). Detection latency is bounded by the scan interval only during uptime.

## SECTION 26 — PREDICTION VERSION AUDIT

| Version | n | Win% | PF | PF ex-best | Avg ret | Median | TP1/2/3 % | MFE/MAE | Avg stop slip% | Median hold h | Naive DD % | Brier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V0: pre entry_quality (created < 2026-08-10) | 17 | 35.3% | 0.74 | 0.33 | -1.508 | -2.319 | 41.2/35.3/5.9 | 4.782/-5.695 | -4.85 | 40.323 | -71.9 | 0.311 |
| V1: entry_quality live, pre EV/TradeManager/metadata | 73 | 38.4% | 1.36 | 1.18 | 1.254 | -1.635 | 42.5/38.4/16.4 | 5.269/-3.75 | -3.10 | 19.513 | -100.5 | 0.302 |
| V2: EV + Trade Manager + reliability + metadata live (created ≥ 2026-09-12 06:56) | 26 | 42.3% | 4.16 | 2.61 | 8.969 | -1.004 | 53.8/46.2/3.8 | 12.547/-2.851 | -2.81 | 41.59 | -51.7 | 0.283 |

Stored prediction_metadata versions across all 924 plans: {'unversioned': 688, 'v3.2': 236}. EV, Trade Manager, reliability and metadata all went live in the same deployment (first stored EV/metadata plan: 2026-09-12 06:56), so they **cannot be separated**; reliability/calibration are display-only (not stored per trade). **Regime/time caveat:** these are different calendar windows and market regimes (V0 is early risk_on; V2 is the most recent window), so differences are NOT attributable to the features. V2 n=26 — its PF is dominated by a single +114% winner (see PF ex-best). **Confidence:** INSUFFICIENT DATA to credit any version. **Recommendation:** keep collecting under the frozen engine; compare versions only at n≥100 per version.

## SECTION 27 — PORTFOLIO ANALYSIS

| Concurrency at entry (closed trades only) | Value |
|---|---|
| Trades analyzed | 116 |
| Mean / median / max other open trades at entry | 6.3 / 6.5 / 12 |
| Entries with ≥5 other open trades | 82 |
| Entries with ≥1 same-family open trade | 86 |

| Test | Spearman with realized return | p | n |
|---|---|---|---|
| # concurrent open trades at entry | 0.191 | 0.04 | 116 |
| # concurrent SAME-FAMILY trades at entry | 0.175 | 0.061 | 116 |

| Family | n | Win% | PF | Avg ret | Longs / Shorts |
|---|---|---|---|---|---|
| other_altcoin | 51 | 35.3% | 1.42 | 2.115 | 44/7 |
| stocks_etfs | 28 | 50.0% | 1.61 | 0.962 | 24/4 |
| crypto_majors | 15 | 20.0% | 0.67 | -1.046 | 13/2 |
| ai_coins | 8 | 62.5% | 7.84 | 19.652 | 6/2 |
| gold | 7 | 42.9% | 0.89 | -0.101 | 5/2 |
| meme_coins | 7 | 28.6% | 1.49 | 3.362 | 5/2 |

Stop-out clusters (≥2 losses within 2h): 16 clusters, 48 losses (67.6% of losses); largest = 5 simultaneous stops.
Magnificent-Seven concentration: only NVDA appears among the symbols; other listed themes are approximated by the family map. **BTC/ETH beta and rolling correlation: INSUFFICIENT DATA** (OHLCV history exists for only 6 symbols). **Did correlation raise drawdowns?** Not supported: more concurrent open trades at entry correlated POSITIVELY with realized return (Spearman 0.191, p=0.04), most likely a time-period confound (busy periods coincided with the strong late window). Losses do cluster (16 clusters holding 67.6% of losses), consistent with common-factor/outage exits. **Confidence:** LOW. **Recommendation:** keep exposure warnings as analytics; no gating.

## SECTION 28 — MARKET HEALTH AUDIT

Days with both scan data and trades entered: n=17 (of 20 scan days). Retro health inputs available per day from ScanSnapshot: % of directional scans that are long (breadth proxy), avg risk-penalty (volatility-quality proxy), avg funding component, % no_trade; Fear&Greed from the trades' stored value. **Not stored historically:** BTC dominance, true volume breadth, news stress, liquidity → INSUFFICIENT DATA.
| Retro health input (daily) | Spearman vs day's avg trade return | p | days n |
|---|---|---|---|
| long share of directional scans | -0.132 | 0.613 | 17 |
| avg risk-penalty component | 0.277 | 0.282 | 17 |
| avg funding component | -0.235 | 0.363 | 17 |
| % no_trade scans | 0.048 | 0.855 | 17 |
| Fear & Greed (trade-day avg) | -0.366 | 0.149 | 17 |

Note: trades cluster on few days, days are autocorrelated, and the 'entered on that day' return is realized weeks later — a very weak test. **Does market health predict profitability?** INSUFFICIENT DATA unless a row above shows p<0.05 (none is expected at this n). **Recommendation:** keep Market Health as context only; re-test at ≥100 trading days.

## SECTION 29 — ROOT CAUSE ANALYSIS

Ranking metric = over-representation: (share of losses [wins] with the factor) minus (share of ALL closed trades with the factor), in percentage points; factors with <5 trades excluded. This removes pure base-rate effects (e.g. 'long' is 84% of all trades). The share-of-magnitude column is kept for context (factors overlap). 'Avg impact' = average return with vs without the factor over all n=116 closed trades. Frequency ≠ cause; factors are correlational.

### Top 20 reasons Karma LOSES (ranked by over-representation in losses vs. base rate)

| # | Factor | Frequency in losses | Share of loss magnitude | Avg ret with vs without | Example trades | Engineering fix (hypothesis, shadow-test only) |
|---|---|---|---|---|---|---|
| 1 | Never reached TP1 (all no-TP1 losses) | 63/71 (88.7%) | 82.1% | -5.48% vs 12.49% | BICOUSDT -44.4%; ZECUSDT -28.8% | Same as immediate reversal. |
| 2 | Immediate reversal (no TP1, MFE<1%) | 57/71 (80.3%) | 77.1% | -5.78% vs 10.66% | BICOUSDT -44.4%; ZECUSDT -28.8% | Improve entry evidence (entry_quality already helps); shadow-test stricter confirmation. |
| 3 | regime=risk_on | 25/71 (35.2%) | 35.1% | -1.70% vs 4.28% | BICOUSDT -44.4%; ACEUSDT -9.7% | Track in shadow mode; no prediction change supported at current n. |
| 4 | Short direction | 16/71 (22.5%) | 34.7% | -7.55% vs 4.56% | ZECUSDT -28.8%; ETHUSDT -26.7% | Soft derate flag (built); collect ≥30 shorts before any hard rule. |
| 5 | RSI chop zone 30–49 | 18/71 (25.4%) | 35.1% | -4.23% vs 4.26% | ZECUSDT -28.8%; ETHUSDT -26.7% | Red-flag (built); shadow-mode entry filter. |
| 6 | strategy=ema_pullback | 32/71 (45.1%) | 40.7% | 4.01% vs 1.60% | ZECUSDT -28.8%; ETHUSDT -26.7% | Track in shadow mode; no prediction change supported at current n. |
| 7 | Low-volume setup (volume_score<8) | 34/71 (47.9%) | 44.6% | 3.37% vs 1.96% | ZECUSDT -28.8%; TRUMPUSDT -20.9% | Track in shadow mode; no prediction change supported at current n. |
| 8 | Hit TP1 then stopped | 7/71 (9.9%) | 13.5% | -8.24% vs 3.27% | TRUMPUSDT -20.9%; DOGEUSDT -15.8% | Shadow-mode breakeven stop after TP1 (§19). |
| 9 | Gap/slippage through stop (≥5%) | 7/71 (9.9%) | 34.4% | -21.05% vs 4.10% | ZECUSDT -28.8%; ETHUSDT -26.7% | Same as infrastructure (monitoring gaps). |
| 10 | Weak structure (structure_score<9) | 46/71 (64.8%) | 66.1% | 2.51% vs 2.69% | ZECUSDT -28.8%; ETHUSDT -26.7% | Capture BOS/CHoCH at issuance (analytics) then re-test. |
| 11 | entry_quality=good | 14/71 (19.7%) | 15.0% | -0.48% vs 3.22% | WLDUSDT -18.8%; HOLOUSDT -7.2% | Track in shadow mode; no prediction change supported at current n. |
| 12 | trend_score ≥ 22 | 27/71 (38.0%) | 37.0% | 1.17% vs 3.38% | BICOUSDT -44.4%; TRUMPUSDT -20.9% | Track in shadow mode; no prediction change supported at current n. |
| 13 | entry_quality=neutral | 38/71 (53.5%) | 57.2% | 3.41% vs 1.66% | ZECUSDT -28.8%; ETHUSDT -26.7% | Track in shadow mode; no prediction change supported at current n. |
| 14 | strategy=trend_continuation_other | 17/71 (23.9%) | 26.2% | -0.51% vs 3.56% | TRUMPUSDT -20.9%; MOVRUSDT -16.0% | Track in shadow mode; no prediction change supported at current n. |
| 15 | strategy=bos_pullback | 7/71 (9.9%) | 18.7% | 3.08% vs 2.52% | BICOUSDT -44.4%; ACEUSDT -9.7% | Track in shadow mode; no prediction change supported at current n. |
| 16 | CMF > 0 | 38/71 (53.5%) | 40.7% | 2.99% vs 2.08% | ETHUSDT -26.7%; MOVRUSDT -16.0% | Track in shadow mode; no prediction change supported at current n. |
| 17 | strategy=fvg_continuation | 14/71 (19.7%) | 13.2% | 3.20% vs 2.41% | WLDUSDT -18.8%; CYSUSDT -6.1% | Track in shadow mode; no prediction change supported at current n. |
| 18 | FVG active at entry | 14/71 (19.7%) | 13.2% | 3.20% vs 2.41% | WLDUSDT -18.8%; CYSUSDT -6.1% | Track in shadow mode; no prediction change supported at current n. |
| 19 | Negative CMF | 15/71 (21.1%) | 31.2% | 5.56% vs 1.67% | ZECUSDT -28.8%; TRUMPUSDT -20.9% | Track in shadow mode; no prediction change supported at current n. |
| 20 | Exit inside a monitoring outage | 30/71 (42.3%) | 66.3% | 5.05% vs 0.57% | BICOUSDT -44.4%; ZECUSDT -28.8% | Run the scanner as a supervised always-on service; not a strategy change. |

### Top 20 reasons Karma WINS (ranked by over-representation in wins vs. base rate)

| # | Factor | Frequency in wins | Share of gain magnitude | Avg ret with vs without | Example trades | Guidance |
|---|---|---|---|---|---|---|
| 1 | reached TP3 | 14/45 (31.1%) | 32.6% | 16.94% vs 0.61% | ACEUSDT +39.8%; ZECUSDT +37.1% | Preserve — do not change the mechanism behind this. |
| 2 | regime=mixed | 37/45 (82.2%) | 87.0% | 4.28% vs -1.70% | NEARUSDT +114.3%; UNIUSDT +52.2% | Preserve — do not change the mechanism behind this. |
| 3 | RSI 50–70 | 37/45 (82.2%) | 89.3% | 5.27% vs -4.48% | NEARUSDT +114.3%; UNIUSDT +52.2% | Preserve — do not change the mechanism behind this. |
| 4 | direction=long | 42/45 (93.3%) | 99.3% | 4.56% vs -7.55% | NEARUSDT +114.3%; UNIUSDT +52.2% | Preserve — do not change the mechanism behind this. |
| 5 | Overbought entry (RSI≥70 or MFI>80) | 8/45 (17.8%) | 4.2% | -2.25% vs 3.08% | SKHYUSDT +8.7%; SAMSUNGUSDT +6.4% | Preserve — do not change the mechanism behind this. |
| 6 | entry_quality=excellent | 10/45 (22.2%) | 20.3% | 7.02% vs 1.76% | PUMPUSDT +39.4%; HYPEUSDT +29.1% | Preserve — do not change the mechanism behind this. |
| 7 | no historical analogue | 42/45 (93.3%) | 95.5% | 3.12% vs -1.05% | NEARUSDT +114.3%; UNIUSDT +52.2% | Preserve — do not change the mechanism behind this. |
| 8 | volume_score ≥ 8 | 28/45 (62.2%) | 50.1% | 1.96% vs 3.37% | UNIUSDT +52.2%; ZECUSDT +45.4% | Preserve — do not change the mechanism behind this. |
| 9 | confidence 60–64 | 17/45 (37.8%) | 30.2% | 2.89% vs 2.43% | UNIUSDT +52.2%; VELVETUSDT +27.3% | Preserve — do not change the mechanism behind this. |
| 10 | structure_score ≥ 9 | 19/45 (42.2%) | 36.3% | 2.69% vs 2.51% | ACEUSDT +39.8%; PUMPUSDT +39.4% | Preserve — do not change the mechanism behind this. |
| 11 | Exit inside a monitoring outage | 22/45 (48.9%) | 75.1% | 5.05% vs 0.57% | NEARUSDT +114.3%; UNIUSDT +52.2% | Preserve — do not change the mechanism behind this. |
| 12 | Negative CMF | 12/45 (26.7%) | 39.0% | 5.56% vs 1.67% | NEARUSDT +114.3%; ZECUSDT +37.1% | Preserve — do not change the mechanism behind this. |
| 13 | strategy=fvg_continuation | 11/45 (24.4%) | 18.8% | 3.20% vs 2.41% | PUMPUSDT +39.4%; HYPEUSDT +29.1% | Preserve — do not change the mechanism behind this. |
| 14 | FVG active at entry | 11/45 (24.4%) | 18.8% | 3.20% vs 2.41% | PUMPUSDT +39.4%; HYPEUSDT +29.1% | Preserve — do not change the mechanism behind this. |
| 15 | CMF > 0 | 26/45 (57.8%) | 50.2% | 2.99% vs 2.08% | UNIUSDT +52.2%; ZECUSDT +45.4% | Preserve — do not change the mechanism behind this. |
| 16 | strategy=bos_pullback | 6/45 (13.3%) | 16.5% | 3.08% vs 2.52% | ACEUSDT +39.8%; VELVETUSDT +27.3% | Preserve — do not change the mechanism behind this. |
| 17 | strategy=trend_continuation_other | 11/45 (24.4%) | 13.5% | -0.51% vs 3.56% | LINKUSDT +24.7%; APRUSDT +19.0% | Preserve — do not change the mechanism behind this. |
| 18 | entry_quality=neutral | 23/45 (51.1%) | 62.3% | 3.41% vs 1.66% | NEARUSDT +114.3%; UNIUSDT +52.2% | Preserve — do not change the mechanism behind this. |
| 19 | trend_score ≥ 22 | 15/45 (33.3%) | 28.5% | 1.17% vs 3.38% | ACEUSDT +39.8%; PUMPUSDT +39.4% | Preserve — do not change the mechanism behind this. |
| 20 | entry_quality=good | 6/45 (13.3%) | 7.5% | -0.48% vs 3.22% | VELVETUSDT +27.3%; BTWUSDT +13.5% | Preserve — do not change the mechanism behind this. |

**Category split:** Model/prompt issue — entry selection (immediate reversals dominate); Execution/infrastructure — outage & slippage (§25); Market-regime — regime is confounded with time (§14); Small-sample — everything at family/symbol level (§6, §16); the *prompt* cannot be assessed independently (no A/B) → INSUFFICIENT DATA.

## SECTION 30 — KARMA V3.0 ENGINEERING PLAN

Every row below is tied to a section above; nothing here changes prediction logic.

| Bucket | Item | Evidence (section) | Expected improvement |
|---|---|---|---|
| Ship immediately (analytics/display only) | Always show n, Wilson CI, and ex-top-3 PF beside every headline stat | §1: PF 1.7 -> 1.2 ex-top-3; median trade -1.59% | Prevents over-reading a right-tail-driven PF |
| Ship immediately | Annotate every metric with % of trades exposed to a monitoring gap | §25: 82/116 closed trades open during a gap; 66.3% of loss magnitude exits inside gaps | Separates infra from strategy failure |
| Ship immediately | Show calibrated confidence with interval instead of raw confidence as a probability | §8: Brier 0.299 vs base-rate 0.2373 | Removes misleading probability framing |
| Ship immediately | Show an INSUFFICIENT DATA badge whenever a slice has n<10 | §3-§29: most slices non-significant | Prevents false precision |
| Ship immediately (ops) | Run the scanner as a supervised always-on service | §25: uptime 15.3%, longest gap 265.0h | Largest data-quality lever; not a model change |
| Shadow mode (log, don't act) | Breakeven-stop-after-TP1 policy | §19: bounds 126.1%..356.6% vs actual 299.1% (inconclusive) | Unknown; needs per-trade path data |
| Shadow mode | RSI 30-49 chop-zone warning as a soft flag | §13/§21: win 21.7% (n=23) vs 43.0%, p=0.093 (suggestive only) | Possible; unproven |
| Shadow mode | Short-direction flag (already built), no hard block | §15: overall p=0.037 but ex-outage n=8 shorts, 37.5% win | Unknown |
| Shadow mode | Persist BOS/CHoCH/sweep/OBV booleans at issuance | §3/§12/§13: not stored -> INSUFFICIENT DATA | Enables a future structure audit |
| Needs 200 trades | Any change to score weights | §10: CV-AUC 0.553, 0/10 coefficients significant | Cannot be estimated |
| Needs 200 trades | Entry-quality tier validation | §7: excellent vs rest OR 2.24, p=0.1814 | Unknown |
| Needs 200 trades | EV as a ranking/selection signal | §18: Spearman -0.104 (p=0.325) | Unknown |
| Needs 500 trades | Regime-conditional behavior; strategy-family ranking; symbol-tier gating | §6/§14/§16: per-cell n mostly <30; only 2 regime labels observed | Unknown |
| Needs 500 resolved scans | Missed-opportunity verdicts on rejected/late/exhausted candidates | §22: ScanSnapshot has no price; recorder not wired | Unknown |
| Needs retraining | None recommended | §10: no evidence retraining would help (CV-AUC 0.553); prior retrain gave identical AUC | - |
| Do not build | Hard short ban; auto weight optimizer; per-coin ML models; regime gating; TP/SL formula fitted on ~50 trades | §15, §10, §16, §14, §19 | Would fit noise |

### Answers to the final questions

**1. Top 10 improvements (evidence-ranked, all non-predictive):** (1) keep the scanner running continuously (§25); (2) publish n + CI + ex-top-3 PF on every dashboard (§1); (3) present confidence as an uncalibrated score with a calibrated interval (§8); (4) persist BOS/CHoCH/sweep booleans at issuance (§12); (5) wire the missed-opportunity recorder (needs explicit approval to touch the scanner) (§22); (6) log a shadow breakeven-after-TP1 policy (§19); (7) record post-invalidation price outcomes for a sample (§23); (8) store entry-time ATR-normalised risk and BTC correlation for portfolio audits (§27); (9) tag every trade with an infra-exposure flag (§25); (10) re-run this audit at n=200 and n=500 (§10).
**2. What must never change (without new evidence):** the deterministic-first design; win/loss/exit bookkeeping; the hold-to-outermost-target exit behavior (§19: exiting at TP1/TP2 was clearly worse); the entry-quality gate blocking late/exhausted setups (0 such trades exist to judge); the frozen modules until n>=150-200.
**3. Modules that work well:** trade lifecycle/outcome tracking, TP/stop hit tracking, Wilson-CI calibration display, slippage/outage measurement, and the outermost-target exit rule that captures the right tail (§19).
**4. Modules that can mislead users:** raw confidence as a probability (§8: Brier worse than base rate); headline win rate/PF without ex-top-3 (§1); short-vs-long comparisons that ignore outage exits (§15); EV as a ranker (§18); history as a quality signal (§17: confounded, n=15); reliability tiers built on 1-2 trades per symbol (§16); Market Health as predictive (§28: INSUFFICIENT DATA).
**5. Prediction card metrics:** entry-quality tier with n; calibrated confidence with interval and sample size; risk:reward and ATR-normalised stop distance; red flags labelled suggestive; symbol reliability with n; data-completeness badge.
**6. Daily dashboard metrics:** scanner uptime and gap exposure; open/closed counts; PF and win rate with n and ex-top-3 PF; median return; stop-slippage split by outage; long vs short with n.
**7. Trade replay metrics:** snapshot price path vs entry/stop/TPs, MFE/MAE, lifecycle pattern, Trade-Truth verdict, monitoring-gap markers, slippage, stored reasoning and level rationale.
**8. Scanner/watchlist metrics:** rejection-reason funnel (published/no_trade/late/exhausted/rank-cutoff), plans replaced while pending (churn), never-entered outcomes (§24), history/reliability coverage.
**9. Confidence metrics:** calibration table with Wilson CIs, Brier vs base-rate Brier, ECE, bucket n, Spearman vs return; label 'not a probability' until Brier beats the base rate.
**10. Hidden diagnostics:** feature-audit table with OR/CI/Fisher/info-gain (§3-§13), CV-AUC and bootstrap coefficients (§10), infra-vs-strategy loss split (§25), flag co-occurrence (§21), concurrency/cluster stats (§27), version-boundary comparisons (§26).

### Karma V3.0 — Changes Backed by Data

| Feature | Evidence Strength | Sample Size | Expected Impact | Safe to Ship? | Needs More Data? |
|---|---|---|---|---|---|
| Scanner always-on / supervised process | Strong (timestamp facts) | 2003 cycles, 97 gaps, n=116 closed | High on data quality (66.3% of loss magnitude exits in gaps); strategy impact unknown | Yes (ops, not model) | No |
| Headline stats with n, CI, ex-top-3 PF | Strong | n=116 | Prevents over-claiming (PF 1.7 -> 1.2) | Yes | No |
| Calibrated confidence + interval display | Moderate | n=111 | Honest uncertainty; no change to trades | Yes | Partly (bucket n small) |
| Infra-exposure tag per trade | Strong | 82/116 exposed | Cleaner evaluation | Yes | No |
| Persist BOS/CHoCH/sweep/OBV booleans | N/A (currently missing) | 0 trades have them | Enables the §12 audit | Yes (additive; needs approval to edit feature code) | Yes |
| Wire missed-opportunity recorder | N/A (currently missing) | 0 recorded rows | Enables §22 | Needs explicit approval (frozen file) | Yes (>=500 rows) |
| Shadow breakeven-after-TP1 | Weak / inconclusive | n=52 TP1 trades | Unknown (bounds straddle actual) | Shadow only | Yes |
| RSI 30-49 chop-zone flag | Weak-moderate (p=0.093) | n=23 flagged | Possible loss avoidance | Shadow only | Yes |
| Short-direction handling | Weak (p=0.037 all; not significant ex-outage) | n=19 (ex-outage 8) | Unknown | Keep soft flag only; no hard block | Yes (>=30 clean shorts) |
| Score weight changes | None | n=116 | CV-AUC 0.553; no coefficient significant | No | Yes (>=200) |
| Entry-quality tier changes | Weak (p=0.1814) | n=99 | Unknown | No | Yes (>=200) |
| EV-based ranking/gating | None | n=91 | Spearman -0.104 | No | Yes (>=200) |
| Regime gating | None | 2 labels observed | Unknown | No | Yes (>=500) |
| ML retraining | None | n=116 | Prior retrain: identical AUC | No | Yes |
| Early-exit at TP1/TP2 policies | Strong AGAINST | n=116 | Sum ret -212.4% / 177.9% vs actual 299.1% | No (would reduce return) | No |
