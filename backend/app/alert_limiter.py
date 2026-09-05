import time
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("stokvigil.alert_limiter")

# In-memory alert state cache: (user_id, symbol) -> (last_alert_timestamp, last_action_bias, last_impact_score)
_ALERT_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}

# Default Cooldown: 45 minutes (2700 seconds)
DEFAULT_COOLDOWN_SECONDS = 2700

def should_dispatch_alert(
    user_id: str,
    symbol: str,
    action_bias: str,
    impact_score: int,
    is_tier1_catalyst: bool = False
) -> Tuple[bool, str]:
    """
    Evaluates anti-fatigue state machine:
    - Allows immediate dispatch if Tier-1 catalyst (e.g. Trailing SL hit, sudden crash, massive deal).
    - Otherwise suppresses repeated alerts for the same symbol within 45 minutes.
    - Allows alert if action_bias flipped (e.g. from BUY_WATCH to SELL_WATCH).
    """
    now = time.time()
    key = (user_id, symbol)
    
    cached = _ALERT_CACHE.get(key)
    if not cached:
        # First alert for this symbol
        _ALERT_CACHE[key] = {
            "timestamp": now,
            "action_bias": action_bias,
            "impact_score": impact_score
        }
        return True, "Initial alert dispatched."
        
    elapsed = now - cached["timestamp"]
    last_bias = cached["action_bias"]
    
    # 1. Tier 1 Catalyst bypasses cooldown (Trailing SL hit, Block deal, or Score >= 88)
    if is_tier1_catalyst or action_bias == "TRAILING_SL_ALERT" or impact_score >= 88:
        _ALERT_CACHE[key] = {
            "timestamp": now,
            "action_bias": action_bias,
            "impact_score": impact_score
        }
        return True, "Tier-1 high urgency alert bypassed cooldown."
        
    # 2. Bias Flip (e.g. BUY -> SELL) bypasses cooldown
    if action_bias != last_bias and action_bias != "HOLD_NEUTRAL":
        _ALERT_CACHE[key] = {
            "timestamp": now,
            "action_bias": action_bias,
            "impact_score": impact_score
        }
        return True, f"Action bias changed from {last_bias} to {action_bias}."
        
    # 3. Cooldown check
    if elapsed < DEFAULT_COOLDOWN_SECONDS:
        remaining_mins = int((DEFAULT_COOLDOWN_SECONDS - elapsed) / 60)
        logger.info(f"Alert throttled for {symbol} (User {user_id[:8]}). Cooldown remaining: {remaining_mins}m")
        return False, f"Throttled: {remaining_mins}m remaining in symbol cooldown."
        
    # Cooldown expired, update cache
    _ALERT_CACHE[key] = {
        "timestamp": now,
        "action_bias": action_bias,
        "impact_score": impact_score
    }
    return True, "Cooldown expired, fresh alert permitted."
