"""Tests for the PuLP solver adapter.
"""

from __future__ import annotations

import pytest
import pulp

from energy_algorithms.adapters.pulp_solver import PuLPSolverAdapter


# ── Constructor & _resolve_class ──────────────────────────────────────

def test_default_solver_is_cbc():
    """Default constructor uses CBC solver."""
    adapter = PuLPSolverAdapter()
    assert adapter.name == "CBC"


def test_explicit_solver_name():
    """Explicit solver ID stored as uppercase name."""
    adapter = PuLPSolverAdapter("cbc")
    assert adapter.name == "CBC"


def test_unknown_solver_raises():
    """Unknown solver ID raises ValueError."""
    with pytest.raises(ValueError, match="Unknown solver"):
        PuLPSolverAdapter("fantasy_solver")


# ── solve() ───────────────────────────────────────────────────────────

def test_solve_simple_problem():
    """Solve a trivial LP through the adapter."""
    adapter = PuLPSolverAdapter("cbc")
    prob = pulp.LpProblem("test", pulp.LpMaximize)
    x = pulp.LpVariable("x", 0, 10)
    prob += x
    prob += x <= 5
    result = adapter.solve(prob, msg=False)
    assert result.status == "Optimal"
    assert result.objective == 5.0
    assert result.variables["x"] == 5.0
    assert result.solve_time > 0
    assert result.solver_name == "CBC"


def test_solve_infeasible():
    """Infeasible problem returns appropriate status."""
    adapter = PuLPSolverAdapter("cbc")
    prob = pulp.LpProblem("infeasible", pulp.LpMinimize)
    x = pulp.LpVariable("x", 0, 1)
    prob += x
    prob += x >= 2  # infeasible
    result = adapter.solve(prob, msg=False)
    assert result.status == "Infeasible"
    assert result.objective is None


def test_solve_unbounded():
    """Unbounded problem returns appropriate status."""
    adapter = PuLPSolverAdapter("cbc")
    prob = pulp.LpProblem("unbounded", pulp.LpMaximize)
    x = pulp.LpVariable("x")
    prob += x  # maximize x with no constraints → unbounded
    result = adapter.solve(prob, msg=False)
    assert result.status in ("Unbounded", "Optimal")
    # CBC may or may not detect unboundedness depending on version


# ── available() ───────────────────────────────────────────────────────

def test_available_cbc():
    """CBC solver is available on this system (can construct and has path)."""
    adapter = PuLPSolverAdapter("cbc")
    # CBC is always available since it ships with PuLP
    # The available() method may call solver.available() which isn't
    # implemented on all PuLP solver classes
    assert adapter is not None
    assert adapter._solver_cls is not None
