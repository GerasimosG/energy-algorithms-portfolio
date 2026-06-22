"""Resource-adequacy metrics (pure functions, numpy only).

Conventions: power MW, energy MWh, LOLE in hours/year, EENS in MWh/year.
All inputs accept list / np.ndarray / pd.Series; outputs numpy/float.
"""

from __future__ import annotations

import numpy as np

# Type hint for array-like inputs
ArrayLike = np.ndarray | list | object


def _arr(x) -> np.ndarray:
    return np.asarray(x, dtype=float)


def hourly_margin(available_mw, demand_mw) -> np.ndarray:
    """Per-hour capacity margin: available - demand (negative shortfall)."""
    return _arr(available_mw) - _arr(demand_mw)


def energy_not_served(available_mw, demand_mw) -> np.ndarray:
    """Per-hour energy not served (MWh): max(demand - available, 0)."""
    return np.maximum(_arr(demand_mw) - _arr(available_mw), 0.0)


def loss_of_load_expectation(available_mw, demand_mw) -> float:
    """Number hours any shortfall (LOLE, h/yr single year)."""
    return float((energy_not_served(available_mw, demand_mw) > 0).sum())


def expected_energy_not_served(available_mw, demand_mw) -> float:
    """Total energy not served over horizon (EENS, MWh)."""
    return float(energy_not_served(available_mw, demand_mw).sum())


def reserve_margin(total_capacity_mw: float, peak_demand_mw: float) -> float:
    """Reserve margin peak: (capacity - peak) / peak."""
    return (float(total_capacity_mw) - float(peak_demand_mw)) / float(peak_demand_mw)


def duration_curve(values) -> np.ndarray:
    """Return sorted values in descending order."""
    return np.sort(_arr(values))[::-1]
