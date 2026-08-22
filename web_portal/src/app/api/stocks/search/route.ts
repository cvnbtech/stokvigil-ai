import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get('q')?.trim() || '';

  if (!q) {
    return NextResponse.json({ stocks: [] });
  }

  const results: Array<{
    symbol: string;
    name: string;
    exchange: string;
    full_symbol: string;
    sector: string;
  }> = [];

  const seenSymbols = new Set<string>();
  const searchHosts = ['query1.finance.yahoo.com', 'query2.finance.yahoo.com'];

  for (const host of searchHosts) {
    try {
      const url = `https://${host}/v1/finance/search?q=${encodeURIComponent(q)}&quotesCount=10&newsCount=0`;
      const res = await fetch(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
          'Accept': 'application/json, text/plain, */*',
        },
        next: { revalidate: 60 },
      });

      if (res.ok) {
        const data = await res.json();
        for (const item of data.quotes || []) {
          const quoteType = item.quoteType || '';
          if (quoteType !== 'EQUITY') continue;

          const sym = item.symbol || '';
          let cleanSym = sym;
          let exchange = 'NSE';

          if (sym.endsWith('.NS')) {
            cleanSym = sym.replace('.NS', '');
            exchange = 'NSE';
          } else if (sym.endsWith('.BO')) {
            cleanSym = sym.replace('.BO', '');
            exchange = 'BSE';
          } else if (['NSI', 'NSE'].includes(item.exchange)) {
            exchange = 'NSE';
          } else if (['BOM', 'BSE'].includes(item.exchange)) {
            exchange = 'BSE';
          } else {
            continue;
          }

          if (seenSymbols.has(cleanSym) || cleanSym.startsWith('0P')) continue;
          seenSymbols.add(cleanSym);

          const name = item.longname || item.shortname || cleanSym;
          const sector = item.sector || item.industry || `${exchange} Listed`;

          results.push({
            symbol: cleanSym,
            name,
            exchange,
            full_symbol: sym,
            sector,
          });

          if (results.length >= 5) break;
        }
      }
      if (results.length > 0) break;
    } catch (err) {
      console.warn(`Search error on ${host}:`, err);
    }
  }

  // Fallback if query looks like a valid stock ticker
  if (results.length === 0 && q.length >= 2 && /^[A-Za-z0-9&-]{2,15}$/.test(q)) {
    const cleanQ = q.toUpperCase();
    results.push({
      symbol: cleanQ,
      name: `${cleanQ} (NSE)`,
      exchange: 'NSE',
      full_symbol: `${cleanQ}.NS`,
      sector: 'NSE Listed',
    });
  }

  return NextResponse.json({ stocks: results.slice(0, 5) });
}
