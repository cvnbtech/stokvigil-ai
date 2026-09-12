import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

interface StockSearchResult {
  symbol: string;
  name: string;
  exchange: string;
  full_symbol: string;
  sector: string;
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const q = (searchParams.get("q") || "").trim();

  if (!q) {
    return NextResponse.json({ stocks: [] });
  }

  // Tier 1: Try Python FastAPI Backend
  const backendUrl = (process.env.STOKVIGIL_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
  try {
    const backendRes = await fetch(
      `${backendUrl}/api/stocks/search?q=${encodeURIComponent(q)}`,
      { signal: AbortSignal.timeout(3500), cache: "no-store" }
    );
    if (backendRes.ok) {
      const data = await backendRes.json();
      if (Array.isArray(data.stocks) && data.stocks.length > 0) {
        return NextResponse.json(data);
      }
    }
  } catch {
    // Backend offline, fall through to Tier 2
  }

  // Tier 2: Direct Yahoo Finance Search
  const searchHeaders = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
  };

  for (const host of ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]) {
    try {
      const url = `https://${host}/v1/finance/search?q=${encodeURIComponent(q)}&quotesCount=10&newsCount=0`;
      const res = await fetch(url, { headers: searchHeaders, cache: "no-store" });
      if (!res.ok) continue;

      const data = await res.json();
      const rawQuotes = data?.quotes || [];
      const results: StockSearchResult[] = [];
      const seenSymbols = new Set<string>();

      for (const item of rawQuotes) {
        const sym = item.symbol || "";
        const quoteType = item.quoteType || "";
        if (quoteType !== "EQUITY") continue;

        let cleanSym = sym;
        let exchange = "NSE";
        if (sym.endsWith(".NS")) {
          cleanSym = sym.slice(0, -3);
          exchange = "NSE";
        } else if (sym.endsWith(".BO")) {
          cleanSym = sym.slice(0, -3);
          exchange = "BSE";
        } else if (["NSI", "NSE"].includes(item.exchange)) {
          exchange = "NSE";
        } else if (["BOM", "BSE"].includes(item.exchange)) {
          exchange = "BSE";
        } else {
          continue;
        }

        if (seenSymbols.has(cleanSym) || cleanSym.startsWith("0P")) continue;
        seenSymbols.add(cleanSym);

        const name = item.longname || item.shortname || cleanSym;
        const sector = item.sector || item.industry || `${exchange} Listed`;

        results.push({
          symbol: cleanSym,
          name,
          exchange,
          full_symbol: sym,
          sector
        });

        if (results.length >= 8) break;
      }

      return NextResponse.json({ stocks: results });
    } catch {
      // Continue to next host
    }
  }

  return NextResponse.json({ stocks: [] });
}
