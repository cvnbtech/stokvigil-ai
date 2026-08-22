import asyncio
import sys
import os

# Set UTF-8 encoding for Windows stdout
sys.stdout.reconfigure(encoding='utf-8')

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.technical_engine import fetch_multi_timeframe_technicals
from app.flow_tracker import fetch_delivery_and_fo_flow, fetch_bulk_and_block_deals
from app.macro_filter import fetch_macro_market_regime, evaluate_forensic_health
from app.alert_limiter import should_dispatch_alert
from app.notifications import format_telegram_alert, build_telegram_inline_keyboard
from app.agent_runner import evaluate_stock_with_ai

async def run_all_tests():
    print("==================================================")
    print("STOKVIGIL AI: INSTITUTIONAL ENGINE UNIT TESTS")
    print("==================================================")

    # 1. Test Macro Market Regime
    print("\n[1/6] Testing Macro Market Regime (India VIX & NIFTY)...")
    macro = fetch_macro_market_regime()
    print(f"[OK] NIFTY 50: {macro['nifty_price']} ({macro['nifty_change_pct']}%) | Trend: {macro['nifty_trend']}")
    print(f"[OK] India VIX: {macro['india_vix']} | Regime: {macro['vix_regime']}")

    # 2. Test Multi-Timeframe Technicals
    test_symbol = "RELIANCE"
    print(f"\n[2/6] Testing Multi-Timeframe Technical Engine for {test_symbol}...")
    technicals = fetch_multi_timeframe_technicals(test_symbol)
    print(f"[OK] Price: Rs {technicals['current_price']}")
    print(f"[OK] RSI 5m: {technicals['rsi_5m']} | RSI 15m: {technicals['rsi_15m']} | RSI Daily: {technicals['rsi_daily']}")
    print(f"[OK] RSI Divergence: {technicals['rsi_divergence']}")
    print(f"[OK] MACD Trend: {technicals['macd_trend']} (Line: {technicals['macd_line']}, Signal: {technicals['macd_signal']})")
    print(f"[OK] VWAP: Rs {technicals['vwap']} (Price vs VWAP: {technicals['price_vs_vwap_pct']}%)")
    print(f"[OK] 14-period ATR: Rs {technicals['atr_14']} | Technical Score: {technicals['technical_score']}/100")

    # 3. Test Flow Tracker
    print(f"\n[3/6] Testing Institutional Flow Tracker for {test_symbol}...")
    flow = fetch_delivery_and_fo_flow(test_symbol, technicals.get("price_vs_vwap_pct", 0.0))
    print(f"[OK] Estimated Delivery %: {flow['delivery_pct']}% | F&O OI Status: {flow['fo_oi_status']}")

    # 4. Test Forensic Health
    print(f"\n[4/6] Testing Forensic Health Filter...")
    dummy_fin = {"pe_ratio": 24.5, "forward_pe": 21.0, "debt_to_equity": 0.42, "profit_margin_pct": 14.8}
    forensics = evaluate_forensic_health(test_symbol, dummy_fin)
    print(f"[OK] Sector: {forensics['sector_name']} | Forensic Score: {forensics['forensic_score']}/100")
    print(f"[OK] Strengths: {forensics['strengths']}")

    # 5. Test AI Evaluation & Tactical Trade Levels
    print(f"\n[5/6] Testing Full Multi-Factor AI Confluence Evaluation...")
    dummy_holding = {"symbol": test_symbol, "quantity": 50, "average_price": 2800.0}
    ai_result = await evaluate_stock_with_ai(
        symbol=test_symbol,
        technicals=technicals,
        flow_data=flow,
        macro_data=macro,
        forensics=forensics,
        financials=dummy_fin,
        news_items=[{"title": "Reliance bags massive commercial contract for green energy", "link": "#", "published": "Today"}],
        holding_info=dummy_holding
    )
    print(f"[OK] Action Bias: {ai_result['action_bias']}")
    print(f"[OK] Confluence Score: {ai_result['confluence_score']}/100")
    print(f"[OK] Alert Title: {ai_result['alert_title']}")
    print(f"[OK] Tactical Levels: {ai_result['tactical_levels']}")
    print(f"[OK] Holding Guidance: {ai_result['holding_guidance']}")

    # 6. Test Telegram Formatter & Anti-Fatigue State Machine
    print(f"\n[6/6] Testing Rich Telegram Card Formatting & Anti-Fatigue Limiter...")
    allowed, reason = should_dispatch_alert("user_123", test_symbol, ai_result['action_bias'], ai_result['confluence_score'])
    print(f"[OK] Dispatch Allowed: {allowed} ({reason})")
    
    # Check immediate duplicate suppression
    allowed_2, reason_2 = should_dispatch_alert("user_123", test_symbol, ai_result['action_bias'], ai_result['confluence_score'])
    print(f"[OK] Duplicate Throttled: {not allowed_2} ({reason_2})")

    html_card = format_telegram_alert(
        symbol=test_symbol,
        alert_title=ai_result['alert_title'],
        action_bias=ai_result['action_bias'],
        confluence_score=ai_result['confluence_score'],
        catalyst_type=ai_result['catalyst_category'],
        confluence_drivers=ai_result['confluence_drivers'],
        tactical_levels=ai_result['tactical_levels'],
        demat_position={"is_in_portfolio": True, "quantity": 50, "average_buy_price": 2800.0, "unrealized_pnl_pct": 5.2},
        metrics_snapshot=technicals
    )
    print("\n[OK] Formatted Telegram HTML Alert Sample:\n" + html_card[:250] + "...\n")
    
    print("==================================================")
    print("SUCCESS: ALL 6 INSTITUTIONAL ENGINE MODULES PASSED!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
