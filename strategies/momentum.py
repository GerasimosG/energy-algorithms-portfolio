"""
Momentum Strategy.
Goes long when recent returns are positive, short when negative.
"""

import numpy as np
import pandas as pd


def momentum(
    prices: np.ndarray,
    lookback: int = 60,
    hold: int = 20,
) -> np.ndarray:
    """
    Momentum factor signal.

    Computes return over lookback period.
    1  when return > 0 (positive momentum, go long)
    -1 when return < 0 (negative momentum, go short)
    0  otherwise (flat)

    Parameters
    ----------
    prices : ndarray of close prices
    lookback : period for momentum calculation
    hold : holding period (signal regenerates every `hold` days)

    Returns
    -------
    ndarray of ints: -1, 0, 1
    """
    n = len(prices)
    signal = np.zeros(n)

    # Compute lookback returns
    returns = pd.Series(prices).pct_change(lookback).values

    # Generate signal at each hold period boundary
    for i in range(lookback, n, hold):
        end = min(i + hold, n)
        if returns[i] > 0.02:  # threshold to avoid noise
            signal[i:end] = 1
        elif returns[i] < -0.02:
            signal[i:end] = -1
        else:
            signal[i:end] = 0

    signal[:lookback] = 0  # flat during warm-up
    return signal.astype(int)
