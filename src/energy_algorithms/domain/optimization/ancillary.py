"""
Ancillary Services Bid Optimisation — FCR + aFRR joint with BESS.

Simplified but realistic model of an ENERGY-style BESS offering
symmetric FCR and asymmetric aFRR capacity products in parallel
with day-ahead energy arbitrage.

Ancillary services (Belgian / European context)
-----------------------------------------------
**FCR (Frequency Containment Reserve)** — symmetric product. The
provider commits a capacity in MW that can be activated in both
upward and downward direction proportionally to the frequency
deviation. Procurement is daily; the capacity payment is the only
revenue (activation is rare and not modelled here). FCR is procured
symmetrically in BE/DE/FR/AT (PICASSO platform since 2022).

**aFRR (automatic Frequency Restoration Reserve)** — activated
automatically by the TSO controller (5-min cycle). Provider commits
a capacity in MW (and direction: up or down); when activated, energy
flows accordingly. Revenue: capacity payment (€/MW/h) plus, when
activated, energy payment at the imbalance price (€/MWh).

**mFRR (manual Frequency Restoration Reserve)** — manually activated.
Not modelled here — its TSO rules differ per country and the
activation is slow (15 min).

**Joint energy + reserve optimisation**
----------------------------------------
Reserving capacity for FCR/aFRR constrains the BESS operating
range. If 1 MW of FCR is committed, the BESS can only use
``P_max - 1 MW`` for energy arbitrage (since the symmetric reserve
could be called in either direction). The optimisation must decide
how to split capacity between the three revenue streams:

    max  Σ_t [ energy_price[t] · (discharge[t] − charge[t])
              + fcr_price · fcr_capacity
              + afrr_up_price[t] · afrr_up[t]
              + afrr_down_price[t] · afrr_down[t] ]

subject to SoC dynamics and reduced power headroom for the
committed reserve.

This is a linear, deterministic LP — CBC solves it in <1 s.

**Caveats / simplifications documented**

1. No activation probability — aFRR is modelled as if energy
   payment is certain at the expected imbalance price. Production
   would use probabilistic activation.
2. Symmetric FCR only — asymmetric FCR (rare) not handled.
3. Single BESS — no portfolio of assets bidding jointly.
4. No prequalification constraints (minimum bid size, ramp rate,
   state-of-energy envelope) — these are TSO-specific and out of
   scope for a portfolio.

References
----------
- ENTSO-E SAFA Appendix A (FCR/aFRR/mFRR definitions)
- Elia "Ancillary Services — Products and Balancing" (2024)
- Kiesel & Paraschiv (2021), "The Value of Liquidity in Intraday
  Markets for Energy Reserves"
"""
from __future__ import annotations

from collections.abc import Sequence

import pulp

from energy_algorithms.infrastructure.solver_config import solve_model


def solve_fcr_only(
    fcr_price: float,
    max_power_mw: float,
    horizon_hours: int = 24,
) -> dict:
    """
    Solve a pure FCR (symmetric) capacity bid for a single BESS.

    The optimal bid is always the full power capability — FCR is a
    pure capacity product with no energy displacement cost in this
    simplified model. (Production would subtract opportunity cost
    of not arbitraging energy.)

    Parameters
    ----------
    fcr_price : float
        FCR capacity price in €/MW/h.
    max_power_mw : float
        Maximum charge/discharge power in MW.
    horizon_hours : int
        Reservation horizon in hours (default 24 h, the typical
        daily procurement window).

    Returns
    -------
    dict with keys:
        status : str
        fcr_capacity_mw : float — optimal committed capacity.
        revenue_eur : float — expected revenue over the horizon.
    """
    prob = pulp.LpProblem("FCR_Bid", pulp.LpMaximize)
    fcr = pulp.LpVariable("fcr_capacity", lowBound=0, upBound=max_power_mw)
    prob += fcr_price * horizon_hours * fcr
    result = solve_model(prob)
    fcr_val = fcr.value() or 0.0
    return {
        "status": result["status"],
        "fcr_capacity_mw": fcr_val,
        "revenue_eur": fcr_val * fcr_price * horizon_hours,
    }


def solve_joint_bess_reserve(
    prices: Sequence[float],
    capacity_mwh: float,
    max_power_mw: float,
    eff_in: float,
    eff_out: float,
    initial_soc_mwh: float,
    fcr_price: float,
    afrr_up_price: Sequence[float],
    afrr_down_price: Sequence[float],
    afrr_activation_prob: float = 1.0,
    horizon_hours: int | None = None,
) -> dict:
    """
    Joint day-ahead energy arbitrage + FCR + aFRR bidding for a BESS.

    Decision variables (per period t in 0..T-1):
        charge[t]         : MW, energy bought from grid.
        discharge[t]      : MW, energy sold to grid.
        soc[t]            : MWh, state of charge at end of t.
        fcr_capacity      : MW, symmetric FCR capacity (constant).
        afrr_up[t]        : MW, upward aFRR capacity committed.
        afrr_down[t]      : MW, downward aFRR capacity committed.
        soc_reserve_up    : MWh, SoC reserved for upward reserve.

    Constraints:
        - SoC dynamics with η_in / η_out.
        - 0 ≤ soc[t] ≤ capacity.
        - charge[t] + afrr_up[t] + fcr_capacity ≤ max_power_mw.
        - discharge[t] + afrr_down[t] + fcr_capacity ≤ max_power_mw.
        - soc[t] ≥ soc_reserve_up (for upward reserve headroom).
        - soc[t] ≤ capacity - soc_reserve_down (for downward reserve).
        - soc_reserve_up ≥ afrr_up[t] / η_out · 1h · activation_prob.
        - soc_reserve_down ≥ afrr_down[t] · η_in · 1h · activation_prob.

    The reserve-coupling constraints are the key insight: reserving
    capacity for FCR/aFRR shrinks the feasible energy range, and the
    optimiser trades capacity revenue against lost arbitrage revenue.

    Parameters
    ----------
    prices : sequence of float
        Day-ahead prices in €/MWh, length T.
    capacity_mwh : float
        BESS energy capacity in MWh.
    max_power_mw : float
        BESS power capability in MW.
    eff_in, eff_out : float
        Round-trip charge / discharge efficiencies (0–1).
    initial_soc_mwh : float
        State of charge at t=0 in MWh.
    fcr_price : float
        Symmetric FCR capacity price in €/MW/h, constant for the horizon.
    afrr_up_price, afrr_down_price : sequence of float
        aFRR capacity price in €/MW/h per period (length T).
    afrr_activation_prob : float
        Probability [0, 1] that reserved aFRR capacity is actually
        called. 1.0 = always activated; 0.0 = pure capacity payment.
    horizon_hours : int, optional
        If given, used for the FCR revenue term (T-1 implicit if not).

    Returns
    -------
    dict with keys:
        status, total_revenue_eur, energy_revenue_eur,
        fcr_revenue_eur, afrr_revenue_eur,
        fcr_capacity_mw, afrr_up, afrr_down,
        schedule (list of dicts: charge, discharge, soc).
    """
    T = len(prices)
    if len(afrr_up_price) != T or len(afrr_down_price) != T:
        raise ValueError(
            f"aFRR price series must match prices length T={T}; "
            f"got up={len(afrr_up_price)} down={len(afrr_down_price)}"
        )
    if horizon_hours is None:
        horizon_hours = T

    prob = pulp.LpProblem("Joint_BESS_Reserve", pulp.LpMaximize)

    # ── Decision variables ────────────────────────────────────────────
    charge = [
        pulp.LpVariable(f"charge_{t}", lowBound=0, upBound=max_power_mw)
        for t in range(T)
    ]
    discharge = [
        pulp.LpVariable(f"discharge_{t}", lowBound=0, upBound=max_power_mw)
        for t in range(T)
    ]
    soc = [
        pulp.LpVariable(f"soc_{t}", lowBound=0, upBound=capacity_mwh)
        for t in range(T)
    ]
    fcr_cap = pulp.LpVariable("fcr_cap", lowBound=0, upBound=max_power_mw)
    afrr_up = [
        pulp.LpVariable(f"afrr_up_{t}", lowBound=0, upBound=max_power_mw)
        for t in range(T)
    ]
    afrr_dn = [
        pulp.LpVariable(f"afrr_dn_{t}", lowBound=0, upBound=max_power_mw)
        for t in range(T)
    ]

    # ── Objective ─────────────────────────────────────────────────────
    energy_revenue = pulp.lpSum(
        [prices[t] * (discharge[t] - charge[t]) for t in range(T)]
    )
    fcr_revenue = fcr_price * horizon_hours * fcr_cap
    afrr_revenue = afrr_activation_prob * pulp.lpSum(
        [afrr_up_price[t] * afrr_up[t] + afrr_down_price[t] * afrr_dn[t]
         for t in range(T)]
    )
    prob += energy_revenue + fcr_revenue + afrr_revenue

    # ── Constraints ──────────────────────────────────────────────────
    for t in range(T):
        # SoC dynamics
        prev_soc = initial_soc_mwh if t == 0 else soc[t - 1]
        prob += soc[t] == prev_soc + eff_in * charge[t] - discharge[t] / eff_out

        # Symmetric FCR shrinks both charge and discharge headroom
        prob += charge[t] + afrr_up[t] + fcr_cap <= max_power_mw
        prob += discharge[t] + afrr_dn[t] + fcr_cap <= max_power_mw

        # SoC headroom for upward reserve (must be able to discharge)
        prob += soc[t] >= afrr_up[t] * afrr_activation_prob / eff_out
        # SoC headroom for downward reserve (must be able to charge)
        prob += soc[t] <= capacity_mwh - afrr_dn[t] * afrr_activation_prob * eff_in

    result = solve_model(prob)

    if result["status"] != "Optimal":
        return {
            "status": result["status"],
            "total_revenue_eur": 0.0,
            "energy_revenue_eur": 0.0,
            "fcr_revenue_eur": 0.0,
            "afrr_revenue_eur": 0.0,
            "fcr_capacity_mw": 0.0,
            "afrr_up": [0.0] * T,
            "afrr_down": [0.0] * T,
            "schedule": [],
        }

    fcr_val = fcr_cap.value() or 0.0
    afrr_up_vals = [v.value() or 0.0 for v in afrr_up]
    afrr_dn_vals = [v.value() or 0.0 for v in afrr_dn]
    schedule = []
    for t in range(T):
        schedule.append(
            {
                "charge_mw": charge[t].value() or 0.0,
                "discharge_mw": discharge[t].value() or 0.0,
                "soc_mwh": soc[t].value() or 0.0,
            }
        )

    energy_rev = sum(
        prices[t] * (schedule[t]["discharge_mw"] - schedule[t]["charge_mw"])
        for t in range(T)
    )
    fcr_rev = fcr_val * fcr_price * horizon_hours
    afrr_rev = afrr_activation_prob * sum(
        afrr_up_price[t] * afrr_up_vals[t] + afrr_down_price[t] * afrr_dn_vals[t]
        for t in range(T)
    )

    return {
        "status": "Optimal",
        "total_revenue_eur": energy_rev + fcr_rev + afrr_rev,
        "energy_revenue_eur": energy_rev,
        "fcr_revenue_eur": fcr_rev,
        "afrr_revenue_eur": afrr_rev,
        "fcr_capacity_mw": fcr_val,
        "afrr_up": afrr_up_vals,
        "afrr_down": afrr_dn_vals,
        "schedule": schedule,
    }


def demo_joint_bess_reserve() -> dict:
    """
    Demo on a 24-hour Belgian profile with realistic FCR/aFRR prices.

    Day-ahead prices: 24-h sinusoidal profile (cheap overnight,
    expensive evening peak).
    FCR price: €20/MW/h (typical BE 2024 level).
    aFRR: €15/MW/h for up and down capacity (typical BE 2024).
    """
    import math

    T = 24
    prices = [40 + 30 * math.sin((t - 6) * math.pi / 12) for t in range(T)]
    afrr_up = [15.0] * T
    afrr_dn = [12.0] * T
    return solve_joint_bess_reserve(
        prices=prices,
        capacity_mwh=100.0,
        max_power_mw=50.0,
        eff_in=0.92,
        eff_out=0.92,
        initial_soc_mwh=50.0,
        fcr_price=20.0,
        afrr_up_price=afrr_up,
        afrr_down_price=afrr_dn,
        afrr_activation_prob=0.5,
    )


__all__ = [
    "solve_fcr_only",
    "solve_joint_bess_reserve",
    "demo_joint_bess_reserve",
]
