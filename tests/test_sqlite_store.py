"""Tests for the SQLite storage adapter.

Tests init_db, insert_ohlcv, get_ticker_data, get_summary,
get_connection, and edge cases like duplicate handling and
date type conversion.
"""
from __future__ import annotations

import tempfile

import pytest


@pytest.fixture
def db_conn():
 """Create a temporary SQLite database with initialized schema."""
 from energy_algorithms.adapters.sqlite_store import get_connection, init_db

 with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
 db_path = f.name

 conn = get_connection(db_path)
 init_db(conn)
 yield conn
 conn.close()
 import os
 os.unlink(db_path)


@pytest.fixture
def sample_records():
 """Sample OHLCV records for testing."""
 return [
 {"ticker": "AAPL", "date": "2024-01-02", "open": 180.0, "high": 185.0,
 "low": 179.0, "close": 184.0, "volume": 50000000},
 {"ticker": "AAPL", "date": "2024-01-03", "open": 184.0, "high": 186.0,
 "low": 182.0, "close": 185.0, "volume": 45000000},
 {"ticker": "MSFT", "date": "2024-01-02", "open": 370.0, "high": 375.0,
 "low": 368.0, "close": 374.0, "volume": 30000000},
 ]


class TestInitDb:
 """Tests for init_db()."""

 def test_init_db_creates_tables(self, db_conn):
 """Tables exist after initialization."""
 cursor = db_conn.execute(
 "SELECT name FROM sqlite_master WHERE type='table' AND name='daily_ohlcv'"
 )
 assert cursor.fetchone() is not None

 def test_init_db_idempotent(self, db_conn):
 """Calling init_db multiple times is safe."""
 from energy_algorithms.adapters.sqlite_store import init_db

 # Call init_db again (should not raise)
 init_db(db_conn)
 # Table still works
 cursor = db_conn.execute("SELECT COUNT(*) FROM daily_ohlcv")
 assert cursor.fetchone()[0] == 0


class TestInsertOhlcv:
 """Tests for insert_ohlcv()."""

 def test_insert_records(self, db_conn, sample_records):
 """Insert records and verify count."""
 from energy_algorithms.adapters.sqlite_store import insert_ohlcv

 count = insert_ohlcv(db_conn, sample_records)
 assert count == 3

 # Verify in database
 rows = db_conn.execute("SELECT * FROM daily_ohlcv").fetchall()
 assert len(rows) == 3

 def test_insert_duplicate_skipped(self, db_conn, sample_records):
 """Duplicate (ticker, date) pairs are silently ignored."""
 from energy_algorithms.adapters.sqlite_store import insert_ohlcv

 insert_ohlcv(db_conn, sample_records)
 count = insert_ohlcv(db_conn, sample_records)
 assert count == 0 # No new records

 rows = db_conn.execute("SELECT * FROM daily_ohlcv").fetchall()
 assert len(rows) == 3

 def test_insert_empty_list(self, db_conn):
 """Empty record list inserts nothing."""
 from energy_algorithms.adapters.sqlite_store import insert_ohlcv

 count = insert_ohlcv(db_conn, [])
 assert count == 0

 def test_insert_with_datetime_date(self, db_conn):
 """Records with datetime.date objects are handled correctly."""
 from datetime import date

 from energy_algorithms.adapters.sqlite_store import insert_ohlcv

 records = [
 {
 "ticker": "TEST", "date": date(2024, 6, 15),
 "open": 100.0, "high": 105.0, "low": 99.0,
 "close": 103.0, "volume": 10000,
 },
 ]
 count = insert_ohlcv(db_conn, records)
 assert count == 1

 def test_insert_with_null_volume(self, db_conn):
 """Records with None/zero volume work correctly."""
 from energy_algorithms.adapters.sqlite_store import insert_ohlcv

 records = [
 {
 "ticker": "TEST", "date": "2024-01-02",
 "open": 100.0, "high": 105.0, "low": 99.0,
 "close": 103.0, "volume": None,
 },
 ]
 count = insert_ohlcv(db_conn, records)
 assert count == 1

 def test_insert_with_datetime_instance(self, db_conn):
 """Records with datetime.datetime objects are handled correctly (line 51)."""
 from datetime import datetime

 from energy_algorithms.adapters.sqlite_store import insert_ohlcv

 records = [
 {
 "ticker": "TEST", "date": datetime(2024, 6, 15, 10, 30, 0),
 "open": 100.0, "high": 105.0, "low": 99.0,
 "close": 103.0, "volume": 10000,
 },
 ]
 count = insert_ohlcv(db_conn, records)
 assert count == 1

 def test_malformed_record_skipped(self, db_conn):
 """Malformed records (missing keys) are caught and skipped (line 76)."""
 from energy_algorithms.adapters.sqlite_store import insert_ohlcv

 records = [
 {"ticker": "BAD", "date": "2024-01-02"}, # missing OHLCV
 ]
 count = insert_ohlcv(db_conn, records)
 assert count == 0


class TestGetTickerData:
 """Tests for get_ticker_data()."""

 def test_get_ticker_data(self, db_conn, sample_records):
 """Retrieve data for a specific ticker."""
 from energy_algorithms.adapters.sqlite_store import get_ticker_data, insert_ohlcv

 insert_ohlcv(db_conn, sample_records)

 rows = get_ticker_data(db_conn, "AAPL")
 assert len(rows) == 2
 assert rows[0]["ticker"] == "AAPL"
 assert rows[1]["ticker"] == "AAPL"

 def test_get_ticker_data_empty(self, db_conn):
 """Non-existent ticker returns empty list."""
 from energy_algorithms.adapters.sqlite_store import get_ticker_data

 rows = get_ticker_data(db_conn, "NONEXISTENT")
 assert rows == []


class TestGetSummary:
 """Tests for get_summary()."""

 def test_get_summary(self, db_conn, sample_records):
 """Summary returns per-ticker stats and total row count."""
 from energy_algorithms.adapters.sqlite_store import get_summary, insert_ohlcv

 insert_ohlcv(db_conn, sample_records)
 summary = get_summary(db_conn)

 assert summary["total_rows"] == 3
 assert len(summary["tickers"]) == 2

 ticker_names = {t["ticker"] for t in summary["tickers"]}
 assert ticker_names == {"AAPL", "MSFT"}

 def test_get_summary_empty_db(self, db_conn):
 """Empty database returns summary with zero rows."""
 from energy_algorithms.adapters.sqlite_store import get_summary

 summary = get_summary(db_conn)
 assert summary["total_rows"] == 0
 assert summary["tickers"] == []


class TestGetConnection:
 """Tests for get_connection()."""

 def test_get_connection_row_factory(self):
 """Connection uses sqlite3.Row row factory."""
 import sqlite3

 from energy_algorithms.adapters.sqlite_store import get_connection
 with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
 db_path = f.name

 conn = get_connection(db_path)
 assert conn.row_factory == sqlite3.Row
 conn.close()
 import os
 os.unlink(db_path)
