"""Benchmark and stress test suite — designed for PC execution (not Raspberry Pi).

These tests scale model sizes beyond what the Pi can handle comfortably,
validating that our optimization modules handle production-scale inputs.

Usage (run on PC, skip on Pi):
    pytest tests/test_benchmarks.py -v -m "slow"

Markers:
    @pytest.mark.slow — >5s solve time on PC
    @pytest.mark.pc   — requires PC hardware (>1GB RAM)
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pulp
import pytest

from energy_markets.fbmc import solve_fbmc
from energy_markets.multi_day import solve_multi_day
from lp_optimization.stochastic import (
    generate_wind_scenarios,
    solve_scenario_uc,
    compute_vss,
)
from lp_optimization.assets import BatteryAsset, GeneratorAsset, SpillAsset, build_site
from energy_markets.lodf_utils import compute_lodf, screen_cbcos


# ── Slow markers ───────────────────────────────────────────────────

slow = pytest.mark.slow
pc = pytest.mark.pc


# ═══════════════════════════════════════════════════════════════════
# FBMC stress tests
# ═══════════════════════════════════════════════════════════════════

@slow
@pc
def test_fbmc_10_zones():
    """FBMC with 10 zones and 15 branches — production-scale."""
    np.random.seed(42)
    n_zones = 10
    n_branches = 15

    zones = []
    for i in range(n_zones):
        zones.append({
            "name": f"Z{i}",
            "supply": [
                {"price": np.random.uniform(5, 30), "qty": np.random.uniform(50, 500)}
                for _ in range(3)
            ],
            "demand": [
                {"price": np.random.uniform(50, 200), "qty": np.random.uniform(50, 400)}
                for _ in range(2)
            ],
        })

    # Generate PTDF with row sums ~0
    ptdf = np.random.randn(n_branches, n_zones) * 0.5
    ptdf -= ptdf.mean(axis=1, keepdims=True)

    zone_names = [z["name"] for z in zones]
    ram_limits = [
        {"name": f"L{i}", "ram_forward": 300, "ram_reverse": 300}
        for i in range(n_branches)
    ]

    start = time.perf_counter()
    result = solve_fbmc(zones, ptdf, ram_limits, zone_names)
    elapsed = time.perf_counter() - start

    assert result["status"] == "Optimal"
    assert result["welfare"] > 0
    assert elapsed < 30.0, f"FBMC 10-zone solve took {elapsed:.1f}s (limit 30s)"


@slow
@pc
def test_fbmc_50_zones():
    """FBMC with 50 zones — scaling test."""
    np.random.seed(99)
    n_zones = 50
    n_branches = 80

    zones = []
    for i in range(n_zones):
        zones.append({
            "name": f"Z{i}",
            "supply": [{"price": np.random.uniform(5, 80), "qty": np.random.uniform(50, 300)} for _ in range(2)],
            "demand": [{"price": np.random.uniform(50, 200), "qty": np.random.uniform(50, 300)} for _ in range(1)],
        })

    ptdf = np.random.randn(n_branches, n_zones) * 0.3
    ptdf -= ptdf.mean(axis=1, keepdims=True)

    zone_names = [z["name"] for z in zones]
    ram_limits = [
        {"name": f"L{i}", "ram_forward": 500, "ram_reverse": 500}
        for i in range(n_branches)
    ]

    start = time.perf_counter()
    result = solve_fbmc(zones, ptdf, ram_limits, zone_names, verbose=False)
    elapsed = time.perf_counter() - start

    assert result["status"] == "Optimal"
    assert result["welfare"] > 0
    assert elapsed < 120.0, f"FBMC 50-zone solve took {elapsed:.1f}s (limit 120s)"


# ═══════════════════════════════════════════════════════════════════
# Unit commitment stress tests
# ═══════════════════════════════════════════════════════════════════

@slow
@pc
def test_uc_100_generators_24_hours():
    """Unit commitment: 100 generators × 24 hours."""
    np.random.seed(7)
    T = 24
    G = 100
    generators = [
        {
            "name": f"Gen{i}",
            "min_output": 0,
            "max_output": np.random.uniform(50, 200),
            "cost_per_mwh": np.random.uniform(20, 80),
        }
        for i in range(G)
    ]
    demand = [np.random.uniform(3000, 5000) for _ in range(T)]
    wind = np.array([np.random.uniform(200, 800) for _ in range(T)])
    solar = np.zeros(T)

    start = time.perf_counter()
    result = solve_scenario_uc(demand, wind, solar, generators)
    elapsed = time.perf_counter() - start

    assert result["status"] == "Optimal"
    assert result["total_cost"] > 0
    assert elapsed < 60.0, f"UC 100-gen took {elapsed:.1f}s (limit 60s)"


@slow
@pc
def test_uc_500_generators_48_hours():
    """Unit commitment: 500 generators × 48 hours — near-production scale."""
    np.random.seed(13)
    T = 48
    G = 500
    generators = [
        {
            "name": f"Gen{i}",
            "min_output": 0,
            "max_output": np.random.uniform(30, 150),
            "cost_per_mwh": np.random.uniform(15, 90),
        }
        for i in range(G)
    ]
    demand = [np.random.uniform(8000, 12000) for _ in range(T)]
    wind = np.array([np.random.uniform(500, 2000) for _ in range(T)])
    solar = np.array([np.random.uniform(0, 1500) for _ in range(T)])

    start = time.perf_counter()
    result = solve_scenario_uc(demand, wind, solar, generators)
    elapsed = time.perf_counter() - start

    assert result["status"] == "Optimal"
    assert result["total_cost"] > 0
    assert elapsed < 300.0, f"UC 500-gen took {elapsed:.1f}s (limit 300s)"


# ═══════════════════════════════════════════════════════════════════
# LODF / CBCO stress tests
# ═══════════════════════════════════════════════════════════════════

@slow
@pc
def test_lodf_500_branches():
    """LODF computation for 500 branches — N-1 scale."""
    np.random.seed(3)
    n_branches = 500
    n_zones = 30
    ptdf = np.random.randn(n_branches, n_zones) * 0.4
    ptdf -= ptdf.mean(axis=1, keepdims=True)

    branch_map = [(np.random.randint(0, n_zones), np.random.randint(0, n_zones))
                  for _ in range(n_branches)]

    start = time.perf_counter()
    lodf = compute_lodf(ptdf, branch_zone_map=branch_map)
    elapsed = time.perf_counter() - start

    assert lodf.shape == (n_branches, n_branches)
    assert elapsed < 10.0, f"LODF 500-branch took {elapsed:.1f}s (limit 10s)"


@slow
@pc
def test_cbco_screening_200_branches():
    """CBCO screening with 200 branches."""
    np.random.seed(17)
    n_branches = 200
    n_zones = 15
    ptdf = np.random.randn(n_branches, n_zones) * 0.5
    ptdf -= ptdf.mean(axis=1, keepdims=True)

    branch_map = [(np.random.randint(0, n_zones), np.random.randint(0, n_zones))
                  for _ in range(n_branches)]
    base_flows = np.random.uniform(-100, 100, size=n_branches)
    ram_limits = np.random.uniform(50, 200, size=n_branches)

    start = time.perf_counter()
    critical = screen_cbcos(ptdf, base_flows, ram_limits,
                            branch_zone_map=branch_map, threshold=0.10)
    elapsed = time.perf_counter() - start

    assert len(critical) <= n_branches
    assert elapsed < 5.0, f"CBCO 200-branch took {elapsed:.1f}s (limit 5s)"


# ═══════════════════════════════════════════════════════════════════
# Asset / Site stress tests
# ═══════════════════════════════════════════════════════════════════

@slow
@pc
def test_site_168_hours():
    """Site optimization: 1-week (168 hours) with battery + generator + spill."""
    battery = BatteryAsset("BESS", capacity=500, max_power=50,
                           eff_in=0.95, eff_out=0.95, initial_soc=100)
    gen = GeneratorAsset("Gen1", min_output=0, max_output=200, cost_per_mwh=45)
    spill = SpillAsset("Spill", penalty=5000)

    hours = 168
    interval_data = []
    for h in range(hours):
        hour_of_day = h % 24
        price = 30 + 40 * np.sin(np.pi * (hour_of_day - 6) / 12) ** 2
        demand = 100 + 80 * np.sin(np.pi * (hour_of_day - 6) / 12) ** 2
        interval_data.append({"price": round(price, 1), "demand": round(demand, 1)})

    start = time.perf_counter()
    prob = build_site([battery, gen, spill], interval_data)
    elapsed = time.perf_counter() - start

    assert pulp.LpStatus[prob.status] == "Optimal"
    assert elapsed < 30.0, f"Site 168h took {elapsed:.1f}s (limit 30s)"


# ═══════════════════════════════════════════════════════════════════
# Stochastic VSS at scale
# ═══════════════════════════════════════════════════════════════════

@slow
@pc
def test_vss_50_scenarios():
    """VSS computation with 50 scenarios — stress test stochastic module."""
    base_wind = np.array([120.0, 180.0, 250.0, 150.0])
    demand = [700.0, 750.0, 800.0, 700.0]
    generators = [
        {"name": "Gas", "min_output": 0, "max_output": 500,
         "cost_per_mwh": 50},
        {"name": "Coal", "min_output": 100, "max_output": 400,
         "cost_per_mwh": 30},
    ]

    start = time.perf_counter()
    vss = compute_vss(demand=demand, base_wind=base_wind,
                      base_solar=np.zeros(4), generators=generators,
                      n_scenarios=50, std_pct=0.20, seed=1)
    elapsed = time.perf_counter() - start

    assert isinstance(vss, float)
    assert vss >= 0
    assert elapsed < 120.0, f"VSS 50-scenarios took {elapsed:.1f}s (limit 120s)"


# ═══════════════════════════════════════════════════════════════════
# Multi-day stress
# ═══════════════════════════════════════════════════════════════════

@slow
@pc
def test_multi_day_7_days():
    """Multi-day coupling: 7 days with storage across all days."""
    np.random.seed(5)
    days = []
    for d in range(7):
        zones = [{
            "name": f"Z{d}",
            "supply": [
                {"price": np.random.uniform(5, 60), "qty": np.random.uniform(100, 500)}
                for _ in range(3)
            ],
            "demand": [
                {"price": np.random.uniform(50, 200), "qty": np.random.uniform(100, 400)}
                for _ in range(2)
            ],
        }]
        atc = {}
        days.append({"zones": zones, "atc": atc})

    storage_config = {
        "enabled": True,
        "capacity": 200,
        "max_power": 50,
        "eff_in": 0.95,
        "eff_out": 0.95,
        "initial_soc": 50,
    }

    zones_per_day = [d["zones"] for d in days]
    atc_per_day = [d["atc"] for d in days]

    start = time.perf_counter()
    result = solve_multi_day(zones_per_day, atc_per_day, storage_config, horizon_days=7)
    elapsed = time.perf_counter() - start

    assert result["status"] == "Optimal"
    assert result["welfare"] > 0
    assert elapsed < 30.0, f"Multi-day 7d took {elapsed:.1f}s (limit 30s)"


# ═══════════════════════════════════════════════════════════════════
# Quick benchmarks (run even on Pi — just performance tracking)
# ═══════════════════════════════════════════════════════════════════

def test_fbmc_solve_benchmark():
    """Track FBMC solve time — should be <1s on any hardware."""
    from energy_markets.fbmc import solve_fbmc
    zones = [
        {"name": "A", "supply": [{"price": 10, "qty": 300}], "demand": [{"price": 100, "qty": 100}]},
        {"name": "B", "supply": [{"price": 50, "qty": 300}], "demand": [{"price": 100, "qty": 200}]},
        {"name": "C", "supply": [{"price": 70, "qty": 300}], "demand": [{"price": 100, "qty": 200}]},
    ]
    ptdf = np.array([[0.6, -0.4, -0.2], [0.3, 0.3, -0.6], [0.1, -0.1, 0.0]])
    ram = [{"name": f"L{i}", "ram_forward": 300, "ram_reverse": 300} for i in range(3)]

    start = time.perf_counter()
    result = solve_fbmc(zones, ptdf, ram, ["A", "B", "C"])
    elapsed = time.perf_counter() - start

    assert result["status"] == "Optimal"
    assert elapsed < 5.0, f"FBMC benchmark took {elapsed:.2f}s"


def test_uc_solve_benchmark():
    """Track UC solve time."""
    demand = [500, 600, 700, 650]
    wind = np.array([100, 120, 80, 90])
    solar = np.array([0, 50, 200, 0])
    generators = [
        {"name": "Gas", "min_output": 50, "max_output": 400, "cost_per_mwh": 50},
        {"name": "Coal", "min_output": 100, "max_output": 500, "cost_per_mwh": 30},
    ]

    start = time.perf_counter()
    result = solve_scenario_uc(demand, wind, solar, generators)
    elapsed = time.perf_counter() - start

    assert result["status"] == "Optimal"
    assert elapsed < 5.0, f"UC benchmark took {elapsed:.2f}s"
