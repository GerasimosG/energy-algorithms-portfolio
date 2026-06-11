"""
SMA Crossover Strategy.
Generates long/short signals from fast/slow moving average cross.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma_crossover(
 prices: np.ndarray,
 fast: int = 20,
 slow: int = 50,
) -> np.ndarray:
 """
 SMA crossover signal.

 1 when fast MA > slow MA (long)
 -1 when fast MA < slow MA (short)
 0 during warm-up period

 Parameters
 ----------
 prices : ndarray of close prices
 fast : fast SMA window
 slow : slow SMA window

 Returns
 -------
 ndarray of ints: -1, 0, 1
 """
 fast_sma = pd.Series(prices).rolling(fast).mean().values
 slow_sma = pd.Series(prices).rolling(slow).mean().values
 signal = np.zeros(len(prices))
 signal[fast_sma > slow_sma] = 1
 signal[fast_sma < slow_sma] = -1
 signal[:slow] = 0 # flat during warm-up
 return signal.astype(int)
