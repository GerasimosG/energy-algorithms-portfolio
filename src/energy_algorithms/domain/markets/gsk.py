"""GSK (Generation Shift Key) strategies for zonal-to-nodal mapping.

In European electricity market coupling (Euphemia), the GSK matrix maps
zonal net positions to nodal generation injections. Different GSK
strategies reflect different assumptions about which generators respond
to zonal imbalances.

Strategies
----------
- **flat_gsk**: Uniform distribution — every node in a zone gets an
  equal share of the zone's net position change.
- **gmax_gsk**: Generation capacity-weighted — nodes with higher
  installed capacity get a larger share.
- **dynamic_gsk**: Dispatch-weighted — nodes with higher actual
  generation output get a larger share, reflecting real-time conditions.

References
----------
- ENTSO-E GSK methodology: "Generation Shift Keys for Flow-Based
  Market Coupling"
- pomato framework (github.com/FRESNA/pomato)
"""

import numpy as np
from typing import Optional

__all__ = ["flat_gsk", "gmax_gsk", "dynamic_gsk", "apply_gsk", "demo_gsk"]


# ---------------------------------------------------------------------------
# flat_gsk
# ---------------------------------------------------------------------------

def flat_gsk(
    n_zones: int,
    nodes_per_zone: list[int],
) -> np.ndarray:
    """Build a flat (uniform) GSK matrix.

    Every node in a zone receives an equal share of the zone's net
    position change. This is the simplest GSK strategy and is used
    when no generation capacity or dispatch data is available.

    Parameters
    ----------
    n_zones : int
        Number of market zones.

    nodes_per_zone : list of int
        Number of nodes in each zone. Length must equal ``n_zones``.
        Each entry must be non-negative.

    Returns
    -------
    gsk : np.ndarray, shape (n_nodes, n_zones)
        GSK matrix where column ``z`` sums to 1.0 and each node
        belongs to exactly one zone.

    Raises
    ------
    ValueError
        If ``nodes_per_zone`` length doesn't match ``n_zones``, or if
        any entry is negative.

    Examples
    --------
    >>> gsk = flat_gsk(n_zones=2, nodes_per_zone=[3, 2])
    >>> gsk.shape
    (5, 2)
    >>> gsk.sum(axis=0)  # each zone sums to 1
    array([1., 1.])
    """
    if n_zones <= 0:
        raise ValueError(f"n_zones must be positive, got {n_zones}")
    if len(nodes_per_zone) != n_zones:
        raise ValueError(
            f"nodes_per_zone length ({len(nodes_per_zone)}) "
            f"must match n_zones ({n_zones})"
        )
    if any(n < 0 for n in nodes_per_zone):
        raise ValueError("All entries in nodes_per_zone must be non-negative")

    total_nodes = sum(nodes_per_zone)
    gsk = np.zeros((total_nodes, n_zones))

    node_idx = 0
    for z in range(n_zones):
        n_nodes = nodes_per_zone[z]
        if n_nodes > 0:
            gsk[node_idx : node_idx + n_nodes, z] = 1.0 / n_nodes
        node_idx += n_nodes

    return gsk


# ---------------------------------------------------------------------------
# gmax_gsk
# ---------------------------------------------------------------------------

def gmax_gsk(
    capacity_vector: np.ndarray,
    zone_map: list[int],
    n_zones: Optional[int] = None,
) -> np.ndarray:
    """Build a Gmax (capacity-weighted) GSK matrix.

    Each node's share within its zone is proportional to its installed
    generation capacity. Nodes with higher capacity receive a larger
    portion of the zone's net position change.

    Parameters
    ----------
    capacity_vector : np.ndarray, shape (n_nodes,)
        Installed generation capacity in MW for each node. All values
        must be non-negative.

    zone_map : list of int
        Zone assignment for each node. ``zone_map[i]`` is the zone
        index (0-based) for node ``i``. Must have same length as
        ``capacity_vector``.

    n_zones : int, optional
        Total number of zones. If not provided, inferred from
        ``max(zone_map) + 1``. Use this to include empty zones.

    Returns
    -------
    gsk : np.ndarray, shape (n_nodes, n_zones)
        GSK matrix where column ``z`` sums to 1.0. Empty zones have
        all-zero columns.

    Raises
    ------
    ValueError
        If array sizes mismatch, capacities are negative, or zone
        indices are invalid.

    Examples
    --------
    >>> cap = np.array([100.0, 300.0, 50.0])
    >>> zm = [0, 0, 1]
    >>> gsk = gmax_gsk(capacity_vector=cap, zone_map=zm)
    >>> gsk[:, 0]  # zone 0 shares: 0.25, 0.75
    array([0.25, 0.75, 0.  ])
    """
    n_nodes = len(capacity_vector)

    if len(zone_map) != n_nodes:
        raise ValueError(
            f"zone_map length ({len(zone_map)}) must match "
            f"capacity_vector length ({n_nodes})"
        )
    if np.any(capacity_vector < 0):
        raise ValueError("All capacities must be non-negative")

    if n_zones is None:
        n_zones = max(zone_map) + 1 if zone_map else 0

    if n_zones <= 0 and n_nodes > 0:
        raise ValueError("n_zones must be positive when nodes are present")

    gsk = np.zeros((n_nodes, n_zones))

    for z in range(n_zones):
        # Find nodes in this zone
        mask = np.array([zm == z for zm in zone_map])
        z_caps = capacity_vector[mask]
        total_cap = z_caps.sum()

        if total_cap > 0:
            gsk[mask, z] = z_caps / total_cap
        # If total_cap == 0, column stays zero (empty zone)

    return gsk


# ---------------------------------------------------------------------------
# dynamic_gsk
# ---------------------------------------------------------------------------

def dynamic_gsk(
    capacity_vector: np.ndarray,
    dispatch_vector: np.ndarray,
    zone_map: list[int],
    n_zones: Optional[int] = None,
) -> np.ndarray:
    """Build a dynamic (dispatch-weighted) GSK matrix.

    Each node's share is proportional to its *actual* dispatch (generation
    output), not its capacity. When a zone has zero total dispatch, the
    strategy falls back to capacity-weighted distribution.

    This reflects real-time conditions and is the most accurate GSK
    strategy for operational planning.

    Parameters
    ----------
    capacity_vector : np.ndarray, shape (n_nodes,)
        Installed generation capacity in MW. Used as fallback when
        dispatch is zero for a zone.

    dispatch_vector : np.ndarray, shape (n_nodes,)
        Actual generation output (dispatch) in MW. Must have same
        length as ``capacity_vector``. All values non-negative.

    zone_map : list of int
        Zone assignment for each node. Same semantics as
        :func:`gmax_gsk`.

    n_zones : int, optional
        Total number of zones.

    Returns
    -------
    gsk : np.ndarray, shape (n_nodes, n_zones)
        GSK matrix where column ``z`` sums to 1.0.

    Raises
    ------
    ValueError
        If array sizes mismatch or values are negative.

    Examples
    --------
    >>> cap = np.array([500.0, 500.0])
    >>> disp = np.array([800.0, 200.0])  # big generation difference
    >>> zm = [0, 0]
    >>> gsk = dynamic_gsk(capacity_vector=cap, dispatch_vector=disp, zone_map=zm)
    >>> gsk[:, 0]  # 0.8 vs 0.2 (weighted by dispatch)
    array([0.8, 0.2])
    """
    n_nodes = len(capacity_vector)

    if len(dispatch_vector) != n_nodes:
        raise ValueError(
            f"dispatch_vector ({len(dispatch_vector)}) and "
            f"capacity_vector ({n_nodes}) must have same length"
        )
    if len(zone_map) != n_nodes:
        raise ValueError(
            f"zone_map length ({len(zone_map)}) must match "
            f"number of nodes ({n_nodes})"
        )
    if np.any(capacity_vector < 0):
        raise ValueError("All capacities must be non-negative")
    if np.any(dispatch_vector < 0):
        raise ValueError("All dispatch values must be non-negative")

    if n_zones is None:
        n_zones = max(zone_map) + 1 if zone_map else 0

    if n_zones <= 0 and n_nodes > 0:
        raise ValueError("n_zones must be positive when nodes are present")

    gsk = np.zeros((n_nodes, n_zones))

    for z in range(n_zones):
        mask = np.array([zm == z for zm in zone_map])
        z_dispatch = dispatch_vector[mask]
        total_dispatch = z_dispatch.sum()

        if total_dispatch > 0:
            gsk[mask, z] = z_dispatch / total_dispatch
        else:
            # Fallback: capacity-weighted
            z_caps = capacity_vector[mask]
            total_cap = z_caps.sum()
            if total_cap > 0:
                gsk[mask, z] = z_caps / total_cap
            # else: column stays zero

    return gsk


# ---------------------------------------------------------------------------
# apply_gsk
# ---------------------------------------------------------------------------

def apply_gsk(
    net_positions: np.ndarray,
    gsk_matrix: np.ndarray,
) -> np.ndarray:
    """Apply a GSK matrix to zonal net positions to obtain nodal injections.

    This is the fundamental operation: ``nodal = GSK @ net_positions``.
    Each node's injection is the sum over zones of its GSK share times
    that zone's net position.

    Parameters
    ----------
    net_positions : np.ndarray, shape (n_zones,)
        Net position for each zone in MW (positive = net export,
        negative = net import).

    gsk_matrix : np.ndarray, shape (n_nodes, n_zones)
        GSK matrix from :func:`flat_gsk`, :func:`gmax_gsk`, or
        :func:`dynamic_gsk`.

    Returns
    -------
    nodal_injections : np.ndarray, shape (n_nodes,)
        Nodal generation injections in MW. Conservation is preserved:
        ``sum(nodal) == sum(net_positions)``.

    Raises
    ------
    ValueError
        If dimensions mismatch or ``gsk_matrix`` is not 2D.

    Examples
    --------
    >>> gsk = np.array([[0.5, 0.0], [0.5, 0.0], [0.0, 1.0]])
    >>> net = np.array([100.0, -50.0])
    >>> apply_gsk(net, gsk)
    array([ 50.,  50., -50.])
    """
    if gsk_matrix.ndim != 2:
        raise ValueError(
            f"gsk_matrix must be 2-dimensional, got {gsk_matrix.ndim}D"
        )
    n_nodes, n_zones_from_gsk = gsk_matrix.shape
    if len(net_positions) != n_zones_from_gsk:
        raise ValueError(
            f"net_positions length ({len(net_positions)}) must match "
            f"gsk_matrix columns ({n_zones_from_gsk})"
        )

    return gsk_matrix @ net_positions


# ---------------------------------------------------------------------------
# demo_gsk — 3-zone demo showing all three strategies
# ---------------------------------------------------------------------------

def demo_gsk() -> dict:
    """Demonstrate GSK strategies on a 3-zone, 5-node system.

    Creates a small example with:
    - Zone North: 2 nodes (300 MW, 100 MW capacity)
    - Zone Central: 2 nodes (400 MW, 200 MW capacity)
    - Zone South: 1 node (500 MW capacity)

    Compares flat, gmax, and dynamic GSK strategies given a
    hypothetical set of zonal net positions.

    Returns
    -------
    result : dict
        Dictionary with keys:
        - ``net_positions`` (np.ndarray): zonal net positions in MW
        - ``flat`` (np.ndarray): nodal injections under flat GSK
        - ``gmax`` (np.ndarray): nodal injections under gmax GSK
        - ``dynamic`` (np.ndarray): nodal injections under dynamic GSK
        - ``capacities`` (np.ndarray): node capacities in MW
        - ``dispatch`` (np.ndarray): node dispatch in MW
    """
    # 5 nodes across 3 zones
    capacities = np.array([300.0, 100.0, 400.0, 200.0, 500.0])
    dispatch = np.array([250.0, 50.0, 350.0, 180.0, 400.0])
    zone_map = [0, 0, 1, 1, 2]
    nodes_per_zone = [2, 2, 1]
    n_zones = 3

    # Hypothetical net positions: North exports, Central and South import
    net_positions = np.array([120.0, -70.0, -50.0])

    # Build GSK matrices
    gsk_flat = flat_gsk(n_zones=n_zones, nodes_per_zone=nodes_per_zone)
    gsk_cap = gmax_gsk(capacity_vector=capacities, zone_map=zone_map)
    gsk_dyn = dynamic_gsk(
        capacity_vector=capacities,
        dispatch_vector=dispatch,
        zone_map=zone_map,
    )

    # Apply to net positions
    nodal_flat = apply_gsk(net_positions, gsk_flat)
    nodal_cap = apply_gsk(net_positions, gsk_cap)
    nodal_dyn = apply_gsk(net_positions, gsk_dyn)

    return {
        "net_positions": net_positions,
        "flat": nodal_flat,
        "gmax": nodal_cap,
        "dynamic": nodal_dyn,
        "capacities": capacities,
        "dispatch": dispatch,
    }
