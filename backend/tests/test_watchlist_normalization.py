import pytest
from unittest.mock import MagicMock
from app.engine.portfolio_sync import normalize_watchlist_symbol
from app.routers.auth import _async_sync_demat_to_watchlists


def test_normalize_watchlist_symbol_nse():
    # Strips .NS suffix to canonical bare symbol
    assert normalize_watchlist_symbol("RELIANCE.NS") == "RELIANCE"
    assert normalize_watchlist_symbol("reliance.ns") == "RELIANCE"
    assert normalize_watchlist_symbol("  TCS.NS  ") == "TCS"
    assert normalize_watchlist_symbol("INFY") == "INFY"


def test_normalize_watchlist_symbol_bse():
    # Preserves .BO suffix
    assert normalize_watchlist_symbol("RELIANCE.BO") == "RELIANCE.BO"
    assert normalize_watchlist_symbol("500325.BO") == "500325.BO"
    assert normalize_watchlist_symbol("tcs.bo") == "TCS.BO"

    # Preserves 6-digit numeric BSE scrip codes
    assert normalize_watchlist_symbol("500325") == "500325"
    assert normalize_watchlist_symbol("532540") == "532540"

    # Appends .BO when exchange is explicitly BSE
    assert normalize_watchlist_symbol("ZOMATO", exchange="BSE") == "ZOMATO.BO"
    assert normalize_watchlist_symbol("zomato", exchange="bse") == "ZOMATO.BO"
    assert normalize_watchlist_symbol("ZOMATO.BO", exchange="BSE") == "ZOMATO.BO"
    assert normalize_watchlist_symbol("500325", exchange="BSE") == "500325"


def test_normalize_watchlist_symbol_edge_cases():
    assert normalize_watchlist_symbol("") == ""
    assert normalize_watchlist_symbol(None) == ""
    assert normalize_watchlist_symbol("   ") == ""


def test_async_sync_demat_to_watchlists_deduplication():
    # Simulates demat holdings containing both RELIANCE and RELIANCE.NS, plus a BSE holding
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table
    mock_upsert = MagicMock()
    mock_table.upsert.return_value = mock_upsert

    holdings = [
        {"symbol": "RELIANCE.NS", "quantity": 10, "average_price": 2800.0, "exchange": "NSE"},
        {"symbol": "RELIANCE", "quantity": 10, "average_price": 2800.0, "exchange": "NSE"},
        {"symbol": "TCS.BO", "quantity": 5, "average_price": 3500.0, "exchange": "BSE"},
        {"symbol": "500209", "quantity": 2, "average_price": 1500.0, "exchange": "BSE"},  # Infosys on BSE
    ]

    _async_sync_demat_to_watchlists(mock_db, "user-123", holdings)

    mock_db.table.assert_called_with("user_watchlists")
    # Verify upsert payload is deduplicated
    call_args, call_kwargs = mock_table.upsert.call_args
    payload = call_args[0]
    assert call_kwargs.get("on_conflict") == "user_id,isin"

    # Must contain exactly 3 items: RELIANCE, TCS.BO, 500209 (RELIANCE.NS merged into RELIANCE)
    symbols = [row["symbol"] for row in payload]
    assert len(symbols) == 3
    assert "RELIANCE" in symbols
    assert "TCS.BO" in symbols
    assert "500209" in symbols
    assert "RELIANCE.NS" not in symbols


def test_async_sync_demat_to_watchlists_string_deduplication():
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table
    mock_upsert = MagicMock()
    mock_table.upsert.return_value = mock_upsert

    symbol_strings = ["INFY.NS", "INFY", "WIPRO.BO", "wipro.bo"]
    _async_sync_demat_to_watchlists(mock_db, "user-456", symbol_strings)

    call_args, call_kwargs = mock_table.upsert.call_args
    payload = call_args[0]
    symbols = [row["symbol"] for row in payload]
    assert len(symbols) == 2
    assert "INFY" in symbols
    assert "WIPRO.BO" in symbols
