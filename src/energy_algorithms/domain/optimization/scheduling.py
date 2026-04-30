"""
Unit Commitment (Simplified) — MIP for generator scheduling.

Models a day-ahead dispatch with:
- Minimum uptime (once on, must stay on for N periods)
- Minimum downtime (once off, must stay off for N periods)
- Ramp rate limits
- Demand balance
- Reserve margin
- Initial conditions (status, uptime, downtime)
- Horizon-end min up/down enforcement
- Lifecycle hooks (pre_solve, post_solve, post_extract)
"""

import pulp

from energy_algorithms.infrastructure.hooks import run_hooks, PRE_SOLVE, POST_SOLVE, POST_EXTRACT
from energy_algorithms.infrastructure.options import get_option


def solve_unit_commitment(
    demand: list[float],
    generators: list[dict],
    reserve_margin: float = 0.1,
    init_status: list[int] | None = None,
    init_uptime: list[int] | None = None,
    init_downtime: list[int] | None = None,
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
    init_status : list of initial on/off status for each generator (0 or 1).
        Default: all off.
    init_uptime : list of periods each generator has already been on at t=0.
        Only meaningful if init_status[g] == 1. Default: 0.
    init_downtime : list of periods each generator has already been off at t=0.
        Only meaningful if init_status[g] == 0. Default: 0.

    Returns
    -------
    dict with schedule, costs, status
    """
    T = len(demand)
    G = len(generators)
    gen_names = [g["name"] for g in generators]

    # Default initial conditions: all off
    if init_status is None:
        init_status = [0] * G
    if init_uptime is None:
        init_uptime = [0] * G
    if init_downtime is None:
        init_downtime = [0] * G

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
            # su/sd for all t (including t=0 for initial transitions)
            su[g, t] = pulp.LpVariable(f"su_{gn}_{t}", cat="Binary")
            sd[g, t] = pulp.LpVariable(f"sd_{gn}_{t}", cat="Binary")

    # Objective: minimize total cost (fuel + startup)
    total_cost = pulp.lpSum(
        generators[g]["cost_per_mwh"] * p[g, t]
        for g in range(G) for t in range(T)
    )
    # Add startup costs (including t=0)
    for g in range(G):
        for t in range(T):
            total_cost += generators[g]["startup_cost"] * su[g, t]

    prob += total_cost

    # ── Fix 1a: Energy balance (generation must exactly match demand) ──────────
    for t in range(T):
        prob += (
            pulp.lpSum(p[g, t] for g in range(G)) == demand[t],
            f"energy_balance_{t}",
        )

    # ── Fix 1b: Reserve constraint (committed capacity covers demand + reserve) ─
    for t in range(T):
        prob += (
            pulp.lpSum(generators[g]["max_output"] * u[g, t] for g in range(G))
            >= demand[t] * (1 + reserve_margin),
            f"reserve_{t}",
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

    # ── Fix 2: Startup/shutdown logic at t=0 (from init_status) ────────────────
    for g in range(G):
        # t=0: transition from initial status
        prob += (
            su[g, 0] - sd[g, 0] == u[g, 0] - init_status[g],
            f"init_transition_{gen_names[g]}",
        )
        prob += su[g, 0] + sd[g, 0] <= 1

    # 4. Startup/shutdown logic for t >= 1: su - sd = u_t - u_{t-1}
    for g in range(G):
        for t in range(1, T):
            prob += su[g, t] - sd[g, t] == u[g, t] - u[g, t - 1]
            prob += su[g, t] + sd[g, t] <= 1

    # ── Fix 3a: Initial minimum uptime (honour pre-t=0 uptime) ─────────────────
    # When a generator starts the horizon already ON but hasn't fulfilled min_up
    for g in range(G):
        min_up = generators[g]["min_up"]
        if min_up <= 0:
            continue
        if init_status[g] == 1:
            remaining_up = min_up - init_uptime[g]
            if remaining_up > 0:
                bound = min(remaining_up, T)
                prob += (
                    pulp.lpSum(u[g, tau] for tau in range(bound)) >= bound,
                    f"init_min_up_{gen_names[g]}",
                )

    # ── Fix 3b: Initial minimum downtime (honour pre-t=0 downtime) ─────────────
    # When a generator starts the horizon already OFF but hasn't fulfilled min_down
    for g in range(G):
        min_down = generators[g]["min_down"]
        if min_down <= 0:
            continue
        if init_status[g] == 0:
            remaining_down = min_down - init_downtime[g]
            if remaining_down > 0:
                bound = min(remaining_down, T)
                prob += (
                    pulp.lpSum(1 - u[g, tau] for tau in range(bound)) >= bound,
                    f"init_min_down_{gen_names[g]}",
                )

    # 5. Minimum uptime (standard constraint for interior + t=0 startups)
    for g in range(G):
        min_up = generators[g]["min_up"]
        if min_up <= 0:
            continue
        for t in range(0, T - min_up + 1):
            prob += (
                pulp.lpSum(u[g, tau] for tau in range(t, t + min_up))
                >= min_up * su[g, t],
                f"min_up_{gen_names[g]}_{t}",
            )

    # ── Fix 4a: Horizon-end minimum uptime ─────────────────────────────────────
    # If a startup occurs too close to T, enforce remaining periods
    for g in range(G):
        min_up = generators[g]["min_up"]
        if min_up <= 0:
            continue
        for t in range(max(0, T - min_up + 1), T):
            remaining = T - t
            prob += (
                pulp.lpSum(u[g, tau] for tau in range(t, T)) >= remaining * su[g, t],
                f"horizon_min_up_{gen_names[g]}_{t}",
            )

    # 6. Minimum downtime (standard constraint for interior + t=0 shutdowns)
    for g in range(G):
        min_down = generators[g]["min_down"]
        if min_down <= 0:
            continue
        for t in range(0, T - min_down + 1):
            prob += (
                pulp.lpSum(1 - u[g, tau] for tau in range(t, t + min_down))
                >= min_down * sd[g, t],
                f"min_down_{gen_names[g]}_{t}",
            )

    # ── Fix 4b: Horizon-end minimum downtime ───────────────────────────────────
    for g in range(G):
        min_down = generators[g]["min_down"]
        if min_down <= 0:
            continue
        for t in range(max(0, T - min_down + 1), T):
            remaining = T - t
            prob += (
                pulp.lpSum(1 - u[g, tau] for tau in range(t, T)) >= remaining * sd[g, t],
                f"horizon_min_down_{gen_names[g]}_{t}",
            )

    # Solve
    # --- Pre-solve hook ---
    if get_option("run_hooks"):
        run_hooks(PRE_SOLVE, prob=prob, solver="cbc")

    prob.solve(pulp.PULP_CBC_CMD(msg=verbose))

    status_str = pulp.LpStatus[prob.status]

    # --- Post-solve hook ---
    if get_option("run_hooks"):
        run_hooks(POST_SOLVE, prob=prob, status=status_str, solver="cbc")

    if status_str != "Optimal":
        return {"status": status_str}

    # Extract schedule
    schedule = {}
    for t in range(T):
        period = {gen_names[g]: float(pulp.value(p[g, t])) for g in range(G)}
        period["_demand"] = demand[t]
        period["_reserve"] = (
            sum(generators[g]["max_output"] * float(pulp.value(u[g, t])) for g in range(G))
            - demand[t]
        )
        period["_online"] = [gen_names[g] for g in range(G) if pulp.value(u[g, t]) > 0.5]
        schedule[f"t={t}"] = period

    # --- Post-extract hook ---
    if get_option("run_hooks"):
        run_hooks(
            POST_EXTRACT,
            prob=prob,
            status=status_str,
            schedule=schedule,
            total_cost=round(float(pulp.value(total_cost)), 2),
        )

    return {
        "status": status_str,
        "total_cost": round(float(pulp.value(total_cost)), 2),
        "schedule": schedule,
    }


def demo_uc() -> dict:
    """Run a 12-period unit commitment with 3 generators, all initially off."""
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
        # All generators initially off; downtime set high enough so min_down
        # is already satisfied and units can start when needed.
        init_status=[0, 0, 0],
        init_uptime=[0, 0, 0],
        init_downtime=[99, 99, 99],
    )
