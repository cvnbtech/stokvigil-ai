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


def snap_to_exchange_tick(price: Optional[float], tick_size: float = 0.05) -> float:
    """
    Snaps order price to Indian exchange standard ₹0.05 tick size using standard half-up rounding.
    NSE/BSE equity orders with invalid sub-tick fractions are rejected by exchange matching engines.
    """
    if price is None or price <= 0:
        return 0.0
    ticks = math.floor(float(price) / tick_size + 0.5)
    return round(ticks * tick_size, 2)


# Financial Idempotency Cache for Order Execution
# Scoped Key -> {"status": "in_flight"|"completed", "timestamp": float, "ttl": float, "response": dict, "user_id": str}
_ORDER_IDEMPOTENCY_CACHE: Dict[str, Dict[str, Any]] = {}
_ORDER_IDEMPOTENCY_LOCK = threading.Lock()
_ORDER_IDEMPOTENCY_TTL = 120.0  # 2 minutes TTL for explicit client idempotency keys
_ORDER_AUTO_DEBOUNCE_TTL = 15.0  # 15 seconds TTL for rapid double-tap fingerprint debounce
