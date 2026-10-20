"use client";
import { useState, useCallback, useRef, useEffect } from "react";
import { BACKEND_URL, supabase } from "../components/ui/DesignTokens";

export const clientQuoteCache: Record<string, any> = {};

export function getCachedClientQuote(symbol: string): any {
  const clean = symbol.replace(/\.(BO|NS)$/i, "").trim().toUpperCase();
  return clientQuoteCache[clean] || clientQuoteCache[symbol.trim().toUpperCase()];
}

interface UseWatchlistManagerProps {
  userId?: string;
}

export function useWatchlistManager({ userId }: UseWatchlistManagerProps) {
  const [watchlist, setWatchlist] = useState<any[]>([]);
  const [ticker, setTicker] = useState("");
  const [tickerSuggestions, setTickerSuggestions] = useState<any[]>([]);
  const [flashMap, setFlashMap] = useState<Record<string, "up" | "down">>({});
  const searchTimerRef = useRef<NodeJS.Timeout | null>(null);
  const flashTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const watchlistRef = useRef<any[]>([]);
  watchlistRef.current = watchlist;

  const loadWatchlistData = useCallback(async (uid: string) => {
    if (supabase) {
      try {
        const { data } = await supabase.from('user_watchlists').select('*').eq('user_id', uid).order('created_at', { ascending: false });
        if (data && data.length > 0) {
          const mapWatchlistItems = (rawItems: any[], quotesMap: Record<string, any>) => {
            return rawItems.map((w: any) => {
              const rawSym = (w.symbol || "").toUpperCase();
              const cleanSym = rawSym.replace(/\.(BO|NS)$/i, "").trim();
              const q = quotesMap[cleanSym] || quotesMap[rawSym] || getCachedClientQuote(cleanSym) || {};
              const price = q.price !== undefined ? q.price : 0;
              const rawChg = q.change_pct;
              const chgPct = typeof rawChg === "number" ? rawChg : (rawChg != null ? parseFloat(rawChg) : 0.0);
              const isPos = chgPct >= 0;
              const exch = q.exchange || (rawSym.endsWith(".BO") ? "BSE" : "NSE");
              const hasRealPrice = price > 0;
              const hasActiveSignal = hasRealPrice && q.signal && q.signal !== "--" && q.signal !== "MONITORING" && q.signal !== "HOLD";
              const signal = hasActiveSignal ? q.signal : "--";
              const signalType = (hasActiveSignal && q.signal_type) ? q.signal_type : "none";
              const target = (hasActiveSignal && q.target && q.target !== "--" && q.target !== "₹0") ? (String(q.target).startsWith("₹") ? q.target : `₹${q.target}`) : "--";
              const sl = (hasActiveSignal && q.stop_loss && q.stop_loss !== "--" && q.stop_loss !== "₹0") ? (String(q.stop_loss).startsWith("₹") ? q.stop_loss : `₹${q.stop_loss}`) : "--";

              return {
                id: w.id,
                symbol: cleanSym,
                fullSymbol: rawSym,
                exchange: exch,
                name: q.name || cleanSym,
                auto: w.is_auto_synced || false,
                price,
                chg: hasRealPrice ? `${isPos ? "+" : ""}${chgPct.toFixed(2)}%` : "--",
                isPositive: isPos,
                signal,
                signalType,
                target,
                sl
              };
            });
          };

          // Step 1: Render immediately from SWR memory cache (< 2ms)
          setWatchlist(mapWatchlistItems(data, clientQuoteCache));

          // Step 2: Fetch fresh quotes from Next.js API route in background
          const symbols = data.map((w: any) => (w.symbol || "").toUpperCase());
          try {
            const res = await fetch(`/api/stocks/quotes?symbols=${encodeURIComponent(symbols.join(','))}`, {
              signal: AbortSignal.timeout(3500)
            });
            if (res.ok) {
              const qData = await res.json();
              const freshQuotes = qData.quotes || {};
              for (const [k, v] of Object.entries(freshQuotes)) {
                if (v && typeof v === "object") {
                  clientQuoteCache[k] = v;
                  const cleanK = k.replace(/\.(BO|NS)$/i, "").trim().toUpperCase();
                  if (cleanK) clientQuoteCache[cleanK] = v;
                }
              }
              // Smooth in-place state update
              setWatchlist(mapWatchlistItems(data, clientQuoteCache));
            }
          } catch (qErr) {
            console.debug("Background quote refresh note:", qErr);
          }
          return;
        }
      } catch (e) {
        console.warn("Watchlist fetch error:", e);
      }
    }
    setWatchlist([]);
  }, []);

  const handleStockChange = (val: string) => {
    setTicker(val);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    const q = val.trim();
    if (q.length < 2) {
      setTickerSuggestions([]);
      return;
    }
    searchTimerRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/stocks/search?q=${encodeURIComponent(q)}`);
        if (res.ok) {
          const data = await res.json();
          setTickerSuggestions(data.stocks || []);
        }
      } catch (e) {
        console.warn("Dynamic stock search error:", e);
      }
    }, 300);
  };

  const addStock = async (explicitSym?: string, explicitName?: string) => {
    const raw = (explicitSym || ticker).trim().toUpperCase();
    if (!raw) return;

    let isValid = false;
    let isTimeout = false;
    let stockName = explicitName || raw;

    if (raw.length < 2) {
      alert(`⚠️ '${raw}' is too short. Please enter a valid NSE or BSE stock symbol.`);
      return;
    }

    let livePrice = 0;

    try {
      const res = await fetch(`${BACKEND_URL}/api/stocks/validate?symbol=${encodeURIComponent(raw)}`, {
        signal: AbortSignal.timeout(30000)
      });
      if (res.ok) {
        const valData = await res.json();
        if (valData.is_valid === true) {
          isValid = true;
          if (valData.name) stockName = valData.name;
          if (valData.price) livePrice = Number(valData.price);
        } else if (valData.is_timeout) {
          isTimeout = true;
        }
      }
    } catch (e: any) {
      if (e?.name === 'TimeoutError' || e?.name === 'AbortError') {
        isTimeout = true;
      }
      console.warn("Stock validation error:", e);
      isValid = false;
    }

    if (isTimeout) {
      alert(`⏳ Connection to exchange timed out for '${raw}'. Please check your connection and try again.`);
      return;
    }

    if (!isValid) {
      alert(`⚠️ '${raw}' is not a recognized or actively traded stock on NSE or BSE.\n\nPlease select from the live search suggestions.`);
      return;
    }

    setTickerSuggestions([]);
    setTicker("");

    const isBse = raw.toUpperCase().endsWith('.BO') || /^\d{6}$/.test(raw.trim());
    let cleanRaw = raw.trim().toUpperCase();
    if (cleanRaw.endsWith('.NS')) {
      cleanRaw = cleanRaw.replace(/\.NS$/i, "").trim();
    }
    // Universal Canonical Suffix Rule: NSE bare, BSE preserves .BO or 6-digit scrip
    const dbSymbol = isBse ? (cleanRaw.endsWith('.BO') || /^\d{6}$/.test(cleanRaw) ? cleanRaw : `${cleanRaw}.BO`) : cleanRaw;
    const displaySymbol = cleanRaw.replace(/\.BO$/i, "").trim();

    if (userId && supabase) {
      setWatchlist(prev => [
        {
          id: Date.now().toString(),
          symbol: displaySymbol,
          fullSymbol: dbSymbol,
          exchange: isBse ? 'BSE' : 'NSE',
          name: stockName && stockName !== raw ? stockName : displaySymbol,
          auto: false,
          price: livePrice,
          chg: livePrice > 0 ? "+0.00%" : "--",
          isPositive: true,
          signal: "--",
          signalType: "none",
          target: "--",
          sl: "--"
        },
        ...prev.filter(p => p.symbol !== displaySymbol && p.fullSymbol !== dbSymbol)
      ]);

      await supabase.from('user_watchlists').upsert({
        user_id: userId,
        symbol: dbSymbol,
        is_auto_synced: false
      }, { onConflict: 'user_id,symbol' });
      loadWatchlistData(userId);
    } else {
      setWatchlist(prev => [
        {
          id: Date.now().toString(),
          symbol: displaySymbol,
          fullSymbol: dbSymbol,
          exchange: isBse ? 'BSE' : 'NSE',
          name: stockName && stockName !== raw ? stockName : displaySymbol,
          auto: false,
          price: livePrice,
          chg: livePrice > 0 ? "+0.00%" : "--",
          isPositive: true,
          signal: "--",
          signalType: "none",
          target: "--",
          sl: "--"
        },
        ...prev.filter(p => p.symbol !== displaySymbol && p.fullSymbol !== dbSymbol)
      ]);
    }
  };

  const removeTicker = async (id: string) => {
    setWatchlist(prev => prev.filter(w => w.id !== id));
    if (userId && supabase) {
      await supabase.from('user_watchlists').delete().eq('id', id);
    }
  };

  const refreshQuotesOnly = useCallback(async () => {
    const currentList = watchlistRef.current;
    if (!currentList || currentList.length === 0) return;

    const symbols = currentList
      .map((w: any) => (w.fullSymbol || w.symbol || "").toUpperCase())
      .filter((s: string) => s.length > 0);
    if (symbols.length === 0) return;

    try {
      const res = await fetch(`/api/stocks/quotes?symbols=${encodeURIComponent(symbols.join(','))}`, {
        signal: AbortSignal.timeout(4000)
      });
      if (res.ok) {
        const qData = await res.json();
        const freshQuotes = qData.quotes || {};
        const newFlashMap: Record<string, "up" | "down"> = {};

        for (const [k, v] of Object.entries(freshQuotes)) {
          if (v && typeof v === "object") {
            const cleanK = k.replace(/\.(BO|NS)$/i, "").trim().toUpperCase();
            const prevQ = clientQuoteCache[cleanK] || clientQuoteCache[k];
            const oldPrice = prevQ?.price ? Number(prevQ.price) : 0;
            const newPrice = (v as any).price ? Number((v as any).price) : 0;

            if (oldPrice > 0 && newPrice > 0 && oldPrice !== newPrice) {
              newFlashMap[cleanK] = newPrice > oldPrice ? "up" : "down";
            }

            clientQuoteCache[k] = v;
            if (cleanK) clientQuoteCache[cleanK] = v;
          }
        }

        setWatchlist(prev => prev.map(item => {
          const cleanSym = (item.symbol || "").toUpperCase();
          const fullSym = (item.fullSymbol || cleanSym).toUpperCase();
          const q = freshQuotes[cleanSym] || freshQuotes[fullSym] || clientQuoteCache[cleanSym] || {};
          const price = q.price !== undefined ? q.price : item.price;
          const rawChg = q.change_pct !== undefined ? q.change_pct : null;
          const chgPct = typeof rawChg === "number" ? rawChg : (rawChg != null ? parseFloat(rawChg) : null);
          const isPos = chgPct != null ? chgPct >= 0 : item.isPositive;
          const hasRealPrice = price > 0;
          const hasActiveSignal = hasRealPrice && q.signal && q.signal !== "--" && q.signal !== "MONITORING" && q.signal !== "HOLD";
          const signal = hasActiveSignal ? q.signal : item.signal;
          const signalType = (hasActiveSignal && q.signal_type) ? q.signal_type : item.signalType;
          const target = (hasActiveSignal && q.target && q.target !== "--" && q.target !== "₹0")
            ? (String(q.target).startsWith("₹") ? q.target : `₹${q.target}`)
            : item.target;
          const sl = (hasActiveSignal && q.stop_loss && q.stop_loss !== "--" && q.stop_loss !== "₹0")
            ? (String(q.stop_loss).startsWith("₹") ? q.stop_loss : `₹${q.stop_loss}`)
            : item.sl;

          return {
            ...item,
            price,
            chg: (hasRealPrice && chgPct != null) ? `${isPos ? "+" : ""}${chgPct.toFixed(2)}%` : item.chg,
            isPositive: isPos,
            signal,
            signalType,
            target,
            sl
          };
        }));

        if (Object.keys(newFlashMap).length > 0) {
          setFlashMap(newFlashMap);
          if (flashTimeoutRef.current) clearTimeout(flashTimeoutRef.current);
          flashTimeoutRef.current = setTimeout(() => {
            setFlashMap({});
          }, 1200);
        }
      }
    } catch (e) {
      console.debug("Background auto-refresh note:", e);
    }
  }, []);

  // 30-Second Background Auto-Refresh (Silent In-Place Sync)
  useEffect(() => {
    if (!userId) return;

    const interval = setInterval(() => {
      if (typeof document !== "undefined" && document.visibilityState === "hidden") {
        return;
      }
      refreshQuotesOnly();
    }, 30000);

    return () => clearInterval(interval);
  }, [userId, refreshQuotesOnly]);

  return {
    watchlist, setWatchlist,
    ticker, setTicker,
    tickerSuggestions, setTickerSuggestions,
    handleStockChange,
    addStock,
    removeTicker,
    loadWatchlistData,
    refreshQuotesOnly,
    flashMap
  };
}
