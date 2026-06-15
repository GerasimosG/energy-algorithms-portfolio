"""
Risk & performance metrics. Pure numpy functions.
Sharpe, Sortino, max drawdown, Calmar, VaR, Kelly.
"""
from __future__ import annotations

import numpy as np


def sharpe_ratio(returns: np.ndarray, rf: float = 0.0, periods: int = 252) -> float:
    if len(returns) < 2 or np.std(returns) == 0:
        return 0.0
    excess = returns - rf / periods
    return float(np.mean(excess) / np.std(returns) * np.sqrt(periods))


def sortino_ratio(returns: np.ndarray, rf: float = 0.0, periods: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    excess = returns - rf / periods
    # Downside deviation: sqrt(mean(min(0, r)²))
    downside = np.minimum(0, returns)
    downside_dev = np.sqrt(np.mean(downside ** 2))
    if downside_dev == 0:
        return 0.0
    return float(np.mean(excess) / downside_dev * np.sqrt(periods))


def max_drawdown(equity: np.ndarray) -> float:
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    return float(np.min(dd))


def calmar_ratio(returns: np.ndarray, periods: int = 252) -> float:
    ann = (1 + np.mean(returns)) ** periods - 1
    dd = max_drawdown(100 * np.cumprod(1 + returns))
    return float(ann / abs(dd)) if dd != 0 else 0.0


def value_at_risk(returns: np.ndarray, confidence: float = 0.95) -> float:
    return float(np.percentile(returns, (1 - confidence) * 100))


def kelly_fraction(returns: np.ndarray) -> float:
    winners = returns[returns > 0]
    losers = returns[returns < 0]
    if len(winners) == 0 or len(losers) == 0:
        return 0.0
    p = len(winners) / len(returns[returns != 0])
    b = np.mean(winners) / abs(np.mean(losers)) if abs(np.mean(losers)) > 0 else 0
    if b == 0:
        return 0.0
    f = (p * b - (1 - p)) / b
    return max(0.0, min(1.0, float(f)))


def compute_all(returns: np.ndarray, equity: np.ndarray) -> dict:
    return {
        "sharpe": round(sharpe_ratio(returns), 4),
        "sortino": round(sortino_ratio(returns), 4),
        "max_drawdown": round(max_drawdown(equity), 4),
        "calmar": round(calmar_ratio(returns), 4),
        "var_95": round(value_at_risk(returns, 0.95), 4),
        "var_99": round(value_at_risk(returns, 0.99), 4),
        "kelly": round(kelly_fraction(returns), 4),
    }
