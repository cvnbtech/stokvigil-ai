from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import date


class BaseBrokerAdapter(ABC):
    """
    Abstract Base Class for Broker Integrations.
    Follows the Strategy/Adapter pattern to allow seamless addition of future brokers
    (e.g., Zerodha Kite, Angel One SmartAPI, Upstox, Groww, HSBC InvestDirect)
    without modifying core trading logic, models, or database schemas.
    """
    broker_id: str
    display_name: str
    is_active: bool = True
    auth_type: str = "session_token"  # "session_token", "oauth_redirect", "totp"

    @abstractmethod
    def get_login_url(self, redirect_uri: Optional[str] = None) -> str:
        """
        Returns the official broker login URL configured with institutional Master API Keys.
        Retail customers log in directly via their regular credentials (User ID + Password + OTP).
        """
        pass

    @abstractmethod
    def save_credentials(
        self,
        db: Any,
        vault: Any,
        user_id: str,
        session_token: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Securely encrypts credentials and stores them in the Supabase vault.
        """
        pass

    @abstractmethod
    def fetch_holdings(self, decrypted_creds: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Fetches holdings from the broker and normalizes them into StokVigil's internal format:
        [
            {
                "symbol": "TCS",
                "stock_code": "TCS",
                "quantity": 10,
                "average_price": 3800.0
            }
        ]
        """
        pass

    @abstractmethod
    def place_order(
        self,
        decrypted_creds: Dict[str, str],
        order_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Translates standardized order parameters into the broker-specific API/SDK call.
        """
        pass

    def validate_session(self, token_date: str) -> bool:
        """
        Validates if the session token is active for today per SEBI daily expiration rules.
        """
        return str(token_date).strip() == str(date.today())
