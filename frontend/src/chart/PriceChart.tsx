import React, { useEffect, useRef } from "react";
import { createChart, ISeriesApi, CandlestickData } from "lightweight-charts";

type Props = {
  symbol: string;
  wsUrl: string;
};

export default function PriceChart({ symbol, wsUrl }: Props) {
  const chartDivRef = useRef<HTMLDivElement | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const container = chartDivRef.current!;
    const chart = createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: { backgroundColor: "#ffffff", textColor: "#333" },
      timeScale: { timeVisible: true, secondsVisible: true },
    });
    const candleSeries = chart.addCandlestickSeries();
    seriesRef.current = candleSeries;

    // handle resize
    const onResize = () => {
      chart.applyOptions({ width: container.clientWidth, height: container.clientHeight });
    };
    window.addEventListener("resize", onResize);

    // connect websocket
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      console.log("WS open for", symbol);
    };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.error) {
          console.error("WS error:", msg.error);
          return;
        }
        // convert ms timestamp -> seconds unix for lightweight-charts
        const t = Math.floor(msg.timestamp / 1000);
        const candle: CandlestickData = {
          time: t,
          open: msg.open,
          high: msg.high,
          low: msg.low,
          close: msg.close,
        };
        // update chart
        candleSeries.update(candle);
      } catch (e) {
        console.error("WS parse error", e);
      }
    };
    ws.onclose = () => console.log("WS closed for", symbol);
    ws.onerror = (e) => console.error("WS error", e);
    wsRef.current = ws;

    return () => {
      wsRef.current?.close();
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, [symbol, wsUrl]);

  return <div ref={chartDivRef} style={{ width: "100%", height: "100%" }} />;
}
