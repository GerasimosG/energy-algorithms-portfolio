"""Tests for application demo modules — function-level tests for moved utilities."""

from __future__ import annotations

import io
import sys

import numpy as np
import pandas as pd

from tests.test_lightweight_coverage import DummyAxis, fake_backtest_result


def patch_plotting(monkeypatch, module, tmp_path):
    """Patch matplotlib calls in demo modules."""
    axes = [DummyAxis(), DummyAxis(), DummyAxis()]
    monkeypatch.setattr(module.plt, "subplots", lambda *a, **kw: (object(), axes))
    monkeypatch.setattr(module.plt, "tight_layout", lambda: None)
    monkeypatch.setattr(module.plt, "savefig", lambda *a, **kw: None)
    monkeypatch.setattr(module.plt, "close", lambda: None)
    monkeypatch.setattr(module.os.path, "dirname", lambda path: str(tmp_path))


# ── strategies_demo ──────────────────────────────────────────────────

def test_strategies_demo_best_params():
    """grid_search_best_params finds parameter combinations for all 3 strategies."""
    from energy_algorithms.application.data_loader import grid_search_best_params
    from energy_algorithms.domain.trading import (
        mean_reversion,
        momentum,
        sma_crossover,
        synthetic_prices,
    )

    prices, _dates = synthetic_prices(200, seed=42)

    # Test SMA param search
    sma_kwargs, _ = grid_search_best_params(prices, sma_crossover, [
        {"fast": 5, "slow": 20}, {"fast": 10, "slow": 30}, {"fast": 30, "slow": 80},
    ])
    assert "fast" in sma_kwargs
    assert "slow" in sma_kwargs
    assert sma_kwargs["fast"] < sma_kwargs["slow"]

    # Test momentum param search
    mom_kwargs, _ = grid_search_best_params(prices, momentum, [
        {"lookback": 1, "hold": 1, "threshold": 0.01},
        {"lookback": 5, "hold": 2, "threshold": 0.02},
    ])
    assert "lookback" in mom_kwargs

    # Test mean reversion param search
    mr_kwargs, _ = grid_search_best_params(prices, mean_reversion, [
        {"window": 5, "n_std": 1.0}, {"window": 10, "n_std": 2.0},
    ])
    assert "window" in mr_kwargs


# ── optimization_demo ────────────────────────────────────────────────

def test_optimization_demo_main_runs():
    """optimization_demo.main() runs all three LP problems successfully."""
    from energy_algorithms.application.optimization_demo import main as opt_main

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        opt_main()
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    assert "LP/MIP Optimization Module" in output or "All three LP/MIP problems solved" in output


# ── market_data_demo ─────────────────────────────────────────────────

def test_market_data_demo_main_verbose(monkeypatch, capsys):
    """market_data_demo.main() runs without errors."""
    from energy_algorithms.application import market_data_demo

    class FakeConn:
        def close(self):
            pass

    monkeypatch.setattr(market_data_demo, "fetch_batch", lambda tickers, period: {})
    monkeypatch.setattr(market_data_demo, "get_connection", lambda: FakeConn())
    monkeypatch.setattr(market_data_demo, "init_db", lambda conn: None)
    monkeypatch.setattr(
        market_data_demo,
        "get_summary",
        lambda conn: {"total_rows": 0, "tickers": []},
    )
    market_data_demo.main()
    captured = capsys.readouterr()
    assert "Market Data Demo" in captured.out


# ── live_backtest ────────────────────────────────────────────────────

def test_live_backtest_demo_with_fake_strategies(monkeypatch, capsys):
    """live_backtest demo_live_backtest() runs with mocked strategies."""
    from energy_algorithms.application import live_backtest

    monkeypatch.setattr(
        live_backtest, "load_price_data",
        lambda ticker, **kw: np.array([100.0, 101.0, 99.0, 102.0]),
    )
    monkeypatch.setattr(live_backtest, "momentum", lambda prices, **kwargs: np.array([0, 1, 1, 0]))
    monkeypatch.setattr(live_backtest, "mean_reversion", lambda prices, **kwargs: np.array([0, -1, 0, 1]))
    monkeypatch.setattr(live_backtest, "sma_crossover", lambda prices, **kwargs: np.array([0, 1, 0, 1]))
    monkeypatch.setattr(
        live_backtest, "backtest",
        lambda prices, signal: fake_backtest_result(float(np.sum(signal))),
    )

    result = live_backtest.demo_live_backtest()
    assert set(result) == {"Momentum", "Mean Reversion", "SMA Crossover"}
    assert "Best risk-adjusted" in capsys.readouterr().out


# ── trading_demo ─────────────────────────────────────────────────────

def test_trading_demo_best_sma_params():
    """grid_search_best_params finds optimal SMA parameters via grid search."""
    from energy_algorithms.application.data_loader import grid_search_best_params
    from energy_algorithms.domain.trading import sma_crossover, synthetic_prices

    prices, _dates = synthetic_prices(200, seed=42)
    sma_kwargs, score = grid_search_best_params(prices, sma_crossover, [
        {"fast": 5, "slow": 20}, {"fast": 10, "slow": 30}, {"fast": 30, "slow": 80},
    ])
    assert isinstance(sma_kwargs["fast"], int)
    assert isinstance(sma_kwargs["slow"], int)
    assert sma_kwargs["fast"] < sma_kwargs["slow"]
    assert isinstance(score, float)


def test_trading_demo_load_prices_fallback(monkeypatch):
    """load_price_data falls back to synthetic when no DB/yfinance."""
    from energy_algorithms.application.data_loader import load_price_data

    class FakeConn:
        def close(self) -> None:
            pass

    monkeypatch.setattr(
        "energy_algorithms.application.data_loader.get_connection",
        lambda db_path: FakeConn(),
    )
    monkeypatch.setattr(
        "energy_algorithms.application.data_loader.init_db",
        lambda conn: None,
    )
    monkeypatch.setattr(
        "energy_algorithms.application.data_loader.get_ticker_data",
        lambda conn, ticker: [],
    )

    prices, dates = load_price_data("UNKNOWN_TEST_TICKER123")
    assert len(prices) > 0
    assert len(dates) > 0


# ── strategies_demo (more tests) ─────────────────────────────────────

def test_strategies_demo_load_prices_fallback(monkeypatch):
    """strategies_demo.load_price_data falls back to synthetic data."""
    from energy_algorithms.application import strategies_demo

    class FakeConn:
        def close(self) -> None:
            pass

    monkeypatch.setattr(
        "energy_algorithms.application.data_loader.get_connection",
        lambda db_path: FakeConn(),
    )
    monkeypatch.setattr(
        "energy_algorithms.application.data_loader.init_db",
        lambda conn: None,
    )
    monkeypatch.setattr(
        "energy_algorithms.application.data_loader.get_ticker_data",
        lambda conn, ticker: [],
    )

    prices, dates = strategies_demo.load_price_data("UNKNOWN_TEST_TICKER123")
    assert len(prices) > 0
    assert len(dates) > 0


def test_strategies_demo_main_runs(monkeypatch, capsys, tmp_path):
    """strategies_demo.main() runs and produces strategy output."""
    from energy_algorithms.application import strategies_demo

    prices = np.array([100.0, 101.0, 102.0])
    dates = pd.date_range("2024-01-01", periods=3)
    monkeypatch.setattr(strategies_demo, "load_price_data", lambda ticker: (prices, dates))
    monkeypatch.setattr(
        strategies_demo,
        "grid_search_best_params",
        lambda prices, strategy_fn, param_grid, **kw: (
            {"fast": 1, "slow": 2}, 0.5
        ),
    )
    monkeypatch.setattr(strategies_demo, "sma_crossover", lambda prices, **kwargs: np.array([0, 1, 1]))
    monkeypatch.setattr(strategies_demo, "mean_reversion", lambda prices, **kwargs: np.array([0, -1, -1]))
    monkeypatch.setattr(strategies_demo, "momentum", lambda prices, **kwargs: np.array([0, 1, 0]))
    monkeypatch.setattr(strategies_demo, "backtest", lambda prices, signal: fake_backtest_result())
    patch_plotting(monkeypatch, strategies_demo, tmp_path)

    strategies_demo.main()
    captured = capsys.readouterr()
    assert "All 3 strategies compared" in captured.out


def test_strategies_demo_main_prints_best_params(monkeypatch, capsys, tmp_path):
    """strategies_demo.main() prints best params table."""
    from energy_algorithms.application import strategies_demo

    prices = np.array([100.0, 101.0, 102.0])
    dates = pd.date_range("2024-01-01", periods=3)
    monkeypatch.setattr(strategies_demo, "load_price_data", lambda ticker: (prices, dates))
    monkeypatch.setattr(
        strategies_demo,
        "grid_search_best_params",
        lambda prices, strategy_fn, param_grid, **kw: (
            {"fast": 5, "slow": 20}, 2.0
        ),
    )
    monkeypatch.setattr(strategies_demo, "sma_crossover", lambda prices, **kwargs: np.array([0, 1, 0]))
    monkeypatch.setattr(strategies_demo, "mean_reversion", lambda prices, **kwargs: np.array([0, 0, 1]))
    monkeypatch.setattr(strategies_demo, "momentum", lambda prices, **kwargs: np.array([1, 0, 0]))
    monkeypatch.setattr(strategies_demo, "backtest", lambda prices, signal: fake_backtest_result())
    patch_plotting(monkeypatch, strategies_demo, tmp_path)

    strategies_demo.main()
    captured = capsys.readouterr()
    assert "Best Parameters" in captured.out or "all 3 strategies" in captured.out.lower()


def test_strategies_demo_best_params_returns_valid_shapes():
    """grid_search_best_params returns valid kwarg dicts and scores."""
    from energy_algorithms.application.data_loader import grid_search_best_params
    from energy_algorithms.domain.trading import mean_reversion, sma_crossover, synthetic_prices

    prices, _dates = synthetic_prices(200, seed=42)

    kwargs, score = grid_search_best_params(prices, sma_crossover, [
        {"fast": 5, "slow": 20}, {"fast": 10, "slow": 30},
    ])
    assert isinstance(kwargs, dict)
    assert "fast" in kwargs and "slow" in kwargs
    assert isinstance(score, float)

    kwargs, score = grid_search_best_params(prices, mean_reversion, [
        {"window": 5, "n_std": 1.0},
    ])
    assert "window" in kwargs and "n_std" in kwargs
