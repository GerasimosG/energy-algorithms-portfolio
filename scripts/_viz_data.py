"""Shared data resolver for the portfolio's figure + dashboard generators.

All visualization scripts load their data through this module so a fresh clone
reproduces every figure and the interactive dashboard from the small committed
sample dataset under ``data/``.

Resolution order for each dataset:
  1. ``data/sample_*.csv``  — committed, small, canonical (works on a fresh clone).
  2. ``data/<full>.csv``    — the full local ENTSO-E cache, if a developer has it.

Provenance: the samples are trimmed/de-duplicated copies of cached ENTSO-E
Belgian day-ahead data. See ``data/README.md``.
"""

from __future__ import annotations

import os

import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")


def _resolve(*candidates: str) -> str:
    """Return the first existing path among *candidates* (relative to DATA_DIR)."""
    for name in candidates:
        path = os.path.join(DATA_DIR, name)
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        f"None of {candidates} found in {DATA_DIR}. "
        "Expected the committed sample dataset (data/sample_*.csv)."
    )


def load_prices() -> pd.DataFrame:
    """15-min ENTSO-E day-ahead prices: columns ``date, hour, price_eur_mwh``."""
    return pd.read_csv(_resolve("sample_entsoe_prices.csv", "entsoe_30day_prices.csv"))


def load_summary() -> pd.DataFrame:
    """Daily market summary: avg/min/max price, model MCP, welfare, generation, flags."""
    df = pd.read_csv(_resolve("sample_entsoe_summary.csv", "entsoe_30day_summary.csv"))
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_hourly() -> pd.DataFrame:
    """Hourly OHLCV bars for the backtest signals: ``datetime, open, high, low, close, volume``."""
    df = pd.read_csv(_resolve("sample_bt_hourly.csv", "bt_hourly.csv"))
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def prices_hourly_matrix() -> pd.DataFrame:
    """Pivot prices to a date×hour matrix (€/MWh), averaging the 15-min slots per hour.

    Returns a DataFrame indexed by date (rows) with hour-of-day 0..23 columns.
    """
    df = load_prices().copy()
    df["hod"] = (df["hour"] - 1) // 4  # 15-min slot (1..96) -> hour-of-day 0..23
    hourly = df.groupby(["date", "hod"], as_index=False)["price_eur_mwh"].mean()
    return hourly.pivot(index="date", columns="hod", values="price_eur_mwh").sort_index()


# --- Resource-adequacy sample loaders (synthetic; see data/README.md) -----------

def load_adequacy_units() -> pd.DataFrame:
    """Synthetic thermal fleet: unit, technology, capacity_mw, for (forced-outage rate)."""
    return pd.read_csv(_resolve("sample_adequacy_units.csv"))


def load_load_8760() -> pd.DataFrame:
    """Synthetic one-year hourly demand: datetime, load_mw."""
    df = pd.read_csv(_resolve("sample_load_8760.csv"))
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def load_vre_8760() -> pd.DataFrame:
    """Synthetic one-year hourly VRE availability: datetime, wind_mw, solar_mw."""
    df = pd.read_csv(_resolve("sample_vre_8760.csv"))
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def load_antares_sample() -> pd.DataFrame:
    """Tidy ANTARES economy hourly sample (delegates to the adapter reader)."""
    import sys as _sys
    _sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))
    from energy_algorithms.adapters.antares_io import read_values_hourly
    return read_values_hourly(
        _resolve("antares_sample/economy/mc-all/areas/be/values-hourly.txt"))


if __name__ == "__main__":  # pragma: no cover - manual smoke check
    print("summary:", load_summary().shape)
    print("prices :", load_prices().shape)
    print("hourly :", load_hourly().shape)
    print("matrix :", prices_hourly_matrix().shape)
