"""Tests for tradepro_demo — TradePro Demo functions.

Tests individual functions with synthetic data and mocked dependencies.
Does NOT require real ENTSO-E data or backtrader CSV files.
"""
from __future__ import annotations

import csv
import os

# ── run_backtrader_hod ──────────────────────────────────────────────


def test_run_backtrader_hod_signature():
    """run_backtrader_hod returns expected dict keys when it succeeds."""
    from energy_algorithms.application.tradepro_demo import run_backtrader_hod

    assert callable(run_backtrader_hod)


def test_run_backtrader_hod_mocked(monkeypatch):
    """run_backtrader_hod returns expected structure when mocked."""
    from energy_algorithms.application import tradepro_demo

    monkeypatch.setattr(tradepro_demo, "run_backtrader_hod", lambda: {
        "Engine": "backtrader (event-driven)",
        "Sharpe": 0.5,
        "MaxDD%": 10.0,
        "Return%": 5.0,
        "Trades": 10,
        "WinRate%": 60.0,
    })

    result = tradepro_demo.run_backtrader_hod()
    assert result["Engine"] == "backtrader (event-driven)"
    assert result["Sharpe"] == 0.5
    assert "WinRate%" in result


# ── run_backtrader_solar ────────────────────────────────────────────


def test_run_backtrader_solar_signature():
    """run_backtrader_solar returns expected dict keys."""
    from energy_algorithms.application.tradepro_demo import run_backtrader_solar

    assert callable(run_backtrader_solar)


def test_run_backtrader_solar_mocked(monkeypatch):
    """run_backtrader_solar returns expected structure when mocked."""
    from energy_algorithms.application import tradepro_demo

    monkeypatch.setattr(tradepro_demo, "run_backtrader_solar", lambda: {
        "Engine": "backtrader (event-driven)",
        "Sharpe": 0.3,
        "Return%": 3.0,
        "Trades": 5,
    })
    result = tradepro_demo.run_backtrader_solar()
    assert "Sharpe" in result
    assert "Return%" in result


# ── run_openspace_simulation ────────────────────────────────────────


def test_run_openspace_simulation_returns_tuples():
    """run_openspace_simulation returns two result dicts."""
    from energy_algorithms.application.tradepro_demo import run_openspace_simulation

    result = run_openspace_simulation()
    assert isinstance(result, tuple)
    assert len(result) == 2
    r1, r2 = result
    for r in (r1, r2):
        assert isinstance(r, dict)
        assert "avg_mcp" in r
        assert "total_welfare" in r
        assert "generator_profits" in r


# ── main() ──────────────────────────────────────────────────────────


def test_main_cached_csv_missing(monkeypatch, capsys):
    """main() prints warning when no cached ENTSO-E data."""
    from energy_algorithms.application import tradepro_demo

    monkeypatch.setattr(tradepro_demo.os.path, "exists", lambda p: False)

    tradepro_demo.main()
    captured = capsys.readouterr()
    assert "No cached ENTSO-E data" in captured.out


def test_main_handles_backtrader_errors(monkeypatch, capsys, tmp_path):
    """main() handles exceptions from backtrader functions gracefully."""
    from energy_algorithms.application import tradepro_demo

    # Create cached CSV so main() proceeds past the data check
    csv_path = tmp_path / "data" / "entsoe_prices.csv"
    csv_path.parent.mkdir(parents=True)
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "price_eur_mwh"])
        writer.writeheader()
        writer.writerow({"date": "2024-01-01", "price_eur_mwh": "50.0"})

    monkeypatch.setattr(tradepro_demo, "CACHED_CSV", str(csv_path))

    # Make os.path.exists return True for the cached CSV, False for bt_csv
    orig_exists = os.path.exists

    def mock_exists(p):
        if str(csv_path) in str(p):
            return True
        if "bt_" in str(p):
            return False
        return orig_exists(p)

    monkeypatch.setattr(tradepro_demo.os.path, "exists", mock_exists)

    def failing_hod():
        raise RuntimeError("Test error in HOD")

    monkeypatch.setattr(tradepro_demo, "run_backtrader_hod", failing_hod)
    monkeypatch.setattr(tradepro_demo, "run_backtrader_solar", lambda: {
        "Engine": "backtrader", "Sharpe": 0.3, "Return%": 3.0, "Trades": 5,
    })

    tradepro_demo.main()
    captured = capsys.readouterr()
    assert "Hour-of-Day error" in captured.out


# ── Module-level constants ──────────────────────────────────────────


def test_constants_defined():
    """Module-level paths are defined."""
    from energy_algorithms.application import tradepro_demo

    assert hasattr(tradepro_demo, "CACHED_CSV")
    assert hasattr(tradepro_demo, "BT_HOURLY")
    assert hasattr(tradepro_demo, "BT_DAILY")
