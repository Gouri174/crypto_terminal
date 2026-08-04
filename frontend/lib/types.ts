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
  historical_comparison: string | null;
  summary: string;
  disclaimer: string;
}

export interface Opportunity {
  symbol: string;
  score: number;
  last_price: number;
  change_24h_pct: number;
  trade_plan: TradePlan;
}
