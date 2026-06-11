"""Energy Algorithms — optimization portfolio for energy/quant roles.

Hexagonal architecture with clean separation:
- ``domain/`` — pure business logic (no I/O)
- ``ports/`` — abstract interfaces (Protocols / ABCs)
- ``adapters/`` — concrete implementations of ports
- ``application/`` — use-case orchestrators
- ``infrastructure/`` — cross-cutting concerns (hooks, options, metadata)
"""
from __future__ import annotations

from energy_algorithms.adapters import PuLPSolverAdapter
from energy_algorithms.domain import (
 get_option,
 set_option,
)
from energy_algorithms.domain.markets import PCRModel, solve_fbmc
from energy_algorithms.domain.optimization import (
 Asset,
 BatteryAsset,
 GeneratorAsset,
 SpillAsset,
 build_site,
 optimize_portfolio,
 optimize_portfolio_scipy,
 solve_storage,
 solve_transportation,
 solve_unit_commitment,
)
from energy_algorithms.infrastructure import (
 get_solver,
)

__all__ = [
 # Markets
 "PCRModel",
 "solve_fbmc",
 # Optimization
 "solve_unit_commitment",
 "solve_storage",
 "solve_transportation",
 "optimize_portfolio",
 "optimize_portfolio_scipy",
 "Asset",
 "BatteryAsset",
 "GeneratorAsset",
 "SpillAsset",
 "build_site",
 # Infrastructure
 "get_solver",
 "get_option",
 "set_option",
 # Adapters
 "PuLPSolverAdapter",
]
