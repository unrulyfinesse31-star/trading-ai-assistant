import React, { useEffect, useRef } from "react";
import { createChart, ISeriesApi, CandlestickData } from "lightweight-charts";

type Props = {
  symbol: string;
  wsUrl: string;
};

export default function PriceChart({ symbol, wsUrl }: Props) {
  const chartDivRef = useRef<HTMLDivElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const container = chartDivRef.current!;
    const chart = createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: { backgroundColor: "#0b1220", textColor: "#d5dbe4" },
      grid: {
        vertLines: { color: "rgba(120,120,120,0.1)" },
        horzLines: { color: "rgba(120,120,120,0.1)" },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: "rgba(120,120,120,0.4)" },
      timeScale: { borderColor: "rgba(120,120,120,0.4)" },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    const onResize = () => {
      chart.applyOptions({ width: container.clientWidth, height: container.clientHeight });
    };
    window.addEventListener("resize", onResize);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const candle = JSON.parse(event.data);
        if (candle.error) return;
        const data: CandlestickData = {
          time: Math.floor(candle.timestamp / 1000) as any,
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
        };
        candleSeries.update(data);
      } catch (error) {
        console.error("Failed to parse candle", error);
      }
    };

    ws.onerror = (event) => {
      console.error("WebSocket error", event);
    };

    return () => {
      wsRef.current?.close();
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, [symbol, wsUrl]);

  return <div ref={chartDivRef} style={{ width: "100%", height: "440px" }} />;
}
