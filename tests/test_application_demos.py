"""Tests for application demos — covers orchestration modules.

Tests demo entry points that wire domain + adapters together.
All demos use deterministic demo data (no live API calls).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from energy_algorithms.application.energy_data_demo import demo_energy_data


class DummyAxis:
    """Minimal matplotlib axis double for demo plotting tests."""

    transAxes = object()

    def plot(self, *args, **kwargs) -> None:
        pass

    def fill_between(self, *args, **kwargs) -> None:
        pass

    def axhline(self, *args, **kwargs) -> None:
        pass

    def set_title(self, *args, **kwargs) -> None:
        pass

    def set_ylabel(self, *args, **kwargs) -> None:
        pass

    def set_xlabel(self, *args, **kwargs) -> None:
        pass

    def grid(self, *args, **kwargs) -> None:
        pass

    def text(self, *args, **kwargs) -> None:
        pass


def fake_backtest_result() -> dict:
    """Return the result shape expected by plotting demos."""
    return {
        "equity_curve": pd.Series([100_000.0, 101_000.0, 102_000.0]),
        "total_return": 0.02,
        "sharpe": 1.2,
        "max_drawdown": -0.01,
        "n_trades": 2,
        "win_rate": 0.5,
    }


def patch_plotting(monkeypatch, module, tmp_path) -> None:
    """Patch matplotlib and output paths for cheap demo tests."""
    axes = [DummyAxis(), DummyAxis(), DummyAxis()]
    monkeypatch.setattr(module.plt, "subplots", lambda *a, **kw: (object(), axes))
    monkeypatch.setattr(module.plt, "tight_layout", lambda: None)
    monkeypatch.setattr(module.plt, "savefig", lambda *a, **kw: None)
    monkeypatch.setattr(module.plt, "close", lambda: None)
    monkeypatch.setattr(module.os.path, "dirname", lambda path: str(tmp_path))


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
    # Capture stdout to avoid noise, just verify it doesn't crash
    import io
    import sys

    from energy_algorithms.application.optimization_demo import main as opt_main
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
    import io
    import sys

    from energy_algorithms.application.markets_demo import main as markets_main
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
    import io
    import sys

    from energy_algorithms.application.live_pipeline import demo_live_pipeline
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        result = demo_live_pipeline()
    finally:
        sys.stdout = old_stdout
    assert isinstance(result, dict)


# ── market_data_demo ─────────────────────────────────────────────────

def test_market_data_demo_main_runs(monkeypatch):
    """market_data_demo.main() fetches and stores data (will use demo data if available)."""
    import io
    import sys

    from energy_algorithms.application import market_data_demo

    fake_conn = type("FakeConn", (), {"close": lambda self: None})()
    monkeypatch.setattr(market_data_demo, "fetch_batch", lambda tickers, period: {"AAPL": [{"ticker": "AAPL"}]})
    monkeypatch.setattr(market_data_demo, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(market_data_demo, "init_db", lambda conn: None)
    monkeypatch.setattr(market_data_demo, "insert_ohlcv", lambda conn, records: len(records))
    monkeypatch.setattr(
        market_data_demo,
        "get_summary",
        lambda conn: {
            "total_rows": 1,
            "tickers": [{"ticker": "AAPL", "rows": 1, "first": "2024-01-01", "last": "2024-01-01"}],
        },
    )

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        market_data_demo.main()
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    assert "Market Data" in output or "Fetching" in output


# ── live_backtest ────────────────────────────────────────────────────

def test_live_backtest_demo_runs(monkeypatch):
    """demo_live_backtest falls back to synthetic data and returns results."""
    import io
    import sys

    from energy_algorithms.application import live_backtest

    monkeypatch.setattr(live_backtest, "_load_or_fetch", lambda ticker: np.array([100.0, 101.0, 99.0, 102.0]))
    monkeypatch.setattr(live_backtest, "momentum", lambda prices, **kwargs: np.array([0, 1, 1, 0]))
    monkeypatch.setattr(live_backtest, "mean_reversion", lambda prices, **kwargs: np.array([0, -1, 0, 1]))
    monkeypatch.setattr(live_backtest, "sma_crossover", lambda prices, **kwargs: np.array([0, 1, 0, 1]))
    monkeypatch.setattr(live_backtest, "backtest", lambda prices, signal: fake_backtest_result())

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        result = live_backtest.demo_live_backtest()
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


def test_trading_demo_load_prices_fallback(monkeypatch):
    """_load_prices falls back to synthetic when no DB/yfinance."""
    import io
    import sys

    from energy_algorithms.application import data_loader
    from energy_algorithms.application import trading_demo

    class FakeConn:
        def close(self) -> None:
            pass

    monkeypatch.setattr(data_loader, "get_connection", lambda db_path: FakeConn())
    monkeypatch.setattr(data_loader, "init_db", lambda conn: None)
    monkeypatch.setattr(data_loader, "get_ticker_data", lambda conn, ticker: [])
    monkeypatch.setattr(data_loader, "_fetch_ticker", None)

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        prices, dates = trading_demo._load_prices("AAPL")
    finally:
        sys.stdout = old_stdout
    assert len(prices) > 200  # real or synthetic — both give substantial data
    assert len(dates) > 200


def test_trading_demo_main_runs(monkeypatch, capsys, tmp_path):
    """trading_demo.main() runs with synthetic data and prints results."""
    from energy_algorithms.application import trading_demo

    prices = np.array([100.0, 101.0, 102.0])
    dates = pd.date_range("2024-01-01", periods=3)
    monkeypatch.setattr(trading_demo, "_load_prices", lambda ticker: (prices, dates))
    monkeypatch.setattr(trading_demo, "_best_sma_params", lambda prices: (1, 2))
    monkeypatch.setattr(trading_demo, "sma_crossover", lambda prices, fast, slow: np.array([0, 1, 1]))
    monkeypatch.setattr(trading_demo, "backtest", lambda prices, signal: fake_backtest_result())
    monkeypatch.setattr(
        trading_demo,
        "compute_all",
        lambda returns, equity: {"sharpe": 1.0, "max_drawdown": -0.01},
    )
    patch_plotting(monkeypatch, trading_demo, tmp_path)

    trading_demo.main()
    captured = capsys.readouterr()
    assert "Backtester Demo" in captured.out or "SMA Crossover" in captured.out
    assert "Return" in captured.out


def test_trading_demo_main_prints_metrics(monkeypatch, capsys, tmp_path):
    """trading_demo.main() prints risk metrics for each ticker."""
    from energy_algorithms.application import trading_demo

    prices = np.array([100.0, 101.0, 102.0])
    dates = pd.date_range("2024-01-01", periods=3)
    monkeypatch.setattr(trading_demo, "_load_prices", lambda ticker: (prices, dates))
    monkeypatch.setattr(trading_demo, "_best_sma_params", lambda prices: (1, 2))
    monkeypatch.setattr(trading_demo, "sma_crossover", lambda prices, fast, slow: np.array([0, 1, 1]))
    monkeypatch.setattr(trading_demo, "backtest", lambda prices, signal: fake_backtest_result())
    monkeypatch.setattr(
        trading_demo,
        "compute_all",
        lambda returns, equity: {"sharpe": 1.0, "max_drawdown": -0.01},
    )
    patch_plotting(monkeypatch, trading_demo, tmp_path)

    trading_demo.main()
    captured = capsys.readouterr()
    assert "Sharpe" in captured.out
    assert "Max DD" in captured.out


# ── strategies_demo (extended) ──────────────────────────────────────


def test_strategies_demo_load_prices_fallback(monkeypatch):
    """strategies_demo._load_prices falls back to synthetic data."""
    from energy_algorithms.application import data_loader
    from energy_algorithms.application import strategies_demo

    class FakeConn:
        def close(self) -> None:
            pass

    monkeypatch.setattr(data_loader, "get_connection", lambda db_path: FakeConn())
    monkeypatch.setattr(data_loader, "init_db", lambda conn: None)
    monkeypatch.setattr(data_loader, "get_ticker_data", lambda conn, ticker: [])
    monkeypatch.setattr(data_loader, "_fetch_ticker", None)

    prices, dates = strategies_demo._load_prices("UNKNOWN_TEST_TICKER123")
    assert len(prices) > 0
    assert len(dates) > 0


def test_strategies_demo_main_runs(monkeypatch, capsys, tmp_path):
    """strategies_demo.main() runs and produces strategy output."""
    from energy_algorithms.application import strategies_demo

    prices = np.array([100.0, 101.0, 102.0])
    dates = pd.date_range("2024-01-01", periods=3)
    monkeypatch.setattr(strategies_demo, "_load_prices", lambda ticker: (prices, dates))
    monkeypatch.setattr(
        strategies_demo,
        "_best_params",
        lambda prices: {
            "sma": {"fast": 1, "slow": 2},
            "mr": {"window": 2, "n_std": 1.0},
            "mom": {"lookback": 1, "hold": 1, "threshold": 0.01},
        },
    )
    monkeypatch.setattr(strategies_demo, "sma_crossover", lambda prices, **kwargs: np.array([0, 1, 1]))
    monkeypatch.setattr(strategies_demo, "mean_reversion", lambda prices, **kwargs: np.array([0, -1, -1]))
    monkeypatch.setattr(strategies_demo, "momentum", lambda prices, **kwargs: np.array([0, 1, 0]))
    monkeypatch.setattr(strategies_demo, "backtest", lambda prices, signal: fake_backtest_result())
    patch_plotting(monkeypatch, strategies_demo, tmp_path)

    strategies_demo.main()
    captured = capsys.readouterr()
    assert "Strategies Demo" in captured.out
    assert "SMA Crossover" in captured.out or "Bollinger" in captured.out


def test_strategies_demo_main_prints_best_params(monkeypatch, capsys, tmp_path):
    """strategies_demo.main() prints best parameters per strategy."""
    from energy_algorithms.application import strategies_demo

    prices = np.array([100.0, 101.0, 102.0])
    dates = pd.date_range("2024-01-01", periods=3)
    monkeypatch.setattr(strategies_demo, "_load_prices", lambda ticker: (prices, dates))
    monkeypatch.setattr(
        strategies_demo,
        "_best_params",
        lambda prices: {
            "sma": {"fast": 1, "slow": 2},
            "mr": {"window": 2, "n_std": 1.0},
            "mom": {"lookback": 1, "hold": 1, "threshold": 0.01},
        },
    )
    monkeypatch.setattr(strategies_demo, "sma_crossover", lambda prices, **kwargs: np.array([0, 1, 1]))
    monkeypatch.setattr(strategies_demo, "mean_reversion", lambda prices, **kwargs: np.array([0, -1, -1]))
    monkeypatch.setattr(strategies_demo, "momentum", lambda prices, **kwargs: np.array([0, 1, 0]))
    monkeypatch.setattr(strategies_demo, "backtest", lambda prices, signal: fake_backtest_result())
    patch_plotting(monkeypatch, strategies_demo, tmp_path)

    strategies_demo.main()
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
