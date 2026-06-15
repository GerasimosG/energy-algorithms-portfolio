"""
Shared data loader for portfolio experiments.

Loads Belgian ENTSO-E day-ahead prices from the local CSV with a
synthetic-data fallback when the CSV is missing. Both experiments
(revenue stacking + strategy head-to-head) use this so the CSV
format is documented in exactly one place.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

# Belgian 2024 typical price floor for synthetic fallback.
SYNTHETIC_BASE_PRICE = 60.0
SYNTHETIC_DAYS = 30
SYNTHETIC_START_DATE = datetime(2026, 4, 21)


def load_belgian_prices(
    csv_path: Path,
    source_tag: str = "exp",
) -> tuple[list[list[float]], list[str]]:
    """
    Load Belgian day-ahead prices from the local ENTSO-E CSV.

    The CSV format is ``date,hour,price_eur_mwh`` with quarter-hourly
    granularity (hour 1..96, i.e. ENTSO-E "position" numbering).
    Quarter-hours are bucketed into 24 hourly slots by averaging
    within each ``(date, hour_of_day)`` group.

    Returns
    -------
    prices : list of length-N lists of 24 floats
    dates : list of N date strings (ISO format)

    Falls back to synthetic data if the CSV is missing or empty.
    """
    if not csv_path.exists():
        print(f"[{source_tag}] CSV not found at {csv_path}; using synthetic data.")
        return synthetic_prices()
    if not csv_path.is_file():
        print(f"[{source_tag}] CSV path {csv_path} is not a file; using synthetic data.")
        return synthetic_prices()

    hourly: dict[str, dict[int, list[float]]] = defaultdict(dict)
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row.get("date")
            if not date:
                continue
            try:
                q = int(row["hour"])
                price = float(row["price_eur_mwh"])
            except (KeyError, ValueError, TypeError):
                continue
            # Quarter-hourly position 1..96 → hour-of-day 0..23.
            hour_of_day = (q - 1) // 4
            if not 0 <= hour_of_day <= 23:
                continue
            hourly[date].setdefault(hour_of_day, []).append(price)

    if not hourly:
        print(f"[{source_tag}] CSV {csv_path} has no valid rows; using synthetic data.")
        return synthetic_prices()

    dates = sorted(hourly.keys())
    prices: list[list[float]] = []
    for d in dates:
        day_prices = hourly[d]
        all_prices = [p for hours in day_prices.values() for p in hours]
        daily_mean = (
            float(np.mean(all_prices)) if all_prices else SYNTHETIC_BASE_PRICE
        )
        # Some hours may be missing — fall back to the daily mean so
        # downstream strategies still get 24 values.
        day_24 = [
            float(np.mean(day_prices.get(h, [daily_mean]))) for h in range(24)
        ]
        prices.append(day_24)

    print(f"[{source_tag}] Loaded {len(dates)} days from {csv_path.name}.")
    return prices, dates


def synthetic_prices() -> tuple[list[list[float]], list[str]]:
    """
    Deterministic 30-day Belgian-style profile.

    Sinusoidal intraday curve (low at night, high at evening peak) +
    random daily noise + occasional spike. Same seed across both
    experiments so synthetic runs are reproducible and comparable.
    """
    rng = np.random.default_rng(seed=42)
    dates = [
        (SYNTHETIC_START_DATE + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(SYNTHETIC_DAYS)
    ]
    prices: list[list[float]] = []
    spike_days = {5, 12, 20}
    for i in range(SYNTHETIC_DAYS):
        base = SYNTHETIC_BASE_PRICE + 20.0 * np.sin(
            (np.arange(24) - 6) * np.pi / 12
        )
        noise = rng.normal(0, 5, 24)
        spike = 40.0 if (i in spike_days and rng.random() > 0.3) else 0.0
        prices.append([float(x) for x in base + noise + spike])
    return prices, dates
