#!/usr/bin/env python3
"""
Demo: backtest on 3 assets with SMA crossover, plot equity curves.
"""
from __future__ import annotations

import os

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from energy_algorithms.application.data_loader import (
    grid_search_best_params,
    load_price_data,
)
from energy_algorithms.domain.trading import backtest, compute_all, sma_crossover


def main():
    print("=" * 65)
    print("  Backtester Demo — SMA Crossover (optimized params)")
    print("=" * 65)

    tickers = ["AAPL", "MSFT", "SPY"]
    results = {}

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    # Build param grid once
    sma_param_grid = [
        {"fast": f, "slow": s}
        for f in [5, 10, 20, 30, 50, 80]
        for s in [20, 30, 50, 80, 120, 200]
        if f < s
    ]

    for idx, ticker in enumerate(tickers):
        prices, dates = load_price_data(ticker)

        # Grid-search best SMA parameters
        best_kwargs, _ = grid_search_best_params(
            prices, sma_crossover, sma_param_grid
        )
        fast, slow = best_kwargs["fast"], best_kwargs["slow"]
        signal = sma_crossover(prices, fast=fast, slow=slow)

        # Run backtest
        result = backtest(prices, signal)
        eq = result["equity_curve"].values

        # Compute risk metrics
        daily_ret = np.diff(eq) / eq[:-1]
        metrics = compute_all(daily_ret, eq)

        results[ticker] = {"result": result, "metrics": metrics, "params": (fast, slow)}

        print(f"\n  {ticker}: {len(prices)} days, SMA({fast},{slow})")
        print(f"    Return: {result['total_return']:.2%} | Sharpe: {metrics['sharpe']:.2f} | "
              f"Max DD: {metrics['max_drawdown']:.2%}")

        # Plot
        axes[idx].plot(dates, eq, linewidth=1.5, color="navy")
        axes[idx].fill_between(dates, 100_000, eq, alpha=0.08, color="navy")
        axes[idx].axhline(y=100_000, color="gray", linestyle="--", alpha=0.4)
        axes[idx].set_title(f"{ticker} — SMA({fast},{slow}) [optimized]", fontsize=12, fontweight="bold")
        axes[idx].set_ylabel("Portfolio ($)")
        axes[idx].grid(True, alpha=0.3)

        stats = f"Ret: {result['total_return']:.1%} | SR: {metrics['sharpe']:.2f} | DD: {metrics['max_drawdown']:.1%}"
        axes[idx].text(0.02, 0.93, stats, transform=axes[idx].transAxes,
                       fontsize=8, va="top",
                       bbox=dict(boxstyle="round,pad=0.3", facecolor="wheat", alpha=0.6))

    axes[-1].set_xlabel("Date")
    plt.tight_layout()

    plot_dir = os.path.join(os.path.dirname(__file__), "..", "notebooks", "plots")
    os.makedirs(plot_dir, exist_ok=True)
    plot_path = os.path.join(plot_dir, "equity_curves.png")
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"\n  Plot saved: {plot_path}")
    print(f"\n{'=' * 65}")
    print("  Backtester + risk metrics demo complete.")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    main()
