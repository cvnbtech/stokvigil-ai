"use client";
import { useState, useCallback, useEffect } from "react";
import { supabase } from "../components/ui/DesignTokens";
import type { AlphaCardData } from "../components/ShareAlphaCardModal";

export function formatAlertRecord(a: any) {
  const rawSnap = a.metrics_snapshot || {};
  const flowData = rawSnap.flow_data || {};
  const technicals = rawSnap.technicals || {};
  const macroData = rawSnap.macro_data || {};
  const dematPos = rawSnap.demat_position || null;

  let livePrice = technicals.current_price || rawSnap.current_price || rawSnap.price || (rawSnap.financials && rawSnap.financials.price) || 0;

  let dematSanitized = null;
  if (dematPos && dematPos.is_in_portfolio) {
    const avgP = dematPos.average_buy_price || 0;
    let pnlPct = dematPos.unrealized_pnl_pct != null ? Number(dematPos.unrealized_pnl_pct) : null;
    if (pnlPct !== null && pnlPct <= -99.0) {
      if (livePrice > 0 && avgP > 0) {
        pnlPct = Number((((livePrice - avgP) / avgP) * 100).toFixed(1));
      } else {
        pnlPct = null;
      }
    }
    dematSanitized = {
      quantity: dematPos.quantity || 0,
      average_buy_price: avgP,
      unrealized_pnl_pct: pnlPct
    };
  }

  const bias = a.action_bias || rawSnap.action_bias || a.alert_type || "HOLD_NEUTRAL";
  let tPrice = rawSnap.tactical_levels?.target_1;
  let sLoss = rawSnap.tactical_levels?.protective_stop_loss;

  const isDummy100 = (tPrice === "₹100.00" || tPrice === "100.0" || tPrice === "100") &&
                     (sLoss === "₹100.00" || sLoss === "100.0" || sLoss === "100");

  if (isDummy100 || !tPrice) {
    tPrice = "-";
  }
  if (isDummy100 || !sLoss) {
    sLoss = "-";
  }

  const deliveryVal = flowData.delivery_pct != null ? `${flowData.delivery_pct}%` : (rawSnap.delivery_pct != null ? `${rawSnap.delivery_pct}%` : "-");
  const rsiVal = technicals.rsi_15m != null ? `${technicals.rsi_15m}` : (rawSnap.rsi_15m != null ? `${rawSnap.rsi_15m}` : "-");
  const vwapVal = technicals.vwap && technicals.vwap > 0 ? `₹${technicals.vwap}` : (rawSnap.vwap && rawSnap.vwap > 0 ? `₹${rawSnap.vwap}` : "-");
  const oiVal = (flowData.fo_oi_status || flowData.flow_bias || rawSnap.fo_oi_status || rawSnap.flow_bias)
    ? String(flowData.fo_oi_status || flowData.flow_bias || rawSnap.fo_oi_status || rawSnap.flow_bias).replace(/_/g, ' ')
    : "-";
  const vsaNote = flowData.vsa_note || flowData.vsa_regime || rawSnap.vsa_regime || "";
  const vixVal = macroData.india_vix || rawSnap.india_vix || null;

  const biasUpper = bias.toUpperCase();
  let sigType = "buy";
  if (biasUpper.includes("CAPITAL_PRESERVATION") || biasUpper.includes("CAPITAL PRESERVATION")) {
    sigType = "capital_preservation_exit";
  } else if (biasUpper.includes("MIS_SHORT") || biasUpper.includes("INTRADAY_MIS")) {
    sigType = "intraday_mis_short";
  } else if (biasUpper.includes("SELL")) {
    sigType = "sell";
  } else if (biasUpper.includes("TRAILING")) {
    sigType = "med";
  } else if ((a.impact_score || 0) >= 80) {
    sigType = "strong_buy";
  }

  const hasRealFactors = rawSnap.factor_breakdown &&
    typeof rawSnap.factor_breakdown === 'object' &&
    rawSnap.factor_breakdown.technicals != null;

  const resolvedFactors = hasRealFactors ? {
    technicals: Number(rawSnap.factor_breakdown.technicals),
    flow: Number(rawSnap.factor_breakdown.flow),
    forensics: Number(rawSnap.factor_breakdown.forensics),
    catalysts: Number(rawSnap.factor_breakdown.catalysts)
  } : null;

  const rawAlertSym = (a.symbol || "").toUpperCase();
  const cleanAlertSym = rawAlertSym.replace(/\.(BO|NS)$/i, "").trim();
  const alertExch = rawSnap.exchange || (rawAlertSym.endsWith(".BO") ? "BSE" : "NSE");
  const compName = rawSnap.company_name || rawSnap.financials?.name || rawSnap.stock_name || cleanAlertSym;

  return {
    id: a.id,
    symbol: cleanAlertSym,
    fullSymbol: rawAlertSym,
    exchange: alertExch,
    companyName: compName,
    impact: a.impact_score != null ? a.impact_score : (a.confluence_score != null ? a.confluence_score : "-"),
    impactColor: (a.impact_score || 0) >= 80 ? "emerald" : "amber",
    catalyst: a.catalyst_type || "CATALYST",
    category: a.catalyst_type?.toLowerCase() || "high",
    signal: bias.replace(/_/g, " "),
    signalType: sigType,
    targetPrice: tPrice,
    stopLoss: sLoss,
    title: a.alert_title,
    reasons: a.factual_reasons || [],
    metrics: {
      delivery: deliveryVal,
      rsi: rsiVal,
      vwap: vwapVal,
      flow: oiVal
    },
    vsaNote: vsaNote ? String(vsaNote).replace(/_/g, ' ') : "",
    vix: vixVal,
    dematPosition: dematSanitized,
    factors: resolvedFactors,
    entryRange: rawSnap.tactical_levels?.entry_range || "-",
    riskReward: rawSnap.tactical_levels?.risk_reward_ratio || "-",
    time: new Date(a.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  };
}

interface UseAlertsManagerProps {
  userId?: string;
}

export function useAlertsManager({ userId }: UseAlertsManagerProps) {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [alertFilter, setAlertFilter] = useState<string>("all");
  const [expandedRadarId, setExpandedRadarId] = useState<string | null>(null);
  const [sharingAlert, setSharingAlert] = useState<AlphaCardData | null>(null);

  const loadAlertsData = useCallback(async (uid: string) => {
    if (supabase) {
      try {
        const { data } = await supabase.from('stok_alerts').select('*').eq('user_id', uid).order('created_at', { ascending: false });
        if (data && data.length > 0) {
          setAlerts(data.map(formatAlertRecord));
          return;
        }
      } catch (e) {
        console.warn("Alerts fetch error:", e);
      }
    }
    setAlerts([]);
  }, []);

  // Realtime Supabase Alert Channel for instantaneous (<50ms) push notifications
  useEffect(() => {
    if (!supabase || !userId) return;

    const channel = supabase
      .channel(`stok-alerts-realtime-${userId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'stok_alerts',
          filter: `user_id=eq.${userId}`,
        },
        (payload: any) => {
          if (payload?.new) {
            const formatted = formatAlertRecord(payload.new);
            setAlerts((prev) => [formatted, ...prev.filter(a => a.id !== formatted.id)]);
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [userId]);

  return {
    alerts, setAlerts,
    alertFilter, setAlertFilter,
    expandedRadarId, setExpandedRadarId,
    sharingAlert, setSharingAlert,
    loadAlertsData,
    formatAlertRecord
  };
}
