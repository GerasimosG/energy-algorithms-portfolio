"""Tests for energy_data module — ENTSO-E data pipeline."""

from __future__ import annotations

from energy_algorithms.adapters.entsoe_client import (
 DOC_ACTUAL_GENERATION,
 EntsoeClient,
 fetch_demo_day_ahead,
 fetch_demo_generation_mix,
)


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
 assert 0 <= p["price_eur_mwh"] <= 500 # realistic European range

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


def test_generation_parser_aggregates_duplicate_psr_types():
 """ENTSO-E may return several TimeSeries for the same production type."""
 xml = """<?xml version="1.0" encoding="UTF-8"?>
 <GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
 <TimeSeries>
 <MktPSRType><psrType>B10</psrType></MktPSRType>
 <Period>
 <Point><position>1</position><quantity>10</quantity></Point>
 <Point><position>2</position><quantity>30</quantity></Point>
 </Period>
 </TimeSeries>
 <TimeSeries>
 <MktPSRType><psrType>B10</psrType></MktPSRType>
 <Period>
 <Point><position>1</position><quantity>5</quantity></Point>
 <Point><position>2</position><quantity>15</quantity></Point>
 </Period>
 </TimeSeries>
 <TimeSeries>
 <MktPSRType><psrType>B16</psrType></MktPSRType>
 <Period>
 <Point><position>1</position><quantity>25</quantity></Point>
 <Point><position>2</position><quantity>25</quantity></Point>
 </Period>
 </TimeSeries>
 </GL_MarketDocument>
 """
 client = EntsoeClient(api_key="")

 result = client._parse_response(xml, DOC_ACTUAL_GENERATION, "BE", "2024-03-15")

 generation = {source["type"]: source["mw"] for source in result["generation"]}
 assert generation["Hydro Pumped Storage"] == 30.0
 assert generation["Solar"] == 25.0
 assert result["total_mw"] == 55.0
