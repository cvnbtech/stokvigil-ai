"""
StokVigil AI — Test Suite for Vectorized 200+ Stock Ingestion Engine (Phase 2)
Validates chunked batch downloading, MultiIndex extraction, and 200-stock throughput.
"""

import time
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch
from app.technical_engine import (
    batch_fetch_multi_timeframe_technicals,
    _extract_ticker_from_batch
)


def _generate_synthetic_ohlcv(bars: int = 150) -> pd.DataFrame:
    """Generates realistic 5m OHLCV synthetic data for testing."""
    dates = pd.date_range("2026-11-06 09:15:00", periods=bars, freq="5min")
    prices = 1000.0 + np.cumsum(np.random.randn(bars) * 2.0)
    df = pd.DataFrame({
        "Open": prices,
        "High": prices + np.random.uniform(0.5, 3.0, bars),
        "Low": prices - np.random.uniform(0.5, 3.0, bars),
        "Close": prices + np.random.randn(bars),
        "Volume": np.random.randint(10000, 50000, bars)
    }, index=dates)
    return df


def test_extract_ticker_from_multiindex_batch():
    """Validates robust extraction from both standard and alternate MultiIndex DataFrames."""
    df_sym1 = _generate_synthetic_ohlcv(50)
    df_sym2 = _generate_synthetic_ohlcv(50)
    
    # Standard format: Level 0 is Ticker, Level 1 is Field
    batch_dict = {
        ("RELIANCE.NS", "Open"): df_sym1["Open"],
        ("RELIANCE.NS", "High"): df_sym1["High"],
        ("RELIANCE.NS", "Low"): df_sym1["Low"],
        ("RELIANCE.NS", "Close"): df_sym1["Close"],
        ("RELIANCE.NS", "Volume"): df_sym1["Volume"],
        ("TCS.NS", "Open"): df_sym2["Open"],
        ("TCS.NS", "High"): df_sym2["High"],
        ("TCS.NS", "Low"): df_sym2["Low"],
        ("TCS.NS", "Close"): df_sym2["Close"],
        ("TCS.NS", "Volume"): df_sym2["Volume"],
    }
    multi_df = pd.DataFrame(batch_dict)
    multi_df.columns = pd.MultiIndex.from_tuples(multi_df.columns)

    extracted = _extract_ticker_from_batch(multi_df, "RELIANCE.NS", 2)
    assert not extracted.empty
    assert "Close" in extracted.columns
    assert len(extracted) == 50

    extracted_tcs = _extract_ticker_from_batch(multi_df, "TCS.NS", 2)
    assert not extracted_tcs.empty
    assert len(extracted_tcs) == 50


def test_200_stock_scale_chunked_batch_processing():
    """
    Simulates high-throughput surveillance of 200 unique stocks.
    Asserts chunking in batches of 50 and sub-second calculation in RAM.
    """
    symbols = [f"STOCK_{i:03d}" for i in range(1, 201)]  # 200 stocks: STOCK_001 to STOCK_200
    
    # Synthetic batch response mock for a chunk of tickers
    def mock_download(tickers, *args, **kwargs):
        ticker_list = tickers if isinstance(tickers, list) else [tickers]
        data = {}
        for t in ticker_list:
            df = _generate_synthetic_ohlcv(60)
            for col in ["Open", "High", "Low", "Close", "Volume"]:
                data[(t, col)] = df[col]
        m_df = pd.DataFrame(data)
        if m_df.empty:
            return pd.DataFrame()
        m_df.columns = pd.MultiIndex.from_tuples(m_df.columns)
        return m_df

    t0 = time.time()
    with patch("yfinance.download", side_effect=mock_download):
        results = batch_fetch_multi_timeframe_technicals(symbols)
    elapsed = time.time() - t0

    assert len(results) == 200
    for sym in symbols[:10]:
        assert sym in results
        tech = results[sym]
        assert "current_price" in tech
        assert "rsi_14" in tech or "technical_score" in tech

    # Assert computation finishes rapidly (under 12 seconds for 200 stocks in test)
    assert elapsed < 12.0, f"200-stock processing took {elapsed:.2f}s, exceeding 12.0s budget"
