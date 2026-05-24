"""Multi-Zone Market Coupling Example.

Extends the single-zone PCR model to demonstrate multi-zone coupling
with Available Transfer Capacity (ATC) constraints between zones.

This is directly relevant to Euphemia: the algorithm couples 25+ European
power exchanges, where inter-zonal flows are limited by ATC values.
"""
from __future__ import annotations

import pulp

from energy_algorithms.domain.markets.coupling_utils import (
    compute_social_welfare,
    extract_flow_results,
    extract_zone_results,
    validate_atc,
)


def solve_multi_zone(
    zones: list[dict],
    atc: dict[tuple[str, str], float],
    verbose: bool = False,
) -> dict:
    """
    Solve multi-zone market coupling LP.

    Each zone has its own supply/demand curves. The LP maximizes total
    social welfare across all zones, subject to:
      - Per-zone energy balance (including imports/exports)
      - ATC limits on inter-zonal flows

    Parameters
    ----------
    zones : list of dicts, each with keys:
        'name' (str), 'supply' (list of {price, qty}),
        'demand' (list of {price, qty})
    atc : dict {(zone_a, zone_b): capacity_mw}
        Bidirectional ATC limits. Only one direction needed per pair.

    Returns
    -------
    dict with status, welfare, flows, zone_results
    """
    Z = len(zones)
    zone_names = [z["name"] for z in zones]

    prob = pulp.LpProblem("MultiZone_Coupling", pulp.LpMaximize)

    # ---- Decision variables ----
    # Per-zone supply/demand acceptance fractions
    s_vars = {}  # s_vars[zi][si] = fraction
    d_vars = {}  # d_vars[zi][di] = fraction
    # Inter-zonal flows (from i to j)
    flows = {}   # flows[(i,j)] = MW

    for zi in range(Z):
        Ns = len(zones[zi]["supply"])
        Nd = len(zones[zi]["demand"])
        s_vars[zi] = {si: pulp.LpVariable(f"s_z{zi}_{si}", 0, 1) for si in range(Ns)}
        d_vars[zi] = {di: pulp.LpVariable(f"d_z{zi}_{di}", 0, 1) for di in range(Nd)}

    # Flow variables (one signed variable per bidirectional ATC corridor).
    # Positive value follows the tuple direction; negative value is reverse flow.
    flows = {}
    zone_set = set(zone_names)
    atc_pairs = validate_atc(atc, zone_set)
    for a, b, cap in atc_pairs.values():
        flows[(a, b)] = pulp.LpVariable(f"flow_{a}_to_{b}", lowBound=-cap, upBound=cap)

    # ---- Objective: sum of social welfare across all zones ----
    welfare = 0
    for zi in range(Z):
        welfare += compute_social_welfare(zones[zi], s_vars[zi], d_vars[zi])
    prob += welfare

    # ---- Energy balance per zone (including net exports) ----
    for zi in range(Z):
        z = zones[zi]
        supply_qty = pulp.lpSum(
            z["supply"][si]["qty"] * s_vars[zi][si]
            for si in range(len(z["supply"]))
        )
        demand_qty = pulp.lpSum(
            z["demand"][di]["qty"] * d_vars[zi][di]
            for di in range(len(z["demand"]))
        )
        # Net exports are positive when power leaves the zone. A signed flow
        # variable contributes positively to its tuple source and negatively
        # to its tuple sink.
        net_exports = pulp.lpSum(
            var if a == zone_names[zi] else -var
            for (a, b), var in flows.items()
            if zone_names[zi] in (a, b)
        )
        prob += supply_qty == demand_qty + net_exports, f"balance_{zone_names[zi]}"

    # ---- Solve ----
    prob.solve(pulp.PULP_CBC_CMD(msg=verbose))
    status = pulp.LpStatus[prob.status]

    if status != "Optimal":
        return {"status": status}

    # ---- Extract results ----
    flow_results = extract_flow_results(flows, zone_names)

    zone_results = {}
    for zi in range(Z):
        z = zones[zi]
        zname = zone_names[zi]
        zone_results.update(extract_zone_results(z, s_vars[zi], d_vars[zi], zname))

    return {
        "status": status,
        "welfare": round(float(pulp.value(welfare)), 2),
        "flows": flow_results,
        "zones": zone_results,
    }


def demo_multi_zone() -> dict:
    """
    Run a 3-zone coupling example: cheap North, high-demand Center, expensive South.

    North has excess cheap wind → exports to Center.
    South has expensive gas → Center imports from North when cheaper.
    """
    zones = [
        {
            "name": "North",
            "supply": [
                {"price": 5, "qty": 300},   # Wind
                {"price": 30, "qty": 200},  # Hydro
            ],
            "demand": [
                {"price": 100, "qty": 200},
            ],
        },
        {
            "name": "Center",
            "supply": [
                {"price": 40, "qty": 150},  # Gas
                {"price": 70, "qty": 200},  # Coal
            ],
            "demand": [
                {"price": 150, "qty": 400},
            ],
        },
        {
            "name": "South",
            "supply": [
                {"price": 60, "qty": 100},  # Gas
                {"price": 90, "qty": 200},  # Diesel
            ],
            "demand": [
                {"price": 120, "qty": 250},
            ],
        },
    ]

    # ATC limits: North→Center 200MW, Center→South 100MW
    atc = {
        ("North", "Center"): 200,
        ("Center", "South"): 100,
    }

    return solve_multi_zone(zones, atc)
