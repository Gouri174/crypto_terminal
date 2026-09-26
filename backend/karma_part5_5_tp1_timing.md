# Part 5.5 — TP1 timing analysis

| Interval (hours) | n | P25 | median | P75 | P90 | max |
|---|---|---|---|---|---|---|
| Entry → TP1 | 53 | 1.8 | 9.1 | 114.6 | 132.4 | 265.6 |
| TP1 → TP2 | 45 | 0.0 | 0.7 | 18.4 | 267.2 | 348.9 |
| TP1 → stop (TP1-then-loss trades) | 9 | 10.4 | 111.3 | 274.8 | 297.8 | 307.4 |

TP1-reachers with timestamps: n=53 of 54. Times are as recorded by the monitor, so any interval that spans a monitoring gap is stretched (detection delay); the gap-free rows below control for that.
| Gap-free trades only | n | P25 | median | P75 | P90 | max |
|---|---|---|---|---|---|---|
| Entry → TP1 | 9 | 1.4 | 2.1 | 4.0 | 4.1 | 4.1 |
| TP1 → TP2 | 9 | 0.3 | 0.7 | 2.2 | 3.6 | 6.1 |

| Fast (TP1 within median 9.1h) vs slow | n | P(TP2) | P(TP3) | P(final loss) | Avg ret% | Median ret% |
|---|---|---|---|---|---|---|
| Fast TP1 | 27 | 81.5% | 18.5% | 22.2% | 11.72 | 5.63 |
| Slow TP1 | 26 | 88.5% | 34.6% | 11.5% | 11.35 | 7.02 |

Do fast-TP1 trades behave differently? Final-loss rate fast vs slow: OR 0.46, Fisher p=0.4672 (n=27/26) → NOT SUPPORTED. Correlation between hours-to-TP1 and return: Spearman 0.151.
| Time to TP1 bucket | n | P(TP2) | P(TP3) | P(final loss) | Avg ret% | Median ret% |
|---|---|---|---|---|---|---|
| <1h | 6 | 66.7% | 16.7% | 33.3% | 21.29 | 8.86 |
| 1–6h | 17 | 82.4% | 23.5% | 17.6% | 11.41 | 5.70 |
| 6–24h | 7 | 85.7% | 14.3% | 28.6% | -2.75 | 2.93 |
| >24h | 23 | 91.3% | 34.8% | 8.7% | 13.45 | 7.50 |

**Trailing-stop timeout guidance (from TP1→TP2 times):** share of eventual TP2 hits that arrived within X hours of TP1: ≤1h: 56%, ≤4h: 69%, ≤12h: 73%, ≤24h: 80%, ≤72h: 82% (n=45).
**Reversal speed:** among TP1-then-loss trades, time from TP1 to the stop exit: ≤1h: 0%, ≤4h: 22%, ≤12h: 33%, ≤24h: 44%, ≤72h: 44% (n=9); 5 of the 9 exited inside a monitoring gap, so these durations are upper bounds.
Any timeout/trail parameter derived here is POSSIBLE at best (n small, intervals gap-stretched); the only shippable outcome is to LOG these timestamps for every TP1 trade (already stored: `tp1_hit_at`, `tp2_hit_at`, plus highest excursion/lowest retrace after TP1 to be added in shadow mode).