const LABELS: Record<string, string> = {
  WAIT: "Wait",
  PREPARE: "Prepare",
  BUY_NOW: "Buy Now",
  MOVE_STOP_TO_ENTRY: "Move Stop to Entry",
  TAKE_PARTIAL_PROFIT: "Take Partial Profit",
  HOLD: "Hold",
  EXIT_TARGET: "Exit — Target Hit",
  EXIT_STOPPED: "Exit — Stopped Out",
};

export function lifecycleLabel(status: string): string {
  return LABELS[status] ?? status;
}

export function lifecycleColor(status: string): string {
  if (status === "BUY_NOW" || status === "TAKE_PARTIAL_PROFIT" || status === "EXIT_TARGET") {
    return "text-bull border-bull";
  }
  if (status === "EXIT_STOPPED") return "text-bear border-bear";
  if (status === "PREPARE" || status === "MOVE_STOP_TO_ENTRY") return "text-yellow-400 border-yellow-500";
  if (status === "HOLD") return "text-blue-400 border-blue-500";
  return "text-gray-400 border-gray-600";
}
