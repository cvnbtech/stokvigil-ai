import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

interface StockQuote {
  symbol: string;
  name: string;
  exchange: string;
  price: number;
  change_pct: number;
  is_positive: boolean;
  day_high: number | null;
  day_low: number | null;
  target: string | null;
  stop_loss: string | null;
  signal: string | null;
  signal_type: string | null;
}

// In-memory cache in Node.js server instance with 15-second TTL
const quoteCache = new Map<string, { data: StockQuote; timestamp: number }>();
const CACHE_TTL_MS = 15000;

async function fetchDirectYahooQuote(sym: string): Promise<StockQuote | null> {
  const headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://finance.yahoo.com/",
    "Accept": "application/json, text/plain, */*"
  };

  const hosts = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"];
  const exchanges = [
    { suffix: ".NS", exch: "NSE" },
    { suffix: ".BO", exch: "BSE" }
  ];

  for (const { suffix, exch } of exchanges) {
    for (const host of hosts) {
      try {
        const url = `https://${host}/v8/finance/chart/${encodeURIComponent(sym)}${suffix}?range=1d&interval=1d`;
        const res = await fetch(url, { headers, cache: "no-store" });
        if (!res.ok) continue;

        const data = await res.json();
        const resList = data?.chart?.result;
        if (!resList || resList.length === 0) continue;

        const meta = resList[0]?.meta;
        const p = meta?.regularMarketPrice;
        if (p === undefined || p === null || Number(p) <= 0) continue;

        const price = Number(Number(p).toFixed(2));
        const prev = meta?.chartPreviousClose || meta?.previousClose || price;
        const chgPct = prev > 0 ? Number((((price - prev) / prev) * 100).toFixed(2)) : 0.0;
        const name = meta?.shortName || meta?.longName || `${sym} (${exch})`;
        const dayHigh = meta?.regularMarketDayHigh ? Number(Number(meta.regularMarketDayHigh).toFixed(2)) : null;
        const dayLow = meta?.regularMarketDayLow ? Number(Number(meta.regularMarketDayLow).toFixed(2)) : null;

        return {
          symbol: sym,
          name,
          exchange: exch,
          price,
          change_pct: chgPct,
          is_positive: chgPct >= 0,
          day_high: dayHigh,
          day_low: dayLow,
          target: null,
          stop_loss: null,
          signal: "MONITORING",
          signal_type: "monitoring"
        };
      } catch {
        // Try next host/suffix
      }
    }
  }

  return null;
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const rawSymbols = searchParams.get("symbols") || "";

  const symbols = rawSymbols
    .split(",")
    .map(s => s.trim().toUpperCase())
    .filter(s => s.length >= 2 && /^[A-Z0-9_\-\.]+$/.test(s));

  if (symbols.length === 0) {
    return NextResponse.json({ quotes: {} });
  }

  const now = Date.now();
  const quotesMap: Record<string, StockQuote> = {};
  const missingSymbols: string[] = [];

  // Check in-memory cache first (<0.1ms)
  for (const sym of symbols) {
    const cached = quoteCache.get(sym);
    if (cached && (now - cached.timestamp < CACHE_TTL_MS)) {
      quotesMap[sym] = cached.data;
    } else {
      missingSymbols.push(sym);
    }
  }

  // If all requested symbols were cached, return immediately
  if (missingSymbols.length === 0) {
    return NextResponse.json({ quotes: quotesMap });
  }

  // Tier 1: Try Python FastAPI Backend (STOKVIGIL_BACKEND_URL or http://localhost:8000)
  const backendUrl = (process.env.STOKVIGIL_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
  try {
    const backendRes = await fetch(
      `${backendUrl}/api/stocks/quotes?symbols=${encodeURIComponent(missingSymbols.join(","))}`,
      { signal: AbortSignal.timeout(3500), cache: "no-store" }
    );
    if (backendRes.ok) {
      const backendData = await backendRes.json();
      const bQuotes = backendData.quotes || {};
      for (const [sym, q] of Object.entries(bQuotes)) {
        if (q && typeof q === "object" && (q as any).price > 0) {
          quotesMap[sym] = q as StockQuote;
          quoteCache.set(sym, { data: q as StockQuote, timestamp: now });
        }
      }
    }
  } catch {
    // Backend offline, unreachable, or timed out; will fall back to Tier 2
  }

  // Tier 2: Resilient direct Yahoo Finance fetch for any missing symbols
  const stillMissing = missingSymbols.filter(s => !quotesMap[s] || quotesMap[s].price <= 0);
  if (stillMissing.length > 0) {
    await Promise.all(
      stillMissing.map(async (sym) => {
        const yfQuote = await fetchDirectYahooQuote(sym);
        if (yfQuote) {
          quotesMap[sym] = yfQuote;
          quoteCache.set(sym, { data: yfQuote, timestamp: now });
        }
      })
    );
  }

  return NextResponse.json(
    { quotes: quotesMap },
    {
      headers: {
        "Cache-Control": "public, s-maxage=10, stale-while-revalidate=30"
      }
    }
  );
}
