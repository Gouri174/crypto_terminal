"use client";

import { useEffect, useRef, useState } from "react";
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  LineSeries,
  LineStyle,
  ColorType,
  type IChartApi,
  type ISeriesApi,
  type SeriesMarker,
  type Time,
} from "lightweight-charts";
import { fetchChart } from "@/lib/api";
import type { ChartData, ChartLevel, ChartMarker, OrderBlock } from "@/lib/chart-types";

const MARKER_SHAPE: Record<ChartMarker["type"], "arrowUp" | "arrowDown" | "circle" | "square"> = {
  bos_up: "arrowUp",
  bos_down: "arrowDown",
  choch: "circle",
  fvg_up: "square",
  fvg_down: "square",
};

const MARKER_COLOR: Record<ChartMarker["type"], string> = {
  bos_up: "#26a69a",
  bos_down: "#ef5350",
  choch: "#facc15",
  fvg_up: "#3b82f6",
  fvg_down: "#f97316",
};

export default function ChartPanel({ symbol }: { symbol: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [data, setData] = useState<ChartData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<{ label: string; explain: string } | null>(null);

  useEffect(() => {
    fetchChart(symbol).then(setData).catch((e) => setError(e.message));
  }, [symbol]);

  useEffect(() => {
    if (!data || !containerRef.current) return;
    const container = containerRef.current;

    const measureWidth = () =>
      container.clientWidth || container.getBoundingClientRect().width || 800;

    // Deliberately NOT using the `autoSize` option: it relies on
    // ResizeObserver, which only fires as part of an active rendering/paint
    // pipeline and is a no-op in a backgrounded/non-composited tab. An
    // explicit width avoids that dependency entirely.
    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#9ca3af",
      },
      grid: {
        vertLines: { color: "#232838" },
        horzLines: { color: "#232838" },
      },
      width: measureWidth(),
      height: 420,
      timeScale: { timeVisible: true },
    });
    chartRef.current = chart;

    const candleSeries: ISeriesApi<"Candlestick"> = chart.addSeries(CandlestickSeries, {
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderVisible: false,
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
    });
    candleSeries.setData(data.candles.map((c) => ({ ...c, time: c.time as Time })));

    const addEma = (points: ChartData["ema20"], color: string) => {
      const series = chart.addSeries(LineSeries, { color, lineWidth: 1 });
      series.setData(points.map((p) => ({ time: p.time as Time, value: p.value })));
    };
    addEma(data.ema20, "#60a5fa");
    addEma(data.ema50, "#f59e0b");
    addEma(data.ema200, "#a78bfa");

    for (const level of data.levels) {
      if (level.price == null) continue;
      candleSeries.createPriceLine({
        price: level.price,
        color: level.color,
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: level.label,
      });
    }

    if (data.markers.length > 0) {
      const seriesMarkers: SeriesMarker<Time>[] = data.markers.map((m) => ({
        time: m.time as Time,
        position: m.position,
        color: MARKER_COLOR[m.type],
        shape: MARKER_SHAPE[m.type],
        text: m.label,
      }));
      createSeriesMarkers(candleSeries, seriesMarkers);
    }

    chart.timeScale().fitContent();

    const forceResize = () => {
      const w = measureWidth();
      if (w > 0) {
        chart.resize(w, 420);
        chart.timeScale().fitContent();
      }
    };
    // A couple of forced re-measures shortly after mount catch layout that
    // settles after this effect runs (fonts loading, flex reflow) without
    // depending on any observer callback.
    const raf = requestAnimationFrame(forceResize);
    const timeout = setTimeout(forceResize, 250);
    window.addEventListener("resize", forceResize);

    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(timeout);
      window.removeEventListener("resize", forceResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [data]);

  if (error) return <div className="text-bear text-sm">{error}</div>;
  if (!data) return <div className="text-gray-500 text-sm">Loading chart…</div>;

  return (
    <div className="rounded-lg border border-border bg-panel p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-400">
          {data.symbol} · {data.interval} — AI-annotated chart
        </h2>
        <Legend />
      </div>

      <div ref={containerRef} />

      <p className="text-xs text-gray-600 mt-2">
        Click any level, structure marker, or order block below to see why the AI
        drew it. Levels come straight from Claude&apos;s reasoning; structure
        markers (BOS/CHoCH/FVG) are computed deterministically from price
        action — nothing here is a live per-click AI call.
      </p>

      <OverlayList
        levels={data.levels}
        markers={data.markers}
        orderBlocks={data.order_blocks}
        onSelect={setSelected}
      />

      {selected && (
        <div className="mt-3 rounded border border-border bg-bg p-3 text-sm">
          <div className="font-semibold text-gray-200 mb-1">{selected.label}</div>
          <p className="text-gray-300">{selected.explain}</p>
        </div>
      )}
    </div>
  );
}

function Legend() {
  return (
    <div className="flex items-center gap-3 text-[10px] text-gray-500">
      <span className="flex items-center gap-1">
        <span className="w-2 h-0.5 bg-[#60a5fa] inline-block" /> EMA20
      </span>
      <span className="flex items-center gap-1">
        <span className="w-2 h-0.5 bg-[#f59e0b] inline-block" /> EMA50
      </span>
      <span className="flex items-center gap-1">
        <span className="w-2 h-0.5 bg-[#a78bfa] inline-block" /> EMA200
      </span>
    </div>
  );
}

function OverlayList({
  levels,
  markers,
  orderBlocks,
  onSelect,
}: {
  levels: ChartLevel[];
  markers: ChartMarker[];
  orderBlocks: OrderBlock[];
  onSelect: (s: { label: string; explain: string }) => void;
}) {
  const recentMarkers = markers.slice(-12).reverse();
  const recentBlocks = orderBlocks.slice(-6).reverse();

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4 text-xs">
      <div>
        <div className="text-gray-500 mb-1 uppercase tracking-wide">Trade Levels</div>
        <div className="flex flex-col gap-1">
          {levels.map((l, i) => (
            <button
              key={i}
              onClick={() => onSelect({ label: l.label, explain: l.explain })}
              className="text-left px-2 py-1 rounded border border-border hover:border-gray-500"
              style={{ color: l.color }}
            >
              {l.label}
              {l.price != null ? ` — ${l.price}` : ""}
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="text-gray-500 mb-1 uppercase tracking-wide">
          Structure ({markers.length})
        </div>
        <div className="flex flex-col gap-1 max-h-40 overflow-y-auto">
          {recentMarkers.map((m, i) => (
            <button
              key={i}
              onClick={() => onSelect({ label: m.label, explain: m.explain })}
              className="text-left px-2 py-1 rounded border border-border hover:border-gray-500 text-gray-300"
            >
              {m.label} @ {m.price.toLocaleString()}
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="text-gray-500 mb-1 uppercase tracking-wide">
          Order Blocks ({orderBlocks.length})
        </div>
        <div className="flex flex-col gap-1 max-h-40 overflow-y-auto">
          {recentBlocks.map((b, i) => (
            <button
              key={i}
              onClick={() =>
                onSelect({
                  label: `${b.direction} order block`,
                  explain: `${b.explain} Zone: ${b.bottom.toLocaleString()} – ${b.top.toLocaleString()}.`,
                })
              }
              className={`text-left px-2 py-1 rounded border border-border hover:border-gray-500 ${
                b.direction === "bullish" ? "text-bull" : "text-bear"
              }`}
            >
              {b.direction} block {b.bottom.toLocaleString()}–{b.top.toLocaleString()}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
