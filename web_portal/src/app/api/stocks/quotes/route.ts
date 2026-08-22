import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const symbolsParam = (searchParams.get("symbols") || "").trim();

  if (!symbolsParam) {
    return NextResponse.json({ quotes: {} });
  }

  const rawSymbols = symbolsParam.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);
  const uniqueSymbols = Array.from(new Set(rawSymbols));

  const searchHeaders = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  };

  const results: Record<string, any> = {};

  await Promise.all(
    uniqueSymbols.map(async (sym) => {
      for (const suffix of [".NS", ".BO"]) {
        const exch = suffix === ".NS" ? "NSE" : "BSE";
        try {
          const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym)}${suffix}?range=1d&interval=1d`;
          const res = await fetch(url, { headers: searchHeaders, next: { revalidate: 5 } });
          if (res.ok) {
            const data = await res.json();
            const resList = data?.chart?.result;
            if (resList && resList.length > 0) {
              const meta = resList[0]?.meta || {};
              const p = meta.regularMarketPrice;
              if (p !== undefined && p > 0) {
                const price = Number(p);
                const prev = Number(meta.chartPreviousClose || meta.previousClose || price);
                const chgPct = prev > 0 ? Number((((price - prev) / prev) * 100).toFixed(2)) : 0.0;
                const name = meta.shortName || meta.longName || `${sym} (${exch})`;
                const dayHigh = Number(meta.regularMarketDayHigh || (price * 1.02));
                const dayLow = Number(meta.regularMarketDayLow || (price * 0.98));

                const signal = chgPct >= 1.5 ? "STRONG BUY" : (chgPct >= 0 ? "BUY" : (chgPct > -1.5 ? "HOLD" : (chgPct > -2.5 ? "TAKE PROFIT" : "SELL")));
                const signalType = chgPct >= 1.5 ? "strong_buy" : (chgPct >= 0 ? "buy" : (chgPct > -1.5 ? "hold" : (chgPct > -2.5 ? "med" : "sell")));

                results[sym] = {
                  symbol: sym,
                  name,
                  exchange: exch,
                  price: Number(price.toFixed(2)),
                  change_pct: chgPct,
                  is_positive: chgPct >= 0,
                  day_high: Number(dayHigh.toFixed(2)),
                  day_low: Number(dayLow.toFixed(2)),
                  target: Number((price * 1.12).toFixed(2)),
                  stop_loss: Number((price * 0.94).toFixed(2)),
                  signal,
                  signal_type: signalType
                };
                break;
              }
            }
          }
        } catch (e) {
          // continue
        }
      }
    })
  );

  return NextResponse.json({ quotes: results });
}
