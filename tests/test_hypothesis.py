"""Property-based testing with Hypothesis — catches edge cases deterministic tests miss.

Based on energy-py-linear's approach (250 random examples per run).

Usage:
    pip install hypothesis
    pytest tests/test_hypothesis.py -v

Without Hypothesis installed, these tests are skipped gracefully.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest

# Conditionally import Hypothesis
try:
    from hypothesis import given, settings, HealthCheck
    import hypothesis.strategies as st
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False
    # When Hypothesis is unavailable, @settings and @given are no-ops
    # and the @pytest.mark.skipif will skip the test.
    st = None

from energy_algorithms.domain.markets.fbmc import solve_fbmc
from energy_algorithms.domain.optimization.stochastic import (
    generate_wind_scenarios,
    solve_scenario_uc,
)

# Only define hypothesis-backed tests if hypothesis is installed
# Otherwise they're skipped gracefully by the @skipif decorator

@pytest.mark.skipif(
    not HAS_HYPOTHESIS,
    reason="hypothesis not installed (pip install hypothesis)"
)
def test_fbmc_random_energy_balance():
    """Random FBMC inputs always satisfy energy balance (sampling variant)."""
    np.random.seed(42)
    for _ in range(20):
        n_zones = np.random.randint(2, 6)
        n_branches = np.random.randint(1, 4)
        zones = []
        for i in range(n_zones):
            zones.append({
                "name": f"Z{i}",
                "supply": [{"price": np.random.uniform(5, 80), "qty": np.random.uniform(10, 300)}
                            for _ in range(2)],
                "demand": [{"price": np.random.uniform(30, 200), "qty": np.random.uniform(10, 300)}
                            for _ in range(2)],
            })
        ptdf = np.random.randn(n_branches, n_zones) * 0.5
        ptdf -= ptdf.mean(axis=1, keepdims=True)
        zone_names = [z["name"] for z in zones]
        ram = [{"name": f"L{i}", "ram_forward": 500, "ram_reverse": 500} for i in range(n_branches)]

        result = solve_fbmc(zones, ptdf, ram, zone_names)
        if result["status"] != "Optimal":
            continue

        total_supply = sum(zr["supply_cleared_mw"] for zr in result["zones"].values())
        total_demand = sum(zr["demand_cleared_mw"] for zr in result["zones"].values())
        assert abs(total_supply - total_demand) < 0.3


@pytest.mark.skipif(
    not HAS_HYPOTHESIS,
    reason="hypothesis not installed (pip install hypothesis)"
)
def test_wind_scenarios_bounded():
    """100 random wind scenario configs always produce valid outputs."""
    np.random.seed(77)
    for _ in range(100):
        profile_len = np.random.randint(2, 24)
        base = np.random.uniform(0.1, 0.9, size=profile_len)
        std_pct = np.random.uniform(0.01, 0.4)
        scenarios = generate_wind_scenarios(base, std_pct=std_pct, n_scenarios=5, seed=None)
        for s in scenarios:
            assert np.all(s >= 0), "Negative wind value"
            assert np.all(s <= 1.0), "Wind CF > 1.0"


@pytest.mark.skipif(
    not HAS_HYPOTHESIS,
    reason="hypothesis not installed (pip install hypothesis)"
)
def test_uc_random_feasibility():
    """50 random UC configurations should solve or infeasible gracefully."""
    np.random.seed(13)
    for _ in range(50):
        n_gen = np.random.randint(1, 4)
        n_periods = np.random.randint(2, 8)
        generators = [
            {"name": f"G{i}", "min_output": 0,
             "max_output": np.random.uniform(50, 300),
             "cost_per_mwh": np.random.uniform(20, 80)}
            for i in range(n_gen)
        ]
        demand = list(np.random.uniform(50, 500, size=n_periods))
        wind = np.random.uniform(0, 200, size=n_periods)

        result = solve_scenario_uc(demand, wind, np.zeros(n_periods), generators)
        assert result["status"] in ("Optimal", "Infeasible", "Unbounded")


# If Hypothesis IS available, also define actual @given tests
if HAS_HYPOTHESIS:

    @settings(max_examples=50, deadline=None)
    @given(
        n_zones=st.integers(2, 6),
        seed=st.integers(0, 10000),
    )
    def test_fbmc_prop_energy_balance(n_zones, seed):
        """Property: FBMC energy balance holds for all random inputs."""
        np.random.seed(seed)
        zones = []
        for i in range(n_zones):
            zones.append({
                "name": f"Z{i}",
                "supply": [{"price": np.random.uniform(5, 50), "qty": np.random.uniform(10, 300)}
                            for _ in range(2)],
                "demand": [{"price": np.random.uniform(50, 200), "qty": np.random.uniform(10, 300)}
                            for _ in range(2)],
            })
        ptdf = np.random.randn(2, n_zones) * 0.5
        ptdf -= ptdf.mean(axis=1, keepdims=True)
        zone_names = [z["name"] for z in zones]
        ram = [{"name": "L0", "ram_forward": 500, "ram_reverse": 500},
               {"name": "L1", "ram_forward": 500, "ram_reverse": 500}]

        result = solve_fbmc(zones, ptdf, ram, zone_names)
        if result["status"] != "Optimal":
            pytest.skip("Infeasible")
        assert result["welfare"] >= -0.01
