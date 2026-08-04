"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { fetchAnalysis } from "@/lib/api";
import type { Opportunity } from "@/lib/types";

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

      <div className="mt-4 rounded-lg border border-border bg-panel p-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold">{data.symbol}</h1>
          <span className="text-xl">${data.last_price.toLocaleString()}</span>
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

        {plan.historical_comparison && (
          <Section title="Historical Comparison">
            <p className="text-gray-300">{plan.historical_comparison}</p>
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
