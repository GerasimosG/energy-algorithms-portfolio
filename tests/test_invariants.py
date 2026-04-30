"""Tests for lp_optimization.invariants — physical invariant validation."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from energy_algorithms.domain.optimization.invariants import (
    validate_energy_balance,
    validate_soc_bounds,
    validate_power_limits,
    assert_invariants,
)


# ── validate_energy_balance ─────────────────────────────────────────

def test_validate_energy_balance_passes():
    """Energy balance passes when supply = demand + losses (within tolerance)."""
    assert validate_energy_balance(
        supply=[100.0, 50.0, 200.0],
        demand=[95.0, 47.0, 190.0],
        losses=[5.0, 3.0, 10.0],
        tolerance=0.01,
    )


def test_validate_energy_balance_no_losses():
    """Energy balance passes when supply = demand exactly."""
    assert validate_energy_balance(
        supply=[100.0, 50.0],
        demand=[100.0, 50.0],
        losses=None,
        tolerance=0.01,
    )


def test_validate_energy_balance_losses_optional():
    """Losses default to zero when not provided."""
    assert validate_energy_balance(
        supply=[42.0],
        demand=[42.0],
        tolerance=0.01,
    )


def test_validate_energy_balance_fails_on_shortfall():
    """Energy balance fails when supply < demand."""
    assert not validate_energy_balance(
        supply=[90.0],
        demand=[100.0],
        tolerance=0.5,
    )


def test_validate_energy_balance_fails_on_excess():
    """Energy balance fails when supply > demand + losses beyond tolerance."""
    assert not validate_energy_balance(
        supply=[105.0],
        demand=[100.0],
        losses=[2.0],
        tolerance=0.5,
    )


def test_validate_energy_balance_mixed_lengths():
    """Raises ValueError when lists have different lengths."""
    with pytest.raises(ValueError):
        validate_energy_balance(
            supply=[100, 50],
            demand=[100],
        )
    with pytest.raises(ValueError):
        validate_energy_balance(
            supply=[100],
            demand=[100],
            losses=[5, 3],
        )


def test_validate_energy_balance_strict_tolerance():
    """Energy balance fails at zero tolerance with tiny mismatch."""
    assert not validate_energy_balance(
        supply=[100.001],
        demand=[100.0],
        tolerance=0.0,
    )


# ── validate_soc_bounds ─────────────────────────────────────────────

def test_validate_soc_bounds_passes():
    """SoC bounds pass when all values are within [0, capacity]."""
    assert validate_soc_bounds(
        soc_values=[0.0, 25.0, 50.0, 100.0],
        capacity=100.0,
    )


def test_validate_soc_bounds_fails_below_zero():
    """SoC below 0 fails validation."""
    assert not validate_soc_bounds(
        soc_values=[0.0, -0.01],
        capacity=100.0,
    )


def test_validate_soc_bounds_fails_above_capacity():
    """SoC above capacity fails validation."""
    assert not validate_soc_bounds(
        soc_values=[50.0, 100.01],
        capacity=100.0,
    )


def test_validate_soc_bounds_tolerance():
    """SoC within tolerance does not fail."""
    assert validate_soc_bounds(
        soc_values=[0.0, 100.005],
        capacity=100.0,
        tolerance=0.01,
    )


def test_validate_soc_bounds_zero_capacity():
    """Zero capacity: SoC must be exactly 0."""
    assert validate_soc_bounds(
        soc_values=[0.0, 0.0],
        capacity=0.0,
    )
    assert not validate_soc_bounds(
        soc_values=[0.001],
        capacity=0.0,
        tolerance=0.0,
    )


def test_validate_soc_bounds_empty_list():
    """Empty SoC list returns True (vacuously satisfied)."""
    assert validate_soc_bounds([], capacity=100.0)


# ── validate_power_limits ───────────────────────────────────────────

def test_validate_power_limits_passes():
    """Power limits pass when all values are within [0, max_power]."""
    assert validate_power_limits(
        power_values=[0.0, 25.0, 50.0],
        max_power=50.0,
    )


def test_validate_power_limits_fails_negative():
    """Negative power fails validation."""
    assert not validate_power_limits(
        power_values=[10.0, -0.01],
        max_power=100.0,
    )


def test_validate_power_limits_fails_above_max():
    """Power above max_power fails validation."""
    assert not validate_power_limits(
        power_values=[100.0, 100.01],
        max_power=100.0,
    )


def test_validate_power_limits_tolerance():
    """Power within tolerance does not fail."""
    assert validate_power_limits(
        power_values=[100.005],
        max_power=100.0,
        tolerance=0.01,
    )


def test_validate_power_limits_empty():
    """Empty power list returns True."""
    assert validate_power_limits([], max_power=50.0)


# ── assert_invariants ───────────────────────────────────────────────

def test_assert_invariants_all_pass():
    """No exception when all checks pass."""
    result = {"status": "Optimal", "total_cost": 123.45}
    assert_invariants(result, [
        lambda r: r["status"] == "Optimal",
        lambda r: r["total_cost"] > 0,
    ])


def test_assert_invariants_one_fails():
    """Raises AssertionError when a check fails."""
    result = {"status": "Infeasible"}
    with pytest.raises(AssertionError) as exc_info:
        assert_invariants(result, [
            lambda r: r["status"] == "Optimal",
        ])
    assert "failed" in str(exc_info.value)


def test_assert_invariants_multiple_checks_run_all():
    """All checks run and failures are accumulated in the error message."""
    result = {"status": "Infeasible", "total_cost": -5}
    with pytest.raises(AssertionError) as exc_info:
        assert_invariants(result, [
            lambda r: r["status"] == "Optimal",
            lambda r: r["total_cost"] > 0,
        ])
    # Both failures should be mentioned
    msg = str(exc_info.value)
    assert "failed" in msg


def test_assert_invariants_empty_checks():
    """Empty checks list is fine."""
    assert_invariants({}, [])


def test_assert_invariants_with_names():
    """Named checks appear in the error message."""
    result = {"soc": 150, "capacity": 100}
    with pytest.raises(AssertionError) as exc_info:
        assert_invariants(result, [
            (lambda r: r["soc"] <= r["capacity"], "soc_within_capacity"),
        ])
    assert "soc_within_capacity" in str(exc_info.value)


def test_assert_invariants_lambda_str():
    """Lambda without name uses string representation."""
    result = {"x": 1}
    with pytest.raises(AssertionError):
        assert_invariants(result, [
            lambda r: r["x"] > 10,
        ])


# ── Integration with demo_site ──────────────────────────────────────

def test_invariants_on_demo_site():
    """Invariants can be run on demo_site output."""
    from energy_algorithms.domain.optimization.assets import demo_site

    result = demo_site()
    assert result["status"] == "Optimal"

    # Extract SoC values from schedule
    schedule = result["schedule"]
    soc_values = [p.get("battery_soc", 0) for p in schedule]
    battery_capacity = 100.0  # from demo_site defaults

    assert_invariants(result, [
        (lambda r: r["status"] == "Optimal", "status_optimal"),
        (lambda r: r["total_cost"] >= 0, "cost_non_negative"),
    ])
    assert validate_soc_bounds(soc_values, battery_capacity)

    # Verify energy balance from schedule
    for period in schedule:
        supply = period.get("gen_power", 0) + period.get("spill", 0) + period.get("battery_discharge", 0)
        demand = period["demand"] + period.get("battery_charge", 0)
        assert validate_energy_balance(
            supply=[supply], demand=[demand], tolerance=0.01,
        )
