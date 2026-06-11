"""Shared data-loading utilities for demo scripts.

Provides a single source of truth for:
- Price data loading (SQLite → yfinance → synthetic fallback)
- Grid search for strategy parameter optimisation
- ENTSO-E client factory (from config)
"""
from __future__ import annotations

import os
from typing import Any

import numpy as np
import pandas as pd

from energy_algorithms.adapters.config import ENTSOE_API_KEY
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
 """Try SQLite → yfinance → synthetic fallback chain.

 Parameters
 ----------
 ticker : str
 Stock ticker (e.g. ``'AAPL'``).
 with_dates : bool
 If ``True`` (default) return ``(prices, dates)``.
 If ``False`` return only ``prices``.
 db_path : str or None
 Path to SQLite database. If ``None`` defaults to
 ``<package_dir>/market_data/market_data.sqlite``.

 Returns
 -------
 (prices, dates) if *with_dates* else prices
 """
 if db_path is None:
 db_path = os.path.join(
 os.path.dirname(__file__), "..", "market_data", "market_data.sqlite",
 )
 os.makedirs(os.path.dirname(db_path), exist_ok=True)

 conn = get_connection(db_path)
 init_db(conn)

 # 1. Try SQLite
 try:
 rows = get_ticker_data(conn, ticker)
 if rows:
 conn.close()
 prices = np.array([r["close"] for r in rows], dtype=float)
 dates = pd.to_datetime([r["date"] for r in rows])
 print(f" Loaded {len(prices)} days of real {ticker} data")
 return (prices, dates) if with_dates else prices
 except Exception:
 pass

 # 2. Try yfinance
 if _fetch_ticker is not None:
 print(f" Fetching {ticker} from Yahoo Finance...")
 data = _fetch_ticker(ticker, period="2y")
 if data:
 insert_ohlcv(conn, data)
 conn.close()
 prices = np.array([r["close"] for r in data], dtype=float)
 dates = pd.to_datetime([r["date"] for r in data])
 print(f" Loaded {len(prices)} days of real {ticker} data")
 return (prices, dates) if with_dates else prices
 conn.close()

 # 3. Fallback — synthetic data
 print(f" [WARN] Using synthetic data for {ticker}")
 seed = hash(ticker) % (2**31)
 prices, dates = synthetic_prices(500, seed=seed)
 return (prices, dates) if with_dates else prices


def grid_search_best_params(
 prices: np.ndarray,
 strategy_class: Any,
 param_grid: list[dict[str, Any]],
 metric: str = "sharpe",
) -> tuple[dict[str, Any], float]:
 """Grid search over *param_grid*, return best params and best metric value.

 Parameters
 ----------
 prices : np.ndarray
 Price series.
 strategy_class : callable
 A strategy function that takes ``prices`` as first argument
 and ``**kwargs`` from each param dict.
 param_grid : list[dict]
 List of parameter dicts to try.
 metric : str
 Key in the backtest result dict to maximise (default ``'sharpe'``).

 Returns
 -------
 (best_params, best_metric_value)
 """
 best_value = -999.0
 best_params = param_grid[0]
 for params in param_grid:
 signal = strategy_class(prices, **params)
 bt = backtest(prices, signal)
 val = bt.get(metric, -999.0)
 if val > best_value:
 best_value = val
 best_params = params
 return best_params, best_value


def create_entsoe_client(timeout: int = 30):
 """Create an ``EntsoeClient`` using the configured API key.

 Reads ``ENTSOE_API_KEY`` from :mod:`energy_algorithms.adapters.config`
 (which in turn reads it from the environment or a ``.env`` file).

 Parameters
 ----------
 timeout : int
 Request timeout in seconds (default 30).

 Returns
 -------
 EntsoeClient or None
 ``None`` when no API key is configured.
 """
 if not ENTSOE_API_KEY:
 return None
 from energy_algorithms.adapters.entsoe_client import EntsoeClient

 return EntsoeClient(api_key=ENTSOE_API_KEY, timeout=timeout)
