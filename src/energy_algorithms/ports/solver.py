"""Solver port — abstract interface for LP/MIP solvers.

Domain code depends on this protocol, not on concrete solvers (PuLP, HiGHS, etc.).
Adapters implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SolverResult:
    """Immutable result from an optimisation solve."""

    status: str  # "Optimal", "Infeasible", "Unbounded", ...
    objective: float | None = None
    variables: dict[str, float] = field(default_factory=dict)
    solve_time: float | None = None
    solver_name: str = "unknown"


class SolverPort(ABC):
    """Abstract solver interface (Port in hexagonal architecture).

    Domain optimization problems depend on this ABC rather than
    on concrete solver classes like ``pulp.PULP_CBC_CMD``.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable solver identifier (e.g. 'CBC', 'HiGHS')."""
        ...

    @abstractmethod
    def solve(
        self,
        problem: Any,
        **options: Any,
    ) -> SolverResult:
        """Solve the given optimisation problem.

        Parameters
        ----------
        problem : Any
            An LP/MIP problem object (e.g., ``pulp.LpProblem``).
        **options : Any
            Solver-specific keyword arguments (e.g. ``msg=False``,
            ``timeLimit=60``).

        Returns
        -------
        SolverResult
            Status, objective value, variable values, timing.
        """
        ...

    @abstractmethod
    def available(self) -> bool:
        """Return ``True`` if the solver binary is installed and executable."""
        ...
