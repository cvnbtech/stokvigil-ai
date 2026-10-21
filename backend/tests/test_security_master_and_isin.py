"""
Tests for StokVigil AI Security Master & ISIN Resolution Architecture.
Validates ISIN format validation, bidirectional ISIN <-> Ticker resolution,
dynamic runtime security registration, ICICI Direct broker code translation,
BSE 6-digit scrip mapping, and watchlist deduplication logic.
ZERO static dictionary dependencies.
"""

import pytest
from app.engine.security_master import (
    is_valid_isin,
    init_security_master,
    resolve_isin_to_symbol,
    resolve_symbol_to_isin,
    resolve_security,
    register_dynamic_security,
)


@pytest.fixture(scope="module", autouse=True)
def setup_security_master():
    """Ensure Security Master is dynamically initialized and ready before running tests."""
    init_security_master()
    # Register dynamic broker alias as received from authentic Demat holding payloads
    register_dynamic_security("TELCO", "INE155A01022", "TATAMOTORS", "Tata Motors Limited", "NSE")


def test_is_valid_isin():
    # Valid Indian equity ISINs
    assert is_valid_isin("INE002A01018") is True  # Reliance
    assert is_valid_isin("INE155A01022") is True  # Tata Motors
    assert is_valid_isin("INE009A01021") is True  # Infosys
    assert is_valid_isin("INF760C01018") is True  # Mutual Fund / ETF
    assert is_valid_isin("IN9155A01020") is True  # Partly paid shares

    # Invalid ISINs
    assert is_valid_isin("") is False
    assert is_valid_isin(None) is False
    assert is_valid_isin("RELIANCE") is False
    assert is_valid_isin("TELCO") is False
    assert is_valid_isin("INE155A0102") is False  # 11 chars (short)
    assert is_valid_isin("INE155A010222") is False  # 13 chars (long)
    assert is_valid_isin("USA002A01018") is False  # Foreign


def test_dynamic_registration_and_resolution():
    """Verifies that new securities and broker abbreviations can be registered dynamically at runtime."""
    custom_isin = "INE999Z01099"
    register_dynamic_security(
        identifier="MYBROKERCODE",
        isin=custom_isin,
        canonical_symbol="CUSTOMSTOCK",
        company_name="Custom Technologies Limited",
        exchange="NSE"
    )

    # Resolve by broker code
    res_code = resolve_security("MYBROKERCODE")
    assert res_code["isin"] == custom_isin
    assert res_code["symbol"] == "CUSTOMSTOCK"
    assert res_code["company_name"] == "Custom Technologies Limited"

    # Resolve by canonical symbol
    res_sym = resolve_security("CUSTOMSTOCK")
    assert res_sym["isin"] == custom_isin

    # Resolve bidirectional ISIN <-> Symbol
    assert resolve_isin_to_symbol(custom_isin) == "CUSTOMSTOCK"
    assert resolve_symbol_to_isin("MYBROKERCODE") == custom_isin
    assert resolve_symbol_to_isin("CUSTOMSTOCK") == custom_isin


def test_icici_broker_code_resolution():
    # Test major ICICI proprietary codes dynamically resolved
    telco = resolve_security("TELCO")
    assert telco["symbol"] == "TATAMOTORS"
    assert telco["isin"] == "INE155A01022"
    assert telco["exchange"] == "NSE"

    inftec = resolve_security("INFTEC")
    assert inftec["symbol"] == "INFY"
    assert inftec["isin"] == "INE009A01021"

    hdfban = resolve_security("HDFBAN")
    assert hdfban["symbol"] == "HDFCBANK"
    assert hdfban["isin"] == "INE040A01034"

    lartou = resolve_security("LARTOU")
    assert lartou["symbol"] == "LT"
    assert lartou["isin"] == "INE018A01030"

    staban = resolve_security("STABAN")
    assert staban["symbol"] == "SBIN"
    assert staban["isin"] == "INE062A01020"


def test_bse_dynamic_scrip_resolution():
    """Verifies dynamic BSE 6-digit scrip code mapping."""
    reliance_bse = resolve_security("500325", exchange="BSE")
    assert reliance_bse["isin"] == "INE002A01018"
    assert reliance_bse["exchange"] == "BSE"
    assert reliance_bse["full_symbol"] == "500325.BO"

    tcs_bse = resolve_security("532540", exchange="BSE")
    assert tcs_bse["isin"] == "INE467B01029"
    assert tcs_bse["exchange"] == "BSE"
    assert tcs_bse["full_symbol"] == "532540.BO"

    infy_bse = resolve_security("500209", exchange="BSE")
    assert infy_bse["isin"] == "INE009A01021"
    assert infy_bse["exchange"] == "BSE"


def test_isin_to_symbol_resolution():
    # Reliance
    assert resolve_isin_to_symbol("INE002A01018") == "RELIANCE"
    # Infosys
    assert resolve_isin_to_symbol("INE009A01021") == "INFY"
    # Tata Motors
    assert resolve_isin_to_symbol("INE155A01022") == "TATAMOTORS"


def test_symbol_to_isin_resolution():
    assert resolve_symbol_to_isin("RELIANCE") == "INE002A01018"
    assert resolve_symbol_to_isin("RELIANCE.NS") == "INE002A01018"
    assert resolve_symbol_to_isin("INFY") == "INE009A01021"
    assert resolve_symbol_to_isin("TATAMOTORS") == "INE155A01022"
    # ICICI Code directly to ISIN
    assert resolve_symbol_to_isin("TELCO") == "INE155A01022"
    assert resolve_symbol_to_isin("INFTEC") == "INE009A01021"
    # BSE 6-digit scrip directly to ISIN
    assert resolve_symbol_to_isin("500325") == "INE002A01018"
    assert resolve_symbol_to_isin("532540") == "INE467B01029"


def test_resolve_security_any_identifier():
    # 1. By ISIN
    res1 = resolve_security("INE002A01018")
    assert res1["isin"] == "INE002A01018"
    assert res1["symbol"] == "RELIANCE"
    assert res1["full_symbol"] == "RELIANCE.NS"

    # 2. By Clean Ticker
    res2 = resolve_security("TCS")
    assert res2["isin"] == "INE467B01029"
    assert res2["symbol"] == "TCS"
    assert res2["full_symbol"] == "TCS.NS"

    # 3. By Suffix Ticker
    res3 = resolve_security("HDFCBANK.NS")
    assert res3["isin"] == "INE040A01034"
    assert res3["symbol"] == "HDFCBANK"

    # 4. By BSE Scrip Code
    res4 = resolve_security("500570", exchange="BSE")
    assert res4["exchange"] == "BSE"
    assert res4["full_symbol"] == "500570.BO"
    assert res4["isin"] == "INE155A01022"


def test_deduplication_grouping_logic():
    # Simulate rows in database that represent the same stock
    sample_rows = [
        {"id": "1", "symbol": "TELCO", "average_buy_price": None, "quantity": None, "is_auto_synced": True},
        {"id": "2", "symbol": "TATAMOTORS", "average_buy_price": 750.50, "quantity": 100, "is_auto_synced": True},
        {"id": "3", "symbol": "TATAMOTORS.NS", "average_buy_price": None, "quantity": None, "is_auto_synced": False},
        {"id": "4", "symbol": "INE155A01022", "average_buy_price": None, "quantity": None, "is_auto_synced": True},
    ]

    # Map each row through resolve_security
    resolved_groups = {}
    for r in sample_rows:
        sec = resolve_security(r["symbol"])
        isin = sec.get("isin")
        assert isin == "INE155A01022"  # ALL 4 resolve to the identical ISIN!
        if isin not in resolved_groups:
            resolved_groups[isin] = []
        resolved_groups[isin].append(r)

    # All 4 rows collapsed into 1 single ISIN group
    assert len(resolved_groups) == 1
    tata_group = resolved_groups["INE155A01022"]
    assert len(tata_group) == 4

    # Best master row selection: row with average_buy_price > 0
    sorted_group = sorted(
        tata_group,
        key=lambda x: (
            1 if (x.get("average_buy_price") and float(x.get("average_buy_price") or 0) > 0) else 0,
            1 if x.get("is_auto_synced") else 0
        ),
        reverse=True
    )
    master = sorted_group[0]
    duplicates = sorted_group[1:]

    assert master["id"] == "2"
    assert master["average_buy_price"] == 750.50
    assert master["quantity"] == 100
    assert len(duplicates) == 3
    assert set(d["id"] for d in duplicates) == {"1", "3", "4"}
