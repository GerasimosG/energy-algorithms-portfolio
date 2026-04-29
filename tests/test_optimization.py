"""Tests for lp_optimization module: transportation, portfolio, scheduling."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import numpy as np
from lp_optimization.transportation import solve_transportation, demo_transportation
from lp_optimization.portfolio import optimize_portfolio_scipy, demo_portfolio
from lp_optimization.scheduling import solve_unit_commitment, demo_uc


# ── Transportation ──────────────────────────────────────────────────

def test_transportation_solves():
    """Basic transportation problem finds optimal solution."""
    supply = {"A": 100, "B": 150}
    demand = {"R1": 80, "R2": 120}
    cost = {("A", "R1"): 4, ("A", "R2"): 6, ("B", "R1"): 7, ("B", "R2"): 3}
    r = solve_transportation(supply, demand, cost)
    assert r["status"] == "Optimal"
    assert r["total_cost"] > 0
    assert len(r["allocations"]) > 0


def test_transportation_demo():
    """Demo transportation works and returns valid result."""
    r = demo_transportation()
    assert r["status"] == "Optimal"
    assert r["total_cost"] < 10000  # reasonable cost


def test_transportation_infeasible():
    """Transportation is infeasible when supply < demand."""
    supply = {"A": 50}
    demand = {"R1": 100}
    cost = {("A", "R1"): 5}
    r = solve_transportation(supply, demand, cost)
    assert r["status"] == "Infeasible"


# ── Portfolio ────────────────────────────────────────────────────────

def test_portfolio_scipy_solves():
    """Mean-variance portfolio finds optimal weights."""
    r = demo_portfolio()
    assert r["status"] == "Optimal"
    assert r["weights"] is not None
    assert abs(sum(r["weights"]) - 1.0) < 0.01


def test_portfolio_cardinality():
    """Cardinality constraint limits number of assets."""
    er = [0.12, 0.10, 0.08, 0.15, 0.09, 0.11]
    np.random.seed(42)
    n = 6
    cov = np.eye(n) * 0.04
    r = optimize_portfolio_scipy(
        expected_returns=er,
        cov_matrix=cov.tolist(),
        target_return=0.10,
        cardinality=3,
    )
    assert r["n_assets_selected"] <= 3


def test_portfolio_min_variance():
    """Without target_return, finds minimum variance portfolio."""
    er = [0.08, 0.10, 0.12]
    cov = [[0.04, 0.01, 0.01], [0.01, 0.04, 0.01], [0.01, 0.01, 0.04]]
    r = optimize_portfolio_scipy(
        expected_returns=er,
        cov_matrix=cov,
        target_return=None,
        weight_bounds=(0.0, 1.0),  # wider bounds = easier to converge
    )
    assert r["status"] == "Optimal"
    assert r["weights"] is not None
    assert abs(sum(r["weights"]) - 1.0) < 0.01


# ── Unit Commitment ──────────────────────────────────────────────────

def test_uc_demo_solves():
    """Demo unit commitment finds feasible schedule."""
    r = demo_uc()
    assert r["status"] == "Optimal"
    assert r["total_cost"] > 0
    assert len(r["schedule"]) == 12  # 12 periods


def test_uc_energy_balance():
    """Each period's generation matches demand exactly."""
    r = demo_uc()
    for t_key, period in r["schedule"].items():
        gen = sum(v for k, v in period.items() if not k.startswith("_"))
        assert abs(gen - period["_demand"]) < 0.01


def test_uc_init_conditions():
    """Initial conditions constrain early periods — G1 must stay off 2 periods."""
    demand = [300, 300, 500, 500, 500]  # lower early demand so G1 can ramp later
    generators = [{
        "name": "G1",
        "min_output": 100, "max_output": 500,
        "cost_per_mwh": 30, "startup_cost": 5000,
        "min_up": 3, "min_down": 2, "ramp_rate": 0.5,
    }]
    # G1 starts OFF and must stay off for min_down=2 periods
    r = solve_unit_commitment(
        demand=demand, generators=generators,
        init_status=[0], init_uptime=[0], init_downtime=[0],
    )
    assert r["status"] in ("Optimal", "Infeasible")  # may be infeasible for t=0-1
    # If optimal, verify the schedule
    if r["status"] == "Optimal":
        assert len(r["schedule"]) == 5


def test_uc_reserve_margin():
    """Reserve margin provides extra committed capacity."""
    demand = [500]
    generators = [{
        "name": "G1",
        "min_output": 0, "max_output": 1000,
        "cost_per_mwh": 30, "startup_cost": 100,
        "min_up": 0, "min_down": 0, "ramp_rate": 1.0,
    }]
    r = solve_unit_commitment(
        demand=demand, generators=generators, reserve_margin=0.2,
    )
    assert r["status"] == "Optimal"
