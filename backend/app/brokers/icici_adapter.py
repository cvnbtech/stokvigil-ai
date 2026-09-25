import logging
import urllib.parse
from datetime import date
from typing import Dict, Any, List, Optional
from app.config import settings
from app.brokers.base import BaseBrokerAdapter

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

        # Delegate to portfolio parser in app.main (if mocked during tests) or app.agent_runner
        import sys
        main_mod = sys.modules.get("app.main")
        if main_mod and hasattr(main_mod, "fetch_user_portfolio"):
            return main_mod.fetch_user_portfolio(app_key, secret_key, session_token)

        from app.agent_runner import fetch_user_portfolio
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
