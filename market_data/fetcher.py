"""
Fetch OHLCV data from Yahoo Finance via yfinance.
Handles rate limits with polite delays.
"""

import time
from typing import Optional

import yfinance as yf


def fetch_ticker(
    ticker: str,
    period: str = "2y",
    interval: str = "1d",
    retries: int = 3,
    delay: float = 1.0,
) -> Optional[dict]:
    """Fetch daily OHLCV for a ticker. Returns dict or None on failure."""
    for attempt in range(1, retries + 1):
        try:
            t = yf.Ticker(ticker)
            df = t.history(period=period, interval=interval)
            if df.empty:
                print(f"  [WARN] {ticker}: no data returned")
                time.sleep(delay)
                continue
            df = df.reset_index()
            # Keep only the columns we need
            df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]
            df.columns = ["date", "open", "high", "low", "close", "volume"]
            df["ticker"] = ticker
            print(f"  [OK]   {ticker}: {len(df)} rows")
            return df.to_dict("records")
        except Exception as e:
            print(f"  [RETRY] {ticker} attempt {attempt}/{retries}: {e}")
            time.sleep(delay * (2 ** (attempt - 1)))
    print(f"  [FAIL] {ticker}: all retries exhausted")
    return None


def fetch_batch(
    tickers: list[str],
    period: str = "2y",
    interval: str = "1d",
    delay: float = 1.5,
) -> dict[str, list[dict]]:
    """Fetch multiple tickers sequentially with delays."""
    results = {}
    for ticker in tickers:
        print(f"Fetching {ticker}...")
        data = fetch_ticker(ticker, period=period, interval=interval, delay=delay)
        if data:
            results[ticker] = data
        time.sleep(delay)
    return results
