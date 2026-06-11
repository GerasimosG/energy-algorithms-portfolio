"""Trading domain — backtesting engine, risk metrics, signal strategies.

Vectorized backtesting with no look-ahead bias,
momentum/mean-reversion/SMA crossover strategies,
and comprehensive risk analytics.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from energy_algorithms.domain.trading.backtest_engine import backtest
from energy_algorithms.domain.trading.mean_reversion import mean_reversion
from energy_algorithms.domain.trading.momentum import momentum
from energy_algorithms.domain.trading.risk_metrics import (
 calmar_ratio,
 compute_all,
 kelly_fraction,
 max_drawdown,
 sharpe_ratio,
 sortino_ratio,
 value_at_risk,
)
from energy_algorithms.domain.trading.sma_crossover import sma_crossover


def synthetic_prices(
 n: int = 500,
 seed: int = 42,
) -> tuple[np.ndarray, pd.DatetimeIndex]:
 """Generate trending price series with clear bull regimes.

 Uses a regime-switching model: flat → strong uptrend → correction → uptrend.
 Trend-following strategies (SMA crossover, momentum) can profit from this.

 Parameters
 ----------
 n : number of periods
 seed : rng seed

 Returns
 -------
 prices, dates
 """
 rng = np.random.default_rng(seed)
 dates = pd.date_range(end="2024-12-31", periods=n)

 # Regime-switching drift: flat(0.01%), bull trend(0.2%), correction(-0.1%), bull(0.15%)
 regimes = np.zeros(n)
 regime_switches = [
 (0, int(n * 0.15), 0.0001),
 (int(n * 0.15), int(n * 0.55), 0.002),
 (int(n * 0.55), int(n * 0.65), -0.001),
 (int(n * 0.65), n, 0.0015),
 ]
 for start, end, drift in regime_switches:
 regimes[start:end] = drift

 vol = 0.015
 returns = regimes + rng.normal(0, vol, n)
 prices = 100 * np.exp(np.cumsum(returns))
 return prices.astype(float), dates


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
 "synthetic_prices",
]
