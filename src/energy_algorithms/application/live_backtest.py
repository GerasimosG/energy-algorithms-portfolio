#!/usr/bin/env python3
"""
Live YFinance Backtest Demo — Fetch real AAPL data, run all 3 strategies,
produce a professional comparison report.
"""
from __future__ import annotations

import os

import numpy as np

from energy_algorithms.adapters.sqlite_store import (
    get_connection,
    get_ticker_data,
    init_db,
    insert_ohlcv,
)
from energy_algorithms.domain.trading import (
    backtest,
    mean_reversion,
    momentum,
    sma_crossover,
    synthetic_prices,
)

try:
    from energy_algorithms.adapters.yfinance_fetcher import fetch_ticker
except Exception:
    fetch_ticker = None  # type: ignore[assignment]


def _load_or_fetch(ticker: str) -> np.ndarray:
    """Try SQLite first, then yfinance, fall back to synthetic with warning."""
    db_path = os.path.join(os.path.dirname(__file__), "market_data.sqlite")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = get_connection(db_path)
    init_db(conn)

    rows = get_ticker_data(conn, ticker)
    if rows:
        conn.close()
        return np.array([r["close"] for r in rows], dtype=float)

    # Not in DB — fetch live
    if fetch_ticker is not None:
        print(f"  {ticker} not found in SQLite, fetching from Yahoo Finance...")
        data = fetch_ticker(ticker, period="2y")
        if data:
            inserted = insert_ohlcv(conn, data)
            print(f"  Stored {inserted} rows for {ticker}")
            conn.close()
            return np.array([r["close"] for r in data], dtype=float)

    conn.close()
    # Fall back to synthetic
    print(f"  [WARN] Could not fetch {ticker} — using synthetic data")
    prices, _ = synthetic_prices(500, seed=42)
    return prices


def _best_params(prices: np.ndarray, param_grid: list[tuple]) -> tuple:
    """Grid search over param grid, return best by Sharpe."""
    best_sharpe = -999
    best_params = param_grid[0]
    for params in param_grid:
        signal = sma_crossover(prices, *params)
        bt = backtest(prices, signal)
        if bt["sharpe"] > best_sharpe:
            best_sharpe = bt["sharpe"]
            best_params = params
    return best_params


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

    # ── 2. Run strategies with multiple parameter sets ────────────────
    strategy_configs = [
        ("Momentum",        momentum,        [{"lookback": lb, "threshold": 0.01}
                                               for lb in [40, 60, 80, 120]]),
        ("Mean Reversion",  mean_reversion,  [{"window": w, "n_std": 2.0}
                                               for w in [10, 15, 20, 30]]),
        ("SMA Crossover",   sma_crossover,   [{"fast": f, "slow": s}
                                               for f, s in [(10, 30), (20, 50), (30, 80), (50, 150)]]),
    ]

    results = {}
    for name, func, configs in strategy_configs:
        best_sharpe = -999
        best_result = None
        best_kwargs = {}
        for kwargs in configs:
            signal = func(prices, **kwargs)
            bt = backtest(prices, signal)
            if bt["sharpe"] > best_sharpe:
                best_sharpe = bt["sharpe"]
                best_result = bt
                best_kwargs = kwargs
        results[name] = {**best_result, "_params": best_kwargs}

    # ── 3. Print comparison table ─────────────────────────────────────
    header = f"  {'Strategy':<22s} {'Params':<20s} {'Return':>8s} {'Sharpe':>7s} {'Max DD':>7s} {'Trades':>7s} {'Win%':>7s}"
    sep = "  " + "-" * 85
    print(sep)
    print(header)
    print(sep)

    for name, bt in results.items():
        params_str = str(bt["_params"])
        print(f"  {name:<22s} {params_str:<20s} {bt['total_return']:7.1%}  {bt['sharpe']:6.2f}  "
              f"{bt['max_drawdown']:6.1%}  {bt['n_trades']:5d}  "
              f"{bt['win_rate']:6.0%}")

    print(sep)
    best = max(results, key=lambda k: results[k]["sharpe"])
    print(f"  ★ Best risk-adjusted: {best} (Sharpe: {results[best]['sharpe']:.2f}, "
          f"Return: {results[best]['total_return']:.1%})")
    print("=" * 72)
    print("  Demo complete — all strategies backtested.")
    return results


def main():
    """Entry point for CLI execution."""
    demo_live_backtest()


if __name__ == "__main__":
    main()
