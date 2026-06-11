#!/usr/bin/env python3
"""
Demo: compare 3 strategies on AAPL with equity curves.
"""
from __future__ import annotations

import os

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt # noqa: E402

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

# Backward-compatible alias for tests that import or monkeypatch this
_load_prices = load_price_data


def _best_params(prices: np.ndarray) -> dict:
 """Grid search all 3 strategies, return best kwargs per strategy."""
 best = {}
 # SMA crossover
 sma_grid = [
 {"fast": f, "slow": s}
 for f, s in [(5, 20), (10, 30), (20, 50), (30, 80), (50, 120), (50, 200)]
 ]
 best_sma, _ = grid_search_best_params(prices, sma_crossover, sma_grid)
 best["sma"] = best_sma

 # Mean reversion
 mr_grid = [
 {"window": w, "n_std": n}
 for w, n in [(10, 1.5), (15, 2.0), (20, 2.0), (20, 2.5), (30, 2.0), (30, 2.5)]
 ]
 best_mr, _ = grid_search_best_params(prices, mean_reversion, mr_grid)
 best["mr"] = best_mr

 # Momentum
 mom_grid = [
 {"lookback": lb, "hold": h, "threshold": 0.01}
 for lb, h in [(20, 10), (40, 20), (60, 20), (80, 30), (120, 30)]
 ]
 best_mom, _ = grid_search_best_params(prices, momentum, mom_grid)
 best["mom"] = best_mom

 return best


def main():
 print("=" * 65)
 print(" Strategies Demo — 3 Strategies Compared (optimized)")
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
 print(f"\n {name} {params_str}")
 print(f" Return: {result['total_return']:.2%} | Sharpe: {result['sharpe']:.2f} | "
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

 print(f"\n Plot saved: {plot_path}")
 print(f"\n{'=' * 65}")
 print(" All 3 strategies compared — equity curves attached.")
 print(f"{'=' * 65}")


if __name__ == "__main__":
 main()
