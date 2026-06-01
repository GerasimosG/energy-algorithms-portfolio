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

from energy_algorithms.adapters.sqlite_store import (
    get_connection,
    get_ticker_data,
    init_db,
    insert_ohlcv,
)
from energy_algorithms.domain.trading import backtest, compute_all, sma_crossover, synthetic_prices

try:
    from energy_algorithms.adapters.yfinance_fetcher import fetch_ticker as _fetch_ticker
except Exception:
    _fetch_ticker = None


def _load_prices(ticker: str) -> tuple[np.ndarray, pd.DatetimeIndex]:
    """Try SQLite → yfinance → synthetic fallback."""
    db_path = os.path.join(os.path.dirname(__file__), "..", "market_data", "market_data.sqlite")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # 1. Try SQLite
    conn = get_connection(db_path)
    init_db(conn)
    try:
        rows = get_ticker_data(conn, ticker)
        if rows:
            conn.close()
            prices = np.array([r["close"] for r in rows], dtype=float)
            dates = pd.to_datetime([r["date"] for r in rows])
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
            return prices, dates
    conn.close()

    # 3. Fallback
    print(f"  [WARN] Using synthetic data for {ticker}")
    seed = hash(ticker) % (2**31)
    return synthetic_prices(500, seed=seed)


def _best_sma_params(prices: np.ndarray) -> tuple[int, int]:
    """Grid search over SMA param range, return best by Sharpe."""
    best_sharpe = -999
    best = (20, 50)
    param_sets = [(f, s) for f in [5, 10, 20, 30, 50, 80]
                  for s in [20, 30, 50, 80, 120, 200]
                  if f < s]
    for fast, slow in param_sets:
        signal = sma_crossover(prices, fast=fast, slow=slow)
        bt = backtest(prices, signal)
        if bt["sharpe"] > best_sharpe:
            best_sharpe = bt["sharpe"]
            best = (fast, slow)
    return best


def main():
    print("=" * 65)
    print("  Backtester Demo — SMA Crossover (optimized params)")
    print("=" * 65)

    tickers = ["AAPL", "MSFT", "SPY"]
    results = {}

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    for idx, ticker in enumerate(tickers):
        prices, dates = _load_prices(ticker)

        # Grid-search best SMA parameters
        fast, slow = _best_sma_params(prices)
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
