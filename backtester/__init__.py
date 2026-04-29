"""Backtester module — vectorized engine and risk metrics."""

from backtester.engine import backtest
from backtester.metrics import (
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    calmar_ratio,
    value_at_risk,
    kelly_fraction,
    compute_all,
)

__all__ = [
    "backtest",
    "sharpe_ratio",
    "sortino_ratio",
    "max_drawdown",
    "calmar_ratio",
    "value_at_risk",
    "kelly_fraction",
    "compute_all",
]
