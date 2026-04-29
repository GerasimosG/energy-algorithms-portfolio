"""Tests for energy_data module — ENTSO-E data pipeline."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from energy_data.fetcher import fetch_demo_day_ahead, fetch_demo_generation_mix


def test_demo_day_ahead():
    """Demo day-ahead returns 24 hours of data."""
    r = fetch_demo_day_ahead()
    assert "ok" in r["status"]
    assert len(r["prices"]) == 24
    assert r["avg_price"] > 0
    assert r["min_price"] <= r["max_price"]


def test_demo_day_ahead_price_range():
    """Prices are in a realistic range for European markets."""
    r = fetch_demo_day_ahead()
    for p in r["prices"]:
        assert 0 <= p["price_eur_mwh"] <= 500  # realistic European range


def test_demo_day_ahead_hours():
    """All 24 hours are present and sequential."""
    r = fetch_demo_day_ahead()
    hours = [p["hour"] for p in r["prices"]]
    assert hours == list(range(1, 25))


def test_demo_generation_mix():
    """Demo generation mix returns multiple sources."""
    r = fetch_demo_generation_mix()
    assert "ok" in r["status"]
    assert len(r["generation"]) > 0
    assert r["total_mw"] > 0


def test_demo_generation_total():
    """Sum of generation types equals reported total."""
    r = fetch_demo_generation_mix()
    calculated = sum(g["mw"] for g in r["generation"])
    assert abs(calculated - r["total_mw"]) < 0.01
