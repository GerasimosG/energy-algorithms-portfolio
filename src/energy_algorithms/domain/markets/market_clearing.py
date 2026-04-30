"""
Single-zonal market clearing: find equilibrium price and volume
from supply and demand step functions.

Produces a supply/demand stack visualization.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def find_equilibrium(
    supply_orders: list[dict],
    demand_orders: list[dict],
) -> dict:
    """
    Find market equilibrium from supply and demand step functions.
    Returns clearing price, volume.
    """
    # Build cumulative supply (merit order: ascending price)
    sup_sorted = sorted(supply_orders, key=lambda o: o["price"])
    sup_cum_qty = np.cumsum([o["quantity"] for o in sup_sorted])
    sup_prices = np.array([o["price"] for o in sup_sorted])

    # Build cumulative demand (descending price)
    dem_sorted = sorted(demand_orders, key=lambda o: -o["price"])
    dem_cum_qty = np.cumsum([o["quantity"] for o in dem_sorted])
    dem_prices = np.array([o["price"] for o in dem_sorted])

    # Find intersection via interpolation on combined grid
    q_max = min(sup_cum_qty[-1], dem_cum_qty[-1])
    q_grid = np.linspace(0, q_max, 2000)

    sup_at_q = np.interp(q_grid, np.insert(sup_cum_qty, 0, 0),
                         np.insert(sup_prices, 0, 0), left=0, right=sup_prices[-1])
    dem_at_q = np.interp(q_grid, np.insert(dem_cum_qty, 0, 0),
                         np.insert(dem_prices, 0, dem_prices[0]),
                         left=dem_prices[0], right=dem_prices[-1])

    diff = sup_at_q - dem_at_q
    cross = np.where(np.diff(np.sign(diff)))[0]

    if len(cross) > 0:
        idx = cross[0]
        clearing_price = float((sup_at_q[idx] + dem_at_q[idx]) / 2)
        clearing_volume = float(q_grid[idx])
    elif np.all(sup_at_q <= dem_at_q):
        # All supply is cheaper than demand — equilibrium at total demand volume.
        # The marginal price is the supply price at the total demand quantity,
        # i.e. the last (most expensive) unit needed to satisfy demand.
        total_demand_qty = float(dem_cum_qty[-1])
        clearing_volume = total_demand_qty
        # Find the supply price corresponding to this quantity
        clearing_price = float(np.interp(
            total_demand_qty,
            np.insert(sup_cum_qty, 0, 0),
            np.insert(sup_prices, 0, 0),
            left=0, right=sup_prices[-1]
        ))
    else:
        clearing_price = float(dem_prices[0])
        clearing_volume = 0.0

    return {
        "clearing_price": clearing_price,
        "clearing_volume": clearing_volume,
        "supply_prices": sup_prices,
        "supply_cum_qty": sup_cum_qty,
        "demand_prices": dem_prices,
        "demand_cum_qty": dem_cum_qty,
    }


def plot_supply_demand_stack(
    supply_orders: list[dict],
    demand_orders: list[dict],
    save_path: str,
) -> str:
    """Plot supply and demand stack with equilibrium."""
    eq = find_equilibrium(supply_orders, demand_orders)

    fig, ax = plt.subplots(figsize=(10, 7))

    # Supply stack — step plot from cumulative quantities
    sup_x = np.insert(eq["supply_cum_qty"], 0, 0)
    sup_y = np.insert(eq["supply_prices"], 0, 0)
    ax.step(sup_x, sup_y, where="post", linewidth=2, color="forestgreen",
            label="Supply (merit order)")

    # Demand stack
    dem_x = np.insert(eq["demand_cum_qty"], 0, 0)
    dem_y = np.full(len(dem_x), eq["demand_prices"][0])
    dem_y[1:] = eq["demand_prices"]
    ax.step(dem_x, dem_y, where="post", linewidth=2, color="coral",
            label="Demand (bid price)")

    # Equilibrium lines
    cp = eq["clearing_price"]
    cv = eq["clearing_volume"]
    ax.axhline(y=cp, color="red", linestyle="--", alpha=0.7,
               label=f"Clearing Price: €{cp:.0f}/MWh")
    ax.axvline(x=cv, color="red", linestyle=":", alpha=0.5,
               label=f"Volume: {cv:.0f} MWh")

    # Shading for consumer and producer surplus
    # Producer surplus: area between supply curve and price line (0 to cv)
    ax.fill_between(sup_x[:len(sup_x)-1], sup_y[:len(sup_x)-1], cp,
                    where=(cp >= sup_y[:len(sup_x)-1]),
                    step="post", alpha=0.08, color="forestgreen",
                    label="Producer surplus")
    # Consumer surplus: area between demand curve and price line (0 to cv)
    ax.fill_between(dem_x[:len(dem_x)-1], cp, dem_y[:len(dem_x)-1],
                    where=(dem_y[:len(dem_x)-1] >= cp),
                    step="post", alpha=0.08, color="coral",
                    label="Consumer surplus")

    ax.set_xlabel("Quantity (MWh)", fontsize=11)
    ax.set_ylabel("Price (€/MWh)", fontsize=11)
    ax.set_title("Electricity Market — Supply/Demand Stack with Equilibrium",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, max(eq["supply_cum_qty"][-1], eq["demand_cum_qty"][-1]) * 1.05)
    ax.set_ylim(0, max(max(eq["supply_prices"]), max(eq["demand_prices"])) * 1.15)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    return save_path


def demo_clearing() -> dict:
    """Run a 5-supplier × 3-buyer market clearing example."""
    supply = [
        {"id": "Solar", "price": 5, "quantity": 200},
        {"id": "Wind", "price": 15, "quantity": 150},
        {"id": "Hydro", "price": 35, "quantity": 100},
        {"id": "Gas", "price": 80, "quantity": 200},
        {"id": "Diesel", "price": 120, "quantity": 100},
    ]
    demand = [
        {"id": "Ind_Base", "price": 200, "quantity": 300},
        {"id": "Ind_Peak", "price": 150, "quantity": 200},
        {"id": "Residential", "price": 100, "quantity": 150},
    ]
    return find_equilibrium(supply, demand)
