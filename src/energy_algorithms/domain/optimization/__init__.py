"""Optimization domain — LP/MIP models for energy systems.

Classic operations research applied to power systems:
transportation, portfolio (mean-variance), unit commitment,
BESS storage, OneInterval asset pattern, stochastic UC.
"""
from __future__ import annotations

from energy_algorithms.domain.optimization.assets import (
    Asset,
    BatteryAsset,
    GeneratorAsset,
    SpillAsset,
    build_site,
    demo_site,
)
from energy_algorithms.domain.optimization.invariants import (
    assert_invariants,
    validate_energy_balance,
    validate_power_limits,
    validate_soc_bounds,
)
from energy_algorithms.domain.optimization.portfolio import (
    demo_portfolio,
    optimize_portfolio,
    optimize_portfolio_scipy,
)
from energy_algorithms.domain.optimization.scheduling import demo_uc, solve_unit_commitment
from energy_algorithms.domain.optimization.stochastic import (
    compute_evpi,
    compute_vss,
    generate_solar_scenarios,
    generate_wind_scenarios,
    solve_scenario_uc,
)
from energy_algorithms.domain.optimization.storage import demo_storage, solve_storage
from energy_algorithms.domain.optimization.transportation import (
    demo_transportation,
    solve_transportation,
)

__all__ = [
    # Transportation
    "solve_transportation",
    "demo_transportation",
    # Portfolio
    "optimize_portfolio",
    "optimize_portfolio_scipy",
    "demo_portfolio",
    # Unit commitment
    "solve_unit_commitment",
    "demo_uc",
    # Storage
    "solve_storage",
    "demo_storage",
    # Assets
    "Asset",
    "BatteryAsset",
    "GeneratorAsset",
    "SpillAsset",
    "build_site",
    "demo_site",
    # Invariants
    "validate_energy_balance",
    "validate_soc_bounds",
    "validate_power_limits",
    "assert_invariants",
    # Stochastic
    "generate_wind_scenarios",
    "generate_solar_scenarios",
    "solve_scenario_uc",
    "compute_vss",
    "compute_evpi",
]
