"""Tests for engie_demo — Energy Trading Demo functions.

Tests individual functions in isolation with synthetic/minimal data.
Does NOT run the full demo (no API keys or live data).
"""
from __future__ import annotations

import csv
import os
from unittest.mock import MagicMock

import numpy as np

# ── _load_env_key ───────────────────────────────────────────────────


def test_load_env_key_no_env_file(monkeypatch, tmp_path):
    """_load_env_key returns empty string when no .env file exists."""
    import energy_algorithms.application.institutional_trading_demo as ed

    # Clear any token already loaded into the environment (e.g. from a real
    # repo-root .env) so this asserts the genuine no-.env behaviour.
    monkeypatch.delenv("ENTSOE_API_KEY", raising=False)

    # Monkeypatch the module's __file__ to point to a tmp dir with no .env
    fake_app_dir = tmp_path / "application"
    fake_app_dir.mkdir(parents=True)
    monkeypatch.setattr(ed, "__file__", str(fake_app_dir / "engie_demo.py"))

    key = ed._load_env_key()
    assert key == ""


def test_load_env_key_with_env_file(monkeypatch, tmp_path):
    """_load_env_key reads ENTSOE_API_KEY from .env file."""
    import energy_algorithms.application.institutional_trading_demo as ed

    # The function does: dirname(__file__)/../.env
    # So if __file__ = /tmp/.../application/engie_demo.py
    # Then dirname = /tmp/.../application
    # Then join with .. = /tmp/.../
    # Then join with .env = /tmp/.../.env
    fake_app_dir = tmp_path / "application"
    fake_app_dir.mkdir(parents=True)
    fake_parent = tmp_path  # This is the ".." level
    env_file = fake_parent / ".env"
    env_file.write_text("ENTSOE_API_KEY=test-key-123\nOTHER=stuff\n")

    monkeypatch.setattr(ed, "__file__", str(fake_app_dir / "engie_demo.py"))

    key = ed._load_env_key()
    assert key == "test-key-123"


def test_load_env_key_skips_comments(monkeypatch, tmp_path):
    """_load_env_key skips comment lines and blank lines."""
    import energy_algorithms.application.institutional_trading_demo as ed

    fake_app_dir = tmp_path / "application"
    fake_app_dir.mkdir(parents=True)
    env_file = tmp_path / ".env"  # One level up from application
    env_file.write_text("# this is a comment\n\nENTSOE_API_KEY=value\n")

    monkeypatch.setattr(ed, "__file__", str(fake_app_dir / "engie_demo.py"))

    key = ed._load_env_key()
    assert key == "value"


def test_load_env_key_uses_env_var_directly(monkeypatch):
    """_load_env_key returns ENTSOE_API_KEY from environ even without .env."""
    import energy_algorithms.application.institutional_trading_demo as ed

    monkeypatch.setenv("ENTSOE_API_KEY", "from-env-key")
    # Make os.path.exists return False so it skips the .env file
    orig_exists = os.path.exists

    def mock_exists(path):
        if ".env" in str(path):
            return False
        return orig_exists(path)

    monkeypatch.setattr(ed.os.path, "exists", mock_exists)

    key = ed._load_env_key()
    assert key == "from-env-key"


# ── load_cached_data ────────────────────────────────────────────────


def test_load_cached_data_missing_file(monkeypatch):
    """load_cached_data returns empty tuples when CSV doesn't exist."""
    from energy_algorithms.application.institutional_trading_demo import load_cached_data

    orig_exists = os.path.exists

    def mock_exists(p):
        p_str = str(p)
        if "entsoe_prices.csv" in p_str:
            return False
        return orig_exists(p)

    monkeypatch.setattr(os.path, "exists", mock_exists)

    prices, dates, extra = load_cached_data()
    assert prices == []
    assert dates == []


def test_load_cached_data_with_csv(monkeypatch, tmp_path):
    """load_cached_data parses a correctly formatted CSV."""
    import energy_algorithms.application.institutional_trading_demo as ed

    # Create the CSV at a path that matches the function's expectation
    # The function does: dirname(__file__)/../../data/entsoe_prices.csv
    # If __file__ = /tmp/.../src/energy_algorithms/application/engie_demo.py
    # dirname = /tmp/.../src/energy_algorithms/application
    # ../.. = /tmp/.../
    # data/entsoe_prices.csv = /tmp/.../data/entsoe_prices.csv
    fake_app_dir = tmp_path / "src" / "energy_algorithms" / "application"
    fake_app_dir.mkdir(parents=True)
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    csv_path = data_dir / "entsoe_prices.csv"

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "price_eur_mwh"])
        writer.writeheader()
        writer.writerows([
            {"date": "2024-01-01", "price_eur_mwh": "50.0"},
            {"date": "2024-01-01", "price_eur_mwh": "60.0"},
            {"date": "2024-01-02", "price_eur_mwh": "55.0"},
            {"date": "2024-01-02", "price_eur_mwh": "65.0"},
        ])

    monkeypatch.setattr(ed, "__file__", str(fake_app_dir / "engie_demo.py"))

    prices, dates, extra = ed.load_cached_data()
    assert len(prices) == 2  # Two dates
    assert dates == ["2024-01-01", "2024-01-02"]
    assert prices[0] == [50.0, 60.0]
    assert prices[1] == [55.0, 65.0]


def test_load_cached_data_csv_with_no_data_file(monkeypatch, capsys):
    """load_cached_data prints message when CSV doesn't exist."""
    import tempfile

    import energy_algorithms.application.institutional_trading_demo as ed

    # Ensure no real CSV can be found
    # Use a truly non-existent path
    tmpdir = tempfile.mkdtemp()
    try:
        fake_dir = os.path.join(tmpdir, "src", "energy_algorithms", "application")
        os.makedirs(fake_dir)
        monkeypatch.setattr(ed, "__file__", os.path.join(fake_dir, "engie_demo.py"))

        prices, dates, extra = ed.load_cached_data()
        captured = capsys.readouterr()
        assert "Cached data not found" in captured.out
        assert prices == []
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── fetch_recent_data ───────────────────────────────────────────────


def test_fetch_recent_data_returns_prices(monkeypatch):
    """fetch_recent_data returns price data from mocked client."""
    from energy_algorithms.application.institutional_trading_demo import fetch_recent_data

    mock_client = MagicMock()
    mock_client.fetch_day_ahead_prices.return_value = {
        "status": "ok",
        "prices": [
            {"hour": h, "price_eur_mwh": 50.0 + h}
            for h in range(1, 25)
        ],
    }

    prices, dates = fetch_recent_data(mock_client, num_days=3)
    assert len(prices) == 3
    assert len(dates) == 3
    assert len(prices[0]) == 24
    assert mock_client.fetch_day_ahead_prices.call_count == 3


def test_fetch_recent_data_handles_empty_response(monkeypatch):
    """fetch_recent_data handles API returning no prices."""
    from energy_algorithms.application.institutional_trading_demo import fetch_recent_data

    mock_client = MagicMock()
    mock_client.fetch_day_ahead_prices.return_value = {
        "status": "ok",
        "prices": [],
    }

    prices, dates = fetch_recent_data(mock_client, num_days=2)
    assert prices == []
    assert dates == []


def test_fetch_recent_data_handles_error_status(monkeypatch):
    """fetch_recent_data handles API error response."""
    from energy_algorithms.application.institutional_trading_demo import fetch_recent_data

    mock_client = MagicMock()
    mock_client.fetch_day_ahead_prices.return_value = {
        "status": "error",
        "message": "API limit",
    }

    prices, dates = fetch_recent_data(mock_client, num_days=2)
    assert prices == []
    assert dates == []


# ── find_gas_marginal_day ───────────────────────────────────────────


def test_find_gas_marginal_day_high_price():
    """find_gas_marginal_day finds first day with avg price > 80."""
    from energy_algorithms.application.institutional_trading_demo import find_gas_marginal_day

    prices = [
        [50.0] * 24,  # avg 50 — too low
        [85.0] * 24,  # avg 85 — gas marginal
        [40.0] * 24,
    ]
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]

    idx, date = find_gas_marginal_day(prices, dates, {})
    assert idx == 1
    assert date == "2024-01-02"


def test_find_gas_marginal_day_all_low():
    """find_gas_marginal_day returns first date if no day has avg > 80."""
    from energy_algorithms.application.institutional_trading_demo import find_gas_marginal_day

    prices = [
        [40.0] * 24,
        [50.0] * 24,
    ]
    dates = ["2024-01-01", "2024-01-02"]

    idx, date = find_gas_marginal_day(prices, dates, {})
    assert idx == 0
    assert date == "2024-01-01"


# ── run_pcr_with_co2 ────────────────────────────────────────────────


def test_run_pcr_with_co2_no_co2():
    """run_pcr_with_co2 runs PCR model without CO₂ costs."""
    from energy_algorithms.application.institutional_trading_demo import run_pcr_with_co2

    prices_data = {
        "prices": [
            {"hour": 1, "price_eur_mwh": 80.0},
            {"hour": 2, "price_eur_mwh": 90.0},
            {"hour": 3, "price_eur_mwh": 100.0},
        ],
        "avg_price": 90.0,
    }
    gen_data = {
        "generation": [
            {"type": "Fossil Gas", "mw": 1000},
            {"type": "Solar", "mw": 500},
            {"type": "Wind Offshore", "mw": 300},
        ]
    }

    result = run_pcr_with_co2(prices_data, gen_data, co2=False)
    assert "mcp" in result
    assert "welfare" in result
    assert "status" in result
    assert result["co2"] is False


def test_run_pcr_with_co2_with_co2():
    """run_pcr_with_co2 runs PCR model with CO₂ costs."""
    from energy_algorithms.application.institutional_trading_demo import run_pcr_with_co2

    prices_data = {
        "prices": [
            {"hour": 1, "price_eur_mwh": 80.0},
            {"hour": 2, "price_eur_mwh": 90.0},
            {"hour": 3, "price_eur_mwh": 100.0},
        ],
        "avg_price": 90.0,
    }
    gen_data = {
        "generation": [
            {"type": "Fossil Gas", "mw": 1000},
            {"type": "Solar", "mw": 500},
        ]
    }

    result = run_pcr_with_co2(prices_data, gen_data, co2=True)
    assert result["co2"] is True
    assert result["status"] == "Optimal"


def test_run_pcr_with_co2_skips_zero_mw_generation():
    """run_pcr_with_co2 skips generation entries with zero or negative MW."""
    from energy_algorithms.application.institutional_trading_demo import run_pcr_with_co2

    prices_data = {
        "prices": [
            {"hour": 1, "price_eur_mwh": 80.0},
            {"hour": 2, "price_eur_mwh": 90.0},
            {"hour": 3, "price_eur_mwh": 100.0},
        ],
        "avg_price": 90.0,
    }
    gen_data = {
        "generation": [
            {"type": "Fossil Gas", "mw": 1000},
            {"type": "Solar", "mw": 0},  # Should be skipped
            {"type": "Wind", "mw": -5},  # Should be skipped
        ]
    }

    result = run_pcr_with_co2(prices_data, gen_data, co2=False)
    assert result["status"] in ("Optimal", "Feasible")


# ── main() ──────────────────────────────────────────────────────────


def test_main_runs_without_crash(monkeypatch, capsys):
    """main() runs without crashing — uses no data path."""
    from energy_algorithms.application import institutional_trading_demo as engie_demo

    # Force no cached data by making exists return False for entsoe_prices paths
    orig_exists = os.path.exists

    def mock_exists(p):
        p_str = str(p)
        if "entsoe_prices.csv" in p_str:
            return False
        if ".env" in p_str:
            return False
        return orig_exists(p)

    monkeypatch.setattr(engie_demo.os.path, "exists", mock_exists)

    engie_demo.main()
    captured = capsys.readouterr()
    assert "ENERGY TRADING DEMO" in captured.out
    assert "No data available" in captured.out


def test_main_with_cached_data(monkeypatch, capsys, tmp_path):
    """main() runs with mocked cached data."""
    from energy_algorithms.application import institutional_trading_demo as engie_demo

    # Provide realistic price data (24 hours, 5 days)
    prices = []
    for day in range(5):
        daily = []
        for h in range(24):
            base = 50.0 + day * 5
            pattern = 20.0 * np.sin(2 * np.pi * (h - 8) / 24)
            daily.append(base + pattern)
        prices.append(daily)
    dates = [f"2024-01-{d+1:02d}" for d in range(5)]

    monkeypatch.setattr(engie_demo, "_load_env_key", lambda: "")
    monkeypatch.setattr(
        engie_demo, "load_cached_data", lambda: (prices, dates, [])
    )
    # Avoid any client creation
    monkeypatch.setattr(engie_demo, "EntsoeClient", lambda **kw: None)
    # Mock the fetch_recent_data since no client
    monkeypatch.setattr(engie_demo, "fetch_recent_data", lambda c, **kw: ([], []))

    engie_demo.main()
    captured = capsys.readouterr()
    assert "ENERGY TRADING DEMO" in captured.out
    # Should proceed past "No data available"
    assert "No data available" not in captured.out


def test_main_prints_trading_sections(monkeypatch, capsys):
    """main() prints all trading strategy sections when data is present."""
    from energy_algorithms.application import institutional_trading_demo as engie_demo

    # Provide realistic price data (24 hours, 5 days)
    prices = []
    for day in range(5):
        daily = []
        for h in range(24):
            base = 50.0 + day * 5
            pattern = 20.0 * np.sin(2 * np.pi * (h - 8) / 24)
            daily.append(base + pattern)
        prices.append(daily)
    dates = [f"2024-01-{d+1:02d}" for d in range(5)]

    monkeypatch.setattr(engie_demo, "_load_env_key", lambda: "")
    monkeypatch.setattr(
        engie_demo, "load_cached_data", lambda: (prices, dates, [])
    )
    monkeypatch.setattr(engie_demo, "fetch_recent_data", lambda c, **kw: ([], []))
    monkeypatch.setattr(engie_demo, "EntsoeClient", lambda **kw: None)

    engie_demo.main()
    captured = capsys.readouterr()
    assert "HOUR-OF-DAY SPREAD TRADING" in captured.out
    assert "SOLAR DUCK CURVE TRADING" in captured.out
    assert "CALENDAR SPREAD TRADING" in captured.out
    assert "ENERGY ROLE READINESS SUMMARY" in captured.out
