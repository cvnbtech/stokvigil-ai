import logging
from typing import Dict, Any, Optional, Tuple, List

from app.macro_filter import calculate_sector_relative_strength

logger = logging.getLogger("stokvigil.engine.deterministic")


def get_adaptive_weights(macro_data: Dict[str, Any], adx_regime: Optional[str] = None) -> Tuple[Dict[str, float], str]:
    """
    Dynamically allocates confluence weights across the 4 pillars based on macro market regime.
    Prioritizes forensic health and flow during distribution/volatility, and technical momentum during strong trends.
    Returns (weights_dict, regime_name).
    """
    vix_val = macro_data.get("india_vix") or macro_data.get("vix_value")
    vix = float(vix_val) if vix_val is not None else None
    adr_val = macro_data.get("market_breadth_adr") or macro_data.get("adr_ratio")
    adr = float(adr_val) if adr_val is not None else None
    
    # Regime 1: High Volatility, Market Distribution, or Data Unavailable (Defensive posture)
    if (vix is not None and vix > 16.5) or (adr is not None and adr < 0.8) or vix is None or adr is None:
        return {"tech": 0.15, "flow": 0.35, "forensics": 0.35, "news": 0.15}, "HIGH_VOLATILITY_DEFENSIVE"
    # Regime 2: Strong Trending Bull Market (Momentum)
    elif adr >= 1.2 and vix <= 14.5:
        return {"tech": 0.40, "flow": 0.30, "forensics": 0.15, "news": 0.15}, "BULL_MOMENTUM"
    # Regime 3: Normal / Balanced Market
    else:
        return {"tech": 0.30, "flow": 0.25, "forensics": 0.25, "news": 0.20}, "BALANCED_NORMAL"


def compute_tactical_levels(
    current_price: Optional[float],
    atr_val: Optional[float],
    swing_high: Optional[float] = 0.0,
    demat_context: Optional[Dict[str, Any]] = None,
    h3: Optional[float] = None,
    h4: Optional[float] = None,
    l3: Optional[float] = None,
    l4: Optional[float] = None,
    vwap_val: Optional[float] = None,
    vwap_upper_1s: Optional[float] = None,
    action_bias: str = "HOLD_NEUTRAL",
    risk_budget: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Computes institutional tactical levels: entry range, target 1, target 2, protective stop-loss, and R:R ratio.
    Direction-Aware: Properly computes downside targets and protective buy-stops for SELL_WATCH short / breakdown trades.
    Includes Mathematical Risk-Based Position Sizer (1% Capital Risk Rule).
    ZERO-DEFAULT RULE: Returns None if current_price is None or <= 0.
    """
    if current_price is None or float(current_price) <= 0:
        return None

    price = float(current_price)
    atr = float(atr_val or (price * 0.015))
    if atr <= 0:
        atr = price * 0.015

    # Determine risk budget (defaults to ₹2,000 or 1% of Demat portfolio)
    budget = 2000.0
    if risk_budget is not None and float(risk_budget) > 0:
        budget = float(risk_budget)
    elif demat_context and isinstance(demat_context, dict):
        demat_val = demat_context.get("portfolio_value") or demat_context.get("total_value") or demat_context.get("capital")
        if demat_val and float(demat_val) > 0:
            budget = max(500.0, round(float(demat_val) * 0.01, 2))

    is_sell = action_bias in ["SELL_WATCH"]

    # 1. Bearish Breakdown / Short Setup (SELL_WATCH)
    if is_sell:
        if vwap_val is not None and vwap_val > 0:
            entry_min = round(min(price, vwap_val), 2)
            entry_max = round(max(price, vwap_val), 2)
        else:
            entry_min = round(price * 0.995, 2)
            entry_max = round(price * 1.005, 2)

        if l3 and l4 and float(l3) > 0 and float(l4) > 0 and float(l3) < price:
            target_1 = round(min(price - (1.5 * atr), float(l3)), 2)
            target_2 = round(min(price - (2.5 * atr), float(l4)), 2)
            stop_loss = round(max(price + (1.0 * atr), float(h3 or (price * 1.02))), 2)
        else:
            target_1 = round(price - (1.5 * atr), 2)
            target_2 = round(price - (2.5 * atr), 2)
            stop_loss = round(price + (1.0 * atr), 2)

        target_1 = min(target_1, round(price * 0.98, 2))
        target_2 = min(target_2, round(price * 0.95, 2))
        stop_loss = max(stop_loss, round(price * 1.02, 2))

        risk_val = max(1.0, stop_loss - price)
        reward_val = max(2.5, price - target_2)
        rr_ratio = round(reward_val / risk_val, 1)

        risk_per_share = round(abs(price - stop_loss), 2)
        effective_risk = max(0.5, risk_per_share)
        recommended_qty = max(1, int(budget // effective_risk))
        capital_at_risk = round(recommended_qty * effective_risk, 2)
        estimated_pos_val = round(recommended_qty * price, 2)

        return {
            "entry_range": f"₹{entry_min:,.2f} - ₹{entry_max:,.2f}",
            "target_1": f"₹{target_1:,.2f}",
            "target_2": f"₹{target_2:,.2f}",
            "tactical_support_1": f"₹{target_1:,.2f}",
            "expansion_support_2": f"₹{target_2:,.2f}",
            "protective_stop_loss": f"₹{stop_loss:,.2f}",
            "risk_reward_ratio": f"1:{rr_ratio}",
            "recommended_quantity": recommended_qty,
            "risk_per_share": risk_per_share,
            "capital_at_risk": capital_at_risk,
            "estimated_position_value": estimated_pos_val,
            "risk_budget": budget,
            "position_sizing_rule": f"1% Capital Risk Rule (₹{budget:,.0f} risk budget)",
            "volatility_disclaimer": "Mathematical volatility benchmarks (1.5x / 2.5x ATR). Not an advisory target or price promise."
        }

    # 2. Bullish Setup (BUY_WATCH / HOLD_NEUTRAL) or Demat Protection
    if vwap_val is not None and vwap_upper_1s is not None and vwap_val > 0:
        entry_min = round(min(price, vwap_val), 2)
        entry_max = round(max(price, vwap_upper_1s), 2)
    elif h3 and l3 and float(l3) > 0:
        entry_min = round(min(price * 0.995, float(l3)), 2)
        entry_max = round(max(price * 1.005, price), 2)
    else:
        entry_min = round(price * 0.995, 2)
        entry_max = round(price * 1.005, 2)

    try:
        swing = float(swing_high) if swing_high is not None and not isinstance(swing_high, dict) else 0.0
    except (ValueError, TypeError):
        swing = 0.0
    if swing > price:
        target_1 = round(price + (1.5 * atr), 2)
        target_2 = round(swing, 2)
        stop_loss = round(price - (1.0 * atr), 2)
    elif h3 and l3 and float(h3) > 0 and float(l3) > 0:
        target_1 = round(max(price + (1.5 * atr), float(h3)), 2)
        target_2 = round(max(price + (2.5 * atr), float(h4 or h3)), 2)
        stop_loss = round(min(price - (1.0 * atr), float(l4 or l3)), 2)
    else:
        target_1 = round(price + (1.5 * atr), 2)
        target_2 = round(price + (2.5 * atr), 2)
        stop_loss = round(price - (1.0 * atr), 2)

    target_1 = max(target_1, round(price * 1.02, 2))
    target_2 = max(target_2, round(price * 1.05, 2))
    stop_loss = min(stop_loss, round(price * 0.98, 2))

    if demat_context and demat_context.get("is_in_portfolio"):
        avg_buy = demat_context.get("average_buy_price", price)
        chandelier_sl = round(price - (2.5 * atr), 2)
        base_cost_sl = round(avg_buy * 0.96, 2)
        stop_loss = max(stop_loss, base_cost_sl, chandelier_sl)

    risk_val = max(1.0, price - stop_loss)
    reward_val = max(2.5, target_2 - price)
    rr_ratio = round(reward_val / risk_val, 1)

    risk_per_share = round(abs(price - stop_loss), 2)
    effective_risk = max(0.5, risk_per_share)
    recommended_qty = max(1, int(budget // effective_risk))
    capital_at_risk = round(recommended_qty * effective_risk, 2)
    estimated_pos_val = round(recommended_qty * price, 2)

    return {
        "entry_range": f"₹{entry_min:,.2f} - ₹{entry_max:,.2f}",
        "target_1": f"₹{target_1:,.2f}",
        "target_2": f"₹{target_2:,.2f}",
        "tactical_resistance_1": f"₹{target_1:,.2f}",
        "expansion_resistance_2": f"₹{target_2:,.2f}",
        "protective_stop_loss": f"₹{stop_loss:,.2f}",
        "risk_reward_ratio": f"1:{rr_ratio}",
        "recommended_quantity": recommended_qty,
        "risk_per_share": risk_per_share,
        "capital_at_risk": capital_at_risk,
        "estimated_position_value": estimated_pos_val,
        "risk_budget": budget,
        "position_sizing_rule": f"1% Capital Risk Rule (₹{budget:,.0f} risk budget)",
        "volatility_disclaimer": "Mathematical volatility benchmarks (1.5x / 2.5x ATR). Not an advisory target or price promise."
    }


def compute_deterministic_confluence(
    symbol: str,
    technicals: Dict[str, Any],
    flow_data: Dict[str, Any],
    macro_data: Dict[str, Any],
    forensics: Dict[str, Any],
    financials: Dict[str, Any],
    news_items: List[Dict[str, Any]],
    holding_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Deterministic Quantitative Confluence Engine with Adaptive Regime Weighting.
    Evaluates institutional math in 0.001ms with zero API costs.
    """
    price_candidate = (
        technicals.get("current_price") or 
        financials.get("price") or 
        (holding_info.get("current_market_price") if holding_info else None) or
        (holding_info.get("last_price") if holding_info else None) or
        (holding_info.get("average_price") if holding_info else None) or
        technicals.get("previous_close")
    )
    has_real_price = bool(price_candidate and float(price_candidate) > 0)
    current_price = float(price_candidate) if has_real_price else 0.0
    
    raw_atr = technicals.get("atr_14")
    if raw_atr is not None and float(raw_atr) > 0:
        atr_val = float(raw_atr)
    elif has_real_price:
        atr_val = max(1.0, round(current_price * 0.02, 2))
    else:
        atr_val = 0.0

    demat_context = {"is_in_portfolio": False, "quantity": 0, "average_buy_price": 0.0, "unrealized_pnl_pct": 0.0}
    if holding_info:
        avg_p = float(holding_info.get("average_price", 0.0) or 0.0)
        curr_cmp = float(
            technicals.get("current_price") or 
            financials.get("price") or 
            holding_info.get("current_market_price") or 
            holding_info.get("last_price") or 
            0.0
        )
        if avg_p > 0 and curr_cmp > 0:
            pnl_pct = round(((curr_cmp - avg_p) / avg_p) * 100, 2)
        elif holding_info.get("unrealized_pnl_pct") is not None:
            pnl_pct = round(float(holding_info["unrealized_pnl_pct"]), 2)
        elif holding_info.get("pnl_percentage") is not None:
            pnl_pct = round(float(holding_info["pnl_percentage"]), 2)
        else:
            pnl_pct = 0.0

        demat_context = {
            "is_in_portfolio": True,
            "quantity": holding_info.get("quantity", 0),
            "average_buy_price": avg_p,
            "unrealized_pnl_pct": pnl_pct
        }

    raw_ts = technicals.get("technical_score")
    tech_score = float(raw_ts) if raw_ts is not None else 50.0
    raw_fs = flow_data.get("flow_score")
    flow_score = float(raw_fs) if raw_fs is not None else 50.0
    raw_fors = forensics.get("forensic_score")
    forensic_score = float(raw_fors) if raw_fors is not None else 50.0
    
    news_score = 50
    catalyst_category = "TECHNICAL_BREAKOUT"
    alert_title = f"{symbol}: Technical & Momentum Update"
    confluence_drivers = []
    
    for item in news_items:
        title_upper = item.get('title', '').upper()
        if "BLOCK DEAL" in title_upper or "BULK DEAL" in title_upper:
            news_score += 35
            catalyst_category = "BLOCK_DEAL"
            alert_title = f"{symbol}: Institutional Block/Bulk Deal Reported"
            confluence_drivers.append(f"Exchange Filing: {item['title']}")
            break
        elif any(k in title_upper for k in ["PROFIT", "REVENUE", "Q1", "Q2", "Q3", "Q4", "EARNINGS"]):
            news_score += 30
            catalyst_category = "EARNINGS_BEAT"
            alert_title = f"{symbol}: Quarterly Earnings & Financial Catalyst"
            confluence_drivers.append(f"Financial Disclosure: {item['title']}")
            break

    vsa_regime = flow_data.get("vsa_regime", "NORMAL_VOLUME_SPREAD")
    if vsa_regime == "SMART_MONEY_ABSORPTION":
        del_p = flow_data.get("delivery_pct")
        del_str = f" ({del_p}%)" if del_p is not None else ""
        confluence_drivers.append(f"Wyckoff VSA: Institutional Delivery Absorption{del_str}")
        flow_score = min(95, flow_score + 8)
    elif vsa_regime == "OPERATOR_CHURN_TRAP":
        confluence_drivers.append("Wyckoff VSA Warning: Speculative Operator Churn (Low Delivery %)")
        flow_score = max(20, flow_score - 10)

    sector_name = forensics.get("sector_name", "BROAD_MARKET")
    if sector_name != "BROAD_MARKET":
        confluence_drivers.append(f"Sector Alignment: {sector_name}")

    adx_regime = technicals.get("adx_regime", "MODERATE_TREND")
    adx_val = technicals.get("adx_14")
    weights, macro_regime = get_adaptive_weights(macro_data, adx_regime)

    confluence_score = int(round(
        (tech_score * weights["tech"]) +
        (flow_score * weights["flow"]) +
        (forensic_score * weights["forensics"]) +
        (min(95, news_score) * weights["news"])
    ))

    # 1. ADX Trend Strength Check
    if adx_regime == "CHOPPY_SIDEWAYS":
        adx_str = f" ({adx_val} < 20)" if adx_val is not None else ""
        confluence_drivers.append(f"ADX Warning: Low trend strength{adx_str}. Sideways consolidation risk.")
        confluence_score = max(25, confluence_score - 8)
    elif adx_regime == "STRONG_TREND":
        adx_str = f" ({adx_val} >= 25)" if adx_val is not None else ""
        confluence_drivers.append(f"ADX Confirmation: Strong Institutional Trend{adx_str}")

    # 2. Mansfield Relative Strength vs NIFTY 50
    rs_regime = technicals.get("rs_regime", "IN_LINE")
    rs_rating = technicals.get("rs_rating")
    if rs_regime == "OUTPERFORMING_LEADER" and rs_rating is not None:
        confluence_drivers.append(f"Market Leadership: Outperforming NIFTY 50 by {rs_rating:+.1f}%")
        confluence_score = min(98, confluence_score + 5)
    elif rs_regime == "UNDERPERFORMING_LAGGARD" and rs_rating is not None:
        confluence_drivers.append(f"Relative Strength Warning: Underperforming NIFTY 50 by {rs_rating:+.1f}%")
        confluence_score = max(25, confluence_score - 5)

    # 3. Sector Benchmark Relative Strength Integration
    sector_rs_dict = calculate_sector_relative_strength(symbol, rs_rating)
    sec_regime = sector_rs_dict.get("sector_rs_regime")
    sec_rating = sector_rs_dict.get("sector_rs_rating")
    if sec_regime == "SECTOR_LEADER" and sec_rating is not None:
        confluence_drivers.append(f"Sector Leader: Outperforming {sector_rs_dict.get('sector_name')} by {sec_rating:+.1f}%")
        confluence_score = min(98, confluence_score + 4)

    # 4. Intraday Momentum Surge Driver
    day_chg = technicals.get("change_pct")
    orb_stat = technicals.get("orb_status")
    if day_chg is not None and day_chg >= 5.0 and orb_stat == "BULLISH_ORB_BREAKOUT":
        confluence_drivers.append(f"Price Surge: Intraday breakout of {day_chg:+.1f}% confirmed by 15m Opening Range High.")
        confluence_score = min(98, confluence_score + 6)
    elif sec_regime == "SECTOR_LAGGARD" and sec_rating is not None:
        confluence_drivers.append(f"Sector Laggard Warning: Underperforming {sector_rs_dict.get('sector_name')} by {sec_rating:+.1f}%")
        confluence_score = max(25, confluence_score - 6)

    # 5. TTM Volatility Squeeze Engine Integration
    ttm_squeeze = technicals.get("ttm_squeeze", {})
    if ttm_squeeze.get("squeeze_release"):
        mom_trend = ttm_squeeze.get("momentum_trend")
        if mom_trend in ["EXPANDING_BULLISH", "CONTRACTING_BEARISH"]:
            confluence_drivers.append("TTM Squeeze Release: Explosive volatility expansion detected.")
            confluence_score = min(98, confluence_score + 6)
        elif mom_trend in ["EXPANDING_BEARISH"]:
            confluence_drivers.append("TTM Squeeze Breakdown: Downward volatility expansion.")
            confluence_score = max(20, confluence_score - 6)
    elif ttm_squeeze.get("squeeze_on"):
        confluence_drivers.append("TTM Squeeze Coiling: Bollinger Bands compressed inside Keltner Channels (High breakout potential).")
        confluence_score = min(95, confluence_score + 2)

    # 6. Triple-Timeframe Fractal Harmony
    daily_rsi = technicals.get("rsi_daily")
    daily_bullish = (current_price >= (technicals.get("ema_50") or current_price)) and (daily_rsi is not None and daily_rsi >= 48)
    m15_bullish = ((technicals.get("price_vs_vwap_pct") or 0.0) >= -0.2) and (technicals.get("rsi_divergence") != "BEARISH_REGULAR_DIVERGENCE")
    m5_bullish = technicals.get("is_volume_surge", False) or (technicals.get("macd_trend") in ["BULLISH_CROSSOVER", "EXPANDING_BULLISH_MOMENTUM"])

    if daily_bullish and m15_bullish and m5_bullish:
        confluence_drivers.append("Triple-Timeframe Confluence: Daily Tide + 15m Wave + 5m Trigger aligned Bullish")
        confluence_score = min(98, confluence_score + 8)
    elif not daily_bullish and m5_bullish and daily_rsi is not None:
        confluence_drivers.append("Timeframe Divergence: 5m rally conflicting with Daily macro downtrend")
        confluence_score = max(30, confluence_score - 8)

    # 7. F&O Options Chain & Delta-OI Integration
    if flow_data.get("is_fo_stock"):
        pcr_val = flow_data.get("pcr")
        max_pain = flow_data.get("max_pain_strike")
        sup_strike = flow_data.get("major_support_strike")
        res_strike = flow_data.get("major_resistance_strike")
        net_oi_bias = flow_data.get("net_oi_bias")

        if net_oi_bias == "CALL_UNWINDING_SHORT_COVERING":
            confluence_drivers.append("F&O Momentum: Call unwinding detected across strikes (Short covering fuel).")
            confluence_score = min(98, confluence_score + 5)
        elif net_oi_bias == "AGGRESSIVE_PUT_WRITING":
            confluence_drivers.append("F&O Institutional Support: Aggressive Put writing creates strong price floor.")
            confluence_score = min(98, confluence_score + 4)
        elif net_oi_bias == "CALL_WRITING_RESISTANCE":
            confluence_drivers.append("F&O Resistance: Heavy Call writing overhead capping upward momentum.")
            confluence_score = max(25, confluence_score - 5)
        
        if pcr_val is not None and pcr_val >= 1.25:
            sup_str = f" at ₹{sup_strike:,.0f}" if sup_strike else ""
            confluence_drivers.append(f"Option Chain: Bullish Put-Call Ratio ({pcr_val}) with PE writing support{sup_str}")
            confluence_score = min(98, confluence_score + 4)
        elif pcr_val is not None and pcr_val <= 0.65:
            res_str = f" at ₹{res_strike:,.0f}" if res_strike else ""
            confluence_drivers.append(f"Option Chain Warning: Bearish PCR ({pcr_val}) with heavy CE writing{res_str}")
            confluence_score = max(25, confluence_score - 5)

        if max_pain is not None and max_pain > 0 and current_price > 0:
            diff_pct = abs(current_price - max_pain) / max_pain * 100
            if diff_pct <= 0.75:
                confluence_drivers.append(f"F&O Max Pain Pinning: Price ₹{current_price:,.2f} near Max Pain ₹{max_pain:,.0f} ({diff_pct:.1f}% dev)")
            elif current_price > max_pain and pcr_val is not None and pcr_val >= 1.0:
                confluence_drivers.append(f"F&O Bullish Driver: Trading above Max Pain Strike ₹{max_pain:,.0f}")
                confluence_score = min(98, confluence_score + 3)
    elif flow_data.get("fo_oi_status") == "BSE_CASH_DELIVERY":
        del_pct = flow_data.get("delivery_pct")
        del_str = f" ({del_pct}%)" if del_pct is not None else ""
        confluence_drivers.append(f"BSE Cash Market: Delivery volume accumulation{del_str}")

    action_bias = "HOLD_NEUTRAL"
    has_actionable_signal = False
    rsi_15m_val = technicals.get("rsi_15m")

    # Circuit Lock Detection & Handling
    is_locked = technicals.get("is_circuit_locked", False)
    lock_type = technicals.get("circuit_lock_type")
    if is_locked:
        if lock_type == "LOWER_CIRCUIT":
            confluence_drivers.insert(0, "Circuit Lock Warning: Stock locked at Lower Circuit. Order book frozen (No active buyers).")
            confluence_score = min(15, confluence_score)
            action_bias = "SELL_WATCH"
            has_actionable_signal = True
            catalyst_category = "PRICE_BREAKOUT"
            alert_title = f"{symbol}: Trapped at Lower Circuit Freeze"
        elif lock_type == "UPPER_CIRCUIT":
            confluence_drivers.insert(0, "Circuit Lock Notice: Stock locked at Upper Circuit. Order book frozen (No active sellers).")
            confluence_score = max(85, confluence_score)
            action_bias = "BUY_WATCH"
            has_actionable_signal = True
            catalyst_category = "PRICE_BREAKOUT"
            alert_title = f"{symbol}: Locked at Upper Circuit Freeze"

    # Hard Risk Veto for Severe Intraday Breakdown / Supply Shock
    day_change = technicals.get("change_pct")
    p_vs_vwap = technicals.get("price_vs_vwap_pct")
    l4_level = technicals.get("camarilla_pivots", {}).get("l4")
    
    is_severe_breakdown = False
    breakdown_reasons = []

    if day_change is not None and day_change <= -3.5:
        is_severe_breakdown = True
        breakdown_reasons.append(f"Severe intraday price drop ({day_change:+.2f}%)")
    if p_vs_vwap is not None and p_vs_vwap <= -2.0 and technicals.get("is_volume_surge"):
        is_severe_breakdown = True
        breakdown_reasons.append(f"VWAP Breakdown with Volume Surge ({p_vs_vwap:+.2f}% below VWAP)")
    if l4_level is not None and current_price > 0 and current_price < l4_level:
        is_severe_breakdown = True
        breakdown_reasons.append(f"Camarilla L4 institutional floor breached (₹{l4_level:,.2f})")

    if is_severe_breakdown:
        confluence_score = min(28, confluence_score)
        action_bias = "SELL_WATCH"
        has_actionable_signal = True
        catalyst_category = "PRICE_BREAKOUT"
        chg_fmt = f"{day_change:+.1f}%" if day_change is not None else "-3.5%"
        alert_title = f"{symbol}: Severe Price Breakdown Alert ({chg_fmt})"
        for r in reversed(breakdown_reasons):
            confluence_drivers.insert(0, f"Critical Supply Alert: {r}")

    # Demat Holding Portfolio Protection Override
    if demat_context["is_in_portfolio"]:
        pnl = demat_context["unrealized_pnl_pct"]
        if pnl <= -3.5:
            action_bias = "TRAILING_SL_ALERT"
            has_actionable_signal = True
            catalyst_category = "TRAILING_STOP_TRIGGER"
            alert_title = f"{symbol}: Stop-Loss Defense Trigger (P&L: {pnl:+.1f}%)"
            confluence_drivers.insert(0, f"CRITICAL RISK DEFENSE: Position down {pnl:+.1f}%. Protective stop-loss breach.")
            confluence_score = min(20, confluence_score)
        elif pnl >= 5.0 and rsi_15m_val is not None and rsi_15m_val > 72:
            action_bias = "TRAILING_SL_ALERT"
            has_actionable_signal = True
            catalyst_category = "TRAILING_STOP_TRIGGER"
            alert_title = f"{symbol}: Trailing Stop-Loss Trigger (P&L: +{pnl:+.1f}%)"
            confluence_drivers.insert(0, f"Position gained +{pnl:+.1f}%; 15m RSI reached {rsi_15m_val} (Overbought zone).")
    elif not is_severe_breakdown and not is_locked:
        if confluence_score >= 72 and has_real_price:
            action_bias = "BUY_WATCH"
            has_actionable_signal = True
            if day_change is not None and day_change >= 5.0:
                catalyst_category = "PRICE_BREAKOUT"
                alert_title = f"{symbol}: Intraday Momentum Breakout Surge ({day_change:+.1f}%)"
                confluence_drivers.insert(0, f"Momentum Breakout: Strong intraday surge of {day_change:+.2f}% with bullish momentum.")
        elif confluence_score <= 38 and has_real_price:
            action_bias = "SELL_WATCH"
            has_actionable_signal = True

    # Multi-Timeframe, Macro & Sector Veto Guardrails
    ema_200_val = technicals.get("ema_200")
    is_macro_downtrend = bool(ema_200_val and current_price < ema_200_val)
    is_macro_uptrend = bool(ema_200_val and current_price > ema_200_val)
    is_high_vix = not macro_data.get("allow_breakout_trades", True)
    adr_val = macro_data.get("adr_ratio")
    is_breadth_veto = bool(adr_val is not None and float(adr_val) < 0.60)
    is_sector_laggard_veto = bool(sec_regime == "SECTOR_LAGGARD" and sec_rating is not None and sec_rating <= -3.5)

    if (is_macro_downtrend or is_high_vix or is_breadth_veto or is_sector_laggard_veto) and action_bias == "BUY_WATCH":
        veto_reasons = []
        if is_macro_downtrend:
            veto_reasons.append(f"Below 200 EMA (₹{ema_200_val:,.2f})")
        if is_high_vix:
            veto_reasons.append(f"High VIX ({macro_data.get('india_vix')})")
        if is_breadth_veto:
            veto_reasons.append(f"Market Breadth Distribution (ADR: {adr_val} < 0.60)")
        if is_sector_laggard_veto:
            veto_reasons.append(f"Sector Laggard Veto ({sec_rating:+.1f}% vs {sector_rs_dict.get('sector_name')})")

        logger.info(f"Veto triggered for {symbol}: {', '.join(veto_reasons)}. Downgrading BUY_WATCH to HOLD_NEUTRAL.")
        action_bias = "HOLD_NEUTRAL"
        has_actionable_signal = False
        confluence_score = min(55, confluence_score - 8)
        if is_macro_downtrend:
            confluence_drivers.append(f"Macro Trend Veto: Price ₹{current_price:,.2f} is below 200 EMA (₹{ema_200_val:,.2f}). Counter-trend long breakout blocked.")
        if is_breadth_veto:
            confluence_drivers.append(f"Market Breadth Veto: Broad market distribution ({macro_data.get('breadth_regime', 'DISTRIBUTION')}, ADR {adr_val}). Long breakout blocked.")
        if is_sector_laggard_veto:
            confluence_drivers.append(f"Sector Laggard Veto: Stock lagging sector by {sec_rating:+.1f}%. Long setup neutralized.")

    if is_macro_uptrend and action_bias == "SELL_WATCH":
        logger.info(f"Veto triggered for {symbol}: Above 200 EMA (₹{ema_200_val:,.2f}). Downgrading SELL_WATCH to HOLD_NEUTRAL.")
        action_bias = "HOLD_NEUTRAL"
        has_actionable_signal = False
        confluence_score = max(45, confluence_score + 8)
        confluence_drivers.append(f"Macro Trend Veto: Price ₹{current_price:,.2f} is above 200 EMA (₹{ema_200_val:,.2f}). Shorting against primary bull trend blocked.")

    # Confluence Driver Highlights
    if technicals.get("macd_trend") == "BULLISH_CROSSOVER":
        confluence_drivers.append("15m MACD Bullish Crossover detected.")
    if technicals.get("is_volume_surge") and technicals.get("volume_multiple"):
        confluence_drivers.append(f"5m Volume is {technicals.get('volume_multiple')}x above 20 MA.")
    if flow_data.get("is_high_delivery") and flow_data.get("delivery_pct"):
        confluence_drivers.append(f"Institutional delivery estimated at {flow_data.get('delivery_pct')}%.")
    vwap_val = technicals.get("vwap")
    if vwap_val is not None and current_price > vwap_val:
        confluence_drivers.append(f"Trading above Intraday VWAP (₹{vwap_val:,.2f}).")
    if not confluence_drivers and has_real_price:
        rsi_str = f" | 15m RSI: {rsi_15m_val}" if rsi_15m_val is not None else ""
        confluence_drivers.append(f"Current price: ₹{current_price:,.2f}{rsi_str}")

    # Camarilla Equation & VWAP Bands Tactical Execution Levels
    camarilla = technicals.get("camarilla_pivots", {})
    h4 = camarilla.get("h4")
    h3 = camarilla.get("h3")
    l3 = camarilla.get("l3")
    l4 = camarilla.get("l4")
    vwap_upper_1s = technicals.get("vwap_upper_1s")

    if has_real_price and current_price > 0:
        swing_high = float(technicals.get("swing_high") or technicals.get("day_high") or 0.0)
        tactical_dict = compute_tactical_levels(
            current_price=current_price,
            atr_val=atr_val,
            swing_high=swing_high,
            demat_context=demat_context,
            h3=h3,
            h4=h4,
            l3=l3,
            l4=l4,
            vwap_val=vwap_val,
            vwap_upper_1s=vwap_upper_1s,
            action_bias=action_bias
        )
        if demat_context["is_in_portfolio"] and tactical_dict:
            avg_buy = demat_context.get("average_buy_price", current_price)
            holding_guidance = f"Chandelier Trailing SL active at {tactical_dict['protective_stop_loss']} (Protecting cost basis ₹{avg_buy:,.2f})."
        else:
            holding_guidance = "Track for optimal entry in tactical range."
    else:
        holding_guidance = None
        tactical_dict = None

    return {
        "symbol": symbol,
        "has_actionable_signal": has_actionable_signal,
        "action_bias": action_bias,
        "confluence_score": confluence_score,
        "alert_title": alert_title,
        "catalyst_category": catalyst_category,
        "confluence_drivers": confluence_drivers,
        "tactical_levels": tactical_dict,
        "holding_guidance": holding_guidance,
        "growth_outlook_summary": (
            f"Long term valuation: P/E {financials.get('pe_ratio') if financials.get('pe_ratio') is not None else '-'}, "
            f"D/E {financials.get('debt_to_equity') if financials.get('debt_to_equity') is not None else '-'}."
        ),
        "factor_breakdown": {
            "technicals": tech_score,
            "flow": flow_score,
            "forensics": forensic_score,
            "catalysts": min(95, news_score)
        },
        "derivatives_flow": {
            "is_fo_stock": flow_data.get("is_fo_stock", False),
            "pcr": flow_data.get("pcr") if flow_data.get("is_fo_stock") else None,
            "max_pain_strike": flow_data.get("max_pain_strike") if flow_data.get("is_fo_stock") else None,
            "major_support_strike": flow_data.get("major_support_strike") if flow_data.get("is_fo_stock") else None,
            "major_resistance_strike": flow_data.get("major_resistance_strike") if flow_data.get("is_fo_stock") else None,
            "fo_status": flow_data.get("fo_oi_status") if flow_data.get("is_fo_stock") else None
        },
        "market_breadth": {
            "adr_ratio": macro_data.get("adr_ratio"),
            "breadth_regime": macro_data.get("breadth_regime"),
            "advances": macro_data.get("advances"),
            "declines": macro_data.get("declines")
        }
    }


def check_has_active_catalyst(
    symbol: str,
    technicals: Dict[str, Any],
    flow_data: Dict[str, Any],
    news_items: List[Dict[str, Any]],
    holding_info: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    Tier-1 Quantitative Gatekeeper: Evaluates whether a stock has an active momentum,
    volume, corporate filing, or Demat stop-loss catalyst before invoking Gemini AI.
    Quiet/flat stocks are evaluated via pure deterministic mathematics in 0.001 ms.
    """
    # 1. Demat Holding Protection Trigger
    if holding_info:
        raw_curr = technicals.get("current_price")
        curr_p = float(raw_curr) if raw_curr is not None else 0.0
        raw_avg = holding_info.get("average_price")
        avg_p = float(raw_avg) if raw_avg is not None else 0.0
        pnl_pct = ((curr_p - avg_p) / avg_p * 100) if avg_p > 0 else 0.0
        raw_rsi = technicals.get("rsi_15m")
        rsi = float(raw_rsi) if raw_rsi is not None else 50.0
        if (pnl_pct >= 5.0 and rsi > 70.0) or pnl_pct <= -3.5:
            return True, f"Demat Holding Protection Trigger (P&L: {pnl_pct:+.1f}%)"

    # 2. Sharp Intraday Price Surge / Breakdown
    change_pct = technicals.get("change_pct")
    if change_pct is not None:
        try:
            cp = float(change_pct)
            if abs(cp) >= 2.5:
                return True, f"Sharp Price Movement ({cp:+.1f}%)"
        except (ValueError, TypeError):
            pass

    orb_status = technicals.get("orb_status")
    if orb_status in ["BULLISH_ORB_BREAKOUT", "BEARISH_ORB_BREAKDOWN"]:
        if technicals.get("candle_close_confirmed", True):
            return True, f"15m Opening Range Break ({orb_status} - Confirmed)"

    if technicals.get("is_circuit_locked"):
        return True, f"Circuit Lock Freeze ({technicals.get('circuit_lock_type')})"

    # 3. Institutional Volume Surge (>= 1.5x 20-period volume MA)
    raw_vol = technicals.get("volume_multiple")
    if raw_vol is None:
        raw_vol = technicals.get("volume_surge_ratio")
    try:
        vol_mult = float(raw_vol) if raw_vol is not None else 1.0
    except (ValueError, TypeError):
        vol_mult = 1.0

    if technicals.get("is_volume_surge") or vol_mult >= 1.5:
        return True, f"Volume Surge ({vol_mult:.1f}x 20-MA)"

    # 4. Momentum Extremes or Divergence
    raw_rsi_15m = technicals.get("rsi_15m")
    if raw_rsi_15m is not None:
        try:
            rsi_15m = float(raw_rsi_15m)
            if rsi_15m >= 68.0 or rsi_15m <= 32.0:
                return True, f"15m RSI Momentum Extreme ({rsi_15m:.1f})"
        except (ValueError, TypeError):
            pass

    if technicals.get("rsi_divergence") in ["BULLISH_DIVERGENCE", "BEARISH_DIVERGENCE"]:
        return True, f"RSI Divergence: {technicals.get('rsi_divergence')}"

    # 5. MACD Trend Transition
    if technicals.get("macd_trend") == "BULLISH_CROSSOVER":
        return True, "15m MACD Bullish Crossover"

    # 6. Institutional Order Flow / F&O Build-up & Options Extreme
    if flow_data.get("is_high_delivery"):
        return True, f"High Institutional Delivery ({flow_data.get('delivery_pct')}%)"
    if flow_data.get("fo_oi_status") in ["LONG_BUILDUP", "SHORT_BUILDUP"]:
        raw_pcr = flow_data.get("pcr")
        try:
            pcr = float(raw_pcr) if raw_pcr is not None else 1.0
        except (ValueError, TypeError):
            pcr = 1.0
        if pcr >= 1.3 or pcr <= 0.7:
            return True, f"Derivatives Regime: {flow_data.get('fo_oi_status')} (PCR: {pcr:.2f})"
    if flow_data.get("is_fo_stock"):
        raw_pcr = flow_data.get("pcr")
        try:
            pcr = float(raw_pcr) if raw_pcr is not None else 1.0
        except (ValueError, TypeError):
            pcr = 1.0
        if pcr >= 1.4 or pcr <= 0.6:
            return True, f"Extreme Option PCR Catalyst ({pcr:.2f})"

    # 7. Intraday VWAP Breakout with Momentum Confluence
    raw_vwap = technicals.get("price_vs_vwap_pct")
    try:
        vwap_pct = abs(float(raw_vwap)) if raw_vwap is not None else 0.0
    except (ValueError, TypeError):
        vwap_pct = 0.0

    if vwap_pct >= 1.2 or (vwap_pct >= 0.8 and (vol_mult >= 1.3 or technicals.get("is_volume_surge"))):
        return True, f"Intraday VWAP Expansion ({vwap_pct:.1f}%)"

    # 8. Real-Time News / Corporate Catalysts
    for item in news_items:
        title_upper = str(item.get("title", "")).upper()
        if any(w in title_upper for w in ["BLOCK DEAL", "BULK DEAL", "PROFIT", "REVENUE", "QUARTER", "ORDER", "CONTRACT", "DEBT", "ACQUISITION"]):
            return True, f"Corporate Disclosure / News Catalyst: {item.get('title', '')[:50]}"

    return False, "Consolidating / Normal Volatility"
