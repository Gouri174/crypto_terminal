import type { RegimeInfo } from "@/lib/types";

const LABELS: Record<string, string> = {
  risk_on: "Risk ON",
  risk_off: "Risk OFF",
  mixed: "Mixed / Transitional",
};

function labelColor(label: string) {
  if (label === "risk_on") return "text-bull border-bull";
  if (label === "risk_off") return "text-bear border-bear";
  return "text-yellow-400 border-yellow-500";
}

export default function RegimeBanner({ regime }: { regime: RegimeInfo }) {
  return (
    <div className="rounded-lg border border-border bg-panel px-4 py-3 mb-6 flex items-center justify-between flex-wrap gap-2">
      <div className="flex items-center gap-3">
        <span
          className={`text-xs uppercase font-bold px-2 py-1 rounded border ${labelColor(
            regime.label
          )}`}
        >
          {LABELS[regime.label] ?? regime.label}
        </span>
        <span className="text-sm text-gray-300 capitalize">{regime.trend} trend</span>
        <span className="text-xs text-gray-500">Confidence {regime.confidence}%</span>
      </div>
      <div className="text-xs text-gray-500">
        {regime.breadth_bullish_pct}% of {regime.universe_size} coins bullish · BTC{" "}
        {regime.btc_trend}
      </div>
    </div>
  );
}
