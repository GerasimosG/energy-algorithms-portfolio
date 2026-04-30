"""Energy Markets module — PCR market coupling, block orders, market clearing,
and continuous intraday trading simulation.

This is the hero module for Euphemia   applications, demonstrating understanding of
the Euphemia algorithm used in Pan-European electricity market coupling, as well
as continuous intraday market microstructure (XBID/SPOT).
"""

from energy_markets.pcr_model import PCRModel
from energy_markets.intraday import simulate_intraday, demo_intraday
from energy_markets.fbmc import solve_fbmc
from energy_markets.lodf_utils import compute_lodf, screen_cbcos
from energy_markets.gsk import flat_gsk, gmax_gsk, dynamic_gsk, apply_gsk, demo_gsk

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
]
