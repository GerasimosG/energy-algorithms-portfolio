"""
Momentum Strategy.
Goes long when recent returns are positive, short when negative.
"""
from __future__ import annotations


import numpy as np
import pandas as pd


def momentum(
    prices: np.ndarray,
    lookback: int = 60,
    hold: int = 20,
    threshold: float = 0.02,
) -> np.ndarray:
    """
    Momentum factor signal.

    Computes return over lookback period.
    1  when return > threshold (positive momentum, go long)
    -1 when return < -threshold (negative momentum, go short)
    0  otherwise (flat/flat market)

    Parameters
    ----------
    prices : ndarray of close prices
    lookback : period for momentum calculation
    hold : holding period (signal regenerates every `hold` days)
    threshold : minimum return to trigger a signal (default 2%)

    Returns
    -------
    ndarray of ints: -1, 0, 1
    """
    n = len(prices)
    signal = np.zeros(n)

    returns = pd.Series(prices).pct_change(lookback).values

    for i in range(lookback, n, hold):
        end = min(i + hold, n)
        if returns[i] > threshold:
            signal[i:end] = 1
        elif returns[i] < -threshold:
            signal[i:end] = -1
        else:
            signal[i:end] = 0

    signal[:lookback] = 0
    return signal.astype(int)
