#!/usr/bin/env python3
"""
Demo: fetch 5 assets from Yahoo Finance → SQLite.
Run with: python -m market-data.demo (from repo root)
"""
from __future__ import annotations

from energy_algorithms.adapters.sqlite_store import (
 get_connection,
 get_summary,
 init_db,
 insert_ohlcv,
)
from energy_algorithms.adapters.yfinance_fetcher import fetch_batch

TICKERS = ["AAPL", "MSFT", "GOOGL", "SPY", "BTC-USD"]


def main():
 print("=" * 60)
 print("Market Data Demo — Fetching & Storing OHLCV")
 print("=" * 60)

 # 1. Fetch
 print(f"\nFetching {len(TICKERS)} assets...")
 data = fetch_batch(TICKERS, period="2y")

 print(f"\nFetched {len(data)} / {len(TICKERS)} tickers successfully.")

 # 2. Store
 conn = get_connection()
 init_db(conn)

 total = 0
 for ticker, records in data.items():
 n = insert_ohlcv(conn, records)
 total += n
 print(f" Stored {n} rows for {ticker}")

 conn.close()

 # 3. Summary
 conn = get_connection()
 summary = get_summary(conn)
 conn.close()

 print(f"\n{'=' * 60}")
 print(f"Storage Summary: {summary['total_rows']} total rows across tickers")
 for t in summary["tickers"]:
 print(f" {t['ticker']:>8s}: {t['rows']:>5d} rows [{t['first']} → {t['last']}]")
 print(f"{'=' * 60}")


if __name__ == "__main__":
 main()
