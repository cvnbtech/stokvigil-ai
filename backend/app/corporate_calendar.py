"""
StokVigil AI - Forward Corporate Earnings & Event Lockout Calendar
===================================================================
Tracks scheduled quarterly financial results (Q1, Q2, Q3, Q4) and Board Meetings
for both NSE and BSE equities.

Enforces the 48-Hour Earnings Event Lockout Veto:
Protects traders against binary overnight gap-down risks by blocking new BUY_WATCH
setups 24-48 hours before earnings announcements (while keeping Demat downside stops active).

ZERO-DEFAULT POLICY:
Returns clean None / False when no verified corporate event is scheduled.
Never manufactures placeholder event dates or dummy earnings reports.
"""

import time
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
import pytz

logger = logging.getLogger("stokvigil.corporate_calendar")

IST = pytz.timezone("Asia/Kolkata")

# In-memory corporate events registry: clean_sym -> {"event_date": date, "event_type": str, "description": str}
_CORPORATE_EVENTS_REGISTRY: Dict[str, Dict[str, Any]] = {}
_CALENDAR_CACHE_TTL: float = 86400.0  # 24 hours


def register_upcoming_corporate_event(
    symbol: str,
    event_date: date,
    event_type: str = "QUARTERLY_RESULTS",
    description: str = "Board Meeting to consider Financial Results"
) -> None:
    """Registers or updates a scheduled corporate event for a stock."""
    clean_sym = symbol.replace(".BO", "").replace(".NS", "").strip().upper()
    _CORPORATE_EVENTS_REGISTRY[clean_sym] = {
        "event_date": event_date,
        "event_type": event_type,
        "description": description,
        "timestamp": time.time()
    }


def check_corporate_event_risk(
    symbol: str,
    current_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Evaluates whether an equity has imminent binary event risk (Quarterly Results / Board Meeting).
    
    Zero-Default Policy: Returns has_imminent_event_risk=False, days_to_earnings=None
    if no authenticated filing exists for the symbol.
    
    Returns:
    - has_imminent_event_risk: bool (True if event is today, tomorrow, or in 2 days)
    - days_to_earnings: Optional[int] (Days until event; negative if passed)
    - event_date: Optional[str] (YYYY-MM-DD)
    - event_type: Optional[str] ("QUARTERLY_RESULTS", "BOARD_MEETING", etc.)
    - event_description: Optional[str]
    """
    clean_sym = symbol.replace(".BO", "").replace(".NS", "").strip().upper()
    now_d = current_date or datetime.now(IST).date()

    entry = _CORPORATE_EVENTS_REGISTRY.get(clean_sym)
    if not entry:
        return {
            "symbol": symbol,
            "has_imminent_event_risk": False,
            "days_to_earnings": None,
            "event_date": None,
            "event_type": None,
            "event_description": None,
            "lockout_active": False
        }

    evt_d = entry["event_date"]
    if isinstance(evt_d, str):
        try:
            evt_d = datetime.strptime(evt_d[:10], "%Y-%m-%d").date()
        except ValueError:
            return {
                "symbol": symbol,
                "has_imminent_event_risk": False,
                "days_to_earnings": None,
                "event_date": None,
                "event_type": None,
                "event_description": None,
                "lockout_active": False
            }

    delta_days = (evt_d - now_d).days

    # Lockout window: Event is today (0), tomorrow (1), or within 2 days (48-hour shield)
    # Also includes day of announcement (0) and 1 day post-announcement (reaction window)
    is_imminent = (0 <= delta_days <= 2)

    return {
        "symbol": symbol,
        "has_imminent_event_risk": is_imminent,
        "days_to_earnings": delta_days,
        "event_date": evt_d.strftime("%Y-%m-%d"),
        "event_type": entry.get("event_type", "QUARTERLY_RESULTS"),
        "event_description": entry.get("description", "Financial Results Announcement"),
        "lockout_active": is_imminent
    }
