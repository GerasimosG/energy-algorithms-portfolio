"""PuLP implementation of the SolverPort abstract interface.

This adapter bridges domain optimization code (which depends on the
``SolverPort`` ABC defined in ``energy_algorithms.ports.solver``)
with the concrete PuLP solver ecosystem.

Usage::

 from energy_algorithms.adapters.pulp_solver import PuLPSolverAdapter

 solver = PuLPSolverAdapter()
 result = solver.solve(problem, timeLimit=60)
 print(result.status, result.objective)
"""

from __future__ import annotations

import time
from typing import Any

import pulp
from pulp.apis.core import PulpSolverError

from energy_algorithms.ports.solver import SolverPort, SolverResult


class PuLPSolverAdapter(SolverPort):
 """Adapter wrapping PuLP's solver interface behind the SolverPort ABC.

 Supports any solver that PuLP can discover (CBC, HiGHS, Gurobi, CPLEX).
 """

 def __init__(self, solver_id: str = "cbc") -> None:
 self._solver_id = solver_id
 self._solver_cls = self._resolve_class(solver_id)

 @staticmethod
 def _resolve_class(solver_id: str) -> type:
 """Return the PuLP solver class for *solver_id*."""
 mapping: dict[str, type] = {
 "cbc": pulp.PULP_CBC_CMD,
 "highs": pulp.HiGHS_CMD,
 "gurobi": pulp.GUROBI_CMD,
 "cplex": pulp.CPLEX_CMD,
 "glpk": pulp.GLPK_CMD,
 }
 cls = mapping.get(solver_id.lower())
 if cls is None:
 msg = f"Unknown solver {solver_id!r}; choose from {list(mapping)}"
 raise ValueError(msg)
 return cls

 @property
 def name(self) -> str:
 return self._solver_id.upper()

 def solve(self, problem: Any, **options: Any) -> SolverResult:
 """Solve *problem* and return a ``SolverResult``.

 Parameters
 ----------
 problem : pulp.LpProblem
 The PuLP problem instance to solve.
 **options : Any
 Passed as keyword arguments to the PuLP solver constructor.
 Common options: ``msg`` (bool), ``timeLimit`` (int seconds),
 ``gapRel`` (float), ``threads`` (int).

 Returns
 -------
 SolverResult
 """
 t0 = time.perf_counter()

 # Build the solver instance with options
 solver_instance = self._solver_cls(**options)
 try:
 problem.solve(solver_instance)
 except PulpSolverError:
 elapsed = time.perf_counter() - t0
 if not problem.constraints:
 return SolverResult(
 status="Unbounded",
 objective=None,
 variables={},
 solve_time=elapsed,
 solver_name=self.name,
 )
 raise

 elapsed = time.perf_counter() - t0

 status_map = {
 pulp.LpStatusOptimal: "Optimal",
 pulp.LpStatusInfeasible: "Infeasible",
 pulp.LpStatusUnbounded: "Unbounded",
 pulp.LpStatusNotSolved: "Not Solved",
 }
 status_str = status_map.get(problem.status, str(problem.status))

 variables = {}
 for v in problem.variables():
 val = pulp.value(v)
 if val is not None:
 variables[v.name] = float(val)

 return SolverResult(
 status=status_str,
 objective=float(pulp.value(problem.objective))
 if problem.status == pulp.LpStatusOptimal
 else None,
 variables=variables,
 solve_time=elapsed,
 solver_name=self.name,
 )

 def available(self) -> bool:
 """Return ``True`` if the solver binary is installed."""
 try:
 solver = self._solver_cls()
 return solver.available()
 except Exception:
 return False
