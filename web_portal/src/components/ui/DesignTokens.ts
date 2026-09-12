import { createClient, SupabaseClient } from "@supabase/supabase-js";

export const SUPABASE_URL = (process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || "").trim();
export const SUPABASE_ANON_KEY = (process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY || "").trim();
export const BACKEND_URL = (process.env.NEXT_PUBLIC_BACKEND_URL || process.env.STOKVIGIL_BACKEND_URL || "").replace(/\/+$/, "");

export const isSupabaseConfigured = Boolean(
  SUPABASE_URL &&
  !SUPABASE_URL.includes("your-supabase-project") &&
  SUPABASE_ANON_KEY &&
  !SUPABASE_ANON_KEY.includes("dummy") &&
  !SUPABASE_ANON_KEY.includes("your-anon-key")
);

export const supabase: SupabaseClient | null = isSupabaseConfigured
  ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
  : null;

// Vibrant Cyan-Violet Theme
export const C = {
  bg:          "#070913",
  bgCard:      "#0D111E",
  bgCard2:     "#12172A",
  border:      "rgba(255,255,255,0.08)",
  borderCyan:  "rgba(6,182,212,0.35)",
  borderViolet:"rgba(139,92,246,0.35)",
  cyan:        "#06B6D4",
  violet:      "#8B5CF6",
  emerald:     "#10B981",
  rose:        "#EF4444",
  amber:       "#F59E0B",
  white:       "#F8FAFC",
  gray1:       "#94A3B8",
  gray2:       "#64748B",
  gray3:       "#1E293B",
};

export interface HoldingItem {
  symbol: string;
  qty: number;
  avg: number;
  price: number;
  pnl: number;
  pnlPct: number;
  dayHigh: number | null;
  dayLow: number | null;
  high52: number | null;
  sector: string;
  signal: string;
  signalType: "strong_buy" | "buy" | "sell" | "hold" | "neutral" | "monitoring" | string;
  target?: string | null;
  sl?: string | null;
}
