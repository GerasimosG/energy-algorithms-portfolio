#!/usr/bin/env python3
"""
Demo: backtest on 3 assets with SMA crossover, plot equity curves.
"""
from __future__ import annotations

import os

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from energy_algorithms.adapters.sqlite_store import get_connection, get_ticker_data
from energy_algorithms.domain.trading.backtest_engine import backtest
from energy_algorithms.domain.trading.risk_metrics import compute_all
from energy_algorithms.domain.trading.sma_crossover import sma_crossover


def _synthetic_prices(n: int = 500, seed: int = 42) -> tuple[np.ndarray, pd.DatetimeIndex]:
    """Generate plausible synthetic price series for offline demos."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0003, 0.015, n)
    prices = 100 * np.exp(np.cumsum(returns))
    dates = pd.date_range(end="2024-12-31", periods=n)
    return prices.astype(float), dates


def _load_prices(ticker: str) -> tuple[np.ndarray, pd.DatetimeIndex]:
    """Try SQLite first, fall back to synthetic data."""
    db_path = os.path.join(os.path.dirname(__file__), "..", "market_data", "market_data.sqlite")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        conn = get_connection(db_path)
        rows = get_ticker_data(conn, ticker)
        conn.close()
        if rows:
            prices = np.array([r["close"] for r in rows], dtype=float)
            dates = pd.to_datetime([r["date"] for r in rows])
            return prices, dates
    except Exception:
        pass

    print(f"  [WARN] No data for {ticker} — using synthetic data")
    return _synthetic_prices(500, seed=hash(ticker) % (2**31))


def main():
    print("=" * 65)
    print("  Backtester Demo — SMA Crossover on 3 Assets")
    print("=" * 65)

    tickers = ["AAPL", "MSFT", "SPY"]
    results = {}

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    for idx, ticker in enumerate(tickers):
        prices, dates = _load_prices(ticker)

        # Generate signal
        signal = sma_crossover(prices, fast=20, slow=50)

        # Run backtest
        result = backtest(prices, signal)
        eq = result["equity_curve"].values

        # Compute risk metrics
        daily_ret = np.diff(eq) / eq[:-1]
        metrics = compute_all(daily_ret, eq)

        results[ticker] = {"result": result, "metrics": metrics}

        print(f"\n  {ticker}: {len(prices)} days, {result['n_trades']} trades")
        print(f"    Return: {result['total_return']:.2%} | Sharpe: {metrics['sharpe']:.2f} | "
              f"Max DD: {metrics['max_drawdown']:.2%}")

        # Plot
        axes[idx].plot(dates, eq, linewidth=1.5, color="navy")
        axes[idx].fill_between(dates, 100_000, eq, alpha=0.08, color="navy")
        axes[idx].axhline(y=100_000, color="gray", linestyle="--", alpha=0.4)
        axes[idx].set_title(f"{ticker} — SMA Crossover (20/50)", fontsize=12, fontweight="bold")
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
