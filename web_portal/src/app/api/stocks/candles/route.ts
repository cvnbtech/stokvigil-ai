import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const candleCache = new Map<string, { data: any; timestamp: number }>();
const CACHE_TTL_MS = 15000; // 15 seconds

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const symbol = (searchParams.get("symbol") || "").trim().toUpperCase();
  const interval = searchParams.get("interval") || "5m";
  const period = searchParams.get("period") || "5d";

  if (!symbol) {
    return NextResponse.json({ error: "Symbol parameter is required." }, { status: 400 });
  }

  const cacheKey = `${symbol}:${interval}:${period}`;
  const now = Date.now();
  const cached = candleCache.get(cacheKey);
  if (cached && (now - cached.timestamp) < CACHE_TTL_MS) {
    return NextResponse.json(cached.data, {
      headers: { "X-Cache": "HIT", "Cache-Control": "public, max-age=15, stale-while-revalidate=30" }
    });
  }

  // Pure Backend Proxy: Routes strictly and solely to the Python FastAPI backend engine.
  // Zero secondary calculation engines or synthetic client-side fallbacks.
  const backendBase = (
    process.env.STOKVIGIL_BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    "http://localhost:8000"
  ).replace(/\/+$/, "");

  try {
    const backendUrl = `${backendBase}/api/stocks/candles?symbol=${encodeURIComponent(symbol)}&interval=${interval}&period=${period}`;
    const backendRes = await fetch(backendUrl, {
      headers: { "Accept": "application/json" },
      cache: "no-store",
      signal: AbortSignal.timeout(6000)
    });

    if (backendRes.ok) {
      const data = await backendRes.json();
      if (data && data.candles && data.candles.length > 0) {
        candleCache.set(cacheKey, { data, timestamp: now });
        return NextResponse.json(data, {
          headers: { "X-Cache": "MISS-BACKEND", "Cache-Control": "public, max-age=15, stale-while-revalidate=30" }
        });
      }
      return NextResponse.json(data, { status: backendRes.status });
    }

    const errText = await backendRes.text().catch(() => "");
    return NextResponse.json({
      error: `Python backend returned HTTP ${backendRes.status}: ${errText || "No candle data found."}`,
      symbol,
      interval,
      period,
      candles: [],
      camarilla: null
    }, { status: backendRes.status });

  } catch (backendErr: any) {
    return NextResponse.json({
      error: `Python backend unreachable (${backendErr?.message || "Connection refused"}). Please verify backend is running on ${backendBase}.`,
      symbol,
      interval,
      period,
      candles: [],
      camarilla: null
    }, { status: 502 });
  }
}
