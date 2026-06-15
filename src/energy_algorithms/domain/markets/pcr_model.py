"""PCR (Pan-European Coupling) Market Clearing Model.

Simplified version of the Euphemia social welfare maximization LP.
Supports supply/demand curves and block orders (all-or-nothing).

Reference: EUPHEMIA Public Description — PCR Market Coupling Algorithm
https://www.epexspot.com/en/euphemia
"""
from __future__ import annotations

import pulp

from energy_algorithms.domain.markets.coupling_utils import compute_social_welfare
from energy_algorithms.infrastructure.solver_config import solve_model

# ---------------------------------------------------------------------------
# Tolerance: minimum fill fraction for an order to be considered "accepted"
# ---------------------------------------------------------------------------
ACCEPTANCE_TOLERANCE = 0.001


class PCRModel:
    """
    Simplified PCR market clearing model.

    Maximizes social welfare:
        Σ (demand_price × qty_accepted) - Σ (supply_price × qty_accepted)

    Subject to:
        - Supply ≤ available quantity
        - Demand ≤ bid quantity
        - Supply + block_output == Demand (energy balance)
        - Block orders are binary (all-or-nothing)
        - Linked blocks (same non-None group) share the same binary value
        - Exclusive blocks (group='excl_*'): at most one accepted per group
    """

    def __init__(self, area: str = "IT"):
        self.area = area
        self.supply_orders: list[dict] = []
        self.demand_orders: list[dict] = []
        self.block_orders: list[dict] = []
        self._result = None

    def add_supply(self, oid: str, price: float, qty: float) -> None:
        self.supply_orders.append({"id": oid, "price": price, "quantity": qty})

    def add_demand(self, oid: str, price: float, qty: float) -> None:
        self.demand_orders.append({"id": oid, "price": price, "quantity": qty})

    def add_block(self, oid: str, price: float, qty: float, group: str = None) -> None:
        self.block_orders.append({"id": oid, "price": price, "quantity": qty, "group": group})

    def solve(self, verbose: bool = False) -> dict:
        Ns = len(self.supply_orders)
        Nd = len(self.demand_orders)
        Nb = len(self.block_orders)

        prob = pulp.LpProblem(f"PCR_{self.area}", pulp.LpMaximize)

        # Continuous acceptance [0,1]
        s_vars = {i: pulp.LpVariable(f"s_{i}", 0, 1) for i in range(Ns)}
        d_vars = {i: pulp.LpVariable(f"d_{i}", 0, 1) for i in range(Nd)}
        # Binary for block orders
        b_vars = {i: pulp.LpVariable(f"b_{i}", cat="Binary") for i in range(Nb)}

        # Objective: social welfare
        zone_for_utils = {
            "supply": [
                {"price": o["price"], "qty": o["quantity"]}
                for o in self.supply_orders
            ],
            "demand": [
                {"price": o["price"], "qty": o["quantity"]}
                for o in self.demand_orders
            ],
        }
        welfare = compute_social_welfare(zone_for_utils, s_vars, d_vars)
        welfare -= pulp.lpSum(self.block_orders[i]["price"] * self.block_orders[i]["quantity"] * b_vars[i]
                              for i in range(Nb))
        prob += welfare

        # Energy balance: supply + block == demand
        total_supply = pulp.lpSum(
            self.supply_orders[i]["quantity"] * s_vars[i] for i in range(Ns))
        total_block = pulp.lpSum(
            self.block_orders[i]["quantity"] * b_vars[i] for i in range(Nb))
        total_demand = pulp.lpSum(
            self.demand_orders[i]["quantity"] * d_vars[i] for i in range(Nd))
        prob += total_supply + total_block == total_demand

        # Block group constraints
        groups: dict[str, list[int]] = {}
        for i, block in enumerate(self.block_orders):
            g = block.get("group")
            if g is not None:
                groups.setdefault(g, []).append(i)
        for g, indices in groups.items():
            if g.startswith("excl_"):
                # Exclusive group: at most one block can be accepted
                prob += pulp.lpSum(b_vars[i] for i in indices) <= 1
            else:
                # Linked group: all blocks must have the same binary value
                anchor = indices[0]
                for i in indices[1:]:
                    prob += b_vars[i] == b_vars[anchor]

        result = solve_model(prob, msg=verbose)

        status = result["status"]
        if status != "Optimal":
            return {"status": status}

        accepted_supply = [self.supply_orders[i]
                           for i in range(Ns) if (pulp.value(s_vars[i]) or 0) > ACCEPTANCE_TOLERANCE]
        accepted_blocks = [self.block_orders[i]
                           for i in range(Nb) if (pulp.value(b_vars[i]) or 0) > 0.5]
        mcp_prices = [o["price"] for o in accepted_supply] + [b["price"] for b in accepted_blocks]
        mcp = max(mcp_prices) if mcp_prices else 0.0
        traded = float(pulp.value(total_demand))

        orders = {
            "supply": {
                self.supply_orders[i]["id"]: {
                    "price": self.supply_orders[i]["price"],
                    "qty": self.supply_orders[i]["quantity"],
                    "filled_frac": float(pulp.value(s_vars[i]) or 0.0),
                    "filled_qty": self.supply_orders[i]["quantity"] * float(pulp.value(s_vars[i]) or 0.0),
                }
                for i in range(Ns)
            },
            "demand": {
                self.demand_orders[i]["id"]: {
                    "price": self.demand_orders[i]["price"],
                    "qty": self.demand_orders[i]["quantity"],
                    "filled_frac": float(pulp.value(d_vars[i]) or 0.0),
                    "filled_qty": self.demand_orders[i]["quantity"] * float(pulp.value(d_vars[i]) or 0.0),
                }
                for i in range(Nd)
            },
            "blocks": {
                self.block_orders[i]["id"]: {
                    "price": self.block_orders[i]["price"],
                    "qty": self.block_orders[i]["quantity"],
                    "accepted": bool((pulp.value(b_vars[i]) or 0) > 0.5),
                    "group": self.block_orders[i].get("group"),
                }
                for i in range(Nb)
            },
        }

        self._result = {
            "status": status,
            "welfare": float(pulp.value(welfare)),
            "mcp": mcp,
            "traded": traded,
            "orders": orders,
        }
        return self._result

    def solve_with_ip_pricing(self, verbose: bool = False) -> dict:
        """Solve with IP (Integer Programming) pricing for block orders.

        Simplified IP pricing that handles non-convexities from block orders.
        First solves the welfare-maximizing MIP, then computes the uniform
        price that minimizes make-whole payments while preserving the optimal
        dispatch.

        Real Euphemia IP pricing is significantly more complex — this
        implements the core concept of minimizing make-whole payments.

        Parameters
        ----------
        verbose : bool
            Pass through to PuLP solver.

        Returns
        -------
        dict
            Same keys as solve() plus:
            - pricing_method : 'ip'
            - ip_price : float — IP uniform clearing price
            - mcp : float — marginal clearing price (for comparison)
            - make_whole_payments : dict — block_id -> {'type': str, 'payment': float}
        """
        # 1. Solve the welfare-maximizing MIP (same as solve())
        result = self.solve(verbose=verbose)
        if result["status"] != "Optimal":
            result["pricing_method"] = "ip"
            self._result = result
            return result

        mcp = result["mcp"]

        # If there are no block orders, IP pricing is degenerate — use MCP
        if not self.block_orders:
            result["pricing_method"] = "ip"
            result["ip_price"] = mcp
            result["make_whole_payments"] = {}
            self._result = result
            return result

        # 2. Determine the feasible IP price range.
        #    The IP price must be >= all accepted continuous supply prices
        #    (so non-block suppliers remain profitable) and <= all accepted
        #    demand bid prices (so demand is not priced out).
        acc_supply_prices = [
            o["price"] for o in result["orders"]["supply"].values()
            if o["filled_frac"] > ACCEPTANCE_TOLERANCE
        ]
        acc_demand_prices = [
            o["price"] for o in result["orders"]["demand"].values()
            if o["filled_frac"] > ACCEPTANCE_TOLERANCE
        ]
        lower_bound = max(acc_supply_prices) if acc_supply_prices else 0.0
        upper_bound = min(acc_demand_prices) if acc_demand_prices else float("inf")

        # 3. Build candidate IP prices from all relevant price points.
        candidates: set[float] = {lower_bound, upper_bound, mcp}
        candidates.update(acc_supply_prices)
        candidates.update(acc_demand_prices)
        for binfo in result["orders"]["blocks"].values():
            candidates.add(binfo["price"])
        candidates = sorted(
            p for p in candidates if lower_bound - 1e-9 <= p <= upper_bound + 1e-9
        )

        # 4. Find the IP price that minimizes make-whole payments.
        best_ip = mcp
        best_mwp = float("inf")

        for ip in candidates:
            mwp = 0.0
            for bid, binfo in result["orders"]["blocks"].items():
                if binfo["accepted"] and binfo["price"] > ip + 1e-9:
                    # Paradoxically accepted block: gets IP but offered higher
                    mwp += (binfo["price"] - ip) * binfo["qty"]
                elif not binfo["accepted"] and binfo["price"] < ip - 1e-9:
                    # Paradoxically rejected block: would be profitable at IP
                    mwp += (ip - binfo["price"]) * binfo["qty"]
            if mwp < best_mwp - 1e-9:
                best_mwp = mwp
                best_ip = ip

        # 5. Compute make-whole payments at the optimal IP price.
        make_whole: dict[str, dict] = {}
        for bid, binfo in result["orders"]["blocks"].items():
            if binfo["accepted"] and binfo["price"] > best_ip + 1e-9:
                mwp = (binfo["price"] - best_ip) * binfo["qty"]
                make_whole[bid] = {
                    "type": "paradoxically_accepted",
                    "payment": round(mwp, 2),
                }
            elif not binfo["accepted"] and binfo["price"] < best_ip - 1e-9:
                mwp = (best_ip - binfo["price"]) * binfo["qty"]
                make_whole[bid] = {
                    "type": "paradoxically_rejected",
                    "payment": round(mwp, 2),
                }

        result["pricing_method"] = "ip"
        result["ip_price"] = best_ip
        result["make_whole_payments"] = make_whole
        self._result = result
        return result

    def report(self) -> None:
        """Pretty-print results."""
        if not self._result:
            print("No result. Run solve() first.")
            return
        r = self._result
        print(f"\n  Area: {self.area}")
        print(f"  Status: {r['status']}")
        print(f"  Market Clearing Price: €{r['mcp']:.2f}/MWh")
        if r.get("pricing_method") == "ip":
            print(f"  IP Price:              €{r['ip_price']:.2f}/MWh")
            mwp = r.get("make_whole_payments", {})
            if mwp:
                print("  Make-Whole Payments:")
                for bid, info in mwp.items():
                    print(f"    {bid}: €{info['payment']:,.2f} ({info['type']})")
        print(f"  Total Traded: {r['traded']:.1f} MWh")
        print(f"  Social Welfare: €{r['welfare']:>12,.2f}")

        for kind in ("supply", "demand", "blocks"):
            items = r["orders"][kind]
            if not items:
                continue
            print(f"\n  {kind.upper()}:")
            for oid, o in items.items():
                if kind == "blocks":
                    mark = "✓" if o["accepted"] else "✗"
                    group_info = f" [group: {o['group']}]" if o.get("group") else ""
                    print(f"    {mark} {oid}: €{o['price']:.1f} × {o['qty']:.0f} MWh{group_info}")
                else:
                    mark = "✓" if o["filled_frac"] > 0 else "✗"
                    print(f"    {mark} {oid}: €{o['price']:.1f} × {o['filled_qty']:.0f}/{o['qty']:.0f} MWh")
