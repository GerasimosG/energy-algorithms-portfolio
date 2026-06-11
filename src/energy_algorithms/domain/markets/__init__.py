"""Energy markets domain — PCR/Euphemia, block orders, FBMC, intraday.

Core domain models for Pan-European electricity market coupling:
PCR social welfare LP, block orders (linked/exclusive),
flow-based market coupling (PTDF + RAM), continuous intraday matching.
"""
from __future__ import annotations

from energy_algorithms.domain.markets.fbmc import solve_fbmc
from energy_algorithms.domain.markets.gsk import (
 apply_gsk,
 demo_gsk,
 dynamic_gsk,
 flat_gsk,
 gmax_gsk,
)
from energy_algorithms.domain.markets.intraday import demo_intraday, simulate_intraday
from energy_algorithms.domain.markets.lodf_utils import compute_lodf, screen_cbcos
from energy_algorithms.domain.markets.market_clearing import (
 find_equilibrium,
 plot_supply_demand_stack,
)
from energy_algorithms.domain.markets.multi_day import solve_multi_day
from energy_algorithms.domain.markets.multi_zone import demo_multi_zone, solve_multi_zone
from energy_algorithms.domain.markets.pcr_model import PCRModel

__all__ = [
 "PCRModel",
 "simulate_intraday",
 "demo_intraday",
 "solve_fbmc",
 "compute_lodf",
 "screen_cbcos",
 "flat_gsk",
 "gmax_gsk",
 "dynamic_gsk",
 "apply_gsk",
 "demo_gsk",
 "solve_multi_zone",
 "demo_multi_zone",
 "solve_multi_day",
 "find_equilibrium",
 "plot_supply_demand_stack",
]
