"""Smoke tests for the historical analysis pipeline."""
from __future__ import annotations


def test_historical_analysis_imports():
 """Module imports without error."""
 from energy_algorithms.application import historical_analysis
 assert historical_analysis is not None


def test_historical_analysis_build_demand_curve():
 """build_demand_curve returns valid blocks."""
 from energy_algorithms.application.historical_analysis import build_demand_curve

 curves = build_demand_curve([50, 60, 70, 80, 90, 100])
 assert len(curves) > 0
 for c in curves:
 assert "price" in c
 assert "qty" in c
 assert c["qty"] > 0


def test_historical_analysis_analyze_day():
 """analyze_day returns structured results."""
 from energy_algorithms.application.historical_analysis import analyze_day

 day_prices = {"BE": [50, 55, 60], "FR": [30, 35, 40]}
 day_avgs = {"BE": 55.0, "FR": 35.0}
 result = analyze_day(day_prices, day_avgs, "2026-04-01")
 assert result["date"] == "2026-04-01"
 assert result["prices"]["BE"] == 55.0
 assert "cross_border_spreads" in result
 assert "storage_arbitrage" in result


def test_historical_analysis_analyze_day_no_prices():
 """analyze_day handles missing data gracefully."""
 from energy_algorithms.application.historical_analysis import analyze_day

 result = analyze_day({}, {}, "2026-04-01")
 assert result["date"] == "2026-04-01"
 assert "cross_border_spreads" in result
 assert result["max_spread"] == 0.0
