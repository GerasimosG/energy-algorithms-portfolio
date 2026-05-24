"""Flow-Based Market Coupling (FBMC) — Euphemia's actual coupling algorithm.

Extends the ATC-based multi_zone.py with PTDF-based flow constraints,
demonstrating how zonal net positions create loop flows on the physical network.

FBMC vs ATC:
  - ATC: each interconnection has a simple MW capacity limit
  - FBMC: uses a Power Transfer Distribution Factor (PTDF) matrix to
    model how net positions at each node affect all critical branch flows
  - FBMC captures loop flows — a trade between zones A and B can
    overload a line between B and C that ATC would miss

References:
  - ENTSO-E Flow-Based Market Coupling documentation
  - pomato framework (github.com/FRESNA/pomato)
  - Euphemia algorithm specification
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pulp

from energy_algorithms.domain.markets.coupling_utils import (
    compute_social_welfare,
    extract_zone_results,
)


def solve_fbmc(
    zones: list[dict],
    ptdf_matrix: np.ndarray,
    ram_limits: list[dict],
    zone_names: list[str],
    verbose: bool = False,
) -> dict[str, Any]:
    """Solve Flow-Based Market Coupling with PTDF flow constraints.

    Parameters
    ----------
    zones : list of dict
        Each dict with keys:
            'name' (str) — zone name
            'supply' (list) — [{price, qty}, ...] in €/MWh, MW
            'demand' (list) — [{price, qty}, ...] in €/MWh, MW
    ptdf_matrix : np.ndarray, shape (n_branches, n_zones)
        PTDF matrix where PTDF[l, n] = flow on branch l for a
        1 MW net injection at zone n (with 1 MW withdrawal at reference).
        Each row must sum to ~0 (Kirchhoff conservation).
    ram_limits : list of dict
        Each dict with keys:
            'name' (str) — branch identifier
            'ram_forward' (float) — max flow in positive direction (MW)
            'ram_reverse' (float) — max flow in negative direction (MW)
        Length must match ptdf_matrix rows.
    zone_names : list of str
        Ordered zone names — must match zones order and PTDF columns.
    verbose : bool
        If True, print CBC solver output.

    Returns
    -------
    dict with keys:
        status : str — "Optimal", "Infeasible", etc.
        welfare : float — total social welfare (€)
        zones : dict — {zone_name: {supply_cleared_mw, demand_cleared_mw,
                                     net_position_mw, mcp}}
        branch_flows : list — [{branch, flow_mw, ram_forward, ram_reverse,
                                utilization_pct}]

    Raises
    ------
    ValueError
        If PTDF shape, RAM count, row sums, or sign constraints violated.
    """
    Z = len(zones)
    n_branches = ptdf_matrix.shape[0]

    # ── Input validation ────────────────────────────────────────
    if ptdf_matrix.shape[1] != Z:
        raise ValueError(
            f"PTDF columns ({ptdf_matrix.shape[1]}) must match "
            f"number of zones ({Z})"
        )
    if len(ram_limits) != n_branches:
        raise ValueError(
            f"Number of RAM limits ({len(ram_limits)}) must match "
            f"PTDF rows ({n_branches})"
        )
    if not np.allclose(ptdf_matrix.sum(axis=1), 0, atol=1e-10):
        raise ValueError(
            "Each PTDF row must sum to zero "
            "(Kirchhoff current conservation)"
        )
    for rl in ram_limits:
        if rl["ram_forward"] < 0 or rl["ram_reverse"] < 0:
            raise ValueError(
                f"RAM limits must be non-negative (got "
                f"forward={rl['ram_forward']}, "
                f"reverse={rl['ram_reverse']})"
            )

    prob = pulp.LpProblem("FBMC_Coupling", pulp.LpMaximize)

    # ── Decision variables ──────────────────────────────────────
    # Supply/demand acceptance fractions [0, 1]
    s_vars: dict[int, dict[int, pulp.LpVariable]] = {}
    d_vars: dict[int, dict[int, pulp.LpVariable]] = {}
    for zi in range(Z):
        zname = zone_names[zi]
        Ns = len(zones[zi]["supply"])
        Nd = len(zones[zi]["demand"])
        s_vars[zi] = {
            si: pulp.LpVariable(f"s_{zname}_{si}", 0, 1)
            for si in range(Ns)
        }
        d_vars[zi] = {
            di: pulp.LpVariable(f"d_{zname}_{di}", 0, 1)
            for di in range(Nd)
        }

    # Net position per zone (MW, positive = net exporter)
    # Bounds: at most all supply exported, all demand imported
    net_position: dict[int, pulp.LpVariable] = {}
    for zi in range(Z):
        zname = zone_names[zi]
        total_supply = sum(o["qty"] for o in zones[zi]["supply"])
        total_demand = sum(o["qty"] for o in zones[zi]["demand"])
        net_position[zi] = pulp.LpVariable(
            f"net_{zname}",
            lowBound=-total_demand,
            upBound=total_supply,
        )

    # ── Objective: social welfare ───────────────────────────────
    welfare = 0
    for zi in range(Z):
        welfare += compute_social_welfare(zones[zi], s_vars[zi], d_vars[zi])
    prob += welfare

    # ── Constraints ─────────────────────────────────────────────
    # Per-zone balance: supply - demand = net_position
    for zi in range(Z):
        supply_qty = pulp.lpSum(
            zones[zi]["supply"][si]["qty"] * s_vars[zi][si]
            for si in range(len(zones[zi]["supply"]))
        )
        demand_qty = pulp.lpSum(
            zones[zi]["demand"][di]["qty"] * d_vars[zi][di]
            for di in range(len(zones[zi]["demand"]))
        )
        prob += (
            supply_qty - demand_qty == net_position[zi],
            f"balance_{zone_names[zi]}",
        )

    # System energy balance: sum of net positions = 0
    prob += (
        pulp.lpSum([net_position[zi] for zi in range(Z)]) == 0,
        "system_balance",
    )

    # PTDF flow constraints on each critical branch
    for bi in range(n_branches):
        flow_expr = pulp.lpSum([
            float(ptdf_matrix[bi, zi]) * net_position[zi]
            for zi in range(Z)
        ])
        ram = ram_limits[bi]
        prob += flow_expr <= ram["ram_forward"], f"flow_fwd_{ram['name']}"
        prob += flow_expr >= -ram["ram_reverse"], f"flow_rev_{ram['name']}"

    # ── Solve ────────────────────────────────────────────────────
    prob.solve(pulp.PULP_CBC_CMD(msg=verbose))
    status = pulp.LpStatus[prob.status]

    if status != "Optimal":
        return {"status": status}

    # ── Extract zone results ─────────────────────────────────────
    zone_results: dict[str, dict[str, Any]] = {}
    for zi in range(Z):
        zname = zone_names[zi]
        z = zones[zi]
        zone_results.update(extract_zone_results(z, s_vars[zi], d_vars[zi], zname))
        zone_results[zname]["net_position_mw"] = round(
            float(pulp.value(net_position[zi]) or 0), 1
        )

    # ── Extract branch flow results ──────────────────────────────
    branch_flows: list[dict[str, Any]] = []
    for bi in range(n_branches):
        flow_val = sum(
            float(ptdf_matrix[bi, zi])
            * float(pulp.value(net_position[zi]) or 0)
            for zi in range(Z)
        )
        ram = ram_limits[bi]
        util = (
            round(abs(flow_val) / ram["ram_forward"] * 100, 1)
            if ram["ram_forward"] > 0
            else 0.0
        )
        branch_flows.append({
            "branch": ram["name"],
            "flow_mw": round(flow_val, 1),
            "ram_forward": ram["ram_forward"],
            "ram_reverse": ram["ram_reverse"],
            "utilization_pct": util,
        })

    return {
        "status": status,
        "welfare": round(float(pulp.value(welfare)), 2),
        "zones": zone_results,
        "branch_flows": branch_flows,
    }
