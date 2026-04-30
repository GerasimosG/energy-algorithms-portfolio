"""Ports layer — abstract interfaces (Protocols / ABCs).

Defines the contracts between domain logic and infrastructure.
Adapters implement these ports; domain code depends only on ports.
"""

from energy_algorithms.ports.solver import SolverPort, SolverResult

__all__ = ["SolverPort", "SolverResult"]
