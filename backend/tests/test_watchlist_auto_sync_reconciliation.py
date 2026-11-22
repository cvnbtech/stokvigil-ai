import unittest
from unittest.mock import MagicMock, call
from app.routers.auth import _async_sync_demat_to_watchlists


class TestWatchlistAutoSyncReconciliation(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.user_id = "test-user-123"

    def test_reconcile_purges_completely_sold_holding_while_preserving_manual_stock(self):
        """
        Option A: If an auto-synced stock is completely sold (missing from active holdings),
        it must be deleted from user_watchlists table, while manual stocks (is_auto_synced=False)
        must remain untouched.
        """
        # Mock existing database rows in user_watchlists
        # HDFCBANK: auto-synced, now sold 100%
        # RELIANCE: auto-synced, still held
        # INFY: manual watchlist item (is_auto_synced=False)
        existing_rows = [
            {"id": "row-hdfc-1", "symbol": "HDFCBANK", "isin": "INE040A01034"},
            {"id": "row-rel-2", "symbol": "RELIANCE", "isin": "INE002A01018"},
        ]

        # Setup mock db queries
        mock_table = MagicMock()
        self.mock_db.table.return_value = mock_table

        # Mock select query for is_auto_synced=True
        mock_select = MagicMock()
        mock_eq_user = MagicMock()
        mock_eq_auto = MagicMock()
        mock_execute = MagicMock()

        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq_user
        mock_eq_user.eq.return_value = mock_eq_auto
        mock_eq_auto.execute.return_value = MagicMock(data=existing_rows)

        # Mock delete query
        mock_delete = MagicMock()
        mock_in = MagicMock()
        mock_table.delete.return_value = mock_delete
        mock_delete.in_.return_value = mock_in
        mock_in.execute.return_value = MagicMock(data=[])

        # Active holdings returned by broker (HDFCBANK is gone, RELIANCE is held, TRENT is new)
        active_holdings = [
            {"symbol": "RELIANCE", "company_name": "Reliance Industries", "quantity": 50, "average_price": 2500.0, "isin": "INE002A01018"},
            {"symbol": "TRENT", "company_name": "Trent Ltd", "quantity": 25, "average_price": 7100.0, "isin": "INE849A01020"}
        ]

        _async_sync_demat_to_watchlists(self.mock_db, self.user_id, active_holdings)

        # Verify that delete was called strictly for HDFCBANK ("row-hdfc-1")
        mock_table.delete.assert_called()
        mock_delete.in_.assert_called_with("id", ["row-hdfc-1"])

    def test_reconcile_when_all_holdings_are_sold_empty_list(self):
        """
        When user liquidates 100% of all holdings (empty holdings list),
        all auto-synced rows must be purged, while manual rows are never touched.
        """
        existing_rows = [
            {"id": "row-rel-2", "symbol": "RELIANCE", "isin": "INE002A01018"},
            {"id": "row-trent-3", "symbol": "TRENT", "isin": "INE849A01020"}
        ]

        mock_table = MagicMock()
        self.mock_db.table.return_value = mock_table

        mock_select = MagicMock()
        mock_eq_user = MagicMock()
        mock_eq_auto = MagicMock()

        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq_user
        mock_eq_user.eq.return_value = mock_eq_auto
        mock_eq_auto.execute.return_value = MagicMock(data=existing_rows)

        mock_delete = MagicMock()
        mock_in = MagicMock()
        mock_table.delete.return_value = mock_delete
        mock_delete.in_.assert_called_once_with = mock_in

        # Empty active holdings (all sold)
        active_holdings = []

        _async_sync_demat_to_watchlists(self.mock_db, self.user_id, active_holdings)

        # Both auto-synced rows should be deleted
        mock_delete.in_.assert_called_with("id", ["row-rel-2", "row-trent-3"])

    def test_partial_sell_does_not_delete_holding(self):
        """
        Partial sell (quantity remains > 0) must update quantity and NEVER delete the row.
        """
        existing_rows = [
            {"id": "row-rel-2", "symbol": "RELIANCE", "isin": "INE002A01018"}
        ]

        mock_table = MagicMock()
        self.mock_db.table.return_value = mock_table

        mock_select = MagicMock()
        mock_eq_user = MagicMock()
        mock_eq_auto = MagicMock()

        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq_user
        mock_eq_user.eq.return_value = mock_eq_auto
        mock_eq_auto.execute.return_value = MagicMock(data=existing_rows)

        mock_delete = MagicMock()
        mock_table.delete.return_value = mock_delete

        # Partial sell: RELIANCE quantity dropped from 100 to 40, but still > 0
        active_holdings = [
            {"symbol": "RELIANCE", "company_name": "Reliance Industries", "quantity": 40, "average_price": 2500.0, "isin": "INE002A01018"}
        ]

        _async_sync_demat_to_watchlists(self.mock_db, self.user_id, active_holdings)

        # Delete should NOT be called because RELIANCE is still active
        mock_delete.in_.assert_not_called()


if __name__ == "__main__":
    unittest.main()
