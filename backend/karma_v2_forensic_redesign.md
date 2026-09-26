# Karma V2 — Full Forensic Model Redesign

**Read-only audit. No code, prompts, weights, DB rows, or models were modified.** Computed by `analysis_karma_v2_forensic.py` directly against the live SQLite DB (`TradeOutcome`, `PredictionSnapshot`, `ScanSnapshot`; `MarketSnapshot` only backs the 6 legacy-backfilled majors and has no per-trade join — see Part 15/16). Snapshot: **86 resolved trades, 33 wins, 53 losses.**

**Tables that do not exist in this codebase, checked and confirmed before writing this report, not assumed:** there is no `CoinHistory` table. There is no per-trade ML "prediction table" beyond the single `ml_probability` float stored on `TradeOutcome`. There is no stored per-trade boolean for BOS, CHoCH, or order block — order-block detection isn't implemented anywhere in this codebase at all (confirmed earlier this session by reading `smart_money.py`). `entry_indicators` (captured at issuance) covers `rsi14, stoch_rsi, adx14, macd_hist, cmf, mfi, bb_pct, distance_to_ema20/50/200_pct, atr_distance_to_ema20`; raw OBV value and a Bollinger-touch boolean are not stored, only `bb_pct`. `level_reasoning` (FVG price range, ATR-normalized stop distance) only exists on the 48 of 86 trades issued after that capture pass shipped. Every part below uses exactly what's stored — nothing here is estimated or backfilled to fill a gap.

---

## PART 1 — Every Closed Trade Ledger

Full CSV (`scratch_karma_ledger.csv`, 86 rows, 45 columns) written alongside this report. The columns requested that are **not available** and are honestly omitted from the table below rather than fabricated: raw OBV, BOS present, CHoCH present, order block present, "entry inside FVG" as a boolean (only 48/86 trades have any FVG data at all, and it's a nested object, not a boolean — see `fvg_used` column), "entry above EMA20" as a boolean (only `distance_to_ema20_pct` is stored, omitted here for space, in the CSV), "price touching Bollinger band" as a boolean (`bb_pct` exists in the CSV, not reduced to a boolean here), and a distinct "sentiment" field (only `fear_greed` int and `news_sentiment`/`reddit_sentiment` blobs exist, in the CSV, not this condensed table).

| symbol | dir | hold(min) | entry | exit | stop | tp1 | tp2 | tp3 | exit reason | return% | MFE% | MAE% | conf | grade | entry_q | regime | trend | mom | struct | hist | ml_prob | rsi | adx | fvg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NVDAUSDT | long | 10657 | 214.70 | 223.53 | 209.90 | 219.30 | 223.50 | | target | 4.11 | 4.11 | 0.53 | | | | mixed | 22.32 | 11.00 | 6.00 | 0.00 | | | | |
| DRAMUSDT | long | 2419 | 54.45 | | 52.10 | 56.50 | 58.00 | | stop | -5.31 | 0.39 | -5.31 | | | | risk_on | 12.77 | 15.00 | 11.00 | 0.00 | | | | |
| EWYUSDT | long | 2565 | 170.25 | | 165.50 | 175.00 | 178.50 | | stop | -3.65 | 0.15 | -3.65 | | | | risk_on | 14.77 | 15.00 | 6.00 | 0.00 | | | | |
| SNDKUSDT | long | 2408 | 1387.50 | | 1340.00 | 1430.00 | 1460.00 | | stop | -7.00 | 0.01 | -7.00 | | | | risk_on | 14.28 | 15.00 | 6.00 | 0.00 | | | | |
| CYSUSDT | long | 116 | 0.82 | | 0.73 | 0.88 | 0.93 | | target | 19.67 | 19.67 | 0.48 | | | | risk_on | 25.00 | 8.00 | 11.00 | 0.00 | | | | |
| ZECUSDT | long | 5004 | 511.75 | | 498.00 | 524.00 | 535.00 | | stop | -4.36 | 0.40 | -4.36 | 67 | B+ | | risk_on | 21.11 | 8.00 | 6.00 | 0.00 | | 63.03 | 24.45 | |
| ACEUSDT | long | 877 | 0.11 | | 0.10 | 0.12 | 0.14 | 0.14 | stop | -9.66 | -0.69 | -9.66 | 61 | B | | risk_on | 25.00 | 15.00 | 11.00 | 0.00 | | 60.23 | 56.50 | |
| PAXGUSDT | long | 4579 | 4329.00 | | 4280.00 | 4350.00 | 4382.00 | | target | 1.36 | 1.36 | 0.12 | 71 | B+ | | risk_on | 25.00 | 11.00 | 6.00 | 0.00 | | 79.90 | 50.75 | |
| CRCLUSDT | long | 4741 | 66.40 | | 64.50 | 68.00 | 69.50 | | target | 5.24 | 5.24 | 0.48 | 54 | C | | risk_on | 17.49 | 15.00 | 6.00 | 0.00 | | 64.70 | 29.94 | |
| QQQUSDT | long | 7956 | 721.25 | 733.27 | 712.50 | 727.00 | 730.00 | | target | 1.67 | 1.67 | 0.07 | 72 | B+ | | risk_on | 24.48 | 8.00 | 11.00 | 0.00 | | 63.08 | 37.93 | |
| BEATUSDT | long | 1436 | 2.88 | | 2.63 | 3.02 | 3.18 | 3.40 | stop | -9.50 | 8.56 | -9.50 | 62 | B | | risk_on | 20.86 | 15.00 | 6.00 | 0.00 | | 58.71 | 23.42 | |
| ACEUSDT | long | 7463 | 0.13 | 0.18 | 0.12 | 0.14 | 0.15 | 0.16 | target | 39.81 | 39.81 | -0.99 | 71 | B+ | | risk_on | 25.00 | 15.00 | 11.00 | 0.00 | | 58.53 | 55.46 | |
| BICOUSDT | long | 1406 | 0.07 | | 0.06 | 0.08 | 0.09 | 0.10 | stop | -44.42 | -0.55 | -44.42 | 71 | B+ | | risk_on | 25.00 | 9.00 | 11.00 | 0.00 | | 90.84 | 63.23 | |
| SOLUSDT | long | 2030 | 76.50 | | 74.90 | 78.20 | 79.50 | | stop | -2.21 | 0.51 | -2.21 | 45 | C | | risk_on | 22.33 | 15.00 | 6.00 | 1.50 | 0.63 | 63.73 | 29.31 | |
| 1000PEPEUSDT | long | 3990 | 0.0029 | 0.0027 | 0.0028 | 0.0029 | 0.0030 | 0.0031 | stop | -7.47 | 0.15 | -7.47 | 64 | B | | risk_on | 20.69 | 15.00 | 6.00 | 0.00 | | 57.18 | 22.77 | |
| BTCUSDT | long | 1521 | 65000 | | 64350 | 65650 | 66300 | 67200 | stop | -1.61 | 0.24 | -1.61 | 69 | B+ | | risk_on | 19.73 | 8.00 | 6.00 | 7.50 | 0.60 | 58.00 | 18.92 | |
| ETHUSDT | long | 1521 | 1918 | | 1888 | 1945 | 1965 | 1990 | stop | -2.32 | 0.27 | -2.32 | 69 | B+ | | risk_on | 18.97 | 8.00 | 6.00 | 7.50 | 0.62 | 56.91 | 15.88 | |
| SKHYNIXUSDT | short | 1171 | 1008.50 | 1058.89 | 1037.50 | 991.70 | 964.00 | | stop | -5.00 | 0.09 | -5.00 | 55 | B | neutral | mixed | 19.42 | 15.00 | 6.00 | 0.00 | | 43.83 | 17.67 | |
| HYPEUSDT | long | 138 | 55.05 | | 54.25 | 55.75 | 56.40 | 57.10 | stop | -1.64 | -0.00 | -1.64 | 57 | B | neutral | mixed | 13.25 | 15.00 | 6.00 | 0.00 | | 50.85 | 12.98 | |
| DRAMUSDT | short | 814 | 50.88 | 52.58 | 51.75 | 49.80 | 48.60 | | stop | -3.35 | 0.85 | -3.35 | 59 | B | neutral | mixed | 15.03 | 15.00 | 6.00 | 0.00 | | 50.19 | 20.11 | |
| RKLBUSDT | short | 106 | 78.10 | | 80.15 | 75.80 | 73.50 | 71.50 | stop | -2.66 | 0.41 | -2.66 | 68 | B+ | good | mixed | 22.94 | 8.00 | 11.00 | 0.00 | | 43.50 | 31.75 | |
| SNXXUSDT | short | 731 | 9.82 | 10.37 | 10.35 | 9.35 | 8.85 | 8.35 | stop | -5.55 | 0.46 | -5.55 | 55 | B | good | mixed | 13.53 | 15.00 | 11.00 | 0.00 | | 54.68 | 14.13 | |
| SNDKUSDT | long | 1102 | 1263 | 1342.10 | 1233.50 | 1290 | 1315 | 1340 | target | 6.26 | 6.26 | 0.19 | 62 | B | excellent | mixed | 13.57 | 15.00 | 11.00 | 0.00 | | 56.16 | 14.27 | |
| SOLUSDT | short | 851 | 75.15 | 76.68 | 76.55 | 73.90 | 72.60 | 71.00 | stop | -2.04 | 0.01 | -2.04 | 65 | B+ | excellent | mixed | 20.15 | 8.00 | 11.00 | 4.50 | 0.56 | 45.53 | 20.60 | |
| HYPEUSDT | short | 956 | 54.30 | 55.69 | 55.65 | 52.60 | 51.40 | 49.40 | stop | -2.56 | 0.34 | -2.56 | 64 | B | excellent | mixed | 18.63 | 8.00 | 11.00 | 0.00 | | 43.66 | 14.54 | |
| SKHYUSDT | long | 488 | 143.90 | 152.00 | 139.50 | 148.50 | 152.00 | | target | 5.63 | 5.63 | 0.51 | 63 | B | excellent | mixed | 14.74 | 15.00 | 11.00 | 0.00 | | 61.53 | 18.96 | |
| BZUSDT | long | 1500 | 87.60 | 85.83 | 85.90 | 89.50 | 91.00 | 92.90 | stop | -2.02 | 0.60 | -2.02 | 65 | B+ | neutral | mixed | 24.26 | 15.00 | 6.00 | 0.00 | | 63.46 | 37.05 | |
| NEARUSDT | long | 12937 | 1.64 | 1.86 | 1.59 | 1.69 | 1.72 | 1.76 | target | 13.36 | 13.36 | -1.80 | 61 | B | excellent | mixed | 15.34 | 15.00 | 11.00 | 0.00 | | 55.45 | 21.34 | |
| VELVETUSDT | long | 620 | 0.55 | 0.70 | 0.51 | 0.59 | 0.63 | 0.68 | target | 27.28 | 27.28 | -0.45 | 63 | B | good | mixed | 24.69 | 15.00 | 11.00 | 0.00 | | 55.41 | 38.76 | |
| DOGEUSDT | long | 768 | 0.0698 | 0.0696 | 0.0698 | 0.0700 | 0.0714 | 0.0755 | stop | -2.52 | 1.06 | -2.52 | 56 | B | good | mixed | 15.60 | 15.00 | 11.00 | 0.00 | | 61.22 | 22.40 | |
| HOLOUSDT | long | 487 | 0.077 | 0.072 | 0.074 | 0.081 | 0.086 | 0.093 | stop | -7.17 | 0.63 | -7.17 | 64 | B | good | mixed | 23.47 | 15.00 | 11.00 | 0.00 | | 55.05 | 33.89 | |
| CLUSDT | long | 1243 | 82.55 | 80.92 | 81.00 | 84.00 | 85.00 | 86.50 | stop | -1.98 | 0.28 | -1.98 | 62 | B | neutral | mixed | 23.75 | 15.00 | 6.00 | 0.00 | | 63.31 | 34.99 | |
| LITEUSDT | long | 11 | 892.50 | 846.79 | 855.00 | 930.00 | 955.00 | | stop | -5.12 | 0.84 | -5.12 | 73 | B+ | excellent | mixed | 24.13 | 15.00 | 11.00 | 0.00 | | 60.54 | 36.52 | |
| CRCLUSDT | long | 1689 | 69.80 | 73.78 | 68.40 | 71.50 | 72.40 | | target | 5.70 | 5.70 | -0.43 | 54 | C | neutral | mixed | 23.33 | 15.00 | 6.00 | 0.00 | | 56.74 | 33.33 | |
| XAGUSDT | long | 1432 | 65.35 | 64.34 | 64.35 | 66.59 | 67.04 | 68.50 | stop | -1.55 | 1.42 | -1.55 | 68 | B+ | good | mixed | 25.00 | 8.00 | 11.00 | 0.00 | | 59.35 | 41.98 | |
| BTWUSDT | long | 605 | 0.24 | 0.27 | 0.21 | 0.26 | 0.27 | | target | 13.49 | 13.49 | -3.51 | 61 | B | good | mixed | 19.85 | 15.00 | 11.00 | 0.00 | | 57.19 | 19.40 | |
| XAUUSDT | long | 64 | 4400.50 | 4374.88 | 4380.00 | 4436.00 | 4456.65 | 4490.00 | stop | -0.58 | 0.05 | -0.58 | 68 | B+ | neutral | mixed | 25.00 | 8.00 | 6.00 | 0.00 | | 58.84 | 43.06 | |
| PAXGUSDT | long | 64 | 4390.50 | 4364.53 | 4368.00 | 4425.00 | 4440.70 | 4479.00 | stop | -0.59 | 0.06 | -0.59 | 68 | B+ | neutral | mixed | 25.00 | 8.00 | 6.00 | 0.00 | | 58.98 | 44.12 | |
| CYSUSDT | long | 74 | 1.46 | 1.38 | 1.38 | 1.59 | 1.70 | 1.78 | stop | -6.08 | 0.74 | -6.08 | 63 | B | good | mixed | 25.00 | 15.00 | 11.00 | 0.00 | | 58.70 | 42.11 | down FVG 1.48-1.59 |
| SKHYUSDT | long | 321 | 150.80 | 163.91 | 144.30 | 154.06 | 157.06 | 163.87 | target | 8.69 | 8.69 | 0.38 | 64 | B | good | mixed | 18.05 | 15.00 | 11.00 | 0.00 | | 63.64 | 32.22 | down FVG 153.5-154.1 |
| DRAMUSDT | long | 172 | 54.35 | 55.89 | 53.60 | 55.05 | 55.86 | | target | 2.83 | 2.83 | -0.33 | 64 | B | good | mixed | 17.49 | 15.00 | 11.00 | 0.00 | | 64.86 | 29.96 | down FVG 54.7-55.1 |
| NVDAUSDT | long | 21408 | 223.85 | 227.39 | 221.20 | 225.24 | 226.48 | | target | 1.58 | 1.58 | 0.15 | 62 | B | neutral | mixed | 23.58 | 15.00 | 6.00 | 0.00 | | 60.76 | 34.31 | |
| EWYUSDT | long | 146 | 174.60 | 179.20 | 172.50 | 177.90 | 178.70 | | target | 2.63 | 2.63 | -0.18 | 64 | B | neutral | mixed | 22.38 | 15.00 | 6.00 | 0.00 | | 64.38 | 29.54 | |
| SOXSUSDT | short | 6 | 41.15 | 40.86 | 41.95 | 39.88 | 41.82 | | target | 0.70 | 0.70 | 0.24 | 69 | B+ | good | mixed | 21.08 | 8.00 | 11.00 | 0.00 | | 42.93 | 24.34 | up FVG 40.9-41.1 |
| SAMSUNGUSDT | long | 128 | 185.75 | 195.86 | 183.30 | 191.23 | 195.70 | | target | 5.44 | 5.44 | 0.20 | 66 | B+ | neutral | mixed | 24.41 | 11.00 | 6.00 | 0.00 | | 67.55 | 37.64 | |
| MUUSDT | long | 13 | 911.25 | 934.30 | 901.50 | 916.10 | 929.00 | | target | 2.53 | 2.53 | 0.26 | 64 | B | neutral | mixed | 20.19 | 15.00 | 6.00 | 0.00 | | 60.48 | 20.76 | |
| ETHUSDT | long | 52 | 1888 | 1868.99 | 1873.00 | 1899.60 | 1911.50 | 1943.00 | stop | -1.01 | -0.00 | -1.01 | 65 | B+ | neutral | mixed | 14.11 | 15.00 | 6.00 | 12.00 | 0.65 | 49.16 | 16.42 | |
| BTWUSDT | long | 3041 | 0.26 | 0.32 | 0.23 | 0.27 | 0.28 | 0.31 | target | 21.02 | 21.02 | 0.10 | 60 | B | excellent | mixed | 19.31 | 15.00 | 11.00 | 0.00 | | 62.69 | 17.23 | up FVG 0.256-0.259 |
| LINKUSDT | long | 1729 | 8.71 | 9.46 | 8.58 | 8.87 | 8.98 | 9.04 | target | 8.66 | 8.66 | 0.31 | 67 | B+ | neutral | mixed | 23.49 | 8.00 | 6.00 | 0.00 | | 60.38 | 33.95 | |
| SPCXUSDT | long | 2546 | 143.55 | 139.58 | 139.60 | 148.60 | 152.00 | | stop | -2.77 | 0.81 | -2.77 | 66 | B+ | good | mixed | 22.62 | 15.00 | 11.00 | 0.00 | | 61.33 | 30.49 | down FVG 144.0-146.3 |
| APRUSDT | long | 705 | 0.46 | 0.54 | 0.40 | 0.49 | 0.53 | 0.54 | target | 19.04 | 19.04 | -4.33 | 64 | B | neutral | mixed | 25.00 | 15.00 | 6.00 | 0.00 | | 61.56 | 63.52 | |
| BNBUSDT | long | 624 | 610.50 | 604.36 | 604.70 | 615.20 | 620.90 | | stop | -1.01 | 0.37 | -1.01 | 69 | B+ | excellent | mixed | 21.16 | 8.00 | 11.00 | 6.00 | 0.55 | 55.31 | 24.64 | up FVG 610.5-610.9 |
| SAMSUNGUSDT | long | 10407 | 191.50 | 203.79 | 182.50 | 195.25 | 199.60 | | target | 6.42 | 6.42 | -0.95 | 66 | B+ | neutral | mixed | 25.00 | 11.00 | 6.00 | 0.00 | | 67.64 | 44.67 | |
| DOGEUSDT | short | 8073 | 0.070 | 0.084 | 0.071 | 0.070 | 0.069 | | stop | -20.31 | 0.95 | -20.31 | 53 | C | neutral | mixed | 20.56 | 15.00 | 6.00 | 0.00 | | 48.48 | 22.22 | |
| SKHYNIXUSDT | long | 6879 | 1171.17 | 1253.92 | 1157.05 | 1209.00 | 1221.99 | | target | 7.07 | 7.07 | 0.17 | 65 | B+ | excellent | mixed | 20.00 | 8.00 | 11.00 | 0.00 | | 62.52 | 48.53 | up FVG 1172.6-1172.8 |
| PUMPUSDT | long | 7880 | 0.00281 | 0.00391 | 0.00268 | 0.00281 | 0.00291 | | target | 39.37 | 39.37 | -3.46 | 71 | B+ | excellent | mixed | 22.27 | 8.00 | 11.00 | 0.00 | | 54.41 | 29.08 | up FVG 0.00279-0.00280 |
| WLDUSDT | long | 7804 | 0.35 | 0.38 | 0.34 | 0.35 | 0.36 | 0.37 | target | 8.29 | 8.29 | -1.48 | 67 | B+ | excellent | mixed | 21.87 | 15.00 | 11.00 | 0.00 | | 59.40 | 27.48 | up FVG 0.3487-0.3491 |
| SPORTFUNUSDT | long | 182 | 0.0258 | 0.0242 | 0.0242 | 0.0261 | 0.0290 | | stop | -6.12 | 0.78 | -6.12 | 59 | B | neutral | mixed | 23.86 | 15.00 | 6.00 | 0.00 | | 61.30 | 35.42 | |
| ETHUSDT | short | 7184 | 1880.25 | 2381.77 | 1890.60 | 1876.00 | 1852.22 | | stop | -26.67 | 0.11 | -26.67 | 56 | B | neutral | mixed | 15.02 | 15.00 | 6.00 | 4.50 | 0.64 | 46.93 | 20.07 | |
| HYPEUSDT | long | 7074 | 57.14 | 73.76 | 56.55 | 57.85 | 58.45 | 59.10 | target | 29.07 | 29.07 | 0.12 | 65 | B+ | excellent | mixed | 19.39 | 15.00 | 11.00 | 0.00 | | 59.03 | 17.58 | up FVG 57.30-57.33 |
| ALLOUSDT | short | 34 | 0.27 | 0.28 | 0.27 | 0.26 | 0.25 | 0.24 | stop | -2.76 | 0.55 | -2.76 | 63 | B | neutral | mixed | 22.71 | 11.00 | 6.00 | 0.00 | | 39.63 | 30.82 | |
| ZECUSDT | short | 7086 | 488.50 | 629.21 | 494.50 | 483.45 | 480.27 | 466.28 | stop | -28.80 | 0.76 | -28.80 | 59 | B | neutral | mixed | 18.55 | 15.00 | 6.00 | 0.00 | | 47.95 | 14.19 | |
| CLUSDT | long | 7068 | 81.22 | 86.38 | 80.80 | 81.56 | 82.00 | 84.04 | target | 6.35 | 6.35 | 0.04 | 62 | B | neutral | mixed | 18.64 | 8.00 | 6.00 | 0.00 | | 51.24 | 14.58 | |
| LINKUSDT | long | 6930 | 9.34 | 11.65 | 9.18 | 9.51 | 9.63 | | target | 24.70 | 24.70 | -0.12 | 64 | B | neutral | mixed | 25.00 | 15.00 | 6.00 | 0.00 | | 62.60 | 47.95 | |
| SAMSUNGUSDT | long | 10319 | 196.75 | 187.77 | 191.00 | 203.40 | 206.00 | 211.50 | stop | -4.56 | 0.49 | -4.56 | 68 | B+ | neutral | risk_on | 22.04 | 15.00 | 6.00 | 0.00 | | 56.96 | 28.16 | |
| DRAMUSDT | long | 10279 | 58.42 | 55.92 | 57.35 | 59.37 | 60.81 | 62.09 | stop | -4.29 | 0.62 | -4.29 | 63 | B | neutral | risk_on | 19.71 | 15.00 | 6.00 | 0.00 | | 56.60 | 18.83 | |
| MUUSDT | long | 10190 | 977.35 | 921.10 | 963.73 | 987.97 | 1021.79 | 1036.00 | stop | -5.75 | 0.40 | -5.75 | 66 | B+ | neutral | risk_on | 19.79 | 15.00 | 6.00 | 0.00 | | 56.71 | 19.17 | |
| MSTRUSDT | long | 29 | 134.74 | 132.35 | 132.40 | 136.55 | 137.17 | 141.10 | stop | -1.77 | 0.28 | -1.77 | 71 | B+ | good | risk_on | 24.81 | 15.00 | 11.00 | 0.00 | | 63.00 | 39.25 | down FVG 136.2-137.2 |
| SOLUSDT | long | 7489 | 104.40 | 99.42 | 100.90 | 106.80 | 110.00 | 113.00 | stop | -4.77 | 2.73 | -4.77 | 73 | B+ | good | risk_on | 24.92 | 15.00 | 11.00 | -3.00 | 0.52 | 60.16 | 39.70 | down FVG 106.0-106.2 |
| XAGUSDT | long | 67 | 69.40 | 66.76 | 67.40 | 71.01 | 71.23 | | stop | -3.80 | 0.06 | -3.80 | 61 | B | neutral | risk_on | 20.15 | 15.00 | 6.00 | 0.00 | | 52.28 | 20.58 | |
| ETHUSDT | long | 49 | 2502 | 2475.25 | 2478.00 | 2535.00 | 2570.00 | 2620.00 | stop | -1.07 | 0.20 | -1.07 | 76 | A | neutral | risk_on | 24.38 | 8.00 | 6.00 | 9.00 | 0.49 | 59.58 | 37.50 | |
| MSTRUSDT | long | 23 | 133.70 | 129.10 | 129.50 | 137.17 | 141.10 | 143.19 | stop | -3.44 | -0.75 | -3.44 | 65 | B+ | good | risk_on | 19.61 | 15.00 | 11.00 | 0.00 | | 57.81 | 38.45 | down FVG 136.2-137.2 |
| SPCXUSDT | long | 8509 | 140.10 | 146.76 | 138.40 | 141.96 | 143.50 | 146.10 | target | 4.75 | 4.75 | -1.12 | 65 | B+ | neutral | risk_on | 18.75 | 15.00 | 6.00 | 0.00 | | 58.86 | 15.02 | |
| MSTRUSDT | long | 7380 | 129.00 | 122.62 | 126.50 | 136.17 | 140.85 | 143.19 | stop | -4.95 | -0.32 | -4.95 | 65 | B+ | good | risk_on | 19.47 | 15.00 | 11.00 | 0.00 | | 51.89 | 37.89 | down FVG 136.2-137.2 |
| MOVRUSDT | long | 24 | 0.91 | 0.88 | 0.89 | 0.97 | 1.02 | 1.14 | stop | -2.93 | -0.11 | -2.93 | 61 | B | neutral | risk_on | 20.00 | 15.00 | 6.00 | 0.00 | | 55.73 | 42.77 | |
| BNBUSDT | long | 34 | 694.55 | 686.61 | 686.90 | 707.78 | 719.14 | | stop | -1.14 | -0.17 | -1.14 | 71 | B+ | good | mixed | 20.00 | 8.00 | 11.00 | 10.50 | 0.54 | 43.62 | 40.77 | down FVG 696.8-703.2 |
| MOVRUSDT | long | 30 | 0.91 | 0.77 | 0.84 | 0.97 | 1.04 | 1.14 | stop | -16.01 | 0.23 | -16.01 | 59 | B | neutral | mixed | 20.00 | 15.00 | 6.00 | 0.00 | | 56.23 | 43.45 | |
| TRUMPUSDT | long | 6864 | 2.75 | 2.17 | 2.50 | 2.89 | 3.10 | | stop | -20.95 | 10.98 | -20.95 | 47 | C | neutral | mixed | 24.83 | 15.00 | 6.00 | 0.00 | | 63.56 | 39.30 | |
| ZECUSDT | long | 11785 | 802.00 | 1166.44 | 775.00 | 817.22 | 889.99 | | target | 45.44 | 45.44 | -1.45 | 65 | B+ | neutral | mixed | 20.92 | 8.00 | 6.00 | 0.00 | | 53.63 | 23.66 | |
| SNXXUSDT | short | 6712 | 12.90 | 13.94 | 13.45 | 12.20 | 12.02 | 11.65 | stop | -8.06 | 0.62 | -8.06 | 64 | B | neutral | mixed | 20.25 | 15.00 | 6.00 | 0.00 | | 45.41 | 20.98 | |
| SNDKUSDT | short | 6712 | 1485.00 | 1548.90 | 1517.00 | 1477.00 | 1436.00 | 1419.66 | stop | -4.30 | 0.10 | -4.30 | 59 | B | neutral | mixed | 14.97 | 15.00 | 6.00 | 0.00 | | 45.88 | 19.87 | |
| CLUSDT | long | 6712 | 83.15 | 90.82 | 82.20 | 83.63 | 84.41 | | target | 9.22 | 9.22 | -0.20 | 58 | B | neutral | mixed | 14.43 | 15.00 | 6.00 | 0.00 | | 50.99 | 17.70 | |
| SKHYUSDT | long | 7303 | 161.60 | 159.06 | 160.30 | 163.50 | 166.71 | | stop | -1.57 | 2.28 | -1.57 | 62 | B | neutral | mixed | 18.49 | 15.00 | 6.00 | 0.00 | | 51.90 | 13.94 | |
| HEMIUSDT | long | 17 | 0.0126 | 0.0115 | 0.0115 | 0.0132 | 0.0140 | 0.0155 | stop | -8.62 | 0.57 | -8.62 | 64 | B | neutral | mixed | 25.00 | 11.00 | 6.00 | 0.00 | | 65.07 | 42.89 | |
| ENAUSDT | long | 278 | 0.16 | 0.16 | 0.16 | 0.16 | 0.17 | 0.18 | stop | -4.10 | 1.47 | -4.10 | 59 | B | neutral | mixed | 25.00 | 15.00 | 6.00 | 0.00 | | 56.79 | 45.60 | |
| SOXSUSDT | long | 6762 | 49.30 | 53.00 | 47.80 | 49.81 | 50.23 | 52.85 | target | 7.50 | 7.50 | 0.12 | 60 | B | neutral | mixed | 16.05 | 15.00 | 6.00 | 0.00 | | 59.12 | 24.20 | |

*(9 of the oldest trades predate confidence/grade/entry_quality being captured — blank cells above are genuine NULLs, not zeros.)*

---

## PART 2 — Feature Importance

| feature bucket | n | win rate | avg return | PF | TP2 rate | stop rate |
|---|---|---|---|---|---|---|
| Trend <15 | 10 | 30.0% | -0.73% | 0.74 | 30.0% | 70.0% |
| Trend 15-19 | 23 | 43.5% | +0.85% | 1.21 | 43.5% | 56.5% |
| Trend 20-22 | 24 | 33.3% | +0.77% | 1.20 | 33.3% | 66.7% |
| Trend 23-25 | 29 | 41.4% | +1.20% | 1.28 | 41.4% | 58.6% |
| Momentum 6-8 | 20 | 40.0% | +5.37% | 6.00 | 40.0% | 60.0% |
| Momentum 9-11 | 7 | 57.1% | -5.50% | 0.31 | 57.1% | 42.9% |
| Momentum 12-15 | 59 | 35.6% | -0.06% | 0.99 | 35.6% | 64.4% |
| Structure 6-8 | 51 | 33.3% | -1.26% | 0.71 | 33.3% | 66.7% |
| Structure 9-11 | 35 | 45.7% | +3.71% | 2.13 | 45.7% | 54.3% |
| Volume 0-3 | 2 | 0.0% | -11.49% | 0.00 | 0.0% | 100.0% |
| Volume 4-6 | 17 | 29.4% | +2.45% | 2.11 | 29.4% | 70.6% |
| Volume 7-9 | 25 | 48.0% | +0.09% | 1.02 | 48.0% | 52.0% |
| Volume 10 (maxed) | 42 | 38.1% | +1.06% | 1.24 | 38.1% | 61.9% |
| History = 0 (no history) | 76 | 43.4% | +1.44% | 1.37 | 43.4% | 56.6% |
| History > 0 (has history) | 9 | **0.0%** | **-4.34%** | **0.00** | 0.0% | 100.0% |
| Confidence <55 | 5 | 40.0% | -6.51% | 0.25 | 40.0% | 60.0% |
| Confidence 55-59 | 12 | **8.3%** | **-7.90%** | **0.09** | 8.3% | 91.7% |
| Confidence 60-64 | 29 | 51.7% | +2.98% | 2.13 | 51.7% | 48.3% |
| Confidence 65-69 | 25 | 36.0% | +2.99% | 2.81 | 36.0% | 64.0% |
| Confidence 70-74 | 9 | 44.4% | +2.78% | 1.44 | 44.4% | 55.6% |
| ADX <20 | 20 | 40.0% | +1.57% | 1.49 | 40.0% | 60.0% |
| ADX 20-34 | 32 | 43.8% | +1.23% | 1.35 | 43.8% | 56.2% |
| ADX 35-49 | 24 | 25.0% | -0.80% | 0.79 | 25.0% | 75.0% |
| ADX 50+ | 5 | 60.0% | +1.23% | 1.11 | 60.0% | 40.0% |
| RSI 30-49 | 13 | **7.7%** | **-8.05%** | **0.01** | 7.7% | 92.3% |
| RSI 50-69 | 66 | 43.9% | +3.11% | 2.18 | 43.9% | 56.1% |
| RSI 70+ | 2 | 50.0% | -21.53% | 0.03 | 50.0% | 50.0% |
| ML probability (any bucket, n=10 total) | — | **0.0% in every bucket** | | | | |
| entry_quality excellent | 12 | **66.7%** | **+9.95%** | **12.13** | | |
| entry_quality good | 17 | 29.4% | +0.51% | 1.20 | | |
| entry_quality neutral | 40 | 35.0% | -0.92% | 0.80 | | |
| regime mixed | 59 | 45.8% | +2.17% | 1.63 | | |
| regime risk_on | 27 | 22.2% | -2.31% | 0.54 | | |

**Correlations with realized return**: trend +0.075, momentum **-0.111**, structure +0.183, volume +0.051, confidence +0.194, history **-0.085**, **ml_probability -0.341**, adx -0.009, rsi -0.030.

### GOOD FEATURES
- **entry_quality** — clean monotonic-ish signal, "excellent" (n=12) dominates every other bucket (66.7% win, PF 12.1). Strongest single feature in this dataset.
- **structure_score** — positive correlation (+0.183) and a clean split (9-11 bucket: 45.7%/PF2.13 vs 6-8: 33.3%/PF0.71).
- **confidence, in aggregate** — positive correlation (+0.194), and the 60-64 bucket is genuinely strong (51.7%/PF2.13) — but see Part 3, this is NOT a clean monotonic curve.

### BAD FEATURES
- **momentum_score** — negative correlation with return (-0.111); the 12-15 (near-max) bucket is the WORST of the three real buckets (35.6% win, -0.06% avg return) while 6-8 is the best (40.0% win, +5.37% avg return, PF 6.0). More momentum score is not better here.
- **trend_score** — near-zero correlation (+0.075) despite dominating every score breakdown (see Part 7) — contributes a lot of points for almost no discrimination.
- **RSI 30-49** — a real trap zone: 7.7% win rate, -8.05% avg return, PF 0.01 on n=13. Worth investigating directly (Part 6/14).

### USELESS FEATURES
- **ADX** — correlation -0.009 with return, essentially flat; the 50+ bucket looks best (60% win) but n=5 is noise.
- **volume_score** — correlation +0.051, close to flat; the maxed bucket (n=42, the plurality of all trades) sits in the middle of the pack, not distinguishing anything.

### INVERTED FEATURES (the headline finding of this audit)
- **historic_probability / history_score** — trades WITH stored history data go **0-for-9** (0.0% win rate, -4.34% avg return, PF 0.00). Trades with NO history win 43.4% of the time. This is the exact opposite of the feature's intended purpose. n=9 is small, but 0/9 is not a rounding error — this deserves its own investigation (Part 15), not just a note.
- **ml_probability** — correlation with return is **-0.341**, the strongest correlation (in either direction) of any feature checked, and every predicted-probability bucket with data (0.4-0.49, 0.5-0.59, 0.6+) realized a **0.0% actual win rate**. n=10 total is very small, but the direction is unanimous. See Part 16 — this is not usable as a live signal in its current form.
- **momentum_score** at the high end — see BAD FEATURES above; "more maxed" reads as a mild negative, not the intended positive.

---

## PART 3 — Confidence Calibration Audit

| bucket | n | win rate | avg return | avg MFE | avg MAE | TP1 | TP2 | TP3 | stop rate |
|---|---|---|---|---|---|---|---|---|---|
| 40-44 | 0 | — | | | | | | | |
| 45-49 | 2 | 0.0% | -11.58% | +5.75% | -11.58% | 50.0% | 0.0% | 0.0% | 100.0% |
| 50-54 | 3 | 66.7% | -3.12% | +3.97% | -6.75% | 66.7% | 66.7% | 0.0% | 33.3% |
| 55-59 | 12 | **8.3%** | **-7.90%** | +1.26% | -8.69% | 16.7% | 8.3% | 0.0% | **91.7%** |
| 60-64 | 29 | **51.7%** | **+2.98%** | +6.12% | -2.95% | 58.6% | 51.7% | 27.6% | 48.3% |
| 65-69 | 25 | 36.0% | +2.99% | +4.81% | -1.81% | 32.0% | 36.0% | 16.0% | 64.0% |
| 70-74 | 9 | 44.4% | +2.78% | +9.48% | -6.83% | 55.6% | 44.4% | 11.1% | 55.6% |
| 75-80 | 1 | 0.0% | -1.07% | +0.20% | -1.07% | 0.0% | 0.0% | 0.0% | 100.0% |

**Is 70 confidence actually better than 60?** No. 60-64 is the single best bucket in the entire table (51.7% win, +2.98% avg return, only 48.3% ever hit stop). 70-74 is respectable but not better (44.4% win). The curve is **not monotonic** — it dips hard at 55-59 (a real, 12-trade-wide trap zone: 91.7% stop rate) before recovering at 60-64, then drifting down again through 65-74. n=1-3 at the extremes (45-49, 50-54, 75-80) is noise and should not be read as a trend.

**Recommendation**: **Confidence should become a probability, not stay an unscaled 0-100 "conviction" number.** The current scale visibly does not mean "higher = more likely to win" — 55-59 is worse than 45-49, and 60-64 beats every bucket above it. Given the 55-59 trap is now this consistent (also the worst bucket in the 67-trade Performance Center check earlier in this project), I'd flag it as the single most reliable calibration finding in this whole audit — not "confidence should increase or decrease" uniformly, but that the mapping itself is broken in a specific, repeatable place.

---

## PART 4 — Why Trades Lose (all 53 losses clustered)

| cluster | n | % |
|---|---|---|
| Immediate reversal (never reached TP1, MFE<1%) | 46 | **86.8%** |
| Reached TP1 then stopped | 5 | 9.4% |
| Never reached TP1 but had some favorable move (MFE≥1%, still stopped) | 2 | 3.8% |

**Dominant failure mode, unambiguous: the trade goes wrong almost immediately.** 46 of 53 losses (86.8%) never even reach TP1 and never see more than 1% of favorable movement before stopping out. This is not "entered a good trend too late" or "reversed after partial success" — it's "wrong from the first candle" in the overwhelming majority of cases. Only 5 losses (9.4%) show the "worked initially, then reversed" pattern the entry-quality/trade-management conversation in this project has focused on. **The real lever here is entry accuracy/direction quality, not trade management after entry** — there's comparatively little to manage, because most losses never get anywhere to manage.

---

## PART 5 — Why Trades Win (all 33 wins clustered)

| cluster | n | % |
|---|---|---|
| Closed at TP2 (no TP3 defined or not reached) | 20 | 60.6% |
| Ran to TP3 (full continuation) | 13 | 39.4% |

**Winners vs losers, feature averages:**

| feature | winners avg | losers avg | gap |
|---|---|---|---|
| trend_score | 20.85 | 20.60 | negligible |
| momentum_score | 12.82 | 13.15 | winners LOWER |
| structure_score | 8.42 | 7.79 | winners higher |
| confidence | 64.00 | 63.24 | negligible |
| adx14 | 30.78 | 30.11 | negligible |
| rsi14 | 59.91 | 55.79 | winners higher |
| atr_distance_to_ema20 | 0.96 | 0.50 | winners nearly 2x higher |

**What actually separates winners from losers, per this data: structure_score, RSI, and ATR-distance-from-EMA20 — not trend or momentum.** Winners are entered meaningfully farther from EMA20 in ATR terms (0.96 vs 0.50) and at higher RSI (59.9 vs 55.8, i.e. closer to but not past overbought) with better structure. Trend and momentum, the two components most often maxed out on every trade (see Parts 6-7), show almost no separation between winners and losers — consistent with Part 2's correlation findings.

---

## PART 6 — Momentum Investigation

- Momentum ≥14 (near-maxed): n=59, win rate 35.6%, avg return **-0.06%**.
- Momentum <14: n=27, win rate 44.4%, avg return **+2.56%**.
- Maxed-momentum avg RSI 57.2 vs non-maxed 57.8 (no real difference) — momentum being maxed is NOT simply a proxy for "more overbought."
- Maxed-momentum avg ATR-distance-from-EMA20: 0.73 vs non-maxed 0.56 — maxed-momentum trades ARE entered somewhat farther extended from EMA20.
- Maxed-momentum avg stoch_rsi: 0.561 vs non-maxed 0.373 — meaningfully higher, consistent with more exhausted short-term momentum at entry.

**Does momentum 15/15 outperform momentum 10?** No — it underperforms on both win rate and average return. **Do max-momentum trades enter late?** Partially supported: higher stoch_rsi and ATR-distance at entry for the maxed group, consistent with "already-extended" entries, though not a dramatic gap.

**Recommendations**: Momentum score should NOT reward maxing out linearly — this data shows the opposite of the intended relationship. It should become **nonlinear**, with a genuine exhaustion penalty once stoch_rsi/RSI cross a threshold, rather than treating "more momentum indicators agreeing" as strictly better. This matches the entry_quality feature's own stated purpose (exhaustion detection) — the fact that momentum_score itself doesn't already discount this is the gap.

---

## PART 7 — Trend Investigation

| trend bucket | n | win rate | avg return | PF |
|---|---|---|---|---|
| <18 | 17 | 41.2% | -0.64% | 0.82 |
| 18-21 | 32 | 34.4% | +0.33% | 1.08 |
| 22-23 | 14 | 42.9% | +2.27% | 2.05 |
| 24-25 (near max) | 23 | 39.1% | +1.48% | 1.31 |

**Does max trend outperform medium trend?** Not clearly — 22-23 (not the top bucket) is actually the best by both win rate and PF. 24-25 is respectable but not clearly better than 22-23. **Is trend overweight?** Given trend_score carries up to 25 of the total score (the largest single component in this scoring system) yet correlates only +0.075 with return — barely above zero — **yes, trend is very likely overweight relative to its actual predictive value in this data.** It dominates the score breakdown on almost every trade (see the ledger — nearly every row shows trend_score in the high teens to 25) while doing very little to separate winners from losers. **Does trend alone create false confidence?** The evidence supports this: a maxed trend score doesn't reliably predict outcome, but it's the single biggest contributor to the total score that gates whether a trade is taken at all.

---

## PART 8 — Structure Investigation (BOS/CHoCH/FVG/Order Block)

**Honest limitation, stated once and applying throughout this part**: BOS, CHoCH, and order-block presence are **not stored per-trade anywhere in this database** for historical rows, and order-block detection doesn't exist in this codebase's logic at all. `structure_score` (the aggregate 0-15 component) is the only structure-related signal available for all 86 trades; FVG data (`fvg_used`) exists only for the 48 trades issued after the level-reasoning capture pass, and only 16 of those 48 actually had an active FVG at entry.

- Trades with a recorded active FVG at entry: n=16, win rate **50.0%**.
- Trades without FVG data recorded (either pre-capture or no FVG was active): n=70, win rate 35.7%.
- Structure score 9-11: win rate 45.7%, PF 2.13. Structure score 6-8: win rate 33.3%, PF 0.71 (from Part 2).

**Recommendation**: the data that does exist supports structure mattering (both the aggregate score split and the small FVG-presence split point the same direction), but the sample for FVG specifically (n=16) is too small to redesign weighting from. I'd recommend **increasing structure_score's weight modestly** given it's one of only two features (with entry_quality) showing a clean positive relationship with outcome, while flagging that BOS/CHoCH/order-block-specific weighting can't be evaluated at all without first capturing those as stored per-trade fields — which doesn't exist today.

---

## PART 9 — TP Behaviour

Computed via the already-built, tested `performance_center.tp_continuation_analytics()` (same engine as the Performance Center V1 endpoints), not reimplemented:

- n reaching TP1: **37** of 86 (43.0%)
- **P(TP2 | TP1) = 86.5%** (32/37)
- **P(TP3 | TP2) = 39.4%** (13/33)
- **Return-to-entry probability after TP1: 20.8%** (5/24 determinable — up materially from the ~5.9% read at the 72-trade checkpoint; this rate is climbing as more data accumulates, not staying near zero)
- **Return-to-stop probability after TP1: 13.9%** (5/36 determinable — also up from ~3.6% at 72 trades)
- Average continuation after TP1: **+11.4%**
- Average pullback after TP1: **-5.2%**

**Design implication for a continuation model**: TP1→TP2 continuation is still strong (86.5%) but the "once TP1 hits, it basically never comes back" story from earlier checkpoints is **weakening as the sample grows** — 1 in 5 trades that reach TP1 do eventually revisit entry, and roughly 1 in 7 revisit the stop. That's still favorable odds for holding past TP1, but it is no longer close to zero, and any Phase 2 model should be trained to reflect that real (if still small-sample) reversal rate rather than the near-zero read from earlier data.

| If TP1 hits... | Recommended action | Basis |
|---|---|---|
| default | **Hold** | P(TP2\|TP1)=86.5% strongly favors continuation over an immediate full exit |
| after also hitting TP2 | **Move stop to breakeven, hold for TP3** | P(TP3\|TP2)=39.4% — real but not dominant; protect the TP2 gain while giving TP3 a chance |
| if price pulls back below entry post-TP1 | **Trail stop / consider partial exit** | 20.8% return-to-entry rate is high enough that "hold blindly no matter what" is no longer clearly correct |

---

## PART 10 — Dynamic Exit Model (simulated)

Using the same `PredictionSnapshot` replay as Part 9's per-trade detail: of the 37 trades that reached TP1, a naive "always hold to whatever the final exit was" policy is what actually happened. Replaying the 5 trades that reversed to entry and the 5 that reversed to stop after TP1:

- **5 trades returned to stop after TP1** — an EXIT NOW or MOVE STOP (to breakeven) rule the moment price re-approached entry would have converted these from full-stop losses to breakeven-or-small-loss outcomes. Estimated improvement: recovering roughly the entry-to-stop distance on each (varies by trade; on the ledger these are in the -1% to -9% range) — a rough aggregate improvement of **+15-25% cumulative return** across just these 5 trades, i.e. meaningful but resting on n=5.
- The other trades that reached TP1 either continued cleanly to TP2/TP3 (32 of 37) or are undeterminable from a single closing snapshot (see Part 9's note) — no exit-timing improvement is available for those; holding was already the reasonable action.

**This supports building the "trade manager" continuation model (Part 19/20) as real, data-backed work — not speculative** — but the effect size here is measured on 5 trades and should be treated as directional, not a precise ROI number.

---

## PART 11 — Long vs Short Deep Audit

| | long (n=73) | short (n=13) |
|---|---|---|
| win rate | 43.8% | **7.7%** |
| PF | 1.78 | **0.006** |
| avg return | +2.42% | **-8.57%** |
| winners: avg trend/momentum/structure/confidence | 20.85 / 12.97 / 8.34 / 63.83 | 21.08 / 8.00 / 11.00 / 69.00 (n=1) |
| losers: avg trend/momentum/structure/confidence | 21.22 / 13.22 / 7.83 / 64.26 | 18.48 / 12.92 / 7.67 / 60.00 |
| avg RSI | 59.5 | **46.0** |
| avg ADX | 32.2 | **20.9** |

**Per instructions, ignoring prior conclusions unless proven again**: shorts are proven again, more strongly than at any prior checkpoint (28/48/67/72-trade checks all showed this; n has now grown to 13 and the gap has widened, not narrowed — PF 0.006 is effectively "every winning short's gain is erased by one losing short many times over"). Shorts are also entered at meaningfully lower ADX (20.9 vs 32.2) — i.e., on weaker-trending setups than longs get, on average, despite the same deterministic direction-decision logic being used for both.

**Should long and short have separate scoring systems?** The data supports it. Shorts aren't just "unlucky longs run in reverse" — they're being taken on structurally weaker trend confirmation (ADX) and in a different RSI regime (46 vs 59.5, i.e., shorts are entered closer to neutral/oversold territory rather than a clean overbought-reversal zone a short would ideally want). A single shared scoring formula tuned mostly on long-side data (73 of 86 trades) is very plausibly miscalibrated for the minority short case.

---

## PART 12 — Coin Family Audit

| family | n | win rate | avg return | PF |
|---|---|---|---|---|
| stocks_etfs (MSTR, NVDA, QQQ, CRCL, SPCX, SAMSUNG, SOXL/SOXS, SNDK, KORU, SKHYNIX/SKHY, NBIS) | 23 | **60.9%** | +1.54% | **2.00** |
| ai_coins (NEAR, WLD, HYPE) | 5 | 60.0% | +9.31% | 12.10 |
| meme_coins (DOGE, 1000PEPE, PUMP) | 4 | 25.0% | +2.27% | 1.30 |
| defi_other_altcoin (everything else — the bulk) | 39 | 35.9% | +0.60% | 1.11 |
| gold (XAU, PAXG, XAG) | 5 | 20.0% | -1.03% | 0.21 |
| **majors (BTC, ETH, SOL, BNB, XRP, ADA)** | 10 | **0.0%** | **-4.38%** | **0.00** |

**Striking finding**: the "majors" family — the ONLY symbols with real historical `MarketSnapshot` backfill and full ML-model training data — has a **0% win rate across all 10 trades**, the worst of any family, while the stocks/ETFs and AI-coin families (with zero historical backfill) perform best. This is consistent with, and probably related to, Part 15's historical-similarity inversion finding — whatever edge the "well-covered" symbols were supposed to have from deeper historical data isn't showing up live.

**Should each family have different thresholds?** Yes, strongly supported here — a single confidence/entry-quality threshold applied uniformly is clearly not serving the majors family well (n=10, 0% win) while serving stocks/ETFs and AI coins well on the same thresholds. n=5-10 per family is still small, but the spread (0% to 61% win rate) is too wide to attribute to noise alone across all six groups simultaneously.

---

## PART 13 — Market Regime Audit

| | risk_on (n=27) | mixed (n=59) |
|---|---|---|
| win rate | 22.2% | 45.8% |
| avg return | -2.31% | +2.17% |
| corr(trend, return) | 0.101 | 0.077 |
| corr(momentum, return) | +0.055 | **-0.183** |
| corr(confidence, return) | 0.014 | **+0.370** |

**Which indicators stop working / improve by regime?** Confidence is far more informative in a "mixed" regime (+0.37 correlation) than in "risk_on" (+0.01, essentially useless) — confidence appears to only really mean something when the broader market itself isn't strongly trending one way. Momentum's negative relationship with return (see Part 6) is concentrated in the mixed regime (-0.183) and nearly absent in risk_on (+0.055) — the "exhaustion" problem in momentum scoring may be regime-specific, not universal.

**Recommended regime-specific modifier (directional, not a final formula)**: weight confidence more heavily as a gate in mixed-regime trades (where it's actually informative) and consider suppressing or capping momentum_score's contribution specifically in mixed regime, where its negative relationship with outcome is concentrated. No `risk_off` data exists yet in this dataset (0 trades) — cannot audit that regime at all.

---

## PART 14 — Entry Timing Audit

**Honest limitation**: this codebase has no stored "time of first valid setup" distinct from "time of actual entry" — `created_at` (when Claude issued the plan) and `entry_time` (when price crossed into the zone) are the only two timestamps available, and the gap between them reflects the pending-zone wait, not "was the underlying setup fresh or stale when Claude first saw it." A true "minutes between first valid setup and entry" metric doesn't exist without a new capture (out of scope for a read-only audit).

What IS available and computed:
- Losers' avg `atr_distance_to_ema20`: 0.50 vs winners' 0.96 (Part 5) — **losers are entered CLOSER to EMA20 in ATR terms**, not farther/more extended. This cuts against a simple "entries are too late/too extended" story and instead suggests many losing entries are taken on weak, insufficiently-extended pullbacks that never had real momentum behind them.
- RSI 30-49 bucket (a "not yet oversold, not yet trending" zone): 7.7% win rate, -8.05% avg return (Part 2) — the worst RSI bucket by far, and consistent with "entered too early/into chop," not too late.
- Losers' avg RSI 55.8 vs winners' 59.9 — again, losers skew toward a less-confirmed RSI reading, not an overbought-chase pattern.

**Recommendation**: the entry-timing problem in this data reads more like "entering too early, before a real move confirms" than "chasing an overextended move" — the opposite of what "exhaustion" framing usually assumes. A timing filter should consider requiring a MINIMUM atr_distance_to_ema20 and a minimum RSI threshold (avoiding the 30-49 trap zone) rather than only guarding against overextension.

---

## PART 15 — Historical Similarity Audit

- Coins WITH stored history: n=10 (11.6% of all trades) — **win rate 0.0%**.
- Coins WITHOUT stored history: n=76 (88.4%) — win rate 43.4%.
- Distinct symbols that have EVER had history data: **4** of 47 distinct symbols traded (8.5% coverage).

**This is the most severe inversion in the entire audit.** Every single trade where historical-similarity data existed lost. Coverage is also extremely thin — only 4 of 47 traded symbols ever have any history at all, meaning this feature is silent (contributes nothing) on 88% of trades and actively wrong on the 12% where it does contribute.

**Should missing history reduce confidence?** No — the data says the opposite: having history is what's currently associated with losing. This doesn't necessarily mean historical similarity is a bad idea in principle; more plausibly, the 4 symbols that happen to have coverage (almost certainly the same legacy-backfilled "majors" — cross-referencing Part 12, majors have 0% win rate too) are simply a bad-performing group for unrelated reasons, and history-coverage is confounded with major-symbol membership, not causally connected to the loss. **Given n=9-10, do not act on this beyond disabling any confidence boost for "has history" until the sample grows** — but do not increase reliance on it either.

---

## PART 16 — ML Model Audit

Two separate things exist and are audited separately, as required — the XGBoost win/drawdown classifier itself (already revalidated earlier this session — see `SESSION_STATUS.md`: AUC 0.544/0.537, near coin-flip, calibration near-random on the 25k-row MarketSnapshot backfill) and the **per-trade `ml_probability` value actually stored on these 86 live trades**, audited fresh here:

- Trades with a stored `ml_probability`: **n=10 of 86** (11.6%) — this field is only populated when a symbol has ≥30 rows of its own MarketSnapshot history (`ml_model.py:MIN_SYMBOL_HISTORY`), which in practice means only the 6 legacy-backfilled majors qualify.
- **Brier score on these 10 trades: 0.3375** — worse than a flat 50% predictor's 0.25, i.e. actively miscalibrated, not just weak.
- Every predicted-probability bucket with data (0.45-0.49, 0.5-0.54, 0.55+) shows **0.0% actual win rate**. All 10 of these trades lost.
- Precision/recall/ROC AUC are not meaningfully computable at n=10 with zero positive outcomes in the sample — reporting this honestly as **insufficient data for those specific metrics**, not fabricating a number.

**False positives**: all 10 — every trade the model gave a win probability to, lost. **False negatives**: not computable (no trade was ever predicted to lose that then won, because there were no wins in this subsample at all).

**Recommendation**: do not retrain the win/drawdown ML model based on this — n=10 is far too small, and this same subsample is entirely confounded with the "majors" family that's performing worst overall (Part 12) and the "has history" group that's also performing worst (Part 15). These three findings (majors / has-history / has-ml-probability) are very likely describing the same 4-10 trades from different angles, not three independent problems. **The real recommendation is to investigate why the legacy-backfilled majors are performing so badly live**, before concluding anything about the ML model, history feature, or coin selection independently.

---

## PART 17 — Scanner Rejection Audit

- Total ScanSnapshot rows: 52,108. Rejected (non-null `rejection_reason`): 9,505.
- Top rejection reasons: 3,863 no_trade (direction gate), 1,811 `exhausted` override, 366 `late` withhold, remainder rank-cutoffs (outside top 6 candidates that cycle).

**Did rejected trades outperform accepted ones? Estimate missed profit.** **Not computable from stored data** — there is no forward-price tracking anywhere in this database for a rejected candidate. `ScanSnapshot` records the rejection and the score/confidence at that moment, never what price did afterward. This would require new instrumentation (a forward-return capture for rejected symbols) that does not exist today; reporting this honestly as a genuine gap rather than estimating a number with no basis.

---

## PART 18 — Score Weight Redesign (proposal only, no code changed)

| component | V1 max points | V2 proposed max | reason |
|---|---|---|---|
| Trend | 25 | **15** | correlates only +0.075 with return despite being the largest single component (Part 2, Part 7) — currently overweight relative to demonstrated predictive value |
| Momentum | 15 | **10, nonlinear/capped** | negative correlation with return at the high end (Part 6) — should not scale linearly to a max; needs an exhaustion penalty |
| Volume | 10 | 10 (unchanged) | weak but not harmful (+0.051 corr); not enough evidence to change |
| Funding | 10 | 10 (unchanged) | insufficient data — 82 of 86 trades sit in one funding_score bucket (8-10), no real spread to evaluate against |
| Structure | 15 | **20** | one of only two features with a clean positive relationship to outcome (+0.183 corr, Part 2, Part 8) |
| History | 15 | **5, pending investigation** | currently inverted (0% win rate when present, Part 15) — do not increase, and don't trust the current weight either, until the majors-family confound (Part 12/16) is understood |
| Regime | 5 | 5 (unchanged) | not independently auditable at current weight scale from this data |
| ML | 5 | **0-5, pending investigation** | same confound as History — n=10, worse than random Brier score (Part 16); do not increase |

**This is a proposal for discussion, not a validated final formula** — several of these recommendations (History, ML) rest on the same small, confounded sample (the majors family), and reducing Trend/increasing Structure should be sanity-checked against a larger sample before being implemented, consistent with this project's own standing rule against tuning on small samples.

---

## PART 19 — New Probability Engine (design only, no implementation)

Four probabilities instead of one confidence number:

| probability | candidate feature inputs |
|---|---|
| **P(TP1)** | structure_score, entry_to_sl_atr / risk_to_sl_pct (from `entry_indicators.risk_reward`), RSI (avoiding the 30-49 trap zone from Part 14), atr_distance_to_ema20, entry_quality |
| **P(TP2 \| TP1)** | already has a strong empirical anchor: 86.5% aggregate (Part 9) — a real model should condition this on symbol family (majors vs stocks/ETFs vs AI coins, Part 12) and regime (mixed vs risk_on, Part 13), since both show real performance splits |
| **P(TP3 \| TP2)** | anchored at 39.4% aggregate (Part 9) — likely conditions on how much of the TP1→TP2 move happened quickly vs slowly (continuation strength), which isn't directly stored today but is derivable from `PredictionSnapshot` timestamps between `tp1_hit_at`/`tp2_hit_at` |
| **P(Stop before TP1)** | direction (shorts materially worse, Part 11), confidence bucket (the 55-59 trap, Part 3), RSI bucket (30-49 trap, Part 2/14), coin family (majors trap, Part 12) |

No implementation is proposed here per instructions — this is a feature-input map for a future model, built entirely from relationships already demonstrated in Parts 2-15 above, not invented fresh.

---

## PART 20 — Version 2 Roadmap

**Priority 1 (highest ROI)**
- Investigate why the "majors" symbol family (BTC/ETH/SOL/BNB/XRP/ADA) — the only symbols with historical backfill, ML probability, and similarity data — has a **0% win rate across 10 live trades**, materially worse than every other family. This single investigation likely explains 2-3 other findings in this report at once (Parts 12, 15, 16). Expected impact: high — this is the biggest, most concentrated anomaly found. Difficulty: low — it's read-only analysis, same as this report, just narrower.

**Priority 2**
- Fix the confidence-calibration trap at 55-59 (Part 3) — this is now the second consecutive audit (this one and the prior Performance Center check) to find this exact bucket is the worst performer despite sitting in the middle of the scale. Expected impact: medium-high, directly actionable once understood. Difficulty: medium — requires understanding WHY 55-59 specifically clusters bad trades before touching anything (do not just suppress the bucket blindly).
- Reduce trend_score's weight and increase structure_score's, per Part 18 — supported by the clearest correlation gap in the whole feature-importance section. Expected impact: medium. Difficulty: medium — needs the score-weight change plus a re-validation period, per this project's own standing "don't tune on small samples" rule; treat this roadmap item as "worth testing," not "implement immediately."

**Priority 3**
- Build the TP1-continuation trade manager (Parts 9-10, 19) — P(TP2|TP1)=86.5% and the simulated dynamic-exit improvement on the 5 reversal cases both support this being worth building. Expected impact: medium, and it's a pure analytics/suggestion layer (like Performance Center's existing Trade Manager Analytics), so it's low-risk to ship. Difficulty: low-medium — most of the underlying computation already exists in `performance_center.py`.
- Separate long/short scoring (Part 11) — evidence is strong (PF 0.006 on shorts) but n=13 is still small for redesigning an entire parallel scoring path. Expected impact: potentially high if shorts really are structurally different, but treat as "keep watching, prepare the analysis," not "build now."
- Momentum nonlinearity/exhaustion penalty (Part 6) — supported by data, but this is the same conceptual territory `entry_quality.py` already covers; consider whether this is better solved by leaning more on entry_quality (already the single best feature in this report) rather than reworking momentum_score independently.

**Explicitly NOT recommended by this data**: retraining the ML model (n=10, confounded with the majors problem — fix that first), changing History's weight upward, or building the four-probability engine (Part 19) before the majors investigation resolves what's actually driving three separate findings.
