export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface LinePoint {
  time: number;
  value: number;
}

export interface ChartMarker {
  time: number;
  type: "bos_up" | "bos_down" | "choch" | "fvg_up" | "fvg_down";
  position: "aboveBar" | "belowBar" | "inBar";
  price: number;
  label: string;
  explain: string;
}

export interface OrderBlock {
  time_start: number;
  time_end: number;
  top: number;
  bottom: number;
  direction: "bullish" | "bearish";
  explain: string;
}

export interface ChartLevel {
  type: string;
  price: number | null;
  label: string;
  color: string;
  explain: string;
}

export interface ChartData {
  symbol: string;
  interval: string;
  candles: Candle[];
  ema20: LinePoint[];
  ema50: LinePoint[];
  ema200: LinePoint[];
  markers: ChartMarker[];
  order_blocks: OrderBlock[];
  levels: ChartLevel[];
}
