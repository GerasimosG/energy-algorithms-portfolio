"""
from __future__ import annotations

Battery Energy Storage System (BESS) — Revenue-maximizing LP.

Models a single battery over T periods given a price forecast.
The LP maximizes revenue by charging when prices are low and
discharging when prices are high, subject to:
- State-of-charge (SoC) limits: 0 ≤ SoC[t] ≤ capacity
- Charge/discharge power limits: 0 ≤ p ≤ max_power
- Energy balance: SoC[t] = SoC[t-1] + charge[t]·η_in − discharge[t]/η_out
- Initial SoC boundary condition

Note on simultaneous charge/discharge
--------------------------------------
In a pure LP without a binary "can't do both" constraint, the solver
could charge and discharge in the same period. For any positive price
this is never optimal — you lose η_in · η_out < 1 on every pair.
At zero or negative prices a degenerate solution may appear, but the
revenue figure is still valid (simultaneous charge+discharge nets zero
energy change with a loss). This is a known simplification for LP
storage models and is acceptable for the vast majority of price profiles.
"""

import pulp

from energy_algorithms.infrastructure.solver_config import solve_model


def solve_storage(
 prices: list[float],
 capacity: float,
 max_power: float,
 eff_in: float,
 eff_out: float,
 initial_soc: float,
 verbose: bool = False,
) -> dict:
 """
 Solve battery revenue-maximization LP.

 Parameters
 ----------
 prices : list of electricity prices for each time period (€/MWh).
 capacity : battery energy capacity in MWh.
 max_power : maximum charge/discharge power in MW.
 eff_in : charging efficiency (fraction, 0–1).
 eff_out : discharging efficiency (fraction, 0–1).
 initial_soc : state of charge at t=0 in MWh.
 verbose : if True, show PuLP solver output.

 Returns
 -------
 dict with keys:
 status : str, solver status (e.g. "Optimal").
 revenue : float, total revenue over the horizon (€).
 schedule : list of dicts, one per period, with keys
 charge, discharge, soc (all in MWh or MW).
 total_cycles : float, approximate equivalent full cycles.
 """
 T = len(prices)

 # ---- Problem ----
 prob = pulp.LpProblem("BESS_Storage", pulp.LpMaximize)

 # ---- Decision variables ----
 charge = [
 pulp.LpVariable(f"charge_{t}", lowBound=0, upBound=max_power)
 for t in range(T)
 ]
 discharge = [
 pulp.LpVariable(f"discharge_{t}", lowBound=0, upBound=max_power)
 for t in range(T)
 ]
 soc = [
 pulp.LpVariable(f"soc_{t}", lowBound=0, upBound=capacity)
 for t in range(T)
 ]

 # ---- Objective: maximize revenue (sell - buy) -----
 prob += pulp.lpSum(
 prices[t] * (discharge[t] - charge[t]) for t in range(T)
 )

 # ---- Energy balance ----
 inv_eff_out = 1.0 / eff_out
 prob += (
 soc[0] == initial_soc + charge[0] * eff_in - discharge[0] * inv_eff_out,
 "energy_balance_0",
 )
 for t in range(1, T):
 prob += (
 soc[t] == soc[t - 1] + charge[t] * eff_in - discharge[t] * inv_eff_out,
 f"energy_balance_{t}",
 )

 # ---- Solve ----
 result = solve_model(prob, msg=verbose)

 if result["status"] != "Optimal":
 return {"status": result["status"]}

 # ---- Extract schedule ----
 schedule = []
 total_discharge = 0.0
 for t in range(T):
 ch = max(0.0, float(pulp.value(charge[t])))
 dch = max(0.0, float(pulp.value(discharge[t])))
 sc = float(pulp.value(soc[t]))
 schedule.append({"charge": ch, "discharge": dch, "soc": sc})
 total_discharge += dch

 total_cycles = total_discharge / capacity if capacity > 0 else 0.0

 return {
 "status": result["status"],
 "revenue": round(float(pulp.value(prob.objective)), 2),
 "schedule": schedule,
 "total_cycles": round(total_cycles, 4),
 }


def demo_storage() -> dict:
 """
 Run a 24-hour BESS optimization with a realistic price profile.

 Battery specs: 100 MWh capacity, 25 MW power, 90 % round-trip
 efficiency (η_in = η_out ≈ 0.95), starting empty.

 Returns
 -------
 dict : result from solve_storage().
 """
 # 24-hour price profile: cheap overnight, expensive evening peak
 prices = [
 25, 20, 18, 15, 15, 18, # 00:00–05:00 — cheap overnight
 25, 35, 45, 55, 60, 60, # 06:00–11:00 — morning ramp
 55, 50, 55, 65, 80, 95, # 12:00–17:00 — afternoon
 100, 110, 90, 70, 55, 40, # 18:00–23:00 — evening peak then fall
 ]

 return solve_storage(
 prices=prices,
 capacity=100.0,
 max_power=25.0,
 eff_in=0.95,
 eff_out=0.95,
 initial_soc=0.0,
 )
