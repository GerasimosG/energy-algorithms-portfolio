"""Monte-Carlo resource-adequacy screening (pure, numpy only).

Samples 2-state thermal-unit availability from forced-outage rates, adds a VRE
availability profile, and accounts the hourly capacity stack by merit order
(no LP) to derive LOLE / EENS with confidence across Monte-Carlo years.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class AdequacyInputs:
    unit_capacity_mw: np.ndarray   # (n_units,)
    unit_for: np.ndarray           # (n_units,) forced-outage rate in [0, 1]
    demand_mw: np.ndarray          # (n_hours,)
    vre_mw: np.ndarray             # (n_hours,) available renewable infeed


@dataclass
class AdequacyResult:
    lole_h: float                  # mean loss-of-load hours per year
    eens_mwh: float                # mean expected energy not served per year
    lolp_by_hour: np.ndarray       # (n_hours,) P(shortfall) at each hour
    margin_by_hour_mean: np.ndarray
    ens_by_hour_mean: np.ndarray
    lole_samples: np.ndarray       # (n_years,)
    eens_samples: np.ndarray       # (n_years,)


def run_monte_carlo(inputs: AdequacyInputs, n_years: int = 100, seed: int = 42) -> AdequacyResult:
    """Run an N-year Monte-Carlo adequacy screening. Deterministic given ``seed``."""
    rng = np.random.default_rng(seed)
    cap = np.asarray(inputs.unit_capacity_mw, float)
    fo = np.asarray(inputs.unit_for, float)
    demand = np.asarray(inputs.demand_mw, float)
    vre = np.asarray(inputs.vre_mw, float)
    n_hours = demand.shape[0]

    lole_samples = np.empty(n_years)
    eens_samples = np.empty(n_years)
    short_count = np.zeros(n_hours)
    margin_sum = np.zeros(n_hours)
    ens_sum = np.zeros(n_hours)

    for y in range(n_years):
        available_units = rng.random((n_hours, cap.size)) > fo       # (n_hours, n_units) bool
        thermal = available_units @ cap                              # (n_hours,)
        available = thermal + vre
        margin = available - demand
        ens = np.maximum(-margin, 0.0)
        lole_samples[y] = float((ens > 0).sum())
        eens_samples[y] = float(ens.sum())
        short_count += ens > 0
        margin_sum += margin
        ens_sum += ens

    return AdequacyResult(
        lole_h=float(lole_samples.mean()),
        eens_mwh=float(eens_samples.mean()),
        lolp_by_hour=short_count / n_years,
        margin_by_hour_mean=margin_sum / n_years,
        ens_by_hour_mean=ens_sum / n_years,
        lole_samples=lole_samples,
        eens_samples=eens_samples,
    )
