"""Tests for GSK (Generation Shift Key) strategies — energy_markets/gsk.py."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest

from energy_algorithms.domain.markets.gsk import (flat_gsk, gmax_gsk, dynamic_gsk,
                                apply_gsk, demo_gsk)


# ── flat_gsk tests ───────────────────────────────────────────────

def test_flat_gsk_shape():
    """Flat GSK matrix should have shape (n_nodes, n_zones)."""
    gsk = flat_gsk(n_zones=3, nodes_per_zone=[4, 3, 5])
    assert gsk.shape == (12, 3)  # 4+3+5 = 12 nodes, 3 zones


def test_flat_gsk_rows_sum_to_one():
    """Each row (per node) sums to weights for zones; each zone column sums to 1."""
    gsk = flat_gsk(n_zones=2, nodes_per_zone=[3, 2])
    # Column sums should each be 1.0 (total injection split across nodes)
    assert np.allclose(gsk.sum(axis=0), [1.0, 1.0])

    # Each node's row sum should be 0 if it's only in one zone
    # Actually, in a flat GSK, each node belongs to only one zone
    # So rows have one non-zero entry
    for i in range(5):
        nonzero = np.count_nonzero(gsk[i])
        assert nonzero == 1, f"Node {i}: expected 1 non-zero, got {nonzero}"


def test_flat_gsk_uniform_distribution():
    """Each node in a zone gets equal share: 1/n_nodes_in_zone."""
    n_nodes = [3, 5]
    gsk = flat_gsk(n_zones=2, nodes_per_zone=n_nodes)

    # Zone 0: nodes 0-2, each gets 1/3
    assert np.allclose(gsk[0:3, 0], 1.0/3)
    # Zone 1: nodes 3-7, each gets 1/5
    assert np.allclose(gsk[3:8, 1], 1.0/5)

    # Cross-zone: all zeros
    assert np.allclose(gsk[0:3, 1], 0.0)
    assert np.allclose(gsk[3:8, 0], 0.0)


def test_flat_gsk_single_zone():
    """Single zone: all nodes get equal share, all in same column."""
    gsk = flat_gsk(n_zones=1, nodes_per_zone=[4])
    assert gsk.shape == (4, 1)
    assert np.allclose(gsk[:, 0], 0.25)


def test_flat_gsk_empty_zone():
    """Empty zone should still work (but may be degenerate)."""
    gsk = flat_gsk(n_zones=3, nodes_per_zone=[2, 0, 3])
    assert gsk.shape == (5, 3)

    # Zone 1 has 0 nodes — column should be all zeros
    assert np.allclose(gsk[:, 1], 0.0)
    # Other columns should sum to 1
    assert np.allclose(gsk[0:2, 0].sum(), 1.0)
    assert np.allclose(gsk[2:5, 2].sum(), 1.0)


def test_flat_gsk_validation_n_nodes():
    """n_nodes must be positive integers."""
    with pytest.raises(ValueError):
        flat_gsk(n_zones=2, nodes_per_zone=[3])  # mismatch


def test_flat_gsk_zero_zones_raises():
    """Zero zones should raise ValueError."""
    with pytest.raises(ValueError):
        flat_gsk(n_zones=0, nodes_per_zone=[])


# ── gmax_gsk tests ───────────────────────────────────────────────

def test_gmax_gsk_shape():
    """Gmax GSK: shape (n_nodes, n_zones)."""
    capacity = np.array([100.0, 200.0, 50.0, 150.0])  # 4 nodes
    zone_map = [0, 0, 1, 1]  # nodes 0,1 in zone 0; nodes 2,3 in zone 1
    gsk = gmax_gsk(capacity_vector=capacity, zone_map=zone_map)
    assert gsk.shape == (4, 2)


def test_gmax_gsk_proportional():
    """Each node's share is proportional to its capacity within its zone."""
    capacity = np.array([300.0, 700.0, 100.0, 400.0])  # zone 0: 1000, zone 1: 500
    zone_map = [0, 0, 1, 1]
    gsk = gmax_gsk(capacity_vector=capacity, zone_map=zone_map)

    # Zone 0: node 0 gets 300/1000 = 0.3, node 1 gets 700/1000 = 0.7
    assert abs(gsk[0, 0] - 0.3) < 1e-10
    assert abs(gsk[1, 0] - 0.7) < 1e-10

    # Zone 1: node 2 gets 100/500 = 0.2, node 3 gets 400/500 = 0.8
    assert abs(gsk[2, 1] - 0.2) < 1e-10
    assert abs(gsk[3, 1] - 0.8) < 1e-10

    # Cross-zone: all zeros
    assert gsk[0, 1] == 0.0
    assert gsk[1, 1] == 0.0
    assert gsk[2, 0] == 0.0
    assert gsk[3, 0] == 0.0


def test_gmax_gsk_column_sums():
    """Each zone column should sum to 1.0."""
    capacity = np.array([100.0, 200.0, 300.0, 400.0, 500.0])
    zone_map = [0, 0, 1, 1, 2]
    gsk = gmax_gsk(capacity_vector=capacity, zone_map=zone_map)

    col_sums = gsk.sum(axis=0)
    # Zone 0: 2 nodes, sum = 1
    # Zone 1: 2 nodes, sum = 1
    # Zone 2: 1 node, sum = 1
    assert np.allclose(col_sums[:3], 1.0)


def test_gmax_gsk_single_node_per_zone():
    """Single node in a zone gets 100% share."""
    capacity = np.array([100.0, 200.0])
    zone_map = [0, 1]
    gsk = gmax_gsk(capacity_vector=capacity, zone_map=zone_map)
    assert gsk[0, 0] == 1.0
    assert gsk[1, 1] == 1.0


def test_gmax_gsk_all_equal_capacity():
    """Equal capacities: shares are equal (behaves like flat_gsk)."""
    capacity = np.array([100.0, 100.0, 100.0])
    zone_map = [0, 0, 0]
    gsk = gmax_gsk(capacity_vector=capacity, zone_map=zone_map)

    assert np.allclose(gsk[:, 0], 1.0/3)


def test_gmax_gsk_empty_zone():
    """Zone with no nodes should have zero column."""
    capacity = np.array([100.0, 200.0])
    zone_map = [0, 0]  # zone 1 is empty
    gsk = gmax_gsk(capacity_vector=capacity, zone_map=zone_map, n_zones=3)

    assert gsk.shape == (2, 3)
    assert np.allclose(gsk[:, 2], 0.0)  # zone 2 is empty


def test_gmax_gsk_validation():
    """Capacity and zone_map must match in length."""
    capacity = np.array([100.0, 200.0])
    zone_map = [0]  # too short
    with pytest.raises(ValueError):
        gmax_gsk(capacity_vector=capacity, zone_map=zone_map)


def test_gmax_gsk_negative_capacity():
    """Negative capacity raises ValueError."""
    capacity = np.array([100.0, -50.0])
    zone_map = [0, 1]
    with pytest.raises(ValueError, match="non-negative"):
        gmax_gsk(capacity_vector=capacity, zone_map=zone_map)


# ── dynamic_gsk tests ────────────────────────────────────────────

def test_dynamic_gsk_shape():
    """Dynamic GSK based on actual dispatch."""
    capacity = np.array([100.0, 200.0, 50.0])
    dispatch = np.array([60.0, 150.0, 20.0])
    zone_map = [0, 0, 1]
    gsk = dynamic_gsk(capacity_vector=capacity, dispatch_vector=dispatch,
                      zone_map=zone_map)
    assert gsk.shape == (3, 2)


def test_dynamic_gsk_weighted_by_dispatch():
    """Dynamic GSK weights by actual dispatch, not capacity."""
    capacity = np.array([500.0, 500.0])  # equal capacity
    dispatch = np.array([800.0, 200.0])  # big dispatch difference
    zone_map = [0, 0]
    gsk = dynamic_gsk(capacity_vector=capacity, dispatch_vector=dispatch,
                      zone_map=zone_map)

    # Node 0: 800/1000 = 0.8, Node 1: 200/1000 = 0.2
    assert abs(gsk[0, 0] - 0.8) < 1e-10
    assert abs(gsk[1, 0] - 0.2) < 1e-10


def test_dynamic_gsk_zero_dispatch_zone():
    """Zone with zero total dispatch: fall back to capacity-based."""
    capacity = np.array([100.0, 200.0, 50.0])
    dispatch = np.array([0.0, 0.0, 50.0])  # zone 0 has zero dispatch
    zone_map = [0, 0, 1]
    gsk = dynamic_gsk(capacity_vector=capacity, dispatch_vector=dispatch,
                      zone_map=zone_map)

    # Zone 0: no dispatch, fall back to capacity
    assert abs(gsk[0, 0] - 1.0/3) < 1e-10
    assert abs(gsk[1, 0] - 2.0/3) < 1e-10
    # Zone 1: 1 node, gets 100%
    assert gsk[2, 1] == 1.0


def test_dynamic_gsk_column_sums():
    """Each zone column sums to 1.0."""
    capacity = np.array([300.0, 200.0, 100.0])
    dispatch = np.array([250.0, 50.0, 80.0])
    zone_map = [0, 0, 1]
    gsk = dynamic_gsk(capacity_vector=capacity, dispatch_vector=dispatch,
                      zone_map=zone_map)

    assert np.allclose(gsk[:, 0].sum(), 1.0)
    assert np.allclose(gsk[:, 1].sum(), 1.0)


def test_dynamic_gsk_validation():
    """Capacity and dispatch must match in length."""
    capacity = np.array([100.0, 200.0])
    dispatch = np.array([50.0, 60.0, 70.0])  # too long
    zone_map = [0, 1]
    with pytest.raises(ValueError, match="same length"):
        dynamic_gsk(capacity_vector=capacity, dispatch_vector=dispatch,
                    zone_map=zone_map)


# ── apply_gsk tests ──────────────────────────────────────────────

def test_apply_gsk_basic():
    """Apply GSK matrix to zonal net positions -> nodal injections."""
    gsk = np.array([
        [0.5, 0.0],
        [0.5, 0.0],
        [0.0, 1.0],
    ])
    net_positions = np.array([100.0, -50.0])  # zone 0 exports 100, zone 1 imports 50

    nodal = apply_gsk(net_positions, gsk)

    expected = np.array([50.0, 50.0, -50.0])  # 100*0.5, 100*0.5, -50*1.0
    assert np.allclose(nodal, expected)


def test_apply_gsk_zero_net_positions():
    """Zero net positions -> zero nodal injections."""
    gsk = np.array([[0.5, 0.0], [0.5, 0.0], [0.0, 1.0]])
    net_positions = np.zeros(2)
    nodal = apply_gsk(net_positions, gsk)
    assert np.allclose(nodal, 0.0)


def test_apply_gsk_conservation():
    """Sum of nodal injections should equal sum of net positions."""
    np.random.seed(42)
    n_zones = 4
    n_nodes = 10
    gsk = np.random.random((n_nodes, n_zones))
    gsk /= gsk.sum(axis=0, keepdims=True)  # normalize columns

    net_positions = np.random.randn(n_zones) * 100
    net_positions -= net_positions.sum() / n_zones  # make sum zero

    nodal = apply_gsk(net_positions, gsk)

    # Sum of net positions = 0, so sum of nodal should also be ≈ 0
    assert abs(nodal.sum()) < 1e-10


def test_apply_gsk_shape_mismatch():
    """GSK columns must match net_positions length."""
    gsk = np.ones((4, 2))
    net_positions = np.array([100.0, 50.0, 25.0])  # 3 positions, 2 columns
    with pytest.raises(ValueError, match="columns"):
        apply_gsk(net_positions, gsk)


def test_apply_gsk_not_matrix():
    """GSK must be 2D."""
    gsk = np.array([0.5, 0.5])  # 1D
    net_positions = np.array([100.0, 50.0])
    with pytest.raises(ValueError, match="2-dimensional"):
        apply_gsk(net_positions, gsk)


def test_apply_gsk_2zone_flat():
    """End-to-end: flat GSK with 2 zones."""
    gsk = flat_gsk(n_zones=2, nodes_per_zone=[3, 2])
    net_positions = np.array([120.0, -120.0])  # zone 0 exports to zone 1
    nodal = apply_gsk(net_positions, gsk)

    # Each node in zone 0 gets 120/3 = 40
    assert np.allclose(nodal[0:3], 40.0)
    # Each node in zone 1 gets -120/2 = -60
    assert np.allclose(nodal[3:5], -60.0)
    # Conservation
    assert abs(nodal.sum()) < 1e-10


def test_apply_gsk_3zone_all_strategies():
    """3-zone demo: all three GSK strategies produce valid nodal injections."""
    capacity = np.array([300.0, 100.0, 400.0, 200.0, 500.0])
    dispatch = np.array([250.0, 50.0, 350.0, 180.0, 400.0])
    zone_map = [0, 0, 1, 1, 2]
    nodes_per_zone = [2, 2, 1]
    n_zones = 3

    net_positions = np.array([100.0, -50.0, -50.0])

    # Flat
    gsk_flat = flat_gsk(n_zones=n_zones, nodes_per_zone=nodes_per_zone)
    nodal_flat = apply_gsk(net_positions, gsk_flat)
    assert len(nodal_flat) == 5
    assert abs(nodal_flat.sum()) < 1e-10

    # Gmax
    gsk_gmax = gmax_gsk(capacity_vector=capacity, zone_map=zone_map)
    nodal_gmax = apply_gsk(net_positions, gsk_gmax)
    assert len(nodal_gmax) == 5
    assert abs(nodal_gmax.sum()) < 1e-10

    # Dynamic
    gsk_dyn = dynamic_gsk(capacity_vector=capacity,
                          dispatch_vector=dispatch,
                          zone_map=zone_map)
    nodal_dyn = apply_gsk(net_positions, gsk_dyn)
    assert len(nodal_dyn) == 5
    assert abs(nodal_dyn.sum()) < 1e-10


# ── demo_gsk tests ───────────────────────────────────────────────

def test_demo_gsk_runs():
    """Demo function should run without errors and return a dict."""
    result = demo_gsk()
    assert isinstance(result, dict)
    assert "flat" in result
    assert "gmax" in result
    assert "dynamic" in result
    assert "net_positions" in result

    # All three nodal injections should be numpy arrays of same length
    n_nodes = len(result["flat"])
    assert n_nodes > 0
    assert len(result["gmax"]) == n_nodes
    assert len(result["dynamic"]) == n_nodes
