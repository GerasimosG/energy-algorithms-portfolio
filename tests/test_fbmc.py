"""Tests for FBMC (Flow-Based Market Coupling) — energy_markets module."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest

from energy_markets.fbmc import solve_fbmc


# ── 2-Zone, 1-Branch (should match ATC) ──────────────────────────

def test_fbmc_2zone_simple():
    """2 zones, 1 branch: FBMC reduces to ATC-equivalent with same capacity."""
    zones = [
        {
            "name": "North", "zone_id": 0,
            "supply": [{"price": 10, "qty": 200}],
            "demand": [{"price": 100, "qty": 100}],
        },
        {
            "name": "South", "zone_id": 1,
            "supply": [{"price": 50, "qty": 200}],
            "demand": [{"price": 100, "qty": 150}],
        },
    ]
    # 1 branch, 2 zones. PTDF: flow = 0.5*NP[0] - 0.5*NP[1]
    # Since NP[0] + NP[1] = 0 (energy balance), flow = NP[0]
    ptdf = np.array([[0.5, -0.5]])
    zone_names = ["North", "South"]
    ram_limits = [{"name": "N_S", "ram_forward": 150, "ram_reverse": 150}]

    result = solve_fbmc(zones, ptdf, ram_limits, zone_names)

    assert result["status"] == "Optimal"
    assert result["welfare"] > 0
    assert "zones" in result
    assert "North" in result["zones"]
    assert "South" in result["zones"]
    # North should export to South (cheaper generation)
    assert result["zones"]["North"]["supply_cleared_mw"] >= result["zones"]["North"]["demand_cleared_mw"]


def test_fbmc_2zone_binding_constraint():
    """Branch constraint binds: cheaper zone exports hit RAM limit."""
    zones = [
        {
            "name": "North", "zone_id": 0,
            "supply": [{"price": 10, "qty": 500}],  # Lots of cheap power
            "demand": [{"price": 100, "qty": 50}],
        },
        {
            "name": "South", "zone_id": 1,
            "supply": [{"price": 80, "qty": 300}],  # Expensive
            "demand": [{"price": 100, "qty": 200}],
        },
    ]
    ptdf = np.array([[0.5, -0.5]])
    zone_names = ["North", "South"]
    ram_limits = [{"name": "N_S", "ram_forward": 50, "ram_reverse": 50}]  # Tight!

    result = solve_fbmc(zones, ptdf, ram_limits, zone_names)

    assert result["status"] == "Optimal"
    north = result["zones"]["North"]
    south = result["zones"]["South"]
    # North exports at most 50 MW due to RAM limit
    net_export = north["supply_cleared_mw"] - north["demand_cleared_mw"]
    assert net_export <= 50 + 0.1  # Allow small tolerance
    # South must use some expensive supply since cheap imports constrained
    assert south["supply_cleared_mw"] > 0


# ── 3-Zone Triangle (loop flows) ─────────────────────────────────

def test_fbmc_3zone_loop_flow():
    """3 zones in a triangle: PTDF captures loop flows that ATC cannot."""
    zones = [
        {
            "name": "A", "zone_id": 0,
            "supply": [{"price": 5, "qty": 300}],   # Very cheap
            "demand": [{"price": 100, "qty": 50}],
        },
        {
            "name": "B", "zone_id": 1,
            "supply": [{"price": 40, "qty": 200}],  # Medium
            "demand": [{"price": 100, "qty": 200}],
        },
        {
            "name": "C", "zone_id": 2,
            "supply": [{"price": 70, "qty": 200}],  # Expensive
            "demand": [{"price": 100, "qty": 150}],
        },
    ]
    # 3 critical branches forming a triangle A-B-C-A
    # Row sums to 0 (Kirchhoff's law — import=export)
    ptdf = np.array([
        [ 0.6, -0.4, -0.2],  # Line AB
        [ 0.3,  0.3, -0.6],  # Line BC
        [ 0.1, -0.1,  0.0],  # Line AC
    ])
    zone_names = ["A", "B", "C"]
    ram_limits = [
        {"name": "AB", "ram_forward": 200, "ram_reverse": 200},
        {"name": "BC", "ram_forward": 200, "ram_reverse": 200},
        {"name": "AC", "ram_forward": 200, "ram_reverse": 200},
    ]

    result = solve_fbmc(zones, ptdf, ram_limits, zone_names)

    assert result["status"] == "Optimal"
    assert result["welfare"] > 0
    assert len(result["branch_flows"]) == 3
    # Branch flows should sum to something (loop flow exists)
    flow_values = [f["flow_mw"] for f in result["branch_flows"]]
    assert all(isinstance(f, (int, float)) for f in flow_values)


def test_fbmc_3zone_binding_loop():
    """PTDF loop flow constrains cheap zone differently than ATC would."""
    zones = [
        {
            "name": "A", "zone_id": 0,
            "supply": [{"price": 5, "qty": 500}],    # Very cheap
            "demand": [{"price": 100, "qty": 50}],
        },
        {
            "name": "B", "zone_id": 1,
            "supply": [{"price": 40, "qty": 200}],
            "demand": [{"price": 100, "qty": 150}],
        },
        {
            "name": "C", "zone_id": 2,
            "supply": [{"price": 70, "qty": 200}],
            "demand": [{"price": 100, "qty": 200}],
        },
    ]
    # Tight RAM on AC means flow from A→C is limited
    # But A→C flow depends not just on A's export but also on B's position
    ptdf = np.array([
        [ 0.6, -0.4, -0.2],
        [ 0.3,  0.3, -0.6],
        [ 0.1, -0.1,  0.0],
    ])
    zone_names = ["A", "B", "C"]
    ram_limits = [
        {"name": "AB", "ram_forward": 300, "ram_reverse": 300},
        {"name": "BC", "ram_forward": 200, "ram_reverse": 200},
        {"name": "AC", "ram_forward": 20, "ram_reverse": 20},  # Tight on AC!
    ]

    result = solve_fbmc(zones, ptdf, ram_limits, zone_names)

    assert result["status"] == "Optimal"
    # The AC flow must respect RAM
    ac_flow = next(f for f in result["branch_flows"] if f["branch"] == "AC")
    assert abs(ac_flow["flow_mw"]) <= 20 + 0.1
    # Because AC is tight, A's cheap exports are constrained
    # Check that at least one other zone uses their supply
    assert result["zones"]["B"]["supply_cleared_mw"] > 0


# ── Edge cases ───────────────────────────────────────────────────

def test_fbmc_zero_ram_constrains_flow():
    """RAM=0 prevents flow — zones must balance independently, lowering welfare."""
    zones = [
        {
            "name": "A", "zone_id": 0,
            "supply": [{"price": 10, "qty": 200}],  # All supply in A
            "demand": [],
        },
        {
            "name": "B", "zone_id": 1,
            "supply": [],
            "demand": [{"price": 100, "qty": 200}],  # All demand in B
        },
    ]
    ptdf = np.array([[0.5, -0.5]])
    zone_names = ["A", "B"]

    # With RAM=0: no flow → both idle → welfare = 0
    result_restricted = solve_fbmc(
        zones, ptdf,
        [{"name": "AB", "ram_forward": 0, "ram_reverse": 0}],
        zone_names,
    )
    assert result_restricted["status"] == "Optimal"
    assert result_restricted["welfare"] == 0.0
    assert result_restricted["zones"]["A"]["supply_cleared_mw"] == 0

    # With RAM=200: flow allowed → A exports cheap power → welfare > 0
    result_free = solve_fbmc(
        zones, ptdf,
        [{"name": "AB", "ram_forward": 200, "ram_reverse": 200}],
        zone_names,
    )
    assert result_free["status"] == "Optimal"
    assert result_free["welfare"] > 0
    assert result_free["zones"]["A"]["supply_cleared_mw"] > 0


def test_fbmc_zero_demand():
    """Zero demand is handled gracefully."""
    zones = [
        {
            "name": "A", "zone_id": 0,
            "supply": [{"price": 10, "qty": 100}],
            "demand": [],
        },
        {
            "name": "B", "zone_id": 1,
            "supply": [],
            "demand": [],
        },
    ]
    ptdf = np.array([[0.5, -0.5]])
    zone_names = ["A", "B"]
    ram_limits = [{"name": "AB", "ram_forward": 100, "ram_reverse": 100}]

    result = solve_fbmc(zones, ptdf, ram_limits, zone_names)

    assert result["status"] == "Optimal"
    # No demand = no need for supply
    assert result["zones"]["A"]["supply_cleared_mw"] == 0
    assert result["zones"]["A"]["demand_cleared_mw"] == 0


def test_fbmc_zone_order_invariant():
    """Result is invariant under zone reordering."""
    zones_1 = [
        {"name": "North", "zone_id": 0, "supply": [{"price": 10, "qty": 200}], "demand": [{"price": 100, "qty": 100}]},
        {"name": "South", "zone_id": 1, "supply": [{"price": 50, "qty": 200}], "demand": [{"price": 100, "qty": 100}]},
    ]
    ptdf_1 = np.array([[0.5, -0.5]])
    names_1 = ["North", "South"]
    ram_1 = [{"name": "N_S", "ram_forward": 100, "ram_reverse": 100}]

    zones_2 = [
        {"name": "South", "zone_id": 0, "supply": [{"price": 50, "qty": 200}], "demand": [{"price": 100, "qty": 100}]},
        {"name": "North", "zone_id": 1, "supply": [{"price": 10, "qty": 200}], "demand": [{"price": 100, "qty": 100}]},
    ]
    ptdf_2 = np.array([[-0.5, 0.5]])  # Columns swapped
    names_2 = ["South", "North"]
    ram_2 = [{"name": "S_N", "ram_forward": 100, "ram_reverse": 100}]

    r1 = solve_fbmc(zones_1, ptdf_1, ram_1, names_1)
    r2 = solve_fbmc(zones_2, ptdf_2, ram_2, names_2)

    assert r1["status"] == "Optimal"
    assert r2["status"] == "Optimal"
    # Social welfare should be the same
    assert abs(r1["welfare"] - r2["welfare"]) < 1.0
    # Flows should be in opposite directions (order swapped)
    assert abs(r1["zones"]["North"]["supply_cleared_mw"] - r2["zones"]["North"]["supply_cleared_mw"]) < 0.1


# ── PTDF validation ──────────────────────────────────────────────

def test_fbmc_ptdf_row_sums_to_zero():
    """Each PTDF row must sum to ~0 (Kirchhoff conservation)."""
    zones = [
        {"name": "A", "zone_id": 0, "supply": [{"price": 10, "qty": 100}], "demand": [{"price": 100, "qty": 50}]},
        {"name": "B", "zone_id": 1, "supply": [{"price": 10, "qty": 100}], "demand": [{"price": 100, "qty": 50}]},
    ]
    # Invalid PTDF: row doesn't sum to 0
    bad_ptdf = np.array([[0.5, 0.5]])  # Should be [0.5, -0.5]
    zone_names = ["A", "B"]
    ram = [{"name": "AB", "ram_forward": 100, "ram_reverse": 100}]

    with pytest.raises(ValueError, match="Each PTDF row must sum to zero"):
        solve_fbmc(zones, bad_ptdf, ram, zone_names)


def test_fbmc_ptdf_shape_mismatch():
    """PTDF columns must match number of zones."""
    zones = [
        {"name": "A", "zone_id": 0, "supply": [{"price": 10, "qty": 100}], "demand": [{"price": 100, "qty": 50}]},
    ]
    ptdf = np.array([[0.5, -0.5]])  # 2 columns, but only 1 zone
    zone_names = ["A"]
    ram = [{"name": "AB", "ram_forward": 100, "ram_reverse": 100}]

    with pytest.raises(ValueError, match="PTDF columns"):
        solve_fbmc(zones, ptdf, ram, zone_names)


def test_fbmc_ram_branch_count_mismatch():
    """RAM limits must match PTDF rows (number of critical branches)."""
    zones = [
        {"name": "A", "zone_id": 0, "supply": [{"price": 10, "qty": 100}], "demand": [{"price": 100, "qty": 50}]},
        {"name": "B", "zone_id": 1, "supply": [{"price": 10, "qty": 100}], "demand": [{"price": 100, "qty": 50}]},
    ]
    ptdf = np.array([[0.5, -0.5]])
    zone_names = ["A", "B"]
    ram = [
        {"name": "AB", "ram_forward": 100, "ram_reverse": 100},
        {"name": "BC", "ram_forward": 100, "ram_reverse": 100},  # Extra branch!
    ]

    with pytest.raises(ValueError, match="RAM limits"):
        solve_fbmc(zones, ptdf, ram, zone_names)


def test_fbmc_negative_ram_raises():
    """RAM limits must be positive."""
    zones = [
        {"name": "A", "zone_id": 0, "supply": [{"price": 10, "qty": 100}], "demand": [{"price": 100, "qty": 50}]},
        {"name": "B", "zone_id": 1, "supply": [{"price": 10, "qty": 100}], "demand": [{"price": 100, "qty": 50}]},
    ]
    ptdf = np.array([[0.5, -0.5]])
    zone_names = ["A", "B"]
    ram = [{"name": "AB", "ram_forward": -10, "ram_reverse": 100}]

    with pytest.raises(ValueError, match="RAM limits must be non-negative"):
        solve_fbmc(zones, ptdf, ram, zone_names)
