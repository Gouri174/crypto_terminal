# Score Recalibration Report — Measurement Only

**No scoring.py weights are changed by this report.** This replaces the V2.1-C commit's direct edits to `scoring.py` (reverted in the very next commit) — per explicit instruction, measurement and implementation are now two separate, separately-approved steps. Computed by `analysis_score_recalibration.py` against the live DB (86 resolved trades, 33 wins, overall win rate 38.4%). Full machine-readable output: `feature_importance.json`.

## Methodology — and why this supersedes `karma_v2_1_model_improvement_report.md`'s Section 2

The earlier report ranked features by odds ratio and a rough entry_quality-stratified lift check, but never applied a formal significance test. This report adds **Fisher's exact test** (the correct test for a small-sample 2×2 win/loss table — more conservative than a chi-square or z-test at these sample sizes) and **information gain** (entropy reduction in bits) alongside the same odds ratio and Wilson CI. The result is a materially more cautious picture than the earlier report implied:

**At conventional p<0.05, only 2 of 12 measurable features are statistically significant — and one of those two is in the "don't act" direction.**

## Full results

| feature | n present/absent | win rate present | win rate absent | odds ratio | **p-value (Fisher exact)** | info gain (bits) | lift vs overall |
|---|---|---|---|---|---|---|---|
| entry_quality_excellent | 12/57 | 66.7% [39.1-86.2]% | 33.3% | 4.0 | **0.0495** | 0.224 | +28.3 pts |
| rsi_healthy_50_70 | 66/15 | 43.9% [32.6-55.9]% | 13.3% | 5.095 | **0.0384** | 0.103 | +5.5 pts |
| history_present | 9/77 | 0.0% [0-29.9]% | 42.9% | 0.0 | **0.0113** | 0.079 | **-38.4 pts** |
| regime_mixed | 59/27 | 45.8% [33.7-58.3]% | 22.2% | 2.953 | 0.0552 (borderline) | 0.038 | +7.4 pts |
| fvg_present | 16/32 | 50.0% [28.0-72.0]% | 40.6% | 1.462 | 0.5553 | 0.412* | +11.6 pts |
| volume_high (≥8) | 50/36 | 46.0% [33.0-59.6]% | 27.8% | 2.215 | 0.1163 | 0.025 | +7.6 pts |
| structure_high (≥9) | 35/51 | 45.7% [30.5-61.8]% | 33.3% | 1.684 | 0.2674 | 0.011 | +7.3 pts |
| cmf_positive | 48/13 | 43.8% [30.7-57.7]% | 38.5% | 1.244 | 1.0 | 0.264* | +5.4 pts |
| trend_high (≥22) | 37/49 | 40.5% [26.3-56.5]% | 36.7% | 1.174 | 0.8236 | 0.001 | +2.1 pts |
| adx_trending_20_50 | 56/25 | 35.7% [24.5-48.8]% | 44.0% | 0.707 | 0.6212 | 0.061 | -2.7 pts |
| momentum_high (≥14) | 59/27 | 35.6% [24.6-48.3]% | 44.4% | 0.691 | 0.4792 | 0.005 | -2.8 pts |
| funding_high (≥8) | 82/4 | 37.8% [28.1-48.6]% | 50.0% | 0.608 | 0.636 | 0.002 | -0.6 pts |
| OBV | — | — | — | — | — | — | **not stored per-trade anywhere in this codebase** |
| BOS | — | — | — | — | — | — | **not stored per-trade anywhere in this codebase** |
| CHoCH | — | — | — | — | — | — | **not stored per-trade anywhere in this codebase** |

*fvg_present and cmf_positive show inflated information-gain figures relative to their weak p-values — a reminder that information gain alone, without a significance test alongside it, would have been misleading on its own. This is exactly the kind of number that looked more convincing in isolation than it should have.

## What this means for the V2.1-C weight changes that were reverted

- **Momentum reduction (odds ratio 0.691)**: p=0.4792. **Not statistically significant** — entirely consistent with random variation at this sample size. The reverted change was not wrong to suspect, but it was not "measured," it was "noticed and acted on."
- **Volume increase (odds ratio 2.215)**: p=0.1163. Suggestive, not significant. The earlier report's "stratified lift survived in every entry_quality bucket" check is real and worth keeping in mind, but it doesn't substitute for a significance test on the aggregate relationship, which this is short of clearing.
- **Structure/FVG increase**: p=0.2674 (structure) and p=0.5553 (FVG). Neither is significant. FVG in particular is n=16 present — too small for its odds ratio to mean much on its own, exactly as the earlier report itself flagged as "medium risk."

**Reverting these three was the right call.** None of them would have passed a pre-registered significance threshold; they were promoted from "interesting odds ratio" to "shipped weight change" without that check.

## What DOES clear a real bar

- **entry_quality == excellent** (p=0.0495): the strongest, most defensible finding in this whole analysis. 66.7% win rate vs 33.3% baseline, and it's not a new discovery — every audit this project has run has found entry_quality to be its best-performing feature. This is not a reason to touch `scoring.py` (entry_quality already exists as its own separate classifier, not a scoring.py component) but it does reinforce that entry_quality is the one feature this project should keep trusting.
- **RSI 50-70** (p=0.0384): real, and consistent with the "chop zone" (RSI 30-49) finding from the earlier report — but notice the earlier report's specific momentum-formula rewrite (which folded this RSI finding INTO a weight change) is exactly the kind of move this report is now cautioning against making again without a separate checkpoint.
- **history_present** (p=0.0113, but inverted): statistically real, but in the "having history data associates with LOSING" direction — and n=9 is confounded with the "majors" symbol family per the earlier forensic report (Rule 11). This is a genuine, significant finding, and the correct action is still **do not act on it** — the statistical significance describes a real pattern in this specific sample, not necessarily a causal, generalizable one, given the confound.

## Recommendation

**Do not edit `scoring.py` from this report alone.** Three features (entry_quality, RSI zone, history-absence) show real statistical signal; none of them cleanly map onto a `scoring.py` weight change without either (a) already existing as a separate classifier (entry_quality) or (b) being confounded with something else (history). The two components the reverted commit actually touched (momentum, volume) are NOT statistically significant at n=86.

**Next checkpoint, not automatic**: re-run this exact analysis at a larger n (the earlier report suggested milestones around 100-150 trades for calibration/weight work) and look specifically at whether momentum's and volume's odds ratios sharpen (p-value drops) or regress toward 1.0 (revealing they were noise). Only revisit `scoring.py` once that re-run, at a larger n, independently clears a real significance threshold — not from re-reading this same 86-trade sample more carefully.
