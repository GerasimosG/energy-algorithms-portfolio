"""Tests for Multi-Day Market Coupling — energy_markets module."""

from __future__ import annotations

import pytest

from energy_algorithms.domain.markets.multi_day import solve_multi_day

# ── 1. Basic 2-day coupling with storage ──────────────────────────

def test_2day_with_storage_welfare_higher():
 """2-day coupling: battery charges cheap day 1, discharges expensive day 2,
 yielding higher welfare than no-storage baseline."""

 # Day 1: very cheap (North 5 €/MWh), moderate demand
 # Day 2: very expensive, demand higher
 zones_per_day = [
 [ # Day 1
 {
 "name": "North",
 "supply": [{"price": 5, "qty": 500}],
 "demand": [{"price": 100, "qty": 200}],
 },
 {
 "name": "South",
 "supply": [{"price": 50, "qty": 300}],
 "demand": [{"price": 100, "qty": 250}],
 },
 ],
 [ # Day 2 — North cheap supply exhausted, prices high
 {
 "name": "North",
 "supply": [{"price": 150, "qty": 100}],
 "demand": [{"price": 100, "qty": 300}],
 },
 {
 "name": "South",
 "supply": [{"price": 60, "qty": 200}],
 "demand": [{"price": 100, "qty": 350}],
 },
 ],
 ]

 atc_per_day = [
 {(0, 1): 200},
 {(0, 1): 200},
 ]

 storage_config = {
 "capacity": 100.0,
 "max_power": 50.0,
 "eff_in": 0.95,
 "eff_out": 0.95,
 "initial_soc": 0.0,
 }

 # ── With storage ──
 result_with = solve_multi_day(
 zones_per_day, atc_per_day, storage_config, horizon_days=2
 )
 assert result_with["status"] == "Optimal"
 assert result_with["welfare"] > 0
 assert "storage_schedule" in result_with
 assert result_with["storage_schedule"] is not None

 # ── Without storage ──
 result_without = solve_multi_day(
 zones_per_day, atc_per_day, storage_config=None, horizon_days=2
 )
 assert result_without["status"] == "Optimal"
 assert result_without["welfare"] > 0

 # Storage should improve total welfare
 assert result_with["welfare"] >= result_without["welfare"]
 # Energy should be shifted between days
 assert result_with["total_energy_shifted"] >= 0

# ── 2. No-storage baseline (reduces to independent per-day solves) ─

def test_no_storage_independent_days():
 """Without storage, each day is independent and welfare = day1 + day2."""
 zones_per_day = [
 [
 {"name": "A", "supply": [{"price": 20, "qty": 100}],
 "demand": [{"price": 100, "qty": 80}]},
 {"name": "B", "supply": [{"price": 40, "qty": 100}],
 "demand": [{"price": 100, "qty": 60}]},
 ],
 [
 {"name": "A", "supply": [{"price": 30, "qty": 100}],
 "demand": [{"price": 100, "qty": 70}]},
 {"name": "B", "supply": [{"price": 50, "qty": 100}],
 "demand": [{"price": 100, "qty": 90}]},
 ],
 ]
 atc_per_day = [
 {(0, 1): 50},
 {(0, 1): 50},
 ]

 result = solve_multi_day(zones_per_day, atc_per_day, storage_config=None, horizon_days=2)

 assert result["status"] == "Optimal"
 assert result["welfare"] > 0
 # No storage schedule when storage_config is None
 assert result["storage_schedule"] is None
 assert result["total_energy_shifted"] == 0.0
 # Per-day results exist
 assert len(result["per_day"]) == 2


def test_single_atc_pair_allows_reverse_flow_without_storage():
 """Multi-day ATC uses the same bidirectional corridor convention as multi-zone."""
 zones_per_day = [
 [
 {
 "name": "A",
 "supply": [{"price": 100, "qty": 100}],
 "demand": [{"price": 150, "qty": 100}],
 },
 {
 "name": "B",
 "supply": [{"price": 10, "qty": 100}],
 "demand": [{"price": 20, "qty": 100}],
 },
 ],
 ]

 result = solve_multi_day(zones_per_day, [{(0, 1): 100}], storage_config=None, horizon_days=1)

 assert result["status"] == "Optimal"
 assert result["per_day"][0]["flows"] == {"B→A": 100.0}
 assert result["per_day"][0]["zones"]["A"]["supply_cleared_mw"] == 0.0
 assert result["per_day"][0]["zones"]["A"]["demand_cleared_mw"] == 100.0
 assert result["per_day"][0]["zones"]["B"]["supply_cleared_mw"] == 100.0

# ── 3. Storage SoC carry-over ─────────────────────────────────────

def test_storage_soc_carryover():
 """Storage SoC at end of day 0 equals start-SoC of day 1
 (carry-over constraint enforced by LP)."""
 zones_per_day = [
 [
 {"name": "N", "supply": [{"price": 5, "qty": 200}],
 "demand": [{"price": 100, "qty": 100}]},
 {"name": "S", "supply": [{"price": 80, "qty": 200}],
 "demand": [{"price": 100, "qty": 150}]},
 ],
 [
 {"name": "N", "supply": [{"price": 150, "qty": 100}],
 "demand": [{"price": 100, "qty": 200}]},
 {"name": "S", "supply": [{"price": 60, "qty": 200}],
 "demand": [{"price": 100, "qty": 100}]},
 ],
 ]
 atc_per_day = [
 {(0, 1): 100},
 {(0, 1): 100},
 ]

 storage_config = {
 "capacity": 80.0,
 "max_power": 40.0,
 "eff_in": 0.95,
 "eff_out": 0.95,
 "initial_soc": 0.0,
 }

 result = solve_multi_day(zones_per_day, atc_per_day, storage_config, horizon_days=2)
 assert result["status"] == "Optimal"

 sched = result["storage_schedule"]
 assert "day_0" in sched
 assert "day_1" in sched

 # End-of-day SoC for day 0 must equal start-of-day SoC for day 1
 end_day0 = sched["day_0"][-1]["soc_end"]
 start_day1 = sched["day_1"][0]["soc_start"]
 assert abs(end_day0 - start_day1) < 0.01, (
 f"Carry-over failed: day0 end={end_day0}, day1 start={start_day1}"
 )


def test_storage_actually_shifts_energy_across_days():
 """Storage should charge on a cheap surplus day and discharge on a scarce day."""
 zones_per_day = [
 [
 {
 "name": "Hub",
 "supply": [{"price": 5, "qty": 200}],
 "demand": [{"price": 100, "qty": 100}],
 },
 ],
 [
 {
 "name": "Hub",
 "supply": [],
 "demand": [{"price": 100, "qty": 40}],
 },
 ],
 ]
 storage_config = {
 "capacity": 50.0,
 "max_power": 50.0,
 "eff_in": 1.0,
 "eff_out": 1.0,
 "initial_soc": 0.0,
 }

 result = solve_multi_day(zones_per_day, [{}, {}], storage_config, horizon_days=2)

 assert result["status"] == "Optimal"
 assert result["storage_schedule"]["day_0"][0]["charge"] == 40.0
 assert result["storage_schedule"]["day_1"][0]["discharge"] == 40.0
 assert result["total_energy_shifted"] == 40.0

# ── 4. Infeasible storage configuration ───────────────────────────

def test_zero_capacity_storage():
 """Storage with capacity=0 still yields valid optimal solution."""
 zones_per_day = [
 [
 {"name": "A", "supply": [{"price": 10, "qty": 100}],
 "demand": [{"price": 100, "qty": 80}]},
 {"name": "B", "supply": [{"price": 40, "qty": 100}],
 "demand": [{"price": 100, "qty": 60}]},
 ],
 ]
 atc_per_day = [{(0, 1): 50}]

 storage_config = {
 "capacity": 0.0,
 "max_power": 0.0,
 "eff_in": 0.95,
 "eff_out": 0.95,
 "initial_soc": 0.0,
 }

 result = solve_multi_day(zones_per_day, atc_per_day, storage_config, horizon_days=1)
 assert result["status"] == "Optimal"
 assert result["welfare"] >= 0

 # Storage SoC should stay at 0 with no charge/discharge
 for entry in result["storage_schedule"]["day_0"]:
 assert entry["charge"] == 0.0
 assert entry["discharge"] == 0.0
 assert entry["soc_start"] == 0.0
 assert entry["soc_end"] == 0.0

# ── 5. Multi-zone multi-day (3 zones × 2 days) ────────────────────

def test_multi_zone_multi_day():
 """3 zones × 2 days: verify welfare is positive and per-day results exist."""
 zones_per_day = [
 [
 {"name": "X", "supply": [{"price": 10, "qty": 200}],
 "demand": [{"price": 100, "qty": 150}]},
 {"name": "Y", "supply": [{"price": 40, "qty": 200}],
 "demand": [{"price": 100, "qty": 100}]},
 {"name": "Z", "supply": [{"price": 70, "qty": 200}],
 "demand": [{"price": 100, "qty": 120}]},
 ],
 [
 {"name": "X", "supply": [{"price": 15, "qty": 200}],
 "demand": [{"price": 100, "qty": 100}]},
 {"name": "Y", "supply": [{"price": 35, "qty": 200}],
 "demand": [{"price": 100, "qty": 150}]},
 {"name": "Z", "supply": [{"price": 80, "qty": 200}],
 "demand": [{"price": 100, "qty": 140}]},
 ],
 ]
 atc_per_day = [
 {(0, 1): 100, (1, 2): 80},
 {(0, 1): 100, (1, 2): 80},
 ]

 storage_config = {
 "capacity": 50.0,
 "max_power": 25.0,
 "eff_in": 0.95,
 "eff_out": 0.95,
 "initial_soc": 0.0,
 }

 result = solve_multi_day(zones_per_day, atc_per_day, storage_config, horizon_days=2)
 assert result["status"] == "Optimal"
 assert result["welfare"] > 0
 assert len(result["per_day"]) == 2
 assert len(result["storage_schedule"]) == 2 # one per day
 assert result["total_energy_shifted"] >= 0

# ── 6. Single-day with storage (degenerate multi-day) ─────────────

def test_single_day_with_storage():
 """A single day with storage should still solve correctly."""
 zones_per_day = [
 [
 {"name": "A", "supply": [{"price": 5, "qty": 200}],
 "demand": [{"price": 100, "qty": 100}]},
 {"name": "B", "supply": [{"price": 50, "qty": 200}],
 "demand": [{"price": 100, "qty": 150}]},
 ],
 ]
 atc_per_day = [{(0, 1): 100}]

 storage_config = {
 "capacity": 30.0,
 "max_power": 15.0,
 "eff_in": 0.95,
 "eff_out": 0.95,
 "initial_soc": 0.0,
 }

 result = solve_multi_day(zones_per_day, atc_per_day, storage_config, horizon_days=1)
 assert result["status"] == "Optimal"
 assert result["welfare"] > 0
 assert len(result["per_day"]) == 1
 assert "day_0" in result["storage_schedule"]

# ── 7. Input validation ───────────────────────────────────────────

def test_mismatched_days_raises():
 """zones_per_day and atc_per_day must have same length matching horizon_days."""
 zones_per_day = [
 [{"name": "A", "supply": [{"price": 10, "qty": 100}],
 "demand": [{"price": 100, "qty": 50}]}],
 ]
 # atc_per_day has 2 entries but zones_per_day has 1
 atc_per_day = [
 {},
 {},
 ]

 with pytest.raises(ValueError, match="same number of days"):
 solve_multi_day(zones_per_day, atc_per_day, storage_config=None, horizon_days=1)

def test_horizon_days_mismatch():
 """horizon_days must match the number of entries in zones_per_day."""
 zones_per_day = [
 [{"name": "A", "supply": [{"price": 10, "qty": 100}],
 "demand": [{"price": 100, "qty": 50}]}],
 [{"name": "A", "supply": [{"price": 10, "qty": 100}],
 "demand": [{"price": 100, "qty": 50}]}],
 ]
 atc_per_day = [{}, {}]

 with pytest.raises(ValueError, match="zones_per_day"):
 solve_multi_day(zones_per_day, atc_per_day, storage_config=None, horizon_days=3)
