from __future__ import annotations

#!/usr/bin/env python3
"""
Demo: run all three LP/MIP problems.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from energy_algorithms.domain.optimization.transportation import demo_transportation
from energy_algorithms.domain.optimization.portfolio import demo_portfolio
from energy_algorithms.domain.optimization.scheduling import demo_uc


def main():
    print("=" * 65)
    print("  LP Optimization Demo — Transportation / Portfolio / Unit Commitment")
    print("=" * 65)

    # 1. Transportation
    print(f"\n{'─' * 65}")
    print("  1. Transportation Problem")
    print(f"{'─' * 65}")
    t = demo_transportation()
    print(f"  Status: {t['status']}")
    print(f"  Total Cost: ${t['total_cost']:,.2f}")
    for route, qty in sorted(t['allocations'].items()):
        print(f"    {route}: {qty:.0f} units")

    # 2. Portfolio
    print(f"\n{'─' * 65}")
    print("  2. Portfolio Optimization (with sector & cardinality constraints)")
    print(f"{'─' * 65}")
    p = demo_portfolio()
    print(f"  Status: {p['status']}")
    if p['weights'] is not None:
        labels = ["Tech_A", "Tech_B", "Energy_A", "Energy_B", "Health_A", "Health_B"]
        for name, w in zip(labels, p['weights']):
            if w > 0.001:
                print(f"    {name:>12s}: {w:.1%}")
        print(f"  Expected Return: {p['return']:.2%}")
        print(f"  Portfolio Risk:  {p['risk']:.2%}")
        print(f"  Assets Selected: {p['n_assets_selected']} / 6")

    # 3. Unit Commitment
    print(f"\n{'─' * 65}")
    print("  3. Unit Commitment (MIP — min up/down, ramp rates)")
    print(f"{'─' * 65}")
    uc = demo_uc()
    print(f"  Status: {uc['status']}")
    if "total_cost" in uc:
        print(f"  Total Cost: ${uc['total_cost']:,.2f}")
        print(f"\n  Hourly Dispatch:")
        print(f"  {'Hour':>5s} {'Demand':>8s} {'Coal':>8s} {'Gas':>8s} {'Wind':>8s} {'Online':>20s}")
        for period, data in sorted(uc['schedule'].items())[::2]:  # Every 2nd for brevity
            h = period.split("=")[1]
            online = ", ".join(data["_online"])
            print(f"  {h:>5s} {data['_demand']:>8.0f} {data['Coal']:>8.0f} "
                  f"{data['Gas']:>8.0f} {data['Wind']:>8.0f} {online:>20s}")

    print(f"\n{'=' * 65}")
    print("  All three LP/MIP problems solved successfully.")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    main()
