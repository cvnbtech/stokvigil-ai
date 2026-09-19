import logging
from typing import Dict, Any, List, Optional
from app.brokers.base import BaseBrokerAdapter
from app.brokers.icici_adapter import IciciBrokerAdapter

logger = logging.getLogger("stokvigil.brokers.registry")


class BrokerRegistry:
    """
    Central Registry for Broker Adapters.
    Provides dynamic broker discovery and instantiation.
    Adding a new broker (Zerodha, Angel One, Upstox, Groww) in the future requires:
    1. Creating NewBrokerAdapter(BaseBrokerAdapter)
    2. Registering it here with register_broker(NewBrokerAdapter())
    """
    def __init__(self):
        self._adapters: Dict[str, BaseBrokerAdapter] = {}
        # Pre-register default active adapters
        self.register_broker(IciciBrokerAdapter())

    def register_broker(self, adapter: BaseBrokerAdapter) -> None:
        self._adapters[adapter.broker_id.lower()] = adapter
        logger.info(f"Registered broker adapter: '{adapter.broker_id}' ({adapter.display_name})")

    def get_broker(self, broker_id: Optional[str] = "icici") -> BaseBrokerAdapter:
        clean_id = str(broker_id or "icici").lower().strip()
        if clean_id in self._adapters:
            return self._adapters[clean_id]
        logger.warning(f"Broker '{clean_id}' not found in registry. Defaulting to 'icici'.")
        return self._adapters["icici"]

    def list_brokers(self) -> List[Dict[str, Any]]:
        """
        Returns catalog of supported brokers for frontend discovery and selection UI.
        """
        catalog = []
        # Active adapters
        for b_id, adapter in self._adapters.items():
            catalog.append({
                "id": adapter.broker_id,
                "name": adapter.display_name,
                "status": "active" if adapter.is_active else "inactive",
                "auth_type": adapter.auth_type,
                "login_url": adapter.get_login_url(),
                "description": "Connect via official User ID & OTP in 10s"
            })

        # Planned / Upcoming broker placeholders for UI badging
        upcoming = [
            {
                "id": "zerodha",
                "name": "Zerodha Kite",
                "status": "coming_soon",
                "auth_type": "oauth",
                "login_url": "",
                "description": "Kite Connect OAuth2 integration"
            },
            {
                "id": "angelone",
                "name": "Angel One",
                "status": "coming_soon",
                "auth_type": "totp",
                "login_url": "",
                "description": "SmartAPI TOTP integration"
            },
            {
                "id": "upstox",
                "name": "Upstox",
                "status": "coming_soon",
                "auth_type": "oauth",
                "login_url": "",
                "description": "Upstox API integration"
            }
        ]

        active_ids = {c["id"] for c in catalog}
        for up in upcoming:
            if up["id"] not in active_ids:
                catalog.append(up)

        return catalog


# Singleton Registry Instance
broker_registry = BrokerRegistry()


def get_broker(broker_id: Optional[str] = "icici") -> BaseBrokerAdapter:
    return broker_registry.get_broker(broker_id)


def list_supported_brokers() -> List[Dict[str, Any]]:
    return broker_registry.list_brokers()
