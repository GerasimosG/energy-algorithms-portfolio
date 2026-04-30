#!/usr/bin/env python3
"""
Demo: compare 3 strategies on AAPL with equity curves.
"""
from __future__ import annotations

import os

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from energy_algorithms.adapters.sqlite_store import get_connection, get_ticker_data, init_db, insert_ohlcv
from energy_algorithms.domain.trading import (
    backtest,
    mean_reversion,
    momentum,
    sma_crossover,
    synthetic_prices,
)

try:
    from energy_algorithms.adapters.yfinance_fetcher import fetch_ticker as _fetch_ticker
except Exception:
    _fetch_ticker = None


def _load_prices(ticker: str) -> tuple[np.ndarray, pd.DatetimeIndex]:
    """Try SQLite → yfinance → synthetic fallback."""
    db_path = os.path.join(os.path.dirname(__file__), "..", "market_data", "market_data.sqlite")
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
            print(f"\n  Loaded {len(prices)} days of real {ticker} data")
            return prices, dates
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
            print(f"  Loaded {len(prices)} days of real {ticker} data")
            return prices, dates
    conn.close()

    # 3. Fallback
    print(f"  [WARN] Using synthetic data for {ticker}")
    seed = hash(ticker) % (2**31)
    return synthetic_prices(500, seed=seed)


def _best_params(prices: np.ndarray) -> dict:
    """Grid search all 3 strategies, return best kwargs per strategy."""
    best = {}
    # SMA crossover
    best_sharpe = -999
    best_sma = {"fast": 20, "slow": 50}
    for f, s in [(5, 20), (10, 30), (20, 50), (30, 80), (50, 120), (50, 200)]:
        sig = sma_crossover(prices, fast=f, slow=s)
        bt = backtest(prices, sig)
        if bt["sharpe"] > best_sharpe:
            best_sharpe = bt["sharpe"]
            best_sma = {"fast": f, "slow": s}
    best["sma"] = best_sma

    # Mean reversion
    best_sharpe = -999
    best_mr = {"window": 20, "n_std": 2.0}
    for w, n in [(10, 1.5), (15, 2.0), (20, 2.0), (20, 2.5), (30, 2.0), (30, 2.5)]:
        sig = mean_reversion(prices, window=w, n_std=n)
        bt = backtest(prices, sig)
        if bt["sharpe"] > best_sharpe:
            best_sharpe = bt["sharpe"]
            best_mr = {"window": w, "n_std": n}
    best["mr"] = best_mr

    # Momentum
    best_sharpe = -999
    best_mom = {"lookback": 60, "hold": 20, "threshold": 0.02}
    for lb, h in [(20, 10), (40, 20), (60, 20), (80, 30), (120, 30)]:
        sig = momentum(prices, lookback=lb, hold=h, threshold=0.01)
        bt = backtest(prices, sig)
        if bt["sharpe"] > best_sharpe:
            best_sharpe = bt["sharpe"]
            best_mom = {"lookback": lb, "hold": h, "threshold": 0.01}
    best["mom"] = best_mom

    return best


def main():
    print("=" * 65)
    print("  Strategies Demo — 3 Strategies Compared (optimized)")
    print("=" * 65)

    prices, dates = _load_prices("AAPL")
    best = _best_params(prices)

    strategies = [
        ("SMA Crossover", sma_crossover, best["sma"]),
        ("Bollinger Mean Rev", mean_reversion, best["mr"]),
        ("Momentum", momentum, best["mom"]),
    ]

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    for idx, (name, func, kwargs) in enumerate(strategies):
        signal = func(prices, **kwargs)
        result = backtest(prices, signal)
        eq = result["equity_curve"]

        params_str = str(kwargs)
        print(f"\n  {name} {params_str}")
        print(f"    Return: {result['total_return']:.2%} | Sharpe: {result['sharpe']:.2f} | "
              f"Trades: {result['n_trades']} ({result['win_rate']:.0%} win)")

        axes[idx].plot(dates, eq, linewidth=1.5, color="navy")
        axes[idx].fill_between(dates, 100_000, eq, alpha=0.08, color="navy")
        axes[idx].axhline(y=100_000, color="gray", linestyle="--", alpha=0.4)
        axes[idx].set_title(f"{name} {params_str}", fontsize=12, fontweight="bold")
        axes[idx].set_ylabel("Portfolio ($)")
        axes[idx].grid(True, alpha=0.3)

        stats = f"Ret: {result['total_return']:.1%} | Sharpe: {result['sharpe']:.2f} | DD: {result['max_drawdown']:.1%}"
        axes[idx].text(0.02, 0.93, stats, transform=axes[idx].transAxes,
                       fontsize=8, va="top",
                       bbox=dict(boxstyle="round,pad=0.3", facecolor="wheat", alpha=0.6))

    axes[-1].set_xlabel("Date")
    plt.tight_layout()

    plot_dir = os.path.join(os.path.dirname(__file__), "..", "notebooks", "plots")
    os.makedirs(plot_dir, exist_ok=True)
    plot_path = os.path.join(plot_dir, "strategies_comparison.png")
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"\n  Plot saved: {plot_path}")
    print(f"\n{'=' * 65}")
    print("  All 3 strategies compared — equity curves attached.")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    main()
