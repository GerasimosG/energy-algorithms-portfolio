"""backtrader Strategy classes for energy market trading.

Converts our energy-specific strategies (hour-of-day, solar duck curve,
calendar spread) into backtrader ``Strategy`` subclasses that work with
the event-driven engine, order management, and commission models.

Compatible with backtrader (pip install backtrader).
"""
from __future__ import annotations

from datetime import datetime

import backtrader as bt
import numpy as np


class HourOfDaySpread(bt.Strategy):
    """Trade the intraday price curve: buy cheap hours, sell expensive ones.

    Uses a rolling window of N days to compute the average intraday profile.
    When the current hour's price deviates from the average by more than
    the threshold, trade: long when cheap (buy), short when expensive (sell).

    Parameters
    ----------
    lookback_days : int
        Days to compute rolling average profile.
    threshold_pct : float
        Minimum deviation from average profile to trigger a trade (0.05 = 5%).
    position_size : float
        Number of MWh per trade.
    """

    params = (
        ("lookback_days", 7),
        ("threshold_pct", 0.03),
        ("position_size", 1.0),
    )

    def __init__(self) -> None:
        self.hourly_prices: list[float] = []
        self._day_prices: list[float] = []
        self._current_hour = 0

    def next(self) -> None:
        """Called for each bar. Bar 0 = midnight, bar 23 = 23:00."""
        price = self.data.close[0]
        self.hourly_prices.append(price)
        self._day_prices.append(price)
        hour = len(self._day_prices) % 24

        # Only trade at the start of each new hour
        # We need enough data to compute the average profile
        if len(self.hourly_prices) < 24 * self.params.lookback_days:
            return

        # Compute the rolling average profile
        profile = np.array(self.hourly_prices)
        # Reshape into days, compute average per hour
        n_full_days = len(profile) // 24
        if n_full_days < 2:
            return
        profile_2d = profile[-n_full_days * 24:].reshape(-1, 24)
        avg_profile = np.mean(profile_2d[:-1], axis=0)  # exclude today

        if hour >= len(avg_profile):
            return

        avg_for_hour = avg_profile[hour]
        if avg_for_hour <= 0:
            return

        deviation = (price - avg_for_hour) / avg_for_hour
        target_size = self.params.position_size

        if deviation < -self.params.threshold_pct:
            # Price below average — go long
            self.buy(size=target_size)
        elif deviation > self.params.threshold_pct:
            # Price above average — go short
            self.sell(size=target_size)
        else:
            # Close position — go flat around the mean
            if self.position:
                self.close()


class SolarDipTrade(bt.Strategy):
    """Trade the solar duck curve: buy midday dip, sell evening peak.

    Positions are fixed by time of day:
    - Long during solar dip hours (12-16)
    - Short during evening peak (18-21)
    - Flat otherwise

    Parameters
    ----------
    solar_start, solar_end : int
        Hours for solar dip long position.
    peak_start, peak_end : int
        Hours for evening peak short position.
    position_size : float
        MWh per trade.
    """

    params = (
        ("solar_start", 12),
        ("solar_end", 16),
        ("peak_start", 18),
        ("peak_end", 21),
        ("position_size", 1.0),
    )

    def __init__(self) -> None:
        self._hour_counter = 0

    def next(self) -> None:
        hour = self._hour_counter % 24
        self._hour_counter += 1

        if self.params.solar_start <= hour < self.params.solar_end:
            # Solar dip — go long
            if not self.position or self.position.size < 0:
                self.close()
                self.buy(size=self.params.position_size)

        elif self.params.peak_start <= hour < self.params.peak_end:
            # Evening peak — go short
            if not self.position or self.position.size > 0:
                self.close()
                self.sell(size=self.params.position_size)

        else:
            # Flat during other hours
            if self.position:
                self.close()


class CalendarSpreadDaily(bt.Strategy):
    """Calendar spread on daily average prices using MA crossover.

    When the short MA (3-day) crosses below the long MA (7-day), buy.
    When the short MA crosses above the long MA, sell.
    Flat when MAs are close (within threshold).

    Parameters
    ----------
    pfast, pslow : int
        Moving average periods.
    threshold : float
        Minimum MA ratio difference to enter a trade.
    """

    params = (
        ("pfast", 3),
        ("pslow", 7),
        ("threshold", 0.02),
    )

    def __init__(self) -> None:
        self.fast_ma = bt.ind.SMA(period=self.params.pfast)
        self.slow_ma = bt.ind.SMA(period=self.params.pslow)
        self.crossover = bt.ind.CrossOver(self.fast_ma, self.slow_ma)

    def next(self) -> None:
        if not self.fast_ma[0] or not self.slow_ma[0]:
            return

        ratio = self.fast_ma[0] / self.slow_ma[0]

        if ratio < 1 - self.params.threshold:
            # Short-term price depressed — buy (contango)
            self.buy(size=1)
        elif ratio > 1 + self.params.threshold:
            # Short-term price elevated — sell (backwardation)
            self.sell(size=1)
        else:
            # Flat within threshold
            if self.position:
                self.close()
