import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import date
from app.brokers.registry import BrokerRegistry, get_broker
from app.brokers.icici_adapter import IciciBrokerAdapter
from app.brokers.dhan_adapter import DhanBrokerAdapter
from app.brokers.angel_adapter import AngelBrokerAdapter


class TestBrokerRegistry:
    """Verifies Central Broker Registry registration and discovery."""

    def test_registry_has_core_brokers(self):
        registry = BrokerRegistry()
        icici = registry.get_broker("icici")
        assert isinstance(icici, IciciBrokerAdapter)
        assert icici.broker_id == "icici"

        dhan = registry.get_broker("dhan")
        assert isinstance(dhan, DhanBrokerAdapter)
        assert dhan.broker_id == "dhan"

        angel = registry.get_broker("angelone")
        assert isinstance(angel, AngelBrokerAdapter)
        assert angel.broker_id == "angelone"

    def test_fallback_to_default_icici(self):
        registry = BrokerRegistry()
        unknown = registry.get_broker("non_existent_broker")
        assert isinstance(unknown, IciciBrokerAdapter)

    def test_list_brokers_catalog(self):
        registry = BrokerRegistry()
        catalog = registry.list_brokers()
        broker_ids = {c["id"] for c in catalog}
        assert "icici" in broker_ids
        assert "dhan" in broker_ids
        assert "angelone" in broker_ids
        assert "zerodha" in broker_ids

        dhan_entry = next(c for c in catalog if c["id"] == "dhan")
        assert dhan_entry["status"] == "active"
        assert dhan_entry["auth_type"] == "access_token"

        angel_entry = next(c for c in catalog if c["id"] == "angelone")
        assert angel_entry["status"] == "active"
        assert angel_entry["auth_type"] == "totp"


class TestDhanBrokerAdapter:
    """Verifies Dhan HQ Adapter holdings normalization and order execution."""

    def test_save_credentials(self):
        adapter = DhanBrokerAdapter()
        mock_db = MagicMock()
        mock_vault = MagicMock()
        mock_vault.encrypt.side_effect = lambda x: f"enc_{x}"

        res = adapter.save_credentials(
            db=mock_db,
            vault=mock_vault,
            user_id="user_123",
            session_token="dhan_access_jwt_123",
            client_id="1000000001"
        )
        assert res["status"] == "success"
        assert res["broker"] == "dhan"
        assert mock_db.table("user_credentials").upsert.called

    def test_fetch_holdings_normalization(self):
        adapter = DhanBrokerAdapter()
        raw_holdings = [
            {
                "tradingSymbol": "TATAMOTORS",
                "exchangeSegment": "NSE_EQ",
                "totalQty": 25,
                "avgCostPrice": 920.0,
                "lastTradedPrice": 965.50
            },
            {
                "tradingSymbol": "INFY",
                "exchangeSegment": "NSE_EQ",
                "totalQty": 10,
                "avgCostPrice": 1500.0,
                "lastTradedPrice": 1450.0
            }
        ]

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(raw_holdings).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            holdings = adapter.fetch_holdings({
                "session_token": "valid_token",
                "client_id": "1000000001"
            })

        assert len(holdings) == 2
        tata = holdings[0]
        assert tata["symbol"] == "TATAMOTORS"
        assert tata["quantity"] == 25.0
        assert tata["average_price"] == 920.0
        assert tata["current_price"] == 965.50
        assert tata["current_value"] == 25.0 * 965.50
        assert tata["pnl"] == round(25.0 * (965.50 - 920.0), 2)
        assert tata["pnl_percent"] > 0
        assert tata["broker"] == "dhan"

    def test_place_order_sebi_sl_m_ban(self):
        """Verifies SEBI mandatory compliance: SL-M orders must be rejected."""
        adapter = DhanBrokerAdapter()
        with pytest.raises(ValueError, match="SEBI COMPLIANCE VIOLATION"):
            adapter.place_order(
                decrypted_creds={"session_token": "tok"},
                order_params={
                    "stock_code": "RELIANCE",
                    "order_type": "SL-M",
                    "quantity": 10
                }
            )

    def test_place_order_limit_success(self):
        adapter = DhanBrokerAdapter()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({
            "orderId": "DHAN_ORD_998877",
            "orderStatus": "TRANSIT"
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = adapter.place_order(
                decrypted_creds={"session_token": "tok", "client_id": "101"},
                order_params={
                    "stock_code": "RELIANCE",
                    "order_type": "LIMIT",
                    "action": "BUY",
                    "quantity": 5,
                    "price": 2500.0,
                    "product": "cash"
                }
            )

        assert res["status"] == "success"
        assert res["order_id"] == "DHAN_ORD_998877"
        assert res["broker"] == "dhan"


class TestAngelBrokerAdapter:
    """Verifies Angel One SmartAPI Adapter holdings normalization and order execution."""

    def test_save_credentials(self):
        adapter = AngelBrokerAdapter()
        mock_db = MagicMock()
        mock_vault = MagicMock()
        mock_vault.encrypt.side_effect = lambda x: f"enc_{x}"

        res = adapter.save_credentials(
            db=mock_db,
            vault=mock_vault,
            user_id="user_456",
            session_token="angel_jwt_token_xyz",
            client_code="A123456",
            api_key="angel_api_key"
        )
        assert res["status"] == "success"
        assert res["broker"] == "angelone"
        assert mock_db.table("user_credentials").upsert.called

    def test_fetch_holdings_normalization(self):
        adapter = AngelBrokerAdapter()
        raw_response = {
            "status": True,
            "data": [
                {
                    "tradingsymbol": "SBIN-EQ",
                    "exchange": "NSE",
                    "totalholdingqty": 100,
                    "averageprice": 810.0,
                    "ltp": 835.0,
                    "profitandloss": 2500.0,
                    "pnlpercentage": 3.09
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(raw_response).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            holdings = adapter.fetch_holdings({
                "session_token": "jwt_token_sample",
                "api_key": "sample_key"
            })

        assert len(holdings) == 1
        sbin = holdings[0]
        assert sbin["symbol"] == "SBIN"
        assert sbin["quantity"] == 100.0
        assert sbin["average_price"] == 810.0
        assert sbin["current_price"] == 835.0
        assert sbin["broker"] == "angelone"

    def test_place_order_sebi_sl_m_ban(self):
        """Verifies SEBI mandatory compliance: SL-M orders must be rejected."""
        adapter = AngelBrokerAdapter()
        with pytest.raises(ValueError, match="SEBI COMPLIANCE VIOLATION"):
            adapter.place_order(
                decrypted_creds={"session_token": "jwt"},
                order_params={
                    "stock_code": "SBIN",
                    "order_type": "STOPLOSS_MARKET",
                    "quantity": 10
                }
            )

    def test_place_order_limit_success(self):
        adapter = AngelBrokerAdapter()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({
            "status": True,
            "message": "SUCCESS",
            "data": {"orderid": "ANGEL_ORD_112233"}
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = adapter.place_order(
                decrypted_creds={"session_token": "jwt", "api_key": "key"},
                order_params={
                    "stock_code": "SBIN",
                    "order_type": "LIMIT",
                    "action": "BUY",
                    "quantity": 10,
                    "price": 815.0,
                    "product": "cnc"
                }
            )

        assert res["status"] == "success"
        assert res["order_id"] == "ANGEL_ORD_112233"
        assert res["broker"] == "angelone"


class TestMultiBrokerOrderEndpoint:
    """Verifies /api/v1/orders/place routes correctly to Dhan HQ and Angel One adapters."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.auth import get_current_user_id
        app.dependency_overrides[get_current_user_id] = lambda: "test-user-123"
        yield TestClient(app)
        app.dependency_overrides.pop(get_current_user_id, None)

    def test_dhan_order_placement_flow(self, client):
        mock_cred = {
            "user_id": "test-user-123",
            "broker_id": "dhan",
            "encrypted_session_token": "enc_dhan_token",
            "encrypted_app_key": "enc_client_101",
            "token_date": str(date.today())
        }

        mock_db = MagicMock()
        mock_db.table("user_credentials").select.return_value.eq.return_value.execute.return_value.data = [mock_cred]

        from app.core.dependencies import get_supabase
        from app.main import app
        app.dependency_overrides[get_supabase] = lambda: mock_db

        try:
            with patch("app.routers.orders.vault") as mock_vault, \
                 patch("app.brokers.dhan_adapter.DhanBrokerAdapter.place_order") as mock_place_order, \
                 patch("app.routers.orders.get_market_session_status", return_value=(True, "Market Open")):

                mock_vault.decrypt.side_effect = lambda x: f"dec_{x}"
                mock_place_order.return_value = {
                    "status": "success",
                    "broker": "dhan",
                    "order_id": "DHAN_ROUTED_555"
                }

                payload = {
                    "user_id": "test-user-123",
                    "symbol": "INFY",
                    "action": "BUY",
                    "quantity": 10,
                    "order_type": "LIMIT",
                    "price": 1450.0,
                    "product": "cash"
                }

                res = client.post("/api/v1/orders/place", json=payload)
                assert res.status_code == 200
                data = res.json()
                assert data["status"] == "success"
                assert data["broker"] == "dhan"
                assert data["broker_response"]["order_id"] == "DHAN_ROUTED_555"
                assert mock_place_order.called
        finally:
            app.dependency_overrides.pop(get_supabase, None)

    def test_angelone_order_placement_flow(self, client):
        mock_cred = {
            "user_id": "test-user-123",
            "broker_id": "angelone",
            "encrypted_session_token": "enc_angel_jwt",
            "encrypted_app_key": "enc_client_A99",
            "token_date": str(date.today())
        }

        mock_db = MagicMock()
        mock_db.table("user_credentials").select.return_value.eq.return_value.execute.return_value.data = [mock_cred]

        from app.core.dependencies import get_supabase
        from app.main import app
        app.dependency_overrides[get_supabase] = lambda: mock_db

        try:
            with patch("app.routers.orders.vault") as mock_vault, \
                 patch("app.brokers.angel_adapter.AngelBrokerAdapter.place_order") as mock_place_order, \
                 patch("app.routers.orders.get_market_session_status", return_value=(True, "Market Open")):

                mock_vault.decrypt.side_effect = lambda x: f"dec_{x}"
                mock_place_order.return_value = {
                    "status": "success",
                    "broker": "angelone",
                    "order_id": "ANGEL_ROUTED_777"
                }

                payload = {
                    "user_id": "test-user-123",
                    "symbol": "TCS",
                    "action": "BUY",
                    "quantity": 5,
                    "order_type": "LIMIT",
                    "price": 3800.0,
                    "product": "cash"
                }

                res = client.post("/api/v1/orders/place", json=payload)
                assert res.status_code == 200
                data = res.json()
                assert data["status"] == "success"
                assert data["broker"] == "angelone"
                assert data["broker_response"]["order_id"] == "ANGEL_ROUTED_777"
                assert mock_place_order.called
        finally:
            app.dependency_overrides.pop(get_supabase, None)

