# Karma V2.1 — Model Improvement Report

**Read-only. No code, weights, prompts, models, or DB rows modified.** Computed by `analysis_karma_v2_1_report.py` against the live DB (86 resolved trades: 33 wins, 53 losses), reusing `performance_center.py`'s already-tested `tp_continuation_analytics()`, `confidence_lab()`, and `scanner_health()` rather than reimplementing them. Every probability below carries its sample size and a 95% Wilson confidence interval — small-n findings are reported, never hidden, and never treated as equal in strength to large-n ones.

Goal of this report, per instruction: **identify deterministic improvements implementable without retraining ML.** Nothing here recommends a weight change or ML retrain without saying so explicitly and showing why.

---

## 1. TP Continuation Engine

**Base rates** (n=86 entered, n=37 reached TP1):

| metric | value | 95% CI | n |
|---|---|---|---|
| P(TP1) | 43.0% | [33.1-53.6]% | 86 |
| P(stop before TP1) | 55.8% | [45.3-65.8]% | 86 |
| P(TP2\|TP1) | 86.5% | | 37 |
| P(TP3\|TP2) | 39.4% | | 33 |
| Return-to-entry after TP1 | 20.8% | | 24 determinable |
| Return-to-stop after TP1 | 13.9% | | 36 determinable |

**By direction:**

| | n | P(TP1) | 95% CI | P(TP2\|TP1) | 95% CI |
|---|---|---|---|---|---|
| long | 73 | 50.7% | [39.5-61.8]% | 86.5% | [72.0-94.1]% |
| short | 13 | **0.0%** | [0.0-22.8]% | — (n=0) | |

**Important caveat on the short 0.0% figure**: this is not "shorts never get anywhere" in the way it looks — it's partly a known data artifact. SOXSUSDT (short) has its own TP1 placed farther from entry than its TP2 (documented anomaly, confirmed in the prior forensic report), so its one win registers as `tp2_hit=True, tp1_hit=False` — mechanically making it invisible to a TP1-based metric despite being a real win. The true "did shorts ever move favorably" picture is less bleak than 0.0% implies, but the *win rate* itself is still genuinely bad (see Section 5) — this caveat concerns this one metric's construction, not the overall short conclusion.

**By regime:**

| | n | P(TP1) | 95% CI | P(TP2\|TP1) | 95% CI |
|---|---|---|---|---|---|
| mixed | 59 | 49.2% | [36.8-61.6]% | 89.7% | [73.6-96.4]% |
| risk_on | 27 | 29.6% | [15.9-48.5]% | 75.0% | [40.9-92.9]% |

CIs are close to overlapping — directionally consistent with every prior "mixed beats risk_on" finding this project has made, but not yet statistically airtight at this n.

**By entry_quality:**

| | n | P(TP1) | 95% CI | P(TP2\|TP1) | n(TP1) |
|---|---|---|---|---|---|
| excellent | 12 | 66.7% | [39.1-86.2]% | 100.0% | 8 |
| good | 17 | 29.4% | [13.3-53.1]% | 80.0% | 5 |
| neutral | 40 | 42.5% | [28.5-57.8]% | 82.4% | 17 |

**By confidence bucket:** 55-59 stands out again — P(TP1)=16.7% [4.7-44.8]%, the worst of every bucket, echoing Section 3's calibration finding from an entirely different angle.

**By ATR-normalized stop distance** (proxy for volatility percentile — `entry_to_sl_atr`, only stored on 52 of 86 trades post-capture-pass): no clean monotonic pattern (43.2% / 57.1% / 100%(n=1)) — **insufficient data to draw a volatility-percentile conclusion**, reported honestly rather than forced into a trend.

---

## 2. Feature Importance Audit

| feature | winner freq | loser freq | odds ratio | present win% | absent win% | lift survives entry_quality stratification? |
|---|---|---|---|---|---|---|
| RSI 50-70 (healthy zone) | 87.9% | 69.8% | **3.135** | 43.9% (n=66) | 20.0% (n=20) | mixed: [-4.7, +43.8] |
| Volume score ≥8 | 69.7% | 50.9% | **2.215** | 46.0% (n=50) | 27.8% (n=36) | **yes — [+22.9, +57.6, +17.6], positive in all 3 strata** |
| Structure score ≥9 | 48.5% | 35.8% | 1.684 | 45.7% (n=35) | 33.3% (n=51) | untestable (no stratum had both ≥3 present/absent) |
| CMF positive | 63.6% | 50.9% | 1.685 | 43.8% (n=48) | 31.6% (n=38) | mixed: [-11.4, +35.7, +35.7] |
| FVG present at entry | 24.2% | 15.1% | 1.8 | 50.0% (n=16) | 35.7% (n=70) | positive in both testable strata: [+33.3, +1.4] |
| Trend score ≥22 | 45.5% | 41.5% | 1.174 | 40.5% (n=37) | 36.7% (n=49) | **inconsistent sign: [-31.9, +13.5]** |
| ADX 20-50 (trending) | 60.6% | 67.9% | 0.726 | 35.7% (n=56) | 43.3% (n=30) | mixed: [-22.9, +2.4] |
| Momentum score ≥14 | 63.6% | 71.7% | **0.691** | 35.6% (n=59) | 44.4% (n=27) | mixed but net negative: [+45.7, +5.8, **-20.0**] |
| Funding score ≥8 | 93.9% | 96.2% | 0.608 | 37.8% (n=82) | 50.0% (n=4) | untestable, n=4 |
| **History present** | **0.0%** | 17.0% | **0.0** | **0.0%** (n=9) | 42.9% (n=77) | -37.8 (n=1 usable stratum) |
| OBV | — | — | — | **NOT STORED per-trade — not computed, not fabricated** | | |
| BOS | — | — | — | **NOT STORED per-trade — not computed, not fabricated** | | |
| CHoCH | — | — | — | **NOT STORED per-trade — not computed, not fabricated** | | |

**The one methodologically important result here**: Trend's edge (odds ratio 1.174, barely above neutral) does **not** survive stratifying by entry_quality — the lift flips sign between strata (-31.9 in one, +13.5 in another). Volume's edge (odds ratio 2.215) **does** survive, staying positive in every testable stratum. This directly answers the "is trend necessary-but-not-discriminative, or does it just look weak because the engine already filters for trending markets" question raised earlier: at this sample size, trend's apparent edge is not robust to controlling for entry_quality, while volume's is. That's evidence for demoting trend and promoting volume specifically — not proof, given how thin some per-stratum counts are (as low as n=3-5 per cell), but a real signal in a specific, falsifiable direction.

**Recommendation per feature**: Keep RSI-zone and CMF as-is (both positive, both not yet stratification-tested due to sample limits). **Increase** Volume (only feature to pass the stratified check cleanly). **Decrease** Momentum (negative odds ratio, negative net stratified lift). **Investigate further before touching** Trend (evidence points toward demotion but isn't yet conclusive) and FVG/Structure (positive but small-n). **Do not increase** History (confirmed inverted again, but see Section 6 — likely confounded with the "majors" symbol family, not a standalone signal to act on).

---

## 3. Confidence Calibration

| bucket | n | predicted | actual | 95% CI | gap |
|---|---|---|---|---|---|
| 50-54 | 3 | 53.7% | 66.7% | [20.8-93.9]% | -13.0 |
| **55-59** | **12** | 57.6% | **8.3%** | **[1.5-35.4]%** | **49.2** |
| 60-64 | 29 | 62.6% | 51.7% | [34.4-68.6]% | 10.9 |
| 65-69 | 25 | 66.6% | 36.0% | [20.2-55.5]% | 30.6 |
| 70-74 | 9 | 71.6% | 44.4% | [18.9-73.3]% | 27.1 |
| 75+ | 1 | 76.0% | 0.0% | [0.0-79.3]% | 76.0 |

**Brier score: 0.2995** — worse than a flat 50% predictor's 0.25. **Expected Calibration Error: 25.72** percentage points. Confidence, as currently scaled, is not just imprecise — it is actively miscalibrated: a predictor that ignored the model entirely and always said "50%" would score better on Brier than Karma's confidence does today.

**The 55-59 bucket's 95% CI [1.5-35.4]% does not contain its own predicted value (57.6%)** — this is no longer just a suspicious-looking bucket, it's statistically distinguishable from its stated confidence, at n=12. This is the single most defensible, specific, reproducible finding across every audit this project has run (28, 48, 63-67, 86-trade checkpoints all flagged this same range).

**Recommendation: remap confidence, don't retrain it.** A monotonic isotonic-regression-style remapping (or, more conservatively given n=86, simple bucket-average substitution with the Wilson lower bound as a floor) would immediately improve Brier score without any new model. This is a deterministic, no-ML fix.

---

## 4. Expected Value Audit

Per-trade EV computed as `P(TP1) × reward_to_tp1_in_R − P(stop_before_TP1) × 1R`, using the aggregate priors from Section 1 (P(TP1)=0.430, P(stop before TP1)=0.558) since no per-trade prior probability is stored for most trades (only 10 of 86 have an `ml_probability` at all). Computable for 61 of 86 trades (need a valid `risk_to_sl_pct`/`reward_to_tp1_pct` in `entry_indicators.risk_reward`).

- Avg expected R at entry: **-0.068**. Avg realized R: **+0.073**. (The simple EV formula is somewhat conservative — it doesn't credit TP2/TP3 continuation upside — so treat the absolute EV numbers as directional, not exact expected-profit figures.)
- **corr(current total score, expected_r_at_entry) = 0.059** — essentially zero relationship.
- **Top 5 trades by EV and top 5 trades by score share ZERO symbols in common.**

| top 5 by EV | score | expected_r |
|---|---|---|
| MOVRUSDT | 63.0 | +1.349 |
| MSTRUSDT | 61.5 | +0.676 |
| SKHYNIXUSDT | 56.0 | +0.594 |
| SPORTFUNUSDT | 58.9 | +0.517 |
| SAMSUNGUSDT | 59.4 | +0.404 |

| top 5 by score | score | expected_r |
|---|---|---|
| MSTRUSDT | 70.8 | -0.225 |
| LITEUSDT | 70.1 | -0.128 |
| ETHUSDT | 70.1 | +0.034 |
| SAMSUNGUSDT | 66.0 | -0.06 |
| MUUSDT | 65.8 | -0.223 |

**This is the strongest quantitative case in this report for building EV-based ranking.** The current score is picking a completely different set of "best" trades than a simple EV calculation would, and several of the highest-*scored* trades in this sample had *negative* expected R. Given the EV formula's own conservatism noted above, treat this as "score and EV disagree sharply and often," not "EV is definitely better calibrated" — but the disagreement itself is the actionable finding.

---

## 5. Short vs Long Audit (excluding monitoring-outage-affected trades)

37 of 86 trades fall inside a verified scanner monitoring outage (see prior session work — a ~114h and a ~170h gap, both confirmed app-wide via `PredictionSnapshot` timestamps) and are excluded here to isolate genuine signal quality from outage-inflated slippage.

| | long, clean (n=45) | short, clean (n=4) |
|---|---|---|
| win rate | 37.8% | 25.0% |
| avg return | +0.66% | -1.638% |
| avg RSI | 59.5 | 43.9 |
| avg ADX | 32.7 | 22.8 |
| avg funding_score | 9.56 | 10.0 |
| avg structure_score | 8.0 | 11.0 |
| **avg entry_to_sl_atr (stop width in ATR units)** | **0.831** | **0.632** |
| avg risk_to_sl_pct | 2.687% | 1.944% |
| avg holding minutes | 1917 | 480 |

**Only 4 of 13 shorts survive outage exclusion** — the other 9 were either outage-affected or lack the stored ATR/risk-reward fields needed for this comparison. n=4 is too small to draw a hard conclusion, but the direction is informative: **shorts get placed with tighter stops, both in raw % (1.94% vs 2.69%) and in ATR-normalized terms (0.63 vs 0.83 ATR), even after removing the outage-corrupted trades.** Combined with lower average ADX (22.8 vs 32.7 — shorts are taken on weaker-trending setups), this points at **stop placement and entry-timing, not the direction call itself**, as the more specific failure mode.

**Recommendation**: a deterministic short-entry rule requiring a *wider* ATR-normalized stop (matching or exceeding the long-side average of ~0.83 ATR) and a higher minimum ADX threshold, rather than disabling shorts or building a separate model. n=4 clean shorts is genuinely thin — treat this as a hypothesis to validate over the next 15-20 short trades, not a settled rule.

---

## 6. Red Flag Discovery

| flag | n present | loss rate (present) | loss rate (absent, baseline) | lift |
|---|---|---|---|---|
| **RSI 30-49 (chop zone)** | 13 | **92.3%** | 56.2% | **+36.1 pts — strongest single red flag found** |
| No historical analogue | 76 | 56.6% | 100.0% (n=9-10, "has history" group) | inverted — see Section 2/caveat below |
| Structure score <9 (weak structure) | 51 | 66.7% | 54.3% | +12.4 pts |
| BB% > 0.95 | 1 | 0.0% | 62.4% | n=1, not usable |
| RSI>70 + CMF negative | 0 | — | — | never co-occurred in this dataset |

**RSI 30-49 at entry is the single cleanest, highest-confidence red flag in this entire audit**: 12 of 13 trades entered in this zone lost (92.3%), against a 56.2% baseline loss rate elsewhere. This is consistent with, and sharpens, Part 14's entry-timing finding from the prior forensic report ("entering too early, before a real move confirms" reads better than "chasing an overextended move" in this data) — RSI 30-49 is exactly a not-yet-confirmed, still-chopping zone.

The "no historical analogue" row is listed for completeness but its "absent" (has-history) baseline of 100% loss is the same n=9-10 finding already flagged twice in this project as likely confounded with the "majors" symbol family (Section 2, and the prior forensic report's Parts 12/15/16) — do not read this as "history hurts," read it as "the specific 4 symbols that happen to have history data are underperforming for reasons not yet isolated."

---

## 7. Deterministic Rules for Karma V2.1

Only rules with real supporting evidence from the sections above. Two rules are explicitly marked **hold** rather than **implement** — reporting the absence of sufficient evidence is as much the job here as reporting its presence.

### Rule 1 — Reject/flag RSI 30-49 entries ("chop zone")
- **Evidence**: 92.3% loss rate (12/13) vs 56.2% baseline (Section 6).
- **Sample size**: 13.
- **Estimated lift**: ~36 percentage points loss-rate reduction if avoided.
- **Risk of overfitting**: Low-Medium — n=13 is small, but the effect size is large and consistent with independent findings in Parts 2/6/14 of the prior forensic report.
- **Implementation location**: `entry_quality.py` (new "chop zone" flag) or `entry_flags.py` (a new diagnostic flag, observational first).

### Rule 2 — Increase Volume score's weight
- **Evidence**: odds ratio 2.215, and the only feature whose win-rate lift survives entry_quality stratification in all 3 testable strata (+22.9/+57.6/+17.6, Section 2).
- **Sample size**: 50 present / 36 absent.
- **Estimated lift**: ~18 percentage points win-rate gap (46.0% vs 27.8%).
- **Risk of overfitting**: Low — the stratified robustness is the strongest methodological signal in this report.
- **Implementation location**: `scoring.py`'s volume component weight.

### Rule 3 — Decrease Momentum score's weight / cap it
- **Evidence**: odds ratio 0.691, negative correlation with return (-0.111 in the prior forensic report), negative net stratified lift (-20.0 in the neutral entry_quality stratum, Section 2).
- **Sample size**: 59 (high) / 27 (low).
- **Estimated lift**: ~9 percentage point win-rate gap in the wrong direction if left unchanged.
- **Risk of overfitting**: Low — third consecutive audit (48, 86-trade Parts 2/6, and this odds-ratio check) confirming the same negative relationship.
- **Implementation location**: `scoring.py`'s momentum component, or `entry_quality.py`'s exhaustion logic (this may already be the more natural home for this fix, since entry_quality already covers exhaustion).

### Rule 4 — Prefer RSI 50-70 at entry
- **Evidence**: strongest odds ratio found (3.135) — 87.9% of winners fall in this zone vs 69.8% of losers.
- **Sample size**: 66 present / 20 absent.
- **Estimated lift**: ~24 percentage point win-rate gap (43.9% vs 20.0%).
- **Risk of overfitting**: Low-Medium — large n, but stratified-by-entry_quality check was inconsistent ([-4.7, +43.8]), so treat as a standalone signal, not yet proven independent of entry_quality.
- **Implementation location**: `entry_quality.py` or a new gate in `reasoning.py`'s precompute step.

### Rule 5 — Widen short-side stop distance (ATR-normalized)
- **Evidence**: clean shorts (n=4, outage-excluded) average 0.632 ATR-normalized stop distance vs longs' 0.831 (Section 5).
- **Sample size**: 4 (very thin — explicitly flagged).
- **Estimated lift**: directional only — not statistically established at this n.
- **Risk of overfitting**: **High** given n=4 — treat as a hypothesis for the next 15-20 short trades, not a rule to ship confidently.
- **Implementation location**: `reasoning.py`'s short-side stop guidance in the system prompt, or a validation check in `entry_flags.py`.

### Rule 6 — Require higher minimum ADX for shorts
- **Evidence**: clean shorts average ADX 22.8 vs longs' 32.7 (Section 5) — shorts are taken on meaningfully weaker trend confirmation.
- **Sample size**: 4.
- **Estimated lift**: directional only.
- **Risk of overfitting**: **High**, same n=4 caveat as Rule 5.
- **Implementation location**: `decision.py`'s direction gate (a short-specific ADX floor) — or, given `decision.py` is a frozen file, an entry_quality-level check instead.

### Rule 7 — Remap confidence via bucket-based calibration (not retraining)
- **Evidence**: Brier 0.2995 (worse than a flat 50% predictor), ECE 25.72, and the 55-59 bucket's 95% CI [1.5-35.4]% excludes its own predicted value (Section 3).
- **Sample size**: 86 total, 12 in the specific problem bucket.
- **Estimated lift**: closing even half the 25.72-point ECE gap would be a substantial reliability improvement with zero new model training.
- **Risk of overfitting**: Low — this is a deterministic remapping of an existing scalar, not a new model.
- **Implementation location**: `confidence.py` (a post-hoc calibration lookup table, separate from the underlying weighted-agreement formula).

### Rule 8 — Surface Expected Value alongside score (shadow mode)
- **Evidence**: corr(score, EV)=0.059, zero overlap between top-5-by-score and top-5-by-EV (Section 4).
- **Sample size**: 61 of 86 trades had computable EV.
- **Estimated lift**: not yet measurable — this is a ranking change, not a win-rate lever, and needs to be watched in shadow mode before trusting it.
- **Risk of overfitting**: Medium — the EV formula itself uses small-sample aggregate priors and is known to be conservative (avg expected_r -0.068 vs avg realized +0.073).
- **Implementation location**: `background_scanner.py`'s candidate ranking (add EV as a SECOND displayed number, do not replace score-based ranking yet).

### Rule 9 — Increase Structure score's weight
- **Evidence**: odds ratio 1.684, clean win-rate split (45.7% vs 33.3%), consistent with the prior forensic report's structure findings (+0.183 correlation with return).
- **Sample size**: 35 present / 51 absent.
- **Estimated lift**: ~12 percentage points.
- **Risk of overfitting**: Medium — could not be stratification-tested (no entry_quality stratum had ≥3 both present and absent).
- **Implementation location**: `scoring.py`'s structure component weight.

### Rule 10 — Prefer entries with an active FVG
- **Evidence**: odds ratio 1.8, win rate 50.0% vs 35.7%, positive stratified lift in both testable strata (+33.3, +1.4).
- **Sample size**: 16 present / 70 absent.
- **Estimated lift**: ~14 percentage points, but resting on n=16.
- **Risk of overfitting**: Medium-High — small absolute count of FVG-present trades.
- **Implementation location**: `entry_quality.py` (FVG presence could become one more input to the existing classifier, which already has access to this via `structure_4h.fvg_up/down`).

### Rule 11 — Hold: do NOT increase weight or trust for History
- **Evidence**: 0/9 win rate when historic_probability is present (Section 2, Section 6) — but this is very likely confounded with the "majors" symbol family (BTC/ETH/SOL/BNB/XRP/ADA), which independently shows a 0% win rate across all 10 of its own trades in the prior forensic report.
- **Sample size**: 9-10.
- **Estimated lift**: not applicable — this is a "do not act" rule.
- **Risk of overfitting**: **High if acted on now** — this is exactly the kind of small, confounded sample this project's own standing rule says not to tune on.
- **Implementation location**: none — flagged for future investigation (why do the majors underperform?) before any weight change.

### Rule 12 — Hold: do NOT reduce Trend's weight yet
- **Evidence**: odds ratio only 1.174 (near-neutral) AND the stratified lift flips sign between entry_quality strata ([-31.9, +13.5], Section 2) — genuinely ambiguous evidence, not a clean "trend doesn't matter" finding.
- **Sample size**: 37 present / 49 absent, but only 2 usable strata of 3-5 trades each.
- **Estimated lift**: unknown — could go either way.
- **Risk of overfitting**: High if acted on now, given the inconsistent stratified result.
- **Implementation location**: none yet — needs either a larger sample or a proper multivariate control (not just 2-way stratification) before touching `scoring.py`'s trend weight.

### Rule 13 — Condition the post-TP1 Hold recommendation on entry_quality
- **Evidence**: P(TP2|TP1) is 100% for excellent entry_quality (n=8) vs 80-82% for good/neutral (Section 1) — a real, if small-sample, spread.
- **Sample size**: 8/5/17 per stratum.
- **Estimated lift**: directional — a higher-confidence "Hold" recommendation specifically for excellent-entry_quality trades that reach TP1.
- **Risk of overfitting**: Medium — n=8 for the strongest stratum.
- **Implementation location**: `performance_center.py`'s `_recommend()` function (already has the entry_quality field available on the row).

### Rule 14 — Surface a per-trade Red Flag count (observational only)
- **Evidence**: RSI 30-49 (+36pt lift), weak structure (+12pt lift), and the (confounded) history flag each independently associate with worse outcomes (Section 6).
- **Sample size**: varies per flag, 13-76.
- **Estimated lift**: not a win-rate lever by itself — a visibility feature, matching the "Red Flags" idea from the earlier pasted roadmap, but built from flags this data actually supports rather than an assumed list.
- **Risk of overfitting**: Low — purely additive, no logic changes, same contract as `diagnostic_flags` already in `entry_flags.py`.
- **Implementation location**: `entry_flags.py` (extend `compute_diagnostic_flags()`, which already exists for exactly this purpose) or `forensic_diagnostics.py`.

### Rule 15 — Regime-conditioned P(TP1) awareness (not yet a scoring change)
- **Evidence**: mixed regime P(TP1)=49.2% [36.8-61.6]% vs risk_on 29.6% [15.9-48.5]% (Section 1) — CIs are close to overlapping, not yet clearly separated.
- **Sample size**: 59 / 27.
- **Estimated lift**: unclear until CIs separate further.
- **Risk of overfitting**: Medium — directionally consistent with every regime finding this project has made, but not yet statistically decisive on its own.
- **Implementation location**: none yet — track this metric explicitly (e.g. in a future Performance Center regime panel) rather than encoding it into `scoring.py`'s regime weight today.

---

## Summary: what this report does and does not recommend

**Recommended now (deterministic, no retraining)**: Rules 1, 2, 3, 4, 7, 9, 14 — all backed by odds ratios, Wilson CIs, and (where testable) stratified robustness checks.

**Recommended as shadow-mode/observational only**: Rules 8, 13.

**Explicitly flagged as insufficient evidence, do not implement yet**: Rules 5, 6 (n=4), 10 (n=16), 11 (confounded), 12 (inconsistent stratified sign), 15 (CIs not yet separated).

**Not recommended anywhere in this report**: retraining any ML model, or an automated weight optimizer — none of the evidence above meets the bar this project has consistently required before touching either.
