"""
OneInterval asset pattern for LP site optimization.

Follows the energy-py-linear design pattern where each asset type
implements three lifecycle hooks — _constraints(), _objective(),
_post_solve() — that are called by the site-level build_site() function
to assemble a complete PuLP linear program.

Assets modelled:
    - BatteryAsset  : Storage with SoC balance, charge/discharge, efficiency losses.
    - GeneratorAsset: Conventional generator with min/max power and fuel cost.
    - SpillAsset    : Penalty-cost slack supply (ensures LP feasibility).

Usage::

    >>> from energy_algorithms.domain.optimization.assets import demo_site
    >>> result = demo_site()
    >>> print(result["status"])
    Optimal
"""

from __future__ import annotations

import pulp

# ── Asset base class ─────────────────────────────────────────────────────────

class Asset:
    """Base class for OneInterval optimisation assets.

    Each asset contributes variables, constraints, and objective terms
    to a shared PuLP problem.  Subclasses override the three lifecycle
    hooks to implement specific behaviour.

    Parameters
    ----------
    name : str
        Unique identifier for this asset (used in variable/constraint names).

    Attributes
    ----------
    net_power : list[pulp.LpVariable]
        After _constraints() runs, contains one PuLP variable per interval
        representing this asset's net power injection (>0 = generation).
    results : dict
        Populated by _post_solve() with extracted numeric results.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.net_power: list[pulp.LpVariable] = []
        self.results: dict = {}

    def _constraints(self, prob: pulp.LpProblem,
                     interval_data: list[dict], T: int) -> None:
        """Create decision variables and add asset-specific constraints.

        Subclasses MUST populate ``self.net_power`` with one variable
        per interval before returning.

        Parameters
        ----------
        prob : pulp.LpProblem
            The site-level LP being built.
        interval_data : list[dict]
            Per-interval data dicts (keys include 'price', 'demand').
        T : int
            Number of time intervals.
        """
        pass

    def _objective(self, prob, interval_data, T):
        """Return objective expression for this asset, or None."""
        return None

    def _post_solve(self, prob: pulp.LpProblem,
                    interval_data: list[dict], T: int) -> None:
        """Extract numeric results from solved variables into ``self.results``.

        Parameters
        ----------
        prob : pulp.LpProblem
            The solved site-level LP.
        interval_data : list[dict]
            Per-interval data dicts.
        T : int
            Number of time intervals.
        """
        pass


# ── BatteryAsset ─────────────────────────────────────────────────────────────

class BatteryAsset(Asset):
    """Battery Energy Storage asset with round-trip efficiency losses.

    Wraps the storage LP logic (see ``lp_optimization.storage``) into
    the OneInterval hook pattern.  The battery buys power to charge
    when prices are low and sells power by discharging when prices are
    high, subject to capacity and power limits.

    Parameters
    ----------
    name : str
        Asset identifier.
    capacity : float
        Energy capacity in MWh.
    max_power : float
        Maximum charge & discharge power in MW.
    eff_in : float
        Charging efficiency (fraction, 0–1).
    eff_out : float
        Discharging efficiency (fraction, 0–1).
    initial_soc : float
        State of charge at t=0 in MWh.

    Results (after _post_solve)
    ---------------------------
    schedule : list[dict]
        Per-interval dicts with keys ``charge``, ``discharge``, ``soc``.
    total_cycles : float
        Approximate equivalent full cycles.
    """

    def __init__(self, name: str, capacity: float, max_power: float,
                 eff_in: float, eff_out: float, initial_soc: float) -> None:
        super().__init__(name)
        self.capacity = capacity
        self.max_power = max_power
        self.eff_in = eff_in
        self.eff_out = eff_out
        self.initial_soc = initial_soc
        self.variables: dict[str, list[pulp.LpVariable]] = {}

    def _constraints(self, prob: pulp.LpProblem,
                     interval_data: list[dict], T: int) -> None:
        """Create charge/discharge/soc variables and add energy-balance & bound constraints."""
        # Decision variables
        charge = [
            pulp.LpVariable(f"{self.name}_charge_{t}", lowBound=0, upBound=self.max_power)
            for t in range(T)
        ]
        discharge = [
            pulp.LpVariable(f"{self.name}_discharge_{t}", lowBound=0, upBound=self.max_power)
            for t in range(T)
        ]
        soc = [
            pulp.LpVariable(f"{self.name}_soc_{t}", lowBound=0, upBound=self.capacity)
            for t in range(T)
        ]

        # Net power injection: discharge minus charge
        self.net_power = [
            discharge[t] - charge[t]
            for t in range(T)
        ]

        # Energy balance (SoC evolution)
        inv_eff_out = 1.0 / self.eff_out
        prob += (
            soc[0] == self.initial_soc + charge[0] * self.eff_in
            - discharge[0] * inv_eff_out,
            f"{self.name}_energy_balance_0",
        )
        for t in range(1, T):
            prob += (
                soc[t] == soc[t - 1] + charge[t] * self.eff_in
                - discharge[t] * inv_eff_out,
                f"{self.name}_energy_balance_{t}",
            )

        self.variables = {"charge": charge, "discharge": discharge, "soc": soc}

    def _objective(self, prob, interval_data, T):
        """Battery arbitrage: cost = price * (charge - discharge)."""
        charge = self.variables["charge"]
        discharge = self.variables["discharge"]
        return pulp.lpSum(
            interval_data[t]["price"] * (charge[t] - discharge[t])
            for t in range(T)
        )

    def _post_solve(self, prob: pulp.LpProblem,
                    interval_data: list[dict], T: int) -> None:
        """Extract schedule into ``self.results``."""
        schedule = []
        total_discharge = 0.0
        for t in range(T):
            ch = max(0.0, float(pulp.value(self.variables["charge"][t])))
            dch = max(0.0, float(pulp.value(self.variables["discharge"][t])))
            sc = float(pulp.value(self.variables["soc"][t]))
            schedule.append({"charge": ch, "discharge": dch, "soc": sc})
            total_discharge += dch

        self.results = {
            "schedule": schedule,
            "total_cycles": (
                round(total_discharge / self.capacity, 4)
                if self.capacity > 0
                else 0.0
            ),
        }


# ── GeneratorAsset ───────────────────────────────────────────────────────────

class GeneratorAsset(Asset):
    """Conventional generator with min/max output and linear fuel cost.

    Parameters
    ----------
    name : str
        Asset identifier.
    min_output : float
        Minimum stable generation in MW (must-run level).
    max_output : float
        Maximum generation capacity in MW.
    cost_per_mwh : float
        Marginal fuel cost in €/MWh.

    Results (after _post_solve)
    ---------------------------
    power : list[float]
        Per-interval dispatched power in MW.
    total_cost : float
        Sum of fuel cost over all intervals.
    """

    def __init__(self, name: str, min_output: float, max_output: float,
                 cost_per_mwh: float) -> None:
        super().__init__(name)
        self.min_output = min_output
        self.max_output = max_output
        self.cost_per_mwh = cost_per_mwh
        self.variables: dict[str, list[pulp.LpVariable]] = {}

    def _constraints(self, prob: pulp.LpProblem,
                     interval_data: list[dict], T: int) -> None:
        """Create power variable bounded by min/max output."""
        power = [
            pulp.LpVariable(f"{self.name}_p_{t}",
                            lowBound=self.min_output,
                            upBound=self.max_output)
            for t in range(T)
        ]
        self.net_power = list(power)
        self.variables = {"power": power}

    def _objective(self, prob, interval_data, T):
        """Fuel cost term: cost_per_mwh * power."""
        power = self.variables["power"]
        return pulp.lpSum(
            self.cost_per_mwh * power[t]
            for t in range(T)
        )

    def _post_solve(self, prob: pulp.LpProblem,
                    interval_data: list[dict], T: int) -> None:
        """Extract per-interval power dispatch."""
        power_vals = [
            float(pulp.value(self.variables["power"][t]))
            for t in range(T)
        ]
        self.results = {
            "power": power_vals,
            "total_cost": sum(
                self.cost_per_mwh * p for p in power_vals
            ),
        }


# ── SpillAsset ───────────────────────────────────────────────────────────────

class SpillAsset(Asset):
    """Penalty-cost slack supply that guarantees LP feasibility.

    Spill (also called *slack* or *unserved energy*) provides an
    unlimited source of power at a very high penalty price.  When
    the other assets cannot meet demand — e.g. due to capacity
    shortages — the solver uses spill to satisfy the energy balance
    constraint.  Because spill is priced far above normal generation,
    the solver only uses it as a last resort.

    This is a standard technique in energy system modelling to avoid
    infeasible LPs when the physical portfolio has capacity constraints.

    Parameters
    ----------
    name : str
        Asset identifier (typically "Spill" or "Slack").
    penalty : float
        Penalty cost in €/MWh.  Default 10 000 ensures spill is the
        most expensive resource.

    Results (after _post_solve)
    ---------------------------
    spill : list[float]
        Per-interval spill power in MW.
    total_spill : float
        Sum of spill over all intervals.
    """

    def __init__(self, name: str, penalty: float = 10000.0) -> None:
        super().__init__(name)
        self.penalty = penalty
        self.variables: dict[str, list[pulp.LpVariable]] = {}

    def _constraints(self, prob: pulp.LpProblem,
                     interval_data: list[dict], T: int) -> None:
        """Create unbounded spill variable (lower bound = 0, no upper bound)."""
        spill = [
            pulp.LpVariable(f"{self.name}_spill_{t}", lowBound=0)
            for t in range(T)
        ]
        self.net_power = list(spill)
        self.variables = {"spill": spill}

    def _objective(self, prob, interval_data, T):
        """Penalty cost: penalty * spill[t]."""
        spill = self.variables["spill"]
        return pulp.lpSum(
            self.penalty * spill[t]
            for t in range(T)
        )

    def _post_solve(self, prob: pulp.LpProblem,
                    interval_data: list[dict], T: int) -> None:
        """Extract per-interval spill values."""
        spill_vals = [
            float(pulp.value(self.variables["spill"][t]))
            for t in range(T)
        ]
        self.results = {
            "spill": spill_vals,
            "total_spill": sum(spill_vals),
        }


# ── Site builder ─────────────────────────────────────────────────────────────

def build_site(
    assets: list[Asset],
    interval_data: list[dict],
    sense: int = pulp.LpMinimize,
    verbose: bool = False,
) -> pulp.LpProblem:
    """Build and solve a combined site-optimisation LP from assets.

    Each asset contributes decision variables, constraints, and
    objective terms via its lifecycle hooks.  The site-level constraint
    ensures that the sum of net power across all assets equals the
    demand in every interval.

    Parameters
    ----------
    assets : list[Asset]
        Instantiated asset objects (Battery, Generator, Spill, …).
    interval_data : list[dict]
        Per-interval metadata.  Each dict must contain at least
        ``'demand'`` and ``'price'`` keys:

        - ``'demand'`` : float — net demand in MW to meet.
        - ``'price'``  : float — market price in €/MWh (used by BatteryAsset).
    sense : int
        PuLP optimisation sense (default: ``pulp.LpMinimize``).
    verbose : bool
        If True, show CBC solver output.

    Returns
    -------
    pulp.LpProblem
        The solved problem object.  Inspect each asset's ``.results``
        dict for extracted values.
    """
    T = len(interval_data)
    prob = pulp.LpProblem("Site_Optimization", sense)

    # 1. Each asset creates variables and adds its private constraints
    for asset in assets:
        asset._constraints(prob, interval_data, T)

    # 2. Each asset contributes to the global objective
    obj = None
    for asset in assets:
        expr = asset._objective(prob, interval_data, T)
        if expr is not None:
            obj = expr if obj is None else obj + expr
    if obj is not None:
        prob += obj, "total_cost"

    # 3. Site-level energy balance: sum of net power = demand, ∀t
    for t in range(T):
        total_net = pulp.lpSum(asset.net_power[t] for asset in assets)
        prob += (
            total_net == interval_data[t]["demand"],
            f"site_balance_{t}",
        )

    # 4. Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=verbose))

    # 5. Each asset extracts its results
    for asset in assets:
        asset._post_solve(prob, interval_data, T)

    return prob


# ── Demo ─────────────────────────────────────────────────────────────────────

def demo_site() -> dict:
    """Run a 12-period site optimisation with battery, generator, and spill.

    Configures a realistic small microgrid:
    - Battery: 100 MWh / 25 MW, 90 % round-trip, starts empty.
    - Generator: 30–80 MW, €50/MWh fuel cost.
    - Spill: €5 000/MWh penalty (ensures feasibility).

    The demand profile ramps from low overnight to lunchtime peak,
    while prices follow a typical day-ahead pattern.

    Returns
    -------
    dict
        ``status``, ``total_cost``, ``schedule`` (per-interval details).
    """
    battery = BatteryAsset(
        name="BESS",
        capacity=100.0,
        max_power=25.0,
        eff_in=0.95,
        eff_out=0.95,
        initial_soc=0.0,
    )
    generator = GeneratorAsset(
        name="Gen1",
        min_output=30.0,
        max_output=80.0,
        cost_per_mwh=50.0,
    )
    spill = SpillAsset(
        name="Spill",
        penalty=5000.0,
    )

    # 12-period day: overnight → morning ramp → afternoon peak → evening
    interval_data = [
        {"price": 20, "demand": 30},   # 00:00 — cheap, low demand
        {"price": 18, "demand": 25},
        {"price": 15, "demand": 20},
        {"price": 15, "demand": 20},
        {"price": 25, "demand": 35},
        {"price": 45, "demand": 50},   # 05:00 — morning ramp
        {"price": 60, "demand": 65},
        {"price": 80, "demand": 80},
        {"price": 95, "demand": 90},   # 08:00 — peak
        {"price": 100, "demand": 95},
        {"price": 70, "demand": 70},   # 10:00 — evening
        {"price": 40, "demand": 45},
    ]

    prob = build_site([battery, generator, spill], interval_data)

    status = pulp.LpStatus[prob.status]
    if status != "Optimal":
        return {"status": status}

    # Build consolidated schedule
    schedule = []
    for t in range(len(interval_data)):
        period = {
            "t": t,
            "price": interval_data[t]["price"],
            "demand": interval_data[t]["demand"],
            "gen_power": round(generator.results["power"][t], 2),
            "battery_charge": round(battery.results["schedule"][t]["charge"], 2),
            "battery_discharge": round(battery.results["schedule"][t]["discharge"], 2),
            "battery_soc": round(battery.results["schedule"][t]["soc"], 2),
            "spill": round(spill.results["spill"][t], 2),
        }
        schedule.append(period)

    total_cost = round(float(pulp.value(prob.objective)), 2)

    return {
        "status": status,
        "total_cost": total_cost,
        "schedule": schedule,
    }
