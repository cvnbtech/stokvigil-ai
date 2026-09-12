"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  createChart,
  IChartApi,
  LineStyle,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  ISeriesApi,
  IPriceLine,
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

interface CrosshairData {
  time: any;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  volume?: number;
}

interface LightweightCandleChartProps {
  symbol: string;
  initialInterval?: string;
  backendUrl?: string;
  onClose?: () => void;
  isMaximized?: boolean;
  onToggleMaximize?: () => void;
}

function createCamarillaPriceLines(
  series: ISeriesApi<"Candlestick">,
  cam: CamarillaLevels
): IPriceLine[] {
  if (!cam || cam.h4 <= 0) return [];
  return [
    series.createPriceLine({
      price: cam.h4,
      color: "#ec4899",
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: `H4 Breakout (₹${cam.h4})`,
    }),
    series.createPriceLine({
      price: cam.h3,
      color: "#10b981",
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      axisLabelVisible: true,
      title: `H3 Target 1 (₹${cam.h3})`,
    }),
    series.createPriceLine({
      price: cam.l3,
      color: "#06b6d4",
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      axisLabelVisible: true,
      title: `L3 Liquidity (₹${cam.l3})`,
    }),
    series.createPriceLine({
      price: cam.l4,
      color: "#f43f5e",
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: `L4 Hard SL (₹${cam.l4})`,
    }),
  ];
}

export default function LightweightCandleChart({
  symbol,
  initialInterval = "5m",
  backendUrl = "",
  onClose,
  isMaximized = false,
  onToggleMaximize,
}: LightweightCandleChartProps) {
  const chartContainerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);

  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const vwapSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const slSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const camarillaLinesRef = useRef<IPriceLine[]>([]);

  const [interval, setInterval] = useState(initialInterval);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [camarilla, setCamarilla] = useState<CamarillaLevels | null>(null);
  const [lastPrice, setLastPrice] = useState<number | null>(null);
  const [priceChange, setPriceChange] = useState<number>(0);
  const [crosshair, setCrosshair] = useState<CrosshairData | null>(null);

  // Indicator Toggles
  const [showCamarilla, setShowCamarilla] = useState(true);
  const [showVwap, setShowVwap] = useState(true);
  const [showChandelier, setShowChandelier] = useState(true);
  const [showVolume, setShowVolume] = useState(true);

  // Re-apply visibility when toggles change
  useEffect(() => {
    if (volumeSeriesRef.current) {
      volumeSeriesRef.current.applyOptions({ visible: showVolume });
    }
    if (vwapSeriesRef.current) {
      vwapSeriesRef.current.applyOptions({ visible: showVwap });
    }
    if (slSeriesRef.current) {
      slSeriesRef.current.applyOptions({ visible: showChandelier });
    }
    if (candleSeriesRef.current) {
      if (!showCamarilla) {
        camarillaLinesRef.current.forEach((line) => {
          try {
            candleSeriesRef.current?.removePriceLine(line);
          } catch (_) {}
        });
        camarillaLinesRef.current = [];
      } else if (camarilla && camarillaLinesRef.current.length === 0 && camarilla.h4 > 0) {
        camarillaLinesRef.current = createCamarillaPriceLines(candleSeriesRef.current, camarilla);
      }
    }
  }, [showCamarilla, showVwap, showChandelier, showVolume, camarilla]);

  // Handle Resize & Fullscreen Dimension Adjustment
  useEffect(() => {
    if (chartContainerRef.current && chartRef.current) {
      const targetHeight = isMaximized ? Math.max(520, window.innerHeight - 240) : 380;
      chartRef.current.applyOptions({
        width: chartContainerRef.current.clientWidth,
        height: targetHeight,
      });
      chartRef.current.timeScale().fitContent();
    }
  }, [isMaximized]);

  // Fetch Chart Data & Initialize TradingView
  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);
    setCrosshair(null);

    const fetchChartData = async () => {
      try {
        const cleanSym = symbol.trim().toUpperCase();
        const period = interval === "1d" ? "1y" : "5d";
        const res = await fetch(
          `${backendUrl}/api/stocks/candles?symbol=${encodeURIComponent(cleanSym)}&interval=${interval}&period=${period}`
        );
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

          const targetHeight = isMaximized ? Math.max(520, window.innerHeight - 240) : 380;
          const chart = createChart(chartContainerRef.current, {
            layout: {
              background: { color: "#080B16" },
              textColor: "#94a3b8",
              fontSize: 11,
            },
            grid: {
              vertLines: { color: "rgba(255, 255, 255, 0.04)" },
              horzLines: { color: "rgba(255, 255, 255, 0.04)" },
            },
            timeScale: {
              borderColor: "rgba(255, 255, 255, 0.1)",
              timeVisible: true,
              secondsVisible: false,
              fixLeftEdge: true,
              fixRightEdge: true,
            },
            crosshair: {
              vertLine: { color: "#06b6d4", width: 1, style: LineStyle.Dashed },
              horzLine: { color: "#06b6d4", width: 1, style: LineStyle.Dashed },
            },
            rightPriceScale: {
              borderColor: "rgba(255, 255, 255, 0.1)",
              scaleMargins: { top: 0.1, bottom: 0.15 },
              alignLabels: true,
            },
            width: chartContainerRef.current.clientWidth,
            height: targetHeight,
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
          candleSeriesRef.current = candleSeries;

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
          volumeSeriesRef.current = volumeSeries;
          volumeSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.82, bottom: 0 },
          });
          volumeSeries.setData(
            candles.map((c) => ({
              time: c.time as any,
              value: c.volume || 0,
              color: c.close >= c.open ? "rgba(16, 185, 129, 0.3)" : "rgba(244, 63, 94, 0.3)",
            }))
          );
          volumeSeries.applyOptions({ visible: showVolume });

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
            vwapSeriesRef.current = vwapSeries;
            vwapSeries.setData(vwapData);
            vwapSeries.applyOptions({ visible: showVwap });
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
            slSeriesRef.current = slSeries;
            slSeries.setData(slData);
            slSeries.applyOptions({ visible: showChandelier });
          }

          // 5. Overlaid Camarilla Equation Price Lines
          const cam = data.camarilla;
          camarillaLinesRef.current = [];
          if (cam && showCamarilla) {
            camarillaLinesRef.current = createCamarillaPriceLines(candleSeries, cam);
          }

          // 6. Crosshair Movement Subscriber for Live OHLC HUD
          chart.subscribeCrosshairMove((param) => {
            if (!param || !param.time || !param.seriesData) {
              setCrosshair(null);
              return;
            }
            const cData: any = param.seriesData.get(candleSeries);
            if (cData) {
              const vData: any = volumeSeries ? param.seriesData.get(volumeSeries) : null;
              setCrosshair({
                time: param.time,
                open: cData.open,
                high: cData.high,
                low: cData.low,
                close: cData.close,
                volume: vData?.value,
              });
            }
          });

          chart.timeScale().fitContent();

          // Dynamic ResizeObserver for exact window and container resolution
          if (resizeObserverRef.current) {
            resizeObserverRef.current.disconnect();
          }
          const ro = new ResizeObserver((entries) => {
            for (const entry of entries) {
              const cr = entry.contentRect;
              if (cr.width > 20 && cr.height > 20 && chartRef.current) {
                chartRef.current.applyOptions({
                  width: Math.floor(cr.width),
                  height: Math.floor(cr.height),
                });
              }
            }
          });
          ro.observe(chartContainerRef.current);
          resizeObserverRef.current = ro;

          setLoading(false);
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
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
        resizeObserverRef.current = null;
      }
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [symbol, interval, backendUrl]);

  const targetCanvasHeight = isMaximized ? Math.max(520, (typeof window !== "undefined" ? window.innerHeight : 800) - 240) : 380;

  return (
    <div
      style={{
        background: "#080B16",
        border: "1.5px solid rgba(6, 182, 212, 0.3)",
        borderRadius: 20,
        padding: 18,
        boxShadow: "0 16px 48px rgba(0, 0, 0, 0.6)",
        display: "flex",
        flexDirection: "column",
        gap: 10,
        width: "100%",
        transition: "all 0.2s ease",
      }}
    >
      {/* Top Header: Symbol, Price, Controls, Maximize, Close */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          {/* SV StokVigil Logo Badge */}
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
              background: "linear-gradient(135deg, rgba(6, 182, 212, 0.2) 0%, rgba(99, 102, 241, 0.2) 100%)",
              border: "1px solid rgba(6, 182, 212, 0.4)",
              borderRadius: 8,
              padding: "2px 7px",
              boxShadow: "0 0 12px rgba(6, 182, 212, 0.15)",
            }}
          >
            <span style={{ fontSize: 11, fontWeight: 900, color: "#06b6d4", letterSpacing: 0.5 }}>SV</span>
            <span style={{ fontSize: 9, fontWeight: 700, color: "#94a3b8", letterSpacing: 0.8 }}>STOKVIGIL</span>
          </div>
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

        {/* Timeframe Selectors, Maximize & Close */}
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

          {onToggleMaximize && (
            <button
              onClick={onToggleMaximize}
              title={isMaximized ? "Restore Window" : "Maximize Full Screen"}
              style={{
                background: isMaximized ? "rgba(6, 182, 212, 0.25)" : "rgba(255, 255, 255, 0.05)",
                border: `1px solid ${isMaximized ? "#06b6d4" : "rgba(255, 255, 255, 0.1)"}`,
                borderRadius: 8,
                width: 28,
                height: 28,
                color: isMaximized ? "#06b6d4" : "#94a3b8",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 14,
                marginLeft: 4,
              }}
            >
              {isMaximized ? "🗗" : "⛶"}
            </button>
          )}

          {onClose && (
            <button
              onClick={onClose}
              title="Close Chart"
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
                marginLeft: 4,
              }}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Live Crosshair OHLC HUD */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          fontSize: 11,
          color: "#94a3b8",
          background: "rgba(13, 20, 36, 0.7)",
          padding: "5px 10px",
          borderRadius: 8,
          border: "1px solid rgba(255, 255, 255, 0.05)",
          flexWrap: "wrap",
        }}
      >
        <span style={{ color: "#64748b", fontWeight: 700 }}>
          {crosshair ? "CROSSHAIR:" : "LATEST:"}
        </span>
        <span>
          O: <strong style={{ color: "#f8fafc" }}>₹{crosshair?.open?.toFixed(2) ?? "--"}</strong>
        </span>
        <span>
          H: <strong style={{ color: "#10b981" }}>₹{crosshair?.high?.toFixed(2) ?? "--"}</strong>
        </span>
        <span>
          L: <strong style={{ color: "#f43f5e" }}>₹{crosshair?.low?.toFixed(2) ?? "--"}</strong>
        </span>
        <span>
          C: <strong style={{ color: "#38bdf8" }}>₹{crosshair?.close?.toFixed(2) ?? lastPrice?.toFixed(2) ?? "--"}</strong>
        </span>
        {crosshair?.volume !== undefined && (
          <span>
            Vol:{" "}
            <strong style={{ color: "#06b6d4" }}>
              {crosshair.volume >= 1000000
                ? `${(crosshair.volume / 1000000).toFixed(2)}M`
                : crosshair.volume >= 1000
                ? `${(crosshair.volume / 1000).toFixed(1)}K`
                : crosshair.volume}
            </strong>
          </span>
        )}
      </div>

      {/* Indicator Toggles Bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 10,
          color: "#94a3b8",
          flexWrap: "wrap",
        }}
      >
        {[
          { label: "Camarilla Pivots", active: showCamarilla, toggle: () => setShowCamarilla(!showCamarilla), color: "#ec4899" },
          { label: "VWAP", active: showVwap, toggle: () => setShowVwap(!showVwap), color: "#06b6d4" },
          { label: "Chandelier SL", active: showChandelier, toggle: () => setShowChandelier(!showChandelier), color: "#f59e0b" },
          { label: "Volume", active: showVolume, toggle: () => setShowVolume(!showVolume), color: "#10b981" },
        ].map((ind) => (
          <button
            key={ind.label}
            onClick={ind.toggle}
            style={{
              background: ind.active ? `${ind.color}15` : "rgba(255, 255, 255, 0.03)",
              border: `1px solid ${ind.active ? ind.color : "rgba(255, 255, 255, 0.08)"}`,
              color: ind.active ? "#ffffff" : "#64748b",
              borderRadius: 6,
              padding: "3px 8px",
              fontSize: 10,
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 5,
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: ind.active ? ind.color : "#64748b",
              }}
            />
            {ind.label}
          </button>
        ))}

        {camarilla && camarilla.h4 > 0 && showCamarilla && (
          <span style={{ fontSize: 9.5, color: "#64748b", marginLeft: "auto" }}>
            H4: ₹{camarilla.h4} | H3: ₹{camarilla.h3} | L3: ₹{camarilla.l3} | L4: ₹{camarilla.l4}
          </span>
        )}
      </div>

      {/* Chart Canvas Area */}
      <div style={{ position: "relative", width: "100%", height: targetCanvasHeight, minHeight: 360, overflow: "hidden", borderRadius: 12 }}>
        {/* StokVigil SV Background Watermark */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            pointerEvents: "none",
            zIndex: 1,
            userSelect: "none",
            opacity: 0.05,
          }}
        >
          <div style={{ fontSize: 80, fontWeight: 900, letterSpacing: 6, color: "#38bdf8", lineHeight: 1 }}>SV</div>
          <div style={{ fontSize: 13, fontWeight: 800, letterSpacing: 8, color: "#ffffff", marginTop: 4 }}>STOKVIGIL AI</div>
        </div>

        {/* Top-Left Floating Brand Overlay Pill */}
        <div
          style={{
            position: "absolute",
            top: 12,
            left: 12,
            display: "flex",
            flexDirection: "column",
            gap: 2,
            background: "rgba(8, 11, 22, 0.88)",
            backdropFilter: "blur(10px)",
            border: "1px solid rgba(6, 182, 212, 0.4)",
            borderRadius: 8,
            padding: "4px 10px",
            zIndex: 2,
            pointerEvents: "none",
            boxShadow: "0 4px 16px rgba(0, 0, 0, 0.6), 0 0 10px rgba(6, 182, 212, 0.18)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 2,
                borderRadius: 4,
                padding: "1px 5px",
                background: "linear-gradient(135deg, #06b6d4 0%, #10b981 100%)",
                fontSize: 9,
                fontWeight: 900,
                color: "#ffffff",
                letterSpacing: 0.5,
              }}
            >
              <span style={{ fontSize: 8 }}>⚡</span>SV
            </div>
            <span style={{ fontSize: 10.5, fontWeight: 900, color: "#ffffff", letterSpacing: 0.6 }}>STOKVIGIL AI</span>
            <span style={{ fontSize: 9, color: "#06b6d4", fontWeight: 700 }}>•</span>
            <span style={{ fontSize: 9.5, color: "#94a3b8", fontWeight: 700, letterSpacing: 0.5 }}>
              {interval.toUpperCase()} {interval.includes("d") || interval.includes("w") ? "SWING" : "INTRADAY"}
            </span>
          </div>
          <span style={{ fontSize: 8, color: "#64748b", fontWeight: 600, letterSpacing: 0.4 }}>
            Candlesticks &amp; Camarilla Watchtower
          </span>
        </div>

        {loading && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 10,
              background: "rgba(8, 11, 22, 0.8)",
              zIndex: 10,
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                border: "2px solid #06b6d4",
                borderTopColor: "transparent",
                animation: "spin 1s linear infinite",
              }}
            />
            <div style={{ fontSize: 11, color: "#94a3b8" }}>Loading Institutional Candles & Pivots...</div>
          </div>
        )}

        {error ? (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#f43f5e",
              fontSize: 12,
              padding: 20,
              textAlign: "center",
            }}
          >
            {error}
          </div>
        ) : (
          <div ref={chartContainerRef} style={{ width: "100%", height: targetCanvasHeight }} />
        )}
      </div>
    </div>
  );
}
