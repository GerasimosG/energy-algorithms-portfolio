"""
PCR (Pan-European Coupling) Market Clearing Model.

Simplified version of the Euphemia social welfare maximization LP.
Supports supply/demand curves and block orders (all-or-nothing).

Reference: EUPHEMIA Public Description — PCR Market Coupling Algorithm
https://www.epexspot.com/en/euphemia
"""

import pulp


class PCRModel:
    """
    Simplified PCR market clearing model.

    Maximizes social welfare:
        Σ (demand_price × qty_accepted) - Σ (supply_price × qty_accepted)

    Subject to:
        - Supply ≤ available quantity
        - Demand ≤ bid quantity
        - Supply + block_output ≥ Demand (energy balance)
        - Block orders are binary (all-or-nothing)
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

    def add_block(self, oid: str, price: float, qty: float) -> None:
        self.block_orders.append({"id": oid, "price": price, "quantity": qty})

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
        welfare = (
            pulp.lpSum(self.demand_orders[i]["price"] * self.demand_orders[i]["quantity"] * d_vars[i]
                       for i in range(Nd))
            - pulp.lpSum(self.supply_orders[i]["price"] * self.supply_orders[i]["quantity"] * s_vars[i]
                         for i in range(Ns))
            - pulp.lpSum(self.block_orders[i]["price"] * self.block_orders[i]["quantity"] * b_vars[i]
                         for i in range(Nb))
        )
        prob += welfare

        # Energy balance: supply + block ≥ demand
        total_supply = pulp.lpSum(
            self.supply_orders[i]["quantity"] * s_vars[i] for i in range(Ns))
        total_block = pulp.lpSum(
            self.block_orders[i]["quantity"] * b_vars[i] for i in range(Nb))
        total_demand = pulp.lpSum(
            self.demand_orders[i]["quantity"] * d_vars[i] for i in range(Nd))
        prob += total_supply + total_block >= total_demand

        prob.solve(pulp.PULP_CBC_CMD(msg=verbose))

        status = pulp.LpStatus[prob.status]
        if status != "Optimal":
            return {"status": status}

        accepted_supply = [self.supply_orders[i]
                           for i in range(Ns) if pulp.value(s_vars[i]) > 0.001]
        mcp = max(o["price"] for o in accepted_supply) if accepted_supply else 0.0
        traded = float(pulp.value(total_demand))

        orders = {
            "supply": {
                self.supply_orders[i]["id"]: {
                    "price": self.supply_orders[i]["price"],
                    "qty": self.supply_orders[i]["quantity"],
                    "filled_frac": float(pulp.value(s_vars[i])),
                    "filled_qty": self.supply_orders[i]["quantity"] * float(pulp.value(s_vars[i])),
                }
                for i in range(Ns)
            },
            "demand": {
                self.demand_orders[i]["id"]: {
                    "price": self.demand_orders[i]["price"],
                    "qty": self.demand_orders[i]["quantity"],
                    "filled_frac": float(pulp.value(d_vars[i])),
                    "filled_qty": self.demand_orders[i]["quantity"] * float(pulp.value(d_vars[i])),
                }
                for i in range(Nd)
            },
            "blocks": {
                self.block_orders[i]["id"]: {
                    "price": self.block_orders[i]["price"],
                    "qty": self.block_orders[i]["quantity"],
                    "accepted": bool(pulp.value(b_vars[i]) > 0.5),
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

    def report(self) -> None:
        """Pretty-print results."""
        if not self._result:
            print("No result. Run solve() first.")
            return
        r = self._result
        print(f"\n  Area: {self.area}")
        print(f"  Status: {r['status']}")
        print(f"  Market Clearing Price: €{r['mcp']:.2f}/MWh")
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
                    print(f"    {mark} {oid}: €{o['price']:.1f} × {o['qty']:.0f} MWh")
                else:
                    mark = "✓" if o["filled_frac"] > 0 else "✗"
                    print(f"    {mark} {oid}: €{o['price']:.1f} × {o['filled_qty']:.0f}/{o['qty']:.0f} MWh")
