"""Tests for block order scenarios in the PCR model.

Covers simple_block, linked_block, exclusive_block, run_all, and run_exclusive
which are currently at 20% coverage.
"""

from __future__ import annotations

from energy_algorithms.domain.markets.block_orders import (
    run_all,
    run_exclusive,
    scenario_exclusive_block,
    scenario_linked_block,
    scenario_simple_block,
)

# ── Simple block ──────────────────────────────────────────────────────

def test_simple_block_returns_result():
    """Simple block scenario returns optimal result."""
    result = scenario_simple_block()
    assert result["status"] == "Optimal"
    assert result["traded"] > 0
    assert "blocks" in result["orders"]


def test_simple_block_nuclear_decision():
    """Nuclear block may be accepted or rejected based on economics."""
    result = scenario_simple_block()
    nuclear_info = result["orders"]["blocks"]["Nuclear"]
    # block is either accepted or rejected (both are valid outcomes)
    assert isinstance(nuclear_info["accepted"], bool)
    assert nuclear_info["price"] == 40
    assert nuclear_info["qty"] == 80


# ── Linked block ──────────────────────────────────────────────────────

def test_linked_block_returns_result():
    """Linked block scenario returns optimal result."""
    result = scenario_linked_block()
    assert result["status"] == "Optimal"
    assert result["traded"] > 0


def test_linked_blocks_together():
    """Linked blocks must be accepted or rejected together."""
    result = scenario_linked_block()
    blocks = result["orders"]["blocks"]
    a = blocks["Hydro_Upper"]["accepted"]
    b = blocks["Hydro_Lower"]["accepted"]
    assert a == b  # both accepted or both rejected


# ── Exclusive block ───────────────────────────────────────────────────

def test_exclusive_block_returns_result():
    """Exclusive block scenario returns optimal result."""
    result = scenario_exclusive_block()
    assert result["status"] == "Optimal"
    assert result["traded"] > 0


def test_exclusive_at_most_one():
    """At most one exclusive block is accepted."""
    result = scenario_exclusive_block()
    blocks = result["orders"]["blocks"]
    accepted = [b["accepted"] for b in blocks.values()]
    assert sum(accepted) <= 1  # at most one exclusive block


# ── run_all ───────────────────────────────────────────────────────────

def test_run_all_returns_three():
    """run_all returns 3 results (one per scenario)."""
    results = run_all()
    assert len(results) == 3
    names, outputs = zip(*results)
    assert "Simple Block" in names[0]
    assert "Linked Block" in names[1]
    assert "Exclusive Block" in names[2]
    for output in outputs:
        assert output["status"] == "Optimal"


# ── run_exclusive ─────────────────────────────────────────────────────

def test_run_exclusive_returns_recommendation():
    """run_exclusive returns result with recommendation key."""
    output = run_exclusive()
    assert "result" in output
    assert "recommendation" in output
    assert output["result"]["status"] == "Optimal"
    # recommendation is either a block name or "None"
    assert isinstance(output["recommendation"], str)
