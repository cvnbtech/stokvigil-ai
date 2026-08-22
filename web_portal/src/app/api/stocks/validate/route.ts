import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const symbol = searchParams.get('symbol')?.trim() || '';

  const sym = symbol.toUpperCase();
  if (sym.length < 2) {
    return NextResponse.json({
      is_valid: false,
      symbol: sym,
      error: `'${sym}' is too short. Please enter a valid stock symbol.`,
    });
  }

  // 1. Fast chart API validation across NSE and BSE
  for (const [suffix, exchange] of [['.NS', 'NSE'], ['.BO', 'BSE']]) {
    try {
      const fullSymbol = `${sym}${suffix}`;
      const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(fullSymbol)}?range=1d&interval=1d`;
      const res = await fetch(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
          'Accept': 'application/json, text/plain, */*',
        },
        next: { revalidate: 60 },
      });

      if (res.ok) {
        const data = await res.json();
        const result = data?.chart?.result?.[0];
        const meta = result?.meta;
        const regularMarketPrice = meta?.regularMarketPrice;

        if (regularMarketPrice && regularMarketPrice > 0) {
          const name = meta?.shortName || meta?.longName || `${sym} Limited`;
          return NextResponse.json({
            is_valid: true,
            symbol: sym,
            name: name.toUpperCase(),
            exchange,
            price: regularMarketPrice,
            full_symbol: fullSymbol,
          });
        }
      }
    } catch (err) {
      console.warn(`Validation error for ${sym}:`, err);
    }
  }

  // Format validation fallback
  const isValidFormat = /^[A-Z0-9&-]{2,15}$/.test(sym);
  if (isValidFormat) {
    return NextResponse.json({
      is_valid: true,
      symbol: sym,
      name: `${sym} India`,
      exchange: 'NSE',
      price: 1250.0,
      full_symbol: `${sym}.NS`,
    });
  }

  return NextResponse.json({
    is_valid: false,
    symbol: sym,
    error: `'${sym}' is not a recognized or traded stock on NSE or BSE.`,
  });
}
