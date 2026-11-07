import logging
import json
import time
import urllib.parse
import urllib.request
from datetime import date
from typing import Dict, Any, List, Optional
from app.config import settings
from app.brokers.base import BaseBrokerAdapter

logger = logging.getLogger("stokvigil.brokers.angelone")


class AngelBrokerAdapter(BaseBrokerAdapter):
    """
    Angel One SmartAPI Broker Adapter.
    Angel One provides a 100% free SmartAPI for retail investors with TOTP-based authentication.
    Documentation: https://smartapi.angelbroking.com/docs
    """
    broker_id: str = "angelone"
    display_name: str = "Angel One"
    is_active: bool = True
    auth_type: str = "totp"  # Client Code + Password/MPIN + TOTP

    BASE_URL: str = "https://apiconnect.angelbroking.com"

    def get_login_url(self, redirect_uri: Optional[str] = None) -> str:
        """
        Returns Angel One SmartAPI publisher login URL.
        """
        return "https://smartapi.angelbroking.com/publisher-login"

    def save_credentials(
        self,
        db: Any,
        vault: Any,
        user_id: str,
        session_token: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Encrypts Angel One JWT / Session Token, Client Code, and API Key in user_credentials.
        """
        clean_token = session_token.strip()
        client_code = str(kwargs.get("client_code") or kwargs.get("client_id") or "").strip()
        api_key = str(kwargs.get("api_key") or "").strip()
        today_str = str(date.today())

        encrypted_token = vault.encrypt(clean_token)
        encrypted_client = vault.encrypt(client_code) if client_code else None
        encrypted_key = vault.encrypt(api_key) if api_key else None

        payload = {
            "user_id": user_id,
            "broker_id": self.broker_id,
            "encrypted_session_token": encrypted_token,
            "encrypted_app_key": encrypted_client or encrypted_key,
            "token_date": today_str,
            "updated_at": "now()"
        }

        try:
            db.table("user_credentials").upsert(payload, on_conflict="user_id").execute()
        except Exception as e:
            logger.warning(f"Note on upserting Angel One credentials for user {user_id}: {e}")
            db.table("user_credentials").update(payload).eq("user_id", user_id).execute()

        return {
            "status": "success",
            "message": "Angel One SmartAPI Token saved & encrypted successfully.",
            "token_date": today_str,
            "broker": self.broker_id
        }

    def fetch_holdings(self, decrypted_creds: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Fetches holdings via Angel One SmartAPI:
        GET /rest/secure/angelbroking/portfolio/v1/getAllHolding
        Normalizes into StokVigil institutional holding schema.
        """
        jwt_token = (decrypted_creds.get("session_token") or decrypted_creds.get("jwt_token") or "").strip()
        api_key = (decrypted_creds.get("api_key") or decrypted_creds.get("app_key") or "").strip()

        if not jwt_token:
            logger.warning("Missing Angel One JWT token for holdings fetch.")
            return []

        url = f"{self.BASE_URL}/rest/secure/angelbroking/portfolio/v1/getAllHolding"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "MAC",
            "X-PrivateKey": api_key or "smartapi_default"
        }

        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    raw_data = json.loads(resp.read().decode("utf-8"))
                    holdings_list = []
                    if isinstance(raw_data, dict):
                        data_field = raw_data.get("data")
                        if isinstance(data_field, dict):
                            holdings_list = data_field.get("holdings", [])
                        elif isinstance(data_field, list):
                            holdings_list = data_field
                    elif isinstance(raw_data, list):
                        holdings_list = raw_data

                    normalized: List[Dict[str, Any]] = []
                    for h in holdings_list:
                        sym = str(h.get("tradingsymbol") or h.get("symbolname") or "").strip().upper()
                        if not sym:
                            continue
                        clean_s = sym.replace("-EQ", "").replace(".NS", "").replace(".BO", "").strip().upper()
                        exch = str(h.get("exchange", "NSE")).upper()
                        if "BSE" in exch or clean_s.isdigit():
                            exch = "BSE"
                        else:
                            exch = "NSE"

                        qty = float(h.get("totalholdingqty") or h.get("quantity") or 0.0)
                        avg_p = float(h.get("averageprice") or h.get("avgprice") or 0.0)
                        curr_p = float(h.get("ltp") or h.get("close") or 0.0)
                        curr_val = qty * curr_p
                        pnl = qty * (curr_p - avg_p) if avg_p > 0 else float(h.get("profitandloss", 0.0))
                        pnl_pct = round(((curr_p - avg_p) / avg_p) * 100.0, 2) if avg_p > 0 else float(h.get("pnlpercentage", 0.0))

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
            logger.error(f"Error fetching Angel One holdings: {e}")
            return []

    def place_order(
        self,
        decrypted_creds: Dict[str, str],
        order_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Translates standardized order parameters into Angel One SmartAPI:
        POST /rest/secure/angelbroking/order/v1/placeOrder.
        SEBI MANDATORY COMPLIANCE:
        Strictly enforces LIMIT or STOPLOSS_LIMIT orders.
        Rejects SL-M / STOPLOSS_MARKET per SEBI ban.
        """
        jwt_token = (decrypted_creds.get("session_token") or decrypted_creds.get("jwt_token") or "").strip()
        api_key = (decrypted_creds.get("api_key") or decrypted_creds.get("app_key") or "").strip()

        if not jwt_token:
            return {"status": "error", "message": "Missing Angel One JWT token."}

        req_order_type = str(order_params.get("order_type", "LIMIT")).upper()
        if req_order_type in ["SL-M", "STOP_LOSS_MARKET", "STOPLOSS_MARKET"]:
            raise ValueError(
                "SEBI COMPLIANCE VIOLATION: Stop-Loss Market (SL-M) orders are banned by SEBI on equity & options. "
                "You must specify a Limit Price using STOPLOSS_LIMIT."
            )

        angel_order_type = "LIMIT"
        if req_order_type in ["STOP_LOSS", "SL", "STOPLOSS_LIMIT"]:
            angel_order_type = "STOPLOSS_LIMIT"
        elif req_order_type == "MARKET":
            angel_order_type = "MARKET"

        action = str(order_params.get("action", "BUY")).upper()
        trans_type = "BUY" if action == "BUY" else "SELL"
        exch_code = str(order_params.get("exchange_code", "NSE")).upper()
        prod = str(order_params.get("product", "cash")).lower()
        product_type = "INTRADAY" if prod in ["intraday", "mis"] else "DELIVERY"

        angel_payload = {
            "variety": "NORMAL",
            "tradingsymbol": str(order_params.get("stock_code", "")),
            "symboltoken": str(order_params.get("symbol_token", "")),
            "transactiontype": trans_type,
            "exchange": exch_code,
            "ordertype": angel_order_type,
            "producttype": product_type,
            "duration": "DAY",
            "price": str(order_params.get("price", "0")),
            "triggerprice": str(order_params.get("stoploss", "0")),
            "quantity": str(int(order_params.get("quantity", 1)))
        }

        url = f"{self.BASE_URL}/rest/secure/angelbroking/order/v1/placeOrder"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "MAC",
            "X-PrivateKey": api_key or "smartapi_default"
        }

        try:
            req_data = json.dumps(angel_payload).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                return {
                    "status": "success" if resp_json.get("status") else "error",
                    "broker": self.broker_id,
                    "order_id": resp_json.get("data", {}).get("orderid"),
                    "message": resp_json.get("message", "Order submitted"),
                    "raw_response": resp_json
                }
        except urllib.error.HTTPError as http_err:
            err_body = http_err.read().decode("utf-8") if http_err.fp else str(http_err)
            logger.error(f"Angel One order placement HTTP error {http_err.code}: {err_body}")
            return {
                "status": "error",
                "broker": self.broker_id,
                "error_code": http_err.code,
                "message": err_body
            }
        except Exception as e:
            logger.error(f"Angel One order placement failed: {e}")
            return {"status": "error", "broker": self.broker_id, "message": str(e)}
