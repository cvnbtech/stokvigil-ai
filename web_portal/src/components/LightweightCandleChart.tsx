"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  createChart,
  IChartApi,
  LineStyle,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
} from "lightweight-charts";

interface CandleItem {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
  vwap?: number | null;
  chandelier_sl?: number | null;
}

interface CamarillaLevels {
  h4: number;
  h3: number;
  l3: number;
  l4: number;
}

interface LightweightCandleChartProps {
  symbol: string;
  initialInterval?: string;
  backendUrl?: string;
  onClose?: () => void;
}

export default function LightweightCandleChart({
  symbol,
  initialInterval = "5m",
  backendUrl = "",
  onClose,
}: LightweightCandleChartProps) {
  const chartContainerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);

  const [interval, setInterval] = useState(initialInterval);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [camarilla, setCamarilla] = useState<CamarillaLevels | null>(null);
  const [lastPrice, setLastPrice] = useState<number | null>(null);
  const [priceChange, setPriceChange] = useState<number>(0);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    const fetchChartData = async () => {
      try {
        const cleanSym = symbol.trim().toUpperCase();
        const res = await fetch(`${backendUrl}/api/stocks/candles?symbol=${encodeURIComponent(cleanSym)}&interval=${interval}&period=5d`);
        if (!res.ok) {
          throw new Error(`Failed to load candle data (HTTP ${res.status})`);
        }
        const data = await res.json();
        if (!isMounted) return;

        const candles: CandleItem[] = data.candles || [];
        if (candles.length === 0) {
          setError(`No intraday bar data available for ${cleanSym}.`);
          setLoading(false);
          return;
        }

        setCamarilla(data.camarilla || null);
        const lastBar = candles[candles.length - 1];
        const firstBar = candles[0];
        setLastPrice(lastBar.close);
        const diff = lastBar.close - firstBar.open;
        setPriceChange(diff);

        // Initialize Lightweight Charts
        if (chartContainerRef.current) {
          if (chartRef.current) {
            chartRef.current.remove();
            chartRef.current = null;
          }

          const chart = createChart(chartContainerRef.current, {
            layout: {
              background: { color: "#080B16" },
              textColor: "#94a3b8",
            },
            grid: {
              vertLines: { color: "rgba(255, 255, 255, 0.04)" },
              horzLines: { color: "rgba(255, 255, 255, 0.04)" },
            },
            timeScale: {
              borderColor: "rgba(255, 255, 255, 0.1)",
              timeVisible: true,
              secondsVisible: false,
            },
            crosshair: {
              vertLine: { color: "#06b6d4", width: 1, style: LineStyle.Dashed },
              horzLine: { color: "#06b6d4", width: 1, style: LineStyle.Dashed },
            },
            rightPriceScale: {
              borderColor: "rgba(255, 255, 255, 0.1)",
            },
            width: chartContainerRef.current.clientWidth,
            height: 380,
          });

          chartRef.current = chart;

          // 1. Candlestick Series
          const candleSeries = chart.addSeries(CandlestickSeries, {
            upColor: "#10b981",
            downColor: "#f43f5e",
            borderUpColor: "#10b981",
            borderDownColor: "#f43f5e",
            wickUpColor: "#10b981",
            wickDownColor: "#f43f5e",
          });

          candleSeries.setData(
            candles.map((c) => ({
              time: c.time as any,
              open: c.open,
              high: c.high,
              low: c.low,
              close: c.close,
            }))
          );

          // 2. Volume Series
          const volumeSeries = chart.addSeries(HistogramSeries, {
            color: "rgba(6, 182, 212, 0.25)",
            priceFormat: { type: "volume" },
            priceScaleId: "",
          });
          volumeSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.8, bottom: 0 },
          });
          volumeSeries.setData(
            candles.map((c) => ({
              time: c.time as any,
              value: c.volume || 0,
              color: c.close >= c.open ? "rgba(16, 185, 129, 0.3)" : "rgba(244, 63, 94, 0.3)",
            }))
          );

          // 3. VWAP Line Series
          const vwapData = candles
            .filter((c) => c.vwap !== null && c.vwap !== undefined)
            .map((c) => ({ time: c.time as any, value: c.vwap as number }));
          if (vwapData.length > 0) {
            const vwapSeries = chart.addSeries(LineSeries, {
              color: "#06b6d4",
              lineWidth: 2,
              title: "VWAP",
            });
            vwapSeries.setData(vwapData);
          }

          // 4. Chandelier Trailing Stop Line Series
          const slData = candles
            .filter((c) => c.chandelier_sl !== null && c.chandelier_sl !== undefined)
            .map((c) => ({ time: c.time as any, value: c.chandelier_sl as number }));
          if (slData.length > 0) {
            const slSeries = chart.addSeries(LineSeries, {
              color: "#f59e0b",
              lineWidth: 1,
              lineStyle: LineStyle.Dotted,
              title: "Chandelier SL",
            });
            slSeries.setData(slData);
          }

          // 5. Overlaid Camarilla Equation Price Lines
          const cam = data.camarilla;
          if (cam && cam.h4 > 0) {
            candleSeries.createPriceLine({
              price: cam.h4,
              color: "#ec4899",
              lineWidth: 1,
              lineStyle: LineStyle.Dashed,
              axisLabelVisible: true,
              title: `H4 Breakout (₹${cam.h4})`,
            });
            candleSeries.createPriceLine({
              price: cam.h3,
              color: "#10b981",
              lineWidth: 1,
              lineStyle: LineStyle.Dotted,
              axisLabelVisible: true,
              title: `H3 Target 1 (₹${cam.h3})`,
            });
            candleSeries.createPriceLine({
              price: cam.l3,
              color: "#06b6d4",
              lineWidth: 1,
              lineStyle: LineStyle.Dotted,
              axisLabelVisible: true,
              title: `L3 Liquidity Floor (₹${cam.l3})`,
            });
            candleSeries.createPriceLine({
              price: cam.l4,
              color: "#f43f5e",
              lineWidth: 1,
              lineStyle: LineStyle.Dashed,
              axisLabelVisible: true,
              title: `L4 Hard SL (₹${cam.l4})`,
            });
          }

          chart.timeScale().fitContent();

          // Handle Resize
          const handleResize = () => {
            if (chartContainerRef.current && chartRef.current) {
              chartRef.current.applyOptions({
                width: chartContainerRef.current.clientWidth,
              });
            }
          };
          window.addEventListener("resize", handleResize);

          setLoading(false);
          return () => {
            window.removeEventListener("resize", handleResize);
            if (chartRef.current) {
              chartRef.current.remove();
              chartRef.current = null;
            }
          };
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || "Failed to load chart.");
          setLoading(false);
        }
      }
    };

    fetchChartData();

    return () => {
      isMounted = false;
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [symbol, interval, backendUrl]);

  return (
    <div style={{
      background: "#080B16",
      border: "1.5px solid rgba(6, 182, 212, 0.3)",
      borderRadius: 20,
      padding: 18,
      boxShadow: "0 16px 48px rgba(0, 0, 0, 0.6)",
      display: "flex",
      flexDirection: "column",
      gap: 12,
      width: "100%",
    }}>
      {/* Header Bar */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
          <span style={{ fontSize: 20, fontWeight: 900, color: "#ffffff" }}>{symbol}</span>
          {lastPrice !== null && (
            <span style={{ fontSize: 16, fontWeight: 800, color: priceChange >= 0 ? "#10b981" : "#f43f5e" }}>
              ₹{lastPrice.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              <span style={{ fontSize: 11, marginLeft: 6, fontWeight: 600 }}>
                ({priceChange >= 0 ? "+" : ""}{priceChange.toFixed(2)})
              </span>
            </span>
          )}
        </div>

        {/* Timeframe Selectors & Close */}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {["1m", "5m", "15m", "1h", "1d"].map((tf) => (
            <button
              key={tf}
              onClick={() => setInterval(tf)}
              style={{
                background: interval === tf ? "rgba(6, 182, 212, 0.2)" : "rgba(255, 255, 255, 0.04)",
                color: interval === tf ? "#06b6d4" : "#94a3b8",
                border: `1px solid ${interval === tf ? "rgba(6, 182, 212, 0.4)" : "rgba(255, 255, 255, 0.08)"}`,
                borderRadius: 8,
                padding: "4px 8px",
                fontSize: 10.5,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              {tf.toUpperCase()}
            </button>
          ))}

          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: "rgba(255, 255, 255, 0.05)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                borderRadius: 8,
                width: 28,
                height: 28,
                color: "#94a3b8",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 14,
                marginLeft: 6
              }}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Legend Bar */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        fontSize: 10,
        color: "#94a3b8",
        flexWrap: "wrap",
        background: "rgba(255, 255, 255, 0.02)",
        padding: "6px 10px",
        borderRadius: 8,
        border: "1px solid rgba(255, 255, 255, 0.05)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 10, height: 2, background: "#06b6d4" }}></span>
          <span>VWAP</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 10, height: 2, background: "#f59e0b", borderTop: "1px dashed #f59e0b" }}></span>
          <span>Chandelier Trailing SL</span>
        </div>
        {camarilla && camarilla.h4 > 0 && (
          <>
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 10, height: 2, background: "#ec4899" }}></span>
              <span>H4: ₹{camarilla.h4}</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 10, height: 2, background: "#10b981" }}></span>
              <span>H3: ₹{camarilla.h3}</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 10, height: 2, background: "#06b6d4" }}></span>
              <span>L3: ₹{camarilla.l3}</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 10, height: 2, background: "#f43f5e" }}></span>
              <span>L4: ₹{camarilla.l4}</span>
            </div>
          </>
        )}
      </div>

      {/* Chart Canvas Area */}
      <div style={{ position: "relative", width: "100%", minHeight: 380 }}>
        {loading && (
          <div style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            background: "rgba(8, 11, 22, 0.8)",
            zIndex: 10,
          }}>
            <div style={{ width: 28, height: 28, borderRadius: "50%", border: "2px solid #06b6d4", borderTopColor: "transparent", animation: "spin 1s linear infinite" }} />
            <div style={{ fontSize: 11, color: "#94a3b8" }}>Loading Institutional Candles & Pivots...</div>
          </div>
        )}

        {error ? (
          <div style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#f43f5e",
            fontSize: 12,
            padding: 20,
            textAlign: "center"
          }}>
            {error}
          </div>
        ) : (
          <div ref={chartContainerRef} style={{ width: "100%", height: 380 }} />
        )}
      </div>
    </div>
  );
}
