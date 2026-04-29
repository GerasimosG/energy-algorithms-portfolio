"""Energy Markets module — PCR market coupling, block orders, market clearing,
and continuous intraday trading simulation.

This is the hero module for Euphemia   applications, demonstrating understanding of
the Euphemia algorithm used in Pan-European electricity market coupling, as well
as continuous intraday market microstructure (XBID/SPOT).
"""

from energy_markets.pcr_model import PCRModel
from energy_markets.intraday import simulate_intraday, demo_intraday

__all__ = ["PCRModel", "simulate_intraday", "demo_intraday"]
