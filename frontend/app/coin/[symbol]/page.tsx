"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { fetchAnalysis } from "@/lib/api";
import type { Opportunity, ScoreBreakdown } from "@/lib/types";
import { lifecycleColor, lifecycleLabel } from "@/lib/lifecycle";
import RegimeBanner from "@/components/RegimeBanner";

export default function CoinDetailPage({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol } = use(params);
  const [data, setData] = useState<Opportunity | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAnalysis(symbol)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [symbol]);

  if (error) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-10">
        <Link href="/" className="text-sm text-gray-400 hover:underline">
          ← Back
        </Link>
        <div className="mt-4 rounded border border-bear text-bear p-4">{error}</div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-10">
        <div className="text-gray-500">Running full analysis for {symbol}…</div>
      </main>
    );
  }

  const { trade_plan: plan } = data;

  return (
    <main className="max-w-3xl mx-auto px-6 py-10">
      <Link href="/" className="text-sm text-gray-400 hover:underline">
        ← Back
      </Link>

      {data.regime && <div className="mt-4"><RegimeBanner regime={data.regime} /></div>}

      <div className="rounded-lg border border-border bg-panel p-6">
        <div className="flex items-center justify-between mb-1">
          <h1 className="text-2xl font-bold">{data.symbol}</h1>
          <span className="text-xl">${data.last_price.toLocaleString()}</span>
        </div>

        <div className="mb-4">
          <span
            className={`text-xs uppercase font-semibold px-2 py-1 rounded border ${lifecycleColor(
              data.lifecycle_status
            )}`}
          >
            {lifecycleLabel(data.lifecycle_status)}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6 text-sm">
          <Field label="Recommendation" value={plan.recommendation.replace("_", " ")} />
          <Field label="Confidence" value={`${plan.confidence}%`} />
          <Field label="Risk Level" value={plan.risk_level} />
          <Field label="Time Horizon" value={plan.time_horizon} />
          <Field label="Entry" value={fmtRange(plan.entry_low, plan.entry_high)} />
          <Field label="Stop Loss" value={plan.stop_loss ?? "—"} />
          <Field label="Take Profit 1" value={plan.take_profit_1 ?? "—"} />
          <Field label="Take Profit 2" value={plan.take_profit_2 ?? "—"} />
        </div>

        {plan.score_breakdown && (
          <Section title="Why This Score — Computed, Not Guessed">
            <ScoreBars breakdown={plan.score_breakdown} />
          </Section>
        )}

        <Section title="AI Summary">
          <p className="text-gray-300">{plan.summary}</p>
        </Section>

        {plan.reasons_for.length > 0 && (
          <Section title="Reasons Supporting Trade">
            <ul className="list-disc list-inside text-gray-300 space-y-1">
              {plan.reasons_for.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </Section>
        )}

        {plan.reasons_against.length > 0 && (
          <Section title="Reasons Against Trade">
            <ul className="list-disc list-inside text-gray-300 space-y-1">
              {plan.reasons_against.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </Section>
        )}

        {plan.invalidation && (
          <Section title="Invalidation Point">
            <p className="text-gray-300">{plan.invalidation}</p>
          </Section>
        )}

        <Section title="Historical Similarity">
          {plan.history_match ? (
            <HistoryMatchCard match={plan.history_match} />
          ) : (
            <p className="text-gray-500 text-sm">
              Not enough stored history for {data.symbol} yet — this is a real
              limitation, not a fabricated stat. Historical similarity fills in
              as the system backfills and accumulates more market data for
              this symbol.
            </p>
          )}
          {plan.historical_comparison && (
            <p className="text-gray-300 mt-2">{plan.historical_comparison}</p>
          )}
        </Section>

        {data.lifecycle_history.length > 0 && (
          <Section title="Live Reasoning Timeline">
            <ul className="space-y-2">
              {[...data.lifecycle_history].reverse().map((ev, i) => (
                <li key={i} className="text-sm border-l-2 border-border pl-3">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-500 text-xs">
                      {new Date(ev.at).toLocaleTimeString()}
                    </span>
                    <span
                      className={`text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded border ${lifecycleColor(
                        ev.status
                      )}`}
                    >
                      {lifecycleLabel(ev.status)}
                    </span>
                  </div>
                  <p className="text-gray-300">{ev.reason}</p>
                </li>
              ))}
            </ul>
          </Section>
        )}

        <p className="text-xs text-gray-600 mt-6 border-t border-border pt-4">
          {plan.disclaimer}
        </p>
      </div>
    </main>
  );
}

function fmtRange(lo: number | null, hi: number | null) {
  if (lo == null) return "—";
  if (hi == null || hi === lo) return `${lo}`;
  return `${lo}–${hi}`;
}

function Field({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="text-gray-500 text-xs">{label}</div>
      <div className="capitalize">{value}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <h2 className="text-sm font-semibold text-gray-400 mb-2">{title}</h2>
      {children}
    </div>
  );
}

const SCORE_ROWS: {
  key: keyof ScoreBreakdown;
  label: string;
  max: number;
  signed?: boolean;
}[] = [
  { key: "trend", label: "Trend", max: 25 },
  { key: "momentum", label: "Momentum", max: 15 },
  { key: "volume", label: "Volume", max: 10 },
  { key: "funding", label: "Funding", max: 10 },
  { key: "structure", label: "Market Structure", max: 15 },
  { key: "history", label: "History Match", max: 15 },
  { key: "regime", label: "Market Regime Fit", max: 5, signed: true },
  { key: "risk", label: "Risk Penalty", max: 20, signed: true },
];

function ScoreBars({ breakdown }: { breakdown: ScoreBreakdown }) {
  return (
    <div className="space-y-2">
      {SCORE_ROWS.map(({ key, label, max, signed }) => {
        const value = breakdown[key];
        const pct = max > 0 ? Math.min(100, (Math.abs(value) / max) * 100) : 0;
        const isNegative = value < 0;
        const display = signed ? `${value > 0 ? "+" : ""}${value}` : `${value}/${max}`;
        return (
          <div key={key} className="flex items-center gap-3 text-sm">
            <div className="w-36 text-gray-400 shrink-0">{label}</div>
            <div className="flex-1 h-2 rounded bg-border overflow-hidden">
              <div
                className={isNegative ? "h-full bg-bear" : "h-full bg-bull"}
                style={{ width: `${pct}%` }}
              />
            </div>
            <div className="w-16 text-right tabular-nums">{display}</div>
          </div>
        );
      })}
      <div className="flex items-center gap-3 text-sm font-semibold pt-1 border-t border-border">
        <div className="w-36 text-gray-300 shrink-0">Total</div>
        <div className="flex-1" />
        <div className="w-16 text-right tabular-nums">{breakdown.total}/100</div>
      </div>
    </div>
  );
}

function HistoryMatchCard({
  match,
}: {
  match: NonNullable<import("@/lib/types").TradePlan["history_match"]>;
}) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
      <Field label="Similar situations found" value={match.sample_size} />
      <Field label="Of history available" value={match.total_history_available} />
      <Field label="Win rate" value={`${match.win_rate}%`} />
      <Field label="Mean return" value={`${match.mean_return_pct}%`} />
      <Field label="Median return" value={`${match.median_return_pct}%`} />
      {match.avg_drawdown_pct != null && (
        <Field label="Avg drawdown" value={`${match.avg_drawdown_pct}%`} />
      )}
    </div>
  );
}
