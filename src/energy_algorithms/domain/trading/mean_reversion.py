"""
Mean Reversion Strategy using Bollinger Bands.
Buys when price touches lower band, sells (short) when touches upper band.
"""
from __future__ import annotations


import numpy as np
import pandas as pd


def mean_reversion(
    prices: np.ndarray,
    window: int = 20,
    n_std: float = 2.0,
) -> np.ndarray:
    """
    Bollinger Bands mean reversion signal.

    1  when price <= lower band (oversold, go long)
    -1 when price >= upper band (overbought, go short)
    0  otherwise

    Parameters
    ----------
    prices : ndarray of close prices
    window : rolling window for SMA and std
    n_std : number of standard deviations for bands

    Returns
    -------
    ndarray of ints: -1, 0, 1
    """
    series = pd.Series(prices)
    sma = series.rolling(window).mean().values
    std = series.rolling(window).std().values

    upper = sma + n_std * std
    lower = sma - n_std * std

    signal = np.zeros(len(prices))
    signal[prices <= lower] = 1     # oversold → long
    signal[prices >= upper] = -1    # overbought → short
    signal[:window] = 0  # flat during warm-up

    return signal.astype(int)
