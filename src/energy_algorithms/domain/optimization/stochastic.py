"""Renewable Uncertainty Module — Stochastic Programming for Wind/Solar.

Generates Monte Carlo scenarios for wind and solar forecast errors,
solves scenario-based unit commitment, and computes decision-theoretic
metrics (VSS, EVPI) that quantify the value of stochastic modeling.

These concepts are directly relevant to Euphemia  's stochastic market
coupling research and Industry's renewable portfolio risk management.
"""

from __future__ import annotations

import numpy as np
import pulp
from typing import Any


# ---------------------------------------------------------------------------
# Scenario generation
# ---------------------------------------------------------------------------

def generate_wind_scenarios(
    base_profile: np.ndarray,
    std_pct: float = 0.15,
    n_scenarios: int = 10,
    seed: int | None = None,
) -> list[np.ndarray]:
    """Generate wind capacity factor scenarios via Monte Carlo.

    Each scenario perturbs the base profile with Gaussian noise scaled
    by ``std_pct * base_profile``, then clips to [0, 1].

    Parameters
    ----------
    base_profile : np.ndarray, shape (n_periods,)
        Base wind capacity factor profile (0–1).
    std_pct : float
        Standard deviation as fraction of base value (default 0.15 = 15%).
    n_scenarios : int
        Number of scenarios to generate.
    seed : int or None
        RNG seed for reproducibility.

    Returns
    -------
    list of np.ndarray
        Each element is a perturbed profile of the same length as ``base_profile``,
        clipped to [0, 1].
    """
    rng = np.random.RandomState(seed)
    n_periods = len(base_profile)
    scenarios: list[np.ndarray] = []

    for _ in range(n_scenarios):
        noise = rng.normal(0, std_pct, size=n_periods)
        scenario = base_profile * (1.0 + noise)
        scenario = np.clip(scenario, 0.0, 1.0)
        scenarios.append(scenario)

    return scenarios


def generate_solar_scenarios(
    base_profile: np.ndarray,
    std_pct: float = 0.20,
    n_scenarios: int = 10,
    seed: int | None = None,
) -> list[np.ndarray]:
    """Generate solar capacity factor scenarios via Monte Carlo.

    Solar uncertainty is typically larger than wind (cloud cover is
    harder to forecast), hence the higher default ``std_pct``.

    Parameters
    ----------
    base_profile : np.ndarray, shape (n_periods,)
        Base solar capacity factor profile (0–1).
    std_pct : float
        Standard deviation as fraction of base value (default 0.20).
    n_scenarios : int
        Number of scenarios.
    seed : int or None
        RNG seed.

    Returns
    -------
    list of np.ndarray
    """
    rng = np.random.RandomState(seed)
    n_periods = len(base_profile)
    scenarios: list[np.ndarray] = []

    for _ in range(n_scenarios):
        noise = rng.normal(0, std_pct, size=n_periods)
        scenario = base_profile * (1.0 + noise)
        scenario = np.clip(scenario, 0.0, 1.0)
        scenarios.append(scenario)

    return scenarios


# ---------------------------------------------------------------------------
# Scenario-based Unit Commitment
# ---------------------------------------------------------------------------

def solve_scenario_uc(
    demand: list[float],
    wind_scenario: np.ndarray,
    solar_scenario: np.ndarray,
    generators: list[dict[str, Any]],
    verbose: bool = False,
) -> dict[str, Any]:
    """Solve deterministic unit commitment for ONE renewable scenario.

    Parameters
    ----------
    demand : list[float], shape (T,)
        Gross demand in MW per period.
    wind_scenario : np.ndarray, shape (T,)
        Wind generation in MW per period (already scaled).
    solar_scenario : np.ndarray, shape (T,)
        Solar generation in MW per period.
    generators : list of dict
        Each dict: {name, min_output, max_output, cost_per_mwh}.
    verbose : bool
        If True, print solver log.

    Returns
    -------
    dict with keys: status, total_cost, schedule, dispatch
    """
    T = len(demand)
    G = len(generators)

    net_demand = np.maximum(
        np.array(demand) - wind_scenario - solar_scenario, 0.0
    )

    prob = pulp.LpProblem("Scenario_UC", pulp.LpMinimize)

    power = {}
    for g in range(G):
        power[g] = [
            pulp.LpVariable(
                f"gen_{g}_t{t}",
                lowBound=generators[g]["min_output"],
                upBound=generators[g]["max_output"],
            )
            for t in range(T)
        ]

    # Unserved energy (penalty slack)
    unserved = [
        pulp.LpVariable(f"unserved_{t}", lowBound=0) for t in range(T)
    ]

    PENALTY = 10000.0
    cost_expr = pulp.lpSum(
        generators[g]["cost_per_mwh"] * power[g][t]
        for g in range(G)
        for t in range(T)
    )
    cost_expr += pulp.lpSum(PENALTY * unserved[t] for t in range(T))
    prob += cost_expr

    # Energy balance per period
    for t in range(T):
        gen_sum = pulp.lpSum(power[g][t] for g in range(G))
        prob += (
            gen_sum + unserved[t] == net_demand[t],
            f"balance_{t}",
        )

    prob.solve(pulp.PULP_CBC_CMD(msg=verbose))
    status = pulp.LpStatus[prob.status]

    if status != "Optimal":
        return {"status": status}

    # Extract results — per-period schedule as dict
    schedule = {}
    dispatch = {}
    total_cost = 0.0
    for g in range(G):
        p_vals = [float(pulp.value(power[g][t])) for t in range(T)]
        dispatch[generators[g]["name"]] = p_vals
        total_cost += sum(
            generators[g]["cost_per_mwh"] * pv for pv in p_vals
        )

    for t in range(T):
        schedule[f"t={t}"] = {
            gen["name"]: dispatch[gen["name"]][t] for gen in generators
        }

    unserved_vals = [float(pulp.value(u)) for u in unserved]
    total_cost += PENALTY * sum(unserved_vals)

    return {
        "status": status,
        "total_cost": round(total_cost, 2),
        "schedule": schedule,
        "dispatch": dispatch,
        "unserved_energy": [round(v, 2) for v in unserved_vals],
    }


# ---------------------------------------------------------------------------
# Value of Stochastic Solution (VSS)
# ---------------------------------------------------------------------------

def compute_vss(
    demand: list[float],
    base_wind: np.ndarray,
    base_solar: np.ndarray,
    generators: list[dict[str, Any]],
    n_scenarios: int = 10,
    std_pct: float = 0.15,
    seed: int = 42,
) -> float:
    """Compute Value of Stochastic Solution (VSS).

    VSS = EEV - RP, where RP averages optimal cost per scenario
    and EEV uses the deterministic dispatch across all scenarios.

    Parameters
    ----------
    demand : list[float]
        Gross demand per period.
    base_wind, base_solar : np.ndarray
        Expected renewable profiles.
    generators : list of dict
        Generator specs.
    n_scenarios : int
        Number of Monte Carlo scenarios.
    std_pct : float
        Standard deviation for scenario generation.
    seed : int
        RNG seed.

    Returns
    -------
    float — VSS value (positive means stochastic adds value).
    """
    wind_scenarios = generate_wind_scenarios(
        base_wind, std_pct=std_pct, n_scenarios=n_scenarios, seed=seed
    )
    solar_scenarios = generate_solar_scenarios(
        base_solar, std_pct=std_pct, n_scenarios=n_scenarios, seed=seed
    )

    # RP: solve each scenario optimally
    rp_costs = []
    for i in range(n_scenarios):
        result = solve_scenario_uc(
            demand, wind_scenarios[i], solar_scenarios[i], generators
        )
        if result["status"] == "Optimal":
            rp_costs.append(result["total_cost"])
    rp_cost = np.mean(rp_costs) if rp_costs else 0.0

    # EV: solve with expected values
    ev_result = solve_scenario_uc(
        demand, base_wind, base_solar, generators
    )
    if ev_result["status"] != "Optimal":
        return 0.0

    # EEV: evaluate EV dispatch in each scenario
    ev_dispatch = ev_result["dispatch"]
    eev_costs = []
    for i in range(n_scenarios):
        net_demand = np.maximum(
            np.array(demand) - wind_scenarios[i] - solar_scenarios[i], 0
        )
        total = 0.0
        for g_name, p_vals in ev_dispatch.items():
            gen_info = next(g for g in generators if g["name"] == g_name)
            total += sum(
                gen_info["cost_per_mwh"] * p_vals[t]
                for t in range(len(demand))
            )
            # Penalty for unserved energy
            for t in range(len(demand)):
                all_gen = sum(ev_dispatch[n][t] for n in ev_dispatch)
                mismatch = max(0, net_demand[t] - all_gen)
                total += 10000.0 * mismatch
        eev_costs.append(total)
    eev_cost = np.mean(eev_costs) if eev_costs else 0.0

    return round(eev_cost - rp_cost, 2)


# ---------------------------------------------------------------------------
# Expected Value of Perfect Information (EVPI)
# ---------------------------------------------------------------------------

def compute_evpi(
    demand: list[float],
    base_wind: np.ndarray,
    base_solar: np.ndarray,
    generators: list[dict[str, Any]],
    n_scenarios: int = 10,
    std_pct: float = 0.15,
    seed: int = 42,
) -> float:
    """Compute Expected Value of Perfect Information (EVPI).

    EVPI = EV cost - WS cost.
    Maximum you'd pay for a perfect forecast.

    Returns
    -------
    float — EVPI value (non-negative).
    """
    wind_scenarios = generate_wind_scenarios(
        base_wind, std_pct=std_pct, n_scenarios=n_scenarios, seed=seed
    )
    solar_scenarios = generate_solar_scenarios(
        base_solar, std_pct=std_pct, n_scenarios=n_scenarios, seed=seed
    )

    # EV cost: solve with expected values
    ev_result = solve_scenario_uc(demand, base_wind, base_solar, generators)
    ev_cost = ev_result.get("total_cost", 0.0)

    # WS cost: solve each scenario perfectly
    ws_costs = []
    for i in range(n_scenarios):
        result = solve_scenario_uc(
            demand, wind_scenarios[i], solar_scenarios[i], generators
        )
        if result["status"] == "Optimal":
            ws_costs.append(result["total_cost"])

    ws_cost = np.mean(ws_costs) if ws_costs else 0.0
    return max(0.0, round(ev_cost - ws_cost, 2))
