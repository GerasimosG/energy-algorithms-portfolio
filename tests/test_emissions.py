"""Tests for domain/emissions.py — CO₂-adjusted cost calculations."""

from __future__ import annotations

import pytest

from energy_algorithms.domain.emissions import (
    EMISSION_FACTORS,
    adjusted_marginal_cost,
    co2_adjusted_marginal_cost,
    co2_cost_per_mwh,
)


# ── co2_adjusted_marginal_cost ─────────────────────────────────────


def test_co2_adjusted_with_explicit_factor() -> None:
    """Explicit emission_factor is used directly."""
    result = co2_adjusted_marginal_cost(
        fuel_cost=50.0, emission_factor=0.4, co2_price=70.0
    )
    expected = 50.0 + 0.4 * 70.0  # 50 + 28 = 78
    assert result == expected


def test_co2_adjusted_default_co2_price() -> None:
    """Default co2_price of 70 is used when not specified."""
    result = co2_adjusted_marginal_cost(
        fuel_cost=30.0, emission_factor=0.5
    )
    expected = 30.0 + 0.5 * 70.0  # 30 + 35 = 65
    assert result == expected


def test_co2_adjusted_none_factor_high_fuel() -> None:
    """When emission_factor is None and fuel_cost > 30, heuristic uses 0.4."""
    result = co2_adjusted_marginal_cost(
        fuel_cost=50.0, emission_factor=None, co2_price=70.0
    )
    expected = 50.0 + 0.4 * 70.0  # 50 + 28 = 78
    assert result == expected


def test_co2_adjusted_none_factor_low_fuel() -> None:
    """When emission_factor is None and fuel_cost <= 30, heuristic uses 0.0."""
    result = co2_adjusted_marginal_cost(
        fuel_cost=20.0, emission_factor=None, co2_price=70.0
    )
    expected = 20.0 + 0.0 * 70.0  # 20
    assert result == expected


def test_co2_adjusted_none_factor_boundary_30() -> None:
    """Boundary: fuel_cost == 30 should use heuristic 0.0 (not > 30)."""
    result = co2_adjusted_marginal_cost(
        fuel_cost=30.0, emission_factor=None, co2_price=70.0
    )
    expected = 30.0 + 0.0 * 70.0  # 30
    assert result == expected


def test_co2_adjusted_custom_co2_price() -> None:
    """Custom co2_price is respected."""
    result = co2_adjusted_marginal_cost(
        fuel_cost=50.0, emission_factor=0.4, co2_price=100.0
    )
    expected = 50.0 + 0.4 * 100.0  # 50 + 40 = 90
    assert result == expected


def test_co2_adjusted_zero_emission_factor() -> None:
    """Zero emission factor — no CO₂ adder."""
    result = co2_adjusted_marginal_cost(
        fuel_cost=100.0, emission_factor=0.0, co2_price=70.0
    )
    assert result == 100.0


# ── co2_cost_per_mwh ───────────────────────────────────────────────


def test_co2_cost_per_mwh_known_type() -> None:
    """Known generation type returns factor × co2_price."""
    factor = EMISSION_FACTORS["Fossil Hard coal"]  # 0.82
    result = co2_cost_per_mwh("Fossil Hard coal", co2_price=70.0)
    expected = round(0.82 * 70.0, 2)
    assert result == expected


def test_co2_cost_per_mwh_zero_emission_type() -> None:
    """Zero-carbon sources return 0.0."""
    assert co2_cost_per_mwh("Nuclear", co2_price=70.0) == 0.0
    assert co2_cost_per_mwh("Wind Onshore", co2_price=70.0) == 0.0
    assert co2_cost_per_mwh("Solar", co2_price=70.0) == 0.0


def test_co2_cost_per_mwh_unknown_type() -> None:
    """Unknown gen_type uses default emission factor (0.4)."""
    result = co2_cost_per_mwh("Fusion Reactor", co2_price=70.0)
    expected = round(0.4 * 70.0, 2)
    assert result == expected


def test_co2_cost_per_mwh_custom_price() -> None:
    """Custom co2_price is used instead of default 70."""
    result = co2_cost_per_mwh("Fossil Gas", co2_price=80.0)
    expected = round(0.40 * 80.0, 2)
    assert result == expected


def test_co2_cost_per_mwh_default_price() -> None:
    """Default co2_price = 70 is used."""
    result = co2_cost_per_mwh("Fossil Gas")
    expected = round(0.40 * 70.0, 2)
    assert result == expected


# ── adjusted_marginal_cost ─────────────────────────────────────────


def test_adjusted_marginal_cost_known_type() -> None:
    """Full cost = fuel_cost + CO₂ cost for known gen_type."""
    result = adjusted_marginal_cost("Fossil Hard coal", fuel_cost=50.0)
    co2_adder = round(0.82 * 70.0, 2)
    expected = round(50.0 + co2_adder, 2)
    assert result == expected


def test_adjusted_marginal_cost_zero_fuel() -> None:
    """Zero fuel cost — only CO₂ adder applies."""
    result = adjusted_marginal_cost("Fossil Gas", fuel_cost=0.0, co2_price=70.0)
    expected = round(0.0 + round(0.40 * 70.0, 2), 2)
    assert result == expected


def test_adjusted_marginal_cost_unknown_type() -> None:
    """Unknown gen_type uses default emission factor."""
    result = adjusted_marginal_cost("UnknownType", fuel_cost=30.0)
    co2_adder = round(0.4 * 70.0, 2)
    expected = round(30.0 + co2_adder, 2)
    assert result == expected


def test_adjusted_marginal_cost_zero_emission_type() -> None:
    """Zero-carbon source — no CO₂ adder, just fuel cost."""
    result = adjusted_marginal_cost("Nuclear", fuel_cost=10.0)
    assert result == 10.0


def test_adjusted_marginal_cost_custom_co2_price() -> None:
    """Custom CO₂ price flows through to final cost."""
    result = adjusted_marginal_cost("Fossil Oil", fuel_cost=40.0, co2_price=90.0)
    co2_adder = round(0.75 * 90.0, 2)
    expected = round(40.0 + co2_adder, 2)
    assert result == expected
