import logging
import urllib.parse
from datetime import date
from typing import Dict, Any, List, Optional
from app.config import settings
from app.brokers.base import BaseBrokerAdapter
from app.engine.portfolio_sync import fetch_user_portfolio

logger = logging.getLogger("stokvigil.brokers.icici")


class IciciBrokerAdapter(BaseBrokerAdapter):
    """
    ICICI Direct Breeze Connect Broker Adapter.
    Implements institutional Master App Publisher model:
    - End users connect directly using their official ICICI Direct User ID & OTP.
    - Institutional Master App Key & Secret Key are securely managed server-side.
    """
    broker_id: str = "icici"
    display_name: str = "ICICI Direct"
    is_active: bool = True
    auth_type: str = "session_token"

    def get_login_url(self, redirect_uri: Optional[str] = None) -> str:
        master_key = (settings.ICICI_MASTER_APP_KEY or "").strip()
        if not master_key:
            logger.warning(
                "ICICI_MASTER_APP_KEY is unconfigured on the server. "
                "Login URL will be generated without an api_key parameter."
            )
        encoded_key = urllib.parse.quote(master_key)
        return f"https://api.icicidirect.com/apiuser/login?api_key={encoded_key}"

    def save_credentials(
        self,
        db: Any,
        vault: Any,
        user_id: str,
        session_token: str,
        **kwargs
    ) -> Dict[str, Any]:
        clean_tok = session_token.strip()
        if "apisession=" in clean_tok:
            clean_tok = clean_tok.split("apisession=")[1].split("&")[0]
        clean_tok = urllib.parse.unquote(clean_tok).strip()

        # Pure Master App Publisher Model:
        # Developer keys (ICICI_MASTER_APP_KEY, ICICI_MASTER_SECRET_KEY) reside server-side.
        # The database stores strictly the user's daily encrypted session token.
        encrypted_session_token = vault.encrypt(clean_tok)
        today_str = str(date.today())

        payload = {
            "user_id": user_id,
            "encrypted_app_key": None,
            "encrypted_secret_key": None,
            "encrypted_session_token": encrypted_session_token,
            "token_date": today_str,
            "updated_at": "now()"
        }

        try:
            db.table("user_credentials").upsert(payload, on_conflict="user_id").execute()
        except Exception as e:
            err_str = str(e).lower()
            if "not-null" in err_str or "violates not-null" in err_str:
                logger.warning(
                    f"Legacy NOT NULL constraint detected on user_credentials for user {user_id}. "
                    "Populating encrypted master keys for backward compatibility until migration 20260919 is run."
                )
                app_key = str(settings.ICICI_MASTER_APP_KEY or "").strip()
                secret_key = str(settings.ICICI_MASTER_SECRET_KEY or "").strip()
                payload["encrypted_app_key"] = vault.encrypt(app_key)
                payload["encrypted_secret_key"] = vault.encrypt(secret_key)
                db.table("user_credentials").upsert(payload, on_conflict="user_id").execute()
            else:
                logger.error(f"Error upserting credentials for user {user_id}: {e}")
                db.table("user_credentials").update(payload).eq("user_id", user_id).execute()

        return {
            "status": "success",
            "message": "ICICI Breeze Session Token saved & encrypted successfully.",
            "token_date": today_str,
            "broker": self.broker_id
        }

    def fetch_holdings(self, decrypted_creds: Dict[str, str]) -> List[Dict[str, Any]]:
        # Master App Publisher Model: server-configured master credentials take precedence over stale legacy keys
        app_key = (settings.ICICI_MASTER_APP_KEY or decrypted_creds.get("app_key") or "").strip().strip('"').strip("'")
        secret_key = (settings.ICICI_MASTER_SECRET_KEY or decrypted_creds.get("secret_key") or "").strip().strip('"').strip("'")
        session_token = (decrypted_creds.get("session_token") or "").strip().strip('"').strip("'")

        if not app_key or not secret_key or not session_token:
            logger.warning("Missing ICICI credentials for portfolio fetch.")
            return []

        return fetch_user_portfolio(app_key, secret_key, session_token)

    def place_order(
        self,
        decrypted_creds: Dict[str, str],
        order_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        app_key = (settings.ICICI_MASTER_APP_KEY or decrypted_creds.get("app_key") or "").strip().strip('"').strip("'")
        secret_key = (settings.ICICI_MASTER_SECRET_KEY or decrypted_creds.get("secret_key") or "").strip().strip('"').strip("'")
        session_token = (decrypted_creds.get("session_token") or "").strip().strip('"').strip("'")

        from breeze_connect import BreezeConnect
        breeze = BreezeConnect(api_key=app_key)
        breeze.generate_session(api_secret=secret_key, session_token=session_token)

        order_res = breeze.place_order(
            stock_code=order_params["stock_code"],
            exchange_code=order_params["exchange_code"],
            product=order_params["product"],
            action=order_params["action"],
            order_type=order_params["order_type"],
            stoploss=str(order_params.get("stoploss", "0")),
            quantity=str(order_params["quantity"]),
            price=str(order_params.get("price", "0")),
            validity=order_params.get("validity", "day")
        )

        return order_res

    def start_ticker_stream(
        self,
        decrypted_creds: Dict[str, str],
        symbols: List[str],
        on_tick_callback: Any
    ) -> bool:
        """
        Initializes persistent WebSocket stream via ICICI Breeze Connect (breeze.ws_connect()).
        Binds incoming real-time ticks to on_tick_callback.
        """
        app_key = (settings.ICICI_MASTER_APP_KEY or decrypted_creds.get("app_key") or "").strip().strip('"').strip("'")
        secret_key = (settings.ICICI_MASTER_SECRET_KEY or decrypted_creds.get("secret_key") or "").strip().strip('"').strip("'")
        session_token = (decrypted_creds.get("session_token") or "").strip().strip('"').strip("'")

        if not app_key or not secret_key or not session_token:
            logger.warning("Cannot start ICICI WebSocket stream: Incomplete broker credentials.")
            return False

        try:
            from breeze_connect import BreezeConnect
            breeze = BreezeConnect(api_key=app_key)
            breeze.generate_session(api_secret=secret_key, session_token=session_token)

            if not getattr(breeze, "session_key", None):
                logger.warning("ICICI Breeze session generation failed for WebSocket ticker stream.")
                return False

            breeze.on_ticks = on_tick_callback
            breeze.ws_connect()
            self._breeze_ws = breeze
            self._subscribed_codes = set()
            logger.info("✅ ICICI Breeze WebSocket successfully connected.")

            if symbols:
                self.subscribe_symbols(symbols)
            return True
        except Exception as e:
            logger.error(f"Error starting ICICI Breeze WebSocket ticker stream: {e}")
            self._breeze_ws = None
            return False

    def subscribe_symbols(self, symbols: List[str]) -> bool:
        """
        Subscribes a list of symbols to the active ICICI Breeze WebSocket feed.
        """
        breeze = getattr(self, "_breeze_ws", None)
        if not breeze:
            logger.debug("Cannot subscribe symbols: ICICI Breeze WebSocket is not active.")
            return False

        if not hasattr(self, "_subscribed_codes"):
            self._subscribed_codes = set()

        subscribed_count = 0
        for raw_sym in symbols:
            if not raw_sym:
                continue
            clean_sym = str(raw_sym).replace(".NS", "").replace(".BO", "").strip().upper()
            is_bse = str(raw_sym).endswith(".BO") or (clean_sym.isdigit() and len(clean_sym) == 6)
            exchange = "BSE" if is_bse else "NSE"
            code_key = f"{exchange}:{clean_sym}"

            if code_key in self._subscribed_codes:
                continue

            try:
                breeze.subscribe_feeds(
                    exchange_code=exchange,
                    stock_code=clean_sym,
                    product_type="cash"
                )
                self._subscribed_codes.add(code_key)
                subscribed_count += 1
            except Exception as sub_err:
                logger.warning(f"Error subscribing ICICI Breeze feed for {code_key}: {sub_err}")

        if subscribed_count > 0:
            logger.info(f"Subscribed {subscribed_count} new symbols to ICICI Breeze WebSocket.")
        return True

    def stop_ticker_stream(self) -> None:
        """
        Gracefully disconnects ICICI Breeze WebSocket ticker feed.
        """
        breeze = getattr(self, "_breeze_ws", None)
        if breeze:
            try:
                breeze.ws_disconnect()
                logger.info("ICICI Breeze WebSocket successfully disconnected.")
            except Exception as e:
                logger.debug(f"Note on ICICI Breeze ws_disconnect: {e}")
            finally:
                self._breeze_ws = None
                self._subscribed_codes = set()
