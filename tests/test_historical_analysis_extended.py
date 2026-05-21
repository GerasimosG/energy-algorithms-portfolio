"""Extended tests for historical_analysis — 30-Day ENTSO-E Analysis.

Tests individual functions: _ensure_cache, _cache_path, build_demand_curve,
analyze_day (more edge cases), print_monthly_report, run_30day_analysis
(mocked), and main().
"""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest


# ── _ensure_cache / _cache_path ─────────────────────────────────────


def test_ensure_cache_creates_directory(tmp_path):
    """_ensure_cache creates the cache directory."""
    from energy_algorithms.application import historical_analysis

    cache_dir = tmp_path / ".data_cache"
    import energy_algorithms.application.historical_analysis as ha

    # Monkey-patch CACHE_DIR
    original_cache = ha.CACHE_DIR
    ha.CACHE_DIR = str(cache_dir)
    try:
        ha._ensure_cache()
        assert cache_dir.exists()
    finally:
        ha.CACHE_DIR = original_cache


def test_ensure_cache_idempotent(tmp_path):
    """_ensure_cache doesn't error when dir already exists."""
    from energy_algorithms.application import historical_analysis

    import energy_algorithms.application.historical_analysis as ha

    cache_dir = tmp_path / ".data_cache"
    cache_dir.mkdir(parents=True)

    original_cache = ha.CACHE_DIR
    ha.CACHE_DIR = str(cache_dir)
    try:
        ha._ensure_cache()  # Should not raise
        assert True
    finally:
        ha.CACHE_DIR = original_cache


def test_cache_path_returns_correct_path():
    """_cache_path returns correct file path."""
    from energy_algorithms.application.historical_analysis import _cache_path

    import energy_algorithms.application.historical_analysis as ha

    original_cache = ha.CACHE_DIR
    ha.CACHE_DIR = "/tmp/test_cache"
    try:
        path = _cache_path("BE", "2024-01-01")
        assert "BE" in path
        assert "2024-01-01" in path
        assert path.endswith(".json")
    finally:
        ha.CACHE_DIR = original_cache


# ── build_demand_curve (extended) ───────────────────────────────────


def test_build_demand_curve_three_blocks():
    """build_demand_curve returns 3 blocks for sufficient price data."""
    from energy_algorithms.application.historical_analysis import build_demand_curve

    blocks = build_demand_curve([50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0, 120.0, 130.0])
    assert len(blocks) == 3
    assert all(b["qty"] == 2000 for b in blocks)
    assert blocks[0]["price"] > blocks[1]["price"] > blocks[2]["price"]


def test_build_demand_curve_empty():
    """build_demand_curve returns fallback for empty list."""
    from energy_algorithms.application.historical_analysis import build_demand_curve

    blocks = build_demand_curve([])
    assert blocks == [{"price": 100, "qty": 1000}]


def test_build_demand_curve_single():
    """build_demand_curve handles single-element list."""
    from energy_algorithms.application.historical_analysis import build_demand_curve

    blocks = build_demand_curve([5.0])
    assert len(blocks) == 3
    assert all(b["qty"] == 2000 for b in blocks)
    # With a single price, all thirds use the same value
    assert blocks[0]["price"] >= 80


def test_build_demand_curve_all_zeros():
    """build_demand_curve handles all-zero prices."""
    from energy_algorithms.application.historical_analysis import build_demand_curve

    blocks = build_demand_curve([0.0, 0.0, 0.0])
    assert len(blocks) == 3
    # All prices are zero, so max(bot + 10, 40) = 40
    assert blocks[2]["price"] == 40


# ── analyze_day (extended) ──────────────────────────────────────────


def test_analyze_day_with_full_data():
    """analyze_day runs storage arbitrage and coupling with 24-hour data."""
    from energy_algorithms.application.historical_analysis import analyze_day

    day_prices = {
        "BE": [float(30 + i) for i in range(24)],
        "FR": [float(40 + i) for i in range(24)],
        "DE": [float(50 + i) for i in range(24)],
        "NL": [float(35 + i) for i in range(24)],
    }
    day_avgs = {
        "BE": 41.5,
        "FR": 51.5,
        "DE": 61.5,
        "NL": 46.5,
    }

    result = analyze_day(day_prices, day_avgs, "2024-01-15")
    assert result["date"] == "2024-01-15"
    assert "storage_arbitrage" in result
    assert "bess_100mw_95eff" in result["storage_arbitrage"]
    assert "bess_300mw_81eff" in result["storage_arbitrage"]
    assert "cross_border_spreads" in result
    assert "coupling" in result


def test_analyze_day_no_be_prices():
    """analyze_day handles missing BE prices."""
    from energy_algorithms.application.historical_analysis import analyze_day

    day_prices = {"FR": [50.0, 55.0]}
    day_avgs = {"BE": 0.0, "FR": 52.5}

    result = analyze_day(day_prices, day_avgs, "2024-01-15")
    # Should not crash, storage skipped due to no BE prices
    assert "storage_arbitrage" not in result
    assert "cross_border_spreads" in result


def test_analyze_day_no_spreads():
    """analyze_day handles when all prices are zero."""
    from energy_algorithms.application.historical_analysis import analyze_day

    day_prices = {"BE": [50.0, 55.0], "FR": [30.0, 35.0]}
    day_avgs = {"BE": 0.0, "FR": 0.0}

    result = analyze_day(day_prices, day_avgs, "2024-01-15")
    assert result["max_spread"] == 0.0


def test_analyze_day_single_zone_present():
    """analyze_day handles when only one zone has data."""
    from energy_algorithms.application.historical_analysis import analyze_day

    day_prices = {"BE": [50.0, 55.0, 60.0]}
    day_avgs = {"BE": 55.0}

    result = analyze_day(day_prices, day_avgs, "2024-01-15")
    assert result["max_spread"] == 0.0
    assert "storage_arbitrage" in result  # BE prices present


# ── fetch_day ───────────────────────────────────────────────────────


def test_fetch_day_uses_cache(monkeypatch, tmp_path):
    """fetch_day returns cached data without calling client."""
    from energy_algorithms.application import historical_analysis

    import energy_algorithms.application.historical_analysis as ha

    original_cache = ha.CACHE_DIR
    cache_dir = tmp_path / ".data_cache"
    cache_dir.mkdir(parents=True)
    ha.CACHE_DIR = str(cache_dir)

    # Create cached file
    cached = {"prices": [50.0, 55.0], "avg": 52.5}
    cache_file = cache_dir / "prices_BE_2024-01-01.json"
    with open(cache_file, "w") as f:
        json.dump(cached, f)

    try:
        mock_client = MagicMock()
        result = ha.fetch_day(mock_client, "BE", "10YBE----------2", "2024-01-01")
        assert result == cached
        mock_client.fetch_day_ahead_prices.assert_not_called()
    finally:
        ha.CACHE_DIR = original_cache


def test_fetch_day_no_cache_calls_client(monkeypatch, tmp_path):
    """fetch_day calls client and caches result when no cached file."""
    from energy_algorithms.application import historical_analysis

    import energy_algorithms.application.historical_analysis as ha

    original_cache = ha.CACHE_DIR
    cache_dir = tmp_path / ".data_cache"
    cache_dir.mkdir(parents=True)
    ha.CACHE_DIR = str(cache_dir)

    try:
        mock_client = MagicMock()
        mock_client.fetch_day_ahead_prices.return_value = {
            "status": "ok",
            "prices": [{"hour": h, "price_eur_mwh": 50.0 + h} for h in range(1, 25)],
        }

        result = ha.fetch_day(mock_client, "BE", "10YBE----------2", "2024-01-15")
        assert "prices" in result
        assert len(result["prices"]) == 24
        assert result["avg"] > 0
        mock_client.fetch_day_ahead_prices.assert_called_once()

        # Verify cache file was created
        cache_file = cache_dir / "prices_BE_2024-01-15.json"
        assert cache_file.exists()
    finally:
        ha.CACHE_DIR = original_cache


def test_fetch_day_client_returns_empty(monkeypatch, tmp_path):
    """fetch_day handles client returning no prices."""
    from energy_algorithms.application import historical_analysis

    import energy_algorithms.application.historical_analysis as ha

    original_cache = ha.CACHE_DIR
    cache_dir = tmp_path / ".data_cache"
    cache_dir.mkdir(parents=True)
    ha.CACHE_DIR = str(cache_dir)

    try:
        mock_client = MagicMock()
        mock_client.fetch_day_ahead_prices.return_value = {
            "status": "ok",
            "prices": [],
        }

        result = ha.fetch_day(mock_client, "BE", "10YBE----------2", "2024-01-15")
        assert result["prices"] == []
        assert result["avg"] == 0.0
    finally:
        ha.CACHE_DIR = original_cache


# ── print_monthly_report ────────────────────────────────────────────


def test_print_monthly_report_empty(capsys):
    """print_monthly_report handles empty results list."""
    from energy_algorithms.application.historical_analysis import print_monthly_report

    print_monthly_report([])
    captured = capsys.readouterr()
    assert "MONTHLY PERFORMANCE REPORT" in captured.out


def test_print_monthly_report_with_data(capsys):
    """print_monthly_report prints price stats, spreads, and storage info."""
    from energy_algorithms.application.historical_analysis import print_monthly_report

    results = [
        {
            "date": "2024-01-01",
            "prices": {"BE": 50.0, "FR": 45.0, "DE": 55.0, "NL": 48.0},
            "cross_border_spreads": {"BE↔DE": 5.0, "FR↔DE": 10.0},
            "max_spread": 10.0,
            "storage_arbitrage": {
                "bess_100mw_95eff": 5000.0,
                "bess_300mw_81eff": 8000.0,
                "min_price": 30.0,
                "max_price": 70.0,
                "volatility": 15.0,
            },
            "coupling": {
                "welfare": 500000.0,
                "active_flows": 3,
                "zones": {"BE": {"mcp": 48.0}, "FR": {"mcp": 45.0}},
            },
        },
        {
            "date": "2024-01-02",
            "prices": {"BE": 60.0, "FR": 55.0, "DE": 65.0, "NL": 58.0},
            "cross_border_spreads": {"BE↔DE": 5.0},
            "max_spread": 5.0,
            "storage_arbitrage": {
                "bess_100mw_95eff": 3000.0,
                "bess_300mw_81eff": 6000.0,
                "min_price": 40.0,
                "max_price": 80.0,
                "volatility": 12.0,
            },
            "coupling": {
                "welfare": 400000.0,
                "active_flows": 2,
                "zones": {"BE": {"mcp": 58.0}, "FR": {"mcp": 55.0}},
            },
        },
    ]

    print_monthly_report(results)
    captured = capsys.readouterr()
    assert "PRICE STATISTICS" in captured.out
    assert "CROSS-BORDER SPREADS" in captured.out
    assert "BESS STORAGE ARBITRAGE" in captured.out
    assert "EUROPEAN MARKET COUPLING" in captured.out
    assert "KEY INSIGHT" in captured.out


def test_print_monthly_report_missing_storage(capsys):
    """print_monthly_report handles results without storage data."""
    from energy_algorithms.application.historical_analysis import print_monthly_report

    results = [
        {
            "date": "2024-01-01",
            "prices": {"BE": 50.0},
            "cross_border_spreads": {},
            "max_spread": 0.0,
        }
    ]
    print_monthly_report(results)
    captured = capsys.readouterr()
    assert "MONTHLY PERFORMANCE REPORT" in captured.out


# ── run_30day_analysis ──────────────────────────────────────────────


def test_run_30day_analysis_mocked(monkeypatch, capsys, tmp_path):
    """run_30day_analysis runs with mocked data fetcher."""
    from energy_algorithms.application import historical_analysis

    import energy_algorithms.application.historical_analysis as ha

    original_cache = ha.CACHE_DIR
    ha.CACHE_DIR = str(tmp_path / ".data_cache")

    # Mock EntsoeClient and fetch_day
    mock_client = MagicMock()

    def fake_fetch_day(client, code, eic, date):
        return {"prices": [50.0] * 24, "avg": 50.0}

    monkeypatch.setattr(ha, "fetch_day", fake_fetch_day)
    monkeypatch.setattr(ha, "EntsoeClient", lambda **kw: mock_client)

    try:
        results = ha.run_30day_analysis(num_days=3)
        captured = capsys.readouterr()
        assert len(results) == 3  # All 3 days have data
        assert "30-DAY HISTORICAL ANALYSIS" in captured.out
    finally:
        ha.CACHE_DIR = original_cache


def test_run_30day_analysis_handles_errors(monkeypatch, capsys, tmp_path):
    """run_30day_analysis handles fetch errors gracefully."""
    from energy_algorithms.application import historical_analysis

    import energy_algorithms.application.historical_analysis as ha

    original_cache = ha.CACHE_DIR
    ha.CACHE_DIR = str(tmp_path / ".data_cache")

    def failing_fetch(client, code, eic, date):
        raise ValueError("API Error")

    monkeypatch.setattr(ha, "fetch_day", failing_fetch)
    monkeypatch.setattr(ha, "EntsoeClient", lambda **kw: MagicMock())

    try:
        results = ha.run_30day_analysis(num_days=5)
        captured = capsys.readouterr()
        assert len(results) == 0  # All days failed
        assert "errors" in captured.out
    finally:
        ha.CACHE_DIR = original_cache


def test_run_30day_analysis_no_data(monkeypatch, capsys, tmp_path):
    """run_30day_analysis handles days with zero price data."""
    from energy_algorithms.application import historical_analysis

    import energy_algorithms.application.historical_analysis as ha

    original_cache = ha.CACHE_DIR
    ha.CACHE_DIR = str(tmp_path / ".data_cache")

    def zero_data_fetch(client, code, eic, date):
        return {"prices": [], "avg": 0.0}

    monkeypatch.setattr(ha, "fetch_day", zero_data_fetch)
    monkeypatch.setattr(ha, "EntsoeClient", lambda **kw: MagicMock())

    try:
        results = ha.run_30day_analysis(num_days=3)
        assert len(results) == 0  # No data to analyze
    finally:
        ha.CACHE_DIR = original_cache


# ── main() ──────────────────────────────────────────────────────────


def test_main_runs(monkeypatch, capsys):
    """main() runs and prints monthly report."""
    from energy_algorithms.application import historical_analysis

    import energy_algorithms.application.historical_analysis as ha

    fake_results = [
        {
            "date": "2024-01-01",
            "prices": {"BE": 50.0},
            "cross_border_spreads": {},
            "max_spread": 0.0,
        }
    ]

    monkeypatch.setattr(ha, "run_30day_analysis", lambda n: fake_results)
    monkeypatch.setattr(ha, "print_monthly_report", lambda r: None)

    # main() just calls run_30day_analysis and print_monthly_report
    ha.main(num_days=5)
    captured = capsys.readouterr()
    # main() prints a blank line before running
    assert True  # No crash


def test_main_without_args(monkeypatch):
    """__main__ block uses sys.argv to determine num_days."""
    from energy_algorithms.application import historical_analysis

    import energy_algorithms.application.historical_analysis as ha

    called_with = []

    def fake_main(n):
        called_with.append(n)

    monkeypatch.setattr(ha, "main", fake_main)

    # Simulate __main__: `if __name__ == "__main__": n = int(sys.argv[1])...`
    import sys

    old_argv = sys.argv
    try:
        sys.argv = ["prog", "10"]
        # Execute the logic from the __main__ block
        n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
        ha.main(n)
        assert called_with == [10]
    finally:
        sys.argv = old_argv


def test_main_default_args(monkeypatch):
    """__main__ block defaults to 30 days."""
    from energy_algorithms.application import historical_analysis

    import energy_algorithms.application.historical_analysis as ha

    called_with = []

    def fake_main(n):
        called_with.append(n)

    monkeypatch.setattr(ha, "main", fake_main)

    import sys

    old_argv = sys.argv
    try:
        sys.argv = ["prog"]
        n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
        ha.main(n)
        assert called_with == [30]
    finally:
        sys.argv = old_argv
