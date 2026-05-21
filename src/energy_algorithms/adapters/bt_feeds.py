"""backtrader data feed adapters for ENTSO-E price data.

Converts our 26-day Belgian ENTSO-E day-ahead price CSV into
backtrader GenericCSVDataFeeds compatible with backtrader's event-driven engine.
"""
from __future__ import annotations

import os
from datetime import datetime

import backtrader as bt


class EntsoeHourlyFeed(bt.feeds.GenericCSVData):
    """backtrader data feed for ENTSO-E hourly day-ahead prices.

    Takes our entsoe_prices.csv (columns: date, hour, price_eur_mwh)
    and maps each hour to a backtrader bar. The hour column becomes
    the session, and each week's 168 hours create a continuous data feed.

    Parameters
    ----------
    datapath : str
        Path to CSV with date,hour,price_eur_mwh columns.
    session_start : int
        Starting hour (default 0 = midnight).
    """

    params = (
        ("nullvalue", float("nan")),
        ("dtformat", "%Y-%m-%d"),
        ("tmformat", "%H"),
        ("time", -1),
        ("datetime", -1),
        ("open", -1),
        ("high", -1),
        ("low", -1),
        ("close", -1),
        ("volume", -1),
        ("openinterest", -1),
    )

    def __init__(self, datapath: str = "", session_start: int = 0):
        if datapath:
            self.p.datapath = datapath
        self._session_start = session_start
        super().__init__()


class EntsoeDailyFeed(bt.feeds.GenericCSVData):
    """backtrader data feed for daily average ENTSO-E prices.

    Aggregates hourly data into daily bars for strategies operating
    on daily frequency.

    Parameters
    ----------
    datapath : str
        Path to CSV with date,close columns.
    """

    params = (
        ("nullvalue", float("nan")),
        ("dtformat", "%Y-%m-%d"),
        ("time", -1),
        ("open", -1),
        ("high", -1),
        ("low", -1),
        ("close", 1),
        ("volume", -1),
        ("openinterest", -1),
    )


def prepare_hourly_csv(
    source_csv: str,
    output_csv: str,
    start_hour: int = 0,
) -> str:
    """Convert ENTSO-E price CSV to backtrader-compatible hourly format.

    Maps each (date, hour) to a bar with datetime, open, high, low, close, volume.
    Since day-ahead prices are a single price per hour (no OHLCV), we
    use the same price for all four OHLC fields and assume 1 MWh volume.

    Parameters
    ----------
    source_csv : str
        Path to source entsoe_prices.csv.
    output_csv : str
        Path for backtrader-compatible CSV.
    start_hour : int
        Starting hour offset (default 0).

    Returns
    -------
    str
        Path to output CSV.
    """
    import csv
    from collections import defaultdict

    # Read source
    hourly: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    with open(source_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            h = int(row["hour"])
            # Map hour 0 → 23, keep hours 1-24 as-is
            hourly[row["date"]][h].append(float(row["price_eur_mwh"]))

    # Write backtrader format (hourly bars with session datetime)
    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)
    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["datetime", "open", "high", "low", "close", "volume"])
        for date in sorted(hourly.keys()):
            hours_data = hourly[date]
            for hour in sorted(hours_data.keys()):
                prices = hours_data[hour]
                avg_price = sum(prices) / len(prices)
                h = hour % 24
                if h == 0 and hour == 24:
                    h = 23
                dt = f"{date} {h:02d}:00"
                writer.writerow([dt, round(avg_price, 2), round(avg_price, 2),
                                 round(avg_price, 2), round(avg_price, 2), 1])

    return output_csv


def prepare_daily_csv(
    source_csv: str,
    output_csv: str,
) -> str:
    """Aggregate hourly ENTSO-E data to daily average for backtrader.

    Parameters
    ----------
    source_csv, output_csv : str
        Input/output paths.
    """
    import csv
    from collections import defaultdict

    hourly: dict[str, list[float]] = defaultdict(list)
    with open(source_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            hourly[row["date"]].append(float(row["price_eur_mwh"]))

    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)
    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["datetime", "close"])
        for date in sorted(hourly.keys()):
            avg = sum(hourly[date]) / len(hourly[date])
            writer.writerow([date, round(avg, 2)])

    return output_csv
