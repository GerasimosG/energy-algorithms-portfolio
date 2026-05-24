"""Adapters layer — concrete implementations of ports.

ENTSO-E API client, yfinance data fetcher, SQLite store,
and application configuration.
"""
from __future__ import annotations

from energy_algorithms.adapters.config import ENTSOE_API_KEY, create_entsoe_client
from energy_algorithms.adapters.entsoe_client import (
    EntsoeClient,
    fetch_demo_day_ahead,
    fetch_demo_generation_mix,
)
from energy_algorithms.adapters.pulp_solver import PuLPSolverAdapter  # noqa: F401
from energy_algorithms.adapters.sqlite_store import (
    get_connection,
    get_summary,
    get_ticker_data,
    init_db,
    insert_ohlcv,
)

try:
    from energy_algorithms.adapters.yfinance_fetcher import fetch_batch, fetch_ticker
except ImportError:
    fetch_batch = None  # type: ignore[assignment]
    fetch_ticker = None  # type: ignore[assignment]

__all__ = [
    "PuLPSolverAdapter",
    # Config
    "ENTSOE_API_KEY",
    "create_entsoe_client",
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
