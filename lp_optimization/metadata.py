"""
Descriptive metadata registry for LP/MIP models.

Provides classes that track variable names, types, and bounds as well
as aggregate constraint and objective information so that users can
introspect a built model before or after solving.
"""

from __future__ import annotations

import logging
from typing import Any

import pulp

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# VariableRegistry
# ---------------------------------------------------------------------------


class VariableRegistry:
    """
    Collects metadata about decision variables declared in a PuLP problem.

    Usage::

        reg = VariableRegistry()
        reg.register_variable("x_0", var_type="Continuous", bounds=(0, 10))
        reg.register_variable("y_0", var_type="Binary", bounds=(0, 1))

        print(reg.count())          # 2
        print(reg.by_type())        # {"Continuous": ["x_0"], "Binary": ["y_0"]}
    """

    def __init__(self) -> None:
        """Initialise an empty variable registry."""
        self._vars: list[dict[str, Any]] = []

    def register_variable(
        self,
        name: str,
        var_type: str = "Continuous",
        bounds: tuple[float | None, float | None] = (0, None),
    ) -> None:
        """
        Register a variable with its metadata.

        Parameters
        ----------
        name : str
            Variable name (should match the PuLP variable name for
            correlation).
        var_type : str
            One of ``"Continuous"``, ``"Binary"``, ``"Integer"``.
        bounds : tuple of (float or None, float or None)
            Lower and upper bounds.  ``None`` means unbounded.
        """
        self._vars.append({
            "name": name,
            "type": var_type,
            "lower": bounds[0],
            "upper": bounds[1],
        })

    def count(self) -> int:
        """
        Return the total number of registered variables.

        Returns
        -------
        int
        """
        return len(self._vars)

    def by_type(self) -> dict[str, list[str]]:
        """
        Group variable names by their declared type.

        Returns
        -------
        dict
            Mapping ``{type_name: [var_name, ...]}``.
        """
        result: dict[str, list[str]] = {}
        for v in self._vars:
            result.setdefault(v["type"], []).append(v["name"])
        return result

    def variables(self) -> list[dict[str, Any]]:
        """
        Return the raw list of variable metadata dicts.

        Returns
        -------
        list of dict
        """
        return list(self._vars)

    def clear(self) -> None:
        """Remove all registered variables."""
        self._vars.clear()


# ---------------------------------------------------------------------------
# ModelMetadata
# ---------------------------------------------------------------------------


class ModelMetadata:
    """
    High-level metadata for a PuLP `LpProblem` instance.

    Collects counts of variables (by category) and constraints, the
    objective sense, and the solver name.  Designed for quick
    introspection in notebooks and logging pipelines.

    Usage::

        prob = pulp.LpProblem("Example", pulp.LpMinimize)
        # ... add variables and constraints ...
        meta = ModelMetadata.from_problem(prob, solver_name="CBC")
        print(meta.summary())
    """

    def __init__(
        self,
        name: str = "",
        sense: str = "",
        solver_name: str = "",
    ) -> None:
        """
        Parameters
        ----------
        name : str
            Problem name (usually ``prob.name``).
        sense : str
            Objective sense (``"Minimize"`` or ``"Maximize"``).
        solver_name : str
            Identifier of the solver used, e.g. ``"CBC"``.
        """
        self.name = name
        self.sense = sense
        self.solver_name = solver_name
        self.var_count: int = 0
        self.constraint_count: int = 0
        self.binary_count: int = 0
        self.integer_count: int = 0
        self.continuous_count: int = 0

    @classmethod
    def from_problem(
        cls,
        prob: pulp.LpProblem,
        solver_name: str = "",
    ) -> "ModelMetadata":
        """
        Build a ModelMetadata instance by inspecting *prob*.

        Parameters
        ----------
        prob : pulp.LpProblem
            A populated PuLP problem object.
        solver_name : str
            Solver identifier for inclusion in the metadata.

        Returns
        -------
        ModelMetadata
        """
        sense_str = (
            "Minimize"
            if prob.sense == pulp.LpMinimize
            else "Maximize"
        )
        meta = cls(
            name=prob.name,
            sense=sense_str,
            solver_name=solver_name,
        )
        meta.var_count = len(prob.variables())
        meta.constraint_count = len(prob.constraints)

        for var in prob.variables():
            if var.isBinary():
                meta.binary_count += 1
            elif var.isInteger():
                meta.integer_count += 1
            else:
                meta.continuous_count += 1

        return meta

    def summary(self) -> dict[str, Any]:
        """
        Return a dictionary summary suitable for logging or display.

        Returns
        -------
        dict
            Keys: ``name``, ``sense``, ``solver``, ``var_count``,
            ``constraint_count``, ``binary``, ``integer``,
            ``continuous``.
        """
        return {
            "name": self.name,
            "sense": self.sense,
            "solver": self.solver_name,
            "var_count": self.var_count,
            "constraint_count": self.constraint_count,
            "binary": self.binary_count,
            "integer": self.integer_count,
            "continuous": self.continuous_count,
        }

    def __repr__(self) -> str:
        return (
            f"ModelMetadata(name={self.name!r}, sense={self.sense!r}, "
            f"solver={self.solver_name!r}, "
            f"vars={self.var_count}, constraints={self.constraint_count})"
        )


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def get_model_summary(prob: pulp.LpProblem) -> dict[str, Any]:
    """
    Build and return a summary dictionary for a PuLP problem.

    Parameters
    ----------
    prob : pulp.LpProblem
        The problem to introspect.

    Returns
    -------
    dict
        Summary with keys ``var_count``, ``constraint_count``,
        ``solver``, ``binary``, ``integer``, ``continuous``,
        ``name``, ``sense``.
    """
    meta = ModelMetadata.from_problem(prob)
    return meta.summary()
