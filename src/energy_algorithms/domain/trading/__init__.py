"""Trading domain — backtesting engine, risk metrics, signal strategies.

Vectorized backtesting with no look-ahead bias,
momentum/mean-reversion/SMA crossover strategies,
and comprehensive risk analytics.
"""
from __future__ import annotations


from energy_algorithms.domain.trading.backtest_engine import backtest
from energy_algorithms.domain.trading.risk_metrics import (
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    calmar_ratio,
    value_at_risk,
    kelly_fraction,
    compute_all,
)
from energy_algorithms.domain.trading.momentum import momentum
from energy_algorithms.domain.trading.mean_reversion import mean_reversion
from energy_algorithms.domain.trading.sma_crossover import sma_crossover

__all__ = [
    "backtest",
    "sharpe_ratio",
    "sortino_ratio",
    "max_drawdown",
    "calmar_ratio",
    "value_at_risk",
    "kelly_fraction",
    "compute_all",
    "momentum",
    "mean_reversion",
    "sma_crossover",
]
