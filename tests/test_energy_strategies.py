"""Tests for domain/trading/energy_strategies.py — electricity market trading strategies."""

from __future__ import annotations

import numpy as np

from energy_algorithms.domain.trading.energy_strategies import (
    calendar_spread_strategy,
    energy_backtest,
    hour_of_day_strategy,
    solar_dip_strategy,
)

# ── hour_of_day_strategy ───────────────────────────────────────────


def test_hod_strategy_basic_shape() -> None:
    """Returns positions array of length 24 and a metadata dict."""
    prices = np.array([
        20, 18, 16, 15, 14, 15,  # night
        25, 40, 55, 50, 45, 40,  # morning peak
        35, 30, 28, 30, 35,      # solar dip
        45, 55, 60, 50, 40, 30, 25,  # evening peak → night
    ], dtype=float)

    positions, meta = hour_of_day_strategy(prices, lookback_days=7, threshold_pct=0.05)

    assert len(positions) == 24
    assert isinstance(meta, dict)
    assert "daily_avg" in meta
    assert "long_hours" in meta
    assert "short_hours" in meta
    assert "flat_hours" in meta
    assert "total_pnl_per_mwh" in meta
    assert "win_rate" in meta
    assert set(positions).issubset({-1.0, 0.0, 1.0})


def test_hod_strategy_insufficient_data() -> None:
    """Fewer than 24 elements returns all zeros and error metadata."""
    prices = np.array([10, 20, 30])

    positions, meta = hour_of_day_strategy(prices)

    assert len(positions) == 3
    assert np.all(positions == 0.0)
    assert meta["error"] == "insufficient data"


def test_hod_strategy_all_same_price() -> None:
    """All equal prices → all flat (no deviation)."""
    prices = np.full(24, 50.0)

    positions, meta = hour_of_day_strategy(prices, threshold_pct=0.01)

    assert np.all(positions == 0.0)
    assert meta["flat_hours"] == 24


def test_hod_strategy_extreme_deviation() -> None:
    """Extreme price deviation triggers clear long/short signals."""
    prices = np.array([
        10, 10, 10, 10, 10, 10,  # very cheap → long
        90, 90, 90, 90, 90, 90,  # very expensive → short
        10, 10, 10, 10, 10, 10,  # cheap → long
        90, 90, 90, 90, 90, 90,  # expensive → short
    ], dtype=float)

    positions, meta = hour_of_day_strategy(prices, threshold_pct=0.05)

    # Daily avg = 50. Threshold = 2.5. Hours with 10 → long, 90 → short
    assert meta["long_hours"] == 12
    assert meta["short_hours"] == 12
    assert meta["flat_hours"] == 0


# ── solar_dip_strategy ─────────────────────────────────────────────


def test_solar_dip_basic_shape() -> None:
    """Returns positions array of length 24 and metadata."""
    prices = np.random.default_rng(42).uniform(20, 80, 24)

    positions, meta = solar_dip_strategy(prices)

    assert len(positions) == 24
    assert isinstance(meta, dict)
    assert "solar_avg_price" in meta
    assert "peak_avg_price" in meta
    assert "peak_premium" in meta
    assert "spread_pnl_per_mwh" in meta


def test_solar_dip_insufficient_data() -> None:
    """Fewer than 24 elements returns zeros and error metadata."""
    prices = np.array([10, 20, 30])

    positions, meta = solar_dip_strategy(prices)

    assert len(positions) == 3
    assert np.all(positions == 0.0)
    assert meta["error"] == "insufficient data"


def test_solar_dip_positions_in_range() -> None:
    """Long during solar hours (12-16), short during peak (18-21)."""
    prices = np.random.default_rng(42).uniform(20, 80, 24)

    positions, meta = solar_dip_strategy(prices)

    # Solar hours: indices 12-15 (inclusive) → long
    assert np.all(positions[12:16] == 1.0)
    # Peak hours: indices 18-20 (inclusive) → short
    assert np.all(positions[18:21] == -1.0)
    # All other hours: flat
    other = np.concatenate([positions[:12], positions[16:18], positions[21:]])
    assert np.all(other == 0.0)


def test_solar_dip_custom_hours() -> None:
    """Custom solar/peak hour ranges are respected."""
    prices = np.random.default_rng(42).uniform(20, 80, 24)

    positions, _ = solar_dip_strategy(
        prices, solar_hours=(10, 14), peak_hours=(17, 20)
    )

    assert np.all(positions[10:14] == 1.0)
    assert np.all(positions[17:20] == -1.0)


def test_solar_dip_peak_premium_positive() -> None:
    """When peak prices > solar prices, peak_premium is positive."""
    prices = np.full(24, 50.0)
    prices[12:16] = 30.0   # cheap solar dip
    prices[18:21] = 80.0   # expensive peak

    positions, meta = solar_dip_strategy(prices)

    assert meta["peak_premium"] > 0
    assert meta["spread_pnl_per_mwh"] > 0


# ── calendar_spread_strategy ───────────────────────────────────────


def test_calendar_spread_basic() -> None:
    """Returns signals array of length len(prices) and metadata."""
    rng = np.random.default_rng(42)
    trend = np.linspace(100, 110, 30)  # gentle uptrend
    noise = rng.normal(0, 2, 30)
    prices = trend + noise

    signals, meta = calendar_spread_strategy(
        prices, short_window=3, long_window=7, threshold=0.02
    )

    assert len(signals) == len(prices)
    assert isinstance(meta, dict)
    assert "total_return_pct" in meta
    assert "sharpe" in meta
    assert "trades" in meta
    assert set(signals).issubset({-1.0, 0.0, 1.0})


def test_calendar_spread_insufficient_data() -> None:
    """Fewer points than long_window returns zeros and error metadata."""
    prices = np.array([10, 20, 30])

    signals, meta = calendar_spread_strategy(
        prices, short_window=3, long_window=7
    )

    assert len(signals) == 3
    assert np.all(signals == 0.0)
    assert meta["error"] == "insufficient data"


def test_calendar_spread_constant_price() -> None:
    """Constant prices → no signals (all flat)."""
    prices = np.full(50, 100.0)

    signals, meta = calendar_spread_strategy(
        prices, short_window=3, long_window=7, threshold=0.01
    )

    # No deviation → all flat
    assert np.all(signals[6:] == 0.0)  # after warmup


def test_calendar_spread_threshold_effect() -> None:
    """Higher threshold suppresses marginal signals."""
    rng = np.random.default_rng(42)
    prices = 100 + np.cumsum(rng.normal(0, 1, 50))

    signals_low, _ = calendar_spread_strategy(
        prices, short_window=3, long_window=7, threshold=0.01
    )
    signals_high, _ = calendar_spread_strategy(
        prices, short_window=3, long_window=7, threshold=0.10
    )

    # Higher threshold should have <= non-zero signals
    non_zero_low = np.count_nonzero(signals_low)
    non_zero_high = np.count_nonzero(signals_high)
    assert non_zero_high <= non_zero_low


def test_calendar_spread_sharpe_finite() -> None:
    """Sharpe ratio in metadata is finite (no division by zero)."""
    rng = np.random.default_rng(42)
    prices = 100 + np.cumsum(rng.normal(0, 0.5, 30))

    _, meta = calendar_spread_strategy(
        prices, short_window=3, long_window=7, threshold=0.02
    )

    assert np.isfinite(meta["sharpe"])


# ── energy_backtest ────────────────────────────────────────────────


def test_energy_backtest_basic() -> None:
    """Backtest runs with default strategies and returns results for each."""
    rng = np.random.default_rng(42)
    daily_prices = [rng.uniform(20, 80, 24).tolist() for _ in range(5)]
    dates = [f"2025-01-{d:02d}" for d in range(1, 6)]

    results = energy_backtest(daily_prices, dates)

    assert "hour_of_day" in results
    assert "solar_dip" in results
    assert results["hour_of_day"]["total_days"] == 5
    assert results["solar_dip"]["total_days"] == 5


def test_energy_backtest_custom_strategies() -> None:
    """Custom strategies dict can be passed."""
    def dummy_strategy(prices):
        import numpy as np
        return np.zeros(24), {"dummy": True}

    daily_prices = [list(range(24)) for _ in range(3)]
    dates = ["2025-01-01", "2025-01-02", "2025-01-03"]

    results = energy_backtest(
        daily_prices, dates, strategies={"custom": dummy_strategy}
    )

    assert "custom" in results
    assert results["custom"]["total_days"] == 3


def test_energy_backtest_single_day() -> None:
    """Backtest works with a single day of data."""
    daily_prices = [[float(i) for i in range(24)]]
    dates = ["2025-01-01"]

    results = energy_backtest(daily_prices, dates)

    assert results["hour_of_day"]["total_days"] == 1
    assert results["solar_dip"]["total_days"] == 1


def test_energy_backtest_solar_dip_aggregation() -> None:
    """Solar dip aggregation uses spread_pnl_per_mwh key."""
    rng = np.random.default_rng(42)
    daily_prices = [rng.uniform(20, 80, 24).tolist() for _ in range(5)]
    dates = [f"2025-01-{d:02d}" for d in range(1, 6)]

    results = energy_backtest(daily_prices, dates)

    assert "avg_spread_pnl_per_mwh" in results["solar_dip"]
    assert "total_spread_pnl_per_mwh" in results["solar_dip"]
    assert "max_spread" in results["solar_dip"]
    assert "min_spread" in results["solar_dip"]
    assert "profitable_days" in results["solar_dip"]
    assert "win_rate" in results["solar_dip"]
    assert "daily_details" in results["solar_dip"]
    assert len(results["solar_dip"]["daily_details"]) == 5


def test_energy_backtest_hour_of_day_aggregation() -> None:
    """Hour-of-day aggregation uses total_pnl_pct key."""
    rng = np.random.default_rng(42)
    daily_prices = [rng.uniform(20, 80, 24).tolist() for _ in range(5)]
    dates = [f"2025-01-{d:02d}" for d in range(1, 6)]

    results = energy_backtest(daily_prices, dates)

    assert "avg_daily_pnl_pct" in results["hour_of_day"]
    assert "total_pnl_pct" in results["hour_of_day"]
    assert "std_pnl_pct" in results["hour_of_day"]
    assert "avg_win_rate" in results["hour_of_day"]
    assert "best_day" in results["hour_of_day"]
    assert "worst_day" in results["hour_of_day"]
    assert "daily_details" in results["hour_of_day"]
    assert len(results["hour_of_day"]["daily_details"]) == 5
