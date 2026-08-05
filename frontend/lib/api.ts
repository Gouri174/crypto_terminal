import type { Opportunity } from "./types";
import type { ChartData } from "./chart-types";

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

export async function fetchChart(
  symbol: string,
  interval = "4h",
  limit = 300
): Promise<ChartData> {
  const res = await fetch(
    `${API_BASE_URL}/api/chart/${symbol}?interval=${interval}&limit=${limit}`,
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error(`Failed to fetch chart for ${symbol}: ${res.status}`);
  return res.json();
}

/**
 * Opens a websocket to the background scanner and calls onUpdate() whenever
 * it broadcasts that a scan cycle finished — the caller re-fetches via the
 * REST endpoint rather than trusting a pushed payload, keeping this dumb
 * and hard to get out of sync. Auto-reconnects on drop. Returns a cleanup
 * function.
 */
export function subscribeToScannerUpdates(onUpdate: () => void): () => void {
  const wsUrl = `${API_BASE_URL.replace(/^http/, "ws")}/ws/opportunities`;
  let socket: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let stopped = false;

  const connect = () => {
    if (stopped) return;
    socket = new WebSocket(wsUrl);
    socket.onmessage = () => onUpdate();
    socket.onclose = () => {
      if (!stopped) reconnectTimer = setTimeout(connect, 5000);
    };
    socket.onerror = () => socket?.close();
  };

  connect();

  return () => {
    stopped = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    socket?.close();
  };
}
