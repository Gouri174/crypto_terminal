export interface ScoreBreakdown {
  trend: number;
  momentum: number;
  volume: number;
  funding: number;
  structure: number;
  history: number;
  regime: number;
  ml: number;
  sentiment: number;
  liquidity: number;
  risk: number;
  total: number;
}

export interface MLPrediction {
  win_probability: number;
  large_drawdown_probability: number;
}

export interface HorizonReturn {
  horizon: string;
  mean_return_pct: number;
  sample_size: number;
}

export interface HistoryMatch {
  sample_size: number;
  total_history_available: number;
  mean_return_pct: number;
  median_return_pct: number;
  win_rate: number;
  avg_drawdown_pct: number | null;
  horizon_candles: number | null;
  most_similar_return_pct: number | null;
  largest_gain_pct: number | null;
  largest_loss_pct: number | null;
  most_similar_dates: string[];
  horizon_returns: HorizonReturn[];
  key_difference: string | null;
}

export interface RegimeInfo {
  label: "risk_on" | "risk_off" | "mixed" | string;
  trend: "bullish" | "bearish" | "ranging" | "transitional" | string;
  confidence: number;
  btc_trend: string;
  breadth_bullish_pct: number;
  breadth_bearish_pct: number;
  universe_size: number;
  summary: string;
}

export interface ConfidenceBreakdown {
  components: Record<string, number>;
  penalties: string[];
}

export interface AlternativeTrade {
  symbol: string;
  reason: string;
}

export interface TradePlan {
  symbol: string;
  recommendation: "long" | "short" | "no_trade" | string;
  confidence: number;
  grade: string | null;
  confidence_breakdown: ConfidenceBreakdown | null;
  checklist: Record<string, boolean>;
  thesis: string | null;
  alternative_trade: AlternativeTrade | null;
  entry_low: number | null;
  entry_high: number | null;
  stop_loss: number | null;
  take_profit_1: number | null;
  take_profit_2: number | null;
  take_profit_3: number | null;
  risk_level: string;
  time_horizon: string;
  risk_reward: string | null;
  market_regime: string | null;
  // Entry-timing/exhaustion classification — app/engine/entry_quality.py.
  // Deterministic, computed before Claude runs; a hypothesis/measurement
  // layer, not a hard filter yet.
  entry_quality: string | null; // "excellent" | "good" | "neutral" | "late" | "exhausted" | "invalid"
  entry_quality_score: number | null;
  entry_quality_reasons: string[];
  reasons_for: string[];
  reasons_against: string[];
  invalidation: string | null;
  historical_comparison: string | null;
  bullish_scenario: string | null;
  bearish_scenario: string | null;
  biggest_risks: string[];
  evidence_that_would_increase_confidence: string | null;
  summary: string;
  score_breakdown: ScoreBreakdown | null;
  history_match: HistoryMatch | null;
  ml_prediction: MLPrediction | null;
  disclaimer: string;
}

export interface LifecycleEvent {
  at: number;
  status: string;
  reason: string;
  // Added later — events written before this field existed won't have it.
  // See app/engine/lifecycle.py:plan_signature; identical signature means
  // "same trade," a changed one marks a new trade cycle for this symbol.
  signature?: string;
}

// One row from GET /api/outcomes?symbol=X — a real, resolved-or-open trade
// record, distinct from the always-current LiveOpportunity/TradePlan.
export interface TradeOutcomeSummary {
  id: number;
  created_at: number;
  symbol: string;
  direction: string;
  entry_low: number;
  entry_high: number;
  entry: number;
  stop_loss: number;
  tp1: number | null;
  tp2: number | null;
  tp3: number | null;
  status: string; // "pending" | "open" | "closed_win" | "closed_loss" | "closed_stale" | "invalidated"
  confidence: number | null;
  grade: string | null;
  realized_return_pct: number | null;
  exit_time: number | null;
}

export interface Opportunity {
  symbol: string;
  score: number;
  last_price: number;
  change_24h_pct: number;
  trade_plan: TradePlan;
  lifecycle_status: string;
  lifecycle_history: LifecycleEvent[];
  regime: RegimeInfo | null;
}
