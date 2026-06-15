#!/usr/bin/env python3
"""
Live YFinance Backtest Demo — Fetch real AAPL data, run all 3 strategies,
produce a professional comparison report.
"""
from __future__ import annotations

import os

import numpy as np

from energy_algorithms.application.data_loader import (
    grid_search_best_params,
    load_price_data,
)
from energy_algorithms.domain.trading import (
    backtest,
    mean_reversion,
    momentum,
    sma_crossover,
)


def _load_or_fetch(ticker: str) -> np.ndarray:
    """Try SQLite first, then yfinance, fall back to synthetic with warning."""
    db_path = os.path.join(os.path.dirname(__file__), "market_data.sqlite")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return load_price_data(ticker, with_dates=False, db_path=db_path)


def _best_params(prices: np.ndarray, param_grid: list[tuple]) -> tuple:
    """Grid search over param grid, return best by Sharpe.

    Backward-compatible wrapper for tests; accepts tuples and delegates
    to :func:`grid_search_best_params`.
    """
    dict_grid = [{"fast": f, "slow": s} for f, s in param_grid]
    best_params, _ = grid_search_best_params(prices, sma_crossover, dict_grid)
    return best_params["fast"], best_params["slow"]


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
        best_kwargs, _ = grid_search_best_params(prices, func, configs)
        signal = func(prices, **best_kwargs)
        bt = backtest(prices, signal)
        results[name] = {**bt, "_params": best_kwargs}

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
