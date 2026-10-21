import math
import threading
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator


class PlaceOrderRequest(BaseModel):
    user_id: str
    symbol: str = Field(..., min_length=1, max_length=20, pattern=r'^[A-Z0-9_\-&]{1,20}$')
    action: str = Field(..., pattern=r'^(BUY|SELL|buy|sell)$')
    order_type: str = Field(..., pattern=r'^(MARKET|LIMIT|market|limit|STOPLOSS_LIMIT|STOPLOSS|SL|SL-L|sl-l|sl|stoploss|SL-M|sl-m|STOPLOSS_MARKET)$')
    quantity: int = Field(..., gt=0, le=100000)
    price: Optional[float] = Field(default=0.0, ge=0.0)
    trigger_price: Optional[float] = Field(default=None, ge=0.0)
    product: Optional[str] = Field(default=None, pattern=r'^(cash|margin|CASH|MARGIN)?$')
    idempotency_key: Optional[str] = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_order_parameters(self):
        ot = self.order_type.upper()
        if ot in ["SL-M", "STOPLOSS_MARKET"] or (ot == "MARKET" and self.trigger_price is not None and float(self.trigger_price) > 0.0):
            raise ValueError(
                "Stop-Loss Market (SL-M) orders are prohibited under SEBI/NSE F&O rules to prevent illiquid flash crashes. "
                "Please place a Stop-Loss Limit (SL-L) order with both price and trigger_price."
            )
        if ot == "LIMIT":
            if self.price is None or float(self.price) <= 0.0:
                raise ValueError("Limit orders strictly require a positive non-zero limit price (price > 0.0).")
        if ot in ["STOPLOSS_LIMIT", "STOPLOSS", "SL", "SL-L"]:
            if self.price is None or float(self.price) <= 0.0:
                raise ValueError("Stop-Loss Limit (SL-L) orders strictly require a positive non-zero limit execution price (price > 0.0).")
            if self.trigger_price is None or float(self.trigger_price) <= 0.0:
                raise ValueError("Stop-Loss Limit (SL-L) orders strictly require a positive non-zero trigger price (stoploss).")
        return self


def get_exchange_tick_size(price: Optional[float], is_fno: bool = False) -> float:
    """
    Returns official NSE/BSE exchange tick size under Circular NSE/CMTR/62326:
    - ₹0.01 (1 paisa) for Cash Market equity securities trading strictly below ₹250.00.
    - ₹0.05 (5 paise) for Cash Market equities trading at or above ₹250.00, and all F&O derivatives.
    """
    if is_fno or price is None or float(price) <= 0:
        return 0.05
    return 0.01 if float(price) < 250.0 else 0.05


def snap_to_exchange_tick(
    price: Optional[float],
    tick_size: float = 0.05,
    dynamic: bool = False,
    is_fno: bool = False
) -> float:
    """
    Snaps order price to Indian exchange standard tick size using financial half-up rounding.
    When dynamic=True, automatically resolves to ₹0.01 for cash stocks < ₹250 and ₹0.05 for >= ₹250.
    Default tick_size=0.05 preserves backwards compatibility for existing callers and fixtures.
    """
    if price is None or float(price) <= 0:
        return 0.0
    p = float(price)
    eff_tick = get_exchange_tick_size(p, is_fno=is_fno) if dynamic else tick_size
    ticks = math.floor(p / eff_tick + 0.5)
    return round(ticks * eff_tick, 2)


# Financial Idempotency Cache for Order Execution
# Scoped Key -> {"status": "in_flight"|"completed", "timestamp": float, "ttl": float, "response": dict, "user_id": str}
_ORDER_IDEMPOTENCY_CACHE: Dict[str, Dict[str, Any]] = {}
_ORDER_IDEMPOTENCY_LOCK = threading.Lock()
_ORDER_IDEMPOTENCY_TTL = 120.0  # 2 minutes TTL for explicit client idempotency keys
_ORDER_AUTO_DEBOUNCE_TTL = 15.0  # 15 seconds TTL for rapid double-tap fingerprint debounce
