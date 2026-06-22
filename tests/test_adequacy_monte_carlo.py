import numpy as np

from energy_algorithms.domain.adequacy.monte_carlo import (
    AdequacyInputs,
    AdequacyResult,
    run_monte_carlo,
)


def _inp(cap, for_, demand, vre):
    return AdequacyInputs(
        unit_capacity_mw=np.array(cap, float), unit_for=np.array(for_, float),
        demand_mw=np.array(demand, float), vre_mw=np.array(vre, float),
    )

def test_zero_outage_no_shortfall():
    r = run_monte_carlo(_inp([100, 100], [0, 0], [150, 150], [0, 0]), n_years=5, seed=1)
    assert isinstance(r, AdequacyResult)
    assert r.lole_h == 0.0 and r.eens_mwh == 0.0

def test_guaranteed_shortfall_is_deterministic():
    # one 100 MW unit, never enough for 150 MW demand -> always short by 50
    r = run_monte_carlo(_inp([100], [0], [150], [0]), n_years=10, seed=1)
    assert r.lole_h == 1.0
    assert r.eens_mwh == 50.0
    assert r.lolp_by_hour.tolist() == [1.0]

def test_seed_is_reproducible():
    args = ([100, 80], [0.1, 0.2], [150, 120], [10, 5])
    a = run_monte_carlo(_inp(*args), n_years=50, seed=7)
    b = run_monte_carlo(_inp(*args), n_years=50, seed=7)
    assert a.lole_h == b.lole_h and a.eens_mwh == b.eens_mwh
