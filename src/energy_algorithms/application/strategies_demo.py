#!/usr/bin/env python3
"""
Demo: compare 3 strategies on AAPL with equity curves.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from energy_algorithms.adapters.sqlite_store import get_connection, get_ticker_data
from energy_algorithms.domain.trading.backtest_engine import backtest
from energy_algorithms.domain.trading.sma_crossover import sma_crossover
from energy_algorithms.domain.trading.mean_reversion import mean_reversion
from energy_algorithms.domain.trading.momentum import momentum


def main():
    print("=" * 65)
    print("  Strategies Demo — 3 Strategies Compared")
    print("=" * 65)

    db_path = os.path.join(os.path.dirname(__file__), "..", "market_data", "market_data.sqlite")
    conn = get_connection(db_path)
    rows = get_ticker_data(conn, "AAPL")
    conn.close()

    prices = np.array([r["close"] for r in rows], dtype=float)
    dates = pd.to_datetime([r["date"] for r in rows])
    print(f"\n  Loaded {len(prices)} days of AAPL")

    strategies = [
        ("SMA Crossover (20/50)", sma_crossover, {"fast": 20, "slow": 50}),
        ("Bollinger Mean Rev (20,2)", mean_reversion, {"window": 20, "n_std": 2.0}),
        ("Momentum (60/20)", momentum, {"lookback": 60, "hold": 20}),
    ]

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    for idx, (name, func, kwargs) in enumerate(strategies):
        signal = func(prices, **kwargs)
        result = backtest(prices, signal)
        eq = result["equity_curve"]

        print(f"\n  {name}")
        print(f"    Return: {result['total_return']:.2%} | Sharpe: {result['sharpe']:.2f} | "
              f"Trades: {result['n_trades']} ({result['win_rate']:.0%} win)")

        axes[idx].plot(dates, eq, linewidth=1.5, color="navy")
        axes[idx].fill_between(dates, 100_000, eq, alpha=0.08, color="navy")
        axes[idx].axhline(y=100_000, color="gray", linestyle="--", alpha=0.4)
        axes[idx].set_title(name, fontsize=12, fontweight="bold")
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
