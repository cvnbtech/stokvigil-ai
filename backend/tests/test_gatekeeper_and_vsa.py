import unittest
import sys
import os

# Set UTF-8 encoding for Windows stdout
sys.stdout.reconfigure(encoding='utf-8')

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agent_runner import check_has_active_catalyst, compute_deterministic_confluence
from app.flow_tracker import fetch_delivery_and_fo_flow
from app.notifications import build_telegram_inline_keyboard

class TestGatekeeperAndVSA(unittest.TestCase):

    def test_01_flat_stock_filtered_by_gatekeeper(self):
        """Flat, consolidating stock without any catalyst should return False (0 LLM calls)."""
        technicals = {
            "current_price": 1000.0,
            "rsi_15m": 52.0,
            "rsi_5m": 50.0,
            "rsi_divergence": "NONE",
            "volume_surge_ratio": 0.8,  # Below 1.5x threshold
            "macd_trend": "BULLISH_CONTINUATION",
            "vwap": 998.0,
            "price_vs_vwap_pct": 0.2,  # Close to VWAP
            "atr_14": 15.0
        }
        flow_data = {
            "delivery_pct": 40.0,
            "vsa_regime": "NEUTRAL_FLOW"
        }
        has_catalyst, reason = check_has_active_catalyst(
            symbol="INFY",
            technicals=technicals,
            flow_data=flow_data,
            news_items=[],
            holding_info=None
        )
        self.assertFalse(has_catalyst, f"Expected False for flat stock, got True with reason: {reason}")
        self.assertIn("Consolidating", reason)

    def test_02_volume_surge_triggers_catalyst(self):
        """Volume surge >= 1.5x should activate Gemini Tier-2 evaluation."""
        technicals = {
            "current_price": 1000.0,
            "rsi_15m": 55.0,
            "rsi_5m": 58.0,
            "rsi_divergence": "NONE",
            "volume_surge_ratio": 2.3,  # 2.3x volume surge
            "macd_trend": "BULLISH_CONTINUATION",
            "vwap": 1000.0,
            "price_vs_vwap_pct": 0.0,
            "atr_14": 15.0
        }
        flow_data = {"delivery_pct": 52.0, "vsa_regime": "SMART_MONEY_ABSORPTION"}
        has_catalyst, reason = check_has_active_catalyst(
            symbol="TATASTEEL",
            technicals=technicals,
            flow_data=flow_data,
            news_items=[],
            holding_info=None
        )
        self.assertTrue(has_catalyst)
        self.assertIn("Volume Surge", reason)

    def test_03_demat_sl_threat_triggers_immediate_catalyst(self):
        """Portfolio holding trading near or below Demat cost basis must trigger immediately."""
        technicals = {
            "current_price": 940.0,
            "rsi_15m": 38.0,
            "rsi_5m": 36.0,
            "rsi_divergence": "NONE",
            "volume_surge_ratio": 0.9,
            "macd_trend": "BEARISH_CONTINUATION",
            "vwap": 950.0,
            "price_vs_vwap_pct": -1.05,
            "atr_14": 12.0
        }
        flow_data = {"delivery_pct": 35.0, "vsa_regime": "DISTRIBUTION"}
        holding_info = {
            "symbol": "HDFCBANK",
            "quantity": 100,
            "average_price": 1000.0  # Currently down 6% (Demat SL risk)
        }
        has_catalyst, reason = check_has_active_catalyst(
            symbol="HDFCBANK",
            technicals=technicals,
            flow_data=flow_data,
            news_items=[],
            holding_info=holding_info
        )
        self.assertTrue(has_catalyst)
        self.assertIn("Demat Holding", reason)

    def test_04_wyckoff_vsa_absorption_confluence(self):
        """High delivery + positive price action should award Smart Money Absorption score."""
        flow = fetch_delivery_and_fo_flow("ITC", price_change_pct=1.2)
        # Verify VSA regime is assigned
        self.assertIn("vsa_regime", flow)
        self.assertIn("vsa_note", flow)

    def test_05_deterministic_confluence_math(self):
        """Quiet stock evaluates deterministically with 0 API calls in sub-millisecond time."""
        technicals = {
            "current_price": 2500.0,
            "technical_score": 60,
            "rsi_15m": 52.0,
            "volume_surge_ratio": 0.9,
            "vwap": 2490.0,
            "atr_14": 25.0
        }
        flow_data = {
            "delivery_pct": 60.0,
            "vsa_regime": "SMART_MONEY_ABSORPTION"
        }
        macro_data = {"sector_trend": "BULLISH_EXPANSION"}
        forensics = {"forensic_score": 75}
        
        result = compute_deterministic_confluence(
            symbol="TCS",
            technicals=technicals,
            flow_data=flow_data,
            macro_data=macro_data,
            forensics=forensics,
            financials={},
            news_items=[],
            holding_info=None
        )
        self.assertIn("confluence_score", result)
        self.assertIn("action_bias", result)
        self.assertIn("tactical_levels", result)
        self.assertIn("risk_reward_ratio", result["tactical_levels"])
        self.assertEqual(result["tactical_levels"]["risk_reward_ratio"], "1:2.5")

    def test_06_telegram_inline_keyboard_urls(self):
        """Telegram inline keyboard should contain TradingView and ICICI Direct links."""
        kb = build_telegram_inline_keyboard("RELIANCE.NS")
        self.assertIn("inline_keyboard", kb)
        buttons = kb["inline_keyboard"]
        flat_buttons = [btn for row in buttons for btn in row]
        button_texts = [b["text"] for b in flat_buttons]
        
        self.assertTrue(any("TradingView" in t for t in button_texts))
        self.assertTrue(any("ICICI Direct" in t for t in button_texts))
        self.assertTrue(any("NSE India" in t for t in button_texts))
        
        # Verify TradingView clean symbol link
        tv_btn = next(b for b in flat_buttons if "TradingView" in b["text"])
        self.assertIn("NSE:RELIANCE", tv_btn["url"])

    def test_07_bse_stock_telegram_and_exchange_routing(self):
        """BSE stocks (.BO) should correctly route to BSE TradingView charts and BSE India links."""
        from app.notifications import format_telegram_alert
        
        bse_symbol = "500325.BO"
        kb = build_telegram_inline_keyboard(bse_symbol)
        buttons = [btn for row in kb["inline_keyboard"] for btn in row]
        button_texts = [b["text"] for b in buttons]
        
        # Must have BSE India Live button
        self.assertTrue(any("BSE India" in t for t in button_texts))
        bse_live = next(b for b in buttons if "BSE India" in b["text"])
        self.assertIn("bseindia.com", bse_live["url"])
        
        # TradingView link should point to BSE
        tv_btn = next(b for b in buttons if "TradingView" in b["text"])
        self.assertIn("BSE:500325", tv_btn["url"])
        
        # Formatted card should state (BSE)
        card = format_telegram_alert(
            symbol=bse_symbol,
            alert_title="BSE Stock Alert",
            action_bias="ACCUMULATE",
            confluence_score=80,
            catalyst_type="VOLUME_SURGE",
            confluence_drivers=["BSE volume breakout"]
        )
        self.assertIn("(BSE)", card)

    def test_08_adx_trend_filter(self):
        """14-period ADX should differentiate strong trend from choppy sideways market."""
        from app.technical_engine import calculate_adx
        import pandas as pd
        import numpy as np

        # Create trending dataframe (consistently higher highs and closes)
        dates = pd.date_range("2026-09-01", periods=30, freq="15min")
        trending_df = pd.DataFrame({
            "High": [100 + (i * 2.5) for i in range(30)],
            "Low": [98 + (i * 2.5) for i in range(30)],
            "Close": [99 + (i * 2.5) for i in range(30)],
            "Volume": [1000] * 30
        }, index=dates)

        adx_res = calculate_adx(trending_df, 14)
        self.assertIn("adx_14", adx_res)
        self.assertIn("adx_regime", adx_res)
        self.assertEqual(adx_res["adx_regime"], "STRONG_TREND")
        self.assertGreaterEqual(adx_res["adx_14"], 25.0)

        # Create flat/choppy dataframe (oscillating within tight band)
        choppy_df = pd.DataFrame({
            "High": [100.5 if i % 2 == 0 else 100.2 for i in range(30)],
            "Low": [99.5 if i % 2 == 0 else 99.8 for i in range(30)],
            "Close": [100.0 for _ in range(30)],
            "Volume": [1000] * 30
        }, index=dates)

        choppy_res = calculate_adx(choppy_df, 14)
        self.assertEqual(choppy_res["adx_regime"], "CHOPPY_SIDEWAYS")
        self.assertLess(choppy_res["adx_14"], 20.0)

    def test_09_camarilla_pivots_math(self):
        """Camarilla equation pivots must satisfy H4 > H3 > L3 > L4 institutional structure."""
        from app.technical_engine import calculate_camarilla_pivots
        import pandas as pd

        daily_df = pd.DataFrame({
            "High": [2500.0, 2520.0],
            "Low": [2450.0, 2480.0],
            "Close": [2480.0, 2510.0]
        })
        pivots = calculate_camarilla_pivots(daily_df)
        self.assertIn("h4", pivots)
        self.assertIn("h3", pivots)
        self.assertIn("l3", pivots)
        self.assertIn("l4", pivots)

        # Mathematical hierarchy check
        self.assertGreater(pivots["h4"], pivots["h3"])
        self.assertGreater(pivots["h3"], pivots["l3"])
        self.assertGreater(pivots["l3"], pivots["l4"])

    def test_10_relative_strength_vs_nifty(self):
        """Relative Strength should award leaders and penalize laggards against NIFTY 50."""
        from app.technical_engine import calculate_relative_strength
        import pandas as pd

        # Outperforming stock (+15% over 20 days vs NIFTY +1%)
        leader_df = pd.DataFrame({
            "Close": [100.0] + [100.0 + (i * 0.75) for i in range(1, 25)]
        })
        leader_res = calculate_relative_strength(leader_df, nifty_20d_ret=1.0)
        self.assertEqual(leader_res["rs_regime"], "OUTPERFORMING_LEADER")
        self.assertGreaterEqual(leader_res["rs_rating"], 3.0)

        # Underperforming laggard (-10% over 20 days vs NIFTY +1%)
        laggard_df = pd.DataFrame({
            "Close": [100.0] + [100.0 - (i * 0.5) for i in range(1, 25)]
        })
        laggard_res = calculate_relative_strength(laggard_df, nifty_20d_ret=1.0)
        self.assertEqual(laggard_res["rs_regime"], "UNDERPERFORMING_LAGGARD")
        self.assertLessEqual(laggard_res["rs_rating"], -3.0)

    def test_11_triple_timeframe_confluence(self):
        """Triple-Timeframe harmony should boost confluence score; conflict should penalize."""
        technicals_aligned = {
            "current_price": 1000.0,
            "technical_score": 70,
            "rsi_15m": 58.0,
            "rsi_daily": 56.0,
            "ema_50": 950.0,
            "ema_200": 900.0,
            "ma_trend": "STRONG_BULLISH_ALIGNMENT",
            "vwap": 995.0,
            "price_vs_vwap_pct": 0.5,
            "is_volume_surge": True,
            "volume_multiple": 2.1,
            "macd_trend": "BULLISH_CROSSOVER",
            "atr_14": 15.0,
            "adx_regime": "STRONG_TREND",
            "adx_14": 28.0,
            "rs_regime": "OUTPERFORMING_LEADER",
            "rs_rating": 4.5,
            "camarilla_pivots": {"h4": 1030.0, "h3": 1015.0, "l3": 985.0, "l4": 970.0}
        }
        res = compute_deterministic_confluence(
            symbol="SBIN",
            technicals=technicals_aligned,
            flow_data={"delivery_pct": 60.0, "vsa_regime": "SMART_MONEY_ABSORPTION", "is_high_delivery": True},
            macro_data={"nifty_trend": "BULLISH", "allow_breakout_trades": True},
            forensics={"forensic_score": 80, "sector_name": "NIFTY BANK"},
            financials={},
            news_items=[],
            holding_info=None
        )
        self.assertEqual(res["action_bias"], "BUY_WATCH")
        self.assertGreaterEqual(res["confluence_score"], 75)
        self.assertTrue(any("Triple-Timeframe" in d for d in res["confluence_drivers"]))

    def test_12_chandelier_trailing_stop_loss(self):
        """Demat holding should dynamically ratchet stop-loss to lock in profit."""
        technicals = {
            "current_price": 1200.0,
            "technical_score": 60,
            "rsi_15m": 55.0,
            "rsi_daily": 52.0,
            "ema_50": 1100.0,
            "ema_200": 1000.0,
            "atr_14": 15.0,
            "vwap": 1195.0,
            "adx_regime": "STRONG_TREND",
            "adx_14": 26.0,
            "camarilla_pivots": {"h4": 1220.0, "h3": 1210.0, "l3": 1190.0, "l4": 1180.0}
        }
        holding_info = {
            "symbol": "TCS",
            "quantity": 25,
            "average_price": 1000.0  # Bought at 1000, now at 1200 (+20% gain)
        }
        res = compute_deterministic_confluence(
            symbol="TCS",
            technicals=technicals,
            flow_data={"delivery_pct": 50.0},
            macro_data={"allow_breakout_trades": True},
            forensics={"forensic_score": 80},
            financials={},
            news_items=[],
            holding_info=holding_info
        )
        tactical = res["tactical_levels"]
        # Stop loss should have ratcheted up past 1000 to protect profit (e.g. ~1162.50)
        sl_str = tactical["protective_stop_loss"].replace("₹", "").replace(",", "").strip()
        sl_val = float(sl_str)
        self.assertGreater(sl_val, 1100.0, "Chandelier trailing stop failed to ratchet upward to lock in profits!")
        self.assertIn("Chandelier Trailing SL", res["holding_guidance"])

if __name__ == "__main__":
    unittest.main()
