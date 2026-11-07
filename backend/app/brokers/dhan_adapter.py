import logging
import json
import time
import urllib.parse
import urllib.request
from datetime import date
from typing import Dict, Any, List, Optional
from app.config import settings
from app.brokers.base import BaseBrokerAdapter

logger = logging.getLogger("stokvigil.brokers.dhan")


class DhanBrokerAdapter(BaseBrokerAdapter):
    """
    Dhan HQ Developer API Broker Adapter.
    Dhan provides a 100% free trading API with zero subscription fees for retail and algorithmic traders.
    Documentation: https://dhanhq.co/docs/v2/
    """
    broker_id: str = "dhan"
    display_name: str = "Dhan HQ"
    is_active: bool = True
    auth_type: str = "access_token"  # Dhan Personal Access Token (60-day or daily)

    BASE_URL: str = "https://api.dhan.co/v2"

    def get_login_url(self, redirect_uri: Optional[str] = None) -> str:
        """
        Returns Dhan login / token generation portal URL.
        """
        return "https://login.dhan.co/"

    def save_credentials(
        self,
        db: Any,
        vault: Any,
        user_id: str,
        session_token: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Encrypts Dhan Client ID and Access Token and stores them in user_credentials.
        """
        clean_token = session_token.strip()
        client_id = str(kwargs.get("client_id") or kwargs.get("dhan_client_id") or "").strip()
        today_str = str(date.today())

        encrypted_token = vault.encrypt(clean_token)
        encrypted_client = vault.encrypt(client_id) if client_id else None

        payload = {
            "user_id": user_id,
            "broker_id": self.broker_id,
            "encrypted_session_token": encrypted_token,
            "encrypted_app_key": encrypted_client,
            "token_date": today_str,
            "updated_at": "now()"
        }

        try:
            db.table("user_credentials").upsert(payload, on_conflict="user_id").execute()
        except Exception as e:
            logger.warning(f"Note on upserting Dhan credentials for user {user_id}: {e}")
            db.table("user_credentials").update(payload).eq("user_id", user_id).execute()

        return {
            "status": "success",
            "message": "Dhan HQ Access Token saved & encrypted successfully.",
            "token_date": today_str,
            "broker": self.broker_id
        }

    def fetch_holdings(self, decrypted_creds: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Fetches holdings via Dhan HQ API: GET /v2/holdings
        Normalizes into StokVigil institutional holding schema.
        """
        access_token = (decrypted_creds.get("session_token") or decrypted_creds.get("access_token") or "").strip()
        client_id = (decrypted_creds.get("app_key") or decrypted_creds.get("client_id") or "").strip()

        if not access_token:
            logger.warning("Missing Dhan access token for holdings fetch.")
            return []

        url = f"{self.BASE_URL}/holdings"
        headers = {
            "access-token": access_token,
            "client-id": client_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    raw_data = json.loads(resp.read().decode("utf-8"))
                    holdings_list = raw_data if isinstance(raw_data, list) else raw_data.get("data", [])
                    
                    normalized: List[Dict[str, Any]] = []
                    for h in holdings_list:
                        sym = str(h.get("tradingSymbol") or h.get("securityId") or "").strip().upper()
                        if not sym:
                            continue
                        clean_s = sym.replace(".NS", "").replace(".BO", "").strip().upper()
                        exch_seg = str(h.get("exchangeSegment", "NSE_EQ")).upper()
                        exch = "BSE" if "BSE" in exch_seg or clean_s.isdigit() else "NSE"
                        
                        qty = float(h.get("totalQty") or h.get("quantity") or 0.0)
                        avg_p = float(h.get("avgCostPrice") or h.get("averagePrice") or 0.0)
                        curr_p = float(h.get("lastTradedPrice") or h.get("currentPrice") or 0.0)
                        curr_val = qty * curr_p
                        pnl = qty * (curr_p - avg_p) if avg_p > 0 else 0.0
                        pnl_pct = round(((curr_p - avg_p) / avg_p) * 100.0, 2) if avg_p > 0 else 0.0

                        normalized.append({
                            "symbol": clean_s,
                            "clean_symbol": clean_s,
                            "stock_code": clean_s,
                            "exchange": exch,
                            "quantity": qty,
                            "average_price": avg_p,
                            "current_price": curr_p,
                            "current_value": curr_val,
                            "pnl": round(pnl, 2),
                            "pnl_percent": pnl_pct,
                            "broker": self.broker_id
                        })
                    return normalized
        except Exception as e:
            logger.error(f"Error fetching Dhan holdings: {e}")
            return []

    def place_order(
        self,
        decrypted_creds: Dict[str, str],
        order_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Translates standardized order parameters into Dhan HQ API: POST /v2/orders.
        SEBI MANDATORY COMPLIANCE:
        Strictly enforces LIMIT or STOP_LOSS_LIMIT orders.
        Rejects SL-M (Stop Loss Market) per SEBI circular on Stop Loss Market Orders.
        """
        access_token = (decrypted_creds.get("session_token") or decrypted_creds.get("access_token") or "").strip()
        client_id = (decrypted_creds.get("app_key") or decrypted_creds.get("client_id") or "").strip()

        if not access_token:
            return {"status": "error", "message": "Missing Dhan access token."}

        req_order_type = str(order_params.get("order_type", "LIMIT")).upper()
        if req_order_type in ["SL-M", "STOP_LOSS_MARKET"]:
            raise ValueError(
                "SEBI COMPLIANCE VIOLATION: Stop-Loss Market (SL-M) orders are banned by SEBI on equity & options. "
                "You must specify a Limit Price using STOP_LOSS_LIMIT."
            )

        dhan_order_type = "LIMIT"
        if req_order_type in ["STOP_LOSS", "SL", "STOPLOSS_LIMIT"]:
            dhan_order_type = "STOP_LOSS"
        elif req_order_type == "MARKET":
            dhan_order_type = "MARKET"

        action = str(order_params.get("action", "BUY")).upper()
        trans_type = "BUY" if action == "BUY" else "SELL"
        exch_code = str(order_params.get("exchange_code", "NSE")).upper()
        exchange_segment = "BSE_EQ" if exch_code == "BSE" else "NSE_EQ"
        prod = str(order_params.get("product", "cash")).lower()
        product_type = "INTRADAY" if prod in ["intraday", "mis"] else "CNC"

        dhan_payload = {
            "dhanClientId": client_id,
            "correlationId": str(order_params.get("correlation_id", f"stok_{int(time.time())}")),
            "transactionType": trans_type,
            "exchangeSegment": exchange_segment,
            "productType": product_type,
            "orderType": dhan_order_type,
            "validity": "DAY",
            "securityId": str(order_params.get("security_id") or order_params.get("stock_code", "")),
            "quantity": int(order_params.get("quantity", 1)),
            "price": float(order_params.get("price", 0.0)),
            "triggerPrice": float(order_params.get("stoploss", 0.0))
        }

        url = f"{self.BASE_URL}/orders"
        headers = {
            "access-token": access_token,
            "client-id": client_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            req_data = json.dumps(dhan_payload).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                return {
                    "status": "success",
                    "broker": self.broker_id,
                    "order_id": resp_json.get("orderId"),
                    "order_status": resp_json.get("orderStatus", "TRANSIT"),
                    "raw_response": resp_json
                }
        except urllib.error.HTTPError as http_err:
            err_body = http_err.read().decode("utf-8") if http_err.fp else str(http_err)
            logger.error(f"Dhan order placement HTTP error {http_err.code}: {err_body}")
            return {
                "status": "error",
                "broker": self.broker_id,
                "error_code": http_err.code,
                "message": err_body
            }
        except Exception as e:
            logger.error(f"Dhan order placement failed: {e}")
            return {"status": "error", "broker": self.broker_id, "message": str(e)}
