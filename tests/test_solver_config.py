"""Tests for lp_optimization.solver_config — solver discovery and fallback."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from energy_algorithms.infrastructure.solver_config import (
    get_solver,
    list_available_solvers,
    solver_capabilities,
)


class TestListAvailableSolvers:
    """Tests for list_available_solvers()."""

    def test_always_includes_cbc(self):
        """CBC is always available because it ships with PuLP."""
        solvers = list_available_solvers()
        assert "cbc" in solvers

    def test_returns_list_of_strings(self):
        """Return type is a sorted list of strings."""
        solvers = list_available_solvers()
        assert isinstance(solvers, list)
        assert all(isinstance(s, str) for s in solvers)
        assert solvers == sorted(solvers)


class TestGetSolver:
    """Tests for get_solver()."""

    def test_default_is_cbc(self):
        """Default (no args) returns a CBC solver object."""
        solver = get_solver()
        assert solver is not None
        # CBC_CMD objects have a path attribute
        assert hasattr(solver, "path")

    def test_cbc_explicit(self):
        """Explicit 'cbc' returns a CBC solver object."""
        solver = get_solver("cbc")
        assert solver is not None
        assert hasattr(solver, "path")

    def test_cbc_with_kwargs(self):
        """Keyword arguments are forwarded to the solver constructor."""
        solver = get_solver("cbc", msg=False, timeLimit=30)
        assert solver is not None

    def test_unknown_solver_raises(self):
        """An unknown solver name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown solver"):
            get_solver("nonexistent_solver_xyz")

    def test_case_insensitive(self):
        """Solver name is case-insensitive."""
        solver = get_solver("CBC")
        assert solver is not None

    def test_fallback_for_uninstalled(self):
        """
        Requesting a solver that isn't installed warns and falls
        back to CBC.  We use 'gurobi' as the test target because
        it's unlikely to be installed in CI.
        """
        installed = list_available_solvers()
        if "gurobi" in installed:
            pytest.skip("Gurobi is installed — can't test fallback")

        with pytest.warns(UserWarning, match="Falling back to CBC"):
            solver = get_solver("gurobi")
        assert solver is not None
        assert hasattr(solver, "path")  # CBC

    def test_highs_fallback_when_not_installed(self):
        """HiGHS gracefully falls back when not installed."""
        installed = list_available_solvers()
        if "highs" in installed:
            pytest.skip("HiGHS is installed — can't test fallback")

        with pytest.warns(UserWarning, match="Falling back to CBC"):
            solver = get_solver("highs")
        assert solver is not None


class TestSolverCapabilities:
    """Tests for solver_capabilities()."""

    def test_cbc_capabilities(self):
        """CBC supports MIP, not QP."""
        caps = solver_capabilities("cbc")
        assert caps["mip"] is True
        assert caps["lp"] is True
        assert caps["qp"] is False
        assert caps["installed"] is True

    def test_highs_capabilities(self):
        """HiGHS capabilities are documented even if not installed."""
        caps = solver_capabilities("highs")
        assert caps["mip"] is True
        assert caps["qp"] is True
        assert caps["barrier"] is True
        # installed flag reflects reality
        assert caps["installed"] == ("highs" in list_available_solvers())

    def test_unknown_solver_defaults_to_cbc_capabilities(self):
        """Asking about an unknown solver returns CBC-like capabilities."""
        caps = solver_capabilities("foobar")
        assert caps["qp"] is False

    def test_all_known_solvers_have_installed_flag(self):
        """Every known solver dict includes the 'installed' key."""
        for name in ["cbc", "highs", "gurobi", "cplex", "glpk"]:
            caps = solver_capabilities(name)
            assert "installed" in caps
            assert isinstance(caps["installed"], bool)
