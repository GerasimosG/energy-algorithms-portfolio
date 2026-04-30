"""Optimization domain — LP/MIP models for energy systems.

Classic operations research applied to power systems:
transportation, portfolio (mean-variance), unit commitment,
BESS storage, OneInterval asset pattern, stochastic UC.
"""
from __future__ import annotations


from energy_algorithms.domain.optimization.transportation import solve_transportation, demo_transportation
from energy_algorithms.domain.optimization.portfolio import (
    optimize_portfolio,
    optimize_portfolio_scipy,
    demo_portfolio,
)
from energy_algorithms.domain.optimization.scheduling import solve_unit_commitment, demo_uc
from energy_algorithms.domain.optimization.storage import solve_storage, demo_storage
from energy_algorithms.domain.optimization.assets import (
    Asset,
    BatteryAsset,
    GeneratorAsset,
    SpillAsset,
    build_site,
    demo_site,
)
from energy_algorithms.domain.optimization.invariants import (
    validate_energy_balance,
    validate_soc_bounds,
    validate_power_limits,
    assert_invariants,
)
from energy_algorithms.domain.optimization.stochastic import (
    generate_wind_scenarios,
    generate_solar_scenarios,
    solve_scenario_uc,
    compute_vss,
    compute_evpi,
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
