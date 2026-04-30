"""
SQLite storage for OHLCV market data.
Schema: daily_ohlcv table with composite index.
"""
from __future__ import annotations


import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "market_data.sqlite")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create the schema if it doesn't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS daily_ohlcv (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker      TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            open        REAL    NOT NULL,
            high        REAL    NOT NULL,
            low         REAL    NOT NULL,
            close       REAL    NOT NULL,
            volume      INTEGER NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE(ticker, date)
        );

        CREATE INDEX IF NOT EXISTS idx_daily_ohlcv_ticker_date
            ON daily_ohlcv(ticker, date);

        CREATE INDEX IF NOT EXISTS idx_daily_ohlcv_date
            ON daily_ohlcv(date);
    """)
    conn.commit()


def insert_ohlcv(conn: sqlite3.Connection, records: list[dict]) -> int:
    """Insert OHLCV records, skipping duplicates. Returns count inserted."""
    inserted = 0
    for r in records:
        try:
            date_str = r["date"]
            if isinstance(date_str, datetime):
                date_str = date_str.strftime("%Y-%m-%d")
            elif hasattr(date_str, "strftime"):
                date_str = date_str.strftime("%Y-%m-%d")
            else:
                date_str = str(date_str)[:10]

            before = conn.total_changes
            conn.execute(
                """
                INSERT OR IGNORE INTO daily_ohlcv (ticker, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r["ticker"],
                    date_str,
                    float(r["open"]),
                    float(r["high"]),
                    float(r["low"]),
                    float(r["close"]),
                    int(r["volume"]) if r["volume"] else 0,
                ),
            )
            if conn.total_changes > before:
                inserted += 1
        except Exception as e:
            print(f"  [SKIP] {r.get('ticker', '?')} {r.get('date', '?')}: {e}")
    conn.commit()
    return inserted


def get_ticker_data(conn: sqlite3.Connection, ticker: str) -> list[sqlite3.Row]:
    """Retrieve all OHLCV data for a ticker, ordered by date."""
    return conn.execute(
        "SELECT * FROM daily_ohlcv WHERE ticker = ? ORDER BY date", (ticker,)
    ).fetchall()


def get_summary(conn: sqlite3.Connection) -> dict:
    """Get storage summary: ticker count, row count, date range."""
    tickers = conn.execute(
        "SELECT ticker, COUNT(*) as rows, MIN(date) as first, MAX(date) as last "
        "FROM daily_ohlcv GROUP BY ticker ORDER BY ticker"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) as cnt FROM daily_ohlcv").fetchone()
    return {"tickers": [dict(t) for t in tickers], "total_rows": total["cnt"]}
