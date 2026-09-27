import re
from typing import Optional
from pydantic import BaseModel, Field

class BacktestRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=25)
    period: Optional[str] = "1y"
    interval: Optional[str] = "1d"
    strategy: Optional[str] = "camarilla_breakout"
    capital: Optional[float] = 200000.0
    risk_budget: Optional[float] = 2000.0
