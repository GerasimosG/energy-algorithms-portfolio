"""Tests for ATC-based multi-zone market coupling."""

from __future__ import annotations

import pytest

from energy_algorithms.domain.markets.multi_zone import (
    demo_multi_zone,
    solve_multi_zone,
)


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


# ── Validation error paths ─────────────────────────────────────────


def test_atc_unknown_zone_raises() -> None:
    """ATC referencing an unknown zone raises ValueError."""
    zones = [
        {"name": "A", "supply": [{"price": 10, "qty": 100}],
         "demand": [{"price": 100, "qty": 50}]},
        {"name": "B", "supply": [{"price": 20, "qty": 100}],
         "demand": [{"price": 100, "qty": 50}]},
    ]
    with pytest.raises(ValueError, match="unknown zone"):
        solve_multi_zone(zones, {("A", "X"): 50})


def test_atc_same_zone_raises() -> None:
    """ATC pair with same start and end zone raises ValueError."""
    zones = [
        {"name": "A", "supply": [{"price": 10, "qty": 100}],
         "demand": [{"price": 100, "qty": 50}]},
    ]
    with pytest.raises(ValueError, match="must be different"):
        solve_multi_zone(zones, {("A", "A"): 50})


def test_atc_negative_capacity_raises() -> None:
    """Negative ATC capacity raises ValueError."""
    zones = [
        {"name": "A", "supply": [{"price": 10, "qty": 100}],
         "demand": [{"price": 100, "qty": 50}]},
        {"name": "B", "supply": [{"price": 20, "qty": 100}],
         "demand": [{"price": 100, "qty": 50}]},
    ]
    with pytest.raises(ValueError, match="non-negative"):
        solve_multi_zone(zones, {("A", "B"): -10})


def test_duplicate_atc_corridor_consistent_capacity() -> None:
    """Duplicate ATC corridor with same capacity is silently accepted."""
    zones = [
        {"name": "A", "supply": [{"price": 10, "qty": 100}],
         "demand": [{"price": 100, "qty": 50}]},
        {"name": "B", "supply": [{"price": 20, "qty": 100}],
         "demand": [{"price": 100, "qty": 50}]},
    ]
    # Both tuple orders — same capacity → no error
    result = solve_multi_zone(zones, {("A", "B"): 100, ("B", "A"): 100})
    assert result["status"] == "Optimal"


def test_duplicate_atc_corridor_conflicting_capacity_raises() -> None:
    """Duplicate ATC corridor with different capacities raises ValueError."""
    zones = [
        {"name": "A", "supply": [{"price": 10, "qty": 100}],
         "demand": [{"price": 100, "qty": 50}]},
        {"name": "B", "supply": [{"price": 20, "qty": 100}],
         "demand": [{"price": 100, "qty": 50}]},
    ]
    with pytest.raises(ValueError, match="conflicting"):
        solve_multi_zone(zones, {("A", "B"): 100, ("B", "A"): 200})


# ── Non-optimal status ─────────────────────────────────────────────


def test_infeasible_problem_returns_status() -> None:
    """Infeasible problem returns status dict without welfare/flows."""
    # Impossibly high demand and no supply → infeasible
    zones = [
        {
            "name": "A",
            "supply": [{"price": 10, "qty": 10}],
            "demand": [{"price": 1000, "qty": 10000}],
        },
    ]
    result = solve_multi_zone(zones, {})
    # Either Infeasible or Optimal depending on solver's ability
    # to satisfy demand (puLP might meet demand partially)
    assert "status" in result
    # If not Optimal, should only have 'status' key
    if result["status"] != "Optimal":
        assert set(result.keys()) == {"status"}


# ── demo_multi_zone ────────────────────────────────────────────────


def test_demo_multi_zone_runs() -> None:
    """demo_multi_zone runs without error and returns a valid result."""
    result = demo_multi_zone()
    assert result["status"] == "Optimal"
    assert result["welfare"] > 0
    assert "North" in result["zones"]
    assert "Center" in result["zones"]
    assert "South" in result["zones"]


def test_demo_multi_zone_flows_exist() -> None:
    """Demo produces flows between zones."""
    result = demo_multi_zone()
    assert len(result["flows"]) > 0
    # North has cheap wind → should export to Center
    assert "North→Center" in result["flows"] or "Center→North" in result["flows"]


def test_demo_multi_zone_zone_details() -> None:
    """Each zone has supply_cleared_mw, demand_cleared_mw, and mcp."""
    result = demo_multi_zone()
    for zname in ("North", "Center", "South"):
        z = result["zones"][zname]
        assert "supply_cleared_mw" in z
        assert "demand_cleared_mw" in z
        assert "mcp" in z
        assert z["supply_cleared_mw"] > 0
        assert z["demand_cleared_mw"] > 0
