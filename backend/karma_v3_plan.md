# Karma V3.0 — Implementation Plan from Evidence (Parts 1–12)

Generated 2026-09-26 19:20 UTC from `crypto_terminal.db`, read-only. Live: 982 plans, **118 closed (46W/72L)**, win rate 39.0%, PF 1.62, avg 2.38%, median -1.59%. **No code, DB row, prompt, weight or model was changed, and no commit was made.** Part 12 contains *proposed* code only for files that are not frozen; nothing touching scoring.py / decision.py / market_regime.py / prompt / ML is proposed, because the evidence below does not support it. Labels: CONFIRMED (p<.01, n≥30) · LIKELY (p<.05) · POSSIBLE (p<.15) · NOT SUPPORTED (adequate n, p≥.15) · INSUFFICIENT DATA. Chronological validation = fit on the earlier half of trades (by entry time, n≈59), test on the later half; all p-values are optimistic because trades cluster in time.

## SECTION 0 — VERIFICATION OF THE RECOMMENDATION YOU PASTED (against the DB)

| Claim in the pasted text | What the DB says | Verdict |
|---|---|---|
| 118 closed, 45W/71L, PF 1.70, avg +2.58%, median −1.59% | 118 closed, 46W/72L, PF 1.62, avg 2.38%, median -1.59% (moves as new trades close) | Consistent (slightly older snapshot) |
| After TP1: reached TP2 46/52 (88%) | 46/54 (85.2%) reached TP2 | TRUE |
| After TP1: reached TP3 14/52 (27%) | 14/54 (25.9%) reached TP3 (= 30.4% of TP2 reachers) | TRUE |
| 'Returned to stop: 5 trades' | 9 of 54 TP1-reachers ended as losses (16.7%) | Understated (9, not 5) |
| Calibration example: 71% → 56% ± 8%; 64% → 44% ± 9%; 58% → 28% ± 10% | Observed win rate: 70–74 bucket = 33.3% (n=12); 60–64 = 46.2% (n=39); 55–59 = 31.8% (n=22). Higher confidence does NOT map to higher win rate: 58→~32%, 64→~46%, 71→~33% | FALSE — the example mapping is monotone and invented; the data is flat/non-monotone |
| Expected Outcome card: TP1 68%, TP2 49%, TP3 17%, Stop 32% | Unconditional (all 118 entered trades): TP1 45.8%, TP2 39.8%, TP3 11.9%, Stop 61.0% | FALSE — TP1 is ~46%, not 68%; stops are ~61%, not 32% |
| Short gates: Excellent entry + reliability ≥60 + calibrated p ≥55% | Shorts that are 'excellent': 4 of 20; shorts with prior-trades reliability ≥60: 0; trades (any direction) with reliability ≥60: 0 of 118; highest observed win rate in ANY confidence bucket ≥50: 57.1% → calibrated p ≥55% is met by essentially nothing | As written, the gates = disable shorts (no evidence that is warranted, see Part 4) |
| Trend dominates bad trades | Trend ≥22 is present in 37.5% of losses AND 34.8% of wins; trend has no relation to outcome (OR 0.89, p=0.8455). It is a near-universal gate, so it cannot 'dominate' losers more than winners | Not supported (trend is uninformative, not harmful) |
| Short strategy is fundamentally underperforming — Very High | Headline 15.0% win (n=20), but 11/20 shorts exited inside scanner downtime and all lost; uptime-only shorts win 33.3% (n=9) vs longs 36.8% | Overstated — confounded with downtime; POSSIBLE at most |
| Trade management is better than entry prediction — Very High | Holding to the outermost target beats exiting at TP1/TP2 (Part 11: CONFIRMED arithmetic). But every proposed *new* management rule is unproven (Part 5/11); the path-replay gains are largely fill-idealisation (previous report §9) | Half-true: 'hold' is validated, 'smarter management' is not |

Bottom line of this check: the *direction* of two priorities is right (calibration display; do not exit at TP1), but three numbers in the pasted text (the calibration mapping, the Expected-Outcome card, the short gates) are not supported by — and in places contradicted by — the database.

## SECTION PART 1 — ROOT CAUSE ANALYSIS — ONE PRIMARY VERDICT PER CLOSED TRADE

| Verdict | n | Win rate | Avg ret% | Median ret% | Total PnL contribution pp | Top 5 symbols |
|---|---|---|---|---|---|---|
| Infrastructure Failure | 8 | 0.0% | -21.33 | -20.63 | -170.6 | DOGEUSDT×2, ETHUSDT×1, ZECUSDT×1, MOVRUSDT×1, TRUMPUSDT×1 |
| Scanner Gap | 24 | 0.0% | -6.33 | -4.73 | -152.0 | DRAMUSDT×2, SNXXUSDT×2, SOLUSDT×2, BEATUSDT×1, BICOUSDT×1 |
| Structure Failure | 19 | 0.0% | -2.93 | -2.21 | -55.6 | ETHUSDT×3, SNDKUSDT×1, EWYUSDT×1, HYPEUSDT×1, SOLUSDT×1 |
| Liquidity / Volatility Failure | 3 | 0.0% | -8.54 | -8.62 | -25.6 | ACEUSDT×1, HEMIUSDT×1, LABUSDT×1 |
| Trend Failure | 6 | 0.0% | -3.21 | -2.64 | -19.2 | DRAMUSDT×1, DOGEUSDT×1, CYSUSDT×1, XAGUSDT×1, BNBUSDT×1 |
| Bad Entry | 7 | 0.0% | -2.13 | -2.04 | -14.9 | MSTRUSDT×2, RKLBUSDT×1, SOLUSDT×1, HYPEUSDT×1, BNBUSDT×1 |
| TP Management Failure | 3 | 0.0% | -2.22 | -1.57 | -6.7 | ENAUSDT×1, SKHYUSDT×1, CRCLUSDT×1 |
| Momentum Exhaustion | 2 | 0.0% | -3.17 | -3.17 | -6.3 | FLOCKUSDT×1, SUIUSDT×1 |
| Unknown | 3 | 100.0% | 23.96 | 19.04 | 71.9 | BTWUSDT×1, APRUSDT×1, PUMPUSDT×1 |
| Perfect Trade | 43 | 100.0% | 15.35 | 7.07 | 659.9 | CRCLUSDT×2, SKHYUSDT×2, NVDAUSDT×2, SOXSUSDT×2, SAMSUNGUSDT×2 |

**Assignment rules (first match wins; rules are mine and listed so they can be audited):** wins: Perfect Trade = MAE ≥ −2%; Good Entry Bad Exit = Trade-Truth verdict; else Unknown. Losses, in this priority: Infrastructure Failure (stop slippage ≤ −5%) → Scanner Gap (exit inside a monitoring gap) → TP Management Failure (TP1 had been reached) → Good Entry Early Stop (MFE ≥80% of TP1 distance, then stopped) → Liquidity/Volatility (thin book, or top-tercile ATR% with ≥2% slippage) → Momentum Exhaustion (RSI≥70 / MFI>80 / StochRSI>0.9 / >2.5 ATR from EMA20) → Structure Failure (structure_score<9) → Trend Failure (trend_score<18 or against BTC trend) → Bad Entry (immediate reversal not otherwise explained) → Unknown. **Important caveat:** because the priority order decides who gets the label, and 'structure<9' is true of ~62% of ALL trades, the *Structure Failure* count reflects that base rate as much as causation — see the base-rate column below. Verdict = classification of what the stored fields show, not proof of cause.
| Trait behind the label | Share of ALL closed trades with it | Share of LOSSES with it | Share of WINS with it | Lift (loss share ÷ win share) |
|---|---|---|---|---|
| Structure Failure | 61.9% | 63.9% | 58.7% | 1.09 |
| Trend Failure | 49.2% | 38.9% | 65.2% | 0.60 |
| Momentum Exhaustion | 22.9% | 13.9% | 37.0% | 0.38 |
| Liquidity / Volatility Failure | 8.5% | 13.9% | 0.0% | inf (0 wins have it) |

**Read the lift column:** Trend Failure and Momentum Exhaustion traits are MORE common among winners than losers (lift < 1), so labelling a loss with them is descriptive, not causal; only Liquidity/Volatility (n=3 wins-free) leans toward losses and its n is tiny.
Open trades (24 open, 11 pending) are excluded from every statistic above and are analysed separately in Part 9. **Evidence:** the counts are facts (CONFIRMED); causal interpretation of any label is POSSIBLE at best. Infrastructure Failure + Scanner Gap together carry 71.5% of total loss magnitude.

## SECTION PART 2 — SCORING MODEL FROM EVIDENCE (MEASUREMENT; scoring.py UNTOUCHED)

| Component | Current weight range | n pass/fail | Win% pass / fail | OR | 95% CI | Fisher p | Info gain (bits) | AUC of pass-flag | Evidence | Ship now? |
|---|---|---|---|---|---|---|---|---|---|---|
| Trend | 0–25 | 43/75 | 37.2% / 40.0% | 0.89 | [0.41, 1.92] | 0.8455 | 0.0005 | 0.486 | NOT SUPPORTED | Wait — no evidence to change |
| Momentum | 0–15 | 86/32 | 39.5% / 37.5% | 1.09 | [0.47, 2.51] | 1.0 | 0.0002 | 0.508 | NOT SUPPORTED | Wait — no evidence to change |
| Volume | 0–10 | 66/52 | 43.9% / 32.7% | 1.61 | [0.76, 3.44] | 0.2559 | 0.0095 | 0.558 | NOT SUPPORTED | Wait — no evidence to change |
| Structure | 0–15 | 45/73 | 42.2% / 37.0% | 1.25 | [0.58, 2.66] | 0.6978 | 0.002 | 0.526 | NOT SUPPORTED | Wait — no evidence to change |
| Funding | 0–10 | 113/5 | 38.9% / 40.0% | 0.96 | [0.15, 5.96] | 1.0 | 0.0 | 0.499 | INSUFFICIENT DATA | Wait — no evidence to change |
| History | −15..+15 | 13/105 | 23.1% / 41.0% | 0.43 | [0.11, 1.66] | 0.2459 | 0.0101 | 0.463 | NOT SUPPORTED | Wait — no evidence to change |
| Regime (mixed) | −5..+5 | 84/34 | 44.0% / 26.5% | 2.19 | [0.91, 5.25] | 0.0964 | 0.0199 | 0.576 | POSSIBLE | Wait — no evidence to change |
| Risk penalty absent | −20..0 | 93/25 | 41.9% / 28.0% | 1.86 | [0.71, 4.88] | 0.252 | 0.0102 | 0.549 | NOT SUPPORTED | Wait — no evidence to change |
| Entry Quality excellent | n/a (not in score) | 19/82 | 52.6% / 36.6% | 1.93 | [0.7, 5.27] | 0.2067 | 0.0116 | 0.551 | NOT SUPPORTED | Wait — no evidence to change |
| EV > 0 (retro) | n/a (not in score) | 32/61 | 31.2% / 47.5% | 0.5 | [0.2, 1.23] | 0.1844 | 0.0181 | 0.425 | NOT SUPPORTED | Wait — no evidence to change |
| Reliability ≥ median (prior-trades) | n/a (not in score) | 59/59 | 33.9% / 44.1% | 0.65 | [0.31, 1.37] | 0.3454 | 0.0079 | 0.447 | NOT SUPPORTED | Wait — no evidence to change |
| Red flags = 0 | n/a (not in score) | 3/115 | 0.0% / 40.0% | 0.21 | [0.01, 4.23] | 0.2803 | 0.0184 | 0.479 | INSUFFICIENT DATA | Wait — no evidence to change |

Discrimination of the *current total score* on win/loss: AUC 0.487 (bootstrap 95% CI [0.384, 0.594]); 0.5 = no skill. Note range restriction: only trades that already passed the score/gate are observed, which attenuates every feature's apparent value.
**Interpretation:** the total score has AUC 0.487 against win/loss (CI includes 0.5; later-half AUC is below 0.5), i.e. it does not separate winners from losers in this sample (LIKELY no skill; range-restricted). That is a statement about the score as a *win/loss* ranker; it may still order *magnitudes* (Spearman above is also ~0).
**Proposed NEW weight table:**

| Component | Current | Proposed | Evidence | Confidence | Ship now or wait |
|---|---|---|---|---|---|
| Trend | 0–25 | unchanged | OR 0.89 p=0.8455 n=43/75 | NOT SUPPORTED | WAIT |
| Momentum | 0–15 | unchanged | OR 1.09 p=1.0 n=86/32 | NOT SUPPORTED | WAIT |
| Volume | 0–10 | unchanged | OR 1.61 p=0.2559 n=66/52 | NOT SUPPORTED | WAIT |
| Structure | 0–15 | unchanged | OR 1.25 p=0.6978 n=45/73 | NOT SUPPORTED | WAIT |
| Funding | 0–10 | unchanged | OR 0.96 p=1.0 n=113/5 | INSUFFICIENT DATA | WAIT |
| History | −15..+15 | unchanged | OR 0.43 p=0.2459 n=13/105 | NOT SUPPORTED | WAIT |
| Regime (mixed) | −5..+5 | unchanged | OR 2.19 p=0.0964 n=84/34 | POSSIBLE | WAIT |
| Risk penalty absent | −20..0 | unchanged | OR 1.86 p=0.252 n=93/25 | NOT SUPPORTED | WAIT |
| EV / Reliability / Entry Quality / Red flags | not in score | keep OUT of score | EV is anti-predictive of TP2/stop (rho −0.25, p≈0.02); reliability & EQ not significant | LIKELY (EV); NOT SUPPORTED (others) | WAIT (display-only) |

**Proposed weights: none change.** No component meets 'significant AND adequately sampled'. I will not fabricate a weight table (the earlier V2.1 attempt at invented weights was reverted for exactly this reason).
| Experiment (analytics only; NOT implemented) | AUC vs win/loss (n=118) | Bootstrap 95% CI | AUC 1st half / 2nd half | Spearman vs return | p |
|---|---|---|---|---|---|
| Current score | 0.487 | [0.371, 0.595] | 0.534 / 0.398 | -0.045 | 0.626 |
| Trend weight 25→18 | 0.489 | [0.378, 0.597] | 0.526 / 0.437 | -0.05 | 0.587 |
| Trend weight 25→15 | 0.49 | [0.383, 0.603] | 0.528 / 0.447 | -0.054 | 0.562 |
| Trend removed from score (gate only) | 0.487 | [0.385, 0.577] | 0.484 / 0.476 | -0.053 | 0.57 |
| Structure only | 0.526 | [0.438, 0.611] | 0.574 / 0.461 | 0.064 | 0.493 |
| Score − trend + 2×structure (trend as gate, structure emphasised) | 0.508 | [0.394, 0.624] | 0.546 / 0.477 | 0.006 | 0.949 |

| Is trend mandatory? (gate) | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | PF 1st / 2nd half |
|---|---|---|---|---|---|---|---|
| Trend gate: trend_score ≥ 0 | 118 | 39.0% | 30.7–48.0 | 2.38 | -1.59 | 1.62 | 1.15 / 2.13 |
| Trend gate: trend_score ≥ 18 | 92 | 39.1% | 29.8–49.3 | 3.10 | -1.59 | 1.87 | 1.33 / 2.50 |
| Trend gate: trend_score ≥ 20 | 66 | 36.4% | 25.8–48.4 | 3.10 | -1.88 | 1.81 | 1.41 / 2.28 |
| Trend gate: trend_score ≥ 22 | 43 | 37.2% | 24.4–52.1 | 1.26 | -1.77 | 1.34 | 1.97 / 0.45 |

**Answers:** *Trend mandatory?* Every published plan already has trend ≥12.8 (median 20.1); tightening the gate to ≥22 removes ~64% of trades with no PF gain in the later half → NOT SUPPORTED. *Trend weight 25→18 / 25→15?* the AUC differences are within the bootstrap CI (indistinguishable) → NOT SUPPORTED; *Trend gate + Structure?* structure adds nothing detectable (AUC CI spans 0.5). **Do not ship any trend/weight change**; all rows are in-sample and range-restricted.

## SECTION PART 3 — CONFIDENCE CALIBRATION V2

| Bucket | n | Mean raw conf | Observed win% | TP1% | TP2% | TP3% | Stop% | Expected return % | PF | 95% credible interval | Overconfidence pp |
|---|---|---|---|---|---|---|---|---|---|---|---|
| <45 | 0 |  |  |  |  |  |  |  |  |  |
| 45–49 | 3 | 46.7 | 0.0% | 33.3 | 0.0 | 0.0 | 100.0 | -10.17 | 0.00 | 1–60 | 46.7 |
| 50–54 | 7 | 52.9 | 57.1% | 71.4 | 57.1 | 0.0 | 42.9 | 0.96 | 1.26 | 24–84 | -4.2 |
| 55–59 | 22 | 57.4 | 31.8% | 40.9 | 31.8 | 4.5 | 68.2 | 4.66 | 1.80 | 16–53 | 25.6 |
| 60–64 | 39 | 62.4 | 46.2% | 56.4 | 48.7 | 20.5 | 53.8 | 2.27 | 1.65 | 32–62 | 16.2 |
| 65–69 | 29 | 66.7 | 37.9% | 34.5 | 37.9 | 13.8 | 62.1 | 3.15 | 2.97 | 23–56 | 28.8 |
| 70–74 | 12 | 71.6 | 33.3% | 41.7 | 33.3 | 8.3 | 66.7 | 1.29 | 1.23 | 14–61 | 38.3 |
| 75+ | 1 | 76.0 | 0.0% | 0.0 | 0.0 | 0.0 | 100.0 | -1.07 | 0.00 | 1–84 | 76.0 |

The requested 40–45 / 45–50 buckets contain only 0 and 3 trades, and there are none above 75 except one at 76 — those cells are INSUFFICIENT DATA.
| Chronological test on the later 57 trades (fit on earlier 56) | Brier (lower=better) |
|---|---|
| Raw confidence ÷ 100 (current) | 0.3177 |
| Pasted example (monotone 'conf−15pp' style mapping) | 0.2548 |
| Constant = earlier-half win rate (44.6%) | 0.235 |
| Monotone bucket map (pool-adjacent-violators) + shrinkage k=10 | 0.2595 |
| 1-variable logistic on confidence | 0.2505 |

**Fitted monotone map on ALL trades (for display, shrinkage k=10 toward the pooled win rate):**

| Raw confidence range | Trades pooled | Calibrated P(win) | 95% credible interval |
|---|---|---|---|
| 50–59 | 32 | 35% | 20–52% |
| ≥60 | 81 | 41% | 31–52% |

Because the data is non-monotone, pool-adjacent-violators pools most buckets into one block — i.e. the honest calibration function is **almost flat at ≈39%**. Logistic slope on the earlier half: 0.0528 per point. Chronological Brier: every mapping that simply lowers the level beats raw confidence (the pasted 'conf−15pp' example, the monotone map and the logistic all score ~0.25–0.26 vs raw 0.318), **but all of them lose to a constant at the base rate (0.235)** — i.e. the rank structure of confidence adds no calibrated information; only the level correction helps (CONFIRMED level error, LIKELY no rank information). **Calibration function to return:** `p = shrunk_monotone_map(raw)` as coded in Part 12, Commit A, with a hard floor/ceiling (0.20–0.60) until n≥200 per used bucket. Evidence: CONFIRMED that raw confidence overstates (mean 62.6% vs 39.0% observed); LIKELY that there is no usable rank information in the 50–74 range.

## SECTION PART 4 — LONG VS SHORT ENGINE

| Segment | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | TP1% | TP2% | Stop% | Avg MFE | Avg MAE | Avg stop dist % | Avg stop dist (ATR) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Long — all | 98 | 43.9% | 34.5–53.7 | 4.57 | -1.11 | 2.60 | 49.0 | 43.9 | 56.1 | 7.939 | -3.018 | 3.16 | 1.02 |
| Short — all | 20 | 15.0% | 5.2–36.0 | -8.34 | -3.83 | 0.03 | 30.0 | 20.0 | 85.0 | 1.303 | -8.585 | 1.85 | 0.81 |
| Long — exit in uptime | 57 | 36.8% | 25.5–49.8 | 0.80 | -1.46 | 1.34 | 40.4 | 36.8 | 63.2 | 3.459 | -2.431 | 2.90 | 0.89 |
| Short — exit in uptime | 9 | 33.3% | 12.1–64.6 | -3.04 | -0.99 | 0.16 | 44.4 | 33.3 | 66.7 | 1.62 | -3.588 | 1.84 | 0.75 |
| Short — exit in gap | 11 | 0.0% | 0.0–25.9 | -12.67 | -8.06 | 0.00 | 18.2 | 9.1 | 100.0 | 1.043 | -12.673 | 1.86 | 0.85 |

| Feature | n present/absent | win% present / absent | Odds ratio | 95% CI | Fisher p | Info gain (bits) | Confidence |
|---|---|---|---|---|---|---|---|
| short vs long — all | 20/98 | 15.0% / 43.9% | 0.23 | [0.06, 0.82] | 0.022 | 0.0398 | MEDIUM |
| short vs long — exit in uptime only | 9/57 | 33.3% / 36.8% | 0.86 | [0.19, 3.79] | 1.0 | 0.0005 | INSUFFICIENT DATA |

**Is short alpha real after removing outage trades?** Uptime-only shorts: 33.3% win, PF 0.16, avg -3.04% (n=9) vs uptime longs 36.8%, PF 1.34 (n=57); difference p=1.0. With n=9 the sample cannot show either alpha or its absence → **INSUFFICIENT DATA**. Note uptime longs are also weak (PF 1.34); the engine's headline PF comes from gap-exit winners and a few huge longs.
| Indicator (mean) | SHORT winners / losers | LONG winners / losers |
|---|---|---|
| RSI | 43.91 (n=3) / 45.54 (n=17) | 58.69 (n=41) / 58.27 (n=52) |
| ADX | 18.35 (n=3) / 21.33 (n=17) | 28.59 (n=41) / 31.77 (n=52) |
| CMF | -0.06 (n=3) / -0.07 (n=11) | 0.09 (n=36) / 0.06 (n=43) |
| MFI | 61.32 (n=3) / 50.44 (n=11) | 61.65 (n=36) / 59.16 (n=43) |
| StochRSI | 0.72 (n=3) / 0.64 (n=17) | 0.62 (n=41) / 0.53 (n=52) |
| BB %B | 0.41 (n=3) / 0.47 (n=11) | 0.72 (n=36) / 0.68 (n=43) |
| Structure score | 11.00 (n=3) / 8.06 (n=17) | 7.86 (n=43) / 7.73 (n=55) |
| Volume score | 5.67 (n=3) / 8.00 (n=17) | 8.28 (n=43) / 7.89 (n=55) |
| Stop distance ATR | 0.78 (n=3) / 0.81 (n=11) | 1.17 (n=32) / 0.89 (n=38) |
| ATR% | 1.48 (n=3) / 2.52 (n=11) | 3.22 (n=32) / 3.98 (n=38) |

**Which indicators behave differently for shorts?** With 3 short winners (or 3 uptime winners) no per-indicator winner/loser difference among shorts is testable → INSUFFICIENT DATA; the table is descriptive only.
| Stop distance by group (median) | n | % from entry | In ATR | Stop slippage % |
|---|---|---|---|---|
| Short winners | 3 | 0.69 | 0.63 | — |
| Short losers | 17 | 1.35 | 0.86 | -2.08 |
| Long winners | 43 | 2.62 | 0.98 | — |
| Long losers | 55 | 2.10 | 0.78 | -0.37 |

| Entry quality | Dir | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF |
|---|---|---|---|---|---|---|---|
| excellent | short | 4 | 25.0% | 4.6–69.9 | -6.24 | -2.30 | 0.10 |
| excellent | long | 15 | 60.0% | 35.7–80.2 | 8.54 | 6.26 | 8.59 |
| good | short | 6 | 33.3% | 9.7–70.0 | -4.29 | -1.83 | 0.08 |
| good | long | 14 | 28.6% | 11.7–54.6 | 1.15 | -2.15 | 1.45 |
| neutral | short | 10 | 0.0% | 0–27.8 | -11.60 | -6.53 | 0.00 |
| neutral | long | 52 | 46.2% | 33.3–59.5 | 6.33 | -0.80 | 3.56 |

**The pasted 3-gate short policy:** shorts that are excellent = 4/20; with reliability ≥60 = 0/20; all gates incl. calibrated ≥55% = 0 (no bucket reaches it) → the policy is a **disable** in practice, on evidence of 20 shorts of which 11 died inside downtime. Not supported.
Shorts that reached TP1: 6 of 20; 4 of those later ended as losses (2 of them with the exit inside a monitoring gap) — a management/monitoring issue rather than an entry issue (n too small to be more than POSSIBLE). Stop distance: shorts' stops are tighter in % (median 1.29% vs 2.31%) but similar in ATR terms (0.81 vs 0.93 ATR), so 'stops too tight' is NOT supported as the short failure mode.
**Recommendation: KEEP shorts, PENALISE visibly (display only), do not restrict or disable.** Concretely: label every short 'High risk — monitoring-sensitive', keep the existing soft flag, and require a healthy heartbeat for a short to be marked *actionable*. Evidence for a hard rule: INSUFFICIENT DATA (uptime shorts n=9). Re-decide at ≥30 uptime-exited shorts; hard restriction only if they then underperform uptime longs at p<0.05.

## SECTION PART 5 — TRADE MANAGEMENT REWRITE

| After TP1 (n=54) | n | P(TP2|TP1) (Wilson) | P(TP3|TP2) | P(final loss) |
|---|---|---|---|---|
| All | 54 | 85.2% (73.4–92.3) | 30.4% (n=46) | 16.7% |
| conf <60 | 17 | 76.5% (52.7–90.4) | 7.7% (n=13) | 23.5% |
| conf 60–64 | 22 | 86.4% (66.7–95.3) | 42.1% (n=19) | 18.2% |
| conf ≥65 | 15 | 93.3% (70.2–98.8) | 35.7% (n=14) | 6.7% |
| long | 48 | 89.6% (77.8–95.5) | 32.6% (n=43) | 10.4% |
| short | 6 | 50.0% (18.8–81.2) | 0.0% (n=3) | 66.7% |
| EQ excellent | 11 | 90.9% (62.3–98.4) | 50.0% (n=10) | 9.1% |
| EQ neutral | 28 | 85.7% (68.5–94.3) | 25.0% (n=24) | 14.3% |
| reliability ≥ median | 27 | 77.8% (59.2–89.4) | 28.6% (n=21) | 25.9% |
| reliability < median | 27 | 92.6% (76.6–97.9) | 32.0% (n=25) | 7.4% |

P(return to entry after TP1) = 17.9% (n=39 with a determinable path); P(return to stop) = 17.0% (n=53); maximum continuation after TP1 (best excursion): avg 14.21%, median 6.98%.
**Can the pasted rule ('recalibrated probability ≥80% → continue; 60–80% → half & trail; <60% → exit at TP1') be built?** The quantity it needs is the *conditional* probability of reaching TP2 given TP1. Using only information available at the time (expanding window of earlier TP1-reachers), I tested it:
Decisions the ≥80/60–80/<60 rule would have made on the 54 TP1-reachers (probability from earlier trades only): {'insufficient prior data → default hold': 14, '≥80% → continue': 40}. The *pooled* version never leaves the 'continue' branch (P(TP2|TP1) ≈85%). Sliced versions would trigger for confidence <60 (76.5%, n=17) and reliability ≥ median (77.8%, n=27), but their Wilson intervals (53–90% and 59–89%) include 80%, so those slices are statistically indistinguishable from the 80% line — the extra branches are NOT supported (POSSIBLE at most), and the simulation below shows the sliced rules change nothing or hurt.
**Trailing-stop recommendation:** from the earlier path replay, trailing 50% of MFE after TP1 raised summed return on covered trades, but ~half of the gain sat in gap-exit trades (an idealised-fill effect) and winners-cut is a lower bound (snapshot cadence) → POSSIBLE, shadow-log only. **Break-even after TP1:** same status. **Partial exits:** cannot be tested (each trade has one recorded exit) → INSUFFICIENT DATA.
**Rules I can defend from the data:** (1) After TP1, default = HOLD toward the outermost defined target (CONFIRMED: exiting at TP1 lowers summed return from 280.8% to -203.6% — Part 11). (2) Show P(TP2|TP1)≈85% (Wilson interval above) as information. (3) Do not add a <60% exit branch — no slice supports it. (4) Shadow-log break-even and trail outcomes for every TP1 trade.

## SECTION PART 6 — ENTRY QUALITY REWRITE

| EQ | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | Median hold h | Loss patterns |
|---|---|---|---|---|---|---|---|---|
| excellent | 19 | 52.6% | 31.7–72.7 | 5.43 | 2.93 | 3.30 | 114.6 | {'immediate_reversal': 8, 'reached_tp1_then_stopped': 1} |
| good | 20 | 30.0% | 14.5–51.9 | -0.48 | -2.15 | 0.85 | 10.2 | {'immediate_reversal': 9, 'some_favorable_move_then_stopped': 2, 'reached_tp1_then_stopped': 2, 'hit_tp2_then_reversed': 1} |
| neutral | 62 | 38.7% | 27.6–51.2 | 3.43 | -1.60 | 1.87 | 26.6 | {'immediate_reversal': 30, 'reached_tp1_then_stopped': 4, 'some_favorable_move_then_stopped': 4} |
| late | 0 |  |  |  |  |  |  |  |
| exhausted | 0 |  |  |  |  |  |  |  |

Excellent vs rest p=0.2067 → NOT SUPPORTED. `late`/`exhausted` never become trades (n=0 by construction); at scan level: {None: 6012, 'excellent': 2322, 'exhausted': 11099, 'good': 3326, 'invalid': 23433, 'late': 15921, 'neutral': 19427}. The pasted text says 'Excellent is finally outperforming' — its point estimate is better (PF 3.30) but it is NOT statistically distinguishable at n=19.
**New categories.** Only categories that can be computed from *pre-entry* stored fields are eligible (labels defined from what happened after entry — 'Fake Breakout', 'Liquidity Sweep' — are circular or need per-candle data that is not stored → INSUFFICIENT DATA). Tested rules, with chronological halves:
| Candidate category (pre-entry rule) | 1st half n / win% | 2nd half n / win% | OR | p | Evidence |
|---|---|---|---|---|---|
| Momentum Chase: RSI≥65 or StochRSI>0.85 or >1.5 ATR above EMA20 | 12 / 58.3% | 18 / 44.4% | 1.84 | 0.1941 | NOT SUPPORTED |
| Pullback Continuation: trend≥20, within 1.5% of EMA20, RSI 40–60 | 9 / 22.2% | 13 / 23.1% | 0.39 | 0.0951 | POSSIBLE |
| Mean-Reversion Entry: against BTC trend (dip-buy / rally-short) | 30 / 56.7% | 13 / 46.2% | 2.6 | 0.0188 | LIKELY |
| Late Breakout: BB%B>0.9 and >1.0 ATR above EMA20 | 2 / 100.0% | 3 / 33.3% | 2.44 | 0.3767 | INSUFFICIENT DATA |
| Fake Breakout / Liquidity Sweep | — | — | — | — | INSUFFICIENT DATA (needs candle-level / post-entry data) |

Base win rate: 1st half 42.4%, 2nd half 35.6%. **Classification rules to keep (analytics-only labels, no gating):** the four rules above as tags; none is confirmed. The one with a notable signal ('against BTC trend' = better outcomes) is the *opposite* of what a 'Mean Reversion = risky' label would imply, so it should not be presented to users as a risk warning.

## SECTION PART 7 — COIN RELIABILITY ENGINE

| Symbol | n | Raw win% | Bayesian win% (k=10) | 95% credible | PF | Avg ret | Median ret | TP1 freq | Stop freq | Reliability score | Label |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ETHUSDT | 5 | 0.0% | 26.0% | 0–46 | 0.00 | -6.50 | -1.46 | 0.0% | 100.0% | 26.0 | Watch |
| SOLUSDT | 5 | 20.0% | 32.7% | 4–64 | 1.75 | 1.80 | -2.21 | 40.0% | 80.0% | 32.7 | Watch |
| CLUSDT | 4 | 50.0% | 42.1% | 15–85 | 2.58 | 2.38 | 2.19 | 50.0% | 50.0% | 42.1 | Watch |
| DRAMUSDT | 4 | 25.0% | 35.0% | 5–72 | 0.22 | -2.53 | -3.82 | 25.0% | 75.0% | 35.0 | Watch |
| HYPEUSDT | 4 | 50.0% | 42.1% | 15–85 | 10.56 | 10.02 | 6.78 | 50.0% | 50.0% | 42.1 | Watch |
| SKHYUSDT | 4 | 50.0% | 42.1% | 15–85 | 3.19 | 2.46 | 2.03 | 75.0% | 50.0% | 42.1 | Watch |
| SPCXUSDT | 4 | 25.0% | 35.0% | 5–72 | 0.94 | -0.07 | -1.14 | 25.0% | 75.0% | 35.0 | Watch |
| ZECUSDT | 4 | 50.0% | 42.1% | 15–85 | 2.49 | 12.34 | 16.36 | 50.0% | 50.0% | 42.1 | Watch |
| BNBUSDT | 3 | 33.3% | 37.7% | 7–81 | 3.25 | 1.61 | -1.01 | 33.3% | 66.7% | 37.7 | Watch |
| CRCLUSDT | 3 | 66.7% | 45.4% | 19–93 | 11.03 | 3.32 | 5.24 | 100.0% | 33.3% | 45.4 | Watch |
| DOGEUSDT | 3 | 0.0% | 30.0% | 1–60 | 0.00 | -12.88 | -15.80 | 33.3% | 100.0% | 30.0 | Watch |
| LINKUSDT | 3 | 66.7% | 45.4% | 19–93 | 6.08 | 9.29 | 8.66 | 66.7% | 33.3% | 45.4 | Watch |
| MSTRUSDT | 3 | 0.0% | 30.0% | 1–60 | 0.00 | -3.39 | -3.44 | 0.0% | 100.0% | 30.0 | Watch |
| PUMPUSDT | 3 | 33.3% | 37.7% | 7–81 | 1.55 | 4.64 | -2.15 | 66.7% | 66.7% | 37.7 | Watch |
| SAMSUNGUSDT | 3 | 66.7% | 45.4% | 19–93 | 2.60 | 2.43 | 5.44 | 66.7% | 33.3% | 45.4 | Watch |
| SKHYNIXUSDT | 3 | 33.3% | 37.7% | 7–81 | 0.97 | -0.07 | -2.28 | 33.3% | 66.7% | 37.7 | Watch |
| SNDKUSDT | 3 | 33.3% | 37.7% | 7–81 | 0.55 | -1.68 | -4.30 | 33.3% | 66.7% | 37.7 | Watch |
| XAGUSDT | 3 | 33.3% | 37.7% | 7–81 | 0.55 | -0.81 | -1.55 | 33.3% | 66.7% | 37.7 | Watch |
| 1000PEPEUSDT | 2 | 50.0% | 40.8% | 9–91 | 4.34 | 12.47 | 12.47 | 50.0% | 50.0% | 40.8 | Watch |
| ACEUSDT | 2 | 50.0% | 40.8% | 9–91 | 4.12 | 15.08 | 15.08 | 50.0% | 50.0% | 40.8 | Watch |
| BTWUSDT | 2 | 100.0% | 49.2% | 29–99 | — | 17.25 | 17.25 | 100.0% | 0.0% | 49.2 | Trusted |
| BZUSDT | 2 | 0.0% | 32.5% | 1–71 | 0.00 | -3.35 | -3.35 | 0.0% | 100.0% | 32.5 | Watch |
| CYSUSDT | 2 | 50.0% | 40.8% | 9–91 | 3.23 | 6.79 | 6.79 | 50.0% | 50.0% | 40.8 | Watch |
| EWYUSDT | 2 | 50.0% | 40.8% | 9–91 | 0.72 | -0.51 | -0.51 | 50.0% | 50.0% | 40.8 | Watch |
| MOVRUSDT | 2 | 0.0% | 32.5% | 1–71 | 0.00 | -9.47 | -9.47 | 0.0% | 100.0% | 32.5 | Watch |
| MUUSDT | 2 | 50.0% | 40.8% | 9–91 | 0.44 | -1.61 | -1.61 | 50.0% | 50.0% | 40.8 | Watch |
| NEARUSDT | 2 | 100.0% | 49.2% | 29–99 | — | 63.82 | 63.82 | 100.0% | 0.0% | 49.2 | Trusted |
| NVDAUSDT | 2 | 100.0% | 49.2% | 29–99 | — | 2.85 | 2.85 | 100.0% | 0.0% | 49.2 | Trusted |
| PAXGUSDT | 2 | 50.0% | 40.8% | 9–91 | 2.29 | 0.38 | 0.38 | 50.0% | 50.0% | 40.8 | Watch |
| SNXXUSDT | 2 | 0.0% | 32.5% | 1–71 | 0.00 | -6.80 | -6.80 | 0.0% | 100.0% | 32.5 | Watch |
| SOXSUSDT | 2 | 100.0% | 49.2% | 29–99 | — | 4.11 | 4.11 | 50.0% | 0.0% | 49.2 | Trusted |
| SUIUSDT | 2 | 0.0% | 32.5% | 1–71 | 0.00 | -3.46 | -3.46 | 0.0% | 100.0% | 32.5 | Watch |
| WLDUSDT | 2 | 50.0% | 40.8% | 9–91 | 0.44 | -5.25 | -5.25 | 100.0% | 50.0% | 40.8 | Watch |
| XAUUSDT | 2 | 50.0% | 40.8% | 9–91 | 2.64 | 0.48 | 0.48 | 50.0% | 50.0% | 40.8 | Watch |
| ADAUSDT | 1 | 100.0% | 44.5% | 16–99 | — | 4.95 | 4.95 | 100.0% | 0.0% | 44.5 | Watch |
| ALLOUSDT | 1 | 0.0% | 35.4% | 1–84 | 0.00 | -2.76 | -2.76 | 0.0% | 100.0% | 35.4 | Watch |
| APRUSDT | 1 | 100.0% | 44.5% | 16–99 | — | 19.04 | 19.04 | 100.0% | 0.0% | 44.5 | Watch |
| BEATUSDT | 1 | 0.0% | 35.4% | 1–84 | 0.00 | -9.50 | -9.50 | 100.0% | 100.0% | 35.4 | Watch |
| BICOUSDT | 1 | 0.0% | 35.4% | 1–84 | 0.00 | -44.42 | -44.42 | 0.0% | 100.0% | 35.4 | Watch |
| BTCUSDT | 1 | 0.0% | 35.4% | 1–84 | 0.00 | -1.61 | -1.61 | 0.0% | 100.0% | 35.4 | Watch |
| ENAUSDT | 1 | 0.0% | 35.4% | 1–84 | 0.00 | -4.10 | -4.10 | 100.0% | 100.0% | 35.4 | Watch |
| FILUSDT | 1 | 100.0% | 44.5% | 16–99 | — | 14.90 | 14.90 | 100.0% | 0.0% | 44.5 | Watch |
| FLOCKUSDT | 1 | 0.0% | 35.4% | 1–84 | 0.00 | -5.38 | -5.38 | 0.0% | 100.0% | 35.4 | Watch |
| HEMIUSDT | 1 | 0.0% | 35.4% | 1–84 | 0.00 | -8.62 | -8.62 | 0.0% | 100.0% | 35.4 | Watch |
| HOLOUSDT | 1 | 0.0% | 35.4% | 1–84 | 0.00 | -7.17 | -7.17 | 0.0% | 100.0% | 35.4 | Watch |
| LABUSDT | 1 | 0.0% | 35.4% | 1–84 | 0.00 | -7.36 | -7.36 | 0.0% | 100.0% | 35.4 | Watch |
| LITEUSDT | 1 | 0.0% | 35.4% | 1–84 | 0.00 | -5.12 | -5.12 | 0.0% | 100.0% | 35.4 | Watch |
| QQQUSDT | 1 | 100.0% | 44.5% | 16–99 | — | 1.67 | 1.67 | 100.0% | 0.0% | 44.5 | Watch |
| RIVERUSDT | 1 | 100.0% | 44.5% | 16–99 | — | 18.82 | 18.82 | 100.0% | 0.0% | 44.5 | Watch |
| RKLBUSDT | 1 | 0.0% | 35.4% | 1–84 | 0.00 | -2.66 | -2.66 | 0.0% | 100.0% | 35.4 | Watch |
| SPORTFUNUSDT | 1 | 0.0% | 35.4% | 1–84 | 0.00 | -6.12 | -6.12 | 0.0% | 100.0% | 35.4 | Watch |
| TRUMPUSDT | 1 | 0.0% | 35.4% | 1–84 | 0.00 | -20.95 | -20.95 | 100.0% | 100.0% | 35.4 | Watch |
| UNIUSDT | 1 | 100.0% | 44.5% | 16–99 | — | 52.19 | 52.19 | 100.0% | 0.0% | 44.5 | Watch |
| USELESSUSDT | 1 | 0.0% | 35.4% | 1–84 | 0.00 | -4.71 | -4.71 | 0.0% | 100.0% | 35.4 | Watch |
| VELVETUSDT | 1 | 100.0% | 44.5% | 16–99 | — | 27.28 | 27.28 | 100.0% | 0.0% | 44.5 | Watch |
| XRPUSDT | 1 | 100.0% | 44.5% | 16–99 | — | 4.61 | 4.61 | 100.0% | 0.0% | 44.5 | Watch |

Label rule (statistical, not arbitrary): **Trusted** if P(true win rate > pooled 39.0%) ≥ 0.90 under a uniform-prior Beta posterior; **Avoid** if P(below pooled) ≥ 0.95; else **Watch**. Counts: {'Watch': 52, 'Trusted': 4}; symbols with n≥5: 2/56. Chronological check: prior-trades reliability ≥ median vs outcome OR 0.65, p=0.3454 → NOT SUPPORTED: **reliability does not yet predict later outcomes**, so present it as descriptive history with n, not as a gate.

## SECTION PART 8 — MARKET REGIME INTELLIGENCE (OBSERVATIONAL; market_regime.py UNTOUCHED)

Rule-based labels from pre-entry stored fields (ADX, ATR% terciles, BTC trend, Fear&Greed) — not learned clusters (a k-means attempt on the score components gave silhouette 0.195, i.e. no real structure). Labels: Panic = F&G≤20 & BTC bear; Expansion = ADX≥25 & top-tercile ATR%; Trending Bull/Bear = ADX≥25 by BTC trend; Compression = ADX<20 & bottom-tercile ATR%; Range = ADX<20; Mean Reversion = ADX 20–25 and against BTC trend.
| Regime | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF | TP1% | Stop% |
|---|---|---|---|---|---|---|---|---|
| Range | 25 | 44.0% | 26.7–62.9 | 5.34 | -1.57 | 2.20 | 48.0 | 56.0 |
| Expansion | 15 | 26.7% | 10.9–52.0 | 7.08 | -4.95 | 2.25 | 40.0 | 73.3 |
| Trending Bear | 14 | 71.4% | 45.4–88.3 | 5.06 | 4.14 | 13.91 | 71.4 | 28.6 |
| Trending Bull | 13 | 7.7% | 1.4–33.3 | -2.28 | -2.28 | 0.14 | 15.4 | 92.3 |
| Compression | 12 | 66.7% | 39.1–86.2 | 2.93 | 3.84 | 1.75 | 75.0 | 33.3 |
| Mean Reversion | 5 | 20.0% | 3.6–62.4 | -5.26 | -1.01 | 0.09 | 60.0 | 80.0 |
| Panic | 0 | — | — | — | — | — | — | — |

| Regime | Strategy family (n≥5 only) | n | Win% | Wilson 95% CI | Avg ret% | Median ret% | PF |
|---|---|---|---|---|---|---|---|
| Trending Bear | ema_pullback | 5 | 40.0% | 11.8–76.9 | 1.50 | -0.58 | 3.77 |
| Trending Bear | fvg_continuation | 5 | 80.0% | 37.6–96.4 | 4.82 | 7.07 | 9.72 |
| Expansion | trend_continuation_other | 10 | 20.0% | 5.7–51.0 | -3.10 | -5.11 | 0.55 |
| Range | ema_pullback | 14 | 35.7% | 16.3–61.2 | 7.77 | -2.98 | 2.48 |
| Range | fvg_continuation | 6 | 50.0% | 18.8–81.2 | 1.51 | -0.28 | 1.33 |
| Compression | ema_pullback | 8 | 62.5% | 30.6–86.3 | 0.34 | 5.55 | 1.06 |
| Trending Bull | ema_pullback | 6 | 0.0% | 0–39.0 | -2.23 | -1.87 | 0.00 |
| Trending Bull | fvg_continuation | 5 | 0.0% | 0–43.4 | -3.32 | -3.44 | 0.00 |

| Regime (vs all other trades) | n | OR | Fisher p | Bonferroni p (x6 tests) | 1st half n / win% | 2nd half n / win% | Evidence after correction |
|---|---|---|---|---|---|---|---|
| Range | 25 | 1.15 | 0.8123 | 1.000 | 5 / 60.0% | 20 / 40.0% | NOT SUPPORTED |
| Expansion | 15 | 0.45 | 0.2535 | 1.000 | 4 / 50.0% | 11 / 18.2% | NOT SUPPORTED |
| Trending Bear | 14 | 4.5 | 0.0181 | 0.109 | 12 / 66.7% | 2 / 100.0% | POSSIBLE |
| Trending Bull | 13 | 0.09 | 0.0064 | 0.038 | 0 / —% | 13 / 7.7% | LIKELY |
| Compression | 12 | 3.33 | 0.1109 | 0.665 | 2 / 0.0% | 10 / 80.0% | NOT SUPPORTED |
| Mean Reversion | 5 | 0.33 | 0.3956 | 1.000 | 2 / 50.0% | 3 / 0.0% | INSUFFICIENT DATA |

The named regimes have workable n (12–25 each) but the labels were defined once, a priori, from the names you listed, and 6 regimes with trades are tested, so Bonferroni-corrected p is shown. **Time confound:** all 13 Trending-Bull trades fall in the later half (0 in the earlier half), so that cell cannot be chronologically validated — it may reflect one market episode rather than a regime effect. The striking cells — Trending Bull (ADX≥25 with BTC bullish) winning far LESS and Trending Bear far MORE — are consistent with the 'against-BTC-trend entries do better' finding in Part 6, which makes them a coherent hypothesis (POSSIBLE/LIKELY after correction as shown) but not a rule: they are in-sample, longs dominate the sample so 'Trending Bear' is mostly countertrend longs, and the regime×strategy cells have n<10 → INSUFFICIENT DATA for 'which strategies work inside each regime'. No change to market_regime.py is proposed. Regime labels the production engine actually emitted: {'risk_on': 34, 'mixed': 84}.

## SECTION PART 9 — OPEN TRADES HEALTH CHECK (evaluated separately; never used for optimisation)

| Symbol | Dir | Status | Stage | EV(R) | Reliability | Historical analogue P(win) | P(TP1) | P(TP2) | P(stop before TP1) | Manager decision | Recommendation | Days since snapshot |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ONUSDT | long | open | None | — | — | none | — | — | 0.53 (pooled) | — | STALE — do not act | 49.4 |
| SKYAIUSDT | long | open | None | — | — | none | — | — | 0.53 (pooled) | — | STALE — do not act | 47.6 |
| GWEIUSDT | long | open | None | — | — | none | — | — | 0.53 (pooled) | — | STALE — do not act | 48.6 |
| MMTUSDT | long | pending | None | — | — | none | — | — | 0.53 (pooled) | — | STALE — do not act | 48.6 |
| 1000CATUSDT | long | open | None | — | — | none | — | — | 0.53 (pooled) | — | STALE — do not act | 48.6 |
| TSTUSDT | long | pending | None | — | — | none | — | — | 0.53 (pooled) | — | STALE — do not act | 46.4 |
| MUBARAKUSDT | long | open | None | — | — | none | — | — | 0.53 (pooled) | — | STALE — do not act | 47.6 |
| GUAUSDT | short | open | None | — | — | none | — | — | 0.53 (pooled) | — | STALE — do not act | 46.1 |
| BANKUSDT | short | open | TP1_REACHED | — | — | none | — | — | 0.53 (pooled) | HOLD | STALE — do not act | 43.4 |
| LITEUSDT | long | open | OPEN | — | 35.4 | none | — | — | 0.53 (pooled) | HOLD | STALE — do not act | 44.1 |
| ALLOUSDT | short | open | OPEN | — | 35.4 | none | — | — | 0.53 (pooled) | HOLD | STALE — do not act | 41.2 |
| BOMEUSDT | long | pending | PRE_ENTRY | — | — | none | — | — | 0.53 (pooled) | HOLD | STALE — do not act | 36.4 |
| XMRUSDT | long | pending | PRE_ENTRY | — | — | none | — | — | 0.53 (pooled) | HOLD | STALE — do not act | 41.2 |
| SPORTFUNUSDT | long | pending | PRE_ENTRY | — | 35.4 | none | — | — | 0.53 (pooled) | HOLD | STALE — do not act | 41.2 |
| 4USDT | long | pending | — | — | — | none | — | — | 0.53 (pooled) | — | STALE — do not act | never |
| RAYSOLUSDT | long | open | OPEN | 0.12 | — | none | 53.10 | — | 0.53 (pooled) | HOLD | STALE — do not act | 13.2 |
| LINKUSDT | short | pending | PRE_ENTRY | -0.45 | 45.4 | none | 50.00 | — | 0.53 (pooled) | HOLD | Hold | 0.4 |
| SOXLUSDT | short | pending | PRE_ENTRY | 0.39 | — | none | 57.90 | — | 0.53 (pooled) | HOLD | Hold | 0.4 |
| REZUSDT | long | pending | PRE_ENTRY | -0.45 | — | none | 40.00 | — | 0.53 (pooled) | HOLD | STALE — do not act | 12.1 |
| 我踏马来了USDT | long | open | OPEN | 0.89 | — | none | 58.60 | — | 0.53 (pooled) | HOLD | STALE — do not act | 13.5 |
| RIVERUSDT | short | pending | PRE_ENTRY | -1.00 | 44.5 | none | 0.00 | — | 0.53 (pooled) | HOLD | STALE — do not act | 13.4 |
| WLFIUSDT | long | open | OPEN | 0.25 | — | none | 53.10 | — | 0.53 (pooled) | HOLD | STALE — do not act | 13.4 |
| GRIFFAINUSDT | long | open | OPEN | 0.38 | — | none | 53.10 | — | 0.53 (pooled) | HOLD | STALE — do not act | 13.2 |
| QQQUSDT | short | open | OPEN | -1.00 | 44.5 | none | 0.00 | — | 0.53 (pooled) | HOLD | STALE — do not act | 12.0 |
| KORUUSDT | long | open | OPEN | -0.12 | — | none | 60.00 | — | 0.53 (pooled) | HOLD | Hold | 0.4 |
| BNBUSDT | long | open | OPEN | 0.81 | 37.7 | 0.75 | 60.00 | — | 0.53 (pooled) | HOLD | Hold | 0.4 |
| DOGEUSDT | long | open | OPEN | -0.49 | 30.0 | none | 30.00 | — | 0.53 (pooled) | HOLD | Hold | 0.4 |
| SKHYNIXUSDT | long | open | OPEN | -0.53 | 37.7 | none | 35.70 | — | 0.53 (pooled) | HOLD | Hold | 0.4 |
| SKHYUSDT | long | open | OPEN | -0.17 | 42.1 | none | 35.70 | — | 0.53 (pooled) | HOLD | Hold | 0.4 |
| CLUSDT | long | open | OPEN | -0.15 | 42.1 | none | 60.00 | — | 0.53 (pooled) | HOLD | Hold | 0.4 |
| BZUSDT | long | open | OPEN | -0.12 | 32.5 | none | 60.00 | — | 0.53 (pooled) | HOLD | Hold | 0.4 |
| WLDUSDT | long | open | OPEN | -0.35 | 40.8 | none | 30.00 | — | 0.53 (pooled) | HOLD | Hold | 0.4 |
| SUIUSDT | long | open | OPEN | -0.40 | 32.5 | none | 30.00 | — | 0.53 (pooled) | HOLD | Hold | 0.4 |
| TAOUSDT | long | open | OPEN | -0.56 | — | none | 30.00 | — | 0.53 (pooled) | HOLD | Hold | 0.4 |
| PUMPUSDT | long | pending | — | 0.04 | 37.7 | none | — | — | 0.53 (pooled) | — | STALE — do not act | never |

**23 of 35 open/pending trades are stale (no snapshot >1 day; median age 13.4 days).** For those, stage/probabilities/recommendations are last-known values, not a live assessment, so I withhold Reduce/Exit/Take-TP1 calls. 'P(stop)' is the pooled historical rate (no per-trade stop-probability model exists). Immediate action: restart the scanner so every open trade is re-snapshotted, then re-run this table.

## SECTION PART 10 — MISSED OPPORTUNITY ANALYSIS

| Rejection reason | Scan rows |
|---|---|
| published/active | 67402 |
| no_trade (direction gate) | 5962 |
| rank cutoff | 4551 |
| exhausted | 3086 |
| late | 539 |

Rejected scans carry no entry/stop/TP levels and no price, and the 48 avoid-grade plans have zero PredictionSnapshots. Therefore *'would TP1/TP2/stop have hit'* and **rejection accuracy cannot be computed → INSUFFICIENT DATA.** The only forward-return numbers derivable (Engineering report §14) rely on a tiny, selection-biased subset (n<15 per cell at 24–72h). I will not publish an accuracy figure; doing so would be invention. Fix = Part 12, Commit F (recorder wiring; needs approval because it touches `background_scanner.py`).

## SECTION PART 11 — SIMULATION LAB (ALL 118 TRADES, CHRONOLOGICAL SPLIT)

Every row replays the same historical trades under a rule. Rules that need a learned quantity (P(TP2|TP1), reliability) use **only trades that had already closed** at decision time (no future information). Path-based rules use recorded snapshot paths (no intra-bar wicks; fills at the rule level; fees ignored) and apply only to trades with ≥4 path points — others keep their actual result. **All rules were chosen after seeing this data → in-sample**; the half-split columns show stability, not out-of-sample proof.
| Strategy (ranked by PF) | n trades | Win rate | PF | PF ex-best | Avg ret% | Median ret% | Max DD (summed) | Sharpe (per-trade) | PF 1st half / 2nd half |
|---|---|---|---|---|---|---|---|---|---|
| Only Excellent entry quality | 19 | 52.6% | 3.30 | 2.42 | 5.43 | 2.93 | -24.3 | 0.40 | 8.76 / 1.59 |
| No shorts | 98 | 43.9% | 2.60 | 2.19 | 4.57 | -1.11 | -86.6 | 0.26 | 1.96 / 3.23 |
| Break-even after TP1 | 118 | 38.1% | 1.98 | 1.66 | 2.98 | -1.01 | -90.7 | 0.18 | 1.07 / 3.65 |
| Swing stop (nearest support/resistance) | 118 | 38.1% | 1.94 | 1.64 | 2.99 | -1.29 | -90.7 | 0.18 | 1.26 / 2.86 |
| Tight ATR stop (1.0×) | 118 | 39.0% | 1.93 | 1.63 | 2.99 | -1.37 | -90.7 | 0.18 | 1.26 / 2.80 |
| Raw confidence ≥ 65 | 42 | 35.7% | 1.93 | 1.53 | 2.52 | -1.11 | -64.4 | 0.18 | 1.55 / 2.57 |
| Trail 50% of MFE after TP1 | 118 | 45.8% | 1.91 | 1.60 | 2.79 | -1.01 | -105.6 | 0.17 | 0.92 / 3.77 |
| Raw confidence ≥ 60 | 81 | 40.7% | 1.78 | 1.57 | 2.40 | -1.14 | -78.2 | 0.17 | 2.03 / 1.56 |
| Current engine | 118 | 39.0% | 1.62 | 1.37 | 2.38 | -1.59 | -98.9 | 0.14 | 1.15 / 2.13 |
| Continue to TP2 only if P(TP2|TP1) ≥ 80% (pooled, prior trades) | 118 | 39.0% | 1.62 | 1.37 | 2.38 | -1.59 | -98.9 | 0.14 | 1.15 / 2.13 |
| Same, conditioned on confidence bucket | 118 | 39.0% | 1.62 | 1.37 | 2.38 | -1.59 | -98.9 | 0.14 | 1.15 / 2.13 |
| Reliability-adjusted TP manager (continue only if reliability ≥ median) | 118 | 40.7% | 0.94 | 0.68 | -0.20 | -1.50 | -135.5 | -0.01 | 0.78 / 1.14 |
| Exit TP1 always | 118 | 46.6% | 0.42 | 0.39 | -1.73 | -1.01 | -228.5 | -0.25 | 0.38 / 0.48 |
| Calibrated p ≥ 55% (pasted rule) | 0 | — | — | — | — | — | — | — | — |

**Reading (no over-claiming):** (1) 'Exit TP1 always' is by far the worst — CONFIRMED that early exit destroys the right tail. (2) The 80%-probability TP manager is identical to the current engine in practice (its condition is almost always true) — it adds nothing measurable. (3) The reliability-adjusted manager exits many good trades early and underperforms. (4) Stop-style and break-even/trailing rows improve PF, but roughly half of that gain is gap-exit idealisation (previous report §9); treat as POSSIBLE, shadow-log. (5) 'Only Excellent' and 'No shorts' rank high on PF but rest on n=19 / 98 trades chosen post hoc; check the ex-best PF and the half-split before believing them. (6) A raw-confidence ≥65 filter shows PF 1.93 vs 1.62 and better PF in both halves, but its WIN RATE is lower (35.7% vs 39.0%) — the PF gain comes from larger winners in the 65–69 bucket (PF 2.97), while 70–74 is weak (PF 1.23, win 33%); with n=42 and no monotone bucket pattern that is POSSIBLE at best and has no calibrated-probability meaning. The pasted 'calibrated ≥55%' rule selects nothing (0 trades). **No strategy is CONFIRMED better than the current engine on out-of-sample evidence.**

## SECTION PART 12 — EXACT CODE CHANGES (PROPOSED — NOT APPLIED)

Only additive / non-frozen files. Frozen files (scoring.py, decision.py, market_regime.py, reasoning prompt, ML) get **no** change: the evidence in Parts 2–4 does not justify one. Each commit is small, individually revertable, and requires your explicit go-ahead. Code below is a draft to be implemented *with tests* on approval; I have not run it.
| Commit | Files | Why (evidence) | Expected improvement | Risk | Frozen files changed? |
|---|---|---|---|---|---|
| A — calibrated probability display | `app/engine/calibration.py`, `app/routes/outcomes.py` serializer (display fields only) | Part 3: mean conf 62.6% vs 39.0% observed; only flat/shrunk mappings beat raw on the chronological test | Removes ~24pp overstatement from what users see; no change to trades | Very low — display only | No |
| B — Trade Truth taxonomy V2 + KPI honesty | `app/analytics/trade_truth.py`, `app/engine/performance_center.py`, `app/routes/performance.py` | Part 1 verdict set; every KPI shows n, Wilson CI, median, ex-top-3 PF, gap-exposed % | Debug/analytics quality | Very low | No |
| C — Trade manager: 'HOLD to outermost target' default + shadow logging of BE/trail | `app/engine/trade_manager.py` (probability display + shadow fields only), `app/analytics/stop_styles.py` (new) | Part 5/11: exit-at-TP1 is CONFIRMED harmful; BE/trail unproven | Evidence collection; no behaviour change | Low | No |
| D — Reliability & Expected-Outcome card fields | `app/analytics/reliability.py`, serializer | Part 7; replaces EV number with observed TP1/TP2/TP3/stop rates (unconditional: TP1 46%, TP2 40%, TP3 12%, stop 61%) | Removes anti-predictive EV from the UI | Low | No |
| E — Short 'High risk / monitoring-sensitive' badge | `app/analytics/trade_quality.py`, serializer | Part 4 | Honest labelling; no gating | Low | No |
| F — Wire missed-opportunity recorder + 72h post-close price capture (**needs approval**) | `app/engine/background_scanner.py`, `app/analytics/missed_opportunity.py`, `db_models.py` (additive) | Part 10: rejection accuracy INSUFFICIENT DATA | Unblocks Part 10 and 'should have continued' verdicts | Low–Medium (touches scanner) | **Yes — background_scanner.py** |
| G — Ops: supervised always-on scanner + heartbeat alert | deployment config only | Uptime ≈16%; 72% of loss magnitude in gap/infra verdicts; 23 stale open trades | Largest data-quality lever | Very low | No |
| NOT PROPOSED — C/D of the pasted plan (scoring weights, decision gates) | scoring.py, decision.py | Parts 2–4: no component significant; 0/12 components support a weight change; trend variants indistinguishable | None demonstrable | High (overfit) | Would change frozen files — **rejected on evidence** |

**Commit A — draft code (calibration.py addition):**
```python
def _pav_blocks(rows):
    """rows: [(raw_confidence, won_bool)] -> monotone non-decreasing blocks [[lo_bucket, wins, n], ...]"""
    grp = {}
    for c, won in rows:
        k = int(min(max(c, 50), 70) // 5 * 5)
        w, n = grp.get(k, (0, 0)); grp[k] = (w + bool(won), n + 1)
    blocks = [[k, w, n] for k, (w, n) in sorted(grp.items())]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][1] / blocks[i][2] > blocks[i + 1][1] / blocks[i + 1][2]:
            blocks[i] = [blocks[i][0], blocks[i][1] + blocks[i + 1][1], blocks[i][2] + blocks[i + 1][2]]
            del blocks[i + 1]; i = max(i - 1, 0)
        else:
            i += 1
    return blocks

def calibrated_probability(raw_confidence, rows, shrink_k=10, lo=0.20, hi=0.60):
    """Display-only calibrated P(win) with credible interval. NEVER feeds scoring/decision."""
    if not rows:
        return {"p": None, "interval": None, "n": 0, "evidence": "INSUFFICIENT DATA"}
    prior = sum(1 for _, w in rows if w) / len(rows)
    blocks = _pav_blocks(rows)
    c = int(min(max(raw_confidence, 50), 70) // 5 * 5)
    b = max([x for x in blocks if x[0] <= c], key=lambda x: x[0], default=blocks[0])
    p = (b[1] + shrink_k * prior) / (b[2] + shrink_k)
    p = min(max(p, lo), hi)
    a, bb = 1 + b[1], 1 + b[2] - b[1]          # Beta posterior for the interval
    from scipy.stats import beta
    return {"p": round(p, 3), "interval": [round(beta.ppf(.025, a, bb), 3), round(beta.ppf(.975, a, bb), 3)],
            "n": b[2], "evidence": "LIKELY" if b[2] >= 30 else "INSUFFICIENT DATA"}
```
*Tests to write:* monotonicity of the map; empty/one-class input; interval contains p; never returns outside [0.20, 0.60]; does not import or alter scoring/decision modules; serializer adds `calibrated_probability` without changing existing fields.
**Commit C — trade_manager.py behaviour:** *no change to decisions.* Add fields `p_tp2_given_tp1` (+Wilson interval, n) to the snapshot payload and log (not act on) the hypothetical BE/trail exit for every TP1 trade so the ≥200-trade re-audit can settle Part 5 with clean data.
**Expected combined effect of A–E and G:** no change to trade selection or exits; what changes is honesty of displayed numbers and quality of the data collected. I am deliberately not promising a profit-factor improvement — none is demonstrated by the evidence.

### Sequencing
1. **G** (uptime) — highest leverage, no code. 2. **A, B, D, E** — display/analytics, one at a time. 3. **C** — shadow logging. 4. **F** — only with your explicit approval (frozen scanner file). 5. Re-run this script at ≥200 closed trades; only then consider weights, decision gates, or exit-rule changes, using the chronological split shown above (fit on the first half, confirm on the second).

---

## Revisions after review (2026-09-27)

**Adopted from the review** (all implemented, tested, committed locally, not pushed):

| Review point | What changed |
|---|---|
| Implementation order G -> ... | G, A, D, B, E built in that order; F and C not built (see below) |
| A: show ranges, not fake precision | Display is now a pooled range: "<50" (n=3, falls back to overall), "50-59" (~38%), "60+" (~41%), with 95% interval, n and a tooltip. No per-point percentages. |
| D: rename Trusted/Watch/Avoid | Now **Positive history / Insufficient history / Negative history**, posterior-threshold based, with a **5-trade minimum** (2 wins from 2 trades was labelled "Trusted" in the audit report - that was too generous; corrected). Each label carries the "reliability has not been shown to predict outcomes" caveat. |
| E: badge wording | "Lower historical reliability (small sample)"; downtime is stated as one unresolved hypothesis; the badge withdraws itself when shorts outperform longs or n>=30. |
| Part 7 / 8 cautions | Reliability presented as descriptive; Trending Bull kept as a hypothesis under monitoring (all 13 trades in the later half), not used to penalise trades. |

**Corrections to statements in the review (checked against the DB):**
* "F - Recorder wiring ... heartbeat, TP touches, monitoring state": in this plan F is the *missed-opportunity recorder + 72h post-close price capture* and it edits the frozen `background_scanner.py`. Heartbeat/monitoring state is G (done, no scanner edit). F is therefore **held for your explicit confirmation** of that scope.
* "24 Scanner Gap losses and 8 Infrastructure Failures contribute over 70% of loss magnitude": correct by the verdict definition (71.5%: 32 losses, -322.6pp of -451pp). My earlier 62.8% counted only exits inside a gap; the two figures answer different questions.
* C (trade manager): the review and this plan agree - shadow logging only, no behaviour change - but it needs new columns for highest-excursion/lowest-retrace after TP1, which is a schema change, so it is queued after F.

**Part 5.5 - TP1 timing (new, requested in the review):** see `karma_part5_5_tp1_timing.md`. Key facts: 53 TP1-reachers with timestamps; median entry->TP1 9.1h overall but only **9 of 53 are gap-free** (their median is 2.1h), so raw timings are dominated by monitoring gaps; TP1->TP2 median 0.7h (56% of eventual TP2 hits within 1h, 80% within 24h); fast-vs-slow TP1 final-loss rate OR 0.46, p=0.47 (NOT SUPPORTED); TP1->stop reversals: 5 of 9 exited inside a gap. Conclusion: no timeout/trail parameter can be derived; log the timestamps.
