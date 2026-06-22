import numpy as np
import pytest

from energy_algorithms.domain.adequacy.metrics import (
    duration_curve,
    energy_not_served,
    expected_energy_not_served,
    hourly_margin,
    loss_of_load_expectation,
    reserve_margin,
)


def test_no_shortfall_is_zero():
    avail, dem = [100, 100, 100], [90, 80, 100]
    assert expected_energy_not_served(avail, dem) == 0.0
    assert loss_of_load_expectation(avail, dem) == 0.0
    assert np.array_equal(energy_not_served(avail, dem), np.zeros(3))

def test_shortfall_counts_hours_and_energy():
    avail, dem = [100, 50, 80], [90, 80, 100]   # short by 30 then 20
    assert loss_of_load_expectation(avail, dem) == 2.0
    assert expected_energy_not_served(avail, dem) == 50.0
    assert np.array_equal(energy_not_served(avail, dem), np.array([0, 30, 20]))

def test_margin_and_duration_curve():
    assert np.array_equal(hourly_margin([100, 50], [90, 80]), np.array([10, -30]))
    assert np.array_equal(duration_curve([1, 5, 3]), np.array([5, 3, 1]))

def test_reserve_margin():
    assert reserve_margin(120, 100) == pytest.approx(0.2)
