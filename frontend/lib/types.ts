export interface ScoreBreakdown {
  trend: number;
  momentum: number;
  volume: number;
  funding: number;
  structure: number;
  history: number;
  regime: number;
  risk: number;
  total: number;
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

export interface TradePlan {
  symbol: string;
  recommendation: "long" | "short" | "no_trade" | string;
  confidence: number;
  entry_low: number | null;
  entry_high: number | null;
  stop_loss: number | null;
  take_profit_1: number | null;
  take_profit_2: number | null;
  risk_level: string;
  time_horizon: string;
  risk_reward: string | null;
  market_regime: string | null;
  reasons_for: string[];
  reasons_against: string[];
  invalidation: string | null;
  historical_comparison: string | null;
  summary: string;
  score_breakdown: ScoreBreakdown | null;
  history_match: HistoryMatch | null;
  disclaimer: string;
}

export interface LifecycleEvent {
  at: number;
  status: string;
  reason: string;
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
