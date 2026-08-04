import type { Opportunity } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function fetchOpportunities(limit = 6): Promise<Opportunity[]> {
  const res = await fetch(`${API_BASE_URL}/api/opportunities?limit=${limit}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch opportunities: ${res.status}`);
  return res.json();
}

export async function fetchAnalysis(symbol: string): Promise<Opportunity> {
  const res = await fetch(`${API_BASE_URL}/api/analyze/${symbol}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch analysis for ${symbol}: ${res.status}`);
  return res.json();
}
