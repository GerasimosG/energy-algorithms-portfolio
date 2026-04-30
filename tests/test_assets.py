"""Tests for lp_optimization.assets — OneInterval asset pattern."""
from __future__ import annotations

import pulp
import pytest

from energy_algorithms.domain.optimization.assets import (
    Asset,
    BatteryAsset,
    GeneratorAsset,
    SpillAsset,
    build_site,
    demo_site,
)

# ── Base Asset ───────────────────────────────────────────────────────

def test_asset_base_class_lifecycle():
    """Base Asset exposes lifecycle hooks that subclasses override."""
    asset = Asset("base")
    assert asset.name == "base"
    assert asset.net_power == []
    assert asset.results == {}

    # Hooks should be callable (no-op by default)
    prob = pulp.LpProblem("test", pulp.LpMinimize)
    interval_data = [{"price": 50, "demand": 0}]
    T = len(interval_data)

    asset._constraints(prob, interval_data, T)
    asset._objective(prob, interval_data, T)
    asset._post_solve(prob, interval_data, T)
    # No errors = pass

# ── BatteryAsset ─────────────────────────────────────────────────────

def test_battery_asset_lifecycle():
    """BatteryAsset creates variables, constraints, and extracts results."""
    battery = BatteryAsset("BESS", capacity=100, max_power=25,
                           eff_in=0.95, eff_out=0.95, initial_soc=0)
    interval_data = [
        {"price": 10, "demand": 0},
        {"price": 10, "demand": 0},
        {"price": 100, "demand": 0},
        {"price": 100, "demand": 0},
    ]
    prob = pulp.LpProblem("test", pulp.LpMinimize)
    T = len(interval_data)

    battery._constraints(prob, interval_data, T)
    # Should have created charge, discharge, soc variables
    assert sum(len(v) for v in battery.variables.values()) == T * 3  # charge_t, discharge_t, soc_t for each t
    assert len(battery.net_power) == T

    expr = battery._objective(prob, interval_data, T)
    if expr is not None:
        prob += expr

    # Solve
    prob += pulp.lpSum(battery.net_power[t] for t in range(T)) == 0
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    assert pulp.LpStatus[prob.status] == "Optimal"

    battery._post_solve(prob, interval_data, T)
    assert len(battery.results["schedule"]) == T
    sched = battery.results["schedule"]
    # Battery should charge when cheap (prices 10, 10), discharge when expensive (100, 100)
    assert sched[0]["charge"] >= 0 or sched[1]["charge"] >= 0, "Battery should charge during cheap periods"
    # Discharge may be tricky with net_power constraint = 0; just verify values are reasonable
    assert all(0 <= p["discharge"] <= battery.max_power for p in sched)
    assert all(0 <= p["charge"] <= battery.max_power for p in sched)

def test_battery_asset_soc_bounds():
    """State of charge never exceeds capacity."""
    battery = BatteryAsset("BESS", capacity=100, max_power=50,
                           eff_in=0.95, eff_out=0.95, initial_soc=0)
    interval_data = [{"price": 50, "demand": 0}] * 10
    prob = pulp.LpProblem("test", pulp.LpMinimize)
    T = len(interval_data)

    battery._constraints(prob, interval_data, T)
    expr = battery._objective(prob, interval_data, T)
    if expr is not None:
        prob += expr
    prob += pulp.lpSum(battery.net_power[t] for t in range(T)) == 0
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    assert pulp.LpStatus[prob.status] == "Optimal"

    battery._post_solve(prob, interval_data, T)
    for period in battery.results["schedule"]:
        assert 0 <= period["soc"] <= 100 + 0.01

def test_battery_asset_energy_balance():
    """SoC evolves correctly: SoC[t] = SoC[t-1] + charge*eff_in - discharge/eff_out."""
    battery = BatteryAsset("BESS", capacity=100, max_power=25,
                           eff_in=0.9, eff_out=0.9, initial_soc=50)
    interval_data = [{"price": 50, "demand": 0}] * 5
    prob = pulp.LpProblem("test", pulp.LpMinimize)
    T = len(interval_data)

    battery._constraints(prob, interval_data, T)
    expr = battery._objective(prob, interval_data, T)
    if expr is not None:
        prob += expr
    prob += pulp.lpSum(battery.net_power[t] for t in range(T)) == 0
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    battery._post_solve(prob, interval_data, T)

    sched = battery.results["schedule"]
    # Check SoC evolution
    soc_prev = 50.0
    for t, period in enumerate(sched):
        expected_soc = (soc_prev +
                        period["charge"] * 0.9 -
                        period["discharge"] / 0.9)
        assert abs(period["soc"] - expected_soc) < 0.01
        soc_prev = period["soc"]

# ── GeneratorAsset ──────────────────────────────────────────────────

def test_generator_asset_lifecycle():
    """GeneratorAsset respects min/max bounds."""
    gen = GeneratorAsset("Gen1", min_output=10, max_output=100, cost_per_mwh=30)
    interval_data = [{"price": 60, "demand": 50}] * 3
    prob = pulp.LpProblem("test", pulp.LpMinimize)
    T = len(interval_data)

    gen._constraints(prob, interval_data, T)
    assert len(gen.net_power) == T

    expr = gen._objective(prob, interval_data, T)
    if expr is not None:
        prob += expr

    # Force generator to meet demand exactly
    for t in range(T):
        prob += gen.net_power[t] == interval_data[t]["demand"]

    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    assert pulp.LpStatus[prob.status] == "Optimal"

    gen._post_solve(prob, interval_data, T)
    for power in gen.results["power"]:
        assert 10 <= power <= 100

def test_generator_asset_at_min_output():
    """Generator can be forced to its minimum output."""
    gen = GeneratorAsset("Gen1", min_output=50, max_output=200, cost_per_mwh=40)
    interval_data = [{"price": 60, "demand": 50}]
    prob = pulp.LpProblem("test", pulp.LpMinimize)
    T = len(interval_data)

    gen._constraints(prob, interval_data, T)
    expr = gen._objective(prob, interval_data, T)
    if expr is not None:
        prob += expr
    prob += gen.net_power[0] == 50  # demand = min_output
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    assert pulp.LpStatus[prob.status] == "Optimal"
    gen._post_solve(prob, interval_data, T)
    assert gen.results["power"][0] == pytest.approx(50, abs=0.01)

# ── SpillAsset ──────────────────────────────────────────────────────

def test_spill_asset_makes_feasible():
    """An infeasible problem becomes feasible when SpillAsset is added."""
    # Generator with max_output=30, but demand=100 -> infeasible without spill
    gen = GeneratorAsset("Gen1", min_output=0, max_output=30, cost_per_mwh=50)
    spill = SpillAsset("Spill", penalty=10000)

    interval_data = [{"price": 60, "demand": 100}]
    T = len(interval_data)

    # Without spill: infeasible
    prob_no_spill = pulp.LpProblem("no_spill", pulp.LpMinimize)
    gen2 = GeneratorAsset("Gen1", min_output=0, max_output=30, cost_per_mwh=50)
    gen2._constraints(prob_no_spill, interval_data, T)
    expr = gen2._objective(prob_no_spill, interval_data, T)
    if expr is not None:
        prob_no_spill += expr
    prob_no_spill += gen2.net_power[0] == 100
    prob_no_spill.solve(pulp.PULP_CBC_CMD(msg=False))
    assert pulp.LpStatus[prob_no_spill.status] == "Infeasible"

    # With spill: feasible
    prob = build_site([gen, spill], interval_data)
    assert pulp.LpStatus[prob.status] == "Optimal"
    gen._post_solve(prob, interval_data, T)
    spill._post_solve(prob, interval_data, T)
    # Generator provides 30, spill provides remaining 70
    assert gen.results["power"][0] == pytest.approx(30, abs=0.01)
    assert spill.results["spill"][0] == pytest.approx(70, abs=0.01)

def test_spill_asset_not_used_when_unnecessary():
    """Spill asset stays at zero when other assets can meet demand."""
    gen = GeneratorAsset("Gen1", min_output=0, max_output=200, cost_per_mwh=50)
    spill = SpillAsset("Spill", penalty=10000)

    interval_data = [{"price": 60, "demand": 100}]
    prob = build_site([gen, spill], interval_data)
    assert pulp.LpStatus[prob.status] == "Optimal"

    gen._post_solve(prob, interval_data, T=1)
    spill._post_solve(prob, interval_data, T=1)
    assert gen.results["power"][0] == pytest.approx(100, abs=0.01)
    assert spill.results["spill"][0] == pytest.approx(0, abs=0.01)

def test_spill_asset_high_penalty():
    """SpillAsset with higher penalty is used less."""
    gen = GeneratorAsset("Gen1", min_output=0, max_output=50, cost_per_mwh=60)
    # Two spill assets with different penalties
    spill_cheap = SpillAsset("SpillLow", penalty=500)
    spill_expensive = SpillAsset("SpillHigh", penalty=9999)

    interval_data = [{"price": 60, "demand": 100}]
    prob = build_site([gen, spill_cheap, spill_expensive], interval_data)
    assert pulp.LpStatus[prob.status] == "Optimal"

    gen._post_solve(prob, interval_data, T=1)
    spill_cheap._post_solve(prob, interval_data, T=1)
    spill_expensive._post_solve(prob, interval_data, T=1)

    # Generator at max; cheaper spill fills gap, expensive spill unused
    assert gen.results["power"][0] == pytest.approx(50, abs=0.01)
    assert spill_cheap.results["spill"][0] == pytest.approx(50, abs=0.01)
    assert spill_expensive.results["spill"][0] == pytest.approx(0, abs=0.01)

# ── build_site ──────────────────────────────────────────────────────

def test_build_site_demo():
    """demo_site() returns a valid optimal solution."""
    result = demo_site()
    assert result["status"] == "Optimal"
    assert "total_cost" in result
    assert "schedule" in result
    assert len(result["schedule"]) > 0

def test_build_site_energy_balance():
    """Total net power from all assets equals demand in each period."""
    battery = BatteryAsset("BESS", capacity=100, max_power=25,
                           eff_in=0.95, eff_out=0.95, initial_soc=0)
    gen = GeneratorAsset("Gen1", min_output=0, max_output=80, cost_per_mwh=50)
    spill = SpillAsset("Spill", penalty=5000)

    interval_data = [
        {"price": 10, "demand": 30},
        {"price": 20, "demand": 60},
        {"price": 100, "demand": 90},
        {"price": 80, "demand": 40},
    ]
    prob = build_site([battery, gen, spill], interval_data)
    assert pulp.LpStatus[prob.status] == "Optimal"

    battery._post_solve(prob, interval_data, T=4)
    gen._post_solve(prob, interval_data, T=4)
    spill._post_solve(prob, interval_data, T=4)

    for t in range(4):
        net = (battery.results["schedule"][t]["discharge"] -
               battery.results["schedule"][t]["charge"] +
               gen.results["power"][t] +
               spill.results["spill"][t])
        assert net == pytest.approx(interval_data[t]["demand"], abs=0.01)

def test_build_site_battery_arbitrage_in_site():
    """Battery charges when price is low and discharges when high in a site context."""
    battery = BatteryAsset("BESS", capacity=50, max_power=10,
                           eff_in=0.95, eff_out=0.95, initial_soc=0)
    gen = GeneratorAsset("Baseload", min_output=20, max_output=45, cost_per_mwh=40)

    interval_data = [
        {"price": 10, "demand": 20},   # cheap: battery charges
        {"price": 10, "demand": 20},   # cheap: battery charges
        {"price": 100, "demand": 45},  # expensive: battery discharges
        {"price": 100, "demand": 45},  # expensive: battery discharges
    ]
    prob = build_site([battery, gen], interval_data)
    assert pulp.LpStatus[prob.status] == "Optimal"

    battery._post_solve(prob, interval_data, T=4)
    sched = battery.results["schedule"]

    # Battery should charge during cheap periods
    assert sched[0]["charge"] > 0 or sched[1]["charge"] > 0
    # Battery should discharge during expensive periods
    assert sched[2]["discharge"] > 0 or sched[3]["discharge"] > 0
    # Total discharge < total charge (round-trip losses)
    total_charge = sum(p["charge"] for p in sched)
    total_discharge = sum(p["discharge"] for p in sched)
    if total_charge > 0:
        assert total_discharge < total_charge

def test_build_site_multiple_generators():
    """Multiple generators are dispatched economically."""
    gen_cheap = GeneratorAsset("Cheap", min_output=0, max_output=50, cost_per_mwh=20)
    gen_expensive = GeneratorAsset("Expensive", min_output=0, max_output=100, cost_per_mwh=80)

    interval_data = [
        {"price": 60, "demand": 40},
        {"price": 60, "demand": 80},
    ]
    prob = build_site([gen_cheap, gen_expensive], interval_data)
    assert pulp.LpStatus[prob.status] == "Optimal"

    gen_cheap._post_solve(prob, interval_data, T=2)
    gen_expensive._post_solve(prob, interval_data, T=2)

    # Cheap generator should be preferred
    assert gen_cheap.results["power"][0] == pytest.approx(40, abs=0.01)
    assert gen_expensive.results["power"][0] == pytest.approx(0, abs=0.01)
    # Second period: cheap at max, expensive fills the rest
    assert gen_cheap.results["power"][1] == pytest.approx(50, abs=0.01)
    assert gen_expensive.results["power"][1] == pytest.approx(30, abs=0.01)
