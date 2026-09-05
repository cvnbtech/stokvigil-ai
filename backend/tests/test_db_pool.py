import sys
import os
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.config import settings
from app.db_pool import _mask_db_url, init_db_pool, close_db_pool, get_db_pool, get_db_connection, is_pool_ready


class TestDBPool(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Reset pool before tests
        await close_db_pool()

    async def asyncTearDown(self):
        await close_db_pool()

    def test_mask_db_url_security(self):
        """Verifies database password is never exposed in logs."""
        raw = "postgresql://postgres.testref:SecretPass123@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?pgbouncer=true"
        masked = _mask_db_url(raw)
        self.assertNotIn("SecretPass123", masked)
        self.assertIn("postgres.testref", masked)
        self.assertIn("pooler.supabase.com:6543", masked)
        self.assertIn("***", masked)

    async def test_init_db_pool_unconfigured(self):
        """When DATABASE_URL is empty, init_db_pool gracefully returns None without crashing."""
        with patch.object(settings, "DATABASE_URL", ""):
            pool = await init_db_pool()
            self.assertIsNone(pool)
            self.assertFalse(is_pool_ready())

    def test_api_health_db_unconfigured(self):
        """Endpoint /api/health/db reports fallback to supabase-rest when unconfigured."""
        client = TestClient(app)
        res = client.get("/api/health/db")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ready")
        self.assertFalse(data["pooler_active"])
        self.assertEqual(data["driver"], "supabase-rest")

    async def test_get_db_health_mocked_active_pool(self):
        """Verifies health check output when PgBouncer pool is active."""
        mock_pool = MagicMock()
        mock_pool._closed = False
        mock_pool.get_max_size.return_value = 10
        mock_pool.get_min_size.return_value = 2
        mock_pool.get_idle_size.return_value = 2

        mock_conn = MagicMock()
        mock_conn.fetchval = AsyncMock(return_value=1)

        # Mock pool.acquire context manager
        mock_acquire_cm = MagicMock()
        mock_acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_cm.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = mock_acquire_cm

        with patch("app.main.get_db_pool", AsyncMock(return_value=mock_pool)):
            client = TestClient(app)
            res = client.get("/api/health/db")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["status"], "healthy")
            self.assertTrue(data["pooler_active"])
            self.assertEqual(data["pooler"], "pgbouncer-6543")
            self.assertEqual(data["test_query"], 1)
            self.assertEqual(data["max_size"], 10)

    async def test_context_manager_unconfigured(self):
        """get_db_connection yields None safely when pool is unconfigured."""
        async with get_db_connection() as conn:
            self.assertIsNone(conn)

    def test_normalize_param_uuid_and_primitives(self):
        """Valid UUID strings are converted to uuid.UUID; other primitives remain unchanged."""
        from app.db_pool import _normalize_param
        import uuid

        raw_uuid = "550e8400-e29b-41d4-a716-446655440000"
        norm_uuid = _normalize_param(raw_uuid)
        self.assertIsInstance(norm_uuid, uuid.UUID)
        self.assertEqual(str(norm_uuid), raw_uuid)

        # Non-UUID string preserved
        self.assertEqual(_normalize_param("RELIANCE"), "RELIANCE")
        self.assertEqual(_normalize_param(100), 100)

    def test_normalize_value_and_row(self):
        """Verifies UUID, datetime, Decimal, and JSON fields match Supabase REST contracts."""
        from app.db_pool import _normalize_row
        import uuid
        from datetime import datetime, timezone
        from decimal import Decimal

        test_uuid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        record = {
            "id": test_uuid,
            "created_at": now,
            "impact_score": Decimal("85.50"),
            "metrics_snapshot": '{"entry_range": "100-105", "target_1": "115"}',
            "symbol": "TCS",
            "is_active": True,
            "null_val": None
        }

        normalized = _normalize_row(record)
        self.assertEqual(normalized["id"], str(test_uuid))
        self.assertEqual(normalized["created_at"], now.isoformat())
        self.assertEqual(normalized["impact_score"], 85.50)
        self.assertIsInstance(normalized["metrics_snapshot"], dict)
        self.assertEqual(normalized["metrics_snapshot"]["target_1"], "115")
        self.assertEqual(normalized["symbol"], "TCS")
        self.assertTrue(normalized["is_active"])
        self.assertIsNone(normalized["null_val"])

    async def test_fetch_all_and_fetch_one_normalization(self):
        """fetch_all and fetch_one normalize types when acquiring from pool."""
        from app.db_pool import fetch_all, fetch_one
        import uuid

        test_uid = uuid.uuid4()
        fake_records = [
            {"id": test_uid, "user_id": test_uid, "metrics_snapshot": '{"a": 1}'}
        ]

        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=fake_records)
        mock_conn.fetchrow = AsyncMock(return_value=fake_records[0])

        mock_acquire_cm = MagicMock()
        mock_acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_cm.__aexit__ = AsyncMock(return_value=None)

        mock_pool = MagicMock()
        mock_pool._closed = False
        mock_pool.acquire.return_value = mock_acquire_cm

        with patch("app.db_pool.get_db_pool", AsyncMock(return_value=mock_pool)):
            # Test fetch_all
            rows = await fetch_all("SELECT * FROM stok_alerts WHERE user_id = $1", str(test_uid))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], str(test_uid))
            self.assertEqual(rows[0]["metrics_snapshot"], {"a": 1})

            # Test fetch_one
            single = await fetch_one("SELECT * FROM profiles WHERE id = $1", str(test_uid))
            self.assertEqual(single["id"], str(test_uid))

            # Test fetch_one when not found
            mock_conn.fetchrow.return_value = None
            empty = await fetch_one("SELECT * FROM profiles WHERE id = $1", str(test_uid))
            self.assertEqual(empty, {})


if __name__ == "__main__":
    unittest.main()
