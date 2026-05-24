#!/usr/bin/env python3
"""Shared data-loading and grid-search utilities extracted from demo files.

Provides:
- load_price_data: SQLite → yfinance → synthetic fallback chain
- grid_search_best_params: generic strategy parameter optimization
"""
from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from energy_algorithms.adapters.sqlite_store import (
    get_connection,
    get_ticker_data,
    init_db,
    insert_ohlcv,
)
from energy_algorithms.domain.trading import backtest, synthetic_prices

try:
    from energy_algorithms.adapters.yfinance_fetcher import fetch_ticker as _fetch_ticker
except Exception:
    _fetch_ticker = None


def load_price_data(
    ticker: str,
    with_dates: bool = True,
    db_path: str | None = None,
) -> tuple[np.ndarray, pd.DatetimeIndex] | np.ndarray:
    """Try SQLite → yfinance → synthetic fallback for price data.

    Parameters
    ----------
    ticker : str
        Ticker symbol (e.g., "AAPL").
    with_dates : bool
        If True, return ``(prices, dates)``; else just the prices array.
    db_path : str or None
        Path to SQLite database. Defaults to
        ``<application_dir>/../market_data/market_data.sqlite``.

    Returns
    -------
    tuple[np.ndarray, pd.DatetimeIndex] or np.ndarray
        ``(prices, dates)`` if *with_dates* is True, else *prices* only.
    """
    if db_path is None:
        db_path = os.path.join(
            os.path.dirname(__file__), "..", "market_data", "market_data.sqlite"
        )
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # 1. Try SQLite
    conn = get_connection(db_path)
    init_db(conn)
    try:
        rows = get_ticker_data(conn, ticker)
        if rows:
            conn.close()
            prices = np.array([r["close"] for r in rows], dtype=float)
            dates = pd.to_datetime([r["date"] for r in rows])
            return (prices, dates) if with_dates else prices
    except Exception:
        pass

    # 2. Try yfinance
    if _fetch_ticker is not None:
        print(f"  Fetching {ticker} from Yahoo Finance...")
        data = _fetch_ticker(ticker, period="2y")
        if data:
            insert_ohlcv(conn, data)
            conn.close()
            prices = np.array([r["close"] for r in data], dtype=float)
            dates = pd.to_datetime([r["date"] for r in data])
            return (prices, dates) if with_dates else prices
    conn.close()

    # 3. Fallback — synthetic prices
    print(f"  [WARN] Using synthetic data for {ticker}")
    seed = hash(ticker) % (2**31)
    prices, dates = synthetic_prices(500, seed=seed)
    return (prices, dates) if with_dates else prices


def grid_search_best_params(
    prices: np.ndarray,
    strategy_fn: Callable[..., np.ndarray],
    param_grid: list[dict[str, Any]],
    metric: str = "sharpe",
) -> tuple[dict[str, Any], float]:
    """Grid search for best strategy parameters by backtest metric.

    For each *param_grid* entry, calls ``strategy_fn(prices, **kwargs)``
    to generate a signal, then ``backtest(prices, signal)`` to evaluate
    the chosen *metric*.

    Parameters
    ----------
    prices : ndarray
        1-D array of close prices.
    strategy_fn : callable
        Strategy function that takes ``prices`` plus keyword arguments
        and returns a signal array of the same length.
    param_grid : list[dict]
        List of keyword-argument dicts to try (e.g.
        ``[{"fast": 10, "slow": 30}, {"fast": 20, "slow": 50}]``).
    metric : str
        Backtest result key to maximize (default ``"sharpe"``).

    Returns
    -------
    tuple[dict, float]
        ``(best_kwargs, best_metric_value)``.
    """
    best_value = -float("inf")
    best_kwargs: dict[str, Any] = param_grid[0]
    for kwargs in param_grid:
        signal = strategy_fn(prices, **kwargs)
        bt = backtest(prices, signal)
        val = bt[metric]
        if val > best_value:
            best_value = val
            best_kwargs = kwargs
    return best_kwargs, best_value


__all__ = [
    "load_price_data",
    "grid_search_best_params",
]
