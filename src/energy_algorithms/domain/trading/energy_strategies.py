"""Electricity market-specific trading strategies.

Unlike equities, electricity prices exhibit:
- Strong intraday seasonality (low night, high peak)
- Mean reversion (spikes revert quickly)
- Renewable-driven patterns (solar dip at midday, wind-driven baseload shifts)
- Calendar effects (weekend vs weekday, seasonal)

These strategies are designed for day-ahead electricity prices from ENTSO-E.
All are vectorized for speed and tested against 30-day real data.
"""
from __future__ import annotations

from typing import Any

import numpy as np


def hour_of_day_strategy(
    prices_24h: np.ndarray,
    lookback_days: int = 7,
    threshold_pct: float = 0.05,
    reference_profile: np.ndarray | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Trade the intraday price curve causally: long hours that are *usually*
    cheap and short hours that are *usually* expensive, settled at today's prices.

    The position for each hour is decided from ``reference_profile`` — the
    expected 24-hour price shape built from PRIOR days — so the decision uses no
    future information. P&L is realized as ``position * (today_avg - price)``,
    i.e. buying a cheap hour and selling the day's baseload block. Because the
    signal is lagged, P&L can be negative when the profile mispredicts (unlike
    an in-sample anchor, which is profitable by construction).

    Parameters
    ----------
    prices_24h : np.ndarray
        24 realized hourly prices for the trading day.
    lookback_days : int
        Reserved for callers. The lagged profile is built by
        ``rolling_reference_profiles(daily_prices, lookback_days)`` and passed in
        as ``reference_profile``; kept here for backwards compatibility.
    threshold_pct : float
        Minimum deviation of the reference profile from its daily mean to trigger
        a trade (e.g. 0.05 = 5%).
    reference_profile : np.ndarray | None
        Expected 24-hour price profile from prior days. If None, the function
        falls back to today's own profile (IN-SAMPLE / look-ahead) and sets
        ``in_sample=True`` in the metadata. Callers reporting performance MUST
        pass a lagged profile (see ``rolling_reference_profiles``).

    Returns
    -------
    tuple[np.ndarray, dict]
        positions array (+1=long, -1=short, 0=flat) and metadata dict.

    Notes
    -----
    Literature basis: "Intraday Electricity Trading: A Survey"
    (Kiesel & Paraschiv, 2021) — hour-of-day effects are the
    most persistent and exploitable pattern in day-ahead markets.
    """
    prices_24h = np.asarray(prices_24h, dtype=float)
    if len(prices_24h) < 24:
        return np.zeros(len(prices_24h)), {"error": "insufficient data"}

    in_sample = reference_profile is None
    ref = prices_24h if in_sample else np.asarray(reference_profile, dtype=float)
    ref_avg = float(np.mean(ref))

    # Causal signal: long the hours the reference profile says are cheap, short
    # the hours it says are expensive. Uses only prior-day information.
    ref_dev = ref - ref_avg
    positions = np.where(ref_dev < -threshold_pct * ref_avg, 1.0,
                         np.where(ref_dev > threshold_pct * ref_avg, -1.0, 0.0))

    # Realized P&L per MWh: long = buy hour h, sell the day's baseload (today avg).
    # With a lagged signal this can be negative when the profile mispredicts.
    today_avg = float(np.mean(prices_24h))
    pnl_hourly = positions * (today_avg - prices_24h)
    total_pnl = float(np.sum(pnl_hourly))
    traded = pnl_hourly[positions != 0]
    win_rate = float(np.mean(traded > 0)) if traded.size else 0.0
    avg_win = float(np.mean(traded[traded > 0])) if np.any(traded > 0) else 0.0
    avg_loss = float(np.mean(traded[traded < 0])) if np.any(traded < 0) else 0.0

    metadata = {
        "daily_avg": round(today_avg, 2),
        "positions": len(positions),
        "long_hours": int(np.sum(positions > 0)),
        "short_hours": int(np.sum(positions < 0)),
        "flat_hours": int(np.sum(positions == 0)),
        "total_pnl_per_mwh": round(total_pnl, 2),
        "avg_pnl_per_trade_per_mwh": round(total_pnl / max(int(np.sum(positions != 0)), 1), 2),
        "win_rate": round(win_rate, 4),
        "avg_win_per_mwh": round(avg_win, 2),
        "avg_loss_per_mwh": round(avg_loss, 2),
        "threshold_pct": threshold_pct,
        "in_sample": in_sample,
    }

    return positions, metadata


def rolling_reference_profiles(
    daily_prices: list[np.ndarray],
    lookback_days: int = 7,
) -> list[np.ndarray | None]:
    """Lagged expected 24-hour profile for each day.

    For day index ``i`` returns the mean profile over the previous
    ``lookback_days`` days (``None`` for ``i == 0``, which has no history). Use
    the result as the ``reference_profile`` argument to ``hour_of_day_strategy``
    so the strategy is causal (no future information).

    Parameters
    ----------
    daily_prices : list[np.ndarray]
        Date-ordered list of 24-length hourly price arrays.
    lookback_days : int
        Number of prior days to average.

    Returns
    -------
    list[np.ndarray | None]
        One entry per input day; ``None`` where there is no prior history.
    """
    profiles: list[np.ndarray | None] = []
    history: list[np.ndarray] = []
    for day in daily_prices:
        day = np.asarray(day, dtype=float)
        if history:
            window = np.vstack(history[-lookback_days:])
            profiles.append(np.mean(window, axis=0))
        else:
            profiles.append(None)
        history.append(day)
    return profiles


def solar_dip_strategy(
    prices_24h: np.ndarray,
    solar_hours: tuple[int, int] = (12, 16),
    peak_hours: tuple[int, int] = (18, 21),
) -> tuple[np.ndarray, dict[str, Any]]:
    """Trade the solar duck curve: buy solar dip, sell evening peak.

    Solar generation causes a price depression at midday when PV output peaks.
    As sun sets, prices spike when gas plants ramp up. This is the most
    reliable pattern in summer European electricity markets.

    Parameters
    ----------
    prices_24h : np.ndarray
        24 hourly prices (0-indexed).
    solar_hours : tuple
        Hour range (0-23) when solar depresses prices (default: 12-16).
    peak_hours : tuple
        Hour range for evening peak short (default: 18-21).

    Returns
    -------
    tuple[np.ndarray, dict]
        positions and metadata.
    """
    if len(prices_24h) < 24:
        return np.zeros(len(prices_24h)), {"error": "insufficient data"}

    positions = np.zeros(24)
    positions[solar_hours[0]:solar_hours[1]] = 1.0    # Long during solar dip
    positions[peak_hours[0]:peak_hours[1]] = -1.0     # Short during evening peak

    # Evening peak premium = avg evening price - avg solar dip price
    solar_avg = np.mean(prices_24h[solar_hours[0]:solar_hours[1]]) if solar_hours[0] < solar_hours[1] else 0
    peak_avg = np.mean(prices_24h[peak_hours[0]:peak_hours[1]]) if peak_hours[0] < peak_hours[1] else 0
    peak_premium = peak_avg - solar_avg

    # P&L simulate: long at solar dip (buy cheap), short at peak (sell expensive)
    # For modelling: buy solar_mwh at solar_avg, sell at peak_avg
    spread_pnl = peak_premium  # €/MWh profit on each MWh traded

    return positions, {
        "solar_avg_price": round(solar_avg, 2),
        "peak_avg_price": round(peak_avg, 2),
        "peak_premium": round(peak_premium, 2),
        "spread_pnl_per_mwh": round(spread_pnl, 2),
        "solar_hours": f"{solar_hours[0]}-{solar_hours[1]}",
        "peak_hours": f"{peak_hours[0]}-{peak_hours[1]}",
    }


def calendar_spread_strategy(
    prices: np.ndarray,
    short_window: int = 3,
    long_window: int = 7,
    threshold: float = 0.02,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Trade calendar spreads on daily average prices.

    Compares short-term vs long-term moving average of daily prices.
    When short-term dips below long-term (contango in bears), buy.
    When short-term rises above long-term (backwardation in bulls), sell.

    Adapted from classic commodity trading for power markets.

    Parameters
    ----------
    prices : np.ndarray
        Daily average prices.
    short_window, long_window : int
        Moving average windows (e.g., 3-day vs 7-day).
    threshold : float
        Entry threshold as fraction of long avg.

    Returns
    -------
    tuple[np.ndarray, dict]
    """
    if len(prices) < long_window:
        return np.zeros(len(prices)), {"error": "insufficient data"}

    short_ma = np.convolve(prices, np.ones(short_window) / short_window, mode="valid")
    long_ma = np.convolve(prices, np.ones(long_window) / long_window, mode="valid")

    # Align lengths
    min_len = min(len(short_ma), len(long_ma))
    short_ma = short_ma[-min_len:]
    long_ma = long_ma[-min_len:]

    signals = np.zeros(len(prices))
    signals[-min_len:] = np.where(
        short_ma < long_ma * (1 - threshold), 1.0,  # Buy (short-term bearish)
        np.where(short_ma > long_ma * (1 + threshold), -1.0, 0.0)  # Sell (short-term bullish)
    )

    # Compute simple equity curve
    returns = np.diff(prices[-min_len:]) / prices[-min_len:-1]
    sig = signals[-min_len:][:-1]
    strat_returns = sig * returns
    total_return = np.sum(strat_returns)
    sharpe = (np.mean(strat_returns) / max(np.std(strat_returns), 1e-10)) * np.sqrt(252)

    return signals, {
        "total_return_pct": round(total_return * 100, 2),
        "sharpe": round(sharpe, 2),
        "trades": int(np.sum(np.abs(np.diff(signals))) / 2),
        "short_window": short_window,
        "long_window": long_window,
        "threshold": threshold,
    }


def energy_backtest(
    daily_prices: list[list[float]],
    dates: list[str],
    strategies: dict[str, callable] | None = None,
) -> dict[str, Any]:
    """Run all energy trading strategies on a multi-day dataset.

    Parameters
    ----------
    daily_prices : list[list[float]]
        List of 24-hour price arrays, one per day.
    dates : list[str]
        Date strings for each day.
    strategies : dict or None
        Strategy functions to run. Defaults to all built-in strategies.

    Returns
    -------
    dict with per-strategy and aggregate results.
    """
    if strategies is None:
        strategies = {
            "hour_of_day": hour_of_day_strategy,
            "solar_dip": solar_dip_strategy,
        }

    results: dict[str, Any] = {}
    for name, strategy_fn in strategies.items():
        day_results = []
        for i, (prices, date) in enumerate(zip(daily_prices, dates)):
            np_prices = np.array(prices, dtype=float)
            _, meta = strategy_fn(np_prices)
            meta["date"] = date
            day_results.append(meta)

        # Aggregate
        if name == "solar_dip":
            spreads = [r.get("spread_pnl_per_mwh", 0) for r in day_results]
            results[name] = {
                "avg_spread_pnl_per_mwh": round(float(np.mean(spreads)), 2),
                "total_spread_pnl_per_mwh": round(float(np.sum(spreads)), 2),
                "max_spread": round(float(np.max(spreads)), 2),
                "min_spread": round(float(np.min(spreads)), 2),
                "profitable_days": int(np.sum(np.array(spreads) > 0)),
                "total_days": len(spreads),
                "win_rate": round(float(np.mean(np.array(spreads) > 0)), 3),
                "daily_details": day_results,
            }
        else:
            pnls = [r.get("total_pnl_per_mwh", 0) for r in day_results]
            win_rates = [r.get("win_rate", 0) for r in day_results]
            results[name] = {
                "avg_daily_pnl_per_mwh": round(float(np.mean(pnls)), 2),
                "total_pnl_per_mwh": round(float(np.sum(pnls)), 2),
                "std_pnl_per_mwh": round(float(np.std(pnls)), 2),
                "profitable_days": int(np.sum(np.array(pnls) > 0)),
                "total_days": len(pnls),
                "avg_win_rate": round(float(np.mean(win_rates)), 4),
                "best_day": round(float(np.max(pnls)), 2),
                "worst_day": round(float(np.min(pnls)), 2),
                "daily_details": day_results,
            }

    return results
