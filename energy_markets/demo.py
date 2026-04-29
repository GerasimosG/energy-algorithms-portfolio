#!/usr/bin/env python3
"""
Demo: run all energy market examples — PCR clearing, block orders, market stack.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from energy_markets.pcr_model import PCRModel
from energy_markets.block_orders import run_all, run_exclusive
from energy_markets.market_clearing import demo_clearing, plot_supply_demand_stack


def main():
    print("=" * 65)
    print("  ★ ENERGY MARKETS MODULE — PCR Coupling, Block Orders, Market Clearing")
    print("  ★ Built for Euphemia   Junior Optimization Engineer applications")
    print("=" * 65)

    # 1. Simple PCR Market
    print(f"\n{'─' * 65}")
    print("  1. Simple PCR Market Clearing (3 suppliers, 2 buyers)")
    print(f"{'─' * 65}")
    model = PCRModel("IT")
    model.add_supply("Gas", 80, 100)
    model.add_supply("Coal", 50, 80)
    model.add_supply("Solar", 10, 60)
    model.add_demand("Industry", 150, 120)
    model.add_demand("Residential", 100, 80)
    result = model.solve()
    if result.get("status") != "Optimal":
        print(f"  ⚠ Solve returned {result.get('status')}, skipping report")
    else:
        model.report()

    # 2. PCR with Block Order
    print(f"\n\n{'─' * 65}")
    print("  2. PCR with Block Order (must-run nuclear)")
    print(f"{'─' * 65}")
    model2 = PCRModel("DE")
    model2.add_supply("Gas", 90, 100)
    model2.add_supply("Wind", 5, 80)
    model2.add_supply("Hydro", 30, 50)
    model2.add_demand("Industry", 200, 150)
    model2.add_demand("Residential", 120, 100)
    model2.add_block("NuclearBaseload", 45, 80)
    result2 = model2.solve()
    if result2.get("status") != "Optimal":
        print(f"  ⚠ Solve returned {result2.get('status')}, skipping report")
    else:
        model2.report()

    # 3. Block Order Scenarios
    print(f"\n\n{'─' * 65}")
    print("  3. Block Order Scenarios")
    print(f"{'─' * 65}")
    scenarios = run_all()
    for name, result in scenarios:
        print(f"\n  [{name}]")
        print(f"    Status:  {result['status']}")
        print(f"    Welfare: €{result['welfare']:>10,.2f}")
        print(f"    MCP:     €{result['mcp']:.2f}/MWh")
        for bname, b in result["orders"]["blocks"].items():
            print(f"    Block '{bname}': {'✓ ACCEPTED' if b['accepted'] else '✗ REJECTED'}")

    # 4. Exclusive Block Comparison
    print(f"\n\n{'─' * 65}")
    print("  4. Exclusive Block Comparison (mutually exclusive)")
    print(f"{'─' * 65}")
    excl = run_exclusive()
    result = excl["result"]
    print(f"  Status: {result['status']}")
    print(f"  Welfare: €{result['welfare']:>10,.2f}")
    print(f"  MCP: €{result['mcp']:.2f}/MWh")
    for bname, b in result["orders"]["blocks"].items():
        mark = "✓" if b["accepted"] else "✗"
        print(f"  Block '{bname}': {mark} {'ACCEPTED' if b['accepted'] else 'REJECTED'}")
    print(f"  → Recommended: {excl['recommendation']} plant")

    # 5. Supply/Demand Stack
    print(f"\n\n{'─' * 65}")
    print("  5. Market Clearing — Supply/Demand Stack")
    print(f"{'─' * 65}")
    eq = demo_clearing()
    print(f"  Clearing Price: €{eq['clearing_price']:.2f}/MWh")
    print(f"  Clearing Volume: {eq['clearing_volume']:.0f} MWh")

    plot_dir = os.path.join(os.path.dirname(__file__), "..", "notebooks", "plots")
    os.makedirs(plot_dir, exist_ok=True)
    plot_path = os.path.join(plot_dir, "supply_demand_stack.png")
    plot_supply_demand_stack(
        [
            {"id": "Solar", "price": 5, "quantity": 200},
            {"id": "Wind", "price": 15, "quantity": 150},
            {"id": "Hydro", "price": 35, "quantity": 100},
            {"id": "Gas", "price": 80, "quantity": 200},
            {"id": "Diesel", "price": 120, "quantity": 100},
        ],
        [
            {"id": "Ind_Base", "price": 200, "quantity": 300},
            {"id": "Ind_Peak", "price": 150, "quantity": 200},
            {"id": "Residential", "price": 100, "quantity": 150},
        ],
        plot_path,
    )
    print(f"  Plot saved: {plot_path}")

    print(f"\n{'=' * 65}")
    print("  Energy markets module complete. Euphemia connection documented.")
    print("  This module distinguishes the repo for energy market roles at Euphemia  .")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    main()
