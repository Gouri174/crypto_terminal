# Karma Engineering Forensic Report — Sections 1–23

Generated 2026-09-26 20:20 UTC from `crypto_terminal.db`, read-only. Live counts: 982 plans, 118 closed (46W/72L), 24 open, 11 pending, 774 invalidated, 48 avoided, 26509 PredictionSnapshots, 81540 ScanSnapshots. (The DB grows while the scanner runs; the counts in your brief are a few days old.)

**Rules followed:** no code, prompt, weight, model, or DB change was made; scoring.py / decision.py / prompt / ML stay frozen. Section 23 is a *plan*; no diffs or commits were produced, because — as the evidence below shows — almost nothing predictive is proven strongly enough to justify a code change yet. Labels: CONFIRMED (p<.01, n≥30) · LIKELY (p<.05) · POSSIBLE (p<.15) · NOT SUPPORTED (adequate n, p≥.15) · INSUFFICIENT DATA (n<10 or field not stored). Fisher exact / bootstrap; p-values optimistic because trades cluster in time and by symbol.

**Read this first — what the archive can and cannot support:** (1) Only 118-ish resolved trades, ~46 wins, with profit concentrated in a few large longs. (2) The scanner was up only ≈16% of the calendar span, so any exit-timing / stop analysis is contaminated by monitoring gaps. (3) Rejected scans have no prices and avoided plans have no forward tracking, so 'missed opportunity' cannot be measured. (4) BOS/CHoCH/OBV/market-cap were never stored per trade. Where a requested item hinges on those, I say INSUFFICIENT DATA rather than invent it.

## SECTION 1 — COMPLETE TRADE FORENSICS

**Verdict rules (first match wins; losses only unless noted):** Infrastructure Failure = stop slippage ≤ −5% (price gapped through the stop); Scanner Outage = exit inside a monitoring gap; Low Liquidity = liquidity_score<0; TP1 Hit — Should Have Exited = loss after TP1 had already been reached (hindsight); Immediate Reversal = no TP1 and MFE<1%; Counter Trend = BTC trend disagrees with direction; Weak Structure = structure_score<9; Bad Confidence = confidence ≥65 on a loss; wins: Perfect = MAE ≥ −2%, otherwise Good Entry Good Exit (Good Entry Bad Exit only if Trade-Truth says so). **'TP2 Hit — Should Have Continued' cannot be assigned: no prices are recorded after a trade closes → INSUFFICIENT DATA.** 'News Event' likewise. Full per-trade rows (all stored fields, incl. snapshot counts) are in `karma_eng_ledger.csv`; the table below is the compact form.
| Symbol | Dir | Created | Entered | Exited | Hold h | Entry | Stop | TP1 | TP2 | TP3 | Conf | Grade | EV(R) | Rel* | EQ | Regime | Trend | Mom | Vol | Struct | Fund | Hist | ML prob | Risk flags | Red flags | Failure pattern | Ret% | MFE% | MAE% | Slip% | TP stage | Snaps | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ADAUSDT | long | 2026-09-25 21:16 | 2026-09-25 21:22 | 2026-09-26 01:47 | 4.4 | 0.25145 | 0.232 | 0.2585 | 0.2623 | — | 62 | B | -0.70 | 44.5 | neutral | risk_on | 23.0 | 15.0 | 10.0 | 6.0 | 10.0 | -1.5 | 0.48 | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,LOW_TP1_RR | weak_structure | closed_at_tp2 | 4.95 | 4.95 | 0.54 | — | TP2 | 49 | Perfect Trade |
| SPCXUSDT | long | 2026-09-14 19:01 | 2026-09-14 19:07 | 2026-09-25 20:45 | 265.6 | 150.075 | 148.6 | 151.57 | 152.52 | 154.77 | 70 | B+ | 0.29 | 35.0 | excellent | risk_on | 19.3 | 15.0 | 10.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | no_history | immediate_reversal | -1.02 | 0.13 | -1.02 | -0.03 | none | 9 | Scanner Outage |
| BNBUSDT | long | 2026-09-14 19:01 | 2026-09-14 19:07 | 2026-09-25 20:45 | 265.6 | 725.55 | 717 | 729.13 | 737.4 | — | 65 | B+ | -0.82 | 37.7 | neutral | risk_on | 18.7 | 15.0 | 10.0 | 6.0 | 10.0 | 1.5 | 0.48 | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure | closed_at_tp2 | 6.98 | 6.98 | 0.07 | — | TP2 | 9 | Perfect Trade |
| UNIUSDT | long | 2026-09-14 17:00 | 2026-09-14 17:06 | 2026-09-25 20:45 | 267.7 | 6.36 | 6.19 | 6.57 | 6.8 | — | 64 | B | 0.15 | 44.5 | neutral | mixed | 20.0 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | closed_at_tp2 | 52.19 | 52.19 | 0.55 | — | TP2 | 30 | Perfect Trade |
| ZECUSDT | long | 2026-09-14 16:14 | 2026-09-14 16:32 | 2026-09-25 20:45 | 268.2 | 1130 | 1108 | 1161.98 | 1184 | 1297.5 | 59 | B | 0.26 | 42.1 | neutral | mixed | 18.4 | 15.0 | 7.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,negative_cmf | ran_to_tp3 | 37.08 | 37.08 | 0.36 | — | TP3 | 38 | Perfect Trade |
| HYPEUSDT | long | 2026-09-14 15:50 | 2026-09-14 15:57 | 2026-09-25 20:45 | 268.8 | 79.8 | 76.5 | 80.77 | 89.67 | — | 59 | B | -0.33 | 42.1 | neutral | mixed | 15.1 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | rsi_chop_30_49,weak_structure,no_history | closed_at_tp2 | 15.19 | 15.19 | -0.13 | — | TP2 | 42 | Perfect Trade |
| BZUSDT | long | 2026-09-14 15:50 | 2026-09-14 15:57 | 2026-09-25 20:45 | 268.8 | 102.25 | 99 | 103.91 | 112.75 | — | 54 | C | -0.22 | 32.5 | neutral | mixed | 23.7 | 15.0 | 10.0 | 6.0 | 0.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,funding_elevated | immediate_reversal | -4.68 | 0.37 | -4.68 | -1.56 | none | 42 | Scanner Outage |
| NEARUSDT | long | 2026-09-14 15:50 | 2026-09-14 15:57 | 2026-09-25 20:45 | 268.8 | 2.3875 | 2.276 | 2.435 | 2.727 | — | 57 | B | -0.27 | 49.2 | neutral | mixed | 21.6 | 15.0 | 2.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,negative_cmf | closed_at_tp2 | 114.28 | 114.28 | 0.40 | — | TP2 | 42 | Perfect Trade |
| SUIUSDT | short | 2026-09-14 15:38 | 2026-09-14 15:50 | 2026-09-14 16:48 | 1.0 | 0.725 | 0.731 | 0.705 | 0.692 | — | 61 | B | -1.00 | 32.5 | neutral | mixed | 17.7 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE,SHORT_TIGHT_STOP | rsi_chop_30_49,weak_structure,no_history,risk_penalty_applied | immediate_reversal | -0.95 | 0.18 | -0.95 | -0.12 | none | 12 | Immediate Reversal |
| XRPUSDT | long | 2026-09-14 14:44 | 2026-09-14 14:57 | 2026-09-14 18:32 | 3.6 | 1.392 | 1.3312 | 1.4094 | 1.4502 | — | 63 | B | -0.34 | 44.5 | neutral | mixed | 18.9 | 15.0 | 10.0 | 6.0 | 10.0 | 1.5 | 0.47 | HIGH_MOMENTUM_WEAK_STRUCTURE,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure | closed_at_tp2 | 4.61 | 4.61 | 0.37 | — | TP2 | 39 | Perfect Trade |
| SOLUSDT | long | 2026-09-14 14:44 | 2026-09-14 14:57 | 2026-09-25 20:45 | 269.8 | 101.25 | 98.92 | 102.31 | 105.77 | — | 57 | B | -0.25 | 32.7 | neutral | mixed | 13.9 | 15.0 | 7.0 | 6.0 | 10.0 | 3.0 | 0.57 | HIGH_MOMENTUM_WEAK_STRUCTURE,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,negative_cmf | closed_at_tp2 | 21.00 | 21.00 | 0.25 | — | TP2 | 53 | Perfect Trade |
| 1000PEPEUSDT | long | 2026-09-13 11:00 | 2026-09-13 11:06 | 2026-09-25 20:45 | 297.7 | 0.0033925 | 0.0032 | 0.003485 | 0.0037666 | — | 56 | B | -0.21 | 40.8 | neutral | mixed | 15.3 | 15.0 | 7.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | rsi_chop_30_49,weak_structure,no_history,negative_cmf | closed_at_tp2 | 32.42 | 32.42 | -1.42 | — | TP2 | 348 | Perfect Trade |
| CLUSDT | long | 2026-09-13 10:54 | 2026-09-13 11:00 | 2026-09-25 20:45 | 297.8 | 96.35 | 94.6 | 100.9 | 106.98 | — | 63 | B | 0.91 | 42.1 | neutral | mixed | 21.2 | 8.0 | 8.0 | 6.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | some_favorable_move_then_stopped | -4.06 | 4.24 | -4.06 | -2.28 | none | 349 | Scanner Outage |
| FLOCKUSDT | long | 2026-09-13 10:47 | 2026-09-13 14:00 | 2026-09-13 17:49 | 3.8 | 0.07915 | 0.07602 | 0.08205 | 0.08619 | — | 60 | B | 0.02 | 35.4 | neutral | mixed | 25.0 | 11.0 | 7.0 | 6.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,negative_cmf,risk_penalty_applied | some_favorable_move_then_stopped | -5.38 | 2.73 | -5.38 | -1.49 | none | 74 | Weak Structure Entry |
| PUMPUSDT | short | 2026-09-13 10:12 | 2026-09-13 10:19 | 2026-09-26 07:22 | 309.1 | 0.003731 | 0.003971 | 0.003508 | 0.003442 | — | 60 | B | 0.10 | 37.7 | excellent | mixed | 14.9 | 15.0 | 7.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | rsi_chop_30_49,no_history,negative_cmf | reached_tp1_then_stopped | -23.29 | 6.97 | -23.29 | -15.84 | TP1 | 244 | Infrastructure Failure |
| DOGEUSDT | short | 2026-09-13 06:29 | 2026-09-14 09:53 | 2026-09-25 20:45 | 274.9 | 0.084945 | 0.08545 | 0.08454 | 0.08216 | — | 59 | B | -1.00 | 30.0 | neutral | mixed | 14.9 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE,SHORT_TIGHT_STOP | rsi_chop_30_49,weak_structure,no_history | reached_tp1_then_stopped | -15.80 | 2.10 | -15.80 | -15.12 | TP1 | 394 | Infrastructure Failure |
| XAUUSDT | short | 2026-09-13 04:24 | 2026-09-13 04:49 | 2026-09-14 09:25 | 28.6 | 4359.75 | 4390 | 4325 | 4295 | — | 55 | B | -0.31 | 40.8 | good | mixed | 19.5 | 15.0 | 5.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | rsi_chop_30_49,no_history,negative_cmf,mfi_over_80 | closed_at_tp2 | 1.53 | 1.53 | -0.03 | — | TP2 | 306 | Perfect Trade |
| USELESSUSDT | long | 2026-09-13 03:42 | 2026-09-13 03:48 | 2026-09-13 07:16 | 3.5 | 0.2343 | 0.2235 | 0.2448 | 0.2559 | 0.274 | 58 | B | 0.20 | 35.4 | neutral | mixed | 19.5 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,risk_penalty_applied | immediate_reversal | -4.71 | -0.01 | -4.71 | -0.10 | none | 36 | Immediate Reversal |
| PUMPUSDT | long | 2026-09-13 03:12 | 2026-09-13 03:18 | 2026-09-13 08:33 | 5.3 | 0.003775 | 0.0037 | 0.003913 | 0.003967 | — | 56 | B | 0.72 | 37.7 | neutral | mixed | 15.3 | 15.0 | 7.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | rsi_chop_30_49,weak_structure,no_history,negative_cmf | some_favorable_move_then_stopped | -2.15 | 1.80 | -2.15 | -0.16 | none | 54 | Weak Structure Entry |
| ETHUSDT | long | 2026-09-13 02:42 | 2026-09-13 02:48 | 2026-09-13 09:31 | 6.7 | 2518.8 | 2487 | 2546.11 | 2567.24 | 2666 | 55 | B | 0.13 | 26.0 | neutral | mixed | 22.1 | 15.0 | 5.0 | 6.0 | 10.0 | -3.0 | 0.55 | HIGH_MOMENTUM_WEAK_STRUCTURE,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure | immediate_reversal | -1.46 | 0.15 | -1.46 | -0.20 | none | 69 | Immediate Reversal |
| XAGUSDT | short | 2026-09-13 00:24 | 2026-09-13 00:30 | 2026-09-14 09:19 | 32.8 | 64.6 | 64.75 | 64 | 63.03 | — | 51 | C | 1.86 | 37.7 | excellent | mixed | 18.2 | 15.0 | 2.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE,SHORT_TIGHT_STOP | rsi_chop_30_49,no_history,negative_cmf | closed_at_tp2 | 2.93 | 2.93 | -0.01 | — | TP2 | 142 | Perfect Trade |
| WLDUSDT | short | 2026-09-12 16:08 | 2026-09-12 16:14 | 2026-09-25 20:45 | 316.5 | 0.40625 | 0.4165 | 0.398 | 0.387 | 0.378 | 61 | B | -0.41 | 40.8 | good | mixed | 15.2 | 15.0 | 7.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE,SHORT_TIGHT_STOP | rsi_chop_30_49,no_history,negative_cmf | hit_tp2_then_reversed | -18.79 | 4.89 | -18.79 | -15.87 | TP2 | 309 | Infrastructure Failure |
| LABUSDT | long | 2026-09-12 15:39 | 2026-09-12 15:50 | 2026-09-12 15:56 | 0.1 | 0.073 | 0.0695 | 0.0745 | 0.078 | — | 48 | C | -0.09 | 35.4 | neutral | mixed | 20.0 | 15.0 | 7.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,negative_cmf,risk_penalty_applied | immediate_reversal | -7.36 | 0.62 | -7.36 | -2.69 | none | 3 | Immediate Reversal |
| SKHYUSDT | long | 2026-09-12 15:33 | 2026-09-12 15:39 | 2026-09-13 08:28 | 16.8 | 190.2 | 185 | 194 | 197 | 199.6 | 68 | B+ | 0.11 | 42.1 | neutral | mixed | 24.6 | 8.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | immediate_reversal | -2.92 | 0.15 | -2.92 | -0.20 | none | 33 | Immediate Reversal |
| SKHYNIXUSDT | long | 2026-09-12 15:21 | 2026-09-12 15:27 | 2026-09-12 19:38 | 4.2 | 1365.25 | 1360.5 | 1374.4 | 1396 | 1418 | 66 | B+ | 0.87 | 37.7 | neutral | mixed | 22.7 | 8.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | immediate_reversal | -2.28 | 0.25 | -2.28 | -1.94 | none | 38 | Immediate Reversal |
| CRCLUSDT | short | 2026-09-12 14:23 | 2026-09-12 14:29 | 2026-09-14 12:34 | 46.1 | 91.75 | 92.6 | 90.76 | 89.24 | — | 54 | C | -0.30 | 45.4 | good | mixed | 16.2 | 15.0 | 7.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE,SHORT_TIGHT_STOP | rsi_chop_30_49,no_history,negative_cmf | reached_tp1_then_stopped | -0.99 | 1.50 | -0.99 | -0.07 | TP1 | 41 | TP1 Hit — Should Have Exited |
| RIVERUSDT | long | 2026-09-12 13:13 | 2026-09-12 13:19 | 2026-09-12 18:34 | 5.2 | 1.27 | 1.19 | 1.35 | 1.457 | — | 50 | C | 0.28 | 44.5 | neutral | mixed | 19.5 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,risk_penalty_applied | closed_at_tp2 | 18.82 | 18.82 | -0.71 | — | TP2 | 55 | Perfect Trade |
| SPCXUSDT | long | 2026-09-12 12:03 | 2026-09-12 12:09 | 2026-09-14 01:15 | 37.1 | 150.1 | 148.6 | 151.78 | 154.77 | — | 61 | B | 0.70 | 35.0 | excellent | mixed | 20.5 | 15.0 | 2.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | no_history,negative_cmf | immediate_reversal | -1.27 | 0.11 | -1.27 | -0.27 | none | 82 | Immediate Reversal |
| SOLUSDT | long | 2026-09-06 07:06 | 2026-09-06 07:07 | 2026-09-12 06:56 | 143.8 | 104.8 | 102.6 | 107 | 109.5 | 113.6 | 73 | B+ | — | 32.7 | excellent | risk_on | 19.7 | 15.0 | 10.0 | 11.0 | 10.0 | 3.0 | 0.52 | CLUSTERED_MARKET_EXPOSURE | — | immediate_reversal | -2.98 | 0.54 | -2.98 | -0.90 | none | 5 | Scanner Outage |
| LINKUSDT | long | 2026-09-06 07:06 | 2026-09-06 07:07 | 2026-09-12 06:56 | 143.8 | 12.185 | 11.85 | 12.58 | 13 | — | 72 | B+ | — | 45.4 | excellent | risk_on | 21.3 | 11.0 | 10.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | no_history | immediate_reversal | -5.49 | 0.69 | -5.49 | -2.82 | none | 5 | Scanner Outage |
| FILUSDT | long | 2026-09-06 06:53 | 2026-09-06 07:06 | 2026-09-13 14:56 | 175.8 | 0.8021 | 0.7852 | 0.8399 | 0.8672 | — | 69 | B+ | — | 44.5 | excellent | risk_on | 21.1 | 15.0 | 7.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | no_history,negative_cmf | closed_at_tp2 | 14.90 | 14.90 | -0.37 | — | TP2 | 6 | Perfect Trade |
| HEMIUSDT | long | 2026-08-29 03:31 | 2026-08-29 06:47 | 2026-08-29 07:03 | 0.3 | 0.01165 | 0.0109 | 0.01312 | 0.013949 | 0.016 | 64 | B | — | 35.4 | neutral | mixed | 25.0 | 11.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,risk_penalty_applied | immediate_reversal | -8.62 | 0.57 | -8.62 | -2.33 | none | 34 | Immediate Reversal |
| ENAUSDT | long | 2026-08-29 03:31 | 2026-08-29 03:38 | 2026-08-29 08:16 | 4.6 | 0.163 | 0.157 | 0.16471 | 0.17444 | 0.18375 | 59 | B | — | 35.4 | neutral | mixed | 25.0 | 15.0 | 5.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,risk_penalty_applied | reached_tp1_then_stopped | -4.10 | 1.47 | -4.10 | -0.44 | TP1 | 47 | TP1 Hit — Should Have Exited |
| SOXSUSDT | long | 2026-08-29 03:31 | 2026-08-29 03:38 | 2026-09-02 20:20 | 112.7 | 49.3 | 47.8 | 49.81 | 50.23 | 52.85 | 60 | B | — | 49.2 | neutral | mixed | 16.1 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | ran_to_tp3 | 7.50 | 7.50 | 0.12 | — | TP3 | 118 | Perfect Trade |
| SKHYUSDT | long | 2026-08-29 03:31 | 2026-08-29 03:38 | 2026-09-03 05:21 | 121.7 | 161.6 | 160.3 | 163.5 | 166.71 | — | 62 | B | — | 42.1 | neutral | mixed | 18.5 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | reached_tp1_then_stopped | -1.57 | 2.28 | -1.57 | -0.77 | TP1 | 226 | TP1 Hit — Should Have Exited |
| SNXXUSDT | short | 2026-08-29 03:00 | 2026-08-29 03:07 | 2026-09-02 18:59 | 111.9 | 12.9 | 13.45 | 12.2 | 12.02 | 11.65 | 64 | B | — | 32.5 | neutral | mixed | 20.2 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | rsi_chop_30_49,weak_structure,no_history | immediate_reversal | -8.06 | 0.62 | -8.06 | -3.64 | none | 118 | Scanner Outage |
| SNDKUSDT | short | 2026-08-29 03:00 | 2026-08-29 03:07 | 2026-09-02 18:59 | 111.9 | 1485 | 1517 | 1477 | 1436 | 1419.66 | 59 | B | — | 37.7 | neutral | mixed | 15.0 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | rsi_chop_30_49,weak_structure,no_history | immediate_reversal | -4.30 | 0.10 | -4.30 | -2.10 | none | 118 | Scanner Outage |
| CLUSDT | long | 2026-08-29 03:00 | 2026-08-29 03:07 | 2026-09-02 18:59 | 111.9 | 83.15 | 82.2 | 83.63 | 84.41 | — | 58 | B | — | 42.1 | neutral | mixed | 14.4 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | closed_at_tp2 | 9.22 | 9.22 | -0.20 | — | TP2 | 118 | Perfect Trade |
| ZECUSDT | long | 2026-08-29 01:50 | 2026-08-29 01:57 | 2026-09-06 06:22 | 196.4 | 802 | 775 | 817.22 | 889.99 | — | 65 | B+ | — | 42.1 | neutral | mixed | 20.9 | 8.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | closed_at_tp2 | 45.44 | 45.44 | -1.45 | — | TP2 | 338 | Perfect Trade |
| TRUMPUSDT | long | 2026-08-29 00:06 | 2026-08-29 00:34 | 2026-09-02 18:59 | 114.4 | 2.75 | 2.505 | 2.892 | 3.1 | — | 47 | C | — | 35.4 | neutral | mixed | 24.8 | 15.0 | 2.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,negative_cmf,risk_penalty_applied | reached_tp1_then_stopped | -20.95 | 10.98 | -20.95 | -13.21 | TP1 | 148 | Infrastructure Failure |
| MOVRUSDT | long | 2026-08-28 19:42 | 2026-08-28 20:11 | 2026-08-28 20:41 | 0.5 | 0.9115 | 0.845 | 0.975 | 1.038 | 1.138 | 59 | B | — | 32.5 | neutral | mixed | 20.0 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,risk_penalty_applied | immediate_reversal | -16.01 | 0.23 | -16.01 | -9.40 | none | 10 | Infrastructure Failure |
| BNBUSDT | long | 2026-08-28 18:03 | 2026-08-28 18:07 | 2026-08-28 18:40 | 0.6 | 694.55 | 686.9 | 707.78 | 719.14 | — | 71 | B+ | — | 37.7 | good | mixed | 20.0 | 8.0 | 5.0 | 11.0 | 10.0 | 10.5 | 0.54 | CLUSTERED_MARKET_EXPOSURE | rsi_chop_30_49,risk_penalty_applied | immediate_reversal | -1.14 | -0.17 | -1.14 | -0.04 | none | 7 | Immediate Reversal |
| MOVRUSDT | long | 2026-08-28 15:58 | 2026-08-28 16:05 | 2026-08-28 16:29 | 0.4 | 0.9085 | 0.8935 | 0.975 | 1.023 | 1.138 | 61 | B | — | 32.5 | neutral | risk_on | 20.0 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,risk_penalty_applied | immediate_reversal | -2.93 | -0.11 | -2.93 | -1.30 | none | 5 | Immediate Reversal |
| MSTRUSDT | long | 2026-08-28 15:51 | 2026-08-28 15:58 | 2026-09-02 18:59 | 123.0 | 129 | 126.5 | 136.17 | 140.85 | 143.19 | 65 | B+ | — | 30.0 | good | risk_on | 19.5 | 15.0 | 5.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | no_history,risk_penalty_applied | immediate_reversal | -4.95 | -0.32 | -4.95 | -3.07 | none | 233 | Scanner Outage |
| SPCXUSDT | long | 2026-08-28 15:51 | 2026-08-28 15:58 | 2026-09-03 13:47 | 141.8 | 140.1 | 138.4 | 141.96 | 143.5 | 146.1 | 65 | B+ | — | 35.0 | neutral | risk_on | 18.8 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | ran_to_tp3 | 4.75 | 4.75 | -1.12 | — | TP3 | 437 | Perfect Trade |
| MSTRUSDT | long | 2026-08-28 15:21 | 2026-08-28 15:28 | 2026-08-28 15:51 | 0.4 | 133.7 | 129.5 | 137.17 | 141.1 | 143.19 | 65 | B+ | — | 30.0 | good | risk_on | 19.6 | 15.0 | 5.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | no_history | immediate_reversal | -3.44 | -0.75 | -3.44 | -0.31 | none | 5 | Immediate Reversal |
| ETHUSDT | long | 2026-08-28 15:03 | 2026-08-28 15:10 | 2026-08-28 15:58 | 0.8 | 2502 | 2478 | 2535 | 2570 | 2620 | 76 | A | — | 26.0 | neutral | risk_on | 24.4 | 8.0 | 10.0 | 6.0 | 10.0 | 9.0 | 0.49 | HIGH_SCORE_WEAK_STRUCTURE,CLUSTERED_MARKET_EXPOSURE | weak_structure | immediate_reversal | -1.07 | 0.20 | -1.07 | -0.11 | none | 9 | Immediate Reversal |
| SUIUSDT | long | 2026-08-28 14:57 | 2026-08-28 15:03 | 2026-09-12 06:56 | 351.9 | 0.76925 | 0.7241 | 0.8013 | 0.9555 | — | 63 | B | — | 32.5 | neutral | risk_on | 19.9 | 15.0 | 7.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | rsi_chop_30_49,weak_structure,no_history,negative_cmf | some_favorable_move_then_stopped | -5.97 | 3.59 | -5.97 | -0.11 | none | 462 | Scanner Outage |
| XAGUSDT | long | 2026-08-28 14:51 | 2026-08-28 15:15 | 2026-08-28 16:22 | 1.1 | 69.4 | 67.4 | 71.01 | 71.23 | — | 61 | B | — | 37.7 | neutral | risk_on | 20.1 | 15.0 | 5.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | immediate_reversal | -3.80 | 0.06 | -3.80 | -0.95 | none | 15 | Immediate Reversal |
| SOLUSDT | long | 2026-08-28 14:04 | 2026-08-28 14:10 | 2026-09-02 18:59 | 124.8 | 104.4 | 100.9 | 106.8 | 110 | 113 | 73 | B+ | — | 32.7 | good | risk_on | 24.9 | 15.0 | 5.0 | 11.0 | 10.0 | -3.0 | 0.52 | LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | — | reached_tp1_then_stopped | -4.77 | 2.73 | -4.77 | -1.47 | TP1 | 251 | Scanner Outage |
| MSTRUSDT | long | 2026-08-28 13:34 | 2026-08-28 13:40 | 2026-08-28 14:10 | 0.5 | 134.74 | 132.4 | 136.55 | 137.17 | 141.1 | 71 | B+ | — | 30.0 | good | risk_on | 24.8 | 15.0 | 5.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | no_history | immediate_reversal | -1.77 | 0.28 | -1.77 | -0.04 | none | 6 | Immediate Reversal |
| MUUSDT | long | 2026-08-21 10:23 | 2026-08-21 10:34 | 2026-08-28 12:24 | 169.8 | 977.35 | 963.73 | 987.97 | 1021.79 | 1036 | 66 | B+ | — | 40.8 | neutral | risk_on | 19.8 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | immediate_reversal | -5.75 | 0.40 | -5.75 | -4.42 | none | 5 | Scanner Outage |
| DRAMUSDT | long | 2026-08-21 08:59 | 2026-08-21 09:05 | 2026-08-28 12:24 | 171.3 | 58.425 | 57.35 | 59.37 | 60.81 | 62.09 | 63 | B | — | 35.0 | neutral | risk_on | 19.7 | 15.0 | 7.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,negative_cmf | immediate_reversal | -4.29 | 0.62 | -4.29 | -2.49 | none | 18 | Scanner Outage |
| SAMSUNGUSDT | long | 2026-08-21 08:13 | 2026-08-21 08:25 | 2026-08-28 12:24 | 172.0 | 196.75 | 191 | 203.4 | 206 | 211.5 | 68 | B+ | — | 45.4 | neutral | risk_on | 22.0 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,NO_HISTORY,NO_ML | weak_structure,no_history,liquidity_stress | immediate_reversal | -4.56 | 0.49 | -4.56 | -1.69 | none | 26 | Scanner Outage |
| LINKUSDT | long | 2026-08-16 12:03 | 2026-08-16 12:09 | 2026-08-21 07:40 | 115.5 | 9.34 | 9.18 | 9.507 | 9.63 | — | 64 | B | — | 45.4 | neutral | mixed | 25.0 | 15.0 | 5.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | closed_at_tp2 | 24.70 | 24.70 | -0.12 | — | TP2 | 10 | Perfect Trade |
| CLUSDT | long | 2026-08-16 09:45 | 2026-08-16 09:51 | 2026-08-21 07:40 | 117.8 | 81.225 | 80.8 | 81.56 | 82 | 84.04 | 62 | B | — | 42.1 | neutral | mixed | 18.6 | 8.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | ran_to_tp3 | 6.35 | 6.35 | 0.04 | — | TP3 | 24 | Perfect Trade |
| ZECUSDT | short | 2026-08-16 09:27 | 2026-08-16 09:34 | 2026-08-21 07:40 | 118.1 | 488.5 | 494.5 | 483.45 | 480.27 | 466.28 | 59 | B | — | 42.1 | neutral | mixed | 18.6 | 15.0 | 7.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | rsi_chop_30_49,weak_structure,no_history,negative_cmf | immediate_reversal | -28.80 | 0.76 | -28.80 | -27.24 | none | 27 | Infrastructure Failure |
| ALLOUSDT | short | 2026-08-16 08:42 | 2026-08-16 10:31 | 2026-08-16 11:06 | 0.6 | 0.268 | 0.274 | 0.2616 | 0.2535 | 0.244 | 63 | B | — | 35.4 | neutral | mixed | 22.7 | 11.0 | 7.0 | 6.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | rsi_chop_30_49,weak_structure,no_history,negative_cmf | immediate_reversal | -2.76 | 0.55 | -2.76 | -0.51 | none | 15 | Scanner Outage |
| HYPEUSDT | long | 2026-08-16 08:07 | 2026-08-16 09:45 | 2026-08-21 07:40 | 117.9 | 57.145 | 56.55 | 57.85 | 58.45 | 59.1 | 65 | B+ | — | 42.1 | excellent | mixed | 19.4 | 15.0 | 7.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | no_history,negative_cmf | ran_to_tp3 | 29.07 | 29.07 | 0.12 | — | TP3 | 34 | Perfect Trade |
| ETHUSDT | short | 2026-08-16 07:44 | 2026-08-16 07:55 | 2026-08-21 07:40 | 119.7 | 1880.25 | 1890.6 | 1876 | 1852.22 | — | 56 | B | — | 26.0 | neutral | mixed | 15.0 | 15.0 | 10.0 | 6.0 | 10.0 | 4.5 | 0.64 | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | rsi_chop_30_49,weak_structure | immediate_reversal | -26.67 | 0.11 | -26.67 | -25.98 | none | 37 | Infrastructure Failure |
| SPORTFUNUSDT | long | 2026-08-16 03:29 | 2026-08-16 03:40 | 2026-08-16 06:42 | 3.0 | 0.0258 | 0.02422 | 0.02975 | 0.03598 | — | 59 | B | — | 35.4 | neutral | mixed | 23.9 | 15.0 | 7.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,negative_cmf,risk_penalty_applied | immediate_reversal | -6.12 | 0.78 | -6.12 | 0.00 | none | 5 | Immediate Reversal |
| WLDUSDT | long | 2026-08-15 21:29 | 2026-08-15 21:35 | 2026-08-21 07:40 | 130.1 | 0.34795 | 0.339 | 0.3547 | 0.3629 | 0.372 | 67 | B+ | — | 40.8 | excellent | mixed | 21.9 | 15.0 | 7.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | no_history,negative_cmf | ran_to_tp3 | 8.29 | 8.29 | -1.48 | — | TP3 | 77 | Perfect Trade |
| PUMPUSDT | long | 2026-08-15 17:42 | 2026-08-15 20:20 | 2026-08-21 07:40 | 131.3 | 0.002807 | 0.002681 | 0.002946 | 0.002987 | — | 71 | B+ | — | 37.7 | excellent | mixed | 22.3 | 8.0 | 10.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | no_history | closed_at_tp2 | 39.37 | 39.37 | -3.46 | — | TP2 | 96 | Good Entry, Good Exit |
| SKHYNIXUSDT | long | 2026-08-15 17:07 | 2026-08-16 13:01 | 2026-08-21 07:40 | 114.6 | 1171.17 | 1157.05 | 1209 | 1221.99 | — | 65 | B+ | — | 37.7 | excellent | mixed | 20.0 | 8.0 | 7.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | no_history,negative_cmf | closed_at_tp2 | 7.07 | 7.07 | 0.17 | — | TP2 | 99 | Perfect Trade |
| DOGEUSDT | short | 2026-08-15 16:26 | 2026-08-15 17:07 | 2026-08-21 07:40 | 134.5 | 0.07015 | 0.0711 | 0.0688 | 0.0677 | — | 53 | C | — | 30.0 | neutral | mixed | 20.6 | 15.0 | 7.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | rsi_chop_30_49,weak_structure,no_history,negative_cmf | immediate_reversal | -20.31 | 0.95 | -20.31 | -18.71 | none | 102 | Infrastructure Failure |
| BNBUSDT | long | 2026-08-14 00:44 | 2026-08-14 00:50 | 2026-08-14 11:14 | 10.4 | 610.5 | 604.7 | 615.2 | 620.9 | — | 69 | B+ | — | 37.7 | excellent | mixed | 21.2 | 8.0 | 5.0 | 11.0 | 10.0 | 6.0 | 0.55 | LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | — | immediate_reversal | -1.01 | 0.37 | -1.01 | -0.06 | none | 108 | Immediate Reversal |
| SAMSUNGUSDT | long | 2026-08-14 00:44 | 2026-08-14 02:12 | 2026-08-21 07:40 | 173.5 | 191.5 | 182.5 | 195.25 | 199.6 | — | 66 | B+ | — | 45.4 | neutral | mixed | 25.0 | 11.0 | 8.0 | 6.0 | 10.0 | 0.0 | — | HIGH_SCORE_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,mfi_over_80 | closed_at_tp2 | 6.42 | 6.42 | -0.95 | — | TP2 | 115 | Perfect Trade |
| APRUSDT | long | 2026-08-14 00:33 | 2026-08-14 00:44 | 2026-08-14 12:29 | 11.8 | 0.457 | 0.401 | 0.4877 | 0.5278 | 0.5393 | 64 | B | — | 44.5 | neutral | mixed | 25.0 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,risk_penalty_applied | ran_to_tp3 | 19.04 | 19.04 | -4.33 | — | TP3 | 114 | Good Entry, Good Exit |
| SPCXUSDT | long | 2026-08-13 19:27 | 2026-08-13 19:33 | 2026-08-15 14:00 | 42.4 | 143.55 | 139.6 | 148.6 | 152 | — | 66 | B+ | — | 35.0 | good | mixed | 22.6 | 15.0 | 5.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | no_history | immediate_reversal | -2.77 | 0.81 | -2.77 | -0.01 | none | 176 | Immediate Reversal |
| LINKUSDT | long | 2026-08-13 17:20 | 2026-08-14 08:24 | 2026-08-15 13:13 | 28.8 | 8.705 | 8.58 | 8.865 | 8.982 | 9.038 | 67 | B+ | — | 45.4 | neutral | mixed | 23.5 | 8.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | ran_to_tp3 | 8.66 | 8.66 | 0.31 | — | TP3 | 191 | Perfect Trade |
| BTWUSDT | long | 2026-08-13 15:48 | 2026-08-13 15:54 | 2026-08-15 18:35 | 50.7 | 0.2615 | 0.235 | 0.2692 | 0.285 | 0.31 | 60 | B | — | 49.2 | excellent | mixed | 19.3 | 15.0 | 10.0 | 11.0 | 5.0 | 0.0 | — | NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | no_history,risk_penalty_applied,funding_elevated | ran_to_tp3 | 21.02 | 21.02 | 0.10 | — | TP3 | 155 | Perfect Trade |
| ETHUSDT | long | 2026-08-13 15:42 | 2026-08-13 15:48 | 2026-08-13 16:40 | 0.9 | 1888 | 1873 | 1899.6 | 1911.5 | 1943 | 65 | B+ | — | 26.0 | neutral | mixed | 14.1 | 15.0 | 7.0 | 6.0 | 10.0 | 12.0 | 0.65 | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | rsi_chop_30_49,weak_structure,negative_cmf | immediate_reversal | -1.01 | -0.00 | -1.01 | -0.21 | none | 10 | Immediate Reversal |
| MUUSDT | long | 2026-08-13 13:29 | 2026-08-13 13:35 | 2026-08-13 13:47 | 0.2 | 911.25 | 901.5 | 916.1 | 929 | — | 64 | B | — | 40.8 | neutral | mixed | 20.2 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | closed_at_tp2 | 2.53 | 2.53 | 0.26 | — | TP2 | 3 | Perfect Trade |
| SAMSUNGUSDT | long | 2026-08-13 13:10 | 2026-08-13 13:16 | 2026-08-13 15:24 | 2.1 | 185.75 | 183.3 | 191.23 | 195.7 | — | 66 | B+ | — | 45.4 | neutral | mixed | 24.4 | 11.0 | 8.0 | 6.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,mfi_over_80 | closed_at_tp2 | 5.44 | 5.44 | 0.20 | — | TP2 | 22 | Perfect Trade |
| SOXSUSDT | short | 2026-08-13 12:52 | 2026-08-13 12:58 | 2026-08-13 13:04 | 0.1 | 41.15 | 41.95 | 39.88 | 41.82 | — | 69 | B+ | — | 49.2 | good | mixed | 21.1 | 8.0 | 10.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | rsi_chop_30_49,no_history | closed_at_tp2 | 0.70 | 0.70 | 0.24 | — | TP2 | 2 | Perfect Trade |
| EWYUSDT | long | 2026-08-13 12:03 | 2026-08-13 12:10 | 2026-08-13 14:36 | 2.4 | 174.6 | 172.5 | 177.9 | 178.7 | — | 64 | B | — | 40.8 | neutral | mixed | 22.4 | 15.0 | 8.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,mfi_over_80 | closed_at_tp2 | 2.63 | 2.63 | -0.18 | — | TP2 | 25 | Perfect Trade |
| DRAMUSDT | long | 2026-08-13 11:27 | 2026-08-13 11:33 | 2026-08-13 14:24 | 2.9 | 54.35 | 53.6 | 55.05 | 55.86 | — | 64 | B | — | 35.0 | good | mixed | 17.5 | 15.0 | 8.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | no_history,mfi_over_80 | closed_at_tp2 | 2.83 | 2.83 | -0.33 | — | TP2 | 29 | Perfect Trade |
| NVDAUSDT | long | 2026-08-13 11:27 | 2026-08-13 15:36 | 2026-08-28 12:24 | 356.8 | 223.85 | 221.2 | 225.24 | 226.48 | — | 62 | B | — | 49.2 | neutral | mixed | 23.6 | 15.0 | 5.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,negative_cmf,mfi_over_80 | closed_at_tp2 | 1.58 | 1.58 | 0.15 | — | TP2 | 49 | Perfect Trade |
| SKHYUSDT | long | 2026-08-13 09:21 | 2026-08-13 09:27 | 2026-08-13 14:48 | 5.3 | 150.8 | 144.3 | 154.06 | 157.06 | 163.87 | 64 | B | — | 42.1 | good | mixed | 18.1 | 15.0 | 8.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | no_history,mfi_over_80 | ran_to_tp3 | 8.69 | 8.69 | 0.38 | — | TP3 | 54 | Perfect Trade |
| CYSUSDT | long | 2026-08-13 08:01 | 2026-08-13 08:07 | 2026-08-13 09:21 | 1.2 | 1.465 | 1.38 | 1.5923 | 1.6995 | 1.7787 | 63 | B | — | 40.8 | good | mixed | 25.0 | 15.0 | 5.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | no_history,risk_penalty_applied | immediate_reversal | -6.08 | 0.74 | -6.08 | -0.30 | none | 13 | Immediate Reversal |
| XAUUSDT | long | 2026-08-13 05:13 | 2026-08-13 05:34 | 2026-08-13 06:37 | 1.1 | 4400.5 | 4380 | 4436 | 4456.65 | 4490 | 68 | B+ | — | 40.8 | neutral | mixed | 25.0 | 8.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | immediate_reversal | -0.58 | 0.05 | -0.58 | -0.12 | none | 16 | Immediate Reversal |
| PAXGUSDT | long | 2026-08-13 05:13 | 2026-08-13 05:34 | 2026-08-13 06:37 | 1.1 | 4390.5 | 4368 | 4425 | 4440.7 | 4479 | 68 | B+ | — | 40.8 | neutral | mixed | 25.0 | 8.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | immediate_reversal | -0.59 | 0.06 | -0.59 | -0.08 | none | 16 | Immediate Reversal |
| BTWUSDT | long | 2026-08-13 04:55 | 2026-08-13 05:13 | 2026-08-13 15:18 | 10.1 | 0.23761 | 0.214 | 0.25517 | 0.26918 | — | 61 | B | — | 49.2 | good | mixed | 19.9 | 15.0 | 10.0 | 11.0 | 5.0 | 0.0 | — | NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | no_history,risk_penalty_applied,funding_elevated | closed_at_tp2 | 13.49 | 13.49 | -3.51 | — | TP2 | 105 | Good Entry, Good Exit |
| XAGUSDT | long | 2026-08-12 19:17 | 2026-08-12 19:23 | 2026-08-13 19:15 | 23.9 | 65.35 | 64.35 | 66.59 | 67.04 | 68.5 | 68 | B+ | — | 37.7 | good | mixed | 25.0 | 8.0 | 5.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | no_history | some_favorable_move_then_stopped | -1.55 | 1.42 | -1.55 | -0.02 | none | 245 | Counter Trend Entry |
| CRCLUSDT | long | 2026-08-12 14:50 | 2026-08-12 14:55 | 2026-08-13 19:04 | 28.1 | 69.8 | 68.4 | 71.5 | 72.4 | — | 54 | C | — | 45.4 | neutral | mixed | 23.3 | 15.0 | 5.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | closed_at_tp2 | 5.70 | 5.70 | -0.43 | — | TP2 | 31 | Perfect Trade |
| LITEUSDT | long | 2026-08-12 13:17 | 2026-08-12 13:29 | 2026-08-12 13:40 | 0.2 | 892.5 | 855 | 930 | 955 | — | 73 | B+ | — | 35.4 | excellent | mixed | 24.1 | 15.0 | 10.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | no_history | immediate_reversal | -5.12 | 0.84 | -5.12 | -0.96 | none | 3 | Scanner Outage |
| CLUSDT | long | 2026-08-12 11:49 | 2026-08-12 11:55 | 2026-08-13 08:38 | 20.7 | 82.55 | 81 | 84 | 85 | 86.5 | 62 | B | — | 42.1 | neutral | mixed | 23.8 | 15.0 | 5.0 | 6.0 | 10.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history | immediate_reversal | -1.98 | 0.28 | -1.98 | -0.10 | none | 176 | Immediate Reversal |
| HOLOUSDT | long | 2026-08-12 10:15 | 2026-08-12 10:21 | 2026-08-12 18:28 | 8.1 | 0.07725 | 0.074 | 0.0825 | 0.0865 | 0.09 | 64 | B | — | 35.4 | good | mixed | 23.5 | 15.0 | 7.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | no_history,negative_cmf,risk_penalty_applied | immediate_reversal | -7.17 | 0.63 | -7.17 | -3.10 | none | 45 | Scanner Outage |
| DOGEUSDT | long | 2026-08-12 08:37 | 2026-08-12 08:43 | 2026-08-12 21:31 | 12.8 | 0.0714 | 0.06975 | 0.0735 | 0.07485 | 0.0762 | 56 | B | — | 30.0 | good | mixed | 15.6 | 15.0 | 10.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | no_history | some_favorable_move_then_stopped | -2.52 | 1.06 | -2.52 | -0.21 | none | 94 | Counter Trend Entry |
| VELVETUSDT | long | 2026-08-12 08:02 | 2026-08-12 08:08 | 2026-08-12 18:28 | 10.3 | 0.5505 | 0.505 | 0.595 | 0.628 | 0.679 | 63 | B | — | 44.5 | good | mixed | 24.7 | 15.0 | 5.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,LOW_TP1_RR,CLUSTERED_MARKET_EXPOSURE | no_history,risk_penalty_applied | ran_to_tp3 | 27.28 | 27.28 | -0.45 | — | TP3 | 68 | Perfect Trade |
| NEARUSDT | long | 2026-08-12 07:56 | 2026-08-12 08:02 | 2026-08-21 07:40 | 215.6 | 1.6425 | 1.595 | 1.69 | 1.72 | 1.76 | 61 | B | — | 49.2 | excellent | mixed | 15.3 | 15.0 | 7.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | no_history,negative_cmf | ran_to_tp3 | 13.36 | 13.36 | -1.80 | — | TP3 | 72 | Perfect Trade |
| BZUSDT | long | 2026-08-12 07:31 | 2026-08-12 07:37 | 2026-08-13 08:38 | 25.0 | 87.6 | 85.9 | 89.5 | 91 | 92.9 | 65 | B+ | — | 32.5 | neutral | mixed | 24.3 | 15.0 | 10.0 | 6.0 | 5.0 | 0.0 | — | HIGH_MOMENTUM_WEAK_STRUCTURE,HIGH_SCORE_WEAK_STRUCTURE,NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | weak_structure,no_history,funding_elevated | immediate_reversal | -2.02 | 0.60 | -2.02 | -0.08 | none | 220 | Immediate Reversal |
| SKHYUSDT | long | 2026-08-12 05:26 | 2026-08-12 05:44 | 2026-08-12 13:52 | 8.1 | 143.9 | 139.5 | 148.5 | 152 | — | 63 | B | — | 42.1 | excellent | mixed | 14.7 | 15.0 | 10.0 | 11.0 | 10.0 | 0.0 | — | NO_HISTORY,NO_ML,CLUSTERED_MARKET_EXPOSURE | no_history | closed_at_tp2 | 5.63 | 5.63 | 0.51 | — | TP2 | 85 | Perfect Trade |
| HYPEUSDT | short | 2026-08-11 19:18 | 2026-08-11 19:24 | 2026-08-12 11:20 | 15.9 | 54.3 | 55.65 | 52.6 | 51.4 | 49.4 | 64 | B | — | 42.1 | excellent | mixed | 18.6 | 8.0 | 7.0 | 11.0 | 10.0 | 0.0 | — | — | rsi_chop_30_49,no_history | immediate_reversal | -2.56 | 0.34 | -2.56 | -0.07 | none | 67 | Immediate Reversal |
| SOLUSDT | short | 2026-08-11 19:11 | 2026-08-11 19:18 | 2026-08-12 09:29 | 14.2 | 75.15 | 76.55 | 73.9 | 72.6 | 71 | 65 | B+ | — | 32.7 | excellent | mixed | 20.1 | 8.0 | 2.0 | 11.0 | 10.0 | 4.5 | 0.56 | — | rsi_chop_30_49 | immediate_reversal | -2.04 | 0.01 | -2.04 | -0.17 | none | 49 | Immediate Reversal |
| SNDKUSDT | long | 2026-08-11 18:14 | 2026-08-11 18:32 | 2026-08-12 12:54 | 18.4 | 1263 | 1233.5 | 1290 | 1315 | 1340 | 62 | B | — | 37.7 | excellent | mixed | 13.6 | 15.0 | 10.0 | 11.0 | 10.0 | 0.0 | — | — | no_history | ran_to_tp3 | 6.26 | 6.26 | 0.19 | — | TP3 | 92 | Perfect Trade |
| SNXXUSDT | short | 2026-08-11 17:09 | 2026-08-11 17:15 | 2026-08-12 05:26 | 12.2 | 9.825 | 10.35 | 9.35 | 8.85 | 8.35 | 55 | B | — | 32.5 | good | mixed | 13.5 | 15.0 | 8.0 | 11.0 | 10.0 | 0.0 | — | — | no_history,risk_penalty_applied | immediate_reversal | -5.55 | 0.46 | -5.55 | -0.19 | none | 26 | Scanner Outage |
| RKLBUSDT | short | 2026-08-11 16:57 | 2026-08-11 17:03 | 2026-08-11 18:49 | 1.8 | 78.1 | 80.15 | 75.8 | 73.5 | 71.5 | 68 | B+ | — | 35.4 | good | mixed | 22.9 | 8.0 | 7.0 | 11.0 | 10.0 | 0.0 | — | — | rsi_chop_30_49,no_history | immediate_reversal | -2.66 | 0.41 | -2.66 | — | none | 19 | Immediate Reversal |
| DRAMUSDT | short | 2026-08-11 15:46 | 2026-08-11 15:52 | 2026-08-12 05:26 | 13.6 | 50.875 | 51.75 | 49.8 | 48.6 | — | 59 | B | — | 35.0 | neutral | mixed | 15.0 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | — | weak_structure,no_history | immediate_reversal | -3.35 | 0.85 | -3.35 | -1.60 | none | 40 | Scanner Outage |
| HYPEUSDT | long | 2026-08-11 13:11 | 2026-08-11 13:17 | 2026-08-11 15:35 | 2.3 | 55.05 | 54.25 | 55.75 | 56.4 | 57.1 | 57 | B | — | 42.1 | neutral | mixed | 13.2 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | — | weak_structure,no_history | immediate_reversal | -1.64 | -0.00 | -1.64 | — | none | 25 | Immediate Reversal |
| SKHYNIXUSDT | short | 2026-08-11 09:49 | 2026-08-11 09:55 | 2026-08-12 05:26 | 19.5 | 1008.5 | 1037.5 | 991.7 | 964 | — | 55 | B | — | 37.7 | neutral | mixed | 19.4 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | — | rsi_chop_30_49,weak_structure,no_history | immediate_reversal | -5.00 | 0.09 | -5.00 | -2.06 | none | 102 | Scanner Outage |
| BTCUSDT | long | 2026-08-10 05:47 | 2026-08-10 05:50 | 2026-08-11 07:11 | 25.3 | 65000 | 64350 | 65650 | 66300 | 67200 | 69 | B+ | — | 35.4 | — | risk_on | 19.7 | 8.0 | 7.0 | 6.0 | 10.0 | 7.5 | 0.60 | — | weak_structure | immediate_reversal | -1.61 | 0.24 | -1.61 | — | none | 6 | Scanner Outage |
| ETHUSDT | long | 2026-08-10 05:47 | 2026-08-10 05:50 | 2026-08-11 07:11 | 25.3 | 1918 | 1888 | 1945 | 1965 | 1990 | 69 | B+ | — | 26.0 | — | risk_on | 19.0 | 8.0 | 7.0 | 6.0 | 10.0 | 7.5 | 0.62 | — | weak_structure | immediate_reversal | -2.32 | 0.27 | -2.32 | — | none | 6 | Scanner Outage |
| SOLUSDT | long | 2026-08-10 05:47 | 2026-08-10 05:50 | 2026-08-11 15:40 | 33.8 | 76.5 | 74.9 | 78.2 | 79.5 | — | 45 | C | — | 32.7 | — | risk_on | 22.3 | 15.0 | 10.0 | 6.0 | 10.0 | 1.5 | 0.63 | — | weak_structure | immediate_reversal | -2.21 | 0.51 | -2.21 | — | none | 96 | Immediate Reversal |
| 1000PEPEUSDT | long | 2026-08-10 05:47 | 2026-08-10 05:50 | 2026-08-13 00:20 | 66.5 | 0.0029 | 0.00282 | 0.00297 | 0.00305 | 0.00315 | 64 | B | — | 40.8 | — | risk_on | 20.7 | 15.0 | 7.0 | 6.0 | 10.0 | 0.0 | — | — | weak_structure,no_history | immediate_reversal | -7.47 | 0.15 | -7.47 | -4.85 | none | 14 | Immediate Reversal |
| BICOUSDT | long | 2026-08-09 05:40 | 2026-08-09 05:46 | 2026-08-10 05:12 | 23.4 | 0.07085 | 0.0615 | 0.0785 | 0.085 | 0.095 | 71 | B+ | — | 35.4 | — | risk_on | 25.0 | 9.0 | 10.0 | 11.0 | 10.0 | 0.0 | — | — | no_history,high_atr_extension,risk_penalty_applied | immediate_reversal | -44.42 | -0.55 | -44.42 | — | none | 4 | Scanner Outage |
| ACEUSDT | long | 2026-08-09 05:28 | 2026-08-09 05:34 | 2026-08-14 09:57 | 124.4 | 0.128 | 0.1155 | 0.1425 | 0.155 | 0.1645 | 71 | B+ | — | 40.8 | — | risk_on | 25.0 | 15.0 | 10.0 | 11.0 | 10.0 | 0.0 | — | — | no_history,risk_penalty_applied | ran_to_tp3 | 39.81 | 39.81 | -0.99 | — | TP3 | 6 | Perfect Trade |
| BEATUSDT | long | 2026-08-09 05:08 | 2026-08-09 05:16 | 2026-08-10 05:12 | 23.9 | 2.875 | 2.63 | 3.02 | 3.18 | 3.4 | 62 | B | — | 35.4 | — | risk_on | 20.9 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | — | weak_structure,no_history,risk_penalty_applied | reached_tp1_then_stopped | -9.50 | 8.56 | -9.50 | — | TP1 | 10 | Scanner Outage |
| QQQUSDT | long | 2026-08-08 10:23 | 2026-08-08 10:30 | 2026-08-13 23:06 | 132.6 | 721.25 | 712.5 | 727 | 730 | — | 72 | B+ | — | 44.5 | — | risk_on | 24.5 | 8.0 | 7.0 | 11.0 | 10.0 | 0.0 | — | — | no_history | closed_at_tp2 | 1.67 | 1.67 | 0.07 | — | TP2 | 3 | Perfect Trade |
| PAXGUSDT | long | 2026-08-08 06:38 | 2026-08-08 06:45 | 2026-08-11 11:04 | 76.3 | 4329 | 4280 | 4350 | 4382 | — | 71 | B+ | — | 40.8 | — | risk_on | 25.0 | 11.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | — | weak_structure,no_history,high_atr_extension | closed_at_tp2 | 1.36 | 1.36 | 0.12 | — | TP2 | 3 | Perfect Trade |
| CRCLUSDT | long | 2026-08-08 06:38 | 2026-08-08 06:45 | 2026-08-11 13:46 | 79.0 | 66.4 | 64.5 | 68 | 69.5 | — | 54 | C | — | 45.4 | — | risk_on | 17.5 | 15.0 | 8.0 | 6.0 | 10.0 | 0.0 | — | — | weak_structure,no_history | closed_at_tp2 | 5.24 | 5.24 | 0.48 | — | TP2 | 71 | Perfect Trade |
| ACEUSDT | long | 2026-08-07 19:47 | 2026-08-07 19:53 | 2026-08-08 10:30 | 14.6 | 0.1145 | 0.1035 | 0.125 | 0.136 | 0.144 | 61 | B | — | 40.8 | — | risk_on | 25.0 | 15.0 | 10.0 | 11.0 | 0.0 | 0.0 | — | — | no_history,risk_penalty_applied,liquidity_stress,funding_elevated | immediate_reversal | -9.66 | -0.69 | -9.66 | — | none | 15 | Low Liquidity Failure |
| ZECUSDT | long | 2026-08-07 19:40 | 2026-08-07 19:47 | 2026-08-11 07:11 | 83.4 | 511.75 | 498 | 524 | 535 | — | 67 | B+ | — | 42.1 | — | risk_on | 21.1 | 8.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | — | weak_structure,no_history | immediate_reversal | -4.36 | 0.40 | -4.36 | — | none | 42 | Scanner Outage |
| CYSUSDT | long | 2026-08-07 14:34 | 2026-08-07 14:41 | 2026-08-07 16:37 | 1.9 | 0.8175 | 0.735 | 0.88 | 0.93 | — | None | — | — | 40.8 | — | risk_on | 25.0 | 8.0 | 5.0 | 11.0 | 10.0 | 0.0 | — | — | no_history,risk_penalty_applied | closed_at_tp2 | 19.67 | 19.67 | 0.48 | — | TP2 | 4 | Perfect Trade |
| SNDKUSDT | long | 2026-08-05 19:36 | 2026-08-05 19:42 | 2026-08-07 11:51 | 40.1 | 1387.5 | 1340 | 1430 | 1460 | — | None | — | — | 37.7 | — | risk_on | 14.3 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | — | weak_structure,no_history | immediate_reversal | -7.00 | 0.01 | -7.00 | — | none | 0 | Immediate Reversal |
| EWYUSDT | long | 2026-08-05 19:36 | 2026-08-05 19:42 | 2026-08-07 14:27 | 42.7 | 170.25 | 165.5 | 175 | 178.5 | — | None | — | — | 40.8 | — | risk_on | 14.8 | 15.0 | 10.0 | 6.0 | 10.0 | 0.0 | — | — | weak_structure,no_history | immediate_reversal | -3.65 | 0.15 | -3.65 | — | none | 0 | Immediate Reversal |
| DRAMUSDT | long | 2026-08-05 19:25 | 2026-08-05 19:31 | 2026-08-07 11:51 | 40.3 | 54.45 | 52.1 | 56.5 | 58 | — | None | — | — | 35.0 | — | risk_on | 12.8 | 15.0 | 10.0 | 11.0 | 10.0 | 0.0 | — | — | no_history | immediate_reversal | -5.31 | 0.39 | -5.31 | — | none | 0 | Immediate Reversal |
| NVDAUSDT | long | 2026-08-05 11:21 | 2026-08-05 11:25 | 2026-08-12 21:02 | 177.6 | 214.7 | 209.9 | 219.3 | 223.5 | — | None | — | — | 49.2 | — | mixed | 22.3 | 11.0 | 8.0 | 6.0 | 10.0 | 0.0 | — | — | weak_structure,no_history | closed_at_tp2 | 4.11 | 4.11 | 0.53 | — | TP2 | 67 | Perfect Trade |

**Verdict leaderboard**
| Verdict | n | % of all | Avg ret% | Sum ret% | Avg conf |
|---|---|---|---|---|---|
| Infrastructure Failure | 8 | 6.8% | -21.33 | -170.6 | 56.8 |
| Scanner Outage | 24 | 20.3% | -6.33 | -152.0 | 65.0 |
| Immediate Reversal | 32 | 27.1% | -3.14 | -100.4 | 63.2 |
| Low Liquidity Failure | 1 | 0.8% | -9.66 | -9.7 | 61.0 |
| Weak Structure Entry | 2 | 1.7% | -3.76 | -7.5 | 58.0 |
| TP1 Hit — Should Have Exited | 3 | 2.5% | -2.22 | -6.7 | 58.3 |
| Counter Trend Entry | 2 | 1.7% | -2.03 | -4.1 | 62.0 |
| Good Entry, Good Exit | 3 | 2.5% | 23.96 | 71.9 | 65.3 |
| Perfect Trade | 43 | 36.4% | 15.35 | 659.9 | 62.3 |

Note: 'Perfect Trade' (MAE >= -2%) is my threshold; 43 of 46 wins qualify, so the label separates almost nothing among wins, and 'Good Entry, Bad Exit' requires post-exit prices that do not exist (only what Trade-Truth can infer). The informative part of this leaderboard is the loss side.
Secondary tags among the 32 Immediate Reversals: weak structure (<9) 21, counter-BTC-trend 10, confidence ≥65 14, RSI<50 6, short 4. **Finding:** the dominant verdict is Immediate Reversal (CONFIRMED as the largest bucket); infrastructure verdicts (Infrastructure Failure + Scanner Outage) carry 71.5% of total loss magnitude.

## SECTION 2 — FEATURE IMPORTANCE (FISHER + ODDS RATIO + CI)

| Feature | n present/absent | Win% present / absent | OR | 95% CI | Fisher p | Evidence | Recommendation |
|---|---|---|---|---|---|---|---|
| Trend ≥ 22 | 43/75 | 37.2% / 40.0% | 0.89 | [0.41, 1.92] | 0.8455 | NOT SUPPORTED | Ignore (no detectable effect); keep as-is |
| Momentum = 15 (max) | 86/32 | 39.5% / 37.5% | 1.09 | [0.47, 2.51] | 1.0 | NOT SUPPORTED | Ignore (no detectable effect); keep as-is |
| Volume ≥ 8 | 66/52 | 43.9% / 32.7% | 1.61 | [0.76, 3.44] | 0.2559 | NOT SUPPORTED | Ignore (no detectable effect); keep as-is |
| Structure ≥ 9 | 45/73 | 42.2% / 37.0% | 1.25 | [0.58, 2.66] | 0.6978 | NOT SUPPORTED | Ignore (no detectable effect); keep as-is |
| Funding = 10 (uncrowded) | 113/5 | 38.9% / 40.0% | 0.96 | [0.15, 5.96] | 1.0 | INSUFFICIENT DATA | Needs more data |
| History present | 16/102 | 25.0% / 41.2% | 0.48 | [0.14, 1.58] | 0.2767 | NOT SUPPORTED | Ignore (no detectable effect); keep as-is |
| Regime = mixed | 84/34 | 44.0% / 26.5% | 2.19 | [0.91, 5.25] | 0.0964 | POSSIBLE | Needs more data |
| Entry quality = excellent | 19/82 | 52.6% / 36.6% | 1.93 | [0.7, 5.27] | 0.2067 | NOT SUPPORTED | Ignore (no detectable effect); keep as-is |
| Reliability (prior-trades) ≥ median | 59/59 | 33.9% / 44.1% | 0.65 | [0.31, 1.37] | 0.3454 | NOT SUPPORTED | Ignore (no detectable effect); keep as-is |
| EV (retro LOO) > 0 | 32/61 | 31.2% / 47.5% | 0.5 | [0.2, 1.23] | 0.1844 | NOT SUPPORTED | Ignore (no detectable effect); keep as-is |
| Fear&Greed ≥ median (greedier) | 65/53 | 35.4% / 43.4% | 0.71 | [0.34, 1.5] | 0.4488 | NOT SUPPORTED | Ignore (no detectable effect); keep as-is |
| ATR% ≥ median (volatile) | 42/42 | 38.1% / 45.2% | 0.74 | [0.31, 1.78] | 0.6584 | NOT SUPPORTED | Ignore (no detectable effect); keep as-is |
| Volatility percentile top tercile (ATR%) | 28/56 | 39.3% / 42.9% | 0.86 | [0.34, 2.18] | 0.8173 | NOT SUPPORTED | Ignore (no detectable effect); keep as-is |
| ADX ≥ 25 | 56/57 | 37.5% / 40.4% | 0.89 | [0.42, 1.89] | 0.8476 | NOT SUPPORTED | Ignore (no detectable effect); keep as-is |
| RSI 50–70 | 85/28 | 44.7% / 21.4% | 2.96 | [1.09, 8.05] | 0.0432 | LIKELY | Increase |
| CMF > 0 | 65/28 | 41.5% / 42.9% | 0.95 | [0.39, 2.32] | 1.0 | NOT SUPPORTED | Ignore (no detectable effect); keep as-is |
| MFI > 60 | 45/48 | 51.1% / 33.3% | 2.09 | [0.9, 4.83] | 0.096 | POSSIBLE | Needs more data |
| FVG used (post-capture) | 26/54 | 42.3% / 42.6% | 0.99 | [0.38, 2.55] | 1.0 | NOT SUPPORTED | Ignore (no detectable effect); keep as-is |
| EMA20/50/200 alignment | 88/23 | 39.8% / 30.4% | 1.51 | [0.56, 4.04] | 0.4758 | NOT SUPPORTED | Ignore (no detectable effect); keep as-is |
| Liquidity component < 0 (thin book) | 2/116 | 0.0% / 39.7% | 0.3 | [0.01, 6.46] | 0.5202 | INSUFFICIENT DATA | Needs more data |
| Long direction | 98/20 | 43.9% / 15.0% | 4.43 | [1.22, 16.1] | 0.022 | LIKELY | Increase |
| BTC trend agrees with direction | 50/43 | 32.0% / 53.5% | 0.41 | [0.18, 0.95] | 0.0572 | POSSIBLE | Needs more data |

Reading the 'Increase/Reduce' labels: they are mechanical outputs of the p<.05 rule, not advice. 'Long direction: Increase' just restates that longs beat shorts, which section 4 shows is largely a downtime artefact; 'RSI 50-70: Increase' means 'the 50-70 zone did better', which is a hypothesis to shadow-test (one of ~21 tests, so ~1 false positive is expected).
**Not stored, cannot be tested (INSUFFICIENT DATA):** OBV, BOS, CHoCH (per trade), market-cap bucket. Reliability here is computed only from trades that closed before entry (no look-ahead); EV is the pooled leave-one-out estimate. With ~21 features tested, expect ~1 false positive at p<.05 — treat 'Increase/Reduce' as hypotheses. Features with p<.05: ['RSI 50–70', 'Long direction'].

## SECTION 3 — SCORE CALIBRATION AUDIT AND MAPPING

| Bucket | n | Mean predicted % | Observed win% | Wilson (reliability) interval | Calibration error pp | TP1% | TP2% | TP3% | Stop% | Avg ret | PF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| <50 | 3 | 46.7 | 0.0% | 0–56.2 | 46.7 | 33.3 | 0.0 | 0.0 | 100.0 | -10.17 | 0.00 |
| 50–54 | 7 | 52.9 | 57.1% | 25.0–84.2 | -4.2 | 71.4 | 57.1 | 0.0 | 42.9 | 0.96 | 1.26 |
| 55–59 | 22 | 57.4 | 31.8% | 16.4–52.7 | 25.6 | 40.9 | 31.8 | 4.5 | 68.2 | 4.66 | 1.80 |
| 60–64 | 39 | 62.4 | 46.2% | 31.6–61.4 | 16.2 | 56.4 | 48.7 | 20.5 | 53.8 | 2.27 | 1.65 |
| 65–69 | 29 | 66.7 | 37.9% | 22.7–56.0 | 28.8 | 34.5 | 37.9 | 13.8 | 62.1 | 3.15 | 2.97 |
| 70–74 | 12 | 71.6 | 33.3% | 13.8–60.9 | 38.3 | 41.7 | 33.3 | 8.3 | 66.7 | 1.29 | 1.23 |
| 75+ | 1 | 76.0 | 0.0% | 0–79.3 | 76.0 | 0.0 | 0.0 | 0.0 | 100.0 | -1.07 | 0.00 |

Logistic calibration of win on confidence (standardised): slope per +1 SD (5.9 pts) = -0.024 (bootstrap 95% CI [-0.433, 0.338]), intercept implies base rate 38.9%. **The slope's CI includes zero.**
| Mapping (fit on first half chronologically, scored on second half, n_test=57) | Test Brier |
|---|---|
| Raw confidence/100 (current) | 0.3177 |
| Constant base rate from first half (44.6%) | 0.235 |
| Monotone (PAV) bucket map + shrinkage k=10 | 0.2604 |

**Proposed confidence display formula (NOT applied to scoring.py):** `display_p = clip( base_rate + slope × (confidence − mean_conf), 0.20, 0.60 )` with the constants fit on resolved trades — currently base_rate≈38.9%, mean_conf≈62.6, slope≈-0.0042 per point (95% CI spans zero: yes). Because the slope is statistically indistinguishable from zero, the evidence-supported version today is simply **display_p ≈ 39% ± 9 pp (Wilson) for every published trade**, with the raw confidence shown as an uncalibrated ranking score. Uses ≥200 trades to re-fit; a monotone bucket map (table above) is the fallback once buckets have n≥30.

## SECTION 4 — LONG VS SHORT FORENSICS

| Segment | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | MFE | MAE | Slip% | TP1% | TP2% | TP3% | Stop% | Avg struct | Avg vol | Avg RSI | Avg funding | Avg ATR% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Long | 98 | 43.9% | 34.5–53.7 | 4.57 | -1.11 | 2.60 | 7.939 | -3.018 | -1.52 | 49.0 | 43.9 | 14.3 | 56.1 | 7.8 | 8.1 | 58.5 | 9.6 | 3.63 |
| Short | 20 | 15.0% | 5.2–36.0 | -8.34 | -3.83 | 0.03 | 1.303 | -8.585 | -8.08 | 30.0 | 20.0 | 0.0 | 85.0 | 8.5 | 7.7 | 45.3 | 10.0 | 2.30 |
| Long, exit in uptime | 57 | 36.8% | 25.5–49.8 | 0.80 | -1.46 | 1.34 | 3.459 | -2.431 | -0.96 | 40.4 | 36.8 | 8.8 | 63.2 | 7.8 | 8.1 | 58.9 | 9.6 | 4.22 |
| Short, exit in uptime | 9 | 33.3% | 12.1–64.6 | -3.04 | -0.99 | 0.16 | 1.62 | -3.588 | -3.25 | 44.4 | 33.3 | 0.0 | 66.7 | 10.4 | 6.3 | 43.9 | 10.0 | 2.25 |
| Short, exit in gap | 11 | 0.0% | 0.0–25.9 | -12.67 | -8.06 | 0.00 | 1.043 | -12.673 | -10.28 | 18.2 | 9.1 | 0.0 | 100.0 | 6.9 | 8.7 | 46.5 | 10.0 | 2.34 |

| Distribution | Long | Short |
|---|---|---|
| Regime | {'risk_on': 34, 'mixed': 64} | {'mixed': 20} |
| Entry quality | {'none': 17, 'neutral': 52, 'excellent': 15, 'good': 14} | {'good': 6, 'neutral': 10, 'excellent': 4} |
| Timeframe | {'intraday': 41, 'swing': 57} | {'intraday': 14, 'swing': 6} |
| BTC-trend agrees with direction | ? | — |

| BTC-trend alignment | Long n / win% | Short n / win% |
|---|---|---|
| aligned | 45 / 33.3% | 5 / 20.0% |
| counter-BTC | 34 / 61.8% | 9 / 22.2% |

| Test | n short/long | Win% short / long | OR | p |
|---|---|---|---|---|
| All | 20/98 | 15.0% / 43.9% | 0.23 | 0.022 |
| Exit in uptime only | 9/57 | 33.3% / 36.8% | 0.86 | 1.0 |

**Why do shorts fail?** Causal attribution by candidate: **Scanner cadence/infrastructure — LIKELY dominant**: 11/20 shorts exited in a monitoring gap and 11/11 lost (avg -12.67%, worst slippage -27.24%); shorts that exited in uptime win 33.3% (n=9) vs longs 36.8% (p=1.0). **Trend / structure / entry timing / liquidity — NOT SUPPORTED as the cause:** average structure (8.5 vs 7.8), volume (7.7 vs 8.1) and funding are similar to longs and the entry-quality mix is similar; RSI is lower simply because shorts are bearish setups. **Volatility differs:** shorts sit on lower-ATR% assets (2.30% vs 3.63%) and are mostly intraday (14/20 vs 41/98), so stops are tight in % terms, which makes them more gap-sensitive (POSSIBLE contributor, untested). Note the asymmetry: a short's loss is uncapped upside, so gaps hurt shorts most, and all shorts are concentrated in a short calendar window (first short 2026-08-11 09:55, last 2026-09-14 15:50), i.e. one market episode. Regime: shorts exist only in `mixed`, so 'regime-dependent' is UNTESTABLE.
**Side finding (longs):** entering long *against* the BTC trend won 61.8% (n=34) vs 33.3% when aligned (n=45), OR 3.23, p=0.0219 -> LIKELY (contrarian/dip-buy entries did better; hypothesis only, no code implication yet).
**Short-specific decision policy (evidence-supported, no scoring change):** (1) Do NOT disable shorts (uptime-only shorts show no deficit, n small). (2) Keep the existing soft `SHORT_TIGHT_STOP`-style flag and label every short 'monitoring-sensitive'. (3) Require live heartbeat health at issuance/while open — if the scanner is not confirmed healthy the short's plan is shown as *unmonitored* (additive UI/analytics flag, not a trading rule). (4) Re-decide at ≥30 uptime-exited shorts; hard rules only if uptime-only shorts still underperform longs at p<.05. Evidence for a harder rule today: INSUFFICIENT DATA.

## SECTION 5 — ENTRY QUALITY V2

| EQ | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | Median hold h | TP1% | TP2% | TP3% | Stop% | Loss patterns |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| excellent | 19 | 52.6% | 31.7–72.7 | 5.43 | 2.93 | 3.30 | 114.6 | 57.9 | 52.6 | 26.3 | 47.4 | {'immediate_reversal': 8, 'reached_tp1_then_stopped': 1} |
| good | 20 | 30.0% | 14.5–51.9 | -0.48 | -2.15 | 0.85 | 10.2 | 40.0 | 35.0 | 10.0 | 70.0 | {'immediate_reversal': 9, 'some_favorable_move_then_stopped': 2, 'reached_tp1_then_stopped': 2, 'hit_tp2_then_reversed': 1} |
| neutral | 62 | 38.7% | 27.6–51.2 | 3.43 | -1.60 | 1.87 | 26.6 | 45.2 | 38.7 | 9.7 | 61.3 | {'immediate_reversal': 30, 'reached_tp1_then_stopped': 4, 'some_favorable_move_then_stopped': 4} |
| late | 0 |  |  |  |  |  |  |  |  |  |  |  |  |
| exhausted | 0 |  |  |  |  |  |  |  |  |  |  |  |  |


Scan-level entry_quality across all 81540 scans: {None: 6012, 'excellent': 2322, 'exhausted': 11099, 'good': 3326, 'invalid': 23433, 'late': 15921, 'neutral': 19427}. **Should thresholds move?** Excellent vs rest p=0.2067 → NOT SUPPORTED; no evidence supports moving thresholds, and 'good' does not beat 'neutral'.
**Candidate new categories** must be defined from *pre-entry* fields (defining them from the outcome would be circular). Exploratory candidates, tested with a chronological hold-out (first half = discovery, second half = confirmation):
| Candidate | 1st half n / win% | 2nd half n / win% | OR (all) | p | Evidence |
|---|---|---|---|---|---|
| trap: RSI 30–49 AND structure<9 | 5 / 0.0% | 9 / 22.2% | 0.23 | 0.0766 | POSSIBLE |
| trap: RSI<50 AND direction short | 8 / 12.5% | 10 / 20.0% | 0.27 | 0.0386 | LIKELY |
| recovery: price below EMA20 but above EMA50 (pullback in trend) | 2 / 0.0% | 2 / 0.0% | 0.16 | 0.1553 | INSUFFICIENT DATA |
| recovery: RSI 40–50 AND MACD hist > 0 | 4 / 0.0% | 13 / 30.8% | 0.43 | 0.1879 | NOT SUPPORTED |

Base win rate for reference: 1st half 42.4%, 2nd half 35.6%. **Verdict:** a candidate is only worth adding if it is bad/good in BOTH halves with adequate n; none is confirmed — Entry-Quality V2 categories are INSUFFICIENT DATA. The RSI 30-49 + weak-structure 'trap' was weak in both halves (0% then 22%) but with n=5 and 9, so it is POSSIBLE at best and belongs in warnings, not a new tier. The 'RSI<50 AND short' candidate reaches p=0.04 but is confounded with the outage-hit shorts (section 4) - do not treat it as an independent trap.

## SECTION 6 — FAILURE PATTERN ENGINE V2

| Cause (multi-label) | n losses | % of losses | Avg loss% | Avg conf | Entry quality mix | Most-affected coins |
|---|---|---|---|---|---|---|
| No historical analogue | 60 | 83.3% | -6.71 | 62.1 | {'none': 8, 'neutral': 34, 'good': 12, 'excellent': 6} | DRAMUSDT×3, DOGEUSDT×3, SPCXUSDT×3 |
| Immediate reversal | 57 | 79.2% | -5.78 | 63.4 | {'none': 10, 'neutral': 30, 'good': 9, 'excellent': 8} | ETHUSDT×5, DRAMUSDT×3, SOLUSDT×3 |
| Weak structure (<9) | 46 | 63.9% | -6.15 | 61.0 | {'none': 8, 'neutral': 38} | ETHUSDT×5, SNDKUSDT×2, ZECUSDT×2 |
| Scanner outage (exit in gap) | 30 | 41.7% | -9.45 | 63.2 | {'none': 5, 'neutral': 16, 'good': 5, 'excellent': 4} | ZECUSDT×2, ETHUSDT×2, DRAMUSDT×2 |
| Confidence ≥65 | 27 | 37.5% | -4.23 | 68.7 | {'none': 4, 'good': 8, 'excellent': 6, 'neutral': 9} | ETHUSDT×3, SOLUSDT×3, MSTRUSDT×3 |
| Counter-trend (BTC disagrees) | 20 | 27.8% | -5.54 | 63.2 | {'neutral': 10, 'good': 7, 'excellent': 3} | DOGEUSDT×2, BZUSDT×1, HOLOUSDT×1 |
| RSI chop 30–49 | 19 | 26.4% | -9.12 | 60.8 | {'neutral': 12, 'good': 4, 'excellent': 3} | ETHUSDT×2, DOGEUSDT×2, SUIUSDT×2 |
| Short direction | 17 | 23.6% | -10.11 | 59.7 | {'neutral': 10, 'good': 4, 'excellent': 3} | SNXXUSDT×2, DOGEUSDT×2, SKHYNIXUSDT×1 |
| Negative CMF | 16 | 22.2% | -9.79 | 58.5 | {'good': 3, 'neutral': 11, 'excellent': 2} | PUMPUSDT×2, HOLOUSDT×1, ETHUSDT×1 |
| Reached TP1 then stopped | 9 | 12.5% | -11.09 | 59.7 | {'none': 1, 'good': 3, 'neutral': 4, 'excellent': 1} | BEATUSDT×1, SOLUSDT×1, TRUMPUSDT×1 |
| Low liquidity (component<0) | 2 | 2.8% | -7.11 | 64.5 | {'none': 1, 'neutral': 1} | ACEUSDT×1, SAMSUNGUSDT×1 |
| Reached TP2 then reversed | 1 | 1.4% | -18.79 | 61.0 | {'good': 1} | WLDUSDT×1 |
| High ATR extension (>2.5 ATR from EMA20) | 1 | 1.4% | -44.42 | 71.0 | {'none': 1} | BICOUSDT×1 |
| Overbought MFI (>80) | 0 |  |  |  |  |  |

**News event: INSUFFICIENT DATA** (news_sentiment is stored but has no event flag; not evaluated). Frequencies overlap; ranking by frequency, the top causes are the same structural facts as before — no single stored feature explains losses beyond 'immediate reversal'.

## SECTION 7 — WINNER PATTERN ENGINE

| # | Combination (all must hold) | n | Win% | PF | Avg ret | PF ex-best |
|---|---|---|---|---|---|---|
| 1 | EQ excellent + regime mixed + RSI 50–70 | 11 | 72.7% | 17.59 | 11.15 | 12.27 |
| 2 | EQ excellent + regime mixed + long | 11 | 72.7% | 17.59 | 11.15 | 12.27 |
| 3 | EQ excellent + RSI 50–70 | 14 | 64.3% | 12.73 | 9.54 | 9.27 |
| 4 | EQ excellent + structure≥9 + RSI 50–70 | 14 | 64.3% | 12.73 | 9.54 | 9.27 |
| 5 | EQ excellent + RSI 50–70 + long | 14 | 64.3% | 12.73 | 9.54 | 9.27 |
| 6 | EQ excellent + long | 15 | 60.0% | 8.59 | 8.54 | 6.26 |
| 7 | EQ excellent + structure≥9 + long | 15 | 60.0% | 8.59 | 8.54 | 6.26 |
| 8 | volume≥8 + structure≥9 + regime mixed | 11 | 72.7% | 7.43 | 7.71 | 4.45 |
| 9 | structure≥9 + regime mixed + long | 21 | 57.1% | 6.37 | 7.32 | 5.00 |
| 10 | structure≥9 + regime mixed + CMF>0 | 15 | 53.3% | 5.90 | 6.59 | 3.95 |
| 11 | structure≥9 + regime mixed + RSI 50–70 | 21 | 57.1% | 5.52 | 7.11 | 4.33 |
| 12 | regime mixed + long + swing | 38 | 44.7% | 5.45 | 8.57 | 3.89 |
| 13 | regime mixed + RSI 50–70 + swing | 35 | 45.7% | 5.39 | 8.93 | 3.79 |
| 14 | volume≥8 + structure≥9 + CMF>0 | 12 | 58.3% | 5.36 | 6.22 | 3.06 |
| 15 | volume≥8 + regime mixed + long | 36 | 61.1% | 5.33 | 6.89 | 4.42 |
| 16 | volume≥8 + structure≥9 + RSI 50–70 | 14 | 57.1% | 5.11 | 7.88 | 3.62 |
| 17 | reliability≥median + regime mixed + swing | 16 | 31.2% | 5.01 | 8.53 | 1.65 |
| 18 | reliability≥median + structure≥9 + RSI 50–70 | 10 | 50.0% | 4.97 | 6.81 | 2.68 |
| 19 | EQ excellent + volume≥8 | 8 | 50.0% | 4.95 | 7.21 | 2.25 |
| 20 | EQ excellent + volume≥8 + structure≥9 | 8 | 50.0% | 4.95 | 7.21 | 2.25 |
| 21 | EQ excellent + volume≥8 + long | 8 | 50.0% | 4.95 | 7.21 | 2.25 |
| 22 | regime mixed + long | 64 | 53.1% | 4.87 | 7.79 | 3.98 |
| 23 | regime mixed + RSI 50–70 + long | 57 | 54.4% | 4.83 | 8.01 | 3.87 |
| 24 | volume≥8 + reliability≥median + regime mixed | 16 | 56.2% | 4.71 | 6.61 | 3.33 |
| 25 | regime mixed + long + CMF>0 | 44 | 52.3% | 4.66 | 6.29 | 3.97 |

**Multiple-comparison check:** 240 eligible combinations (n≥8). The best observed PF is 17.59; in 200 outcome-shuffles the best-of-240 PF was ≥ that in 21.5% of shuffles (permutation p≈0.219; median null-best PF 10.68). **Verdict:** the leaderboard is NOT distinguishable from data-mined noise — do not treat any combination as a rule (evidence: NOT SUPPORTED). Note the requested 'Trend + X' combinations are all included among the 1–3-way sets.

## SECTION 8 — TP CONTINUATION MODEL

**By overall**
| overall | n(TP1) | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(back to entry) | P(back to stop) | P(final loss) |
|---|---|---|---|---|---|---|
| all | 54 | 85.2% (73.4–92.3) | 30.4% (n=46) | 17.9% (n=39) | 17.0% (n=53) | 16.7% |

**By confidence**
| confidence | n(TP1) | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(back to entry) | P(back to stop) | P(final loss) |
|---|---|---|---|---|---|---|
| 60–64 | 22 | 86.4% (66.7–95.3) | 42.1% (n=19) | 10.5% (n=19) | 18.2% (n=22) | 18.2% |
| 65+ | 15 | 93.3% (70.2–98.8) | 35.7% (n=14) | 20.0% (n=5) | 6.7% (n=15) | 6.7% |
| <60 | 15 | 73.3% (48.0–89.1) | 9.1% (n=11) | 28.6% (n=14) | 26.7% (n=15) | 26.7% |

**By entry quality**
| entry quality | n(TP1) | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(back to entry) | P(back to stop) | P(final loss) |
|---|---|---|---|---|---|---|
| excellent | 11 | 90.9% (62.3–98.4) | 50.0% (n=10) | 0.0% (n=5) | 9.1% (n=11) | 9.1% |
| good | 8 | 75.0% (40.9–92.9) | 33.3% (n=6) | 25.0% (n=8) | 37.5% (n=8) | 37.5% |
| neutral | 28 | 85.7% (68.5–94.3) | 25.0% (n=24) | 21.7% (n=23) | 14.3% (n=28) | 14.3% |

**By trend score**
| trend score | n(TP1) | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(back to entry) | P(back to stop) | P(final loss) |
|---|---|---|---|---|---|---|
| <22 | 35 | 85.7% (70.6–93.7) | 33.3% (n=30) | 11.1% (n=27) | 17.1% (n=35) | 17.1% |
| ≥22 | 19 | 84.2% (62.4–94.5) | 25.0% (n=16) | 33.3% (n=12) | 16.7% (n=18) | 15.8% |

**By structure**
| structure | n(TP1) | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(back to entry) | P(back to stop) | P(final loss) |
|---|---|---|---|---|---|---|
| <9 | 32 | 84.4% (68.2–93.1) | 22.2% (n=27) | 19.2% (n=26) | 15.6% (n=32) | 15.6% |
| ≥9 | 22 | 86.4% (66.7–95.3) | 42.1% (n=19) | 15.4% (n=13) | 19.0% (n=21) | 18.2% |

**By regime**
| regime | n(TP1) | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(back to entry) | P(back to stop) | P(final loss) |
|---|---|---|---|---|---|---|
| mixed | 43 | 86.0% (72.7–93.4) | 32.4% (n=37) | 17.6% (n=34) | 16.3% (n=43) | 16.3% |
| risk_on | 11 | 81.8% (52.3–94.9) | 22.2% (n=9) | 20.0% (n=5) | 20.0% (n=10) | 18.2% |

**By volatility (ATR% tercile)**
| volatility (ATR% tercile) | n(TP1) | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(back to entry) | P(back to stop) | P(final loss) |
|---|---|---|---|---|---|---|
| high | 14 | 78.6% (52.4–92.4) | 36.4% (n=11) | 23.1% (n=13) | 28.6% (n=14) | 28.6% |
| low | 12 | 91.7% (64.6–98.5) | 36.4% (n=11) | 14.3% (n=7) | 8.3% (n=12) | 8.3% |
| mid | 16 | 81.2% (57.0–93.4) | 15.4% (n=13) | 25.0% (n=12) | 18.8% (n=16) | 18.8% |

**By direction**
| direction | n(TP1) | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(back to entry) | P(back to stop) | P(final loss) |
|---|---|---|---|---|---|---|
| long | 48 | 89.6% (77.8–95.5) | 32.6% (n=43) | 15.2% (n=33) | 10.6% (n=47) | 10.4% |
| short | 6 | 50.0% (18.8–81.2) | 0.0% (n=3) | 33.3% (n=6) | 66.7% (n=6) | 66.7% |

**Rules (derived from the arithmetic in §9 and the tables above, all requiring caution because n(TP1)=54):** **Exit at TP1:** NOT supported — exiting everything at TP1 lowers summed return massively (§9). **Hold to TP2:** supported as the default (P(TP2|TP1) is high in every slice with n≥10). **Trail stop:** possible (POSSIBLE; see §9 path simulation). **Move stop to entry:** inconclusive. **Partial exit:** untestable with recorded single-exit outcomes (INSUFFICIENT DATA). No slice shows a difference large enough to justify conditional rules (confidence/EQ/trend/structure/regime tables overlap within Wilson intervals).

## SECTION 9 — DYNAMIC STOP LOSS ANALYSIS (PATH BACKTEST)

Method: for every closed trade with ≥4 snapshots between entry and exit (covered n=111 of 118), replay the recorded price path under each alternative stop rule; if the rule triggers before the actual exit, the trade exits at the rule's level, else the actual result stands. Limits: snapshot path only (5-min cadence during uptime, **no intra-bar wicks, hours-long holes during outages**), exits at the stop level (no extra slippage), fees ignored. A stop **wider than the original** cannot be replayed to a conclusion (the trade record ends at the original stop) so those are reported as *survivors with unknown outcome*. Gap-free subset (trade lifetime entirely within uptime): n=30.
**All covered trades**
| Style | n simulated | Sum ret% | Avg | PF | Median | Win% | Trades changed | Baseline sum on same trades |
|---|---|---|---|---|---|---|---|---|
| Baseline (actual) | 111 | 307.2 | 2.77 | 1.73 | -1.55 | 39.6% | 0 | 307.2 |
| ATR stop 1.0× | 82 | 368.4 | 4.49 | 2.58 | -1.01 | 41.5% | 15 | 296.4 |
| ATR stop 1.5× | 82 | 320.5 | 3.91 | 2.14 | -1.04 | 41.5% | 5 | 296.4 |
| ATR stop 2.0× | 82 | 298.2 | 3.64 | 1.98 | -1.04 | 41.5% | 1 | 296.4 |
| EMA20 stop | 88 | 358.2 | 4.07 | 2.82 | -0.73 | 39.8% | 30 | 340.4 |
| Swing (nearest support/resistance) stop | 71 | 331.0 | 4.66 | 2.70 | -1.01 | 40.8% | 13 | 259.1 |
| Break-even after TP1 | 111 | 378.4 | 3.41 | 2.14 | -1.01 | 38.7% | 9 | 307.2 |
| Trail 50% of MFE after TP1 | 111 | 356.2 | 3.21 | 2.07 | -1.01 | 46.8% | 13 | 307.2 |
| Trail 1×ATR after TP1 | 82 | 377.0 | 4.60 | 2.72 | -0.47 | 48.8% | 8 | 296.4 |
| Break-even after TP1 + Trail 50% | 111 | 356.2 | 3.21 | 2.07 | -1.01 | 46.8% | 13 | 307.2 |

**Gap-free subset (most trustworthy paths)**
| Style | n simulated | Sum ret% | Avg | PF | Median | Win% | Trades changed | Baseline sum on same trades |
|---|---|---|---|---|---|---|---|---|
| Baseline (actual) | 30 | -7.2 | -0.24 | 0.90 | -1.30 | 30.0% | 0 | -7.2 |
| ATR stop 1.0× | 28 | 0.9 | 0.03 | 1.01 | -1.11 | 32.1% | 3 | -2.9 |
| ATR stop 1.5× | 28 | -1.1 | -0.04 | 0.98 | -1.11 | 32.1% | 2 | -2.9 |
| ATR stop 2.0× | 28 | -2.9 | -0.10 | 0.96 | -1.11 | 32.1% | 0 | -2.9 |
| EMA20 stop | 22 | 27.6 | 1.25 | 1.76 | -0.38 | 40.9% | 7 | 10.5 |
| Swing (nearest support/resistance) stop | 23 | -8.8 | -0.38 | 0.85 | -1.31 | 34.8% | 4 | -12.8 |
| Break-even after TP1 | 30 | -7.2 | -0.24 | 0.90 | -1.30 | 30.0% | 0 | -7.2 |
| Trail 50% of MFE after TP1 | 30 | -7.2 | -0.24 | 0.90 | -1.30 | 30.0% | 0 | -7.2 |
| Trail 1×ATR after TP1 | 28 | -2.9 | -0.10 | 0.96 | -1.11 | 32.1% | 0 | -2.9 |
| Break-even after TP1 + Trail 50% | 30 | -7.2 | -0.24 | 0.90 | -1.30 | 30.0% | 0 | -7.2 |

**Wider-stop survivors (loss trades that a wider stop would not have stopped at the original level; outcome after that point is unrecorded):** {'EMA20': 16, 'ATR 1.5×': 43, 'ATR 2×': 47, 'Swing': 29} out of 67 covered losses. **INSUFFICIENT DATA** to say whether widening would have been better or worse.
**Where does each policy's gain come from?** Delta = simulated - actual, summed over covered trades, split by whether the *actual* exit was inside a monitoring gap. A gain in the 'gap-exit' column is mostly an idealised-fill effect (a resting exchange stop would have filled at the stop level while the scanner was down) and is an **execution** benefit, not a better stop *style*.
| Policy | Delta total pp | Delta from gap-exit trades | Delta from uptime-exit trades | Winners cut | Losers rescued |
|---|---|---|---|---|---|
| ATR stop 1.0× | 71.9 | 49.0 | 22.9 | 0 | 15 |
| ATR stop 1.5× | 24.0 | 22.3 | 1.8 | 0 | 5 |
| ATR stop 2.0× | 1.7 | 1.7 | 0.0 | 0 | 1 |
| EMA20 stop | 17.8 | -29.8 | 47.5 | 3 | 27 |
| Swing (nearest support/resistance) stop | 71.9 | 56.7 | 15.2 | 1 | 12 |
| Break-even after TP1 | 71.2 | 41.3 | 30.0 | 1 | 8 |
| Trail 50% of MFE after TP1 | 49.1 | 17.7 | 31.3 | 5 | 8 |
| Trail 1×ATR after TP1 | 80.5 | 52.5 | 28.0 | 1 | 7 |
| Break-even after TP1 + Trail 50% | 49.1 | 17.7 | 31.3 | 5 | 8 |

**Reading the table:** uptime-exit gains range from 0.0 to 47.5 pp across styles (vs a covered baseline of 307.2 pp), and gap-exit gains from -29.8 to 56.7 pp. 'Winners cut' is a LOWER BOUND: the replay uses discrete snapshots, so wicks between snapshots that would have stopped a winner are invisible, which flatters tight stops. Every number is in-sample on the same trades that suggested the rule.
**Answers:** Would ATR/EMA20/swing stops survive? see 'Trades changed' — tighter stops knock out trades that later won, wider ones are untestable. Trailing improves PF? and break-even after TP1 improves PF? — compare each row's PF/Sum to the baseline on the same trades. These are in-sample replays on paths with holes; **no style is CONFIRMED superior**: the gap-exit column shows how much of each headline gain is just replacing gap slippage with an idealised fill (execution, fixable by a resting exchange stop or continuous monitoring), and on the gap-free subset (see its n above) the differences are tiny. Any style with a positive uptime-only Delta is worth shadow-logging; that is POSSIBLE, not proven. The actual system's stop is Claude-chosen free text (no formula).

## SECTION 10 — EXPECTED VALUE ENGINE VALIDATION

| EV series | Correlated with | n | Spearman | p | Evidence |
|---|---|---|---|---|---|
| Stored EV (post-2026-09-12) | realized return | 28 | -0.068 | 0.732 | NOT SUPPORTED |
| Stored EV (post-2026-09-12) | realized R | 28 | -0.003 | 0.989 | NOT SUPPORTED |
| Stored EV (post-2026-09-12) | TP2 reached (0/1) | 28 | -0.279 | 0.15 | NOT SUPPORTED |
| Stored EV (post-2026-09-12) | Stop hit (0/1) | 28 | 0.197 | 0.316 | NOT SUPPORTED |
| Retro leave-one-out EV (all) | realized return | 93 | -0.137 | 0.19 | NOT SUPPORTED |
| Retro leave-one-out EV (all) | realized R | 93 | -0.103 | 0.327 | NOT SUPPORTED |
| Retro leave-one-out EV (all) | TP2 reached (0/1) | 93 | -0.248 | 0.017 | LIKELY |
| Retro leave-one-out EV (all) | Stop hit (0/1) | 93 | 0.235 | 0.024 | LIKELY |

**Stored-EV buckets**
| Bucket | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | TP2% | Stop% |
|---|---|---|---|---|---|---|---|---|
| EV<0 | 14 | 57.1% | 32.6–78.6 | 10.88 | 3.07 | 4.14 | 64.3% | 42.9% |
| 0–0.5R | 9 | 33.3% | 12.1–64.6 | 7.70 | -1.46 | 2.79 | 33.3% | 66.7% |
| 0.5–1R | 4 | 0.0% | 0–49.0 | -2.44 | -2.21 | 0.00 | 0.0% | 100.0% |
| ≥1R | 1 | 100.0% | 20.7–100 | 2.93 | 2.93 | — | 100.0% | 0.0% |

**Retro-EV buckets**
| Bucket | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | TP2% | Stop% |
|---|---|---|---|---|---|---|---|---|
| EV<0 | 61 | 47.5% | 35.5–59.8 | 4.61 | -1.01 | 2.20 | 49.2% | 52.5% |
| 0–0.5R | 25 | 32.0% | 17.2–51.6 | 2.03 | -1.55 | 1.66 | 32.0% | 68.0% |
| 0.5–1R | 4 | 25.0% | 4.6–69.9 | -2.02 | -4.50 | 0.47 | 25.0% | 75.0% |
| ≥1R | 3 | 33.3% | 6.1–79.2 | -0.32 | -0.95 | 0.75 | 33.3% | 66.7% |

| Threshold | n kept | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF |
|---|---|---|---|---|---|---|
| retro EV ≥ -0.5R | 93 | 41.9% | 32.4–52.1 | 3.47 | -1.07 | 1.98 |
| retro EV ≥ -0.25R | 71 | 32.4% | 22.7–43.9 | 0.99 | -1.57 | 1.27 |
| retro EV ≥ 0R | 32 | 31.2% | 18.0–48.6 | 1.30 | -1.56 | 1.44 |
| retro EV ≥ 0.25R | 14 | 28.6% | 11.7–54.6 | -0.25 | -1.64 | 0.90 |
| retro EV ≥ 0.5R | 7 | 28.6% | 8.2–64.1 | -1.29 | -2.93 | 0.53 |

**EV is anti-predictive of TP2/stop, not merely uncorrelated:** retro-EV vs TP2 rho=-0.25 (p=0.017) and vs stop rho=+0.24 (p=0.024): higher EV means *fewer* TP2s and *more* stop-outs (LIKELY, n=93; clustered p is optimistic). Mechanism: EV = P(TP1)*reward/risk - P(stop); P(TP1) is pooled, so EV mostly measures reward/risk, which is largest when the stop is tight. Check: Spearman(EV, stop distance in ATR) = -0.47 (p=0.0, n=84); vs stop distance % = -0.34 (p=0.001). **EV as currently defined should not be used to rank or size trades.**
**Recommended EV thresholds: none.** No correlation with return or realized R reaches p<.05; TP2/stop correlations are significant but in the WRONG direction; and PF falls as the retro-EV threshold rises -> the EV engine is NOT validated as a selector (evidence that it is counter-productive: LIKELY); keep as displayed metadata. Stored-EV n=28 is too small (INSUFFICIENT DATA).

## SECTION 11 — RELIABILITY ENGINE VALIDATION

**Threshold derivation (statistical, not arbitrary):** for each symbol the posterior of its true win rate is Beta(1+wins, 1+losses) (uniform prior). Tier = the *posterior probability* that the symbol's win rate is below/above the pooled rate (38.9%): **Trusted** if P(above pooled) ≥ 0.90; **Caution** if P(below pooled) ≥ 0.80; **Avoid** if P(below pooled) ≥ 0.95; otherwise **Watch**. The 0.80/0.90/0.95 posterior levels are the usual decision-theory conventions (unavoidable, but they are on probability, not on raw counts), and they automatically demand more trades for stronger labels.
| Symbol | n | Raw win% | Bayesian win% (k=10) | 95% credible interval | Avg ret | PF | P(above pooled) | Tier |
|---|---|---|---|---|---|---|---|---|
| ETHUSDT | 5 | 0.0% | 26.0% | 0–46 | -6.50 | 0.00 | 0.05 | Caution |
| SOLUSDT | 5 | 20.0% | 32.6% | 4–64 | 1.80 | 1.75 | 0.25 | Watch |
| CLUSDT | 4 | 50.0% | 42.1% | 15–85 | 2.38 | 2.58 | 0.70 | Watch |
| DRAMUSDT | 4 | 25.0% | 35.0% | 5–72 | -2.53 | 0.22 | 0.36 | Watch |
| HYPEUSDT | 4 | 50.0% | 42.1% | 15–85 | 10.02 | 10.56 | 0.70 | Watch |
| SKHYUSDT | 4 | 50.0% | 42.1% | 15–85 | 2.46 | 3.19 | 0.70 | Watch |
| SPCXUSDT | 4 | 25.0% | 35.0% | 5–72 | -0.07 | 0.94 | 0.36 | Watch |
| ZECUSDT | 4 | 50.0% | 42.1% | 15–85 | 12.34 | 2.49 | 0.70 | Watch |
| BNBUSDT | 3 | 33.3% | 37.6% | 7–81 | 1.61 | 3.25 | 0.49 | Watch |
| CRCLUSDT | 3 | 66.7% | 45.3% | 19–93 | 3.32 | 11.03 | 0.83 | Watch |
| DOGEUSDT | 3 | 0.0% | 30.0% | 1–60 | -12.88 | 0.00 | 0.14 | Caution |
| LINKUSDT | 3 | 66.7% | 45.3% | 19–93 | 9.29 | 6.08 | 0.83 | Watch |
| MSTRUSDT | 3 | 0.0% | 30.0% | 1–60 | -3.39 | 0.00 | 0.14 | Caution |
| PUMPUSDT | 3 | 33.3% | 37.6% | 7–81 | 4.64 | 1.55 | 0.49 | Watch |
| SAMSUNGUSDT | 3 | 66.7% | 45.3% | 19–93 | 2.43 | 2.60 | 0.83 | Watch |
| SKHYNIXUSDT | 3 | 33.3% | 37.6% | 7–81 | -0.07 | 0.97 | 0.49 | Watch |
| SNDKUSDT | 3 | 33.3% | 37.6% | 7–81 | -1.68 | 0.55 | 0.49 | Watch |
| XAGUSDT | 3 | 33.3% | 37.6% | 7–81 | -0.81 | 0.55 | 0.49 | Watch |
| 1000PEPEUSDT | 2 | 50.0% | 40.8% | 9–91 | 12.47 | 4.34 | 0.66 | Watch |
| ACEUSDT | 2 | 50.0% | 40.8% | 9–91 | 15.08 | 4.12 | 0.66 | Watch |
| BTWUSDT | 2 | 100.0% | 49.1% | 29–99 | 17.25 | — | 0.94 | Trusted |
| BZUSDT | 2 | 0.0% | 32.4% | 1–71 | -3.35 | 0.00 | 0.23 | Watch |
| CYSUSDT | 2 | 50.0% | 40.8% | 9–91 | 6.79 | 3.23 | 0.66 | Watch |
| EWYUSDT | 2 | 50.0% | 40.8% | 9–91 | -0.51 | 0.72 | 0.66 | Watch |
| MOVRUSDT | 2 | 0.0% | 32.4% | 1–71 | -9.47 | 0.00 | 0.23 | Watch |
| MUUSDT | 2 | 50.0% | 40.8% | 9–91 | -1.61 | 0.44 | 0.66 | Watch |
| NEARUSDT | 2 | 100.0% | 49.1% | 29–99 | 63.82 | — | 0.94 | Trusted |
| NVDAUSDT | 2 | 100.0% | 49.1% | 29–99 | 2.85 | — | 0.94 | Trusted |
| PAXGUSDT | 2 | 50.0% | 40.8% | 9–91 | 0.38 | 2.29 | 0.66 | Watch |
| SNXXUSDT | 2 | 0.0% | 32.4% | 1–71 | -6.80 | 0.00 | 0.23 | Watch |
| SOXSUSDT | 2 | 100.0% | 49.1% | 29–99 | 4.11 | — | 0.94 | Trusted |
| SUIUSDT | 2 | 0.0% | 32.4% | 1–71 | -3.46 | 0.00 | 0.23 | Watch |
| WLDUSDT | 2 | 50.0% | 40.8% | 9–91 | -5.25 | 0.44 | 0.66 | Watch |
| XAUUSDT | 2 | 50.0% | 40.8% | 9–91 | 0.48 | 2.64 | 0.66 | Watch |
| ADAUSDT | 1 | 100.0% | 44.5% | 16–99 | 4.95 | — | 0.85 | Watch |
| ALLOUSDT | 1 | 0.0% | 35.4% | 1–84 | -2.76 | 0.00 | 0.37 | Watch |
| APRUSDT | 1 | 100.0% | 44.5% | 16–99 | 19.04 | — | 0.85 | Watch |
| BEATUSDT | 1 | 0.0% | 35.4% | 1–84 | -9.50 | 0.00 | 0.37 | Watch |
| BICOUSDT | 1 | 0.0% | 35.4% | 1–84 | -44.42 | 0.00 | 0.37 | Watch |
| BTCUSDT | 1 | 0.0% | 35.4% | 1–84 | -1.61 | 0.00 | 0.37 | Watch |
| ENAUSDT | 1 | 0.0% | 35.4% | 1–84 | -4.10 | 0.00 | 0.37 | Watch |
| FILUSDT | 1 | 100.0% | 44.5% | 16–99 | 14.90 | — | 0.85 | Watch |
| FLOCKUSDT | 1 | 0.0% | 35.4% | 1–84 | -5.38 | 0.00 | 0.37 | Watch |
| HEMIUSDT | 1 | 0.0% | 35.4% | 1–84 | -8.62 | 0.00 | 0.37 | Watch |
| HOLOUSDT | 1 | 0.0% | 35.4% | 1–84 | -7.17 | 0.00 | 0.37 | Watch |
| LABUSDT | 1 | 0.0% | 35.4% | 1–84 | -7.36 | 0.00 | 0.37 | Watch |
| LITEUSDT | 1 | 0.0% | 35.4% | 1–84 | -5.12 | 0.00 | 0.37 | Watch |
| QQQUSDT | 1 | 100.0% | 44.5% | 16–99 | 1.67 | — | 0.85 | Watch |
| RIVERUSDT | 1 | 100.0% | 44.5% | 16–99 | 18.82 | — | 0.85 | Watch |
| RKLBUSDT | 1 | 0.0% | 35.4% | 1–84 | -2.66 | 0.00 | 0.37 | Watch |
| SPORTFUNUSDT | 1 | 0.0% | 35.4% | 1–84 | -6.12 | 0.00 | 0.37 | Watch |
| TRUMPUSDT | 1 | 0.0% | 35.4% | 1–84 | -20.95 | 0.00 | 0.37 | Watch |
| UNIUSDT | 1 | 100.0% | 44.5% | 16–99 | 52.19 | — | 0.85 | Watch |
| USELESSUSDT | 1 | 0.0% | 35.4% | 1–84 | -4.71 | 0.00 | 0.37 | Watch |
| VELVETUSDT | 1 | 100.0% | 44.5% | 16–99 | 27.28 | — | 0.85 | Watch |
| XRPUSDT | 1 | 100.0% | 44.5% | 16–99 | 4.61 | — | 0.85 | Watch |

Tier counts: {'Watch': 49, 'Caution': 3, 'Trusted': 4}; symbols with n≥5: 2 of 56. **Validation:** because per-symbol n is 1–4 for almost all coins, the derived thresholds can fire only for the few multi-trade symbols; the engine is a *shrinkage display* and is NOT validated as predictive (a within-sample rank correlation is hindsight-inflated; the look-ahead-safe version has Spearman p=0.17 vs return, see §2: NOT SUPPORTED).

## SECTION 12 — COIN PERSONALITY REPORT

Classification uses only what is stored (hold time, MFE/MAE, TP progression, immediate-reversal share). **Mean Reverter, News Driven, Low Liquidity, Volatile Breakout as distinct types cannot be identified from these fields** (no return-autocorrelation series, no event flags, no order-book depth) → INSUFFICIENT DATA; symbols with n<4 are not classified at all. Timeframe/strategy recommendations require ≥8 trades per timeframe per symbol — none qualifies.
| Symbol (n≥4) | n | Win% | TP3% | Immediate-reversal share | Avg MFE | Avg MAE | Median hold h | Heuristic class | Best timeframe/strategy |
|---|---|---|---|---|---|---|---|---|---|
| ETHUSDT | 5 | 0.0% | 0.0 | 100% | 0.146 | -6.505 | 6.703 | Fakeout Coin | INSUFFICIENT DATA (n per timeframe <8) |
| SOLUSDT | 5 | 20.0% | 0.0 | 60% | 4.959 | -2.349 | 124.817 | Fakeout Coin | INSUFFICIENT DATA (n per timeframe <8) |
| DRAMUSDT | 4 | 25.0% | 0.0 | 75% | 1.175 | -3.319 | 26.943 | Fakeout Coin | INSUFFICIENT DATA (n per timeframe <8) |
| ZECUSDT | 4 | 50.0% | 25.0 | 50% | 20.922 | -8.563 | 157.257 | Trend Runner | INSUFFICIENT DATA (n per timeframe <8) |
| HYPEUSDT | 4 | 50.0% | 25.0 | 50% | 11.152 | -1.05 | 66.919 | Trend Runner | INSUFFICIENT DATA (n per timeframe <8) |
| SKHYUSDT | 4 | 50.0% | 25.0 | 25% | 4.187 | -0.901 | 12.472 | Trend Runner | INSUFFICIENT DATA (n per timeframe <8) |
| CLUSDT | 4 | 50.0% | 25.0 | 25% | 5.021 | -1.548 | 114.831 | Trend Runner | INSUFFICIENT DATA (n per timeframe <8) |
| SPCXUSDT | 4 | 25.0% | 25.0 | 75% | 1.451 | -1.542 | 92.128 | Trend Runner | INSUFFICIENT DATA (n per timeframe <8) |

Only 8 of 56 symbols have n≥4. The classes above are descriptive labels, not validated personalities (a coin-personality model was previously rejected as unsupportable at this n, and the data still agrees).

## SECTION 13 — MARKET REGIME INTELLIGENCE (CLUSTERING)

K-means on standardised scan score-breakdown vectors (81540 scans, 15k sample; k chosen by silhouette among 3–6 → k=6, silhouette=0.195). **A silhouette below ~0.25 means clusters are weakly separated — these are descriptive groupings of scan states, NOT validated market regimes.**
| Cluster | Scan-sample size | Signature (top deviations) | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF |
|---|---|---|---|---|---|---|---|---|
| 0 | 664 | liquidity ↓4.1σ, funding ↓3.3σ, trend ↑0.8σ | 1 | 0.0% | 0–79.3 | -9.66 | -9.66 | 0.00 |
| 1 | 2790 | structure ↑1.7σ, funding ↑0.3σ, regime ↓0.3σ | 31 | 48.4% | 32.0–65.2 | 3.32 | -0.99 | 2.22 |
| 2 | 1889 | regime ↑2.2σ, funding ↑0.3σ, risk ↑0.2σ | 33 | 27.3% | 15.1–44.2 | -1.25 | -2.98 | 0.71 |
| 3 | 4003 | volume ↓0.9σ, structure ↓0.6σ, momentum ↓0.6σ | 2 | 50.0% | 9.5–90.5 | 46.67 | 46.67 | 5.46 |
| 4 | 4669 | volume ↑0.7σ, structure ↓0.6σ, momentum ↑0.5σ | 50 | 42.0% | 29.4–55.8 | 2.80 | -1.23 | 1.74 |
| 5 | 985 | risk ↓1.9σ, funding ↓1.7σ, trend ↑1.1σ | 1 | 0.0% | 0–79.3 | -4.68 | -4.68 | 0.00 |

Outcome differs across clusters? chi-square p=0.463 (dof=5). Result: NOT SUPPORTED.
Named regimes you listed (Trend Expansion, Exhaustion, Panic Volatility, Mean Reversion, Distribution, Accumulation) cannot be *discovered* here: the clustering uses the score components only (no price-path, volatility or volume-profile features in ScanSnapshot). Existing labels: risk_on / mixed only. **INSUFFICIENT DATA** to add regimes.

## SECTION 14 — MISSED OPPORTUNITY ANALYSIS

| Rejection reason | Scan rows | % |
|---|---|---|
| published/active | 67402 | 82.7 |
| no_trade (direction gate) | 5962 | 7.3 |
| rank cutoff | 4551 | 5.6 |
| exhausted | 3086 | 3.8 |
| late | 539 | 0.7 |

| Category (directional rows) | Directional scans | +1h | +4h | +24h | +72h |
|---|---|---|---|---|---|
| no_trade (direction gate) | 0 | n=0 (INSUFFICIENT) | n=0 (INSUFFICIENT) | n=0 (INSUFFICIENT) | n=0 (INSUFFICIENT) |
| rank cutoff | 4551 | n=13, avg 0.53%, fav 69% | n=11, avg -0.08%, fav 36% | n=4 (INSUFFICIENT) | n=2 (INSUFFICIENT) |
| exhausted | 0 | n=0 (INSUFFICIENT) | n=0 (INSUFFICIENT) | n=0 (INSUFFICIENT) | n=0 (INSUFFICIENT) |
| late | 539 | n=3 (INSUFFICIENT) | n=2 (INSUFFICIENT) | n=2 (INSUFFICIENT) | n=0 (INSUFFICIENT) |

Avoid-grade plans: 48 with price levels but **0 PredictionSnapshots** (never tracked) → whether they later hit TP1/TP2/TP3 is unknowable. Rejected scans carry no TP levels at all. `rejected_opportunity_outcomes` has 0 rows. **'Would Have Won' and 'False Reject' leaderboards: INSUFFICIENT DATA — cannot be produced without inventing outcomes.** Which rules are too strict: no evidence (the two rules with data are `late` and `exhausted`, which by design have no realised-outcome record). What to build: wire the existing recorder (needs approval to touch the scanner) — planned in §23.

## SECTION 15 — INVALIDATED TRADE ANALYSIS

Invalidated: n=774 (691 had entered). The system does not store an invalidation reason; the invalidation rule is supersession by a newer plan on the same symbol. The final-snapshot text (top 6, which is the trade's status message, not a cause): {'Position open, TP1 not yet reached. No target-probability model active yet (Phase 2 not bu': 339, 'Waiting for price to enter the proposed zone.': 71, 'Position open, TP1 not yet reached. Historical P(TP1) for this setup is 60.7% (n=28) — not': 45, 'Position open, TP1 not yet reached. Historical P(TP1) for this setup is 60.0% (n=15) — not': 25, 'Position open, TP1 not yet reached. Historical P(TP1) for this setup is 64.0% (n=25) — not': 23, 'Position open, TP1 not yet reached. Historical P(TP1) for this setup is 0.0% (n=8) — not y': 20}.
| Metric | Value |
|---|---|
| Invalidated & entered: unrealized P&L at last snapshot (n / avg / % positive) | 683 / 0.30% / 73.5% |
| …of which had already hit TP1 | 34 |
| Replacement exists (same symbol, next plan) | 774/774 |
| Replacement flips direction | 26 (3.4%) |
| Replacement confidence − original (avg) | -0.68 |
| Replacements that resolved: n / win rate | 88 / 39.8% (vs 39.0% for all resolved trades) |

**Was invalidation good or bad?** Roughly 73% of entered-then-invalidated trades were in profit at their last snapshot — invalidation closed positions that were mostly fine, but no realised outcome exists to say whether holding would have beaten the replacement (INSUFFICIENT DATA). Replacement win rate is in line with the overall resolved win rate, so there is no evidence replacements are *worse*. Most invalidations are re-issues while pending (churn), which inflates the '727 invalidated' figure without any economic meaning.

## SECTION 16 — OPEN TRADE ANALYSIS

| Symbol | Dir | Status | Stage | PnL% | To TP1% | To stop% | P(TP1) | P(TP2) | EV(R) | Reliability | Manager decision | Recommendation | Last snapshot | Days stale |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ONUSDT | long | open | None | 4.66 | 3.29 | -12.49 | — | — | — | — | — | Hold | 2026-08-08 10:36 | 49.4 |
| SKYAIUSDT | long | open | None | -11.43 | 26.87 | -2.01 | — | — | — | — | — | Hold | 2026-08-10 06:03 | 47.6 |
| GWEIUSDT | long | open | None | -0.75 | 7.96 | -7.96 | — | — | — | — | — | Hold | 2026-08-09 05:57 | 48.6 |
| MMTUSDT | long | pending | None | — | 6.01 | -12.77 | — | — | — | — | — | Hold | 2026-08-09 05:57 | 48.6 |
| 1000CATUSDT | long | open | None | 1.21 | 9.20 | -12.64 | — | — | — | — | — | Hold | 2026-08-09 05:57 | 48.6 |
| TSTUSDT | long | pending | None | — | 22.19 | 2.25 | — | — | — | — | — | Hold | 2026-08-11 09:49 | 46.4 |
| MUBARAKUSDT | long | open | None | 0.92 | 4.72 | -8.27 | — | — | — | — | — | Hold | 2026-08-10 06:03 | 47.6 |
| GUAUSDT | short | open | None | 0.19 | 4.41 | -5.22 | — | — | — | — | — | Hold | 2026-08-11 17:09 | 46.1 |
| BANKUSDT | short | open | TP1_REACHED | 8.53 | -0.00 | -20.02 | — | — | — | — | HOLD | Move Stop to Breakeven | 2026-08-14 08:57 | 43.5 |
| LITEUSDT | long | open | OPEN | -0.32 | 2.40 | -1.72 | — | — | — | 35.4 | HOLD | Hold | 2026-08-13 15:48 | 44.2 |
| ALLOUSDT | short | open | OPEN | 1.91 | 2.70 | -5.47 | — | — | — | 35.4 | HOLD | Hold | 2026-08-16 13:24 | 41.3 |
| BOMEUSDT | long | pending | PRE_ENTRY | — | -34.31 | -38.88 | — | — | — | — | HOLD | Hold | 2026-08-21 10:45 | 36.4 |
| XMRUSDT | long | pending | PRE_ENTRY | — | 0.47 | -1.90 | — | — | — | — | HOLD | Hold | 2026-08-16 13:24 | 41.3 |
| SPORTFUNUSDT | long | pending | PRE_ENTRY | — | 7.19 | -4.03 | — | — | — | 35.4 | HOLD | Hold | 2026-08-16 13:24 | 41.3 |
| 4USDT | long | pending | — | — | — | — | — | — | — | — | — | Hold | — | never |
| RAYSOLUSDT | long | open | OPEN | -6.35 | 12.94 | -1.44 | 53.10 | — | 0.12 | — | HOLD | Hold | 2026-09-13 14:17 | 13.3 |
| LINKUSDT | short | pending | PRE_ENTRY | — | 18.51 | 15.59 | 50.00 | — | -0.45 | 45.4 | HOLD | Hold | 2026-09-26 09:12 | 0.5 |
| SOXLUSDT | short | pending | PRE_ENTRY | — | 20.38 | 18.46 | 57.90 | — | 0.39 | — | HOLD | Hold | 2026-09-26 09:12 | 0.5 |
| REZUSDT | long | pending | PRE_ENTRY | — | -13.54 | -24.51 | 40.00 | — | -0.45 | — | HOLD | Hold | 2026-09-14 15:44 | 12.2 |
| 我踏马来了USDT | long | open | OPEN | -1.25 | 11.66 | -3.66 | 58.60 | — | 0.89 | — | HOLD | Hold | 2026-09-13 07:34 | 13.5 |
| RIVERUSDT | short | pending | PRE_ENTRY | — | 0.40 | -14.53 | 0.00 | — | -1.00 | 44.5 | HOLD | Hold | 2026-09-13 09:07 | 13.5 |
| WLFIUSDT | long | open | OPEN | 0.21 | 1.19 | -1.25 | 53.10 | — | 0.25 | — | HOLD | Hold | 2026-09-13 10:36 | 13.4 |
| GRIFFAINUSDT | long | open | OPEN | -2.29 | 9.22 | -1.98 | 53.10 | — | 0.38 | — | HOLD | Hold | 2026-09-13 13:21 | 13.3 |
| QQQUSDT | short | open | OPEN | -0.23 | 1.05 | -0.46 | 0.00 | — | -1.00 | 44.5 | HOLD | Hold | 2026-09-14 19:47 | 12.0 |
| KORUUSDT | long | open | OPEN | 0.12 | 1.49 | -3.50 | 60.00 | — | -0.12 | — | HOLD | Hold | 2026-09-26 09:12 | 0.5 |
| BNBUSDT | long | open | OPEN | -0.49 | 1.79 | -0.16 | 60.00 | — | 0.81 | 37.7 | HOLD | Hold | 2026-09-26 09:12 | 0.5 |
| DOGEUSDT | long | open | OPEN | -0.25 | 2.42 | -2.88 | 30.00 | — | -0.49 | 30.0 | HOLD | Hold | 2026-09-26 09:12 | 0.5 |
| SKHYNIXUSDT | long | open | OPEN | 0.31 | 0.16 | -1.74 | 35.70 | — | -0.53 | 37.7 | HOLD | Hold | 2026-09-26 09:12 | 0.5 |
| SKHYUSDT | long | open | OPEN | 0.31 | 0.69 | -1.07 | 35.70 | — | -0.17 | 42.1 | HOLD | Hold | 2026-09-26 09:12 | 0.5 |
| CLUSDT | long | open | OPEN | 0.11 | 1.01 | -2.82 | 60.00 | — | -0.15 | 42.1 | HOLD | Hold | 2026-09-26 09:12 | 0.5 |
| BZUSDT | long | open | OPEN | -0.11 | 1.39 | -2.62 | 60.00 | — | -0.12 | 32.5 | HOLD | Hold | 2026-09-26 09:12 | 0.5 |
| WLDUSDT | long | open | OPEN | 0.00 | 5.69 | -4.89 | 30.00 | — | -0.35 | 40.8 | HOLD | Hold | 2026-09-26 09:12 | 0.5 |
| SUIUSDT | long | open | OPEN | 0.39 | 5.07 | -5.80 | 30.00 | — | -0.40 | 32.5 | HOLD | Hold | 2026-09-26 09:12 | 0.5 |
| TAOUSDT | long | open | OPEN | 1.86 | 1.72 | -9.36 | 30.00 | — | -0.56 | — | HOLD | Hold | 2026-09-26 09:12 | 0.5 |
| PUMPUSDT | long | pending | — | — | — | — | — | — | 0.04 | 37.7 | — | Hold | — | never |

**DATA-STALENESS WARNING:** of 35 open/pending trades, 21 have had no snapshot for more than 1 day (median 13.4 days, oldest 49.4 days) and 2 have never been snapshotted. Their 'Hold' recommendations are the default output on stale data, NOT a live assessment - several are near their stops (see 'To stop%'). I therefore do not issue Reduce/Exit/Take-TP1 recommendations: the data cannot support them. Action: bring the scanner up and let it re-snapshot before acting on any of these.
**Recommendations are the existing deterministic Trade-Manager output** (Hold / Move stop / etc.); I did not invent new ones. 'Updated stop probability' and 'updated EV' are not recomputed per open trade by the system — only TP probabilities are stored on snapshots; EV is fixed at issuance (blank for pre-09-12 plans). Several open trades have not been snapshotted recently (scanner downtime), so 'current' values may be stale — check 'Last snapshot'.

## SECTION 17 — DECISION ENGINE AUDIT

| Gate | Passed (W/L) | Failed (W/L) | Win% passed / failed | Fisher p | Evidence the gate discriminates |
|---|---|---|---|---|---|
| trend | 42W/63L | 4W/9L | 40.0% / 30.8% | 0.7642 | NOT SUPPORTED |
| structure | 19W/26L | 27W/46L | 42.2% / 37.0% | 0.6978 | NOT SUPPORTED |
| history | 3W/10L | 43W/62L | 23.1% / 41.0% | 0.2459 | NOT SUPPORTED |
| volume | 44W/69L | 2W/3L | 38.9% / 40.0% | 1.0 | INSUFFICIENT DATA |
| funding | 46W/70L | 0W/2L | 39.7% / 0.0% | 0.5202 | INSUFFICIENT DATA |
| risk | 46W/72L | 0W/0L | 39.0% / -% | - | INSUFFICIENT DATA |
| regime | 46W/72L | 0W/0L | 39.0% / -% | - | INSUFFICIENT DATA |

| Decision rule | Take & won (TP) | Take & lost (FP) | Skip & won (FN) | Skip & lost (TN) | PF taken | PF skipped |
|---|---|---|---|---|---|---|
| ≥7 of 7 checks pass = 'take' | 0 | 3 | 46 | 69 | 0.00 | 1.64 |
| ≥6 of 7 checks pass = 'take' | 18 | 26 | 28 | 46 | 1.66 | 1.60 |
| ≥5 of 7 checks pass = 'take' | 44 | 65 | 2 | 7 | 1.55 | 2.13 |
| ≥4 of 7 checks pass = 'take' | 46 | 72 | 0 | 0 | 1.62 | — |

**Would today's decision still be made?** The live engine has no separate 'accept' step beyond the deterministic direction gate — every trade here was published under current logic; the checklist is diagnostic. **Which gate allowed bad trades / filtered winners:** history and structure fail on most trades regardless of outcome (they fail in ~94%/59% of wins vs ~86%/64% of losses); trend, risk, regime, funding and volume almost never fail (no information). No checklist gate is shown to discriminate (all p>0.15) — NOT SUPPORTED; changing decision.py on this evidence would be tuning on noise.

## SECTION 18 — WEIGHT RECALIBRATION (MEASUREMENT ONLY)

| Component | Current range | OR per +1 SD | Bootstrap 95% CI | Spearman p | Suggested weight | Expected PF improvement | Evidence |
|---|---|---|---|---|---|---|---|
| trend | 0–25 | 0.97 | [0.69,1.46] | 0.84 | No change (current weight retained) | n/a (cannot be estimated without a validated model) | NOT SUPPORTED |
| momentum | 0–15 | 1.07 | [0.77,1.61] | 0.337 | No change (current weight retained) | n/a (cannot be estimated without a validated model) | NOT SUPPORTED |
| volume | 0–10 | 1.09 | [0.75,1.55] | 0.924 | No change (current weight retained) | n/a (cannot be estimated without a validated model) | NOT SUPPORTED |
| funding | 0–10 | 1.1 | [0.10,8.11] | 0.957 | No change (current weight retained) | n/a (cannot be estimated without a validated model) | NOT SUPPORTED |
| structure | 0–15 | 1.11 | [0.77,1.64] | 0.493 | No change (current weight retained) | n/a (cannot be estimated without a validated model) | NOT SUPPORTED |
| history | −15..+15 | 0.6 | [0.31,0.85] | 0.804 | Statistically significant BUT only 16 non-zero trades (confounded with the few majors that have history) -> NOT recommended | n/a (cannot be estimated without a validated model) | LIKELY (confounded) |
| regime | −5..+5 | 0.7 | [0.45,1.01] | 0.036 | No change (current weight retained) | n/a (cannot be estimated without a validated model) | NOT SUPPORTED |
| risk | −20..0 | 1.37 | [0.94,2.25] | 0.039 | No change (current weight retained) | n/a (cannot be estimated without a validated model) | NOT SUPPORTED |
| liquidity | −5..0 | 4.13 | [0.94,8.56] | 0.108 | No change (current weight retained) | n/a (cannot be estimated without a validated model) | NOT SUPPORTED |
| ML | −10..+8 | 0.87 | [0.59,1.50] | 0.227 | No change (current weight retained) | n/a (cannot be estimated without a validated model) | NOT SUPPORTED |

**1 of 10 components have a bootstrap CI excluding 1 (history is nonzero on only 16 trades, all majors, and its win-rate test is p~0.28, so this is a confounded artefact).** Per instructions only statistically significant, adequately-sampled changes are recommended - none qualifies (so no suggested weights, and any 'expected PF improvement' would be fabricated). A cross-validated logistic model on the components had AUC 0.561 (≈ chance-to-weak).

## SECTION 19 — SIMULATION BACKTEST (SCENARIO REPLAY)

Scenarios are filters/policies applied to the same historical trades (in-sample; each was defined *after* seeing the data, so all gains are optimistic). Chronological split shows stability: the first half of trades (by entry time) vs the second. TP-manager and dynamic-stop scenarios use the path simulator from §9 on covered trades and actual results elsewhere.
| Scenario (ranked by PF) | n trades | Frequency kept | Win% | PF | PF ex-best | Median ret | Max DD (summed) | PF 1st half / 2nd half | Sum ret% |
|---|---|---|---|---|---|---|---|---|---|
| Excellent entries only | 19 | 16% | 52.6% | 3.30 | 2.42 | 2.93 | -24.3 | 8.76 / 1.59 | 103.1 |
| RSI 50–70 only | 85 | 72% | 44.7% | 3.17 | 2.61 | -1.07 | -87.0 | 2.88 / 3.37 | 447.4 |
| Longs + TP manager | 98 | 83% | 42.9% | 2.86 | 2.40 | -0.80 | n/a | 1.82 / 4.15 | 459.9 |
| Longs only | 98 | 83% | 43.9% | 2.60 | 2.19 | -1.11 | -88.2 | 1.96 / 3.23 | 447.5 |
| No shorts (identical to longs only) | 98 | 83% | 43.9% | 2.60 | 2.19 | -1.11 | -88.2 | 1.96 / 3.23 | 447.5 |
| Longs + weak-structure filter | 35 | 30% | 45.7% | 2.30 | 1.94 | -1.02 | -54.1 | 2.42 / 1.90 | 146.0 |
| TP manager (break-even after TP1) | 118 | 100% | 38.1% | 1.98 | 1.66 | -1.01 | n/a | 1.07 / 3.65 | 352.0 |
| Dynamic stop (trail 50% MFE after TP1) | 118 | 100% | 45.8% | 1.91 | 1.60 | -1.01 | n/a | 0.92 / 3.77 | 329.8 |
| Baseline | 118 | 100% | 39.0% | 1.62 | 1.37 | -1.59 | -100.5 | 1.15 / 2.13 | 280.8 |
| Weak structure filtered (structure ≥ 9) | 45 | 38% | 42.2% | 1.57 | 1.33 | -1.14 | -66.9 | 2.11 / 0.79 | 95.3 |
| Reliability(prior) ≥ median | 59 | 50% | 33.9% | 1.32 | 0.87 | -2.28 | -71.9 | 1.30 / 1.33 | 81.6 |

**Reading:** any scenario that beats baseline PF in *both* halves and with PF-ex-best>1 would be a lead, but all are in-sample. 'Longs only' improves PF mainly because the short cohort's losses were outage-contaminated (§4). TP-manager/dynamic-stop rows rest on partial path coverage (n in §9). Nothing here is CONFIRMED; ranking is descriptive, not a deployment recommendation.

## SECTION 20 — PREDICTION VERSION COMPARISON

| Version | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | PF ex-best | Brier | Mean conf | Regime mix | Naive DD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v1.0 (pre entry-quality) | 17 | 35.3% | 17.3–58.7 | -1.51 | -2.32 | 0.74 | 0.33 | 0.311 | 64.7 | {'risk_on': 16, 'mixed': 1} | -71.9 |
| Entry-Quality launch → EV launch | 73 | 38.4% | 28.1–49.8 | 1.25 | -1.64 | 1.36 | 1.18 | 0.302 | 63.7 | {'mixed': 58, 'risk_on': 15} | -100.5 |
| EV + Trade Manager + metadata (same deployment) | 28 | 42.9% | 26.5–60.9 | 7.67 | -1.00 | 3.21 | 2.04 | 0.281 | 59.0 | {'mixed': 25, 'risk_on': 3} | -51.7 |

| Comparison | n new/old | Win% new / old | OR | p | Evidence |
|---|---|---|---|---|---|
| post-Entry-Quality vs before | 101/17 | 39.6% / 35.3% | 1.2 | 0.7946 | NOT SUPPORTED |
| post-EV/TradeManager/metadata vs before | 28/90 | 42.9% / 37.8% | 1.24 | 0.6618 | NOT SUPPORTED |

Trade Manager and prediction-metadata launched with EV (same first stored timestamp), so they are not separable. Win-rate differences are **not** statistically meaningful (p above); PF gains in the latest era depend on a single trade (PF ex-best column) and on a different market window/regime mix. **Improvement is NOT statistically established** for any release.

## SECTION 21 — DASHBOARD API SCHEMA (BACKEND ONLY)

All schemas reuse endpoints/modules that already exist; the additions are fields, not new logic. `n` and an `evidence` label are mandatory in every block; `data_quality` reports scanner uptime and % gap-exposed so consumers cannot present a number without its caveat.
```json
{
 "GET /api/performance/daily-scorecard": {
  "as_of": "iso8601",
  "data_quality": {
   "scanner_uptime_pct_24h": "float",
   "gap_exposed_open_trades": "int",
   "last_heartbeat": "iso8601"
  },
  "closed_today": {
   "n": "int",
   "win_rate": "float|null",
   "profit_factor": "float|null",
   "median_return_pct": "float|null",
   "ex_top1_profit_factor": "float|null"
  },
  "funnel": {
   "scanned": "int",
   "published": "int",
   "rejected_by_reason": {
    "late": "int",
    "exhausted": "int",
    "no_trade": "int",
    "rank_cutoff": "int"
   }
  }
 },
 "GET /api/performance/trade-quality/{id}": {
  "score_0_100": "int",
  "band": "A+|A|B|C|D",
  "components": {
   "entry_quality": "float",
   "ev": "float|null",
   "reliability": "float",
   "calibration": "float",
   "structure": "float",
   "red_flags_inverted": "float"
  },
  "evidence": "string",
  "n_basis": "int"
 },
 "GET /api/performance/market-health": {
  "score_0_100": "int",
  "components": [
   {
    "name": "string",
    "value": "float|null",
    "available": "bool",
    "is_proxy": "bool"
   }
  ],
  "unavailable": [
   "news_stress"
  ]
 },
 "GET /api/performance/portfolio-exposure": {
  "open": "int",
  "pending": "int",
  "by_family": [
   {
    "family": "string",
    "n": "int",
    "long": "int",
    "short": "int"
   }
  ],
  "same_direction_share": "float",
  "warnings": [
   "string"
  ]
 },
 "GET /api/performance/coin-reliability": {
  "pooled_win_rate": "float",
  "symbols": [
   {
    "symbol": "string",
    "n": "int",
    "raw_win_rate": "float",
    "bayes_win_rate": "float",
    "credible_interval": "[float,float]",
    "p_above_pooled": "float",
    "tier": "Trusted|Watch|Caution|Avoid",
    "evidence": "string"
   }
  ]
 },
 "GET /api/performance/opportunities?rank=top|worst&limit=10": {
  "items": [
   {
    "trade_outcome_id": "int",
    "symbol": "string",
    "direction": "string",
    "quality_score": "int",
    "ev_r": "float|null",
    "calibrated_p": "float",
    "calibrated_p_interval": "[float,float]",
    "flags": [
     "string"
    ],
    "monitoring_status": "supervised|unmonitored"
   }
  ]
 }
}
```

## SECTION 22 — IMPLEMENTATION ROADMAP

Priority = evidence × size of lever ÷ (risk × complexity). Items that touch prediction are P3 or 'NOT NOW'. Nothing edits scoring.py, decision.py, the prompt or ML.
| Pri | Change | Impact | Risk | Evidence (numbers from DB) | Files affected | Migration | Tests | Expected improvement |
|---|---|---|---|---|---|---|---|---|
| P0 | Supervised always-on scanner + heartbeat alert (ops/deploy, not engine code) | Highest: removes gap exposure | Very low | uptime ≈16.1%; 62.8% of loss magnitude exits inside gaps; 70.3% of trades gap-exposed | deployment config (systemd/NSSM/Docker), `background_scanner.py` untouched | No | Restart/soak test; heartbeat alarm test | Cleaner data; P&L effect not isolatable |
| P0 | Every KPI shows n, Wilson CI, median, ex-top-3 PF, gap-exposed % | High (honesty) | None | PF 1.62 → 1.15 ex-top-3 | analytics/`performance_center.py`, `routes/performance.py` | No | Unit tests on each KPI | Prevents mis-decisions |
| P0 | Display calibrated probability (≈base rate ± Wilson) beside raw confidence | High (honesty) | None | mean conf 62.6 vs 38.9% observed, binomial p≈4.3e-07 | `engine/calibration.py` (display only), routes | No | Calibration tests exist | Removes ~24pp overstatement |
| P1 | Persist BOS/CHoCH/sweep/OBV booleans, ATR%, timeframe trends at issuance (additive columns) | Unblocks §2,5,13 | Low | 0 trades have them → 6 requested features INSUFFICIENT DATA | `db_models.py` (additive), `feature_builder.py`, `trade_outcomes.py` | Yes (additive nullable columns via `_sync_additive_columns`) | Round-trip persistence tests | Enables future evidence |
| P1 | Wire missed-opportunity recorder + track avoided/late/exhausted plans forward | Unblocks §14 | Low (needs approval: frozen `background_scanner.py`) | 48 avoided plans, 0 snapshots; 3625 late/exhausted scans, no prices | `background_scanner.py`, `analytics/missed_opportunity.py` | No (table exists) | Existing test_missed_opportunity | Enables unbiased rejection audit |
| P1 | Snapshot post-close price for 72h (per closed trade) | Unblocks 'should have continued' / early-stop verdicts | Low | Verdicts 'TP2 Hit — Should Have Continued' impossible today | `trade_outcomes.py`/monitor loop | Yes (new columns or table) | Unit tests | Enables exit-policy research |
| P2 | Shadow-log break-even / trailing outcomes for every trade | Medium (evidence for §9) | None | §9 results inconclusive, partial paths | `analytics/*` only | No | Path-sim unit tests | Decides trailing/BE at n=200 |
| P2 | Soft warnings: RSI 30–49 chop; short 'monitoring-sensitive' | Low–Med | Low | RSI30–49 win 20.8% (n=24) vs 43.8%, p≈0.06 | `red_flags.py` (already there), UI | No | Existing | Possible; unproven |
| P3 | Any weight / decision / regime / prompt change | Unknown | High (overfit) | 0 significant components; CV-AUC ≈ chance-to-weak (§18) | scoring.py, decision.py, market_regime.py, reasoning.py | — | — | NOT NOW; re-audit at n≥200 |
| P3 | Hard short ban | Unknown | High | uptime-only shorts 33.3% (n=9) | — | — | — | NOT NOW |
| P3 | ML retrain / coin-personality models | None shown | High | AUC unchanged after retrain; n per coin ≤4 | ml_model.py, ml_retrain.py | — | — | NOT before 200 trades (your rule) and a held-out test |


## SECTION 23 — SAFE IMPLEMENTATION PLAN (COMMIT-BY-COMMIT)

Follows your rules: no scoring.py / decision.py / prompt / ML edits; ML retraining not before 200 resolved trades (currently 118 closed; the 'total resolved' counts differ from your brief only because the scanner has kept running). **No diffs or commits were produced now** — none is justified by evidence yet except the additive ones below, which need your go-ahead.
| # | Commit (message) | Exact files | Type | Gate/evidence | Tests |
|---|---|---|---|---|---|
| 1 | ops: supervised scanner service + heartbeat alert | `deploy/` (service unit/NSSM script), `README` run notes; no app code | Ops | §U/§4: uptime, gap-exposure | Manual soak: kill/restart; gap alert fires |
| 2 | analytics: uptime/gap-exposure annotations on every KPI | `app/engine/performance_center.py`, `app/routes/performance.py` | Additive analytics | §A/§U | extend `test_performance_center.py` |
| 3 | analytics: KPI blocks with n, Wilson CI, median, ex-top-k PF | `app/analytics/kpi.py` (new), `routes/performance.py` | Additive | PF fragile ex-top-3 | new `test_kpi.py` with fixed fixtures |
| 4 | analytics: calibrated-probability display (base-rate ± Wilson) + reliability diagram endpoint | `app/engine/calibration.py`, `app/analytics/calibration_dashboard.py` | Additive display | §3 binomial test | extend `test_calibration.py` |
| 5 | feat(data): additive nullable columns for BOS/CHoCH/sweep/ATR%/timeframe trends on TradeOutcome | `app/models/db_models.py`, `app/engine/feature_builder.py`, `app/engine/trade_outcomes.py` | Additive migration (auto via `_sync_additive_columns`) | §2/§5/§13 INSUFFICIENT DATA | persistence round-trip test; NULL-safe readers |
| 6 | feat(data): wire missed-opportunity recorder for late/exhausted/rank-cutoff/avoid plans (**requires explicit approval — touches frozen background_scanner.py**) | `app/engine/background_scanner.py`, `app/analytics/missed_opportunity.py` | Additive data capture | §14 INSUFFICIENT DATA | extend `test_missed_opportunity.py` |
| 7 | feat(data): 72h post-close price capture | `app/engine/trade_outcomes.py`, `db_models.py` | Additive | 'Should have continued' unknowable | unit test with synthetic closes |
| 8 | analytics: shadow path-simulation logging for BE/trailing/ATR stops on each closed trade | `app/analytics/stop_styles.py` (new) | Additive | §9 inconclusive | port §9 simulator into tests with fixed paths |
| 9 | docs: re-audit scripts (`analysis_karma_*.py`) become `tools/audit/` + weekly run | `tools/audit/*` | Docs/tools | Reproducibility | smoke-run against a DB copy |
| — | **Hold until ≥200 resolved trades and explicit approval:** any scoring/decision/regime/prompt/ML change | — | — | §18: no significant component | Out-of-sample: fit on first half, test on second |


**END REPORT.**