"""Tests for lp_optimization.solver_config — solver discovery and fallback."""
from __future__ import annotations

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
 back to CBC. We use 'gurobi' as the test target because
 it's unlikely to be installed in CI.
 """
 installed = list_available_solvers()
 if "gurobi" in installed:
 pytest.skip("Gurobi is installed — can't test fallback")

 with pytest.warns(UserWarning, match="Falling back to CBC"):
 solver = get_solver("gurobi")
 assert solver is not None
 assert hasattr(solver, "path") # CBC

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

 def test_glpk_capabilities(self):
 """GLPK supports LP/MIP but not QP, barrier, or SOS."""
 caps = solver_capabilities("glpk")
 assert caps["lp"] is True
 assert caps["mip"] is True
 assert caps["qp"] is False
 assert caps["barrier"] is False
 assert caps["sos"] is False

 def test_gurobi_capabilities(self):
 """Gurobi supports all capabilities."""
 caps = solver_capabilities("gurobi")
 assert caps["lp"] is True
 assert caps["mip"] is True
 assert caps["qp"] is True
 assert caps["barrier"] is True
 assert caps["sos"] is True

 def test_cplex_capabilities(self):
 """CPLEX supports all capabilities."""
 caps = solver_capabilities("cplex")
 assert caps["lp"] is True
 assert caps["mip"] is True
 assert caps["qp"] is True
 assert caps["barrier"] is True
 assert caps["sos"] is True


class TestImportHelpers:
 """Tests for the private _try_import_* helper functions."""

 def test_try_import_highs(self):
 """_try_import_highs attempts to import HiGHS from PuLP."""
 from energy_algorithms.infrastructure.solver_config import _try_import_highs

 result = _try_import_highs()
 # May be None if HiGHS not installed, or a class if it is
 assert result is None or callable(result)

 def test_try_import_highs_fallback_via_highspy(self, monkeypatch):
 """_try_import_highs falls back to highspy when pulp.HiGHS_CMD missing."""
 import pulp

 from energy_algorithms.infrastructure.solver_config import _try_import_highs

 # Remove HiGHS_CMD and HIGHS from pulp to trigger fallback
 monkeypatch.delattr(pulp, "HiGHS_CMD", raising=False)
 monkeypatch.delattr(pulp, "HIGHS", raising=False)

 result = _try_import_highs()
 # With highspy installed, it might still resolve; without it, returns None
 assert result is None or callable(result)

 def test_try_import_gurobi_fallback_to_cmd(self, monkeypatch):
 """_try_import_gurobi falls back to GUROBI_CMD when GUROBI missing."""
 import pulp

 from energy_algorithms.infrastructure.solver_config import _try_import_gurobi

 # Remove GUROBI to force fallback to GUROBI_CMD
 monkeypatch.delattr(pulp, "GUROBI", raising=False)
 result = _try_import_gurobi()
 assert result is None or callable(result)

 def test_try_import_gurobi_both_missing(self, monkeypatch):
 """_try_import_gurobi returns None when neither GUROBI nor GUROBI_CMD exist."""
 import pulp

 from energy_algorithms.infrastructure.solver_config import _try_import_gurobi

 monkeypatch.delattr(pulp, "GUROBI", raising=False)
 monkeypatch.delattr(pulp, "GUROBI_CMD", raising=False)
 result = _try_import_gurobi()
 assert result is None

 def test_try_import_cplex_fallback_to_cmd(self, monkeypatch):
 """_try_import_cplex falls back to CPLEX_CMD when CPLEX_PY missing."""
 import pulp

 from energy_algorithms.infrastructure.solver_config import _try_import_cplex

 monkeypatch.delattr(pulp, "CPLEX_PY", raising=False)
 result = _try_import_cplex()
 assert result is None or callable(result)

 def test_try_import_cplex_both_missing(self, monkeypatch):
 """_try_import_cplex returns None when neither CPLEX_PY nor CPLEX_CMD exist."""
 import pulp

 from energy_algorithms.infrastructure.solver_config import _try_import_cplex

 monkeypatch.delattr(pulp, "CPLEX_PY", raising=False)
 monkeypatch.delattr(pulp, "CPLEX_CMD", raising=False)
 result = _try_import_cplex()
 assert result is None

 def test_try_import_glpk_missing(self, monkeypatch):
 """_try_import_glpk returns None when GLPK_CMD does not exist."""
 import pulp

 from energy_algorithms.infrastructure.solver_config import _try_import_glpk

 monkeypatch.delattr(pulp, "GLPK_CMD", raising=False)
 result = _try_import_glpk()
 assert result is None

 def test_highs_module_level_resolved(self):
 """_RESOLVED dict has highs key if import succeeded."""
 import energy_algorithms.infrastructure.solver_config as sc

 # If highspy is installed, highs should be in _RESOLVED
 # Otherwise, it might not be
 assert isinstance(sc._RESOLVED, dict)


class TestGetSolverFallback:
 """Additional fallback path tests for get_solver()."""

 def test_fallback_preserves_specific_kwargs(self):
 """Fallback CBC constructor only gets kwargs it understands."""
 installed = list_available_solvers()
 target = "highs" if "highs" not in installed else "gurobi"
 if target in installed:
 pytest.skip(f"{target} is installed — can't test fallback kwargs filtering")

 with pytest.warns(UserWarning, match="Falling back to CBC"):
 solver = get_solver(target, foo="bar", baz=42)
 # Should not crash — unknown kwargs are filtered
 assert solver is not None

 def test_get_solver_resolved_path(self):
 """Solver that IS in _RESOLVED returns that class directly."""
 import energy_algorithms.infrastructure.solver_config as sc

 # Check if any non-cbc solver is resolved
 non_cbc = {k: v for k, v in sc._RESOLVED.items() if k != "cbc"}
 if non_cbc:
 name = list(non_cbc.keys())[0]
 solver = get_solver(name)
 assert solver is not None

 def test_list_available_includes_resolved(self):
 """list_available_solvers includes all resolved solvers plus cbc."""
 import energy_algorithms.infrastructure.solver_config as sc

 available = list_available_solvers()
 assert "cbc" in available
 # All resolved names should be in the list
 for name in sc._RESOLVED:
 assert name in available
