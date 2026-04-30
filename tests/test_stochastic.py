"""Tests for Renewable Uncertainty Module — lp_optimization module."""
from __future__ import annotations
import os

import numpy as np
import pytest

from energy_algorithms.domain.optimization.stochastic import (
    generate_wind_scenarios,
    generate_solar_scenarios,
    solve_scenario_uc,
    compute_vss,
    compute_evpi,
)

# ── 1. Wind scenario generation ───────────────────────────────────

def test_generate_wind_scenarios_shape():
    """Generated wind scenarios should have correct shape: n_scenarios × len(base)."""
    base = np.array([0.3, 0.5, 0.8, 0.6, 0.4])  # 5-period capacity factor
    n_scenarios = 10
    scenarios = generate_wind_scenarios(base, std_pct=0.15, n_scenarios=n_scenarios)

    assert isinstance(scenarios, list)
    assert len(scenarios) == n_scenarios
    for s in scenarios:
        assert isinstance(s, np.ndarray)
        assert len(s) == len(base)
        # All values should be >= 0 (capacity factor non-negative)
        assert np.all(s >= 0)

def test_generate_wind_scenarios_mean_close_to_base():
    """With many scenarios, mean should approximate base profile."""
    base = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
    n_scenarios = 500
    scenarios = generate_wind_scenarios(base, std_pct=0.10, n_scenarios=n_scenarios)

    stack = np.array(scenarios)
    mean_profile = stack.mean(axis=0)

    # Mean should be within ~5% of base for 500 samples
    assert np.allclose(mean_profile, base, atol=0.05)

def test_generate_wind_scenarios_seed_reproducible():
    """Same seed should produce identical scenarios."""
    base = np.array([0.3, 0.5, 0.8])
    s1 = generate_wind_scenarios(base, std_pct=0.15, n_scenarios=20, seed=42)
    s2 = generate_wind_scenarios(base, std_pct=0.15, n_scenarios=20, seed=42)

    for a, b in zip(s1, s2):
        assert np.array_equal(a, b)

# ── 2. Solar scenario generation ─────────────────────────────────

def test_generate_solar_scenarios_daytime_only():
    """Solar scenarios should be zero where base is zero (night periods)."""
    base = np.array([0.0, 0.0, 0.2, 0.6, 0.8, 0.5, 0.1, 0.0, 0.0])
    scenarios = generate_solar_scenarios(base, std_pct=0.2, n_scenarios=10, seed=99)

    for s in scenarios:
        # Night periods (base == 0) should stay 0
        assert np.all(s[base == 0] == 0)
        # Daytime periods should be >= 0
        assert np.all(s[base > 0] >= 0)

# ── 3. Scenario UC solves ─────────────────────────────────────────

def test_scenario_uc_solves():
    """solve_scenario_uc should return Optimal for a simple setup."""
    demand = [500.0, 600.0, 700.0, 650.0]
    wind_scenario = np.array([100.0, 120.0, 80.0, 90.0])
    solar_scenario = np.array([0.0, 50.0, 200.0, 0.0])

    generators = [
        {"name": "Gas", "min_output": 50, "max_output": 400,
         "cost_per_mwh": 50, "startup_cost": 1000,
         "min_up": 1, "min_down": 1, "ramp_rate": 0.5},
        {"name": "Coal", "min_output": 100, "max_output": 500,
         "cost_per_mwh": 30, "startup_cost": 2000,
         "min_up": 2, "min_down": 2, "ramp_rate": 0.3},
    ]

    result = solve_scenario_uc(demand, wind_scenario, solar_scenario, generators)
    assert result["status"] == "Optimal"
    assert result["total_cost"] > 0
    assert "schedule" in result
    assert len(result["schedule"]) == len(demand)

def test_scenario_uc_renewables_reduce_cost():
    """More renewables → lower dispatch cost."""
    demand = [600.0, 600.0, 600.0, 600.0]
    generators = [
        {"name": "Gas", "min_output": 0, "max_output": 600,
         "cost_per_mwh": 60, "startup_cost": 500,
         "min_up": 1, "min_down": 1, "ramp_rate": 1.0},
    ]

    # High wind reduces residual demand → cheaper
    result_high_wind = solve_scenario_uc(
        demand, np.array([300.0, 300.0, 300.0, 300.0]),
        np.zeros(4), generators
    )
    result_low_wind = solve_scenario_uc(
        demand, np.array([0.0, 0.0, 0.0, 0.0]),
        np.zeros(4), generators
    )

    assert result_high_wind["status"] == "Optimal"
    assert result_low_wind["status"] == "Optimal"
    assert result_high_wind["total_cost"] < result_low_wind["total_cost"]

# ── 4. VSS computation ────────────────────────────────────────────

def test_vss_positive():
    """Value of Stochastic Solution should be non-negative (VSS >= 0)."""
    base_wind = np.array([100.0, 150.0, 200.0, 100.0])
    demand = [600.0, 650.0, 700.0, 600.0]
    generators = [
        {"name": "Gas", "min_output": 50, "max_output": 400,
         "cost_per_mwh": 50, "startup_cost": 1000,
         "min_up": 1, "min_down": 1, "ramp_rate": 0.5},
        {"name": "Coal", "min_output": 100, "max_output": 500,
         "cost_per_mwh": 30, "startup_cost": 2000,
         "min_up": 2, "min_down": 2, "ramp_rate": 0.3},
    ]

    vss = compute_vss(
        demand=demand,
        base_wind=base_wind,
        base_solar=np.zeros(4),
        generators=generators,
        n_scenarios=30,
        std_pct=0.20,
        seed=123,
    )
    assert vss >= 0, f"VSS should be non-negative, got {vss}"

    # Also verify it's a float and not NaN
    assert isinstance(vss, float)
    assert not np.isnan(vss)

# ── 5. EVPI computation ───────────────────────────────────────────

def test_evpi_non_negative():
    """Expected Value of Perfect Information should be non-negative."""
    base_wind = np.array([100.0, 150.0, 200.0, 100.0])
    demand = [600.0, 650.0, 700.0, 600.0]
    generators = [
        {"name": "Gas", "min_output": 0, "max_output": 600,
         "cost_per_mwh": 50, "startup_cost": 500,
         "min_up": 1, "min_down": 1, "ramp_rate": 1.0},
    ]

    evpi = compute_evpi(
        demand=demand,
        base_wind=base_wind,
        base_solar=np.zeros(4),
        generators=generators,
        n_scenarios=20,
        std_pct=0.20,
        seed=456,
    )
    assert evpi >= 0, f"EVPI should be non-negative, got {evpi}"
    assert isinstance(evpi, float)
    assert not np.isnan(evpi)

# ── 6. Deterministic base case ────────────────────────────────────

def test_deterministic_uc_base():
    """Deterministic UC with base renewables should solve."""
    demand = [500.0, 550.0, 600.0, 500.0]
    wind = np.array([100.0, 120.0, 80.0, 90.0])
    solar = np.array([0.0, 50.0, 200.0, 0.0])

    generators = [
        {"name": "CCGT", "min_output": 100, "max_output": 500,
         "cost_per_mwh": 45, "startup_cost": 800,
         "min_up": 1, "min_down": 1, "ramp_rate": 0.4},
    ]

    result = solve_scenario_uc(demand, wind, solar, generators)
    assert result["status"] == "Optimal"
    assert result["total_cost"] > 0

    # Check that renewables are subtracted from demand in generation
    residual = np.array(demand) - wind - solar
    for t in range(len(demand)):
        gen_total = sum(
            result["schedule"][f"t={t}"][g["name"]] for g in generators
        )
        assert abs(gen_total - residual[t]) < 0.1, (
            f"t={t}: gen={gen_total}, residual={residual[t]}"
        )

# ── 7. Large scenario count ───────────────────────────────────────

def test_many_scenarios():
    """100 scenarios should generate and compute VSS without error."""
    base_wind = np.array([80.0, 100.0, 150.0, 120.0])
    demand = [500.0, 550.0, 600.0, 500.0]
    generators = [
        {"name": "Gas", "min_output": 0, "max_output": 600,
         "cost_per_mwh": 50, "startup_cost": 1000,
         "min_up": 1, "min_down": 1, "ramp_rate": 1.0},
    ]

    scenarios = generate_wind_scenarios(base_wind, std_pct=0.20, n_scenarios=100, seed=0)
    assert len(scenarios) == 100

    vss = compute_vss(
        demand=demand, base_wind=base_wind, base_solar=np.zeros(4),
        generators=generators, n_scenarios=100, std_pct=0.20, seed=0,
    )
    assert vss >= 0

# ── 8. Edge case: zero wind / zero solar ──────────────────────────

def test_zero_renewables():
    """Zero wind and solar: UC should still solve (all demand from generators)."""
    demand = [400.0, 500.0, 600.0]
    generators = [
        {"name": "Gen", "min_output": 0, "max_output": 600,
         "cost_per_mwh": 40, "startup_cost": 500,
         "min_up": 1, "min_down": 1, "ramp_rate": 1.0},
    ]

    result = solve_scenario_uc(demand, np.zeros(3), np.zeros(3), generators)
    assert result["status"] == "Optimal"
    # Total generation = demand
    gen_sum = sum(
        result["schedule"][f"t={t}"]["Gen"] for t in range(3)
    )
    assert abs(gen_sum - sum(demand)) < 0.1
