"""Tests for ancillary services: FCR bid + joint BESS reserve optimisation."""
from __future__ import annotations

import math

import pytest

from energy_algorithms.domain.optimization.ancillary import (
    demo_joint_bess_reserve,
    solve_fcr_only,
    solve_joint_bess_reserve,
)

# ── FCR-only ──────────────────────────────────────────────────────────


def test_fcr_only_optimal_is_full_power():
    """FCR-only is a pure capacity LP: optimum is full power capability."""
    r = solve_fcr_only(fcr_price=20.0, max_power_mw=50.0, horizon_hours=24)
    assert r["status"] == "Optimal"
    assert math.isclose(r["fcr_capacity_mw"], 50.0, abs_tol=1e-6)
    assert math.isclose(r["revenue_eur"], 50.0 * 20.0 * 24, abs_tol=1e-6)


def test_fcr_only_scales_with_price():
    """Revenue scales linearly with FCR price (capacity is constant)."""
    r_low = solve_fcr_only(fcr_price=10.0, max_power_mw=30.0, horizon_hours=24)
    r_high = solve_fcr_only(fcr_price=40.0, max_power_mw=30.0, horizon_hours=24)
    assert r_low["fcr_capacity_mw"] == r_high["fcr_capacity_mw"] == 30.0
    assert math.isclose(
        r_high["revenue_eur"] / r_low["revenue_eur"], 4.0, abs_tol=1e-6
    )


def test_fcr_only_horizon_24_default():
    """24-hour horizon is the default Belgian daily procurement window."""
    r_explicit = solve_fcr_only(
        fcr_price=15.0, max_power_mw=10.0, horizon_hours=24
    )
    r_default = solve_fcr_only(fcr_price=15.0, max_power_mw=10.0)
    assert math.isclose(
        r_explicit["revenue_eur"], r_default["revenue_eur"], abs_tol=1e-6
    )


# ── Joint BESS + FCR + aFRR ───────────────────────────────────────────


def test_joint_bess_reserve_known_optimal_toy_case():
    """
    1-period toy case: energy prices are 0 (no arbitrage opportunity),
    FCR price is high, aFRR prices are 0. The optimiser should commit
    full FCR capacity (the only positive-revenue stream) and skip
    energy activity. This isolates the FCR revenue stream.
    """
    r = solve_joint_bess_reserve(
        prices=[0.0],
        capacity_mwh=10.0,
        max_power_mw=5.0,
        eff_in=1.0,
        eff_out=1.0,
        initial_soc_mwh=5.0,
        fcr_price=20.0,
        afrr_up_price=[0.0],
        afrr_down_price=[0.0],
        afrr_activation_prob=0.0,
        horizon_hours=1,
    )
    assert r["status"] == "Optimal"
    # All FCR, no aFRR, no energy activity
    assert math.isclose(r["fcr_capacity_mw"], 5.0, abs_tol=1e-4)
    assert all(v == 0.0 for v in r["afrr_up"])
    assert all(v == 0.0 for v in r["afrr_down"])
    # FCR revenue = 5 MW × 20 €/MW/h × 1 h = 100 €
    assert math.isclose(r["fcr_revenue_eur"], 100.0, abs_tol=1e-3)
    assert r["afrr_revenue_eur"] == 0.0
    assert r["energy_revenue_eur"] == 0.0


def test_joint_reserve_mismatched_afrr_length_raises():
    """Defensive: aFRR price series length must match prices length."""
    with pytest.raises(ValueError, match="must match prices length"):
        solve_joint_bess_reserve(
            prices=[40.0, 50.0, 60.0],
            capacity_mwh=10.0,
            max_power_mw=5.0,
            eff_in=1.0,
            eff_out=1.0,
            initial_soc_mwh=5.0,
            fcr_price=20.0,
            afrr_up_price=[10.0, 10.0],  # wrong length
            afrr_down_price=[8.0, 8.0, 8.0],
        )


def test_joint_reserve_high_fcr_uses_full_power():
    """
    With high FCR price and low energy spread, full capacity goes to FCR.
    """
    r = solve_joint_bess_reserve(
        prices=[50.0, 51.0],  # tiny spread, no arbitrage
        capacity_mwh=10.0,
        max_power_mw=5.0,
        eff_in=0.9,
        eff_out=0.9,
        initial_soc_mwh=5.0,
        fcr_price=200.0,  # very high FCR price
        afrr_up_price=[0.0, 0.0],
        afrr_down_price=[0.0, 0.0],
        afrr_activation_prob=0.0,
    )
    assert r["status"] == "Optimal"
    # FCR should saturate at max_power
    assert r["fcr_capacity_mw"] > 4.9


def test_joint_reserve_zero_fcr_uses_energy_arbitrage():
    """
    With FCR=0 and a price spread, the model should arbitrage energy.

    Prices: cheap then expensive — charge in t=0, discharge in t=1.
    """
    r = solve_joint_bess_reserve(
        prices=[10.0, 100.0],
        capacity_mwh=10.0,
        max_power_mw=5.0,
        eff_in=1.0,
        eff_out=1.0,
        initial_soc_mwh=0.0,
        fcr_price=0.0,
        afrr_up_price=[0.0, 0.0],
        afrr_down_price=[0.0, 0.0],
    )
    assert r["status"] == "Optimal"
    assert r["fcr_capacity_mw"] == 0.0
    # Should charge in t=0, discharge in t=1
    assert r["schedule"][0]["charge_mw"] > 0.1
    assert r["schedule"][1]["discharge_mw"] > 0.1
    # Energy revenue ≈ 5 MW × (100 - 10) = 450 € (per MWh×MW over 1h)
    # charge=5 MW for 1h → 5 MWh stored → discharge=5 MW for 1h → 5 MWh
    # revenue = 5 * 100 - 5 * 10 = 450 €
    assert r["energy_revenue_eur"] > 400.0


def test_joint_reserve_revenue_components_sum_to_total():
    """Revenue decomposition is exact: total == energy + fcr + afrr."""
    r = solve_joint_bess_reserve(
        prices=[30.0, 50.0, 80.0, 40.0, 60.0, 70.0],
        capacity_mwh=20.0,
        max_power_mw=8.0,
        eff_in=0.92,
        eff_out=0.92,
        initial_soc_mwh=10.0,
        fcr_price=15.0,
        afrr_up_price=[10.0, 12.0, 18.0, 14.0, 16.0, 20.0],
        afrr_down_price=[8.0, 10.0, 14.0, 12.0, 14.0, 16.0],
        afrr_activation_prob=0.3,
    )
    assert r["status"] == "Optimal"
    total = (
        r["energy_revenue_eur"]
        + r["fcr_revenue_eur"]
        + r["afrr_revenue_eur"]
    )
    assert math.isclose(total, r["total_revenue_eur"], abs_tol=1e-3)


def test_joint_reserve_zero_fcr_zero_afrr_uses_energy_arbitrage():
    """
    When FCR and aFRR prices are all zero, the model reduces to
    pure energy arbitrage. With a clear price spread (10 → 100), the
    model should buy at t=0 and sell at t=1, ignoring reserve.
    """
    r = solve_joint_bess_reserve(
        prices=[10.0, 100.0],
        capacity_mwh=10.0,
        max_power_mw=5.0,
        eff_in=0.9,
        eff_out=0.9,
        initial_soc_mwh=0.0,
        fcr_price=0.0,
        afrr_up_price=[0.0, 0.0],
        afrr_down_price=[0.0, 0.0],
    )
    assert r["status"] == "Optimal"
    # No reserve committed
    assert r["fcr_capacity_mw"] == 0.0
    assert all(v == 0.0 for v in r["afrr_up"])
    assert all(v == 0.0 for v in r["afrr_down"])
    # All revenue comes from energy
    assert r["afrr_revenue_eur"] == 0.0
    assert r["fcr_revenue_eur"] == 0.0
    # Energy arbitrage positive
    assert r["energy_revenue_eur"] > 0.0
    assert math.isclose(
        r["total_revenue_eur"], r["energy_revenue_eur"], abs_tol=1e-3
    )


def test_joint_reserve_preserves_soc_dynamics():
    """SoC dynamics hold: soc[t] = prev_soc + η_in·charge - discharge/η_out."""
    r = solve_joint_bess_reserve(
        prices=[20.0, 30.0, 50.0, 80.0],
        capacity_mwh=10.0,
        max_power_mw=5.0,
        eff_in=0.9,
        eff_out=0.9,
        initial_soc_mwh=0.0,
        fcr_price=0.0,
        afrr_up_price=[0.0] * 4,
        afrr_down_price=[0.0] * 4,
    )
    assert r["status"] == "Optimal"
    prev_soc = 0.0  # initial_soc_mwh
    for t, period in enumerate(r["schedule"]):
        expected = prev_soc + 0.9 * period["charge_mw"] - period["discharge_mw"] / 0.9
        assert math.isclose(period["soc_mwh"], expected, abs_tol=1e-3)
        assert 0.0 <= period["soc_mwh"] <= 10.0
        prev_soc = period["soc_mwh"]


# ── Demo ──────────────────────────────────────────────────────────────


def test_demo_joint_bess_reserve_runs():
    """Demo on 24h Belgian profile solves and is feasible."""
    r = demo_joint_bess_reserve()
    assert r["status"] == "Optimal"
    assert r["total_revenue_eur"] > 0.0
    assert r["fcr_capacity_mw"] >= 0.0
    assert len(r["afrr_up"]) == 24
    assert len(r["afrr_down"]) == 24
    assert len(r["schedule"]) == 24
