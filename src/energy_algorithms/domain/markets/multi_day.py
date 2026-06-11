"""Multi-Day Market Coupling — FBMC/ATC extended across multiple days.

Models inter-temporal constraints between consecutive market days,
enabling storage assets (batteries, pumped hydro) to shift energy from
cheap days to expensive days. The key insight is that a battery's
State-of-Charge at the end of day D becomes its initial SoC for day D+1.

Single-level formulation: all days are solved in one LP so the solver
sees the entire horizon. The per-day ATC constraints and zone
definitions can differ (e.g. different outages, seasonal ATC levels),
but the storage SoC bridges the days.

Storage is modelled as a "market participant" that can charge (buy
energy, acting as demand) and discharge (sell energy, acting as supply)
in any day. The net injection is added to the global energy balance
for each day. Inter-zonal flows distribute the stored energy across
the coupled zones.

References
----------
 - Euphemia Public Description (PCR market coupling)
 - Conejo et al., "Decision Making Under Uncertainty in Electricity Markets"
 - ENTSO-E Flow-Based Market Coupling documentation
"""
from __future__ import annotations

from typing import Any

import pulp

from energy_algorithms.domain.markets.coupling_utils import (
 compute_social_welfare,
 extract_flow_results,
 extract_zone_results,
 validate_atc,
)
from energy_algorithms.infrastructure.solver_config import solve_model

# ──────────────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────

def solve_multi_day(
 zones_per_day: list[list[dict]],
 atc_per_day: list[dict[tuple[int, int], float]],
 storage_config: dict | None = None,
 horizon_days: int = 2,
 verbose: bool = False,
) -> dict[str, Any]:
 """Solve multi-day market coupling with optional storage.

 Parameters
 ----------
 zones_per_day : list[list[dict]]
 zones_per_day[d] is the market configuration for day *d*.
 Each zone dict has keys ``"name"``, ``"supply"``, ``"demand"``
 following the same convention as
 :func:`energy_markets.multi_zone.solve_multi_zone`.
 atc_per_day : list[dict[tuple[int, int], float]]
 atc_per_day[d] maps ``(zone_i, zone_j) → capacity_mw`` for day *d*.
 Zone indices are per-day, so (0,1) always means the first two
 zones of that day.
 storage_config : dict or None, optional
 Dictionary with keys:

 - ``"capacity"`` — MWh (energy capacity)
 - ``"max_power"`` — MW (charge / discharge power limit)
 - ``"eff_in"`` — charging efficiency, fraction ∈ (0, 1]
 - ``"eff_out"`` — discharging efficiency, fraction ∈ (0, 1]
 - ``"initial_soc"`` — MWh at start of day 0
 - ``"zone"`` — optional zone index where storage is connected
 on each day; defaults to 0

 If ``None``, no storage is modelled (pure per-day coupling).
 horizon_days : int
 Number of days to couple. Must equal ``len(zones_per_day)``
 and ``len(atc_per_day)``.
 verbose : bool
 If ``True``, print the CBC solver output.

 Returns
 -------
 dict
 ``status`` : str — ``"Optimal"``, ``"Infeasible"``, …
 ``welfare`` : float — total social welfare across all days (€)
 ``per_day`` : list of dicts — per-zone results for each day
 ``storage_schedule`` : dict or None —
 ``{"day_0": [period_dict, …], "day_1": …}``.
 Each *period_dict* has keys ``charge``, ``discharge``,
 ``soc_start``, ``soc_end`` (all floats).
 ``total_energy_shifted`` : float — total MWh discharged from
 storage across all days

 Raises
 ------
 ValueError
 If ``zones_per_day`` and ``atc_per_day`` have different lengths,
 or ``horizon_days`` doesn't match.
 """
 # ── Validation ──────────────────────────────────────────────────
 if len(zones_per_day) != horizon_days:
 raise ValueError(
 f"zones_per_day has {len(zones_per_day)} entries "
 f"but horizon_days={horizon_days}"
 )
 if len(atc_per_day) != horizon_days:
 raise ValueError(
 f"atc_per_day has {len(atc_per_day)} entries "
 f"but horizon_days={horizon_days} — both must supply "
 f"the same number of days"
 )

 has_storage = storage_config is not None

 # ── Build the single LP ─────────────────────────────────────────
 prob = pulp.LpProblem("MultiDay_Coupling", pulp.LpMaximize)

 # ── Storage variables (must be declared before balance constraints) ──
 charge_day = []
 discharge_day = []
 soc_in = []
 soc_out = []
 if has_storage:
 cap = storage_config["capacity"]
 max_p = storage_config["max_power"]
 eta_in = storage_config["eff_in"]
 eta_out = storage_config["eff_out"]
 initial_soc = storage_config["initial_soc"]
 storage_zone = int(storage_config.get("zone", 0))

 for d in range(horizon_days):
 soc_in.append(
 pulp.LpVariable(f"soc_in_d{d}", lowBound=0, upBound=cap)
 )
 soc_out.append(
 pulp.LpVariable(f"soc_out_d{d}", lowBound=0, upBound=cap)
 )
 charge_day.append(
 pulp.LpVariable(f"charge_d{d}", lowBound=0, upBound=max_p)
 )
 discharge_day.append(
 pulp.LpVariable(f"discharge_d{d}", lowBound=0, upBound=max_p)
 )

 # Initial SoC
 prob += soc_in[0] == initial_soc, "soc_init"

 # Daily energy balance + carry-over
 for d in range(horizon_days):
 prob += (
 soc_out[d] == soc_in[d]
 + charge_day[d] * eta_in
 - discharge_day[d] * (1.0 / eta_out),
 f"soc_balance_d{d}",
 )
 if d < horizon_days - 1:
 prob += (
 soc_out[d] == soc_in[d + 1],
 f"soc_carry_d{d}_to_d{d + 1}",
 )

 # ── Per-day market variables and constraints ────────────────────
 day_zone_names = []
 day_flows = []
 day_s_frac = []
 day_d_frac = []
 day_welfare_terms = []

 for d in range(horizon_days):
 zones = zones_per_day[d]
 Z = len(zones)
 znames = [z["name"] for z in zones]

 # Flow variables (one signed variable per bidirectional ATC corridor).
 atc_dict = atc_per_day[d]
 flows = {}
 validated = validate_atc(atc_dict, zone_count=Z)
 for _corridor, (i, j, cap) in validated.items():
 flows[(i, j)] = pulp.LpVariable(
 f"flow_d{d}_{znames[i]}_to_{znames[j]}",
 lowBound=-cap,
 upBound=cap,
 )

 # Acceptance fraction variables
 s_frac = {}
 d_frac = {}
 for zi in range(Z):
 Ns = len(zones[zi]["supply"])
 Nd = len(zones[zi]["demand"])
 s_frac[zi] = {
 si: pulp.LpVariable(f"s_d{d}_{znames[zi]}_{si}", 0, 1)
 for si in range(Ns)
 }
 d_frac[zi] = {
 di: pulp.LpVariable(f"d_d{d}_{znames[zi]}_{di}", 0, 1)
 for di in range(Nd)
 }

 # Welfare expression for this day
 welfare_expr = pulp.lpSum(
 compute_social_welfare(zones[zi], s_frac[zi], d_frac[zi])
 for zi in range(Z)
 )

 # Per-zone energy balance
 if has_storage and storage_zone >= Z:
 raise ValueError(
 f"storage zone {storage_zone} is invalid for day {d} "
 f"with {Z} zones"
 )
 for zi in range(Z):
 supply_qty = pulp.lpSum(
 zones[zi]["supply"][si]["qty"] * s_frac[zi][si]
 for si in range(len(zones[zi]["supply"]))
 )
 demand_qty = pulp.lpSum(
 zones[zi]["demand"][di]["qty"] * d_frac[zi][di]
 for di in range(len(zones[zi]["demand"]))
 )
 net_exports = pulp.lpSum(
 var if i == zi else -var
 for (i, j), var in flows.items()
 if zi in (i, j)
 )
 storage_injection = (
 discharge_day[d] - charge_day[d]
 if has_storage and zi == storage_zone
 else 0
 )
 prob += (
 supply_qty + storage_injection == demand_qty + net_exports,
 f"balance_d{d}_{znames[zi]}",
 )

 # Global energy balance with storage injection
 total_supply = pulp.lpSum(
 zones[zi]["supply"][si]["qty"] * s_frac[zi][si]
 for zi in range(Z)
 for si in range(len(zones[zi]["supply"]))
 )
 total_demand = pulp.lpSum(
 zones[zi]["demand"][di]["qty"] * d_frac[zi][di]
 for zi in range(Z)
 for di in range(len(zones[zi]["demand"]))
 )
 if has_storage:
 net_inj = discharge_day[d] - charge_day[d]
 prob += (
 total_supply + net_inj == total_demand,
 f"system_energy_balance_d{d}",
 )

 day_welfare_terms.append(welfare_expr)
 day_zone_names.append(znames)
 day_flows.append(flows)
 day_s_frac.append(s_frac)
 day_d_frac.append(d_frac)

 # ── Total welfare objective ─────────────────────────────────────
 total_welfare = pulp.lpSum(day_welfare_terms)
 prob += total_welfare

 # ── Solve ───────────────────────────────────────────────────────
 result = solve_model(prob, msg=verbose)
 status = result["status"]

 if status != "Optimal":
 return {"status": status}

 # ── Extract results ─────────────────────────────────────────────
 per_day_results = []
 for d in range(horizon_days):
 zones = zones_per_day[d]
 znames = day_zone_names[d]
 s_frac = day_s_frac[d]
 d_frac = day_d_frac[d]
 flows = day_flows[d]

 flow_results = extract_flow_results(flows, znames)

 zone_results = {}
 for zi in range(len(zones)):
 zone_results.update(
 extract_zone_results(zones[zi], s_frac[zi], d_frac[zi], znames[zi])
 )

 per_day_results.append({
 "day": d,
 "flows": flow_results,
 "zones": zone_results,
 })

 # ── Storage schedule ────────────────────────────────────────────
 storage_schedule = None
 total_energy_shifted = 0.0
 if has_storage:
 storage_schedule = {}
 for d in range(horizon_days):
 ch = max(0.0, float(pulp.value(charge_day[d]) or 0))
 dch = max(0.0, float(pulp.value(discharge_day[d]) or 0))
 soc_start = float(pulp.value(soc_in[d]) or 0)
 soc_end_val = float(pulp.value(soc_out[d]) or 0)
 storage_schedule[f"day_{d}"] = [{
 "charge": round(ch, 2),
 "discharge": round(dch, 2),
 "soc_start": round(soc_start, 2),
 "soc_end": round(soc_end_val, 2),
 }]
 total_energy_shifted += dch

 return {
 "status": status,
 "welfare": round(float(pulp.value(total_welfare)), 2),
 "per_day": per_day_results,
 "storage_schedule": storage_schedule,
 "total_energy_shifted": round(total_energy_shifted, 2),
 }
