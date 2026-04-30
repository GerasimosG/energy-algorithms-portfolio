"""
Transportation Problem — Classic LP.

Minimize shipping cost from warehouses (supply) to retailers (demand).
"""
from __future__ import annotations

import pulp


def solve_transportation(
    supply: dict[str, float],
    demand: dict[str, float],
    cost: dict[tuple[str, str], float],
    verbose: bool = False,
) -> dict:
    """
    Solve the transportation LP.

    Parameters
    ----------
    supply : dict {warehouse: available_units}
    demand : dict {retailer: required_units}
    cost : dict {(warehouse, retailer): cost_per_unit}

    Returns
    -------
    dict with allocations, total_cost, status
    """
    warehouses = list(supply.keys())
    retailers = list(demand.keys())

    prob = pulp.LpProblem("Transportation", pulp.LpMinimize)

    # Decision variables: flow from w to r
    flow = {
        (w, r): pulp.LpVariable(f"flow_{w}_{r}", lowBound=0)
        for w in warehouses for r in retailers
    }

    # Objective: minimize total shipping cost
    prob += pulp.lpSum(cost[w, r] * flow[w, r] for w in warehouses for r in retailers)

    # Supply constraints: outflow ≤ available
    for w in warehouses:
        prob += pulp.lpSum(flow[w, r] for r in retailers) <= supply[w], f"supply_{w}"

    # Demand constraints: inflow ≥ required
    for r in retailers:
        prob += pulp.lpSum(flow[w, r] for w in warehouses) >= demand[r], f"demand_{r}"

    # Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=verbose))

    allocations = {}
    total_cost = 0.0
    for (w, r), var in flow.items():
        val = pulp.value(var)
        if val > 0.001:
            allocations[f"{w} → {r}"] = val
            total_cost += val * cost[w, r]

    return {
        "status": pulp.LpStatus[prob.status],
        "total_cost": round(total_cost, 2),
        "allocations": allocations,
    }


def demo_transportation() -> dict:
    """Run a 3-warehouse × 4-retailer transportation problem."""
    supply = {"Warehouse_A": 100, "Warehouse_B": 150, "Warehouse_C": 120}
    demand = {"Retailer_1": 80, "Retailer_2": 100, "Retailer_3": 90, "Retailer_4": 70}

    cost = {
        ("Warehouse_A", "Retailer_1"): 4, ("Warehouse_A", "Retailer_2"): 6,
        ("Warehouse_A", "Retailer_3"): 9, ("Warehouse_A", "Retailer_4"): 5,
        ("Warehouse_B", "Retailer_1"): 7, ("Warehouse_B", "Retailer_2"): 3,
        ("Warehouse_B", "Retailer_3"): 5, ("Warehouse_B", "Retailer_4"): 8,
        ("Warehouse_C", "Retailer_1"): 2, ("Warehouse_C", "Retailer_2"): 9,
        ("Warehouse_C", "Retailer_3"): 4, ("Warehouse_C", "Retailer_4"): 6,
    }

    return solve_transportation(supply, demand, cost)
