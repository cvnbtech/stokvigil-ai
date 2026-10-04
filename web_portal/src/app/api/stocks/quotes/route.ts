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
  const cleanSym = sym.replace(/\.(BO|NS)$/i, "").trim().toUpperCase();
  const isExplicitBse = sym.toUpperCase().endsWith(".BO") || /^\d{6}$/.test(cleanSym);

  const headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://finance.yahoo.com/",
    "Accept": "application/json, text/plain, */*"
  };

  const hosts = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"];
  const exchanges = isExplicitBse
    ? [
        { suffix: ".BO", exch: "BSE" },
        { suffix: ".NS", exch: "NSE" }
      ]
    : [
        { suffix: ".NS", exch: "NSE" },
        { suffix: ".BO", exch: "BSE" }
      ];

  for (const { suffix, exch } of exchanges) {
    for (const host of hosts) {
      try {
        const url = `https://${host}/v8/finance/chart/${encodeURIComponent(cleanSym)}${suffix}?range=5d&interval=1d`;
        const res = await fetch(url, { headers, cache: "no-store", signal: AbortSignal.timeout(2500) });
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
        const name = meta?.shortName || meta?.longName || `${cleanSym} (${exch})`;
        const dayHigh = meta?.regularMarketDayHigh ? Number(Number(meta.regularMarketDayHigh).toFixed(2)) : null;
        const dayLow = meta?.regularMarketDayLow ? Number(Number(meta.regularMarketDayLow).toFixed(2)) : null;

        // Preserve tactical levels from previous cache if available
        const prevCached = quoteCache.get(sym)?.data || quoteCache.get(cleanSym)?.data;

        // Extract completed prior-day (D-1) bar to guarantee static horizontal Camarilla pivots
        const quoteObj = resList[0]?.indicators?.quote?.[0];
        const rawHighs: number[] = (quoteObj?.high || []).filter((v: any) => typeof v === "number" && !isNaN(v));
        const rawLows: number[] = (quoteObj?.low || []).filter((v: any) => typeof v === "number" && !isNaN(v));
        const rawCloses: number[] = (quoteObj?.close || []).filter((v: any) => typeof v === "number" && !isNaN(v));

        let hPrev: number | null = null;
        let lPrev: number | null = null;
        let cPrev: number = Number(prev);

        if (rawHighs.length >= 2 && rawLows.length >= 2) {
          // Completed prior day session is index length - 2
          hPrev = rawHighs[rawHighs.length - 2];
          lPrev = rawLows[rawLows.length - 2];
          if (rawCloses.length >= 2) {
            cPrev = rawCloses[rawCloses.length - 2];
          }
        } else if (rawHighs.length === 1 && rawLows.length === 1) {
          hPrev = rawHighs[0];
          lPrev = rawLows[0];
        }

        // Calculate authentic Camarilla Equation Pivots anchored strictly to D-1 completed session
        const refHigh = hPrev ?? (dayHigh ?? price);
        const refLow = lPrev ?? (dayLow ?? price);
        const trueRange = Math.max(refHigh - refLow, Math.abs(refHigh - cPrev), Math.abs(refLow - cPrev));
        const hasRealVol = trueRange > 0 && cPrev > 0 && price > 0;

        const h3 = cPrev + (trueRange * 1.1 / 4.0);
        const h4 = cPrev + (trueRange * 1.1 / 2.0);
        const l3 = cPrev - (trueRange * 1.1 / 4.0);
        const l4 = cPrev - (trueRange * 1.1 / 2.0);

        let target: string | null = prevCached?.target || null;
        let stop_loss: string | null = prevCached?.stop_loss || null;
        let signal: string = prevCached?.signal || "MONITORING";
        let signal_type: string = prevCached?.signal_type || "monitoring";

        if (hasRealVol) {
          if (price >= h4) {
            signal = "STRONG BUY";
            signal_type = "strong_buy";
            target = `₹${(h4 + (trueRange * 0.5)).toFixed(2)}`;
            stop_loss = `₹${h3.toFixed(2)}`;
          } else if (price >= h3) {
            signal = "BUY";
            signal_type = "buy";
            target = `₹${h4.toFixed(2)}`;
            stop_loss = `₹${l3.toFixed(2)}`;
          } else if (price <= l4) {
            signal = "STOP LOSS EXIT";
            signal_type = "danger";
            target = "CUT RISK";
            stop_loss = `₹${l4.toFixed(2)} BREACHED`;
          } else if (price <= l3) {
            signal = "SELL";
            signal_type = "sell";
            target = `₹${l4.toFixed(2)}`;
            stop_loss = `₹${h3.toFixed(2)}`;
          } else if (price >= cPrev) {
            signal = "ACCUMULATE";
            signal_type = "accumulate";
            target = `₹${h3.toFixed(2)}`;
            stop_loss = `₹${l3.toFixed(2)}`;
          } else {
            signal = "HOLD";
            signal_type = "hold";
            target = `₹${h3.toFixed(2)}`;
            stop_loss = `₹${l3.toFixed(2)}`;
          }
        }

        return {
          symbol: sym,
          name,
          exchange: exch,
          price,
          change_pct: chgPct,
          is_positive: chgPct >= 0,
          day_high: dayHigh,
          day_low: dayLow,
          target,
          stop_loss,
          signal,
          signal_type
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

  // Check in-memory cache first with dual-key clean matching (<0.1ms)
  for (const sym of symbols) {
    const cleanSym = sym.replace(/\.(BO|NS)$/i, "").trim().toUpperCase();
    const cached = quoteCache.get(sym) || quoteCache.get(cleanSym);
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

  // Tier 1: Try Python FastAPI Backend strictly if configured in environment
  const backendUrl = (process.env.STOKVIGIL_BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "").replace(/\/+$/, "");
  if (backendUrl) {
    try {
      const backendRes = await fetch(
        `${backendUrl}/api/stocks/quotes?symbols=${encodeURIComponent(missingSymbols.join(","))}`,
        { signal: AbortSignal.timeout(2500), cache: "no-store" }
      );
      if (backendRes.ok) {
        const backendData = await backendRes.json();
        const bQuotes = backendData.quotes || {};
        for (const [sym, q] of Object.entries(bQuotes)) {
          if (q && typeof q === "object" && (q as any).price > 0) {
            const typedQ = q as StockQuote;
            quotesMap[sym] = typedQ;
            quoteCache.set(sym, { data: typedQ, timestamp: now });
            const cleanK = (typedQ as any).clean_symbol || sym.replace(/\.(BO|NS)$/i, "").trim().toUpperCase();
            if (cleanK) {
              quotesMap[cleanK] = typedQ;
              quoteCache.set(cleanK, { data: typedQ, timestamp: now });
            }
            const fullK = (typedQ as any).full_symbol;
            if (fullK) {
              quotesMap[fullK] = typedQ;
              quoteCache.set(fullK, { data: typedQ, timestamp: now });
            }
          }
        }
      }
    } catch {
      // Backend offline, unreachable, or timed out; will fall back to Tier 2
    }
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
          const cleanK = sym.replace(/\.(BO|NS)$/i, "").trim().toUpperCase();
          if (cleanK) {
            quotesMap[cleanK] = yfQuote;
            quoteCache.set(cleanK, { data: yfQuote, timestamp: now });
          }
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
