import type { Opportunity } from "./types";

export async function fetchOpportunities(limit = 6): Promise<Opportunity[]> {
  const res = await fetch(`/api/opportunities?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch opportunities: ${res.status}`);
  return res.json();
}

export async function fetchAnalysis(symbol: string): Promise<Opportunity> {
  const res = await fetch(`/api/analyze/${symbol}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch analysis for ${symbol}: ${res.status}`);
  return res.json();
}
