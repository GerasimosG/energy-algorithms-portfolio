"""Tests for backtrader CSV data feed adapters.

Tests the prepare_hourly_csv() and prepare_daily_csv() conversion
functions that transform ENTSO-E price CSVs into backtrader-compatible format.
"""
from __future__ import annotations

import csv
import os
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
def source_csv():
 """Create a temporary source CSV in ENTSO-E format."""
 with tempfile.NamedTemporaryFile(
 mode="w", suffix=".csv", delete=False, newline=""
 ) as f:
 writer = csv.writer(f)
 writer.writerow(["date", "hour", "price_eur_mwh"])
 # Two days of hourly data
 for day in ["2024-01-01", "2024-01-02"]:
 for h in range(1, 25):
 price = 50.0 + (h * 2.5) + (10.0 if day == "2024-01-02" else 0.0)
 writer.writerow([day, str(h), f"{price:.2f}"])
 path = f.name
 yield path
 if os.path.exists(path):
 os.unlink(path)


def test_prepare_hourly_csv_creates_file(source_csv):
 """prepare_hourly_csv writes a backtrader-compatible hourly CSV."""
 from energy_algorithms.adapters.bt_feeds import prepare_hourly_csv

 output = source_csv + ".hourly.csv"
 try:
 result = prepare_hourly_csv(source_csv, output)
 assert result == output
 assert os.path.exists(output)

 with open(output, newline="") as f:
 reader = csv.reader(f)
 header = next(reader)
 assert header == ["datetime", "open", "high", "low", "close", "volume"]

 rows = list(reader)
 # 2 days × 24 hours = 48 rows
 assert len(rows) == 48

 # Check first row
 dt, open_, high, low, close, volume = rows[0]
 assert "2024-01-01" in dt
 assert volume == "1"
 finally:
 if os.path.exists(output):
 os.unlink(output)


def test_prepare_hourly_csv_with_start_hour(source_csv):
 """Start hour is passed through (backtrader session_start offset)."""
 from energy_algorithms.adapters.bt_feeds import prepare_hourly_csv

 output = source_csv + ".hourly2.csv"
 try:
 prepare_hourly_csv(source_csv, output, start_hour=6)
 assert os.path.exists(output)
 finally:
 if os.path.exists(output):
 os.unlink(output)


def test_prepare_hourly_csv_sort_order(source_csv):
 """Rows are written in chronological order."""
 from energy_algorithms.adapters.bt_feeds import prepare_hourly_csv

 output = source_csv + ".hourly3.csv"
 try:
 prepare_hourly_csv(source_csv, output)
 with open(output, newline="") as f:
 reader = csv.reader(f)
 next(reader) # skip header
 rows = list(reader)

 dates = [r[0].split(" ")[0] for r in rows]
 # First 24 rows should be day 1, next 24 day 2
 assert all(d == "2024-01-01" for d in dates[:24])
 assert all(d == "2024-01-02" for d in dates[24:])
 finally:
 if os.path.exists(output):
 os.unlink(output)


def test_prepare_hourly_csv_empty_source():
 """Empty CSV with only header produces no data rows."""
 from energy_algorithms.adapters.bt_feeds import prepare_hourly_csv

 with tempfile.NamedTemporaryFile(
 mode="w", suffix=".csv", delete=False, newline=""
 ) as f:
 f.write("date,hour,price_eur_mwh\n")
 src = f.name

 output = src + ".hourly.empty.csv"
 try:
 prepare_hourly_csv(src, output)
 with open(output, newline="") as f:
 rows = list(csv.reader(f))
 assert len(rows) == 1 # header only
 finally:
 for p in [src, output]:
 if os.path.exists(p):
 os.unlink(p)


def test_prepare_daily_csv_creates_file(source_csv):
 """prepare_daily_csv writes a backtrader-compatible daily CSV."""
 from energy_algorithms.adapters.bt_feeds import prepare_daily_csv

 output = source_csv + ".daily.csv"
 try:
 result = prepare_daily_csv(source_csv, output)
 assert result == output
 assert os.path.exists(output)

 with open(output, newline="") as f:
 reader = csv.reader(f)
 header = next(reader)
 assert header == ["datetime", "close"]

 rows = list(reader)
 # 2 days
 assert len(rows) == 2

 # Check row format
 assert rows[0][0] == "2024-01-01"
 close_val = float(rows[0][1])
 assert close_val > 0
 finally:
 if os.path.exists(output):
 os.unlink(output)


def test_prepare_daily_csv_empty_source():
 """Empty CSV produces no data rows in daily output."""
 from energy_algorithms.adapters.bt_feeds import prepare_daily_csv

 with tempfile.NamedTemporaryFile(
 mode="w", suffix=".csv", delete=False, newline=""
 ) as f:
 f.write("date,hour,price_eur_mwh\n")
 src = f.name

 output = src + ".daily.empty.csv"
 try:
 prepare_daily_csv(src, output)
 with open(output, newline="") as f:
 rows = list(csv.reader(f))
 assert len(rows) == 1
 finally:
 for p in [src, output]:
 if os.path.exists(p):
 os.unlink(p)
