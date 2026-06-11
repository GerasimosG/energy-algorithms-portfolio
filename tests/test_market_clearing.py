"""Tests for market clearing equilibrium finding.

Covers find_equilibrium and demo_clearing which are currently at 13% coverage.
The plot function requires matplotlib and is tested implicitly through find_equilibrium.
"""

from __future__ import annotations

import numpy as np

from energy_algorithms.domain.markets.market_clearing import (
 demo_clearing,
 find_equilibrium,
)

# ── Basic equilibrium ─────────────────────────────────────────────────

def test_basic_cross():
 """Simple supply-demand intersection."""
 supply = [
 {"id": "Solar", "price": 5, "quantity": 200},
 {"id": "Gas", "price": 80, "quantity": 200},
 ]
 demand = [
 {"id": "Industry", "price": 150, "quantity": 300},
 ]
 result = find_equilibrium(supply, demand)
 assert result["clearing_price"] > 0
 assert result["clearing_volume"] > 0
 assert result["clearing_volume"] <= 300 # can't exceed demand


def test_clearing_price_between_curves():
 """Clearing price lies between the marginal supply and demand prices."""
 supply = [
 {"id": "Cheap", "price": 10, "quantity": 50},
 {"id": "Mid", "price": 50, "quantity": 50},
 {"id": "Expensive", "price": 100, "quantity": 50},
 ]
 demand = [
 {"id": "Buyer1", "price": 200, "quantity": 60},
 {"id": "Buyer2", "price": 80, "quantity": 40},
 ]
 result = find_equilibrium(supply, demand)
 cp = result["clearing_price"]
 assert cp >= 10
 assert cp <= 200


# ── Edge cases ────────────────────────────────────────────────────────

def test_all_supply_cheaper_than_demand():
 """All supply is cheaper than all demand — clears at total demand volume."""
 supply = [
 {"id": "Free", "price": 0, "quantity": 100},
 {"id": "VeryCheap", "price": 5, "quantity": 100},
 ]
 demand = [
 {"id": "RichBuyer", "price": 500, "quantity": 50},
 ]
 result = find_equilibrium(supply, demand)
 assert result["clearing_volume"] == 50.0 # total demand quantity
 assert result["clearing_price"] >= 0


def test_no_trade_possible():
 """Supply more expensive than demand → tiny clearing from interpolation."""
 supply = [
 {"id": "Expensive", "price": 200, "quantity": 100},
 ]
 demand = [
 {"id": "CheapBuyer", "price": 50, "quantity": 100},
 ]
 result = find_equilibrium(supply, demand)
 # Interpolation: supply starts at 0, rises to 200. Demand is flat at 50.
 # They cross at low volume where supply price ≈ demand price ≈ 50.
 assert result["clearing_volume"] > 0
 assert result["clearing_volume"] < 100 # not full demand
 assert result["clearing_price"] > 0


def test_exact_price_match():
 """Supply and demand with identical prices — intersection handles it."""
 supply = [
 {"id": "S1", "price": 50, "quantity": 100},
 {"id": "S2", "price": 70, "quantity": 100},
 ]
 demand = [
 {"id": "D1", "price": 70, "quantity": 100},
 {"id": "D2", "price": 40, "quantity": 100},
 ]
 result = find_equilibrium(supply, demand)
 assert result["clearing_volume"] > 0
 assert 40 <= result["clearing_price"] <= 70


def test_single_order_each():
 """One supply order and one demand order — clears at demand volume."""
 result = find_equilibrium(
 [{"id": "Gen", "price": 30, "quantity": 100}],
 [{"id": "Load", "price": 100, "quantity": 80}],
 )
 assert result["clearing_volume"] == 80.0
 # Supply price at 80 MWh: 30 * (80/100) = 24 EUR (linear interpolation)
 assert 20 <= result["clearing_price"] <= 35


def test_multiple_equal_prices():
 """Multiple orders at the same price level."""
 supply = [
 {"id": f"Gen{i}", "price": 40, "quantity": 20}
 for i in range(5)
 ]
 demand = [
 {"id": "Buyer", "price": 60, "quantity": 60}
 ]
 result = find_equilibrium(supply, demand)
 assert result["clearing_price"] == 40.0
 assert result["clearing_volume"] == 60.0


# ── Return structure ──────────────────────────────────────────────────

def test_return_keys():
 """find_equilibrium returns expected keys."""
 supply = [{"id": "S", "price": 10, "quantity": 100}]
 demand = [{"id": "D", "price": 100, "quantity": 100}]
 result = find_equilibrium(supply, demand)
 expected = {"clearing_price", "clearing_volume", "supply_prices",
 "supply_cum_qty", "demand_prices", "demand_cum_qty"}
 assert set(result.keys()) == expected


def test_return_types():
 """All return values have correct types."""
 result = find_equilibrium(
 [{"id": "S", "price": 10, "quantity": 100}],
 [{"id": "D", "price": 100, "quantity": 100}],
 )
 assert isinstance(result["clearing_price"], float)
 assert isinstance(result["clearing_volume"], float)
 assert isinstance(result["supply_prices"], np.ndarray)
 assert isinstance(result["demand_prices"], np.ndarray)
 assert isinstance(result["supply_cum_qty"], np.ndarray)
 assert isinstance(result["demand_cum_qty"], np.ndarray)


# ── demo_clearing ─────────────────────────────────────────────────────

def test_demo_clearing():
 """Built-in demo produces valid equilibrium."""
 result = demo_clearing()
 assert result["clearing_price"] > 0
 assert result["clearing_volume"] > 0
 assert len(result["supply_prices"]) == 5
 assert len(result["demand_prices"]) == 3


# ── Cumulative supply/demand consistency ──────────────────────────────

def test_supply_cum_qty_monotonic():
 """Cumulative supply quantities are monotonically increasing."""
 supply = [
 {"id": "A", "price": 10, "quantity": 30},
 {"id": "B", "price": 20, "quantity": 40},
 {"id": "C", "price": 50, "quantity": 30},
 ]
 demand = [{"id": "D", "price": 60, "quantity": 50}]
 result = find_equilibrium(supply, demand)
 sup_cum = result["supply_cum_qty"]
 assert np.all(np.diff(sup_cum) >= 0) # non-decreasing


def test_demand_cum_qty_monotonic():
 """Cumulative demand quantities are monotonically increasing."""
 supply = [{"id": "S", "price": 30, "quantity": 100}]
 demand = [
 {"id": "D1", "price": 100, "quantity": 30},
 {"id": "D2", "price": 80, "quantity": 40},
 ]
 result = find_equilibrium(supply, demand)
 dem_cum = result["demand_cum_qty"]
 assert np.all(np.diff(dem_cum) >= 0)


# ── plot_supply_demand_stack ─────────────────────────────────────────

def test_plot_supply_demand_stack_creates_file(tmp_path) -> None:
 """plot_supply_demand_stack saves a PNG and returns the path."""
 from energy_algorithms.domain.markets.market_clearing import (
 plot_supply_demand_stack,
 )

 supply = [
 {"id": "Solar", "price": 5, "quantity": 200},
 {"id": "Gas", "price": 80, "quantity": 200},
 ]
 demand = [
 {"id": "Industry", "price": 150, "quantity": 300},
 ]

 save_path = str(tmp_path / "market_clearing.png")
 result = plot_supply_demand_stack(supply, demand, save_path)

 assert result == save_path
 import os
 assert os.path.exists(save_path)
 assert os.path.getsize(save_path) > 0


def test_plot_supply_demand_stack_multiple_buyers(tmp_path) -> None:
 """Plot with 5 suppliers and 3 buyers — covers surplus shading branches."""
 from energy_algorithms.domain.markets.market_clearing import (
 plot_supply_demand_stack,
 )

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

 save_path = str(tmp_path / "market_full.png")
 result = plot_supply_demand_stack(supply, demand, save_path)

 assert result == save_path
 import os
 assert os.path.exists(save_path)
 assert os.path.getsize(save_path) > 1000 # full plot > 1KB
