import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const q = (searchParams.get("q") || "").trim();

  if (!q) {
    return NextResponse.json({ stocks: [] });
  }

  const searchHeaders = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
  };

  try {
    const url = `https://query1.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(q)}&quotesCount=6&newsCount=0`;
    const res = await fetch(url, { headers: searchHeaders, next: { revalidate: 10 } });
    if (res.ok) {
      const data = await res.json();
      const quotes = data?.quotes || [];
      const results: any[] = [];
      for (const item of quotes) {
        const rawSym = (item.symbol || "").toString();
        if (rawSym.endsWith(".NS") || rawSym.endsWith(".BO")) {
          const cleanSym = rawSym.replace(".NS", "").replace(".BO", "").toUpperCase();
          const name = item.shortname || item.longname || cleanSym;
          const exch = rawSym.endsWith(".NS") ? "NSE" : "BSE";
          const sector = item.sector || item.industry || exch;
          results.push({
            symbol: cleanSym,
            name,
            exchange: exch,
            sector,
            full_symbol: rawSym
          });
        }
      }
      return NextResponse.json({ stocks: results });
    }
  } catch (e) {
    // fallback
  }

  return NextResponse.json({ stocks: [] });
}
