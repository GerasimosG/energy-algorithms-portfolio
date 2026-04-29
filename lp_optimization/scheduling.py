"""
Unit Commitment (Simplified) — MIP for generator scheduling.

Models a day-ahead dispatch with:
- Minimum uptime (once on, must stay on for N periods)
- Minimum downtime (once off, must stay off for N periods)
- Ramp rate limits
- Demand balance
- Reserve margin
"""

import pulp


def solve_unit_commitment(
    demand: list[float],
    generators: list[dict],
    reserve_margin: float = 0.1,
    verbose: bool = False,
) -> dict:
    """
    Solve simplified unit commitment MIP.

    Parameters
    ----------
    demand : list of demand values for each time period (e.g., 24 hours)
    generators : list of dicts with keys:
        'name', 'min_output', 'max_output', 'cost_per_mwh',
        'startup_cost', 'min_up', 'min_down', 'ramp_rate'
    reserve_margin : fraction of demand to hold as reserve

    Returns
    -------
    dict with schedule, costs, status
    """
    T = len(demand)
    G = len(generators)
    gen_names = [g["name"] for g in generators]

    prob = pulp.LpProblem("Unit_Commitment", pulp.LpMinimize)

    # Decision variables
    p = {}  # Power output
    u = {}  # Binary: unit on/off
    su = {}  # Binary: startup (0→1 transition)
    sd = {}  # Binary: shutdown (1→0 transition)

    for g in range(G):
        for t in range(T):
            gn = gen_names[g]
            p[g, t] = pulp.LpVariable(f"p_{gn}_{t}", lowBound=0)
            u[g, t] = pulp.LpVariable(f"u_{gn}_{t}", cat="Binary")
            if t > 0:
                su[g, t] = pulp.LpVariable(f"su_{gn}_{t}", cat="Binary")
                sd[g, t] = pulp.LpVariable(f"sd_{gn}_{t}", cat="Binary")

    # Objective: minimize total cost (fuel + startup)
    total_cost = pulp.lpSum(
        generators[g]["cost_per_mwh"] * p[g, t]
        for g in range(G) for t in range(T)
    )
    # Add startup costs
    for g in range(G):
        for t in range(1, T):
            total_cost += generators[g]["startup_cost"] * su[g, t]

    prob += total_cost

    # 1. Demand balance
    for t in range(T):
        prob += (
            pulp.lpSum(p[g, t] for g in range(G)) >= demand[t] * (1 + reserve_margin),
            f"demand_{t}",
        )

    # 2. Generation limits
    for g in range(G):
        for t in range(T):
            prob += p[g, t] >= generators[g]["min_output"] * u[g, t]
            prob += p[g, t] <= generators[g]["max_output"] * u[g, t]

    # 3. Ramp rate constraints
    for g in range(G):
        max_ramp = generators[g]["ramp_rate"] * generators[g]["max_output"]
        for t in range(1, T):
            prob += p[g, t] - p[g, t - 1] <= max_ramp
            prob += p[g, t - 1] - p[g, t] <= max_ramp

    # 4. Startup/shutdown logic: su - sd = u_t - u_{t-1}
    for g in range(G):
        for t in range(1, T):
            prob += su[g, t] - sd[g, t] == u[g, t] - u[g, t - 1]
            prob += su[g, t] + sd[g, t] <= 1

    # 5. Minimum uptime: if started at t, must stay on for min_up periods
    for g in range(G):
        min_up = generators[g]["min_up"]
        if min_up <= 0:
            continue
        for t in range(1, T - min_up + 1):
            prob += (
                pulp.lpSum(u[g, tau] for tau in range(t, t + min_up))
                >= min_up * su[g, t]
            )

    # 6. Minimum downtime: if shut down at t, must stay off for min_down periods
    for g in range(G):
        min_down = generators[g]["min_down"]
        if min_down <= 0:
            continue
        for t in range(1, T - min_down + 1):
            prob += (
                pulp.lpSum(1 - u[g, tau] for tau in range(t, t + min_down))
                >= min_down * sd[g, t]
            )

    # Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=verbose))

    if pulp.LpStatus[prob.status] != "Optimal":
        return {"status": pulp.LpStatus[prob.status]}

    # Extract schedule
    schedule = {}
    for t in range(T):
        period = {gen_names[g]: float(pulp.value(p[g, t])) for g in range(G)}
        period["_demand"] = demand[t]
        period["_reserve"] = sum(period[g] for g in gen_names) - demand[t]
        period["_online"] = [gen_names[g] for g in range(G) if pulp.value(u[g, t]) > 0.5]
        schedule[f"t={t}"] = period

    return {
        "status": pulp.LpStatus[prob.status],
        "total_cost": round(float(pulp.value(total_cost)), 2),
        "schedule": schedule,
    }


def demo_uc() -> dict:
    """Run a 12-period unit commitment with 3 generators."""
    demand = [
        500, 480, 460, 450, 460, 500,
        600, 750, 900, 950, 980, 1000,
    ]

    generators = [
        {
            "name": "Coal",
            "min_output": 100, "max_output": 500,
            "cost_per_mwh": 30, "startup_cost": 5000,
            "min_up": 3, "min_down": 2, "ramp_rate": 0.3,
        },
        {
            "name": "Gas",
            "min_output": 50, "max_output": 400,
            "cost_per_mwh": 60, "startup_cost": 2000,
            "min_up": 2, "min_down": 1, "ramp_rate": 0.5,
        },
        {
            "name": "Wind",
            "min_output": 0, "max_output": 300,
            "cost_per_mwh": 5, "startup_cost": 100,
            "min_up": 0, "min_down": 0, "ramp_rate": 1.0,
        },
    ]

    return solve_unit_commitment(
        demand=demand,
        generators=generators,
        reserve_margin=0.1,
    )
