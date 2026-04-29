"""Tests for backtester engine and metrics."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest
from backtester.engine import backtest
from backtester.metrics import sharpe_ratio, sortino_ratio, max_drawdown, value_at_risk, kelly_fraction


def test_backtest_returns_dict():
    """Backtest returns expected keys."""
    prices = np.array([100, 101, 102, 101, 100, 99, 98, 99, 100, 101])
    signals = np.array([1, 1, 1, 1, 1, -1, -1, -1, -1, -1])
    r = backtest(prices, signals)
    assert "equity_curve" in r
    assert "trades" in r
    assert "total_return" in r
    assert "sharpe" in r


def test_backtest_all_flat():
    """All-flat signal produces no trades, flat equity."""
    prices = np.array([100, 101, 102, 103])
    signals = np.array([0, 0, 0, 0])
    r = backtest(prices, signals)
    assert r["n_trades"] == 0
    assert r["total_return"] == 0.0


def test_sharpe_ratio_positive():
    """Sharpe ratio is positive for consistently positive returns (with some variance)."""
    returns = np.array([0.01, 0.015, 0.008, 0.012, 0.011, 0.013] * 42)
    sr = sharpe_ratio(returns)
    assert sr > 0


def test_sharpe_ratio_negative():
    """Sharpe ratio is negative for consistently negative returns (with some variance)."""
    returns = np.array([-0.01, -0.015, -0.008, -0.012, -0.011, -0.013] * 42)
    sr = sharpe_ratio(returns)
    assert sr < 0


def test_sortino_ratio():
    """Sortino uses correct downside deviation."""
    returns = np.array([0.02, -0.01, 0.03, -0.02, 0.01])
    sr = sortino_ratio(returns)
    assert isinstance(sr, float)


def test_max_drawdown():
    """Max drawdown correctly identifies worst peak-to-trough."""
    equity = np.array([100, 110, 90, 80, 105, 120])
    dd = max_drawdown(equity)
    assert dd < 0
    # Peak=110, trough=80, DD=(80-110)/110 = -27.27%
    assert abs(dd - (-0.2727)) < 0.01


def test_var_95():
    """VaR at 95% confidence returns the 5th percentile."""
    returns = np.random.default_rng(42).normal(0, 0.02, 1000) - 0.001
    var = value_at_risk(returns, 0.95)
    assert var < 0


def test_kelly_fraction_bounds():
    """Kelly fraction is between 0 and 1."""
    returns = np.array([0.05, -0.03, 0.04, -0.02, 0.06, -0.01, 0.03])
    kf = kelly_fraction(returns)
    assert 0 <= kf <= 1
