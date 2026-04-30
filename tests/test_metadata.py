"""Tests for lp_optimization.metadata — variable and model metadata."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pulp
import pytest

from lp_optimization.metadata import (
    VariableRegistry,
    ModelMetadata,
    get_model_summary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_simple_problem() -> pulp.LpProblem:
    """Create a small PuLP problem for metadata testing."""
    prob = pulp.LpProblem("Test_Problem", pulp.LpMinimize)
    x = pulp.LpVariable("x", lowBound=0, upBound=10, cat="Continuous")
    y = pulp.LpVariable("y", cat="Binary")
    z = pulp.LpVariable("z", lowBound=0, upBound=100, cat="Integer")
    prob += 2 * x + 3 * y + z, "objective"
    prob += x + y >= 5, "c1"
    prob += z <= 50, "c2"
    prob += x - z == 0, "c3"
    return prob


# ---------------------------------------------------------------------------
# Tests — VariableRegistry
# ---------------------------------------------------------------------------


class TestVariableRegistry:
    """Tests for the VariableRegistry class."""

    def test_register_and_count(self):
        """Registering variables increases the count."""
        reg = VariableRegistry()
        assert reg.count() == 0

        reg.register_variable("x_0", "Continuous", (0, 10))
        assert reg.count() == 1

        reg.register_variable("y_0", "Binary", (0, 1))
        assert reg.count() == 2

    def test_by_type(self):
        """by_type groups variable names by declared type."""
        reg = VariableRegistry()
        reg.register_variable("a", "Continuous", (0, None))
        reg.register_variable("b", "Binary", (0, 1))
        reg.register_variable("c", "Continuous", (None, None))
        reg.register_variable("d", "Integer", (0, 100))

        groups = reg.by_type()
        assert groups["Continuous"] == ["a", "c"]
        assert groups["Binary"] == ["b"]
        assert groups["Integer"] == ["d"]

    def test_variables_returns_copy(self):
        """variables() returns the list of metadata dicts."""
        reg = VariableRegistry()
        reg.register_variable("x", "Continuous", (0, 5))
        vars_ = reg.variables()
        assert len(vars_) == 1
        assert vars_[0]["name"] == "x"
        assert vars_[0]["lower"] == 0
        assert vars_[0]["upper"] == 5

    def test_clear(self):
        """clear() removes all registered variables."""
        reg = VariableRegistry()
        reg.register_variable("x", "Continuous")
        reg.clear()
        assert reg.count() == 0

    def test_default_bounds(self):
        """Default bounds are (0, None)."""
        reg = VariableRegistry()
        reg.register_variable("v")
        var = reg.variables()[0]
        assert var["lower"] == 0
        assert var["upper"] is None


# ---------------------------------------------------------------------------
# Tests — ModelMetadata
# ---------------------------------------------------------------------------


class TestModelMetadata:
    """Tests for the ModelMetadata class."""

    def test_from_problem_counts(self):
        """from_problem correctly counts variables and constraints."""
        prob = _make_simple_problem()
        meta = ModelMetadata.from_problem(prob, solver_name="CBC")

        assert meta.var_count == 3       # x, y, z
        assert meta.constraint_count == 3  # c1, c2, c3
        assert meta.continuous_count == 1
        assert meta.binary_count == 1
        assert meta.integer_count == 1

    def test_from_problem_metadata(self):
        """Name, sense, and solver are captured."""
        prob = _make_simple_problem()
        meta = ModelMetadata.from_problem(prob, solver_name="HiGHS")

        assert meta.name == "Test_Problem"
        assert meta.sense == "Minimize"
        assert meta.solver_name == "HiGHS"

    def test_summary_dict(self):
        """summary() returns a dict with expected keys."""
        prob = _make_simple_problem()
        meta = ModelMetadata.from_problem(prob, solver_name="CBC")
        s = meta.summary()

        assert isinstance(s, dict)
        for key in (
            "name", "sense", "solver", "var_count",
            "constraint_count", "binary", "integer", "continuous",
        ):
            assert key in s

        assert s["var_count"] == 3
        assert s["constraint_count"] == 3

    def test_repr(self):
        """__repr__ is informative."""
        prob = _make_simple_problem()
        meta = ModelMetadata.from_problem(prob)
        r = repr(meta)
        assert "ModelMetadata" in r
        assert "Test_Problem" in r

    def test_empty_problem(self):
        """Metadata works for an empty problem (no variables)."""
        prob = pulp.LpProblem("Empty", pulp.LpMaximize)
        meta = ModelMetadata.from_problem(prob)
        assert meta.var_count == 0
        assert meta.constraint_count == 0
        assert meta.sense == "Maximize"


# ---------------------------------------------------------------------------
# Tests — get_model_summary convenience
# ---------------------------------------------------------------------------


class TestGetModelSummary:
    """Tests for get_model_summary()."""

    def test_returns_dict(self):
        """get_model_summary returns a dictionary."""
        prob = _make_simple_problem()
        summary = get_model_summary(prob)
        assert isinstance(summary, dict)
        assert summary["var_count"] == 3
        assert summary["constraint_count"] == 3

    def test_includes_solver_key(self):
        """The 'solver' key is present (default empty string)."""
        prob = _make_simple_problem()
        summary = get_model_summary(prob)
        assert "solver" in summary
