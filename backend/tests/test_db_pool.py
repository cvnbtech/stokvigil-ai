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


if __name__ == "__main__":
    unittest.main()
