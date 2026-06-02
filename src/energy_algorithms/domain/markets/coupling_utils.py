"""Shared utilities for market coupling models.

Provides common functions for social welfare computation, zone result
extraction, flow result extraction, and ATC validation, shared by
multi-zone, multi-day, and FBMC coupling models.
"""
from __future__ import annotations

from typing import Any

import pulp


def compute_social_welfare(
    zone: dict,
    s_vars: dict[int, pulp.LpVariable],
    d_vars: dict[int, pulp.LpVariable],
) -> pulp.LpAffineExpression:
    """Compute social welfare expression for a single zone.

    Social welfare = sum(demand_price × demand_qty × fraction)
                     - sum(supply_price × supply_qty × fraction)

    Parameters
    ----------
    zone : dict
        Zone dict with ``'supply'`` and ``'demand'`` keys, each a list of
        ``{'price': float, 'qty': float}`` dicts.
    s_vars : dict
        Supply acceptance fraction variables, ``{idx: LpVariable}``.
    d_vars : dict
        Demand acceptance fraction variables, ``{idx: LpVariable}``.

    Returns
    -------
    pulp.LpAffineExpression
        The social welfare expression.
    """
    welfare = pulp.lpSum(
        zone["demand"][di]["price"]
        * zone["demand"][di]["qty"]
        * d_vars[di]
        for di in range(len(zone["demand"]))
    )
    welfare -= pulp.lpSum(
        zone["supply"][si]["price"]
        * zone["supply"][si]["qty"]
        * s_vars[si]
        for si in range(len(zone["supply"]))
    )
    return welfare


def extract_zone_results(
    zone: dict,
    s_vars: dict[int, pulp.LpVariable],
    d_vars: dict[int, pulp.LpVariable],
    zname: str,
) -> dict[str, Any]:
    """Extract per-zone market results from solved LP variables.

    Computes cleared supply/demand quantities and the zonal marginal
    clearing price (MCP = highest accepted supply price).

    Parameters
    ----------
    zone : dict
        Zone dict with ``'supply'`` and ``'demand'`` lists.
    s_vars : dict
        Supply acceptance fraction variables, ``{idx: LpVariable}``.
    d_vars : dict
        Demand acceptance fraction variables, ``{idx: LpVariable}``.
    zname : str
        Zone name for the result key.

    Returns
    -------
    dict
        ``{zname: {"supply_cleared_mw": float, "demand_cleared_mw": float,
                    "mcp": float}}``
    """
    supply_cleared = sum(
        zone["supply"][si]["qty"] * float(pulp.value(s_vars[si]) or 0)
        for si in range(len(zone["supply"]))
    )
    demand_cleared = sum(
        zone["demand"][di]["qty"] * float(pulp.value(d_vars[di]) or 0)
        for di in range(len(zone["demand"]))
    )
    marginal_prices = [
        zone["supply"][si]["price"]
        for si in range(len(zone["supply"]))
        if float(pulp.value(s_vars[si]) or 0) > 0.001
    ]
    mcp = max(marginal_prices) if marginal_prices else 0.0
    return {
        zname: {
            "supply_cleared_mw": round(supply_cleared, 1),
            "demand_cleared_mw": round(demand_cleared, 1),
            "mcp": mcp,
        }
    }


def extract_flow_results(
    flows: dict,
    zone_names: list[str] | None = None,
) -> dict[str, float]:
    """Extract directional flow results from solved LP flow variables.

    Converts signed flow variables (positive = direction of tuple key,
    negative = reverse) into a human-readable dict with arrow keys.

    Parameters
    ----------
    flows : dict
        Mapping ``(a, b) -> LpVariable`` where keys are either zone
        name strings or integer indices.
    zone_names : list of str, optional
        Ordered zone names. Required when flow keys are integer indices
        (multi-day) to resolve index to name.

    Returns
    -------
    dict
        ``{"Source→Target": flow_mw, ...}``. Only flows > 0.01 MW are
        included, with signs resolved to the positive flow direction.
    """
    flow_results: dict[str, float] = {}
    for key, var in flows.items():
        val = pulp.value(var)
        if val is None:
            continue
        a, b = key
        if isinstance(a, int) and zone_names is not None:
            a_name = zone_names[a]
            b_name = zone_names[b]
        else:
            a_name = a
            b_name = b
        if val > 0.01:
            flow_results[f"{a_name}\u2192{b_name}"] = round(val, 1)
        elif val < -0.01:
            flow_results[f"{b_name}\u2192{a_name}"] = round(abs(val), 1)
    return flow_results


def validate_atc(
    atc: dict,
    zone_set: set | None = None,
    zone_count: int | None = None,
) -> dict:
    """Validate ATC entries and return deduplicated corridor info.

    Handles both string-based zone names (multi-zone) and integer
    indices (multi-day). Performs:
        - Endpoint validity (known zone / in-range index)
        - Self-loop detection
        - Negative capacity rejection
        - Duplicate corridor conflict detection

    Parameters
    ----------
    atc : dict
        Mapping ``(a, b) -> capacity`` where keys are either zone name
        strings or integer indices.
    zone_set : set of str, optional
        Valid zone names for string-based validation.
    zone_count : int, optional
        Number of zones for index-based validation.

    Returns
    -------
    dict
        ``{corridor: (a, b, cap)}`` for validated, deduplicated ATC
        corridors. Each corridor is the sorted tuple of endpoints.

    Raises
    ------
    ValueError
        If any ATC entry references an unknown zone, forms a self-loop,
        has negative capacity, or conflicts with an existing corridor.
    """
    pairs: dict = {}
    for (a, b), cap in atc.items():
        # Validate endpoints
        if isinstance(a, int):
            if zone_count is not None and (
                a < 0 or b < 0 or a >= zone_count or b >= zone_count
            ):
                raise ValueError(
                    f"ATC pair ({a}, {b}) references an unknown zone"
                )
        else:
            if zone_set is not None and (
                a not in zone_set or b not in zone_set
            ):
                raise ValueError(
                    f"ATC pair ({a}, {b}) references an unknown zone"
                )

        if a == b:
            raise ValueError("ATC pair endpoints must be different zones")
        if cap < 0:
            raise ValueError(
                f"ATC capacity must be non-negative, got {cap}"
            )

        corridor = tuple(sorted((a, b)))
        if corridor in pairs:
            _, _, prev_cap = pairs[corridor]
            if cap != prev_cap:
                raise ValueError(
                    f"Duplicate ATC corridor {corridor} has conflicting "
                    f"capacities: {prev_cap} and {cap}"
                )
            continue

        pairs[corridor] = (a, b, cap)

    return pairs
