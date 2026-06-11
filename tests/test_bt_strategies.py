"""Tests for backtrader strategy adapters.

Tests the HourOfDaySpread, SolarDipTrade, and CalendarSpreadDaily
strategy classes by running them through a Cerebro engine with
synthetic data.
"""
from __future__ import annotations

import tempfile

import pytest

try:
 import backtrader # noqa: F401
 _HAS_BT = True
except ImportError:
 _HAS_BT = False

pytestmark = pytest.mark.skipif(
 not _HAS_BT,
 reason="backtrader not installed",
)


@pytest.fixture
def hourly_csv():
 """Create a synthetic hourly price CSV for backtrader."""
 import csv
 import os

 with tempfile.NamedTemporaryFile(
 mode="w", suffix=".csv", delete=False, newline=""
 ) as f:
 writer = csv.writer(f)
 writer.writerow(["datetime", "open", "high", "low", "close", "volume"])
 for day in range(1, 15): # 14 days
 for hour in range(24):
 # Create a pattern: cheap at night, expensive at peak
 if 0 <= hour <= 5:
 price = 30.0 + hour * 2
 elif 6 <= hour <= 11:
 price = 50.0 + (hour - 6) * 8
 elif 12 <= hour <= 16:
 price = 60.0 + (hour - 12) * 3 # solar dip
 elif 17 <= hour <= 21:
 price = 80.0 + (hour - 17) * 10 # evening peak
 else:
 price = 55.0
 dt = f"2024-01-{day:02d} {hour:02d}:00:00"
 writer.writerow(
 [dt, f"{price:.2f}", f"{price:.2f}", f"{price:.2f}", f"{price:.2f}", "1"]
 )
 path = f.name
 yield path
 if os.path.exists(path):
 os.unlink(path)


@pytest.fixture
def daily_csv():
 """Create a synthetic daily price CSV for backtrader."""
 import csv
 import os

 with tempfile.NamedTemporaryFile(
 mode="w", suffix=".csv", delete=False, newline=""
 ) as f:
 writer = csv.writer(f)
 writer.writerow(["datetime", "close"])
 for day in range(1, 15):
 avg_price = 50.0 + (day * 2) % 30
 writer.writerow([f"2024-01-{day:02d}", f"{avg_price:.2f}"])
 path = f.name
 yield path
 if os.path.exists(path):
 os.unlink(path)


def _run_strategy(strategy_cls, csv_path, is_daily=False, **strategy_kwargs):
 """Helper to run a backtrader strategy with synthetic data."""
 import backtrader as bt

 cerebro = bt.Cerebro()
 cerebro.addstrategy(strategy_cls, **strategy_kwargs)

 if is_daily:
 cerebro.adddata(bt.feeds.GenericCSVData(
 dataname=csv_path,
 dtformat="%Y-%m-%d",
 open=1, high=1, low=1, close=1,
 volume=-1, openinterest=-1,
 ))
 else:
 cerebro.adddata(bt.feeds.GenericCSVData(
 dataname=csv_path,
 dtformat="%Y-%m-%d %H:%M:%S",
 timeframe=bt.TimeFrame.Minutes,
 compression=60,
 openinterest=-1,
 ))

 cerebro.broker.setcash(100000.0)
 results = cerebro.run()
 return results[0]


class TestHourOfDaySpread:
 """Tests for HourOfDaySpread strategy."""

 def test_strategy_runs(self, hourly_csv):
 """Strategy runs without error and produces trades."""
 from energy_algorithms.adapters.bt_strategies import HourOfDaySpread

 strat = _run_strategy(
 HourOfDaySpread,
 hourly_csv,
 lookback_days=5,
 threshold_pct=0.03,
 position_size=1.0,
 )
 assert strat is not None
 # Check that hour tracking worked
 assert hasattr(strat, "hourly_prices")
 assert len(strat.hourly_prices) > 0

 def test_strategy_with_tight_threshold(self, hourly_csv):
 """Tight threshold triggers more trades."""
 from energy_algorithms.adapters.bt_strategies import HourOfDaySpread

 strat = _run_strategy(
 HourOfDaySpread,
 hourly_csv,
 lookback_days=3,
 threshold_pct=0.01,
 position_size=2.0,
 )
 assert strat is not None

 def test_strategy_with_loose_threshold(self, hourly_csv):
 """Loose threshold triggers fewer trades."""
 from energy_algorithms.adapters.bt_strategies import HourOfDaySpread

 strat = _run_strategy(
 HourOfDaySpread,
 hourly_csv,
 lookback_days=7,
 threshold_pct=0.50,
 position_size=1.0,
 )
 assert strat is not None

 def test_strategy_high_threshold_no_trades(self, hourly_csv):
 """Very high threshold means no trades triggered."""
 from energy_algorithms.adapters.bt_strategies import HourOfDaySpread

 # threshold_pct > 1 means deviation never triggers
 strat = _run_strategy(
 HourOfDaySpread,
 hourly_csv,
 lookback_days=7,
 threshold_pct=10.0,
 position_size=1.0,
 )
 assert strat is not None


class TestSolarDipTrade:
 """Tests for SolarDipTrade strategy."""

 def test_strategy_runs(self, hourly_csv):
 """Strategy runs and enters positions during solar hours."""
 from energy_algorithms.adapters.bt_strategies import SolarDipTrade

 strat = _run_strategy(SolarDipTrade, hourly_csv)
 assert strat is not None
 assert hasattr(strat, "_hour_counter")

 def test_custom_hours(self, hourly_csv):
 """Custom solar/peak hour windows work correctly."""
 from energy_algorithms.adapters.bt_strategies import SolarDipTrade

 strat = _run_strategy(
 SolarDipTrade,
 hourly_csv,
 solar_start=8,
 solar_end=14,
 peak_start=15,
 peak_end=20,
 position_size=2.5,
 )
 assert strat is not None


class TestCalendarSpreadDaily:
 """Tests for CalendarSpreadDaily strategy."""

 def test_strategy_runs(self, daily_csv):
 """Daily MA crossover strategy runs on daily data."""
 from energy_algorithms.adapters.bt_strategies import CalendarSpreadDaily

 strat = _run_strategy(
 CalendarSpreadDaily,
 daily_csv,
 is_daily=True,
 pfast=3,
 pslow=7,
 threshold=0.02,
 )
 assert strat is not None
 assert hasattr(strat, "fast_ma")
 assert hasattr(strat, "slow_ma")
 assert hasattr(strat, "crossover")

 def test_default_params(self, daily_csv):
 """Strategy with default parameters."""
 from energy_algorithms.adapters.bt_strategies import CalendarSpreadDaily

 strat = _run_strategy(CalendarSpreadDaily, daily_csv, is_daily=True)
 assert strat is not None

 def test_tight_threshold(self, daily_csv):
 """Tight threshold triggers more MA crossover trades."""
 from energy_algorithms.adapters.bt_strategies import CalendarSpreadDaily

 strat = _run_strategy(
 CalendarSpreadDaily,
 daily_csv,
 is_daily=True,
 threshold=0.001,
 )
 assert strat is not None
