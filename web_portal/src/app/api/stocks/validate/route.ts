import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const symbol = (searchParams.get("symbol") || "").trim().toUpperCase();

  if (!symbol || symbol.length < 2) {
    return NextResponse.json({
      is_valid: false,
      symbol,
      error: "Stock symbol is too short."
    }, { status: 400 });
  }

  const searchHeaders = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
  };

  // Fast chart API validation on NSE (.NS) and BSE (.BO)
  for (const suffix of [".NS", ".BO"]) {
    const exch = suffix === ".NS" ? "NSE" : "BSE";
    try {
      const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}${suffix}?range=1d&interval=1d`;
      const res = await fetch(url, { headers: searchHeaders, next: { revalidate: 5 } });
      if (res.ok) {
        const data = await res.json();
        const resList = data?.chart?.result;
        if (resList && resList.length > 0) {
          const meta = resList[0]?.meta || {};
          const price = meta.regularMarketPrice;
          if (price !== undefined && price > 0) {
            const name = meta.shortName || meta.longName || `${symbol} (${exch})`;
            return NextResponse.json({
              is_valid: true,
              symbol,
              name,
              exchange: exch,
              price: Number(price),
              full_symbol: `${symbol}${suffix}`
            });
          }
        }
      }
    } catch (e) {
      // try next exchange
    }
  }

  return NextResponse.json({
    is_valid: false,
    symbol,
    error: `'${symbol}' is not a valid listed stock on NSE or BSE.`
  });
}
