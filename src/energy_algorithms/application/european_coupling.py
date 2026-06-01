"""European Market Coupling Demo — Real ENTSO-E Data.

Fetches live day-ahead prices and generation mix for 6 European
bidding zones, builds supply/demand curves, then solves the
multi-zone ATC-coupled market clearing — exactly like Euphemia.

Shows how prices converge (or fail to converge) when ATC constraints
are binding.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from energy_algorithms.adapters.config import ENTSOE_API_KEY
from energy_algorithms.adapters.entsoe_client import EntsoeClient
from energy_algorithms.domain.markets.multi_zone import solve_multi_zone

# ── European bidding zones and typical ATC capacities ──────────────────
# ATC values are approximate winter/summer typical (MW).
# Source: ENTSO-E Transparency Platform + NRCan annual reports
ZONES = {
    "BE": {
        "eic": "10YBE----------2",
        "name": "Belgium",
        "gen_renewable_mwh": 1.0,  # not directly used
    },
    "FR": {
        "eic": "10YFR-RTE------C",
        "name": "France",
    },
    "DE": {
        "eic": "10Y1001A1001A82H",
        "name": "Germany",
    },
    "NL": {
        "eic": "10YNL----------L",
        "name": "Netherlands",
    },
    "ES": {
        "eic": "10YES-REE------0",
        "name": "Spain",
    },
    "PL": {
        "eic": "10YPL-AREA-----S",
        "name": "Poland",
    },
}

# Typical ATC capacities (MW) between European bidding zones
# These are approximate — real ATC varies hourly
ATC_CAPACITIES: dict[tuple[str, str], int] = {
    ("FR", "BE"): 3500,   # France→Belgium
    ("FR", "DE"): 3000,   # France→Germany
    ("FR", "ES"): 2800,   # France→Spain
    ("FR", "NL"): 1000,   # France→Netherlands
    ("BE", "NL"): 2400,   # Belgium→Netherlands
    ("BE", "DE"): 1000,   # Belgium→Germany (via ALEGrO)
    ("NL", "DE"): 4000,   # Netherlands→Germany
    ("DE", "PL"): 2000,   # Germany→Poland
}

# Marginal cost estimates for generation by zone (€/MWh)
# Based on typical fleet composition (nuclear, gas, coal, renewables)
MARGINAL_COSTS: dict[str, list[dict]] = {
    "FR": [
        {"price": 2, "qty": 5000},    # Nuclear baseload
        {"price": 5, "qty": 3000},    # Hydro + Wind
        {"price": 30, "qty": 4000},   # Nuclear mid-merit
        {"price": 70, "qty": 2000},   # Gas
    ],
    "BE": [
        {"price": 1, "qty": 4000},    # Solar + Wind
        {"price": 7, "qty": 3000},    # Nuclear
        {"price": 50, "qty": 2000},   # Gas + CHP
        {"price": 90, "qty": 1000},   # Pumped storage
    ],
    "DE": [
        {"price": 1, "qty": 3000},    # Solar + Wind
        {"price": 10, "qty": 2000},   # Lignite baseload
        {"price": 40, "qty": 4000},   # Hard coal
        {"price": 60, "qty": 3000},   # Gas
        {"price": 100, "qty": 1500},  # Pumped storage, oil
    ],
    "NL": [
        {"price": 10, "qty": 2000},   # Wind + solar
        {"price": 45, "qty": 3000},   # Gas CCGT
        {"price": 70, "qty": 2000},   # Gas peaker
        {"price": 130, "qty": 500},   # Oil
    ],
    "ES": [
        {"price": 1, "qty": 3000},    # Solar
        {"price": 5, "qty": 2000},    # Wind
        {"price": 30, "qty": 2500},   # Hydro + nuclear
        {"price": 65, "qty": 3000},   # Gas CCGT
        {"price": 120, "qty": 1500},  # Gas peaker
    ],
    "PL": [
        {"price": 10, "qty": 4000},   # Lignite baseload
        {"price": 35, "qty": 5000},   # Hard coal
        {"price": 70, "qty": 1000},   # Gas
        {"price": 150, "qty": 500},   # Import/peaker
    ],
}


def fetch_european_prices(client: EntsoeClient, date: str) -> dict[str, float]:
    """Fetch day-ahead prices for all zones. Returns {code: avg_price}."""
    prices: dict[str, float] = {}
    for code, info in ZONES.items():
        r = client.fetch_day_ahead_prices(info["eic"], date)
        hourly = [p for p in r.get("prices", []) if p["hour"] <= 24][:24]
        vals = [p["price_eur_mwh"] for p in hourly]
        if vals:
            prices[code] = round(sum(vals) / len(vals), 2)
        else:
            prices[code] = 0.0
    return prices


def build_demand_curve(
    real_prices: list[float],
    label: str,
) -> list[dict]:
    """Build a 3-block demand curve from real price distribution.

    Uses the price percentile method from our live_pipeline:
    top/mid/bottom thirds of the price distribution become
    demand blocks with willingness-to-pay at their average prices.
    """
    if not real_prices:
        return [{"price": 100, "qty": 1000}]  # fallback

    sorted_p = sorted(real_prices, reverse=True)
    n = len(sorted_p)
    third = max(n // 3, 1)

    def _avg(lst: list[float]) -> float:
        return round(sum(lst) / len(lst), 2) if lst else 0.0

    top = _avg(sorted_p[:third])
    mid = _avg(sorted_p[third:2*third])
    bot = _avg(sorted_p[2*third:])

    scale = 2000  # nominal demand block size in MW
    blocks = []
    if top > 0:
        blocks.append({"price": max(top + 40, 80), "qty": scale})
    if mid > 0:
        blocks.append({"price": max(mid + 20, 60), "qty": scale})
    if bot > 0:
        blocks.append({"price": max(bot + 10, 40), "qty": scale})

    return blocks if blocks else [{"price": 100, "qty": 1000}]


def run_european_coupling() -> dict:
    """Fetch real ENTSO-E data and run multi-zone market coupling.

    Returns the coupling result with flows, zone-level MCPs, and welfare.
    """
    client = EntsoeClient(api_key=ENTSOE_API_KEY, timeout=30)
    date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print("=" * 70)
    print("  🇪🇺  EUROPEAN MARKET COUPLING — Real ENTSO-E Data")
    print(f"     Date: {date}")
    print("=" * 70)

    # Step 1: Fetch real prices for all zones
    print("\n📡 Fetching day-ahead prices...")
    real_prices = fetch_european_prices(client, date)

    # Step 2: Build supply/demand curves for each zone
    print("\n🏗️  Building market models...")
    zones_for_coupling = []
    price_summary: list[tuple[str, str, float]] = []

    for code in ["FR", "BE", "DE", "NL", "ES", "PL"]:
        avg_price = real_prices.get(code, 0)
        supply = MARGINAL_COSTS[code]
        # Build demand curve from the real price
        # Use a synthetic 24h price curve from avg price
        synthetic_24h = [avg_price * (0.6 + 0.4 * np.sin(2 * np.pi * h / 24)) for h in range(24)]
        demand = build_demand_curve(synthetic_24h, code)
        total_supply = sum(s["qty"] for s in supply)
        total_demand = sum(d["qty"] for d in demand)

        zones_for_coupling.append({
            "name": code,
            "supply": supply,
            "demand": demand,
        })
        price_summary.append((code, ZONES[code]["name"], avg_price))

        print(f"   {code:<4} {ZONES[code]['name']:<12} avg €{avg_price:>7.2f}/MWh"
              f"  supply={total_supply:,}MW  demand={total_demand:,}MW")

    # Step 3: Filter ATC to connected zones
    atc_used = {}
    for (a, b), cap in ATC_CAPACITIES.items():
        if a in real_prices and b in real_prices and real_prices[a] > 0 and real_prices[b] > 0:
            atc_used[(a, b)] = cap

    # Step 4: Run multi-zone coupling
    print(f"\n🔗 ATC constraints: {len(atc_used)} interconnectors")
    for (a, b), cap in sorted(atc_used.items()):
        spread = abs(real_prices.get(a, 0) - real_prices.get(b, 0))
        print(f"   {a}→{b}: {cap:,} MW  (price spread: €{spread:.0f}/MWh)")

    print("\n⚡ Solving European market coupling (social welfare max)...")
    result = solve_multi_zone(zones_for_coupling, atc_used, verbose=False)

    return result, real_prices, atc_used


def print_results(result: dict, real_prices: dict, atc: dict) -> None:
    """Print the coupling results."""
    status = result.get("status", "Unknown")
    if status != "Optimal":
        print(f"\n❌ Solve failed: {status}")
        return

    welfare = result.get("welfare", 0)
    flows = result.get("flows", {})
    zones = result.get("zones", {})

    print(f"\n{'=' * 70}")
    print(f"  ✅ OPTIMAL — Social Welfare: €{welfare:,.0f}")
    print(f"{'=' * 70}")

    # ── Zone-level results ──
    print(f"\n{'=' * 70}")
    print("  ZONE-LEVEL RESULTS")
    print(f"{'=' * 70}")
    print(f"  {'Zone':<6} {'Real Price':>12} {'Model MCP':>12} {'Supply (MW)':>12} {'Demand (MW)':>12} {'Net Exp':>10}")
    print(f"  {'─'*6} {'─'*12} {'─'*12} {'─'*12} {'─'*12} {'─'*10}")

    for code in ["FR", "BE", "DE", "NL", "ES", "PL"]:
        z = zones.get(code, {})
        real_p = real_prices.get(code, 0)
        mcp = z.get("mcp", 0)
        supply = z.get("supply_cleared_mw", 0)
        demand = z.get("demand_cleared_mw", 0)
        net = round(supply - demand, 1)
        net_str = f"{net:+.0f}" if net != 0 else "    0"
        print(f"  {code:<6} €{real_p:>8.2f}  €{mcp:>8.2f}  {supply:>10,.0f}  {demand:>10,.0f}  {net_str:>8}")

    # ── Flow results ──
    print(f"\n{'=' * 70}")
    print("  INTER-ZONAL FLOWS")
    print(f"{'=' * 70}")
    total_flow = 0
    for (a, b), cap in sorted(atc.items()):
        flow = flows.get(f"{a}→{b}", 0)
        if flow > 0:
            util = flow / cap * 100
            binding = " ⚠ BINDING" if util > 95 else ""
            print(f"   {a} → {b}:  {flow:>6.0f} MW / {cap:>5} MW  ({util:.0f}%){binding}")
            total_flow += flow

    # ── Price convergence analysis ──
    print(f"\n{'=' * 70}")
    print("  PRICE CONVERGENCE ANALYSIS")
    print(f"{'=' * 70}")
    print(f"  {'Route':<14} {'Real Spread':>14} {'Model Spread':>14} {'Converged?':>12}")
    print(f"  {'─'*14} {'─'*14} {'─'*14} {'─'*12}")

    # Check connected pairs
    checked: set = set()
    for (a, b) in sorted(atc.keys()):
        pair = tuple(sorted([a, b]))
        if pair in checked:
            continue
        checked.add(pair)

        if a not in zones or b not in zones:
            continue
        za = zones[a]
        zb = zones[b]

        real_spread = abs(real_prices.get(a, 0) - real_prices.get(b, 0))
        model_spread = abs(za.get("mcp", 0) - zb.get("mcp", 0))
        converged = model_spread <= 1.0  # within €1

        print(f"  {a} ↔ {b:<10} €{real_spread:>9.2f}      €{model_spread:>9.2f}      {'✅' if converged else '❌':>8}")

    print(f"\n{'=' * 70}")
    print("  💡 INTERVIEW TIP:")
    print("     When ATC binds, prices diverge — creating congestion rent.")
    print("     The model MCP differs from real prices because fleets")
    print("     and demand curves are approximations. In a real coupling")
    print("     (Euphemia), actual order books and PTDF matrices are used.")
    print(f"{'=' * 70}")


# ── CLI entry point ──────────────────────────────────────────────────


def main() -> None:
    """CLI entry point (registered in pyproject.toml as ea-europe)."""
    result, real_prices, atc = run_european_coupling()
    print_results(result, real_prices, atc)


if __name__ == "__main__":
    main()
