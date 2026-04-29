#!/usr/bin/env python3
"""Demo: ENTSO-E energy data pipeline.

Showcases day-ahead price analysis and generation mix breakdown
using demo data (no API key required). For live data, see the
EntsoeClient class in fetcher.py.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from energy_data.fetcher import fetch_demo_day_ahead, fetch_demo_generation_mix


def demo_energy_data() -> dict:
    """Run the energy data pipeline demo.

    Demonstrates:
    - Day-ahead price profile with peak/off-peak analysis
    - Generation mix breakdown by source type
    - Summary statistics

    Returns
    -------
    dict with prices, generation, and summary stats.
    """
    print("=" * 65)
    print("  ENTSO-E Energy Data Pipeline — Demo")
    print("=" * 65)

    # ── Day-ahead prices ─────────────────────────────────────────
    prices = fetch_demo_day_ahead()
    print(f"\n  Day-Ahead Prices — {prices['area']} ({prices['date']})")
    print(f"  Avg: €{prices['avg_price']}/MWh | "
          f"Min: €{prices['min_price']} | Max: €{prices['max_price']}")
    print(f"  {'Hour':>5} {'Price':>8}")
    print(f"  {'─'*5} {'─'*8}")
    for p in prices["prices"]:
        bar = "█" * int(p["price_eur_mwh"] / 5)
        print(f"  {p['hour']:>5} €{p['price_eur_mwh']:>7.1f}  {bar}")

    # ── Generation mix ───────────────────────────────────────────
    gen = fetch_demo_generation_mix()
    print(f"\n  Generation Mix — {gen['area']} ({gen['date']})")
    print(f"  Total: {gen['total_mw']} MW")
    print(f"  {'Source':<25} {'MW':>8} {'Share':>8}")
    print(f"  {'─'*25} {'─'*8} {'─'*8}")
    for g in gen["generation"]:
        share = g["mw"] / gen["total_mw"] * 100 if gen["total_mw"] > 0 else 0
        print(f"  {g['type']:<25} {g['mw']:>8.0f} {share:>7.1f}%")

    # ── Summary ──────────────────────────────────────────────────
    print(f"\n  ── Key Metrics ──")
    print(f"  Day-ahead avg price:  €{prices['avg_price']}/MWh")
    print(f"  Peak price (18:00):   €{prices['prices'][17]['price_eur_mwh']}/MWh")
    print(f"  Off-peak min (04:00): €{prices['prices'][3]['price_eur_mwh']}/MWh")
    print(f"  Renewable share:      {sum(g['mw'] for g in gen['generation'] if g['psr_code'] in ('B16','B18','B19','B01','B11'))/gen['total_mw']*100:.0f}%")
    print(f"  Nuclear share:        {gen['generation'][0]['mw']/gen['total_mw']*100:.0f}%")

    print(f"\n{'=' * 65}")
    print("  Note: Demo data — use EntsoeClient(api_key=...) for live ENTSO-E data")
    print(f"{'=' * 65}")

    return {"prices": prices, "generation": gen}


if __name__ == "__main__":
    demo_energy_data()
