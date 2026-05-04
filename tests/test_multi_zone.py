"""Tests for ATC-based multi-zone market coupling."""

from __future__ import annotations

from energy_algorithms.domain.markets.multi_zone import solve_multi_zone


def test_single_atc_pair_allows_profitable_reverse_flow() -> None:
    """A declared ATC pair is bidirectional, regardless of tuple order."""
    zones = [
        {
            "name": "A",
            "supply": [{"price": 100, "qty": 100}],
            "demand": [{"price": 150, "qty": 100}],
        },
        {
            "name": "B",
            "supply": [{"price": 10, "qty": 100}],
            "demand": [{"price": 20, "qty": 100}],
        },
    ]

    result = solve_multi_zone(zones, {("A", "B"): 100})

    assert result["status"] == "Optimal"
    assert result["flows"] == {"B→A": 100.0}
    assert result["zones"]["A"]["supply_cleared_mw"] == 0.0
    assert result["zones"]["A"]["demand_cleared_mw"] == 100.0
    assert result["zones"]["B"]["supply_cleared_mw"] == 100.0
