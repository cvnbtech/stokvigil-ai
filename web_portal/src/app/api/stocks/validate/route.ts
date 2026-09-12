import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const raw = (searchParams.get("symbol") || "").trim().toUpperCase();

  if (raw.length < 2) {
    return NextResponse.json({
      is_valid: false,
      symbol: raw,
      error: `'${raw}' is too short. Please enter a valid stock symbol.`
    });
  }

  if (!/^[A-Z0-9_\-\.]+$/.test(raw)) {
    return NextResponse.json({
      is_valid: false,
      symbol: raw,
      error: `'${raw}' contains invalid characters. Use valid alphanumeric stock symbols.`
    });
  }

  // Tier 1: Try Python FastAPI Backend
  const backendUrl = (process.env.STOKVIGIL_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
  try {
    const backendRes = await fetch(
      `${backendUrl}/api/stocks/validate?symbol=${encodeURIComponent(raw)}`,
      { signal: AbortSignal.timeout(3500), cache: "no-store" }
    );
    if (backendRes.ok) {
      const data = await backendRes.json();
      return NextResponse.json(data);
    }
  } catch {
    // Backend offline; fallback to direct Yahoo Finance validation
  }

  // Tier 2: Yahoo Finance Chart API validation
  const headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://finance.yahoo.com/",
    "Accept": "application/json, text/plain, */*"
  };

  for (const { suffix, exch } of [{ suffix: ".NS", exch: "NSE" }, { suffix: ".BO", exch: "BSE" }]) {
    for (const host of ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]) {
      try {
        const url = `https://${host}/v8/finance/chart/${encodeURIComponent(raw)}${suffix}?range=1d&interval=1d`;
        const res = await fetch(url, { headers, cache: "no-store" });
        if (!res.ok) continue;

        const data = await res.json();
        const resList = data?.chart?.result;
        if (!resList || resList.length === 0) continue;

        const meta = resList[0]?.meta;
        const p = meta?.regularMarketPrice;
        if (p !== undefined && p !== null && Number(p) > 0) {
          const name = meta?.shortName || meta?.longName || `${raw} (${exch})`;
          return NextResponse.json({
            is_valid: true,
            symbol: raw,
            name,
            exchange: exch,
            price: Number(Number(p).toFixed(2)),
            full_symbol: `${raw}${suffix}`
          });
        }
      } catch {
        // Try next
      }
    }
  }

  return NextResponse.json({
    is_valid: false,
    symbol: raw,
    error: `Could not verify '${raw}' on NSE/BSE. Please select from search suggestions.`
  });
}
