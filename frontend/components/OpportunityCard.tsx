import Link from "next/link";
import type { Opportunity } from "@/lib/types";
import { lifecycleColor, lifecycleLabel } from "@/lib/lifecycle";

function recColor(rec: string) {
  if (rec === "long") return "text-bull border-bull";
  if (rec === "short") return "text-bear border-bear";
  return "text-gray-400 border-gray-600";
}

export default function OpportunityCard({ opp }: { opp: Opportunity }) {
  const { trade_plan: plan } = opp;

  return (
    <Link
      href={`/coin/${opp.symbol}`}
      className="block rounded-lg border border-border bg-panel p-4 hover:border-gray-500 transition-colors"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-lg">{opp.symbol}</span>
        <span
          className={`text-xs uppercase font-bold px-2 py-1 rounded border ${recColor(
            plan.recommendation
          )}`}
        >
          {plan.recommendation.replace("_", " ")}
        </span>
      </div>

      <div className="flex items-center justify-between mb-3">
        <div className="text-sm text-gray-400">
          ${opp.last_price.toLocaleString()}{" "}
          <span className={opp.change_24h_pct >= 0 ? "text-bull" : "text-bear"}>
            {opp.change_24h_pct >= 0 ? "+" : ""}
            {opp.change_24h_pct.toFixed(2)}%
          </span>
        </div>
        <span
          className={`text-[10px] uppercase font-semibold px-2 py-0.5 rounded border ${lifecycleColor(
            opp.lifecycle_status
          )}`}
        >
          {lifecycleLabel(opp.lifecycle_status)}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm mb-3">
        <div>
          <div className="text-gray-500 text-xs">Confidence</div>
          <div>{plan.confidence}%</div>
        </div>
        <div>
          <div className="text-gray-500 text-xs">Score</div>
          <div>{opp.score}</div>
        </div>
        {plan.entry_low != null && (
          <div>
            <div className="text-gray-500 text-xs">Entry</div>
            <div>
              {plan.entry_low}
              {plan.entry_high && plan.entry_high !== plan.entry_low
                ? `–${plan.entry_high}`
                : ""}
            </div>
          </div>
        )}
        {plan.stop_loss != null && (
          <div>
            <div className="text-gray-500 text-xs">Stop Loss</div>
            <div className="text-bear">{plan.stop_loss}</div>
          </div>
        )}
      </div>

      <p className="text-sm text-gray-300 line-clamp-3">{plan.summary}</p>
    </Link>
  );
}
