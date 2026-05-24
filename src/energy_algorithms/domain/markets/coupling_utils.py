"""Shared utilities for market coupling models.

Extracted from pcr_model.py, fbmc.py, multi_zone.py, multi_day.py.
Provides welfare computation, zone/flow result extraction, and ATC validation.
"""

from __future__ import annotations

import pulp


def compute_social_welfare(
    zone: dict,
    s_vars: dict[int, pulp.LpVariable],
    d_vars: dict[int, pulp.LpVariable],
) -> pulp.LpAffineExpression:
    """Compute social welfare expression for a single zone.

    Formula: Σ(demand_price × demand_qty × demand_frac)
           - Σ(supply_price × supply_qty × supply_frac)

    Parameters
    ----------
    zone : dict
        With keys ``'supply'`` (list of ``{price, qty}`` or ``{price, quantity}``)
        and ``'demand'`` (same structure).
    s_vars : dict[int, LpVariable]
        Supply acceptance fractions indexed by order position.
    d_vars : dict[int, LpVariable]
        Demand acceptance fractions indexed by order position.

    Returns
    -------
    pulp.LpAffineExpression
    """
    supply = zone["supply"]
    demand = zone["demand"]

    # Zone-based models use 'qty'; order-based (PCR) uses 'quantity'.
    s_qty_key = "qty" if supply and "qty" in supply[0] else "quantity"
    d_qty_key = "qty" if demand and "qty" in demand[0] else "quantity"

    return (
        pulp.lpSum(
            demand[di]["price"] * demand[di][d_qty_key] * d_vars[di]
            for di in range(len(demand))
        )
        - pulp.lpSum(
            supply[si]["price"] * supply[si][s_qty_key] * s_vars[si]
            for si in range(len(supply))
        )
    )


def extract_zone_results(
    zone: dict,
    s_vars: dict[int, pulp.LpVariable],
    d_vars: dict[int, pulp.LpVariable],
    zname: str,
) -> dict:
    """Extract cleared quantities and MCP for a single zone.

    Parameters
    ----------
    zone : dict
        With keys ``'supply'`` (list of ``{price, qty}``) and
        ``'demand'`` (list of ``{price, qty}``).
    s_vars : dict[int, LpVariable]
        Supply acceptance fractions.
    d_vars : dict[int, LpVariable]
        Demand acceptance fractions.
    zname : str
        Zone name (used as key in the returned dict).

    Returns
    -------
    dict
        ``{zname: {supply_cleared_mw, demand_cleared_mw, mcp}}``
    """
    supply = zone["supply"]
    demand = zone["demand"]

    supply_cleared = sum(
        supply[si]["qty"] * float(pulp.value(s_vars[si]) or 0)
        for si in range(len(supply))
    )
    demand_cleared = sum(
        demand[di]["qty"] * float(pulp.value(d_vars[di]) or 0)
        for di in range(len(demand))
    )
    marginal_prices = [
        supply[si]["price"]
        for si in range(len(supply))
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
    zone_names: list[str],
) -> dict:
    """Extract flow direction with >0.01 MW threshold detection.

    Parameters
    ----------
    flows : dict
        ``{(from, to): LpVariable}`` — keys can be int indices or str names.
    zone_names : list[str]
        Zone names used to resolve int keys to human-readable names.

    Returns
    -------
    dict
        ``{"ZoneA→ZoneB": flow_mw, ...}`` — only non-trivial flows included.
    """
    flow_results: dict[str, float] = {}
    for (a, b), var in flows.items():
        val = pulp.value(var)
        if val is None:
            continue
        name_a = zone_names[a] if isinstance(a, int) else a
        name_b = zone_names[b] if isinstance(b, int) else b
        if val > 0.01:
            flow_results[f"{name_a}→{name_b}"] = round(val, 1)
        elif val < -0.01:
            flow_results[f"{name_b}→{name_a}"] = round(abs(val), 1)
    return flow_results


def validate_atc(
    atc: dict,
    zone_set: set,
    zone_count: int = 0,
) -> dict:
    """Validate ATC pairs and deduplicate corridors.

    Checks performed:
        - Unknown zone (endpoint not in *zone_set*)
        - Self-pair (both endpoints identical)
        - Negative capacity
        - Duplicate corridor with conflicting capacity

    Parameters
    ----------
    atc : dict
        ``{(from, to): capacity_mw}`` — keys may be int indices or str names.
    zone_set : set
        Set of valid zone identifiers.
    zone_count : int
        Total number of zones (reserved for API compatibility).

    Returns
    -------
    dict
        ``{corridor: (a, b, cap)}`` — deduplicated corridors with
        canonical (sorted) keys.

    Raises
    ------
    ValueError
        If any validation check fails.
    """
    pairs: dict[tuple, tuple] = {}
    for (a, b), cap in atc.items():
        if a not in zone_set or b not in zone_set:
            raise ValueError(f"ATC pair ({a}, {b}) references an unknown zone")
        if a == b:
            raise ValueError("ATC pair endpoints must be different zones")
        if cap < 0:
            raise ValueError(f"ATC capacity must be non-negative, got {cap}")

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
