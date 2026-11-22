"""
StokVigil AI - Institutional NSE Derivatives & Open Interest (OI) Engine
========================================================================
Parses and evaluates underlying Futures Open Interest (OI) dynamics for NSE F&O equities.
Implements institutional 4-quadrant Price-OI accumulation vs distribution classification:
1. LONG_BUILDUP (Price ↑ + OI ↑): High institutional accumulation conviction (+10 pts)
2. SHORT_COVERING (Price ↑ + OI ↓): Fragile short squeeze; recommend tight trailing stops (+3 pts)
3. SHORT_BUILDUP (Price ↓ + OI ↑): Heavy institutional short creation; strict BUY veto (-12 pts)
4. LONG_UNWINDING (Price ↓ + OI ↓): Stop-loss liquidations; triggers Demat capital protection (-10 pts)

Zero-Default Guarantee:
Non-F&O cash equities or scrips with missing OI feeds return None/Neutral safely without penalty.
"""

import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("stokvigil.derivatives_tracker")

# In-memory registry for live and mock F&O open interest data
# symbol -> {"price_change_pct": float, "oi_change_pct": float, "timestamp": float}
_DERIVATIVES_OI_CACHE: Dict[str, Dict[str, Any]] = {}
_OI_CACHE_TTL: float = 300.0  # 5 minutes cache TTL


def normalize_fno_symbol(symbol: str) -> str:
    """Normalizes symbol to bare uppercase equity root (e.g. 'RELIANCE.NS' -> 'RELIANCE')."""
    clean = (symbol or "").strip().upper()
    return clean.replace(".NS", "").replace(".BO", "").strip()


def register_scrip_oi(
    symbol: str,
    price_change_pct: float,
    oi_change_pct: float,
    current_oi: Optional[int] = None
) -> None:
    """
    Registers real-time or verified exchange feed Open Interest updates for a scrip.
    Used by WebSocket feeds, NSE F&O batch scrapers, and test runners.
    """
    bare = normalize_fno_symbol(symbol)
    _DERIVATIVES_OI_CACHE[bare] = {
        "price_change_pct": round(float(price_change_pct), 2),
        "oi_change_pct": round(float(oi_change_pct), 2),
        "current_oi": current_oi,
        "timestamp": time.time()
    }


def clear_oi_cache() -> None:
    """Clears the derivatives in-memory cache (primarily for test resets)."""
    global _DERIVATIVES_OI_CACHE
    _DERIVATIVES_OI_CACHE.clear()


def classify_oi_buildup(
    price_change_pct: Optional[float],
    oi_change_pct: Optional[float]
) -> Dict[str, Any]:
    """
    Classifies underlying institutional positioning using the Price + Open Interest matrix.
    
    Returns structured payload with regime, conviction score, and trading desk guidance.
    """
    default_res = {
        "oi_regime": "NEUTRAL",
        "conviction_score": 0,
        "price_change_pct": price_change_pct,
        "oi_change_pct": oi_change_pct,
        "description": "Neutral or insufficient Open Interest shift."
    }

    if price_change_pct is None or oi_change_pct is None:
        return default_res

    p_chg = float(price_change_pct)
    oi_chg = float(oi_change_pct)

    # Thresholds: significant price move >= 0.25%, significant OI shift >= 1.5%
    if p_chg >= 0.25 and oi_chg >= 1.5:
        return {
            "oi_regime": "LONG_BUILDUP",
            "conviction_score": 10,
            "price_change_pct": p_chg,
            "oi_change_pct": oi_chg,
            "description": f"Institutional Long Build-up: Price gained {p_chg:+.2f}% with {oi_chg:+.2f}% fresh Open Interest expansion."
        }
    elif p_chg >= 0.25 and oi_chg <= -1.5:
        return {
            "oi_regime": "SHORT_COVERING",
            "conviction_score": 3,
            "price_change_pct": p_chg,
            "oi_change_pct": oi_chg,
            "description": f"Short Covering Squeeze: Price popped {p_chg:+.2f}% on {oi_chg:+.2f}% OI liquidation. Move is vulnerable to reversal."
        }
    elif p_chg <= -0.25 and oi_chg >= 1.5:
        return {
            "oi_regime": "SHORT_BUILDUP",
            "conviction_score": -12,
            "price_change_pct": p_chg,
            "oi_change_pct": oi_chg,
            "description": f"Institutional Short Build-up: Aggressive supply shock with {oi_chg:+.2f}% open interest dumping price by {p_chg:+.2f}%."
        }
    elif p_chg <= -0.25 and oi_chg <= -1.5:
        return {
            "oi_regime": "LONG_UNWINDING",
            "conviction_score": -10,
            "price_change_pct": p_chg,
            "oi_change_pct": oi_chg,
            "description": f"Long Unwinding Panic: Trapped buyers dumping positions ({oi_chg:+.2f}% OI drop). Protect Demat capital."
        }

    return default_res


def evaluate_derivatives_microstructure(symbol: str) -> Dict[str, Any]:
    """
    Evaluates NSE derivatives open interest for a scrip.
    
    Zero-Default Policy:
    If a scrip is non-F&O cash-only or no verified OI feed exists,
    returns is_fno_eligible=False and oi_regime=None without penalties.
    """
    bare = normalize_fno_symbol(symbol)
    entry = _DERIVATIVES_OI_CACHE.get(bare)
    now = time.time()

    if not entry or (now - entry.get("timestamp", 0)) > _OI_CACHE_TTL:
        return {
            "symbol": symbol,
            "is_fno_eligible": False,
            "oi_regime": None,
            "oi_change_pct": None,
            "conviction_score": 0,
            "description": "Non-F&O equity or active derivatives feed unavailable."
        }

    classification = classify_oi_buildup(
        price_change_pct=entry.get("price_change_pct"),
        oi_change_pct=entry.get("oi_change_pct")
    )

    return {
        "symbol": symbol,
        "is_fno_eligible": True,
        "oi_regime": classification["oi_regime"],
        "oi_change_pct": classification["oi_change_pct"],
        "conviction_score": classification["conviction_score"],
        "description": classification["description"]
    }
