#!/usr/bin/env python3
"""
Live YFinance Backtest Demo — Fetch real AAPL data, run all 3 strategies,
produce a professional comparison report.

Run: .venv/bin/python market_data/live_demo.py  (from repo root)
Or:  python -c "import sys; sys.path.insert(0,'..'); import energy_algorithms.adapters.live_demo"
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np                                    # noqa: E402

from energy_algorithms.adapters.yfinance_fetcher import fetch_ticker          # noqa: E402
from energy_algorithms.adapters.sqlite_store import (                       # noqa: E402
    get_connection, init_db, insert_ohlcv, get_ticker_data,
)
from energy_algorithms.domain.trading.backtest_engine import backtest                # noqa: E402
from energy_algorithms.domain.trading.momentum import momentum              # noqa: E402
from energy_algorithms.domain.trading.mean_reversion import mean_reversion  # noqa: E402
from energy_algorithms.domain.trading.sma_crossover import sma_crossover    # noqa: E402


def _load_or_fetch(ticker: str) -> np.ndarray:
    """Try SQLite first, then yfinance, fall back to synthetic with warning."""
    db_path = os.path.join(os.path.dirname(__file__), "market_data.sqlite")
    conn = get_connection(db_path)
    init_db(conn)

    rows = get_ticker_data(conn, ticker)
    if rows:
        conn.close()
        return np.array([r["close"] for r in rows], dtype=float)

    # Not in DB — fetch live
    print(f"  {ticker} not found in SQLite, fetching from Yahoo Finance...")
    data = fetch_ticker(ticker, period="2y")
    if data:
        inserted = insert_ohlcv(conn, data)
        print(f"  Stored {inserted} rows for {ticker}")
        conn.close()
        return np.array([r["close"] for r in data], dtype=float)

    conn.close()
    # Offline / fetch failed — fall back to synthetic
    print(f"  [WARN] Could not fetch {ticker} (offline?). Generating 500 synthetic prices.")
    return _synthetic_prices(500)


def _synthetic_prices(n: int = 500, seed: int = 42) -> np.ndarray:
    """Generate plausible synthetic price series for offline demos."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0003, 0.015, n)
    prices = 100 * np.exp(np.cumsum(returns))
    return prices.astype(float)


def demo_live_backtest() -> dict:
    """
    Fetch real AAPL data, run all 3 strategies, return comparison.

    Returns dict with results keyed by strategy name.
    """
    print("=" * 72)
    print("  Live YFinance Backtest — AAPL")
    print("=" * 72)

    # ── 1. Load data ──────────────────────────────────────────────────
    prices = _load_or_fetch("AAPL")
    print(f"  Loaded {len(prices)} price points\n")

    # ── 2. Run strategies ─────────────────────────────────────────────
    strategies = [
        ("Momentum",             momentum,         {"lookback": 60}),
        ("Mean Reversion",       mean_reversion,   {"window": 20}),
        ("SMA Crossover",        sma_crossover,    {"fast": 20, "slow": 50}),
    ]

    results = {}
    for name, func, kwargs in strategies:
        signal = func(prices, **kwargs)
        bt = backtest(prices, signal)
        results[name] = bt

    # ── 3. Print comparison table ─────────────────────────────────────
    header = f"  {'Strategy':<20s} {'Return':>8s} {'Sharpe':>7s} {'Max DD':>7s} {'Trades':>7s} {'Win%':>7s}"
    sep = "  " + "-" * 65
    print(sep)
    print(header)
    print(sep)

    for name, bt in results.items():
        print(f"  {name:<20s} {bt['total_return']:7.1%}  {bt['sharpe']:6.2f}  "
              f"{bt['max_drawdown']:6.1%}  {bt['n_trades']:5d}  "
              f"{bt['win_rate']:6.0%}")

    print(sep)
    best = max(results, key=lambda k: results[k]["sharpe"])
    print(f"  ★ Best risk-adjusted: {best} (Sharpe: {results[best]['sharpe']:.2f})")
    print("=" * 72)
    print("  Demo complete — all strategies backtested.")
    return results


def main():
    """Entry point for CLI execution."""
    demo_live_backtest()


if __name__ == "__main__":
    main()
