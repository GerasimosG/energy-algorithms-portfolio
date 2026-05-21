"""Tests for application demos — covers orchestration modules.

Tests demo entry points that wire domain + adapters together.
All demos use deterministic demo data (no live API calls).
"""

from __future__ import annotations

import numpy as np
import pytest

from energy_algorithms.application.energy_data_demo import demo_energy_data


# ── energy_data_demo ─────────────────────────────────────────────────

def test_demo_energy_data_basic():
    """demo_energy_data returns expected structure with prices and generation."""
    result = demo_energy_data()
    assert "prices" in result
    assert "generation" in result
    assert result["prices"]["area"] is not None
    assert result["generation"]["total_mw"] > 0


# ── strategies_demo helpers ──────────────────────────────────────────

def test_strategies_demo_best_params():
    """_best_params finds parameter combinations for all 3 strategies."""
    from energy_algorithms.application.strategies_demo import _best_params
    from energy_algorithms.domain.trading import synthetic_prices

    prices, _dates = synthetic_prices(200, seed=42)
    best = _best_params(prices)
    assert "sma" in best
    assert "mr" in best
    assert "mom" in best
    assert len(best["sma"]) == 2
    assert len(best["mr"]) == 2
    assert len(best["mom"]) == 3


# ── optimization_demo ────────────────────────────────────────────────

def test_optimization_demo_main_runs():
    """optimization_demo.main() runs all three LP problems successfully."""
    from energy_algorithms.application.optimization_demo import main as opt_main

    # Capture stdout to avoid noise, just verify it doesn't crash
    import io
    import sys
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        opt_main()
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    assert "Transportation" in output
    assert "Portfolio" in output
    assert "Unit Commitment" in output
    assert "Optimal" in output


# ── markets_demo ─────────────────────────────────────────────────────

def test_markets_demo_main_runs():
    """markets_demo.main() runs PCR, block orders, FBMC, market clearing."""
    from energy_algorithms.application.markets_demo import main as markets_main

    import io
    import sys
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        markets_main()
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    assert "PCR" in output or "Market" in output
    assert "Optimal" in output


# ── european_coupling ────────────────────────────────────────────────

def test_european_coupling_functions_exist():
    """European coupling module has expected functions."""
    from energy_algorithms.application.european_coupling import (
        build_demand_curve,
        fetch_european_prices,
        run_european_coupling,
    )
    assert callable(build_demand_curve)
    assert callable(fetch_european_prices)
    assert callable(run_european_coupling)


# ── live_pipeline ────────────────────────────────────────────────────

def test_live_pipeline_demo_runs():
    """live_pipeline demo runs using demo data (no API key)."""
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    import io
    import sys
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        result = demo_live_pipeline()
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    assert isinstance(result, dict)


# ── market_data_demo ─────────────────────────────────────────────────

def test_market_data_demo_main_runs():
    """market_data_demo.main() fetches and stores data (will use demo data if available)."""
    from energy_algorithms.application.market_data_demo import main as mdata_main

    import io
    import sys
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        mdata_main()
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    assert "Market Data" in output or "Fetching" in output


# ── live_backtest ────────────────────────────────────────────────────

def test_live_backtest_demo_runs():
    """demo_live_backtest falls back to synthetic data and returns results."""
    from energy_algorithms.application.live_backtest import demo_live_backtest

    import io
    import sys
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        result = demo_live_backtest()
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    assert isinstance(result, dict)
    # Should have results for at least one strategy
    assert len(result) > 0


# ── trading_demo ─────────────────────────────────────────────────────

def test_trading_demo_best_sma_params():
    """_best_sma_params finds optimal SMA parameters via grid search."""
    from energy_algorithms.application.trading_demo import _best_sma_params
    from energy_algorithms.domain.trading import synthetic_prices

    prices, _dates = synthetic_prices(200, seed=42)
    fast, slow = _best_sma_params(prices)
    assert isinstance(fast, int)
    assert isinstance(slow, int)
    assert fast < slow  # SMA param invariant


def test_trading_demo_load_prices_fallback():
    """_load_prices falls back to synthetic when no DB/yfinance."""
    from energy_algorithms.application.trading_demo import _load_prices

    import io
    import sys
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        prices, dates = _load_prices("AAPL")
    finally:
        sys.stdout = old_stdout
    assert len(prices) > 200  # real or synthetic — both give substantial data
    assert len(dates) > 200


def test_trading_demo_main_runs(monkeypatch, capsys):
    """trading_demo.main() runs with synthetic data and prints results."""
    from energy_algorithms.application.trading_demo import main as trading_main

    # main() uses _load_prices which falls back to synthetic
    trading_main()
    captured = capsys.readouterr()
    assert "Backtester Demo" in captured.out or "SMA Crossover" in captured.out
    assert "Return" in captured.out


def test_trading_demo_main_prints_metrics(monkeypatch, capsys):
    """trading_demo.main() prints risk metrics for each ticker."""
    from energy_algorithms.application.trading_demo import main as trading_main

    trading_main()
    captured = capsys.readouterr()
    assert "Sharpe" in captured.out
    assert "Max DD" in captured.out


# ── strategies_demo (extended) ──────────────────────────────────────


def test_strategies_demo_load_prices_fallback():
    """strategies_demo._load_prices falls back to synthetic data."""
    from energy_algorithms.application.strategies_demo import _load_prices
    from energy_algorithms.domain.trading import synthetic_prices

    prices, dates = _load_prices("UNKNOWN_TEST_TICKER123")
    assert len(prices) > 0
    assert len(dates) > 0


def test_strategies_demo_main_runs(monkeypatch, capsys):
    """strategies_demo.main() runs and produces strategy output."""
    from energy_algorithms.application.strategies_demo import main as strategies_main

    strategies_main()
    captured = capsys.readouterr()
    assert "Strategies Demo" in captured.out
    assert "SMA Crossover" in captured.out or "Bollinger" in captured.out


def test_strategies_demo_main_prints_best_params(monkeypatch, capsys):
    """strategies_demo.main() prints best parameters per strategy."""
    from energy_algorithms.application.strategies_demo import main as strategies_main

    strategies_main()
    captured = capsys.readouterr()
    assert "Return" in captured.out
    assert "Sharpe" in captured.out


def test_strategies_demo_best_params_returns_valid_shapes():
    """_best_params returns dict with correct strategy param keys."""
    from energy_algorithms.application.strategies_demo import _best_params
    from energy_algorithms.domain.trading import synthetic_prices

    prices, _dates = synthetic_prices(200, seed=42)
    best = _best_params(prices)
    assert "sma" in best
    assert "mr" in best
    assert "mom" in best

    # Individual param dicts
    assert "fast" in best["sma"]
    assert "slow" in best["sma"]
    assert "window" in best["mr"]
    assert "n_std" in best["mr"]
    assert "lookback" in best["mom"]
    assert "hold" in best["mom"]
