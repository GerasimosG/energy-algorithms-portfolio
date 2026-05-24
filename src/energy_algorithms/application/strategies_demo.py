#!/usr/bin/env python3
"""
Demo: compare 3 strategies on AAPL with equity curves.
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

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


def main():
    print("=" * 65)
    print("  Strategies Demo — 3 Strategies Compared (optimized)")
    print("=" * 65)

    prices, dates = load_price_data("AAPL")

    # Grid-search best params for each strategy
    sma_kwargs, _ = grid_search_best_params(prices, sma_crossover, [
        {"fast": 5, "slow": 20},
        {"fast": 10, "slow": 30},
        {"fast": 20, "slow": 50},
        {"fast": 30, "slow": 80},
        {"fast": 50, "slow": 120},
        {"fast": 50, "slow": 200},
    ])
    mr_kwargs, _ = grid_search_best_params(prices, mean_reversion, [
        {"window": 10, "n_std": 1.5},
        {"window": 15, "n_std": 2.0},
        {"window": 20, "n_std": 2.0},
        {"window": 20, "n_std": 2.5},
        {"window": 30, "n_std": 2.0},
        {"window": 30, "n_std": 2.5},
    ])
    mom_kwargs, _ = grid_search_best_params(prices, momentum, [
        {"lookback": 20, "hold": 10, "threshold": 0.01},
        {"lookback": 40, "hold": 20, "threshold": 0.01},
        {"lookback": 60, "hold": 20, "threshold": 0.01},
        {"lookback": 80, "hold": 30, "threshold": 0.01},
        {"lookback": 120, "hold": 30, "threshold": 0.01},
    ])

    best = {"sma": sma_kwargs, "mr": mr_kwargs, "mom": mom_kwargs}

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
