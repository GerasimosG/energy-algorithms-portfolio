"""Adapters layer — concrete implementations of ports.

ENTSO-E API client, yfinance data fetcher, SQLite store,
and application configuration.
"""

from energy_algorithms.adapters.config import ENTSOE_API_KEY
from energy_algorithms.adapters.entsoe_client import (
    EntsoeClient,
    fetch_demo_day_ahead,
    fetch_demo_generation_mix,
)
from energy_algorithms.adapters.yfinance_fetcher import fetch_ticker, fetch_batch
from energy_algorithms.adapters.sqlite_store import (
    get_connection,
    init_db,
    insert_ohlcv,
    get_ticker_data,
    get_summary,
)

__all__ = [
    # Config
    "ENTSOE_API_KEY",
    # ENTSO-E
    "EntsoeClient",
    "fetch_demo_day_ahead",
    "fetch_demo_generation_mix",
    # yfinance
    "fetch_ticker",
    "fetch_batch",
    # SQLite
    "get_connection",
    "init_db",
    "insert_ohlcv",
    "get_ticker_data",
    "get_summary",
]
