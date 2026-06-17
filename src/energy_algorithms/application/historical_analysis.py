"""30-Day ENTSO-E Historical Analysis Pipeline.

Fetches N days of European market data, runs all optimization
algorithms against each day, and produces a comprehensive report.

This is how  and Energy backtest their algorithms against
historical data — validate performance across market regimes.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from energy_algorithms.adapters.config import ENTSOE_API_KEY
from energy_algorithms.adapters.entsoe_client import BIDDING_ZONES, EntsoeClient
from energy_algorithms.domain.markets.multi_zone import solve_multi_zone
from energy_algorithms.domain.optimization.storage import solve_storage

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".data_cache")

# Zones we track
MONITORED_ZONES = ["BE", "FR", "DE", "NL"]

# Supply curves for multi-zone coupling (same as european_coupling.py)
MARGINAL_COSTS_MULTI: dict[str, list[dict]] = {
    "FR": [
        {"price": 2, "qty": 5000},
        {"price": 5, "qty": 3000},
        {"price": 30, "qty": 4000},
        {"price": 70, "qty": 2000},
    ],
    "BE": [
        {"price": 1, "qty": 4000},
        {"price": 7, "qty": 3000},
        {"price": 50, "qty": 2000},
        {"price": 90, "qty": 1000},
    ],
    "DE": [
        {"price": 1, "qty": 3000},
        {"price": 10, "qty": 2000},
        {"price": 40, "qty": 4000},
        {"price": 60, "qty": 3000},
        {"price": 100, "qty": 1500},
    ],
    "NL": [
        {"price": 10, "qty": 2000},
        {"price": 45, "qty": 3000},
        {"price": 70, "qty": 2000},
        {"price": 130, "qty": 500},
    ],
}

ATC_CAPACITIES: dict[tuple[str, str], int] = {
    ("FR", "BE"): 3500,
    ("FR", "DE"): 3000,
    ("BE", "NL"): 2400,
    ("BE", "DE"): 1000,
    ("NL", "DE"): 4000,
}


def _ensure_cache() -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(code: str, date: str) -> str:
    return os.path.join(CACHE_DIR, f"prices_{code}_{date}.json")


def fetch_day(client: EntsoeClient, code: str, eic: str, date: str) -> dict[str, Any]:
    """Fetch and cache one day of data for one zone."""
    cache_path = _cache_path(code, date)
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            return json.load(f)

    r = client.fetch_day_ahead_prices(eic, date)
    hourly = [p for p in r.get("prices", []) if p["hour"] <= 24][:24]
    vals = [p["price_eur_mwh"] for p in hourly]
    result = {"prices": vals, "avg": float(np.mean(vals)) if vals else 0.0}

    with open(cache_path, "w") as f:
        json.dump(result, f)

    return result


def build_demand_curve(real_prices: list[float]) -> list[dict]:
    """Build a 3-block demand curve from real price distribution."""
    if not real_prices:
        return [{"price": 100, "qty": 1000}]
    sorted_p = sorted(real_prices, reverse=True)
    n = len(sorted_p)
    third = max(n // 3, 1)

    def _avg(lst: list[float]) -> float:
        return round(sum(lst) / len(lst), 2) if lst else 0.0

    top = _avg(sorted_p[:third])
    mid = _avg(sorted_p[third:2*third])
    bot = _avg(sorted_p[2*third:])

    return [
        {"price": max(top + 40, 80), "qty": 2000},
        {"price": max(mid + 20, 60), "qty": 2000},
        {"price": max(bot + 10, 40), "qty": 2000},
    ]


# ── Per-day analysis ─────────────────────────────────────────────


def analyze_day(
    day_prices: dict[str, list[float]],
    day_avgs: dict[str, float],
    date: str,
) -> dict[str, Any]:
    """Run all algorithms against one day of data."""
    result: dict[str, Any] = {
        "date": date,
        "prices": day_avgs,
    }

    # 1. BESS storage arbitrage against BE prices
    be_prices = day_prices.get("BE", [])
    if be_prices:
        batt_95 = solve_storage(be_prices, capacity=100, max_power=25,
                                 eff_in=0.95, eff_out=0.95, initial_soc=50)
        batt_85 = solve_storage(be_prices, capacity=300, max_power=50,
                                 eff_in=0.90, eff_out=0.90, initial_soc=0)
        result["storage_arbitrage"] = {
            "bess_100mw_95eff": round(batt_95["revenue"], 0),
            "bess_300mw_81eff": round(batt_85["revenue"], 0),
            "min_price": min(be_prices),
            "max_price": max(be_prices),
            "volatility": round(np.std(be_prices), 2),
        }

    # 2. Cross-border spread analysis
    spreads = {}
    for za in MONITORED_ZONES:
        for zb in MONITORED_ZONES:
            if za < zb and za in day_avgs and zb in day_avgs and day_avgs[za] > 0 and day_avgs[zb] > 0:
                spread = abs(day_avgs[za] - day_avgs[zb])
                if spread > 1:
                    spreads[f"{za}↔{zb}"] = round(spread, 2)
    result["cross_border_spreads"] = spreads
    result["max_spread"] = max(spreads.values()) if spreads else 0.0

    # 3. Multi-zone market coupling
    zones_for_coupling = []
    for code in MONITORED_ZONES:
        supply = MARGINAL_COSTS_MULTI[code]
        synthetic_24h = []
        avg = day_avgs.get(code, 50)
        for h in range(24):
            synthetic_24h.append(avg * (0.6 + 0.4 * np.sin(2 * np.pi * h / 24)))
        demand = build_demand_curve(synthetic_24h)
        zones_for_coupling.append({
            "name": code,
            "supply": supply,
            "demand": demand,
        })

    # Filter ATC to zones with data today
    atc = {}
    for (a, b), cap in ATC_CAPACITIES.items():
        if a in day_avgs and b in day_avgs and day_avgs[a] > 0 and day_avgs[b] > 0:
            atc[(a, b)] = cap

    coupling = solve_multi_zone(zones_for_coupling, atc, verbose=False)
    if coupling.get("status") == "Optimal":
        welfare = coupling.get("welfare", 0)
        flows = coupling.get("flows", {})
        zones = coupling.get("zones", {})
        result["coupling"] = {
            "welfare": round(welfare, 0),
            "active_flows": len(flows),
            "zones": {z: {"mcp": zones[z]["mcp"]} for z in MONITORED_ZONES if z in zones},
        }

    return result


# ── Main analysis ───────────────────────────────────────────────


def run_30day_analysis(num_days: int = 30) -> list[dict[str, Any]]:
    """Fetch and analyze N days of historical data."""
    _ensure_cache()
    client = EntsoeClient(api_key=ENTSOE_API_KEY, timeout=30)

    results: list[dict[str, Any]] = []
    errors = 0

    print(f"📡 30-DAY HISTORICAL ANALYSIS ({num_days} days)")
    print(f"{'=' * 70}")
    print(f"  Fetching data for {len(MONITORED_ZONES)} zones: {', '.join(MONITORED_ZONES)}")
    print(f"  Cache: {CACHE_DIR}")
    print()

    for day_offset in range(num_days):
        date = (datetime.now() - timedelta(days=day_offset + 1)).strftime("%Y-%m-%d")
        sys.stdout.write(f"\r  Day {day_offset+1:2d}/{num_days}: {date}  ")
        sys.stdout.flush()

        try:
            day_prices: dict[str, list[float]] = {}
            day_avgs: dict[str, float] = {}

            for code in MONITORED_ZONES:
                eic = BIDDING_ZONES[code]
                fetched = fetch_day(client, code, eic, date)
                day_prices[code] = fetched["prices"]
                day_avgs[code] = fetched["avg"]

            # Only analyze if we have real data
            if sum(day_avgs.values()) > 0:
                day_result = analyze_day(day_prices, day_avgs, date)
                results.append(day_result)
                sys.stdout.write(f"✅ avg €{day_avgs.get('BE', 0):.0f}")
            else:
                sys.stdout.write("⏭️  no data")
        except Exception as e:
            errors += 1
            sys.stdout.write(f"❌ {str(e)[:30]}")

        time.sleep(0.2)  # avoid API rate limit

    print(f"\n\n✅ Analyzed {len(results)} days ({errors} errors)")
    return results


# ── Reporting ───────────────────────────────────────────────────


def print_monthly_report(results: list[dict[str, Any]]) -> None:
    """Print a comprehensive monthly report."""
    print(f"\n{'=' * 70}")
    print("  📊 MONTHLY PERFORMANCE REPORT")
    print(f"  {len(results)} days analyzed | Belgium bidding zone")
    print(f"{'=' * 70}")

    # Price statistics
    be_avgs = [r["prices"].get("BE", 0) for r in results if r["prices"].get("BE", 0) > 0]
    if be_avgs:
        print("\n1️⃣  PRICE STATISTICS (BE)")
        print(f"  {'─' * 50}")
        print(f"  Mean:      €{np.mean(be_avgs):>8.2f}/MWh")
        print(f"  Median:    €{np.median(be_avgs):>8.2f}/MWh")
        print(f"  Min:       €{min(be_avgs):>8.2f}/MWh")
        print(f"  Max:       €{max(be_avgs):>8.2f}/MWh")
        print(f"  Std Dev:   €{np.std(be_avgs):>8.2f}/MWh")
        # Price regimes
        cheap = sum(1 for p in be_avgs if p < 40)
        normal = sum(1 for p in be_avgs if 40 <= p <= 100)
        expensive = sum(1 for p in be_avgs if p > 100)
        print(f"  Regimes:   {cheap}d cheap (<€40), {normal}d normal, {expensive}d expensive (>€100)")

    # Cross-border spreads
    if results:
        all_spreads: dict[str, list[float]] = {}
        for r in results:
            for pair, spread in r.get("cross_border_spreads", {}).items():
                all_spreads.setdefault(pair, []).append(spread)

        print("\n2️⃣  CROSS-BORDER SPREADS (Monthly Avg)")
        print(f"  {'Route':<12} {'Avg Spread':>14} {'Max Spread':>14} {'Days >€20':>12}")
        print(f"  {'─'*12} {'─'*14} {'─'*14} {'─'*12}")
        for pair in sorted(all_spreads.keys()):
            vals = all_spreads[pair]
            above_20 = sum(1 for v in vals if v > 20)
            print(f"  {pair:<12} €{np.mean(vals):>9.2f}    €{max(vals):>9.2f}    {above_20:>5d}/{len(vals):<3d}")

        # Best arbitrage opportunities
        print("\n  Best spreads (top 5 days):")
        all_spread_days = [(r["max_spread"], r["date"]) for r in results if r.get("max_spread", 0) > 0]
        all_spread_days.sort(reverse=True)
        for s, d in all_spread_days[:5]:
            print(f"    €{s:>6.1f}/MWh — {d}")

    # Storage arbitrage profitability
    if results and "storage_arbitrage" in results[0]:
        revenues_high = [r["storage_arbitrage"]["bess_100mw_95eff"] for r in results]
        revenues_low = [r["storage_arbitrage"]["bess_300mw_81eff"] for r in results]

        print("\n3️⃣  BESS STORAGE ARBITRAGE (30d backtest)")
        print(f"  {'─' * 55}")
        print(f"  {'':<30} {'100MWh/25MW':>15} {'300MWh/50MW':>15}")
        print(f"  {'':<30} {'95% eff':>15} {'81% eff':>15}")
        print(f"  {'─' * 55}")
        print(f"  {'Monthly Revenue':<30} €{sum(revenues_high):>12,.0f}  €{sum(revenues_low):>12,.0f}")
        print(f"  {'Avg Daily Revenue':<30} €{np.mean(revenues_high):>12,.0f}  €{np.mean(revenues_low):>12,.0f}")
        print(f"  {'Best Day':<30} €{max(revenues_high):>12,.0f}  €{max(revenues_low):>12,.0f}")
        print(f"  {'Days Profitable':<30} {sum(1 for r in revenues_high if r > 0):>9d}/{len(revenues_high):<3d}  {sum(1 for r in revenues_low if r > 0):>9d}/{len(revenues_low):<3d}")
        print(f"  {'Volatility (avg)':<30} €{np.mean([r['storage_arbitrage']['volatility'] for r in results]):>11.2f}")

        # Identify best days for storage
        print("\n  Best days for storage arbitrage (top 5):")
        rev_days = [(r["storage_arbitrage"]["bess_100mw_95eff"], r["date"]) for r in results]
        rev_days.sort(reverse=True)
        for rev, d in rev_days[:5]:
            r_data = [x for x in results if x["date"] == d][0]
            sa = r_data["storage_arbitrage"]
            print(f"    €{rev:>7,.0f} — {d} (min=€{sa['min_price']:.0f}, max=€{sa['max_price']:.0f}, σ={sa['volatility']:.0f})")

    # Market coupling summary
    coupling_results = [r.get("coupling", {}) for r in results if r.get("coupling")]
    if coupling_results:
        welfare_vals = [c["welfare"] for c in coupling_results]
        flows_vals = [c["active_flows"] for c in coupling_results]
        print(f"\n4️⃣  EUROPEAN MARKET COUPLING (4-zone, {len(coupling_results)} days)")
        print(f"  {'─' * 50}")
        print(f"  Avg Social Welfare: €{np.mean(welfare_vals):>12,.0f}/day")
        print(f"  Avg Active Flows:   {np.mean(flows_vals):>8.1f} interconnectors")

    # ── Key insight ──
    print(f"\n{'=' * 70}")
    print("  💡 KEY INSIGHT FOR INTERVIEWS:")
    print("  This is how  backtests Euphemia changes — run the full")
    print("  market coupling against N months of historical data, measure")
    print("  welfare improvement, check for regression bugs, validate")
    print("  convergence properties across different market regimes.")
    print(f"{'=' * 70}")


def main(num_days: int = 30) -> None:
    """CLI entry point."""
    print()
    results = run_30day_analysis(num_days)
    print_monthly_report(results)
    print()


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    main(n)
