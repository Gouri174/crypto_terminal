"use client";

import { useEffect, useState } from "react";
import { fetchOpportunities, subscribeToScannerUpdates } from "@/lib/api";
import type { Opportunity } from "@/lib/types";
import OpportunityCard from "@/components/OpportunityCard";
import RegimeBanner from "@/components/RegimeBanner";

export default function DashboardPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    const load = () => {
      fetchOpportunities(6)
        .then((data) => {
          setOpportunities(data);
          setLastUpdated(new Date());
          setError(null);
        })
        .catch((e) => setError(e.message));
    };

    load();
    const unsubscribe = subscribeToScannerUpdates(load);
    setLive(true);
    return unsubscribe;
  }, []);

  return (
    <main className="max-w-6xl mx-auto px-6 py-10">
      <header className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <h1 className="text-2xl font-bold">Today&apos;s AI Trade Opportunities</h1>
          {live && (
            <span className="flex items-center gap-1 text-xs text-bull">
              <span className="w-2 h-2 rounded-full bg-bull animate-pulse" />
              LIVE
            </span>
          )}
        </div>
        <p className="text-sm text-gray-400">
          AI-generated analysis of Binance USDT-perpetual futures. Estimates, not
          guarantees — always confirm risk yourself before trading.
        </p>
        {lastUpdated && (
          <p className="text-xs text-gray-600 mt-1">
            Last updated {lastUpdated.toLocaleTimeString()} — the background
            engine keeps recomputing continuously and pushes updates here
            automatically.
          </p>
        )}
      </header>

      {error && (
        <div className="rounded border border-bear text-bear p-4 mb-6">
          {error}. Is the backend running on :8000 with ANTHROPIC_API_KEY set?
        </div>
      )}

      {opportunities?.[0]?.regime && <RegimeBanner regime={opportunities[0].regime} />}

      {!opportunities && !error && (
        <div className="text-gray-500">Scanning markets and running AI analysis…</div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {opportunities?.map((opp) => (
          <OpportunityCard key={opp.symbol} opp={opp} />
        ))}
      </div>

      <footer className="mt-10 text-xs text-gray-600 border-t border-border pt-4">
        Not financial advice. AI-generated trade plans are probabilistic estimates
        based on current market data, not predictions of future outcomes. No trade
        is guaranteed to succeed. This tool does not execute trades.
      </footer>
    </main>
  );
}
