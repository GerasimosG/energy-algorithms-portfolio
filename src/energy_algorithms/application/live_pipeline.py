from __future__ import annotations

#!/usr/bin/env python3
"""Live ENTSO-E Pipeline Demo — PCR market model driven by real data.

Fetches live (or recent) Belgian day-ahead prices and generation mix
from the ENTSO-E Transparency Platform, then runs a PCR (Euphemia-style)
market clearing model and compares the model's equilibrium price with
actual ENTSO-E prices.

Gracefully falls back to demo data when the API is unavailable.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from energy_algorithms.adapters.config import ENTSOE_API_KEY, DEFAULT_AREA_CODE
except ImportError:
    ENTSOE_API_KEY = ""
    DEFAULT_AREA_CODE = "10YBE----------2"  # Belgium

from energy_algorithms.adapters.entsoe_client import (
    EntsoeClient,
    fetch_demo_day_ahead,
    fetch_demo_generation_mix,
)
from energy_algorithms.domain.markets.pcr_model import PCRModel

# ── Marginal cost estimates by technology (€/MWh) ────────────────────
# Representative short-run marginal costs for European power generators.
# These are approximate and used to build the supply curve for the PCR model.
MARGINAL_COSTS: dict[str, float] = {
    "Nuclear": 7.0,
    "Wind Onshore": 2.0,
    "Wind Offshore": 8.0,
    "Solar": 1.0,
    "Hydro Run-of-river and poundage": 5.0,
    "Hydro Water Reservoir": 10.0,
    "Hydro Pumped Storage": 90.0,
    "Biomass": 45.0,
    "Fossil Gas": 70.0,
    "Fossil Hard coal": 55.0,
    "Fossil Brown coal/Lignite": 10.0,
    "Fossil Oil": 120.0,
    "Waste": 30.0,
    "Geothermal": 5.0,
    "Marine": 40.0,
    "Other": 60.0,
    "Other renewable": 15.0,
}

# Fallback marginal cost for unknown types
DEFAULT_MARGINAL_COST = 50.0


# ── API helpers ──────────────────────────────────────────────────────


def _most_recent_date() -> str:
    """Return yesterday's date in YYYY-MM-DD format.

    ENTSO-E day-ahead data is typically published by early afternoon
    for the next day, so the most recent fully-available date is yesterday.
    """
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def _try_fetch_live(api_key: str, area: str, date: str) -> dict[str, Any]:
    """Attempt to fetch live data from ENTSO-E.

    Returns a dict with "success" bool plus "prices" and/or "generation"
    on success, or "error" on failure.
    """
    client = EntsoeClient(api_key=api_key, timeout=20)

    prices_result = client.fetch_day_ahead_prices(area, date)
    gen_result = client.fetch_generation_mix(area, date)

    if prices_result.get("status") == "error":
        return {"success": False, "error": prices_result.get("error", "Unknown API error")}
    if gen_result.get("status") == "error":
        return {"success": False, "error": gen_result.get("error", "Unknown API error")}

    # Quick sanity check: prices and generation should have data
    if not prices_result.get("prices") or not gen_result.get("generation"):
        return {"success": False, "error": "API returned empty data"}

    return {
        "success": True,
        "prices": prices_result,
        "generation": gen_result,
        "live": True,
    }


def _build_pcr_model(prices_data: dict, gen_data: dict, area: str) -> PCRModel:
    """Build a PCR market clearing model from live/demo data.

    Supply: each generation type at its representative marginal cost,
    offering its full MW capacity.

    Demand: constructed from the day-ahead price distribution.
    Total demand equals total generation; willingness-to-pay steps
    are derived from the ENTSO-E price percentiles.

    Parameters
    ----------
    prices_data : dict
        Day-ahead prices result from fetcher (has "prices" key).
    gen_data : dict
        Generation mix result from fetcher (has "generation" key).
    area : str
        Bidding zone EIC code.

    Returns
    -------
    PCRModel instance with orders populated.
    """
    model = PCRModel(area=area)

    # ── Supply: one order per generation type ────────────────────────
    for g in gen_data["generation"]:
        if g["mw"] <= 0:
            continue
        mc = MARGINAL_COSTS.get(g["type"], DEFAULT_MARGINAL_COST)
        model.add_supply(
            oid=g["type"],
            price=mc,
            qty=g["mw"],
        )

    # ── Demand: build from price distribution ────────────────────────
    price_list = [p["price_eur_mwh"] for p in prices_data["prices"]]
    total_gen = gen_data["total_mw"]

    if not price_list or total_gen <= 0:
        return model

    price_list_sorted = sorted(price_list, reverse=True)

    # Create 3 demand blocks from the price distribution:
    #   - Top third (peak demand) at high willingness-to-pay
    #   - Middle third at medium price
    #   - Bottom third (baseload) at lower price
    n = len(price_list_sorted)
    third = max(n // 3, 1)

    top_prices = price_list_sorted[:third]
    mid_prices = price_list_sorted[third : 2 * third]
    bot_prices = price_list_sorted[2 * third :]

    def _avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0

    top_price = _avg(top_prices)
    mid_price = _avg(mid_prices)
    bot_price = _avg(bot_prices)

    # Distribute total generation across demand blocks proportionally
    top_qty = round(total_gen * (len(top_prices) / n), 1)
    mid_qty = round(total_gen * (len(mid_prices) / n), 1)
    bot_qty = round(total_gen - top_qty - mid_qty, 1)

    if top_qty > 0 and top_price > 0:
        model.add_demand("Demand_Peak", price=top_price, qty=top_qty)
    if mid_qty > 0 and mid_price > 0:
        model.add_demand("Demand_Mid", price=mid_price, qty=mid_qty)
    if bot_qty > 0 and bot_price > 0:
        model.add_demand("Demand_Base", price=bot_price, qty=bot_qty)

    return model


# ── Public API ───────────────────────────────────────────────────────


def demo_live_pipeline() -> dict[str, Any]:
    """Run the live ENTSO-E pipeline with PCR market model.

    Attempts to fetch live Belgian day-ahead prices and generation mix
    from the ENTSO-E Transparency Platform. If the API is unavailable
    or returns errors, falls back to realistic demo data.

    The pipeline:
      1. Fetch day-ahead prices (live or demo)
      2. Fetch generation mix (live or demo)
      3. Build a PCR (Euphemia-style) market clearing model using the
         real generation as supply and day-ahead prices as demand proxy
      4. Solve for the market clearing price
      5. Compare the PCR model's MCP with the actual ENTSO-E average price

    Returns
    -------
    dict with keys:
        - live : bool — whether live API data was used
        - area : str — bidding zone EIC code
        - date : str — date of the data
        - prices : dict — full prices result
        - generation : dict — full generation result
        - model_result : dict — PCR model solve result
        - model_mcp : float — PCR model market clearing price
        - entsoe_avg_price : float — ENTSO-E actual average price
        - price_diff_pct : float — percentage difference (model vs actual)
        - generation_shares : dict — {type: share_pct} for each source
    """
    area = DEFAULT_AREA_CODE
    date = _most_recent_date()
    live = False

    # ═══════════════════════════════════════════════════════════════
    # Step 1 & 2 — Fetch data (live or fallback)
    # ═══════════════════════════════════════════════════════════════
    prices_data: dict[str, Any]
    gen_data: dict[str, Any]

    try:
        live_result = _try_fetch_live(ENTSOE_API_KEY, area, date)
        if live_result["success"]:
            live = True
            prices_data = live_result["prices"]
            gen_data = live_result["generation"]
        else:
            raise RuntimeError(live_result.get("error", "API unavailable"))
    except Exception:
        # Graceful fallback to demo data
        prices_data = fetch_demo_day_ahead()
        gen_data = fetch_demo_generation_mix()
        date = prices_data.get("date", date)

    # ═══════════════════════════════════════════════════════════════
    # Step 3 — Build PCR model
    # ═══════════════════════════════════════════════════════════════
    pcr_model = _build_pcr_model(prices_data, gen_data, area)
    model_result = pcr_model.solve()

    model_mcp = model_result.get("mcp", 0.0)
    entsoe_avg = prices_data.get("avg_price", 0.0)

    if entsoe_avg > 0:
        price_diff_pct = round((model_mcp - entsoe_avg) / entsoe_avg * 100, 1)
    else:
        price_diff_pct = 0.0

    # ═══════════════════════════════════════════════════════════════
    # Step 4 — Generation shares
    # ═══════════════════════════════════════════════════════════════
    total_mw = gen_data.get("total_mw", 0)
    generation_shares: dict[str, float] = {}
    for g in gen_data.get("generation", []):
        if total_mw > 0:
            generation_shares[g["type"]] = round(g["mw"] / total_mw * 100, 1)
        else:
            generation_shares[g["type"]] = 0.0

    # ═══════════════════════════════════════════════════════════════
    # Step 5 — Print formatted report
    # ═══════════════════════════════════════════════════════════════
    _print_report(
        live=live,
        area=area,
        date=date,
        prices_data=prices_data,
        gen_data=gen_data,
        model_result=model_result,
        model_mcp=model_mcp,
        entsoe_avg=entsoe_avg,
        price_diff_pct=price_diff_pct,
        generation_shares=generation_shares,
    )

    return {
        "live": live,
        "area": area,
        "date": date,
        "prices": prices_data,
        "generation": gen_data,
        "model_result": model_result,
        "model_mcp": model_mcp,
        "entsoe_avg_price": entsoe_avg,
        "price_diff_pct": price_diff_pct,
        "generation_shares": generation_shares,
    }


def _print_report(
    live: bool,
    area: str,
    date: str,
    prices_data: dict,
    gen_data: dict,
    model_result: dict,
    model_mcp: float,
    entsoe_avg: float,
    price_diff_pct: float,
    generation_shares: dict,
) -> None:
    """Print a formatted comparison report."""
    data_source = "LIVE ENTSO-E API" if live else "DEMO (offline fallback)"

    print()
    print("=" * 68)
    print("  ENTSO-E Live Pipeline — PCR Market Model Demo")
    print("=" * 68)
    print(f"  Data source : {data_source}")
    print(f"  Area        : {area} (Belgium)")
    print(f"  Date        : {date}")
    print(f"  Model       : PCR Social Welfare Maximization (PuLP/CBC)")
    print("-" * 68)

    # ── Price comparison ─────────────────────────────────────────────
    print()
    print("  ═══ Price Comparison ═══")
    print(f"  ENTSO-E Day-Ahead Avg Price : €{entsoe_avg:>8.2f} / MWh")
    print(f"  PCR Model Clearing Price    : €{model_mcp:>8.2f} / MWh")
    direction = "↑ above" if price_diff_pct > 0 else "↓ below"
    print(f"  Difference                  : {price_diff_pct:>+8.1f}% ({direction} ENTSO-E)")
    print(f"  Model Status                : {model_result.get('status', 'N/A')}")
    print(f"  Traded Volume               : {model_result.get('traded', 0):>8.1f} MWh")
    welfare = model_result.get("welfare", 0)
    print(f"  Social Welfare              : €{welfare:>10,.2f}")

    # ── Generation mix ───────────────────────────────────────────────
    print()
    print("  ═══ Generation Mix ═══")
    print(f"  Total Generation : {gen_data.get('total_mw', 0):.0f} MW")
    print(f"  {'Source':<30} {'MW':>8} {'Share':>8}  {'Marg €/MWh':>10}")
    print(f"  {'─'*30} {'─'*8} {'─'*8}  {'─'*10}")
    for g in gen_data.get("generation", []):
        mw = g["mw"]
        share = generation_shares.get(g["type"], 0)
        mc = MARGINAL_COSTS.get(g["type"], DEFAULT_MARGINAL_COST)
        bar = "█" * int(share / 2) if share > 0 else ""
        print(f"  {g['type']:<30} {mw:>8.0f} {share:>7.1f}%  €{mc:>8.0f}  {bar}")

    # ── Supply dispatch from PCR model ───────────────────────────────
    print()
    print("  ═══ Supply Dispatch (PCR Model) ═══")
    supply_orders = model_result.get("orders", {}).get("supply", {})
    if supply_orders:
        print(f"  {'Source':<30} {'Bid €':>7} {'Qty':>8} {'Filled %':>8}  Status")
        print(f"  {'─'*30} {'─'*7} {'─'*8} {'─'*8}  ──────")
        for oid, o in sorted(supply_orders.items(), key=lambda x: x[1]["price"]):
            filled_pct = o["filled_frac"] * 100
            status = "✓ Cleared" if filled_pct > 0 else "✗ Not cleared"
            print(f"  {oid:<30} €{o['price']:>6.0f} {o['qty']:>8.0f} {filled_pct:>7.0f}%  {status}")

    # ── Demand dispatch ──────────────────────────────────────────────
    demand_orders = model_result.get("orders", {}).get("demand", {})
    if demand_orders:
        print()
        print(f"  {'Demand Block':<30} {'Bid €':>7} {'Qty':>8} {'Filled %':>8}  Status")
        print(f"  {'─'*30} {'─'*7} {'─'*8} {'─'*8}  ──────")
        for oid, o in demand_orders.items():
            filled_pct = o["filled_frac"] * 100
            status = "✓ Served" if filled_pct > 0 else "✗ Not served"
            print(f"  {oid:<30} €{o['price']:>6.0f} {o['qty']:>8.0f} {filled_pct:>7.0f}%  {status}")

    # ── Price curve (hourly) ─────────────────────────────────────────
    print()
    print("  ═══ Day-Ahead Price Curve (Hourly) ═══")
    prices_list = prices_data.get("prices", [])
    if prices_list:
        # Split into two rows of 12 for compact display
        for half, label in [(prices_list[:12], "Hours 1-12"), (prices_list[12:], "Hours 13-24")]:
            bars = "".join(
                "█" if p["price_eur_mwh"] >= entsoe_avg else "▁"
                for p in half
            )
            vals = "  ".join(f"€{p['price_eur_mwh']:>6.0f}" for p in half)
            print(f"  {label}: {vals}")
            print(f"           {bars}  (█ above avg, ▁ below avg)")

    print()
    print("=" * 68)
    if not live:
        print("  ⚠ Running with demo data — set ENTSOE_API_KEY in")
        print("    energy_data/config.py for live ENTSO-E data.")
    print("=" * 68)
    print()


# ── CLI entry point ──────────────────────────────────────────────────


if __name__ == "__main__":
    demo_live_pipeline()
