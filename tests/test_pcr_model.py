"""Tests for energy_markets PCR model."""

from __future__ import annotations

from energy_algorithms.domain.markets.intraday import demo_intraday, simulate_intraday
from energy_algorithms.domain.markets.pcr_model import PCRModel


# ── Basic PCR ─────────────────────────────────────────────────────────

def test_simple_clearing():
    """Simple market clears with correct MCP and welfare."""

    model = PCRModel("test")
    model.add_supply("Cheap", 10, 100)
    model.add_supply("Expensive", 80, 100)
    model.add_demand("Buyer", 150, 150)
    r = model.solve()
    assert r["status"] == "Optimal"
    assert r["mcp"] == 80  # Expensive is marginal
    assert r["traded"] == 150.0

def test_block_accepted():
    """Cheap block order is accepted."""
    model = PCRModel("test")
    model.add_supply("Gas", 80, 100)
    model.add_supply("Solar", 10, 60)
    model.add_demand("Industry", 150, 120)
    model.add_block("Nuclear", 40, 80)
    r = model.solve()
    assert r["status"] == "Optimal"
    assert r["orders"]["blocks"]["Nuclear"]["accepted"] is True

def test_block_rejected():
    """Expensive block order is rejected."""
    model = PCRModel("test")
    model.add_supply("Wind", 5, 200)
    model.add_supply("Solar", 10, 100)
    model.add_demand("Grid", 100, 250)
    model.add_block("ExpensivePeaker", 120, 40)
    r = model.solve()
    assert r["status"] == "Optimal"
    assert r["orders"]["blocks"]["ExpensivePeaker"]["accepted"] is False

def test_exclusive_blocks():
    """Exclusive blocks: at most one accepted."""
    model = PCRModel("test_excl")
    model.add_supply("Wind", 5, 100)
    model.add_demand("Grid", 150, 80)
    model.add_block("Option_A", 30, 50, group="excl_choice")
    model.add_block("Option_B", 45, 50, group="excl_choice")
    r = model.solve()
    assert r["status"] == "Optimal"
    accepted = [b for b in r["orders"]["blocks"].values() if b["accepted"]]
    assert len(accepted) <= 1  # At most one exclusive block accepted

def test_linked_blocks():
    """Linked blocks: all accepted or all rejected together."""
    model = PCRModel("test_link")
    model.add_supply("Gas", 80, 200)
    model.add_supply("Solar", 10, 100)
    model.add_demand("Grid", 150, 250)
    model.add_block("Block_A", 35, 60, group="cascade")
    model.add_block("Block_B", 35, 50, group="cascade")
    r = model.solve()
    assert r["status"] == "Optimal"
    a = r["orders"]["blocks"]["Block_A"]["accepted"]
    b = r["orders"]["blocks"]["Block_B"]["accepted"]
    assert a == b  # Both accepted or both rejected

def test_energy_balance_exact():
    """Energy balance constraint is equality (supply == demand)."""
    model = PCRModel("test_bal")
    model.add_supply("Gas", 50, 100)
    model.add_demand("Buyer", 100, 80)
    r = model.solve()
    assert r["status"] == "Optimal"
    assert r["traded"] == 80.0
    # Over-generation should not happen: supply == demand
    total_supplied = sum(o["filled_qty"] for o in r["orders"]["supply"].values())
    assert abs(total_supplied - r["traded"]) < 0.01

def test_mcp_with_block():
    """MCP includes block order prices when block is marginal."""
    model = PCRModel("test_mcp")
    model.add_supply("Solar", 10, 60)
    model.add_demand("Grid", 150, 100)
    model.add_block("GasBlock", 80, 50)
    r = model.solve()
    assert r["status"] == "Optimal"
    # If GasBlock is accepted (it should be since Solar only supplies 60 and demand is 100),
    # MCP should be at least 80 (the block's price)
    if r["orders"]["blocks"]["GasBlock"]["accepted"]:
        assert r["mcp"] >= 80

def test_no_trades_zero_demand():
    """Zero demand results in no trades or infeasible (energy balance == 0 supply == 0 demand)."""
    model = PCRModel("test_zero")
    model.add_supply("Gas", 50, 100)
    model.add_demand("Nobody", 100, 0)
    r = model.solve()
    # Either Optimal with 0 trades, or Infeasible (cannot have 0 supply == 0 demand with min constraints)
    assert r["status"] in ("Optimal", "Infeasible")

# ── Intraday ────────────────────────────────────────────────────────


def test_intraday_demo():
    """Demo intraday simulation returns valid result."""
    r = demo_intraday()
    assert r["status"] == "completed"
    assert len(r["trades"]) > 0
    assert r["total_volume"] > 0

def test_intraday_match_buy_sell():
    """A buy order at 100 matches a sell order at 100."""
    orders = [
        {"time": 0, "type": "sell", "price": 100, "qty": 10},
        {"time": 1, "type": "buy", "price": 100, "qty": 10},
    ]
    r = simulate_intraday(orders)
    assert len(r["trades"]) == 1
    assert r["trades"][0]["qty"] == 10

def test_intraday_no_match():
    """Buy at 80 doesn't match sell at 100."""
    orders = [
        {"time": 0, "type": "sell", "price": 100, "qty": 10},
        {"time": 1, "type": "buy", "price": 80, "qty": 10},
    ]
    r = simulate_intraday(orders)
    assert len(r["trades"]) == 0
    assert len(r["unfilled_orders"]) == 2

def test_intraday_partial_fill():
    """Buy for 20 MW where only 10 MW available → partial fill."""
    orders = [
        {"time": 0, "type": "sell", "price": 50, "qty": 10},
        {"time": 1, "type": "buy", "price": 50, "qty": 20},
    ]
    r = simulate_intraday(orders)
    assert len(r["trades"]) == 1
    assert r["trades"][0]["qty"] == 10
    # 10 MW of buy order remains unfilled
    assert len(r["unfilled_orders"]) == 1

def test_intraday_vwap():
    """VWAP reflects price×volume weighting."""
    orders = [
        {"time": 0, "type": "sell", "price": 50, "qty": 5},
        {"time": 1, "type": "sell", "price": 60, "qty": 5},
        {"time": 2, "type": "buy", "price": 70, "qty": 10},
    ]
    r = simulate_intraday(orders)
    # Two trades at 50 and 60, VWAP = (50*5 + 60*5)/10 = 55
    assert abs(r["vwap"] - 55.0) < 0.01


# ── IP Pricing ────────────────────────────────────────────────────────

def test_ip_pricing_basic():
    """solve_with_ip_pricing returns pricing_method='ip' and ip_price."""
    model = PCRModel("test_ip")
    model.add_supply("Cheap", 10, 100)
    model.add_supply("Expensive", 80, 100)
    model.add_demand("Buyer", 150, 150)
    model.add_block("Nuclear", 50, 50)
    r = model.solve_with_ip_pricing()
    assert r["status"] == "Optimal"
    assert r["pricing_method"] == "ip"
    assert "ip_price" in r
    assert "make_whole_payments" in r
    assert r["ip_price"] >= 0  # could be int from pulp but semantically float


def test_ip_pricing_no_blocks():
    """IP pricing with no blocks — degenerate case, ip_price == mcp."""
    model = PCRModel("test_no_blocks")
    model.add_supply("Cheap", 10, 100)
    model.add_supply("Expensive", 80, 100)
    model.add_demand("Buyer", 150, 150)
    # No blocks — solve_with_ip_pricing should still work
    r = model.solve_with_ip_pricing()
    assert r["status"] == "Optimal"
    assert r["pricing_method"] == "ip"
    assert r["ip_price"] == r["mcp"]
    assert r["make_whole_payments"] == {}


def test_ip_pricing_with_paradoxical():
    """IP pricing handles paradoxically accepted/rejected blocks."""
    model = PCRModel("test_paradox")
    model.add_supply("Wind", 5, 100)
    model.add_supply("Gas", 100, 200)
    model.add_demand("Grid", 120, 200)
    # A block at 80 between wind and gas — interesting case
    model.add_block("Coal", 80, 60)
    r = model.solve_with_ip_pricing()
    assert r["status"] == "Optimal"
    assert r["pricing_method"] == "ip"
    # ip_price should be >= 0
    assert r["ip_price"] >= 0


def test_ip_pricing_exclusive_blocks():
    """IP pricing with exclusive blocks."""
    model = PCRModel("test_ip_excl")
    model.add_supply("Wind", 5, 100)
    model.add_demand("Grid", 150, 80)
    model.add_block("Option_A", 30, 50, group="excl_ip")
    model.add_block("Option_B", 45, 50, group="excl_ip")
    r = model.solve_with_ip_pricing()
    assert r["status"] == "Optimal"
    accepted = [b for b in r["orders"]["blocks"].values() if b["accepted"]]
    assert len(accepted) <= 1


# ── report() ──────────────────────────────────────────────────────────

def test_report_runs():
    """report() executes without error (produces stdout)."""
    model = PCRModel("test_report")
    model.add_supply("Gas", 80, 100)
    model.add_demand("Load", 150, 80)
    model.solve()
    # Just verify it runs without exception
    model.report()


def test_report_no_result():
    """report() handles missing result gracefully."""
    model = PCRModel("test_no_result")
    model.report()  # prints "No result. Run solve() first."


def test_report_with_ip():
    """report() with IP pricing result."""
    model = PCRModel("test_report_ip")
    model.add_supply("Wind", 5, 100)
    model.add_demand("Grid", 150, 100)
    model.add_block("Storage", 30, 40)
    model.solve_with_ip_pricing()
    model.report()
